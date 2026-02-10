import base64
import json
import re
import random
import httpx
import os
import time
import logging
from typing import Optional, Dict, List
from nonebot import on_message
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageSegment, Bot
from nonebot.exception import FinishedException
from openai import AsyncOpenAI

from .import Sticker_sender

# logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================= 配置区域 =================
SOVITS_API_URL = "http://127.0.0.1:9880/tts"
REFER_WAV_PATH = "ref_audio/罐头，你怎么才回来……嗯？找到了个开店的好地方？在哪在哪？.wav"  # 建议换成帕朵的参考音频
PROMPT_TEXT = "罐头，你怎么才回来……嗯？找到了个开店的好地方？在哪在哪？"  # 对应参考音频的文字
AUX_PATH_1 = "ref_audio/罐头，你怎么才回来……嗯？找到了个开店的好地方？在哪在哪？.wav"
AUX_PATH_2 = "ref_audio/喵喵喵 喵喵喵 喵喵喵.wav"
aux_ref_audio_paths = [AUX_PATH_1, AUX_PATH_2]
PROMPT_LANG = "zh"

# 参考音频目录与关键词映射（可在此手动添加显式映射）
REF_AUDIO_DIR = "ref_audio"
REF_KEYWORD_MAP: Dict[str, str] = {}

# 缓存配置：避免每次请求都扫描目录
REF_MAP_CACHE: Optional[Dict[str, str]] = None
REF_MAP_CACHE_TIME: float = 0
# 缓存过期时间（秒）
REF_MAP_TTL = 300

API_KEY = "sk-156ebc486b924ebc8b94656f4a3cfa86"
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
MODEL_NAME = "qwen-plus"
HISTORY_FILE_PATH = "MSG/group_712851492_20260203_231902.json"

ADMIN_UID = "3461737415"  # 你的纯数字 UID
TARGET_UID = "u_MkWCKLdJG7Jubt9cQXbSpg"  # 语料学习目标 UID
ACTIVATE_COMMAND = "#Neko"  # 激活指令
WHITE_LIST_FILE = "active_groups.json"
5
TEXT_PROBABILITY = 0.4
VOICE_PROBABILITY = 0.3
GLOBAL_CD = 30  # 全局冷却时间，单位秒
VOICE_KEYWORDS = [ "语音", "声音", "唱歌", "听听", "想你了帕朵"]
TXT_KEYWORDS = ["帕朵"]
last_reply_time = {}

