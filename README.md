# 微信自控回复助手 v2.0

对微信的特定聊天对象，在特定时间段内自动回复。支持**多提供商大模型驱动的角色扮演回复**和预设消息两种模式。

内置 **牧濑红莉栖**角色扮演，傲娇天才科学家为你自动回复消息！

## 功能

### v2.0 新增功能
- ✅ **多提供商大模型支持** - 支持豆包、OpenAI、DeepSeek、通义千问、Kimi、智谱 GLM 等
- ✅ **角色扮演模式** - 内置牧濑红莉栖（命运石之门）角色，支持傲娇天才科学家设定
- ✅ **对话上下文记忆** - 大模型能记住对话历史，实现连贯对话
- ✅ **智能降级** - 大模型调用失败时自动回退到预设消息
- ✅ **命令行控制** - 支持 `--no-llm`、`--provider`、`--character`、`--list-providers`

### 原有功能
- ✅ 指定监控联系人列表（支持备注名/昵称）
- ✅ 设置工作时间段，仅在指定时间段内启用自动回复
- ✅ 自定义回复消息内容（作为大模型不可用时的降级方案）
- ✅ **实时对话模式** - 对方每发一条消息，程序自动回复一条
- ✅ 消息追踪机制 - 通过对比消息内容变化检测新消息
- ✅ 回复日志记录
- ✅ 支持 Ctrl+C 优雅退出

## 环境要求

- Windows 操作系统
- Python 3.10+
- 微信 PC 客户端（已登录状态）
- 任一支持的 LLM 提供商的 API Key

## 支持的 LLM 提供商

