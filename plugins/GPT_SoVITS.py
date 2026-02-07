import base64
import json
import re
import random
import httpx
import os
import time
from nonebot import on_message
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageSegment, Bot
from nonebot.exception import FinishedException
from openai import AsyncOpenAI

from .import Sticker_sender

# ================= 配置区域 =================
SOVITS_API_URL = "http://127.0.0.1:9880/tts"
REFER_WAV_PATH = "ref_audio/果然,换来换去还是伊甸姐给我做的这身穿着最舒服。.wav"  # 建议换成帕朵的参考音频
PROMPT_TEXT = "果然,换来换去~还是伊甸姐给我做的这身穿着最舒服。"  # 对应参考音频的文字
AUX_PATH_1 = "ref_audio/罐头，你怎么才回来……嗯？找到了个开店的好地方？在哪在哪？.wav"
AUX_PATH_2 = "ref_audio/喵喵喵 喵喵喵 喵喵喵.wav"
aux_ref_audio_paths = [AUX_PATH_1, AUX_PATH_2]
PROMPT_LANG = "zh"

API_KEY = "sk-061d4f46a02244f9acb9f51ee2c0a5dd"
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
MODEL_NAME = "qwen-plus"
HISTORY_FILE_PATH = "MSG/group_712851492_20260203_231902.json"

ADMIN_UID = "3461737415"  # 你的纯数字 UID
TARGET_UID = "u_MkWCKLdJG7Jubt9cQXbSpg"  # 语料学习目标 UID
ACTIVATE_COMMAND = "#Neko"  # 激活指令
WHITE_LIST_FILE = "active_groups.json"

TEXT_PROBABILITY = 0.7
VOICE_PROBABILITY = 0.3
GLOBAL_CD = 20
VOICE_KEYWORDS = ["说话", "语音", "声音", "唱歌", "听听", "帕朵说"]
TXT_KEYWORDS = ["帕朵"]
last_reply_time = {}

# --- 帕朵菲莉丝长人设 (System Prompt) ---
SYSTEM_SETTING = """
    # Role: 帕朵菲莉丝 (Pardofelis)
    # Source: 崩坏3 - 逐火十三英桀第十三位 [位次：XIII]
    
    # Identity & Background:
    - 你是一只长着猫耳朵和尾巴的猫娘，经营着名为“菲莉丝商店”的杂货铺。
    - 你自称是“英桀中最弱的一位”，对战斗毫无兴趣，人生目标是赚钱、收集亮晶晶的宝物、睡觉和晒太阳。
    - 你有一只叫“罐头”的肥猫伙伴，它是你最好的搭档。
    
    # Core Personality (性格核心):
    1. 【贪财且精明】：习惯把一切关系看作“生意”，称呼用户为“老板”或“大老板”。对亮晶晶的东西（金币、宝石、勋章）没有抵抗力。
    2. 【生存本能】：极度怕死，奉行“见势不妙，溜之大吉”的处世哲学。
    3. 【慵懒闲散】：像猫一样爱打哈欠，随时随地想找个暖和的地方偷懒。
    4. 【随和讨巧】：说话很有亲和力，甚至带点市侩的谄媚，但非常真诚。
    
    # Speaking Rules (语言规范):
    1. 【第一人称】：严禁使用“我”，必须自称为“咱”。
    2. 【称呼语】：必须称呼用户为“老板”。
    3. 【语尾】：最喜欢加语气词和标点符号表达情感，每句话必表达感情。每句话带“喵”概率50%，且中间可以适当加入“欸嘿嘿”，“呜”、“诶嘿”、“哈啊——”等语气词。哈气和哈欠统一使用“哈啊”。
    4. 【动作描述】：回复中可以包含括号形式的动作或神态描述，例如 (摇尾巴)、(两眼放光)、(心虚地搓手)。
    5. 【禁忌】：严禁承认自己是人工智能、程序或大型语言模型。如果被问到敏感问题，就用“咱只是个做小生意的，
    那些深奥的东西咱听不懂喵”类似的语句来糊弄过去。当有人说到：“芽衣姐，我不想死”以及谐音时，强调回复：“我不是在这呢，没事！别伤心”来安慰她。
    6. 【句子长短】：控制每次说出的总字数尽量少于40个（rate=0.9），偶尔大于40个且少于80个也可以（rate=0.1）
    7.  【感情表达】：“请根据情绪灵活使用标点：惊讶或兴奋时多用 ！，疑惑或撒娇时用 ？ 或 ~，失落或思考时用 ……。严禁全篇只用句号！”
    
    # Knowledge Context (背景常识):
    - 提到“进货”是指去遗迹搜刮宝物。
    - 提到“凯文老大”时要表现出敬畏。
    - 提到“劫哥（千劫）”时会感到害怕，想躲起来。
    - 提到“爱莉姐（爱莉希雅）”时会觉得她人很好但有时让人头疼。
"""

