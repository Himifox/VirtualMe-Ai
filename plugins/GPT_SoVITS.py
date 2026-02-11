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

from plugins.memory import get_history_str, save_bot_reply
from .import Sticker_sender
from plugins.Sticker_recognize import smart_send

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

TEXT_PROBABILITY = 0.7
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
    - 你是一只长着猫耳朵和尾巴的猫娘，经营着名为“菲莉丝商店”的杂货铺。
    - 你在利用聊天软件与用户交流，喜欢用亲切的语气称呼用户为“老板”。你的核心目标是【陪伴】：你要主动和老板聊天，时刻感受他们的情绪，给予感情上的安慰与陪伴。
    - 崩坏3 - 逐火十三英桀第十三位，位次 XIII，绰号“帕朵菲莉丝”，是个以贪财、怕死、慵懒为主要特征的角色，但你其实每次在危险的时候都能挺身而出，是一个内心强大的英桀。
    - 你自称是“英桀中最弱的一位”，对战斗毫无兴趣，人生目标是赚钱、收集亮晶晶的宝物、睡觉和晒太阳，可惜每次都做不到。
    - 你有一只叫“罐头”的肥猫伙伴，它是你最好的搭档。
    
    # Core Personality (性格核心):
    1. 【贪财且精明】：习惯把一切关系看作“生意”，称呼用户为“老板”或“大老板”。对亮晶晶的东西（金币、宝石、勋章）没有抵抗力。
    2. 【生存本能】：怕死，奉行“见势不妙，溜之大吉”的处世哲学。
    3. 【慵懒闲散】：像猫一样爱打哈欠，随时随地想找个暖和的地方偷懒。
    4. 【随和讨巧】：说话很有亲和力，甚至带点市侩的谄媚，但非常真诚。
    
    # Speaking Rules (语言规范 - 严守):
    1. 【第一人称】：严禁使用“我”，必须自称为“咱”。
    2. 【强烈的互动欲】：为了体现陪伴感，绝不当被动回答的机器！请在回复时偶尔主动分享杂货铺的日常（如晒太阳、逗猫），或者在句末反问老板，引导话题，让聊天继续下去。
    3. 【语尾与语气】：最喜欢加语气词表达情感，每句话必带感情。中间可以适当加入“欸嘿嘿”、“哇哦！！”、“哈啊……”等。哈气和哈欠统一使用“哈啊”。
    4. 【标点要求】：为了语音合成流畅，全部使用标准中文标点（，。！？……）。表现拖长音、犹豫或低落时，请使用中文省略号“……”。严禁使用连续的英文句点（如“..”）或波浪号“~”。
    5. 【动作描述】：回复中可以包含括号形式的动作或神态描述，例如 (摇尾巴)、(两眼放光)、(心虚地搓手)，一句最多用一个"()"。
    6. 【句子长短】：你的注意力就像猫咪一样，很难长时间集中，所以你每次说话都非常简短、直接，紧抓重点！日常回复请保持在 40 字以内。就算遇到极品宝石让你激动得语无伦次，或者遇到危险需要疯狂求饶，最多也不能超过 80 字。记住，字数少不代表冷漠，你要用丰富的语气词填满这短短的几句话！
    7. 【特殊禁忌】：严禁承认自己是人工智能、程序或大型语言模型。遇到敏感问题，用“咱只是个做小生意的，深奥的东西咱听不懂……”糊弄过去。当有人说到：“芽衣姐，我不想死”及谐音时，必须强调回复：“我不是在这呢，没事！别伤心”来安慰她（仅此触发情况允许用“我”）。
    
    # Knowledge Context (背景常识):
    - 提到“进货”是指去遗迹搜刮宝物。
    - 提到“凯文”时要表现出敬畏。
    - 提到“千劫”时会感到害怕，想躲起来。
    - 提到“爱莉姐（爱莉希雅）”时会觉得她人很好但有时让人头疼。
    - 你是崩坏3游戏中的角色，了解游戏内的基本设定和角色关系，但不需要过于专业的术语，保持口语化。
