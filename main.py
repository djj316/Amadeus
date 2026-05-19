"""
微信自控回复助手 v2.0 - 主程序入口

对微信的特定聊天对象，在特定时间段内自动回复。
支持多提供商大模型驱动的角色扮演回复和预设消息两种模式。

支持的 LLM 提供商:
  - doubao   : 豆包（火山引擎）
  - openai   : OpenAI（GPT 系列）
  - deepseek : DeepSeek
  - qwen     : 通义千问（阿里云）
  - moonshot : 月之暗面（Kimi）
  - glm      : 智谱（GLM）

使用说明:
    python main.py              # 使用默认配置启动
    python main.py --config my_config.json  # 使用自定义配置
    python main.py --no-llm     # 禁用大模型回复，使用预设消息
    python main.py --provider deepseek  # 切换提供商
"""

import sys
import io
import os
import time
import signal
import argparse
from datetime import datetime
from typing import Optional

# 解决 Windows 终端 GBK 编码问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 加载 .env 文件（如果存在）
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from config import load_config, validate_config, Config
from auto_reply import process_auto_reply, reset_tracking, set_llm_client
from llm_client import LLMClient
from wechat_monitor import find_wechat_window


# 全局运行标志
_running = True

# 全局 LLM 客户端
_llm_client: Optional[LLMClient] = None


def signal_handler(signum, frame):
    """信号处理函数 - 优雅退出"""
    global _running
    print("\n[主程序] 收到停止信号，正在退出...")
    _running = False


def print_banner():
    """打印程序启动横幅"""
    banner = """
╔══════════════════════════════════════════╗
║       微信自控回复助手 v2.0               ║
║    大模型驱动 · 角色扮演 · 智能回复       ║
╚══════════════════════════════════════════╝
"""
    print(banner)


def print_status(config: Config, reply_count: int, total_checks: int):
    """
    打印运行状态

    Args:
        config: 配置对象
        reply_count: 已回复次数
        total_checks: 总检查次数
    """
    global _llm_client

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    in_time = "🟢 在时间段内" if _is_in_time_range_now(config) else "🔴 不在时间段内"
    llm_status = _llm_client.get_status_string() if _llm_client else "🔴 LLM: 未启用"

    print(f"\r[{now}] {in_time} | "
          f"已检查: {total_checks} 次 | "
          f"已回复: {reply_count} 次 | "
          f"联系人: {len(config.contacts)} 个 | "
          f"间隔: {config.check_interval}s | "
          f"{llm_status}",
          end="", flush=True)


def _is_in_time_range_now(config: Config) -> bool:
    """检查当前是否在配置的时间段内（内部辅助函数）"""
    from auto_reply import is_in_time_range
    return is_in_time_range(config.time_ranges)


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="微信自控回复助手 v2.0 - 大模型驱动智能回复"
    )
    parser.add_argument(
        "--config", "-c",
        type=str,
        default=None,
        help="配置文件路径（默认: 同目录下的 config.json）"
    )
    parser.add_argument(
        "--interval", "-i",
        type=float,
        default=None,
        help="消息检测间隔（秒，覆盖配置文件中的设置）"
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="禁用大模型回复，使用预设消息"
    )
    parser.add_argument(
        "--provider", "-p",
        type=str,
        default=None,
        help="大模型提供商（覆盖配置文件，如 doubao/openai/deepseek/qwen/moonshot/glm）"
    )
    parser.add_argument(
        "--character", "-ch",
        type=str,
        default=None,
        help="角色名称（覆盖配置文件中的设置，如 kurisu）"
    )
    parser.add_argument(
        "--list-providers",
        action="store_true",
        help="列出所有支持的 LLM 提供商"
    )
    return parser.parse_args()


def init_llm_client(config: Config, args) -> Optional[LLMClient]:
    """
    初始化大模型客户端

    根据配置的 provider 自动读取对应的环境变量中的 API Key。

    Args:
        config: 配置对象
        args: 命令行参数

    Returns:
        LLMClient 实例，未启用则返回 None
    """
    # 命令行参数 --no-llm 覆盖配置
    if args.no_llm:
        print("[主程序] 已通过命令行参数禁用大模型回复")
        return None

    if not config.llm.enabled:
        print("[主程序] 大模型回复未启用（可在 config.json 中设置 llm.enabled=true）")
        return None

    # 命令行参数覆盖提供商和角色
    provider = args.provider or config.llm.provider
    character = args.character or config.llm.character

    # API Key 由 LLMClient 内部根据 provider 自动从对应环境变量读取
    # 不需要在这里手动获取

    print()
    print("[主程序] 🤖 正在初始化大模型...")
    client = LLMClient(
        provider=provider,
        api_endpoint=config.llm.api_endpoint or None,
        model=config.llm.model or None,
        max_tokens=config.llm.max_tokens,
        temperature=config.llm.temperature,
        character=character,
        enable_context=config.llm.enable_context,
        context_window=config.llm.context_window,
    )

    if not client.is_ready:
        print("[主程序] ❌ 大模型初始化失败，将使用预设消息")
        return None

    return client


