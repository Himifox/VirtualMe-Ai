import random
import json
import aiofiles
from nonebot.adapters.onebot.v11 import Bot, MessageSegment, Event
from nonebot.log import logger
from .Sticker_recognize import load_collection

COLLECTION_JSON = "sticker_collection.json"
# 存储路径

async def find_md5_by_json(text: str) -> tuple | None:
    coll = await load_collection()

    for md5, item_data in coll.items():
        # --- 第一步：统一数据格式 ---
        if isinstance(item_data, dict):
            # 新格式：字典
            description = item_data.get("meaning", "")
            url = item_data.get("url")
        else:
            # 旧格式：字符串
            description = item_data
            url = None

        # --- 第二步：匹配关键词 ---
        if "关键词：" in description:
            keywords_part = description.split("关键词：")[-1]
            keywords_list = keywords_part.replace("。", "").split("、")

            for kw in keywords_list:
                kw = kw.strip()
                # 如果匹配到了关键词，并且我们有可用的 URL
                if kw and kw in text and url:
                    return md5, url

    return None


async def smart_send(bot: Bot, event: Event, ai_text: str, prob:float) -> bool:
    """
    智能发送逻辑：
    返回 True 表示已发送表情（拦截后续文本/语音）
    返回 False 表示未发送（继续执行原有逻辑）
    """
    # 1. 自动调用内部查找函数
    result = await find_md5_by_json(ai_text)

    if result:
        target_md5, target_url = result
        # 2. 概率判定
        if random.random() < prob:
            logger.info(f"🎯 命中！发送表情包 [MD5: {target_md5}]")
            # 3. 使用 URL 发送
            await bot.send(event, MessageSegment.image(file=target_url))
            return True  # 发送成功信号

    return False  # 未触发信号