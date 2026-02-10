import nonebot
from nonebot.adapters.onebot.v11 import Adapter as OneBotV11Adapter
# ZHIPU_API ="14271215eb4e4a33a77ee2e2b81ffbb6.0e9UOV7rUBwUvVy6"

# 初始化 NoneBot
nonebot.init()

# 注册适配器 (连接 Lagrange)
driver = nonebot.get_driver()
driver.register_adapter(OneBotV11Adapter)

# 在这里加载插件
nonebot.load_plugins("plugins")


if __name__ == "__main__":
    # 避免占用默认 8080 端口，改为 8081
    nonebot.run(host="127.0.0.1", port=8081)
