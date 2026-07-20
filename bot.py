import nonebot
from nonebot.adapters.onebot.v11 import Adapter as OneBotV11Adapter

# 初始化 NoneBot
nonebot.init()

# 注册适配器 (连接 Lagrange)
driver = nonebot.get_driver()
driver.register_adapter(OneBotV11Adapter)

# 显式加载已接入插件，避免把其他半成品模块一起加载。
# nonebot.load_plugins("plugins")
nonebot.load_plugin("plugins.pardo")
nonebot.load_plugin("plugins.GPT_SoVITS")
nonebot.load_plugin("plugins.Monitor")

if __name__ == "__main__":
    # 避免占用默认 8080 端口，改为 8081
    nonebot.run(host="127.0.0.1", port=8081)
