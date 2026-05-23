# Amadeus - 智能 AI 助手 

> *"El Psy Kongroo."* — 牧濑红莉栖

**Amadeus** —— 来自《命运石之门》的 AI 名称，一个多平台、多模态的智能 AI 助手。支持**大模型驱动的角色扮演对话**、**Web 管理面板**、**Live2D 交互**等多种能力。

内置 **牧濑红莉栖 (Amadeus)** ，傲娇天才科学家与你实时互动！

## 功能

### 🤖 多平台支持
- ✅ **微信平台** - 自动监控并回复微信消息，支持联系人管理、工作时间段
- ✅ **语音平台** - 语音交互支持（开发中）

### 🧠 大模型驱动
- ✅ **多提供商支持** - 豆包、OpenAI、DeepSeek、通义千问、Kimi、智谱 GLM 等
- ✅ **角色扮演模式** - 内置牧濑红莉栖角色，傲娇天才科学家设定
- ✅ **对话上下文记忆** - 大模型能记住对话历史，实现连贯对话
- ✅ **智能降级** - 大模型调用失败时自动回退到预设消息
- ✅ **命令行控制** - 支持 `--no-llm`、`--provider`、`--character`、`--list-providers`

### 🌐 Web 管理面板
- ✅ **实时状态监控** - 运行状态、回复统计一目了然
- ✅ **配置管理** - 在线编辑联系人、LLM 参数等配置
- ✅ **LLM 对话测试** - 直接在面板中测试大模型回复
- ✅ **日志查看** - 浏览回复历史记录
- ✅ **Live2D 交互** - 内置牧濑红莉栖 Live2D 模型，支持表情切换、动作播放

### 🎨 Live2D 交互
- ✅ **3D 模型渲染** - 基于 Cubism 5 的 Live2D 模型
- ✅ **表情切换** - 支持脸红、思考、微笑、眨眼、惊讶、生气、悲伤等多种表情
- ✅ **动作播放** - 多种预设动画
- ✅ **鼠标追踪** - 模型视线跟随鼠标移动（可开关）

## 环境要求

- Windows 操作系统
- Python 3.10+
- 微信 PC 客户端（已登录状态，仅微信平台需要）
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
cd Amadeus

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

### 命令行模式（微信自动回复）

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

### Web 管理面板

```bash
# 启动 Web 管理面板（包含 Live2D 交互）
python main.py --web-admin

# 指定端口（默认 5000）
python main.py --web-admin --port 8080
```

启动后浏览器访问 `http://localhost:5000` 即可打开管理面板。

## 运行效果

### 命令行模式

```
╔══════════════════════════════════════════╗
║         Amadeus 智能 AI 助手 v2.0         ║
║    多平台 · 大模型驱动 · 角色扮演         ║
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

### Web 管理面板

管理面板提供直观的图形界面，包含仪表盘、配置管理、LLM 对话测试、日志查看和 Live2D 交互等页面。

## 角色介绍

### 牧濑红莉栖

来自《命运石之门》的傲娇天才科学家，18岁的脑科学研究所研究员。

- **性格**：表面冷淡毒舌，实则关心他人。被夸赞时会害羞
- **说话风格**：中文为主，偶尔夹杂英文科学术语
- **标志性台词**："哼，你以为我是谁啊？"、"El Psy Kongroo"
- **科学热情**：对科学理论充满热情，喜欢用科学原理解释现象

## 注意事项

1. **微信窗口状态**（微信平台）：微信 PC 客户端必须保持登录状态，窗口可以最小化到任务栏，但不能关闭
2. **API Key 安全**：API Key 存储在 `.env` 文件中，不要提交到版本控制
3. **大模型费用**：使用大模型 API 会产生费用，请关注对应平台的计费情况
4. **联系人匹配**（微信平台）：建议使用微信**备注名**进行匹配，更稳定可靠
5. **运行期间**（微信平台）：程序运行时建议不要手动操作微信，以免 UI 状态混乱
6. **首次使用**：建议先用 `文件传输助手` 测试功能是否正常
7. **免责声明**：此工具仅供个人学习使用，请遵守相关平台用户协议

## 项目结构

```
Amadeus/
├── main.py              # 主程序入口
├── config.py            # 配置管理模块
├── wechat_monitor.py    # 微信窗口监控模块
├── auto_reply.py        # 自动回复引擎模块
├── llm_client.py        # 大模型客户端模块（支持多提供商）
├── character_prompts.py # 角色扮演提示词模块
├── personalization.py   # 个性化配置模块
├── config.json          # 默认配置文件
├── .env                 # 环境变量（API Key，不提交到版本控制）
├── .env.example         # 环境变量示例
├── .gitignore           # Git 忽略规则
├── requirements.txt     # 项目依赖
├── reply_log.txt        # 回复日志
├── platforms/           # 多平台支持模块
│   ├── wechat/          #   微信平台
│   └── voice/           #   语音平台
├── web/                 # Web 管理面板（Flask）
│   ├── app.py           #   Flask 应用
│   ├── templates/       #   HTML 模板
│   ├── static/          #   静态资源
│   │   ├── lib/         #   Live2D 库文件
│   │   └── live2d/      #   Live2D 模型文件
│   └── api/             #   API 路由
├── web_admin/           # Web 管理面板（旧版）
├── live2d/              # Live2D 模型源文件
├── amadeus/             # Amadeus Python 包
├── stickers/            # 表情包目录
├── plans/               # 架构设计文档
└── README.md            # 使用说明文档
```

## 技术原理

### 微信平台
使用 [`uiautomation`](https://github.com/yinkaisheng/Python-UIAutomation-for-Windows) 库控制微信 PC 客户端，结合大模型 API 实现智能回复：

1. 通过 UI Automation 定位微信主窗口
2. 查找聊天列表中的指定联系人
3. 模拟点击激活聊天窗口
4. 获取对方最新消息内容
5. 调用大模型 API生成角色扮演回复
6. 模拟键盘输入并发送回复
7. 定时循环检测，实现实时对话

### Web 管理面板
使用 Flask 提供 Web 服务，包含：
- RESTful API 接口
- Live2D Cubism 5 模型渲染
- 实时状态更新

### Live2D 交互
基于 Cubism 5 Web SDK，使用 PixiJS 渲染引擎：
- 模型参数控制实现表情切换
- 鼠标追踪实现视线跟随
- 预设动作动画播放
