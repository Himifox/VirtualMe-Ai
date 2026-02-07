import json
import random
import os
import asyncio
import base64
import re
import edge_tts
from nonebot import on_message
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageSegment
from nonebot.exception import FinishedException
from openai import AsyncOpenAI

# ================= 配置区域 =================
API_KEY = "sk-061d4f46a02244f9acb9f51ee2c0a5dd"
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
MODEL_NAME = "qwen-plus"
HISTORY_FILE_PATH = "MSG/group_712851492_20260203_231902.json"
TARGET_UID = "u_MkWCKLdJG7Jubt9cQXbSpg"
# ===========================================

client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL)
mimic_chat = on_message(priority=99, block=False)


def load_target_history(filepath, target_uid):
    if not os.path.exists(filepath): return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            messages = [i.get("content", {}).get("text", "").strip() for i in data.get("messages", []) if
                        i.get("sender", {}).get("uid") == target_uid]
            return [m for m in list(set(messages)) if m and "[" not in m]
    except:
        return []


@mimic_chat.handle()
async def handle_chat(event: GroupMessageEvent):
    raw_msg = event.get_plaintext().strip()
    all_history = load_target_history(HISTORY_FILE_PATH, TARGET_UID)
    if not all_history: return

    style_samples = random.sample(all_history, min(len(all_history), 20))
    system_prompt = f"你是超级元气活泼的猫娘！说话带感叹号，多用语气助词。参考：{style_samples}"

    try:
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": raw_msg}],
            max_tokens=60
        )
        full_reply = response.choices[0].message.content.strip()

        # 1. 强化版正则过滤：移除所有括号（中英文、圆方括号）内的动作
        # 这里的正则包含了你的日志中出现的各种括号情况
        tts_text = re.sub(r'[\(\uff08\[\u3010].*?[\)\uff09\]\u3011]', '', full_reply)

        # 2. 语气微调：把长叹号替换为带有停顿感的感叹号
        tts_text = tts_text.replace("——", "，")
        if "喵" in tts_text:
            tts_text = tts_text.replace("喵", "，喵！")

        print(f"DEBUG: 原始文字: {full_reply}")
        print(f"DEBUG: 实际发音: {tts_text}")

        # 3. 情感参数随机化 (让声音更支棱)
        voice = "zh-CN-XiaoyiNeural"
        # 语速在 +18% 到 +25% 之间随机
        rate = f"+{random.randint(0, 10)}%"
        # 音调在 +10Hz 到 +20Hz 之间随机，制造一种“情绪激动”的起伏感
        pitch = f"+{random.randint(5, 30)}Hz"
        Volume = f"+{random.randint(10, 20)}%"

        audio_data = b""
        try:
            communicate = edge_tts.Communicate(tts_text, voice, rate=rate, pitch=pitch, volume=Volume)
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]
        except Exception as e:
            print(f"❌ TTS 异常: {e}")

        if audio_data:
            audio_b64 = base64.b64encode(audio_data).decode("utf-8")
            # 先发带有动作的文字回复，再发语音
            await mimic_chat.send(full_reply)
            await mimic_chat.send(MessageSegment.record(f"base64://{audio_b64}"))
        else:
            await mimic_chat.send(full_reply)

    except FinishedException:
        pass
    except Exception as e:
        print(f"❌ 系统异常: {e}")
    await mimic_chat.finish()