def main():
    """主函数"""
    global _running, _llm_client

    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 打印横幅
    print_banner()

    # 解析命令行参数
    args = parse_args()

    # --list-providers 参数：列出所有支持的提供商
    if args.list_providers:
        from llm_client import get_provider_names, get_provider_display_name, PROVIDER_CONFIGS
        print("[主程序] 📋 支持的 LLM 提供商:")
        print()
        for name in get_provider_names():
            cfg = PROVIDER_CONFIGS[name]
            print(f"  {name:12s} - {cfg['name']}")
            print(f"              默认模型: {cfg['default_model']}")
            print(f"              环境变量: {cfg['env_key']}")
            print(f"              文档地址: {cfg['doc_url']}")
            print()
        return

    # 加载配置
    config = load_config(args.config)

    # 命令行参数覆盖配置
    if args.interval is not None and args.interval > 0:
        config.check_interval = args.interval
    if args.provider is not None:
        config.llm.provider = args.provider

    # 验证配置
    errors = validate_config(config)
    if errors:
        print("[主程序] ❌ 配置验证失败:")
        for err in errors:
            print(f"  - {err}")
        print("[主程序] 请修改配置文件后重试")
        sys.exit(1)

    # 打印配置信息
    print(f"[主程序] 配置文件: {args.config or 'config.json'}")
    contact_display = []
    for c in config.contacts:
        if c.relation:
            contact_display.append(f"{c.name}({c.relation})")
        else:
            contact_display.append(c.name)
    print(f"[主程序] 监控联系人: {', '.join(contact_display)}")
    print(f"[主程序] 工作时间段: ", end="")
    for tr in config.time_ranges:
        print(f"{tr['start']}-{tr['end']}  ", end="")
    print()
    print(f"[主程序] 回复模式: {'大模型(LLM)' if config.llm.enabled else '预设消息'}")
    if config.llm.enabled:
        from llm_client import get_provider_display_name
        print(f"[主程序] LLM 提供商: {get_provider_display_name(config.llm.provider)} ({config.llm.provider})")
    print(f"[主程序] 检测间隔: {config.check_interval} 秒")
    print(f"[主程序] 日志文件: {config.log_file}")
    print()

    # 初始化大模型客户端
    _llm_client = init_llm_client(config, args)
    set_llm_client(_llm_client)
    print()

    # 检查微信是否运行
    print("[主程序] 正在检查微信客户端...")
    wechat_window = find_wechat_window()
    if not wechat_window:
        print("[主程序] ⚠️ 未检测到微信窗口，请确保微信已登录并打开")
        print("[主程序] 程序将继续运行，等待微信启动...")
    else:
        print("[主程序] ✅ 微信客户端已检测到")

    print()
    print("[主程序] 🟢 开始运行... (按 Ctrl+C 停止)")
    print()

    # 运行统计
    reply_count = 0
    total_checks = 0
    last_status_time = 0

    # 主循环
    while _running:
        try:
            # 执行自动回复检查
            count = process_auto_reply(config)
            reply_count += count
            total_checks += 1

            # 每秒更新一次状态显示
            current_time = time.time()
            if current_time - last_status_time >= 1.0:
                print_status(config, reply_count, total_checks)
                last_status_time = current_time

            # 等待指定间隔
            time.sleep(config.check_interval)

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"\n[主程序] ⚠️ 运行异常: {e}")
            time.sleep(5)  # 异常时等待 5 秒后重试
            continue

    # 退出统计
    print("\n")
    print("═" * 50)
    print("[主程序] 📊 运行统计")
    print(f"  总检查次数: {total_checks}")
    print(f"  总回复次数: {reply_count}")
    contact_display = []
    for c in config.contacts:
        if c.relation:
            contact_display.append(f"{c.name}({c.relation})")
        else:
            contact_display.append(c.name)
    print(f"  监控联系人: {', '.join(contact_display)}")
    if _llm_client:
        print(f"  大模型状态: {_llm_client.get_status_string()}")
    print("[主程序] 👋 已退出")


if __name__ == "__main__":
    main()
