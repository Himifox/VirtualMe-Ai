<div align="center">

# NekoPardo

一个基于 NoneBot + OneBot V11 的 QQ 角色陪伴机器人。

以帕朵菲莉丝为当前角色核心，支持群聊互动、表情识别、云端 TTS、本地长期记忆、向量召回、主动聊天、用量遥测与成本护栏。

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![NoneBot](https://img.shields.io/badge/NoneBot-2.x-EB6EA5?style=flat-square)
![OneBot](https://img.shields.io/badge/OneBot-V11-4B5563?style=flat-square)
![Status](https://img.shields.io/badge/status-in%20progress-0F766E?style=flat-square)

</div>

---

## 项目定位

NekoPardo 不是通用问答 bot，而是一个“带角色人格、记忆和成本控制”的陪伴型聊天机器人。当前主链路以 QQ 群聊为中心：

```text
OneBot V11 事件
  -> NoneBot
  -> 群聊触发 / @ / 表情包识别
  -> 角色 prompt + 短期历史 + 可选长期记忆召回
  -> 大模型回复
  -> 文本 / TTS 语音 / 表情包发送
  -> 记忆落盘 + 用量遥测 + 预算护栏
```

## 当前功能

| 模块 | 状态 | 说明 |
| --- | --- | --- |
| QQ 群聊接入 | 可用 | 基于 NoneBot 和 OneBot V11，入口为 `bot.py` |
| 角色回复 | 可用 | 当前角色为帕朵菲莉丝，主聊天逻辑在 `plugins/pardo_chat.py` |
| 表情识别 | 可用 | 使用 Qwen-VL 识别图片/表情包后生成角色化回复 |
| TTS 语音 | 可用 | 支持豆包、DashScope，GPT-SoVITS 可作为 fallback |
| TTS 遥测 | 可用 | 记录 provider、成功/失败、字符数、估算费用、耗时 |
| 短期记忆 | 可用 | 维护群聊最近上下文 |
| 长期记忆 | 可用 | 以 JSONL 保存聊天记忆，默认 `chat_data.jsonl` |
| 向量记忆 | 默认关闭 | 可构建本地 JSONL 向量索引，并按当前问题召回 topK |
| 主动聊天 | 默认关闭 | 群聊静默一段时间后可主动破冰 |
| Token 遥测 | 可用 | 记录聊天模型和 embedding 的 token 消耗 |
| 成本护栏 | 可用 | 支持聊天、embedding、TTS、主动聊天的每日预算限制 |

## 目录结构

```text
.
├── bot.py                       # NoneBot 启动入口
├── .env.example                 # 环境变量模板，不包含真实密钥
├── chat_data.jsonl              # 长期记忆文件，运行时数据
├── plugins/
│   ├── pardo_chat.py            # 主聊天插件、管理员命令、回复链路
│   ├── proactive_monitor.py     # 主动聊天监控
│   ├── config.py                # 唯一配置入口
│   ├── tts.py                   # 云端 TTS + GSV fallback + TTS 遥测
│   ├── memory.py                # 短期记忆监听
│   ├── memory_store.py          # 长期记忆 JSONL 存储
│   ├── vector_memory.py         # 向量索引构建与召回
│   ├── usage_telemetry.py       # 模型/embedding token 遥测
│   ├── budget_guard.py          # 每日预算护栏
│   ├── proactive_usage.py       # 主动聊天每日计数
│   ├── pardo.py                 # 基础角色插件
│   ├── sticker_service.py       # 表情包识别、学习与发送辅助
│   ├── recorder.py              # 长期记忆写入兼容 helper
│   └── README.md                # 插件命名与职责说明
├── ref_audio/                   # GPT-SoVITS 参考音频
├── sticker_collection/          # 表情包素材
└── data/                        # 运行时索引、遥测文件目录
```

## 快速启动

### 1. 准备 Python 环境

项目未固定依赖文件。当前代码至少需要：

```powershell
pip install nonebot2 nonebot-adapter-onebot openai httpx websockets
```

如果你已经使用项目内 `.venv`，可以直接激活：

```powershell
.\.venv\Scripts\Activate.ps1
```

### 2. 配置环境变量

复制模板并填写真实值：

```powershell
Copy-Item .env.example .env
```

项目不会自动加载 `.env`，需要由你的运行环境、启动脚本或进程管理器注入环境变量。

最低配置建议：

```env
DASHSCOPE_API_KEY=
QWEN_VL_API_KEY=
BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MODEL_NAME=qwen-plus
ADMIN_UID=
STARTUP_GROUP_ID=
```

### 3. 启动 OneBot 实现

先启动你的 OneBot V11 实现，例如 Lagrange，并确保它能连接到 NoneBot。

### 4. 启动机器人

```powershell
python bot.py
```

默认监听：

```text
127.0.0.1:8081
```

## 配置说明

### 大模型

| 变量 | 说明 |
| --- | --- |
| `DASHSCOPE_API_KEY` | 主聊天模型 API Key |
| `BASE_URL` | OpenAI-compatible API Base URL |
| `MODEL_NAME` | 主聊天模型名 |
| `QWEN_VL_API_KEY` | 表情/图片识别模型 API Key |

### 表情包

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `STICKER_COLLECTION_ENABLED` | `true` | 是否自动收藏群聊图片/表情包 |
| `STICKER_COLLECTION_ACTIVE_GROUPS_ONLY` | `true` | 只在已启用机器人群里收藏，避免误收私聊或无关群 |
| `STICKER_RECOGNIZE_EXISTING` | `false` | 已收藏表情是否重新调用 Qwen-VL 识别 |
| `STICKER_SEND_LOCAL_FIRST` | `true` | 发送表情时优先使用本地缓存图片 |

### TTS

| 变量 | 说明 |
| --- | --- |
| `TTS_PROVIDER` | `auto`、`doubao`、`dashscope`、`gsv` |
| `TTS_FALLBACK_PROVIDER` | 主 provider 失败后的备用 provider |
| `TTS_FALLBACK_ENABLED` | 是否启用 fallback |
| `DOUBAO_TTS_API_KEY` | 豆包 TTS API Key |
| `DOUBAO_TTS_VOICE` | 豆包音色 |
| `DASHSCOPE_TTS_API_KEY` | DashScope TTS API Key，默认可复用 `DASHSCOPE_API_KEY` |
| `DASHSCOPE_TTS_VOICE` | DashScope 音色 |
| `SOVITS_API_URL` | GPT-SoVITS 本地接口 |

### 长期记忆与向量召回

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `LONG_TERM_MEMORY_FILE` | `chat_data.jsonl` | 长期记忆 JSONL 文件 |
| `VECTOR_MEMORY_ENABLED` | `false` | 是否在聊天 prompt 中启用向量召回 |
| `EMBEDDING_API_KEY` | 复用主 API Key | embedding API Key |
| `EMBEDDING_MODEL` | `text-embedding-v4` | embedding 模型 |
| `VECTOR_MEMORY_FILE` | `data/vector_memory.jsonl` | 本地向量索引文件 |
| `VECTOR_MEMORY_TOP_K` | `5` | 召回条数 |
| `VECTOR_MEMORY_MAX_CHARS` | `600` | 写入 prompt 的长期记忆总长度上限 |
| `VECTOR_MEMORY_AUTO_INDEX_ENABLED` | `false` | 是否自动低频增量索引 |

### 成本与预算

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `USAGE_TELEMETRY_FILE` | `data/model_usage.jsonl` | 模型 token 用量日志 |
| `TTS_TELEMETRY_FILE` | `data/tts_usage.jsonl` | TTS 用量日志 |
| `CHAT_INPUT_PRICE_PER_1K_TOKENS` | `0.0` | 聊天输入 token 单价 |
| `CHAT_OUTPUT_PRICE_PER_1K_TOKENS` | `0.0` | 聊天输出 token 单价 |
| `EMBEDDING_PRICE_PER_1K_TOKENS` | `0.0` | embedding token 单价 |
| `DAILY_CHAT_TOKEN_LIMIT` | `0` | 每日聊天 token 上限，0 表示不限 |
| `DAILY_EMBEDDING_TOKEN_LIMIT` | `0` | 每日 embedding token 上限，0 表示不限 |
| `DAILY_TTS_CHAR_LIMIT` | `0` | 每日 TTS 字符上限，0 表示不限 |
| `PROACTIVE_DAILY_LIMIT` | `5` | 每日主动聊天次数上限 |

## 管理员命令

以下命令仅建议由 `ADMIN_UID` 使用：

| 命令 | 说明 |
| --- | --- |
| `#Neko` | 在当前群启用机器人 |
| `#tts统计` / `#tts用量` | 查看 TTS 今日用量 |
| `#语音统计` / `#语音花费` | 查看 TTS 今日用量 |
| `#模型用量` / `#token统计` | 查看模型与 embedding token 用量 |
| `#预算统计` | 查看今日预算、剩余额度和估算花费 |
| `#记忆统计` | 查看长期记忆与向量索引状态 |
| `#构建记忆索引` | 手动增量构建向量记忆索引 |

## 运行时数据

以下文件是运行时数据，不建议提交：

```text
chat_data.jsonl
data/tts_usage.jsonl
data/model_usage.jsonl
data/vector_memory.jsonl
```

当前 `.gitignore` 已忽略 `data/*.jsonl` 中的遥测和索引文件。`chat_data.jsonl` 是长期记忆数据，提交前请确认是否包含私人聊天内容。

## 默认启动插件

`bot.py` 目前显式加载：

```python
nonebot.load_plugin("plugins.pardo")
nonebot.load_plugin("plugins.pardo_chat")
nonebot.load_plugin("plugins.proactive_monitor")
```

没有使用 `nonebot.load_plugins("plugins")` 扫描整个目录，避免把半成品或实验模块意外接入线上流程。

## 验证

推荐在提交前运行：

```powershell
$files = Get-ChildItem -Recurse -Filter *.py | Where-Object { $_.FullName -notmatch '\\.venv\\' }
foreach ($file in $files) {
    .\.venv\Scripts\python.exe -m py_compile $file.FullName
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
```

也可以做插件导入检查：

```powershell
$env:PROACTIVE_CHAT_ENABLED='false'
.\.venv\Scripts\python.exe -c "import nonebot; nonebot.init(); import plugins.pardo_chat; import plugins.proactive_monitor; print('ok')"
```

## 维护建议

- 先保持 `VECTOR_MEMORY_ENABLED=false`，等索引质量稳定后再打开。
- 主动聊天建议继续默认关闭，确认成本和群聊体验后再启用。
- 真实密钥只放运行环境，不写入源码。
- 提交前关注 `chat_data.jsonl` 和 `test*` 文件，避免把私人数据或临时测试文件误提交。

## License

见 [LICENSE](LICENSE)。
