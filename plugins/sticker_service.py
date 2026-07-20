import os
import re
import random
import json
import hashlib
import aiohttp
import aiofiles
from nonebot import on_message, on_command, logger
from nonebot.adapters.onebot.v11 import Bot, Event, MessageSegment, Message, GroupMessageEvent, PrivateMessageEvent
from plugins.config import QWEN_VL_API_KEY, QWEN_VL_MODEL

#==============================
# 配置项
#==============================

COLLECTION_DIR = "sticker_collection"
COLLECTION_JSON = "sticker_collection.json"
#===================================
# 异步读写 JSON
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
        await f.write(json.dumps(collection, ensure_ascii=False, indent=2))

# ======================================
# 工具：转换MD5值
# ======================================
async def md5_url(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            content = await response.read()
            md5_obj = hashlib.md5(content)
            return md5_obj.hexdigest()

# ==========================================================
# 模块一：【被动技能】全自动表情包学习机 (监听群聊图片)
# ==========================================================
sticker_listen = on_message(priority=99, block=False)

@sticker_listen.handle()
async def _(bot: Bot, event: Event):
    # 只过滤图片消息，避免满屏幕的 DEBUG text 刷屏
    for seg in event.get_message():
        if seg.type == "image":
            img_url = seg.data.get("url")
            img_md5 = seg.data.get("md5", "").lower()
            
            if not img_url:
                continue
                
            if not img_md5:
                print("DEBUG: 正在计算图片 MD5...")
                img_md5 = await md5_url(img_url)

            coll = await load_collection()
            
            # 检查本地是否已收藏
            if img_md5 in coll:
                old_data = coll[img_md5]
                # 【修复Bug】防止字典重复嵌套
                old_meaning = old_data.get("meaning", old_data) if isinstance(old_data, dict) else old_data
                coll[img_md5] = {"meaning": old_meaning, "url": img_url}
                await save_collection(coll)
                logger.info(f"✅ 更新已有表情包 URL: {img_md5}")
            

            # 全自动模式：立即识别并保存
            print("DEBUG: 检测到新表情，开始 AI 识别...")
            meaning = await qwen_recognize_sticker(img_url)
            if meaning:
                coll[img_md5] = {"meaning": meaning, "url": img_url}
                await save_collection(coll)
                logger.info(f"🎉 AI识别成功：{meaning} (已自动收藏)")
            
            else:
                print("DEBUG: AI 识别返回为空")

            # 确保文件夹存在
            os.makedirs("sticker_collection", exist_ok=True)
            local_img_path = f"sticker_collection/{img_md5}.png"

            # 如果本地还没有这张图，就把它下载下来！
            if not os.path.exists(local_img_path) and img_url:
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(img_url) as resp:
                            if resp.status == 200:
                                img_data = await resp.read()
                                async with aiofiles.open(local_img_path, "wb") as f:
                                    await f.write(img_data)
                                print(f"✅ 图片已成功下载到本地: {local_img_path}")
                except Exception as e:
                    print(f"❌ 下载图片失败: {e}")

async def qwen_recognize_sticker(img_url: str) -> str | None:
    if not QWEN_VL_API_KEY:
        logger.warning("QWEN_VL_API_KEY is not configured; skip sticker recognition.")
        return None

    api_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {QWEN_VL_API_KEY}",
    }
    prompt = """
        请你识别表情包意思，采用关键词，使用文字和颜文字，如：“害羞”，“盯着你”，“QAQ”，
        总字数最多10个。必要时，可以超过10个字数但不多于20个字。
        关键词按照可能性比例分先后顺序。

        【严格按照以下格式输出】
        案例1：“这张表情包的意思是：“惊讶”。关键词：惊讶、震撼、不可思议”。
        案例2："这张表情包的意思是：“不好意思”。关键词：无奈、尴尬、难过"
        案例3："这张图片的意思是：“困惑”。关键词：卖萌、困惑、不知道怎么办、QAQ（表示无奈或无语）"
    """
    pyload = {
        "model": QWEN_VL_MODEL,
        "input": {"messages": [{"role": "user", "content": [{"image": img_url}, {"text": prompt}]}]},
        "parameters": {"result_format": "message"},
    }
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(api_url, json=pyload) as response:
                if response.status != 200: return None
                data = await response.json()
                return data["output"]["choices"][0]["message"]["content"][0]["text"].strip()
    except Exception as e:
        print(f"出错了:{e}")
        return None

# ==========================================================
# 模块二：【主动技能】智能表情包发送系统 (供 GPT 插件调用)
# ==========================================================
async def find_md5_by_json(text: str) -> tuple | None:
    coll = await load_collection()
    for md5, item_data in coll.items():
        if isinstance(item_data, dict):
            description = item_data.get("meaning", "")
            url = item_data.get("url")
        else:
            description = str(item_data)
            url = None

        if not url: continue

        if "关键词" in description:
            parts = re.split(r'关键词[：:]\s*', description)
            if len(parts) > 1:
                keywords_part = parts[-1]
                keywords_list = re.split(r'[、,，]', keywords_part.replace("。", ""))
                for kw in keywords_list:
                    kw = kw.strip()
                    if kw and kw in text:
                        return md5, url
    return None

async def smart_send(bot: Bot, event: Event, ai_text: str, prob: float) -> bool:
    result = await find_md5_by_json(ai_text)
    if result:
        target_md5, target_url = result
        if random.random() < prob:
            logger.info(f"🎯 触发表情包！[MD5: {target_md5}]")
            await bot.send(event, MessageSegment.image(file=target_url))
            return True 
    return False