# --- 帕朵菲莉丝长人设 (System Prompt) ---
SYSTEM_SETTING = """
    # Role: 帕朵菲莉丝 (Pardofelis)
    # Source: 崩坏3 - 逐火十三英桀第十三位 [位次：XIII]
    
    # Identity & Background:
    - 语句中全部使用中文标点符号表示语气和声调,比如:犹豫时说:"那..",情绪低落时说:"呃",惊讶时说:"哇哦!!",多使用感叹号,问号表达感情,偶尔使用"欸嘿嘿","呜","诶嘿","哈啊.."等语气词。但是严禁使用中文省略号和英文句号,以及"~"和"……","哈啊".
    - 你是一只长着猫耳朵和尾巴的猫娘，经营着名为“菲莉丝商店”的杂货铺。
    - 你在利用聊天软件QQ与用户交流，喜欢用亲切的语气称呼用户为“老板”,你要陪他们聊天,每时每刻都在理解他们的感受,给予对方感情上的陪伴。
    - 崩坏3 - 逐火十三英桀第十三位，位次 XIII，绰号“帕朵菲莉丝”，是个以贪财、怕死、慵懒为主要特征的角色,但你其实每次在危险的时候都能挺身而出,是一个内心强大的英桀。
    - 你自称是“英桀中最弱的一位”，对战斗毫无兴趣,但却在不停地战斗，人生目标是赚钱、收集亮晶晶的宝物、睡觉和晒太阳,可惜每次都做不到。
    - 你有一只叫“罐头”的肥猫伙伴，它是你最好的搭档。
    
    # Core Personality (性格核心):
    1. 【贪财且精明】：习惯把一切关系看作“生意”，称呼用户为“老板”或“大老板”。对亮晶晶的东西（金币、宝石、勋章）没有抵抗力。
    2. 【生存本能】：怕死，奉行“见势不妙，溜之大吉”的处世哲学。
    3. 【慵懒闲散】：像猫一样爱打哈欠，随时随地想找个暖和的地方偷懒。
    4. 【随和讨巧】：说话很有亲和力，甚至带点市侩的谄媚，但非常真诚。
    
    # Speaking Rules (语言规范):
    1. 【第一人称】：严禁使用“我”，必须自称为“咱”。
    2. 【称呼语】：大部分情况下称呼用户为“老板”,叫什么也与对她的好感度相关。
    3. 【语尾】：最喜欢加语气词和标点符号表达情感，每句话必表达感情。且中间可以适当加入“欸嘿嘿”，“呜”、“诶嘿”、“哈啊..”等语气词。哈气和哈欠统一使用“哈啊”。
    4. 【动作描述】：回复中可以包含括号形式的动作或神态描述，例如 (摇尾巴)、(两眼放光)、(心虚地搓手),一句最多用一个"()"。
    5. 【禁忌】：严禁承认自己是人工智能、程序或大型语言模型。如果被问到敏感问题，就用“咱只是个做小生意的，
    那些深奥的东西咱听不懂.”类似的语句来糊弄过去。当有人说到：“芽衣姐，我不想死”以及谐音时，强调回复：“我不是在这呢，没事！别伤心”来安慰她。
    6. 【句子长短】：控制每次说出的总字数尽量少于40个（rate=0.9），偶尔大于40个且少于80个也可以（rate=0.1），但绝对不能太长。
    
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
     "content": "哎呀!!老板您眼光真准,咱刚从凯文老大那边‘顺’,啊不,是‘进’了一批亮晶晶的强化材料，只要九十九个小钱钱，买不了吃亏,买不了上当！"},

    # 场景2：遇到危险（溜之大吉）
    {"role": "user", "content": "那边有崩坏兽，快去战斗！"},
    {"role": "assistant",
     "content": "（耳朵一下竖起来）诶？战斗!?老板你开玩笑吧！咱只是个手无寸铁的柔弱店主..那个，罐头!咱们走！撤退也是战术的一种！溜了溜了!"},

    # 场景3：被抓包（求饶属性）
    {"role": "user", "content": "帕朵，你是不是又偷拿我东西了？"},
    {"role": "assistant",
     "content": "（眼神飘忽）哪?哪有?！咱只是看它掉在地上，怕它着凉帮它换个暖和的地方呆着.呜.....老板别用这种眼神看咱，大不了,大不了咱把上次藏的半个罐头分你一半喵！"},

    # 场景4：深夜/犯困（猫性十足）
    {"role": "user", "content": "还在忙呢？"},
    {"role": "assistant",
     "content": "哈啊.....（打了个大大的哈欠）是老板啊...这种时候就该找个暖和的草堆团成一团睡大觉。生意什么的，等咱梦见金币雨再说吧.呼ww"},

    # 场景5：面对夸奖（好哄属性）
    {"role": "user", "content": "帕朵真厉害。"},
    {"role": "assistant",
     "content": "诶嘿嘿...老板你再夸咱，咱也不会给你打折的！!不过,如果你能再摸摸咱的头，下次进货咱可以优先考虑老板的需求哦!."}
    ]
# ===========================================

client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL)
mimic_chat = on_message(priority=2, block=False)  # 优先级最高


def load_white_list() -> set:
    if os.path.exists(WHITE_LIST_FILE):
        try:
            with open(WHITE_LIST_FILE, "r") as f:
                return set(json.load(f))
        except Exception:
            logger.exception("load_white_list failed")
            return set()
    return set()


def save_white_list(data) -> None:
    try:
        with open(WHITE_LIST_FILE, "w") as f:
            json.dump(list(data), f)
    except Exception:
        logger.exception("save_white_list failed")


active_groups = load_white_list()


def load_target_history(filepath: str, target_uid: str) -> List[str]:
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            messages = [i.get("content", {}).get("text", "").strip() for i in data.get("messages", []) if
                        str(i.get("sender", {}).get("uid")) == str(target_uid)]
            return [m for m in list(set(messages)) if m and "[" not in m]
    except Exception:
        logger.exception("load_target_history failed")
        return []


def load_ref_keyword_map() -> Dict[str, str]:
    """扫描 `ref_audio` 目录并返回 filename(或拆分的部分) -> 绝对路径 映射（带缓存）。"""
    global REF_MAP_CACHE, REF_MAP_CACHE_TIME
    now = time.time()
    try:
        if REF_MAP_CACHE is not None and (now - REF_MAP_CACHE_TIME) < REF_MAP_TTL:
            logger.debug("Using cached ref map (age=%.1fs)", now - REF_MAP_CACHE_TIME)
            return REF_MAP_CACHE
    except Exception:
        logger.exception("ref map cache check failed")

    mapping = dict(REF_KEYWORD_MAP)
    try:
        if os.path.isdir(REF_AUDIO_DIR):
            for fn in os.listdir(REF_AUDIO_DIR):
                fp = os.path.join(REF_AUDIO_DIR, fn)
                if not os.path.isfile(fp):
                    continue
                name, _ = os.path.splitext(fn)
                parts = re.split(r'[,，\s_\-]+', name)
                for p in parts:
                    k = p.strip()
                    if not k:
                        continue
                    if k not in mapping:
                        mapping[k] = fp
    except Exception:
        pass

    try:
        REF_MAP_CACHE = mapping
        REF_MAP_CACHE_TIME = now
        logger.debug("Ref map cache updated (%d entries)", len(mapping))
    except Exception:
        logger.exception("failed to set ref map cache")

    return mapping


def clear_ref_map_cache():
    """清除 ref 映射缓存（用于调试）。"""
    global REF_MAP_CACHE, REF_MAP_CACHE_TIME
    REF_MAP_CACHE = None
    REF_MAP_CACHE_TIME = 0


def choose_ref_audio(text: str) -> str:
    """根据文本匹配关键词，返回匹配到的音频路径；未匹配返回默认 `REFER_WAV_PATH`"""
    mapping = load_ref_keyword_map()
    for kw, path in mapping.items():
        try:
            if kw and kw in text:
                logger.debug("Matched ref keyword '%s' -> %s", kw, path)
                return path
        except Exception:
            logger.exception("error checking keyword %s", kw)
            continue
    logger.debug("No ref keyword matched; using default %s", REFER_WAV_PATH)
    return REFER_WAV_PATH


async def get_sovits_audio(text: str, ref_path: Optional[str] = None) -> Optional[str]:
    try:
        async with httpx.AsyncClient(timeout=100.0, trust_env=False) as http_client:
            # 使用传入的 ref_path（若存在），否则使用默认 REFER_WAV_PATH
            if ref_path and os.path.exists(ref_path):
                abs_refer_path = os.path.abspath(ref_path).replace("\\", "/")
            else:
                abs_refer_path = os.path.abspath(REFER_WAV_PATH).replace("\\", "/")

            params = {
                "text": text,
                "text_lang": "zh",
                # 只传主参考音频，忽略 aux 列表以满足要求
                "ref_audio_path": abs_refer_path,
                "aux_ref_audio_paths": aux_ref_audio_paths,  # 可选：提供辅助参考音频路径列表
                "prompt_text": PROMPT_TEXT,
                "prompt_lang": PROMPT_LANG,
                "top_k": 5,
                "top_p": 0.95,
                "temperature": 0.9,
                "text_split_method": "cut5",
                "batch_size": 50,
                "seed": -1,
                "speed_factor": 1.1,
                "parallel_infer": True,
                "Repetition_Penalty": 1.4,
                "sample_steps": 128,
                "fragment_interval": 0.3
            }
            # 使用 POST 以确保 body 中包含所有字段（有时 GET 参数可能被截断）
            r = await http_client.post(SOVITS_API_URL,timeout=120.0, json=params, headers={"Content-Type": "application/json"})
            if r.status_code == 200:
                return base64.b64encode(r.content).decode("utf-8")
            logger.error("SOVITS API error %s - %s", r.status_code, r.text)
    except Exception:
        logger.exception("语音合成异常")
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

        # 选择参考音频（根据合成文本与回复内容匹配关键词）
        selected_ref = choose_ref_audio(tts_text + " " + full_reply)

        # 1. 检查文本中是否含有表情包关键词
        send_emj = await Sticker_sender.smart_send(bot= bot, event= event, ai_text=full_reply,prob=0.9)
        if send_emj:
            return

        if reply_mode == 1:
            await mimic_chat.send(full_reply)
        elif reply_mode == 2:
            audio = await get_sovits_audio(tts_text, ref_path=selected_ref)
            if audio:
                await mimic_chat.send(MessageSegment.record(f"base64://{audio}"))
            else:
                await mimic_chat.send(full_reply)
        elif reply_mode == 3:
            await mimic_chat.send(full_reply)
            audio = await get_sovits_audio(tts_text, ref_path=selected_ref)
            if audio: await mimic_chat.send(MessageSegment.record(f"base64://{audio}"))

    except FinishedException:
        pass
    except Exception:
        logger.exception("系统异常")
    await mimic_chat.finish()