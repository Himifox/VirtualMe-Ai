# C:\Users\xzq\Downloads\Save\047-Blender入门教程\07.合成篇附件\音效
import subprocess
import os

# ================= 配置区域 =================
# 指向你刚才解压的 ffmpeg.exe 路径
FFMPEG_PATH = r"C:\ffm\ffmpeg-8.0.1-essentials_build\bin\ffmpeg.exe"

# 随便找一个现有的音频文件进行测试
INPUT_FILE = r"C:\Users\xzq\Downloads\Save\047-Blender入门教程\07.合成篇附件\音效\夜晚森林篝火声音效.mp3"  # <--- 请修改为你电脑上真实存在的文件路径
OUTPUT_FILE = r"C:\test_output.silk"


# ===========================================

def test_ffmpeg():
    if not os.path.exists(FFMPEG_PATH):
        print(f"❌ 错误：在路径 {FFMPEG_PATH} 找不到 ffmpeg.exe")
        return

    print("🚀 正在尝试调用 FFmpeg 进行转码测试...")

    # 模拟 NapCat 调用 FFmpeg 的核心指令
    cmd = [
        FFMPEG_PATH,
        "-i", INPUT_FILE,
        "-f", "s16le",
        "-ar", "24000",
        "-ac", "1",
        "pipe:1"
    ]

    try:
        # 执行命令
        result = subprocess.run(cmd, capture_output=True, text=False)

        if result.returncode == 0:
            print("✅ FFmpeg 运行成功！它能够正常解析音频并输出数据。")
            print(f"📦 产生的输出数据长度: {len(result.stdout)} 字节")
        else:
            print("❌ FFmpeg 运行报错：")
            # 打印 FFmpeg 报错的原始信息
            print(result.stderr.decode('utf-8', errors='ignore'))

    except Exception as e:
        print(f"❌ 系统调用异常: {e}")


if __name__ == "__main__":
    test_ffmpeg()