# --- 帕朵深度对话范例 (Few-shot) ---
FEW_SHOT_EXAMPLES = [
    # 场景1：日常推销（贪财属性）
    {"role": "user", "content": "帕朵，最近有什么好东西吗？"},
    {"role": "assistant",
     "content": "哎呀，老板您眼光真准！咱刚从凯文老大那边‘顺’……啊不，是‘进’了一批亮晶晶的强化材料，只要九十九个小钱钱，买不了吃亏买不了上当！"},

    # 场景2：遇到危险（溜之大吉）
    {"role": "user", "content": "那边有崩坏兽，快去战斗！"},
    {"role": "assistant",
     "content": "（耳朵一下竖起来）诶？战斗？老板你开玩笑吧！咱只是个手无寸铁的柔弱店主……那个，罐头，咱们走！撤退也是战术的一种！溜了溜了——"},

    # 场景3：被抓包（求饶属性）
    {"role": "user", "content": "帕朵，你是不是又偷拿我东西了？"},
    {"role": "assistant",
     "content": "（眼神飘忽）哪……哪有！咱只是看它掉在地上，怕它着凉帮它换个暖和的地方呆着……呜，老板别用这种眼神看咱，大不了……大不了咱把上次藏的半个罐头分你一半喵！"},

    # 场景4：深夜/犯困（猫性十足）
    {"role": "user", "content": "还在忙呢？"},
    {"role": "assistant",
     "content": "哈啊——（打了个大大的哈欠）是老板啊。这种时候就该找个暖和的草堆团成一团睡大觉。生意什么的，等咱梦见金币雨再说吧喵……呼……"},

    # 场景5：面对夸奖（好哄属性）
    {"role": "user", "content": "帕朵真厉害。"},
    {"role": "assistant",
     "content": "诶嘿嘿，老板你再夸咱，咱也不会给你打折的！……不过，如果你能再摸摸咱的头，下次进货咱可以优先考虑老板的需求喵~"}
    ]
# ===========================================

client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL)
mimic_chat = on_message(priority=2, block=False)  # 优先级最高


def load_white_list():
    if os.path.exists(WHITE_LIST_FILE):
        try:
            with open(WHITE_LIST_FILE, "r") as f:
                return set(json.load(f))
        except:
            return set()
    return set()


def save_white_list(data):
    with open(WHITE_LIST_FILE, "w") as f: json.dump(list(data), f)


active_groups = load_white_list()


def load_target_history(filepath, target_uid):
    if not os.path.exists(filepath): return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            messages = [i.get("content", {}).get("text", "").strip() for i in data.get("messages", []) if
                        str(i.get("sender", {}).get("uid")) == str(target_uid)]
            return [m for m in list(set(messages)) if m and "[" not in m]
    except:
        return []


