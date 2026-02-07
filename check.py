import os
import sys
import socket
import subprocess
import base64


def check_step(name, func):
    print(f"--- 正在检查: {name} ---")
    try:
        result = func()
        print(f"✅ {name} 通过! {result if result else ''}")
        return True
    except Exception as e:
        print(f"❌ {name} 失败: {e}")
        return False


# 1. 检查环境变量
def check_proxy():
    proxies = {k: v for k, v in os.environ.items() if "proxy" in k.lower()}
    if proxies:
        return f"发现残留代理: {proxies} (这可能是 DNS 报错的元凶！)"
    return "环境纯净，未发现代理。"


# 2. 检查必要的库
def check_modules():
    modules = ["openai", "httpx", "nonebot", "edge_tts"]
    missing = []
    for m in modules:
        try:
            __import__(m)
        except ImportError:
            missing.append(m)
    if missing:
        raise ImportError(f"缺少模块: {missing}。请执行: pip install {' '.join(missing)}")
    return "所有必要模块已就绪。"


# 3. 检查 DNS 解析 (核心痛点)
def check_dns():
    target = "dict.youdao.com"
    try:
        ip = socket.gethostbyname(target)
        return f"DNS 正常: {target} -> {ip}"
    except Exception:
        raise Exception(f"DNS 解析失败！你的系统无法识别 {target}，请检查网络或 hosts 文件。")


# 4. 检查 FFmpeg 物理存在
def check_ffmpeg():
    # 填入你 NapCat 目录下的 ffmpeg 路径
    ffmpeg_path = r"C:\Users\xzq\Documents\GitHub\Napcat\napcat\ffmpeg.exe"
    if os.path.exists(ffmpeg_path):
        res = subprocess.run([ffmpeg_path, "-version"], capture_output=True, text=True)
        return f"FFmpeg 已就绪: {res.stdout.splitlines()[0]}"
    else:
        raise FileNotFoundError(f"在 NapCat 目录没找到 ffmpeg.exe！路径: {ffmpeg_path}")


# 5. 检查端口占用
def check_port():
    port = 8080
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(('127.0.0.1', port)) == 0:
            raise Exception(f"端口 {port} 被占用！请在任务管理器杀掉之前的 Python 进程。")
    return f"端口 {port} 空闲。"


if __name__ == "__main__":
    print("=== 猫娘环境体检工具喵 ===")
    results = [
        check_step("代理环境变量", check_proxy),
        check_step("Python 模块", check_modules),
        check_step("网络 DNS 解析", check_dns),
        check_step("FFmpeg 物理路径", check_ffmpeg),
        check_step("8080 端口占用", check_port)
    ]

    if all(results):
        print("\n🎉 奇迹发生了！所有检查项都通过了，现在重启机器人应该必成喵！")
    else:
        print("\n⚠️ 还是有坑，请根据上面的红叉 ❌ 提示进行修复喵。")