| 提供商 | 配置名称 | 默认模型 | 获取 API Key |
|--------|----------|----------|-------------|
| 豆包（火山引擎） | `doubao` | `doubao-pro-32k` | [火山引擎控制台](https://console.volcengine.com/ark) |
| OpenAI | `openai` | `gpt-4o-mini` | [OpenAI API Keys](https://platform.openai.com/api-keys) |
| DeepSeek | `deepseek` | `deepseek-chat` | [DeepSeek 平台](https://platform.deepseek.com/api_keys) |
| 通义千问（阿里云） | `qwen` | `qwen-plus` | [阿里云模型服务](https://help.aliyun.com/zh/model-studio/) |
| 月之暗面（Kimi） | `moonshot` | `moonshot-v1-8k` | [Moonshot 控制台](https://platform.moonshot.cn/console/api-keys) |
| 智谱（GLM） | `glm` | `glm-4-flash` | [智谱开放平台](https://open.bigmodel.cn/usercenter/apikeys) |

> 任何兼容 OpenAI 接口的 API 都可以通过配置 `api_endpoint` 和 `model` 来使用。

## 安装

```bash
# 1. 进入项目目录
cd examples/wechat_auto_reply

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置 API Key
#    复制 .env.example 为 .env，然后编辑 .env 填入你的 API Key
copy .env.example .env
#    然后用文本编辑器打开 .env，将对应提供商的 API Key 填入

# 4. 配置联系人等个性化信息
#    复制 config.example.json 为 config.json，然后编辑
copy config.example.json config.json
```

## 配置

> ⚠️ **隐私保护**：`config.json` 已加入 `.gitignore`，不会上传到 GitHub。
> 请复制 [`config.example.json`](config.example.json) 为 `config.json`，然后编辑你的个性化配置。

编辑 [`config.json`](config.json) 文件（基于 [`config.example.json`](config.example.json)）：

```json
{
  "enabled": true,
  "check_interval": 2.0,
  "contacts": [
    {
      "name": "联系人A",
      "relation": "朋友"
    },
    {
      "name": "联系人B",
      "relation": ""
    }
  ],
  "time_ranges": [
    { "start": "09:00", "end": "12:00" },
    { "start": "13:00", "end": "18:00" }
  ],
  "reply_message": "您好，我现在正在忙，暂时无法回复消息。\n如有急事请电话联系我，谢谢！",
  "log_file": "reply_log.txt",
  "sticker_path": "stickers/your_sticker.gif",
  "llm": {
    "enabled": true,
    "provider": "doubao",
    "api_endpoint": "",
    "model": "",
    "max_tokens": 500,
    "temperature": 0.8,
    "character": "kurisu",
    "enable_context": true,
    "context_window": 10
  }
}
```

### 配置项说明

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `enabled` | 总开关 | `true` |
| `check_interval` | 检测间隔（秒） | `2.0` |
| `contacts` | 需要监控的联系人列表，每个对象包含 `name`（微信备注名）和 `relation`（关系描述，可选） | `[{"name": "文件传输助手", "relation": ""}]` |
| `time_ranges` | 启用自动回复的时间段 | `09:00-12:00, 13:00-18:00` |
| `reply_message` | 预设回复消息（大模型不可用时的降级方案） | 见上 |
| `log_file` | 回复日志文件路径 | `reply_log.txt` |
| `sticker_path` | 首次回复时发送的表情包/GIF 图片路径（空字符串禁用） | `""` |

### LLM 配置项说明

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `llm.enabled` | 是否启用大模型回复 | `false` |
| `llm.provider` | 大模型提供商（见上方支持列表） | `doubao` |
| `llm.api_endpoint` | API 端点地址（留空使用提供商默认） | `""` |
| `llm.model` | 模型名称（留空使用提供商默认） | `""` |
| `llm.max_tokens` | 最大生成 token 数 | `500` |
| `llm.temperature` | 温度参数（0-1，越高越随机） | `0.8` |
| `llm.character` | 角色名称（当前仅支持 `kurisu`） | `kurisu` |

### 联系人个性化配置

你可以为每个联系人设置 `relation`（关系描述），让 LLM 在保持 Kurisu 性格的基础上，根据对象关系微调语气：

```json
"contacts": [
    {"name": "小明", "relation": "男朋友"},
    {"name": "张老师", "relation": "导师"},
    {"name": "李四", "relation": ""}
]
```

- `relation` 留空则使用默认语气
- 支持任意关系描述，LLM 会自动适配
- 整体性格始终是 Kurisu，不会 OOC
| `llm.enable_context` | 是否启用对话上下文记忆 | `true` |
| `llm.context_window` | 上下文记忆轮数 | `10` |

### 切换提供商示例

**使用 DeepSeek：**

```json
{
  "llm": {
    "enabled": true,
    "provider": "deepseek",
    "model": "deepseek-chat"
  }
}
```

对应的 `.env` 文件：
```env
DEEPSEEK_API_KEY=sk-your_deepseek_api_key_here
```

**使用 OpenAI：**

```json
{
  "llm": {
    "enabled": true,
    "provider": "openai",
    "model": "gpt-4o-mini"
  }
}
```

对应的 `.env` 文件：
```env
OPENAI_API_KEY=sk-your_openai_api_key_here
```

### 环境变量配置

创建 `.env` 文件（基于 [`.env.example`](.env.example)），根据你使用的提供商设置对应的 API Key：

```env
# 只设置你使用的那个提供商的 Key 即可
DOUBAO_API_KEY=your_doubao_api_key_here
# OPENAI_API_KEY=sk-...
# DEEPSEEK_API_KEY=sk-...
# QWEN_API_KEY=sk-...
# MOONSHOT_API_KEY=sk-...
# GLM_API_KEY=...
```

## 使用

```bash
# 1. 确保微信 PC 客户端已登录并打开

# 2. 使用默认配置启动（启用大模型回复）
python main.py

# 3. 禁用大模型回复，使用预设消息
python main.py --no-llm

# 4. 使用自定义配置文件
python main.py --config my_config.json

# 5. 覆盖检测间隔
python main.py --interval 3.0

# 6. 切换提供商（覆盖配置文件）
python main.py --provider deepseek

# 7. 列出所有支持的提供商
python main.py --list-providers

# 8. 按 Ctrl+C 停止程序
```

## 运行效果

程序启动后，会在终端显示运行状态：

```
╔══════════════════════════════════════════╗
║       微信自控回复助手 v2.0               ║
║    大模型驱动 · 角色扮演 · 智能回复       ║
╚══════════════════════════════════════════╝

[主程序] 配置文件: config.json
[主程序] 监控联系人: 联系人A
[主程序] 工作时间段: 09:00-12:00  13:00-18:00
[主程序] 回复模式: 大模型(LLM)
[主程序] LLM 提供商: 豆包（火山引擎）(doubao)
[主程序] 检测间隔: 2.0 秒
[主程序] 日志文件: reply_log.txt

[主程序] 🤖 正在初始化大模型...
[LLM] ✅ 大模型客户端初始化完成
[LLM]    提供商: 豆包（火山引擎）
[LLM]    模型: doubao-pro-32k
[LLM]    端点: https://ark.cn-beijing.volces.com/api/v3
[LLM]    角色: kurisu
[LLM]    上下文: 启用

[主程序] 正在检查微信客户端...
[主程序] ✅ 微信客户端已检测到

[主程序] 🟢 开始运行... (按 Ctrl+C 停止)

[2026-05-18 16:40:00] 🟢 在时间段内 | 已检查: 5 次 | 已回复: 0 次 | 联系人: 1 个 | 间隔: 2.0s | 🟢 豆包（火山引擎）: doubao-pro-32k | 角色: kurisu
```

## 角色介绍

### 牧濑红莉栖（Makise Kurisu）

来自《命运石之门》的傲娇天才科学家，18岁的脑科学研究所研究员。

- **性格**：表面冷淡毒舌，实则关心他人。被夸赞时会害羞
- **说话风格**：中文为主，偶尔夹杂英文科学术语
- **标志性台词**："哼，你以为我是谁啊？"、"El Psy Kongroo"
- **科学热情**：对科学理论充满热情，喜欢用科学原理解释现象

## 注意事项

1. **微信窗口状态**：微信 PC 客户端必须保持登录状态，窗口可以最小化到任务栏，但不能关闭
2. **API Key 安全**：API Key 存储在 `.env` 文件中，不要提交到版本控制
3. **大模型费用**：使用大模型 API 会产生费用，请关注对应平台的计费情况
4. **联系人匹配**：建议使用微信**备注名**进行匹配，更稳定可靠
5. **运行期间**：程序运行时建议不要手动操作微信，以免 UI 状态混乱
6. **首次使用**：建议先用 `文件传输助手` 测试功能是否正常
7. **免责声明**：此工具仅供个人学习使用，请遵守微信用户协议

## 项目结构

```
wechat_auto_reply/
├── main.py              # 主程序入口
├── config.py            # 配置管理模块
├── wechat_monitor.py    # 微信窗口监控模块
├── auto_reply.py        # 自动回复引擎模块
├── llm_client.py        # 大模型客户端模块（支持多提供商）
├── character_prompts.py # 角色扮演提示词模块
├── config.json          # 默认配置文件
├── .env                 # 环境变量（API Key，不提交到版本控制）
├── .env.example         # 环境变量示例
├── .gitignore           # Git 忽略规则
├── requirements.txt     # 项目依赖
├── reply_log.txt        # 回复日志
└── README.md            # 使用说明文档
```

## 技术原理

使用 [`uiautomation`](https://github.com/yinkaisheng/Python-UIAutomation-for-Windows) 库控制微信 PC 客户端，结合大模型 API 实现智能回复：

1. 通过 UI Automation 定位微信主窗口
2. 查找聊天列表中的指定联系人
3. 模拟点击激活聊天窗口
4. 获取对方最新消息内容
5. 调用大模型 API（支持多提供商）生成角色扮演回复
6. 模拟键盘输入并发送回复
7. 定时循环检测，实现实时对话