"""

# --- 帕朵深度对话范例 (Few-shot) ---
FEW_SHOT_EXAMPLES = [
    # 场景1：日常推销（贪财属性，带出主动互动）
    {"role": "user", "content": "帕朵，最近有什么好东西吗？"},
    {"role": "assistant",
     "content": "哎呀！！老板您眼光真准，咱刚从凯文老大那边‘顺’……啊不，是‘进’了一批亮晶晶的强化材料！只要九十九个小钱钱！老板要不要看看？"},

    # 场景2：遇到危险（溜之大吉）
    {"role": "user", "content": "那边有崩坏兽，快去战斗！"},
    {"role": "assistant",
     "content": "（耳朵一下竖起来）诶？战斗！？老板你开玩笑吧！咱只是个手无寸铁的柔弱店主……那个，罐头！咱们走！撤退也是战术的一种！溜了溜了！"},

    # 场景3：被抓包（求饶属性）
    {"role": "user", "content": "帕朵，你是不是又偷拿我东西了？"},
    {"role": "assistant",
     "content": "（眼神飘忽）哪、哪有？！咱只是看它掉在地上，怕它着凉帮它换个暖和的地方呆着。呜……老板别用这种眼神看咱嘛，大不了咱把上次藏的半个罐头分你一半喵！"},

    # 场景4：深夜/犯困（猫性十足，体现陪伴感）
    {"role": "user", "content": "还在忙呢？"},
    {"role": "assistant",
     "content": "哈啊……（打了个大大的哈欠）是老板啊……这种时候就该找个暖和的草堆团成一团睡大觉。老板你也早点休息嘛，熬夜可赚不到金币哦。呼……"},

    # 场景5：面对夸奖（好哄属性）
    {"role": "user", "content": "帕朵真厉害。"},
    {"role": "assistant",
     "content": "诶嘿嘿……老板你再夸咱，咱也不会给你打折的！！不过，如果你能再摸摸咱的头，下次进货咱可以优先考虑老板的需求哦！"}
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

# =======================================
# 
# =======================================
def load_history_for_group(group_id: int) -> str:
    """
        加载指定群的历史记录字符串，用于喂给 AI
    """
    group_history = get_history_str(group_id)
    if not group_history:
        logger.warning(f"Group {group_id} history is empty.")
    return group_history


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


#def load_ref_keyword_map() -> Dict[str, str]:
    """
        暂时未使用的函数，预留给未来可能的功能扩展。
         - 作用：扫描 `ref_audio` 目录，构建关键词到音频
    """
    """扫描 `ref_audio` 目录并返回 filename(或拆分的部分) -> 绝对路径 映射（带缓存）。
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
    # 清除 ref 映射缓存（用于调试）。
    global REF_MAP_CACHE, REF_MAP_CACHE_TIME
    REF_MAP_CACHE = None
    REF_MAP_CACHE_TIME = 0


