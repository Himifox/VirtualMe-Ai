import os
import json
import hashlib
import aiohttp
import aiofiles
from nonebot import on_message, on_command, logger
from nonebot.adapters.onebot.v11 import Bot, Event

#==============================
#
#==============================
QWEN_API_KEY = "sk-5a6373479d5d4d538b872e537fabfa28"
QWEN_MODEL = "qwen2-vl-7b-instruct"
COLLECTION_DIR = "sticker_collection"
COLLECTION_NAME = ""
COLLECTION_JSON = "sticker_collection.json"


#===================================

#===================================
os.makedirs(COLLECTION_DIR, exist_ok=True)
if not os.path.exists(COLLECTION_JSON):
    with open(COLLECTION_JSON, "w", encoding="utf-8") as f:
        json.dump({}, f, ensure_ascii=False, indent=2)

async def load_collection():
    async with aiofiles.open(COLLECTION_JSON, "r", encoding="utf-8") as f:
        content = await f.read()
        return json.loads(content)

async def save_collection(collection):
    async with aiofiles.open(COLLECTION_JSON, "w", encoding="utf-8") as f:
        content = await f.write(json.dumps(collection, ensure_ascii=False, indent=2))

sticker_listen = on_message(priority=10,block=False)
# ======================================
#
# ======================================]
async def md5_url(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            content = await response.read()
            md5_obj = hashlib.md5(content)
            md5 = md5_obj.hexdigest()
            return md5

#=======================================

#======================================
current_img = {}
@sticker_listen.handle()
async def _(bot: Bot, event: Event):
    user_id = event.get_user_id()
    for seg in event.get_message():
        print(f"DEBUG: 收到消息类型={seg.type}，详细数据={seg.data}")

        if seg.type == "image":
            img_url = seg.data.get("url")
            img_md5 = seg.data.get("md5", "").lower()
            coll = await load_collection()
            # --- [核心修复] 处理没有 MD5 的情况 ---
            if not img_url:

                return
            if not img_md5 and img_url:
                # 这里缺少检查md5是否已经存在
                print("DEBUG: 正在计算图片 MD5...")
                img_md5 = await md5_url(img_url)
            # ------------------------------------

            # 记录到内存
            current_img[user_id] = {"md5": img_md5, "url": img_url}

            # 检查本地是否已收藏
            coll = await load_collection()
            if img_md5 in coll:
                await sticker_listen.send(f"[√本地已收藏] {coll[img_md5]}")
                old_meaning = coll[img_md5]
                coll[img_md5] = {"meaning":old_meaning, "url": img_url}
                await save_collection(coll)
                logger.info(f"✅ 成功修复旧数据: {img_md5}")
                return

            # --- [全自动模式] 立即识别并保存 ---
            print("DEBUG: 检测到新表情，开始 AI 识别...")
            meaning = await qwen_recognize_sticker(img_url)
            if meaning:
                # 存入数据库
                coll[img_md5] =  {"meaning":meaning, "url": img_url}
                await save_collection(coll)
                # 告诉用户结果
                await sticker_listen.send(f"AI识别成功：{meaning} (已自动收藏)")
            else:
                print("DEBUG: AI 识别返回为空")
            return

#===========================================
# save_sticker 貌似没有
#===========================================
save_sticker = on_command("收藏",aliases={"保存表情包","收藏这个表情"})
@save_sticker.handle()
async def _(bot: Bot, event: Event):
    user_id = event.get_user_id()
    if user_id  not in current_img:
        await save_sticker.send(f"请你先发表情包！！")
        return
    img = current_img[user_id]
    img_md5 = img["md5"]
    img_url = img["url"]
    meaning = await qwen_recognize_sticker(img_url)
    if not meaning:
        await save_sticker.send("识别失败！！")
        return
    coll = await load_collection()
    coll[img_md5] = {"meaning": meaning, "url": img_url}
    await save_collection(coll)
    await save_sticker.send(f"收藏成功\n【表情含义】{meaning}")

# ======================================================================

#=======================================================================
async def qwen_recognize_sticker(img_url:str)-> str|None:
    api_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {QWEN_API_KEY}",
    }
    prompt = ("""
                请你识别表情包意思，采用关键词，使用文字和颜文字，如：“害羞”，“盯着你”，“QAQ”，
                总字数最多10个。必要时，可以超过10个字数但不多于20个字。
                关键词按照可能性比例分先后顺序。
                【严格按照以下格式输出】
                案例1：“这张表情包的意思是：“惊讶”。关键词：惊讶、震撼、不可思议”。
                案例2："这张表情包的意思是：“不好意思”。关键词：无奈、尴尬、难过"
                案例3："这张图片的意思是：“困惑”。关键词：卖萌、困惑、不知道怎么办、QAQ（表示无奈或无语）"
              """)
    pyload = {
        "model": QWEN_MODEL,
        "input": {
            "messages":[{
                "role":"user",
                "content":[
                    {"image":img_url},
                    {"text":prompt},
                ]
            }]
        },
        "parameters":{"result_format":"message"},
    }
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(api_url, json=pyload) as response:
                if response.status != 200:
                    return None
                data = await response.json()
                return data["output"]["choices"][0]["message"]["content"][0]["text"].strip()
    except aiohttp.ClientError as e:
        print(f"出错了:{e}")
        return None