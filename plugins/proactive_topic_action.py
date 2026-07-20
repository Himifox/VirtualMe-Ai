import random
import json
from .action_base import BaseAction, ActionActivationType
from typing import Tuple

class ProactiveTopicAction(BaseAction):
    action_name = "proactive_topic"
    action_description = "主播主动破冰。当直播间冷场时，主动发送文字并配上可爱的表情包。"
    
    # 决策属性：让 LLM 决定话题
    action_require = [
        "观众很久没说话了，主播觉得无聊想找人聊天",
        "主播想分享一个刚看到的八卦或者有趣的事情",
        "单纯想卖个萌，吸引观众的注意力"
    ]
    
    action_parameters = {
        "content": "具体的开场白文字，要符合可爱主播的人设",
        "emotion_keyword": "想要配上的表情包关键词，例如：调皮、开心、求关注、委屈"
    }

    async def execute(self) -> Tuple[bool, str]:
        # 1. 获取 LLM 生成的内容
        content = self.action_data.get("content", "诶？没人理我吗？( > < )")
        keyword = self.action_data.get("emotion_keyword", "调皮")
        
        # 2. 发送第一弹：主播的开场白文字
        # 加上一点主播特有的装饰符号
        decorated_text = f"✨【直播间公告】✨\n{content}"
        await self.send_text(decorated_text)
        
        # 3. 连招第二弹：强行联动表情包逻辑
        # 假设你的 JSON 数据存储在 plugins/emotions.json
        try:
            with open("plugins/emotions.json", "r", encoding="utf-8") as f:
                emotions_data = json.load(f)
            
            # 搜索匹配的表情包
            matched_urls = []
            for info in emotions_data.values():
                if keyword in info.get("meaning", ""):
                    matched_urls.append(info.get("url"))
            
            if matched_urls:
                # 随机抽一张符合氛围的发出去，避免重复
                final_url = random.choice(matched_urls)
                await self.send_image(final_url)
                feedback = f"成功开启话题并发送了‘{keyword}’表情包"
            else:
                feedback = f"开启了话题，但没找到‘{keyword}’的表情包"
                
        except Exception as e:
            feedback = f"话题开启成功，但表情包库读取失败: {str(e)}"
            await self.notify_admin(feedback)

        return True, feedback
