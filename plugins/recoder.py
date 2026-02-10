import json
from nonebot import on_message
from nonebot.adapters.onebot.v11 import GroupMessageEvent

# 定义监听器
message_listener = on_message(priority=1, block=False)


@message_listener.handle()
async def record_message(event: GroupMessageEvent):
    # 1. 提取基础信息
    user_id = event.user_id
    group_id = event.group_id
    raw_time = event.time


    # 2. 提取内容和昵称
    content = event.get_plaintext()
    nickname = event.sender.card or event.sender.nickname

    # 3. 构建数据对象
    msg_data = {
        "content": content,
        "meta": {
            "sender": nickname,
            "user_id": user_id,
            "timestamp": raw_time,
            "group_id": group_id
        }
    }

    # 4. 【新加的部分】写入文件 (使用 'a' 模式)
    # ensure_ascii=False 是为了让它正确显示中文，而不是乱码
    with open("chat_data.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(msg_data, ensure_ascii=False) + "\n")
    import os
    print(f"✅ 成功写入！文件路径在: {os.path.abspath('chat_data.jsonl')}")
    print(f"已记录: {content}")