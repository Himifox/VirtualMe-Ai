import json
import logging
from enum import Enum
from typing import Tuple, List, Dict, Any, Optional

# --- 第一层：激活控制 (硬规则) ---
class ActionActivationType(Enum):
    NEVER = "never"      # 永不激活 (用于临时禁用)
    ALWAYS = "always"    # 始终激活 (核心功能)
    RANDOM = "random"    # 随机概率激活 (增加拟人感)
    KEYWORD = "keyword"  # 检测到特定关键词时激活

# --- 核心基类：BaseAction ---
class BaseAction:
    # 动作元数据 (用于给 LLM 生成 Prompt)
    action_name: str = "base_action"
    action_description: str = "动作描述"
    activation_type: ActionActivationType = ActionActivationType.ALWAYS
    
    # 决策属性 (帮助 LLM 判断何时用、怎么用)
    action_parameters: Dict[str, str] = {}  # 例如: {"keyword": "搜索词"}
    action_require: List[str] = []           # 例如: ["当气氛尴尬时使用"]
    
    # 运行配置
    random_activation_probability: float = 0.1  # 如果是 RANDOM 类型，概率是多少
    associated_types: List[str] = ["text"]       # 会产生什么类型的输出

    def __init__(self, bot_context: Dict[str, Any]):
        """
        初始化时绑定上下文，让 Action 知道‘我是谁，我在哪，面对谁’ 🧊
        """
        self.platform = bot_context.get("platform", "qq")
        self.user_id = bot_context.get("user_id", "")
        self.group_id = bot_context.get("group_id", "")
        self.is_group = bot_context.get("is_group", False)
        
        # 存储 LLM 传入的实际参数
        self.action_data: Dict[str, Any] = {} 
        # 管理员 QQ (建议从配置文件读取)
        self.admin_id = "123456789" 

    async def notify_admin(self, msg: str):
        """向管理员报告错误或重要状态 🚨"""
        print(f"[ADMIN NOTICE] {self.action_name}: {msg}")
        # 这里后续对接你 Adapter 的发送私聊功能

    def get_action_info_for_llm(self) -> Dict[str, Any]:
        """将 Action 转化为符合 OpenAI 工具调用的 JSON 格式 🧠"""
        return {
            "name": self.action_name,
            "description": f"{self.action_description}. 使用建议: {', '.join(self.action_require)}",
            "parameters": {
                "type": "object",
                "properties": {
                    k: {"type": "string", "description": v} 
                    for k, v in self.action_parameters.items()
                },
                "required": list(self.action_parameters.keys())
            }
        }

    async def execute(self) -> Tuple[bool, str]:
        """
        具体执行逻辑 (由子类重写) 🎯
        返回: (是否成功, 给 LLM 的反馈文字)
        """
        raise NotImplementedError("子类必须实现 execute 方法")

    async def run(self) -> str:
        """运行入口，包含报错处理和管理员通知 🛡️"""
        try:
            success, feedback = await self.execute()
            if not success:
                await self.notify_admin(f"执行失败: {feedback}")
            return feedback
        except Exception as e:
            err_msg = f"发生崩溃: {str(e)}"
            await self.notify_admin(err_msg)
            return f"动作执行出错: {err_msg}"