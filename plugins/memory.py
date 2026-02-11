from nonebot import on_message
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from collections import deque, defaultdict

# 1. 创建全局记忆库
# key是群号，value是一个最大长度为20的队列
# 当新的消息进来，旧的消息会自动挤出去
_history_cache = defaultdict(lambda: deque(maxlen=20))

# 2. 监听所有群消息（优先级设为1，保证最先运行）
record_msg = on_message(priority=1, block=False)


@record_msg.handle()
async def _(event: GroupMessageEvent):
    group_id = event.group_id
    # 获取发送者昵称
    sender_name = event.sender.card or event.sender.nickname or "未知用户"
    
    # 遍历消息段，手动拼接完整内容
    content_parts = []
    
    for seg in event.message:
        if seg.type == "text":
            # 纯文本直接拼接
            content_parts.append(seg.data.get("text", ""))
            
        elif seg.type == "image":
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
            
        elif seg.type == "at":
            # 记录被艾特的人
            at_qq = seg.data.get("qq", "")
            content_parts.append(f"[@{at_qq}]")

    # 将各部分拼接成完整的字符串
    content = "".join(content_parts).strip()
    
    # 如果内容不为空，就存起来
    if content:
        # 格式示例: "张三: 大家好 [图片: http...]"
        entry = f"{sender_name}: {content}"
        _history_cache[group_id].append(entry)
        # print(f"已记录群 {group_id} 消息: {entry}") # 调试用

# --- 对外提供的功能函数 ---

def get_history_str(group_id: int) -> str:
    """
    获取指定群的历史记录字符串，用于喂给 AI
    """
    if group_id not in _history_cache:
        return "群聊历史记录为空。"
    # 把队列里的消息用换行符拼起来
    return "\n".join(_history_cache[group_id])

def save_bot_reply(group_id: int, content: str):
    """
    手动保存机器人自己回复的内容
    (因为机器人自己发的消息不会触发 on_message，所以需要手动存)
    """
    if content:
        entry = f"我的发言: {content}"
        _history_cache[group_id].append(entry)