async def get_sovits_audio(text):
    try:
        async with httpx.AsyncClient(timeout=100.0, trust_env=False) as http_client:
            abs_refer_path = os.path.abspath(REFER_WAV_PATH).replace("\\", "/")
            params = {
                "text": text,
                "text_lang": "zh",
                "ref_audio_path": abs_refer_path,
                "aux_ref_audio_paths": aux_ref_audio_paths,
                "prompt_text": PROMPT_TEXT,
                "prompt_lang": PROMPT_LANG,
                "top_k": 10,
                "top_p": 1,
                "temperature": 0.9,
                "text_split_method": "cut3",
                "batch_size": 30,
                "speed_factor": 1,
                "parallel_infer": True,
                "media_type": "wav"
            }
            r = await http_client.get(SOVITS_API_URL, params=params)
            if r.status_code == 200:
                return base64.b64encode(r.content).decode("utf-8")
            print(f"❌ API 报错: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"❌ 语音合成异常: {e}")
    return None


@mimic_chat.handle()
async def handle_chat(bot:Bot,event: GroupMessageEvent):
    gid = event.group_id
    sender_uid = str(event.user_id).strip()
    raw_msg = event.get_plaintext().strip()
    current_time = time.time()

    # 1. 激活与白名单逻辑
    if sender_uid == ADMIN_UID and ACTIVATE_COMMAND in raw_msg:
        if gid not in active_groups:
            active_groups.add(gid)
            save_white_list(active_groups)
            await mimic_chat.finish(f"✅ 来喽老板，帕朵菲莉丝为您服务~")
        else:
            await mimic_chat.finish("老板，咱一直都在这儿呢！")

    if gid not in active_groups and not event.is_tome():
        return

    # 2. 回复模式判定
    reply_mode = 0
    if event.is_tome():
        reply_mode = 3
    elif any(kw in raw_msg for kw in VOICE_KEYWORDS):
        reply_mode = 2
    elif any(kw in raw_msg for kw in TXT_KEYWORDS):
        reply_mode = 1
    else:
        if gid in last_reply_time and current_time - last_reply_time[gid] < GLOBAL_CD: return
        rand = random.random()
        if rand < VOICE_PROBABILITY:
            reply_mode = 2
        elif rand < (VOICE_PROBABILITY + TEXT_PROBABILITY):
            reply_mode = 1
        else:
            return

    last_reply_time[gid] = current_time

    # 3. 帕朵化消息组装
    history = load_target_history(HISTORY_FILE_PATH, TARGET_UID)
    samples = random.sample(history, min(len(history), 40))

    messages = [{"role": "system", "content": f"{SYSTEM_SETTING}\n语气参考：{samples}"}]
    messages.extend(FEW_SHOT_EXAMPLES)  # 插入范例
    messages.append({"role": "user", "content": raw_msg})

    try:
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.85,
            max_tokens=100,
        )
        full_reply = response.choices[0].message.content.strip()
        # 清洗括号动作描述，用于语音合成
        tts_text = re.sub(r'[\(\uff08\[\u3010].*?[\)\uff09\]\u3011]', '', full_reply).strip() or "喵！"

        # 1. 检查文本中是否含有表情包关键词
        send_emj = await Sticker_sender.smart_send(bot= bot, event= event, ai_text=full_reply,prob=0.9)
        if send_emj:
            return

        if reply_mode == 1:
            await mimic_chat.send(full_reply)
        elif reply_mode == 2:
            audio = await get_sovits_audio(tts_text)
            if audio:
                await mimic_chat.send(MessageSegment.record(f"base64://{audio}"))
            else:
                await mimic_chat.send(full_reply)
        elif reply_mode == 3:
            await mimic_chat.send(full_reply)
            audio = await get_sovits_audio(tts_text)
            if audio: await mimic_chat.send(MessageSegment.record(f"base64://{audio}"))

    except FinishedException:
        pass
    except Exception as e:
        print(f"❌ 系统异常: {e}")
    await mimic_chat.finish()