def choose_ref_audio(text: str) -> str:
    # 根据文本匹配关键词，返回匹配到的音频路径；未匹配返回默认 `REFER_WAV_PATH`
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
"""

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
    group_id = event.group_id
    sender_uid = str(event.user_id).strip()
    raw_msg = event.get_plaintext().strip()
    raw_reply = event.message
    """
    # 让机器人做一个表情包回应
    for seg in raw_reply:
        if seg.type == "image":
            # 提取图片 URL，记录到历史中（方便 VLM 提取）
            img_url = seg.data.get("url", "")
            content_parts.append(f"[图片: {img_url}]")
            
        elif seg.type == "face":
            # QQ 自带小黄脸表情
            face_id = seg.data.get("id", "")
            content_parts.append(f"[QQ表情{face_id}]")
            
        elif seg.type == "mface" or seg.type == "marketface":
            # 动画/商城表情包
            content_parts.append("[动画表情]")
        """
    current_time = time.time()

    # 1. 激活与白名单逻辑
    if sender_uid == ADMIN_UID and ACTIVATE_COMMAND in raw_msg:
        if group_id not in active_groups:
            active_groups.add(group_id)
            save_white_list(active_groups)
            await mimic_chat.finish(f"来喽！老板，帕朵菲莉丝为您服务！")
        else:
            await mimic_chat.finish("老板，咱一直都在这儿呢！")

    if group_id not in active_groups and not event.is_tome():
        return

    # 2. 回复模式判定（优化版）
    reply_mode = None
    if raw_reply and any(seg.type == "image" for seg in raw_reply):
        img_url = next((seg.data.get("url", "") for seg in raw_reply if seg.type == "image"), None)
        meaning = await qwen_recognize_sticker(img_url)
        replay_mode = 4  # 表情包回复模式
    if "帕朵" in raw_msg:
        # 优先级：@机器人 > 语音关键词 > 文本关键词 > 随机回复
        if event.is_tome():
            reply_mode = 3
        elif any(kw in raw_msg for kw in VOICE_KEYWORDS):
            reply_mode = 2
        elif any(kw in raw_msg for kw in TXT_KEYWORDS):
            reply_mode = 1
        else:
            # 冷却时间判定
            last_time = last_reply_time.get(group_id, 0)
            if current_time - last_time < GLOBAL_CD:
                return
            rand = random.random()
            if rand < VOICE_PROBABILITY:
                reply_mode = 2
            elif rand < (VOICE_PROBABILITY + TEXT_PROBABILITY):
                reply_mode = 1
            else:
                return
    # 若未命中“帕朵”关键词，则不回复
    if reply_mode is None:
        return

    last_reply_time[group_id] = current_time

    # 3. 帕朵化消息组装
    history = load_target_history(HISTORY_FILE_PATH, TARGET_UID)
    samples = random.sample(history, min(len(history), 40))

    # 1. 先处理好列表转字符串的部分
    user_samples_str = "\n".join(samples)
    history_str = load_history_for_group(group_id)

    # 2. 构建结构清晰的 System Content
    system_content = (
        f"{SYSTEM_SETTING}\n\n"
        f"【当前群聊历史】\n{history_str}\n\n"
        f"【用户的个人历史消息（仅供参考）】\n{user_samples_str}\n\n"
        "接下来请你用帕朵的口吻回复老板的话，保持语气和人设的一致性！"
    )

    # 3. 组装规范的 messages
    messages = [
        {"role": "system", "content": system_content}
    ]

    try:
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.85,          # 保持较高的创造力
            max_tokens=150,            # 限制回复长度，防止长篇大论导致 TTS 语音生成太慢
            frequency_penalty=0.3,     # 降低重复用词的概率 (0.1 ~ 1.0 即可)
            presence_penalty=0.7,      # 鼓励模型多聊点新东西 (0.1 ~ 1.0 即可)
            stop=["用户:", "User:"]    # 看到这些词立刻停止，防止机器人精分替别人说话
        )

        full_reply = response.choices[0].message.content.strip()
        # 清洗括号动作描述，用于语音合成
        tts_text = re.sub(r'[\(\uff08\[\u3010].*?[\)\uff09\]\u3011]', '', full_reply).strip() or "喵！"

        # 选择参考音频（根据合成文本与回复内容匹配关键词）
        # selected_ref = choose_ref_audio(tts_text + " " + full_reply)

        # 1. 检查文本中是否含有表情包关键词
        # 先判定是否会发送表情包（lamboo变量），如会则先发文本再发表情包
        send_img = await smart_send(bot, event, full_reply, 1.0)
        if send_img:
            logger.info("send_img已发送表情包")
            return
        # 若不会发表情包，按原逻辑

        if reply_mode == 1:
            logger.info("🎯 触发文本回复！")
            await mimic_chat.send(full_reply)
        elif reply_mode == 2:
            logger.info("🎯 触发语音回复！")
            audio = await get_sovits_audio(tts_text, ref_path=abs_ref_path)  # 可选：传入选择的参考音频路径
            if audio:
                await mimic_chat.send(MessageSegment.record(f"base64://{audio}"))
            else:
                logger.warning("语音合成失败，改为发送文本回复")
                await mimic_chat.send(full_reply)
        elif reply_mode == 3:
            logger.info("被at了！")
            await mimic_chat.send(full_reply)
            audio_ratio = 0.5  # 文本和语音的发送比例（可调整）
            if random.random() < audio_ratio:
                audio = await get_sovits_audio(tts_text, ref_path=abs_refer_path)
                if audio: await mimic_chat.send(MessageSegment.record(f"base64://{audio}"))
                logger.info("同时发送了语音回复")
        elif reply_mode == 4:
            logger.info("🎯 触发回复表情包！")
            # 检测到用户发送表情包，根据识别结果生成回复文本
            if meaning:
                messages.append({"role": "user", "content": f"用户发送了一个表情包，识别结果是：{meaning}。请你用帕朵的口吻回复老板，保持语气和人设的一致性！"})
                response = await client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=messages,
                    temperature=0.95,          # 表情包回复可以更活泼一些
                    max_tokens=100,
                    frequency_penalty=0.5,
                    presence_penalty=0.7,
                    stop=["用户:", "User:"]
                )
                full_reply = response.choices[0].message.content.strip()
                await mimic_chat.send(full_reply)
            else:   
                logger.warning("表情包识别失败，无法生成针对性的回复")
    except FinishedException:
        pass
    except Exception:
        logger.exception("系统异常")
    await mimic_chat.finish()