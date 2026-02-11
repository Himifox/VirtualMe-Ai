import random
from pathlib import Path
import json
import os
import aiohttp
import hashlib
import aiofiles
from nonebot.adapters.onebot.v11 import Bot, MessageSegment, Event
from nonebot.log import logger
from .Sticker_recognize import load_collection

COLLECTION_JSON = "sticker_collection.json"
# 存储路径

import re
from nonebot.log import logger

async def find_md5_by_json(text: str) -> tuple | None:
    coll = await load_collection()
    
    # 【透视眼1】：看看真正传进来的文本长什么样
    logger.debug(f"🔍 正在尝试匹配表情，当前文本: {text}")

    for md5, item_data in coll.items():
        # --- 第一步：统一数据格式 ---
        if isinstance(item_data, dict):
            description = item_data.get("meaning", "")
            url = item_data.get("url")
        else:
            description = str(item_data)
            url = None

        # 如果连 url 都没有，强行发送也会报错，这里直接打印警告并跳过
        if not url:
            # logger.warning(f"⚠️ 发现没有 URL 的表情数据: {md5}，已跳过")
            continue

        # --- 第二步：兼容全角/半角冒号的正则匹配 ---
        # 无论写的是 "关键词:" 还是 "关键词：" 都能匹配到
        if "关键词" in description:
            # 使用正则切分，兼容全角和半角冒号，以及可能存在的空格
            parts = re.split(r'关键词[：:]\s*', description)
            if len(parts) > 1:
                keywords_part = parts[-1]
                # 兼容中文顿号和英文逗号的切分
                keywords_list = re.split(r'[、,，]', keywords_part.replace("。", ""))

                for kw in keywords_list:
                    kw = kw.strip()
                    if not kw: continue
                    
                    # 【透视眼2】：看看拆出来的关键词是什么
                    # logger.debug(f"尝试匹配关键词: [{kw}]")

                    if kw in text:
                        print(f"\n[Debug] 准备匹配表情，接收到的真实文本是: --->{text}<---")
                        logger.success(f"🎉 成功匹配到关键词: [{kw}] -> 准备发送表情!")
                        return md5, url

    logger.debug("❌ 循环结束，这段话里没有找到匹配的表情包关键词。")
    return None


async def smart_send(bot: Bot, event: Event, ai_text: str, prob: float) -> bool:
    """
        作用：根据 AI 生成的文本内容，智能判断是否发送表情包，并且发送对应的表情包图片。
        1. 调用 find_md5_by_json 来寻找是否有匹配的表情包   
        2. 如果找到了，就进行概率判定，决定是否发送表情包
        3. 如果决定发送，就构建本地图片的绝对路径，并检查文件是否存在
        4. 返回True，False

    """
    # 1. 先去寻找有没有匹配的表情包
    result = await find_md5_by_json(ai_text)
    
    # 2. 如果找到了 (result 不是 None)
    if result:
        # 在这里解包，target_md5 才正式诞生！
        target_md5, target_url = result
        
        # 3. 概率判定
        if random.random() < prob:
            logger.info(f"🎯 命中！准备发送表情包 [MD5: {target_md5}]")
            
            # 4. 构建本地文件的绝对路径 (必须放在 target_md5 诞生之后)
            local_img_path = Path(os.getcwd()) / "sticker_collection" / f"{target_md5}.png"
            
            # 5. 检查本地图片存不存在并发送
            if local_img_path.exists():
                await bot.send(event, MessageSegment.image(file=local_img_path.as_uri()))
                logger.success(f"✅ 成功发送本地表情包: {target_md5}.png")
                await bot.send(event, MessageSegment.text(ai_text))  # 可选：发送原始文本，帮助调试
                logger.debug(f"📌 发送的文本内容是: {ai_text}")
                return True  # 成功发送，拦截后续操作
            else:
                logger.error(f"❌ 找不到本地图片文件: {local_img_path}")
                # 如果本地没有图，返回 False，让机器人至少还能发语音
                return False 

    return False  # 如果没触发，返回 False 放行