"""
自动回复引擎模块 - 时间段判断、联系人匹配、发送回复

核心逻辑：
- 追踪每个联系人的最后一条消息内容
- 当检测到新消息时（消息内容变化），自动回复
- 支持大模型生成回复（角色扮演）和预设消息两种模式
- 对方每发一条消息，就回复一条
- 每次会话首次回复时发送指定表情包/GIF
- 支持按联系人关系个性化回复语气
- 个性化配置通过 personalization 模块统一管理
"""

import os
import time
import datetime
import subprocess
from typing import List, Dict, Optional, Set

import uiautomation as auto

from config import Config, ContactConfig
from llm_client import LLMClient
from personalization import (
    is_silent_now,
    get_custom_reply,
    get_sticker_path,
    get_reply_message,
)
from wechat_monitor import (
    find_wechat_window,
    activate_chat,
    get_chat_input_edit,
    get_active_chat_name,
    bring_window_to_front,
    get_last_message_text,
)


# 记录每个联系人最后一条消息的内容，用于检测新消息
# 格式: {contact_name: last_message_text}
_last_messages: Dict[str, str] = {}

# 记录每个联系人是否已在本次会话中发送过首次回复
# 格式: {contact_name: True/False}
_first_reply_sent: Set[str] = set()

# 记录每个联系人的 custom_reply 是否已在本次会话中执行过
# 用于：custom_reply 仅首次触发时执行一次，后续走正常 LLM 流程
_custom_reply_sent: Set[str] = set()

# 大模型客户端实例（由主程序初始化）
_llm_client: Optional[LLMClient] = None

# 当前活跃的联系人（锁定模式）
# 当检测到某个联系人发消息后，持续关注该联系人，直到其他联系人发消息才切换
# 避免多个联系人同时发消息时频繁切换窗口导致发送失败
_active_contact: Optional[str] = None


def _input_via_clipboard(edit, text: str):
    """
    通过剪贴板 + Ctrl+V 向输入框输入文本

    绕过 uiautomation 的 SendKeys 对 {} 等特殊字符的解析 bug。
    使用 PowerShell 设置剪贴板，文本通过 stdin 传递避免转义问题。

    Args:
        edit: 输入框控件
        text: 要输入的文本
    """
    try:
        # 使用 PowerShell 从 stdin 读取文本并设置到剪贴板
        ps = subprocess.Popen(
            ["powershell", "-NoProfile", "-Command",
             "$s=[Console]::In.ReadToEnd(); Set-Clipboard -Value $s"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True
        )
        ps.communicate(input=text, timeout=10)
        # Ctrl+V 粘贴
        edit.SendKeys("{Ctrl}v")
        time.sleep(0.1)
    except Exception:
        # 回退：逐字符 SendKeys（慢但安全）
        for char in text:
            if char in ('{', '}', '^', '%', '~', '+'):
                edit.SendKeys('{{}' + char + '{}}')
            else:
                edit.SendKeys(char)
            time.sleep(0.005)


def _send_sticker(wechat_window, sticker_path: str) -> bool:
    """
    通过剪贴板发送表情包/GIF 图片

    将图片文件复制到剪贴板，然后粘贴到微信输入框并发送。
    微信会自动将剪贴板中的图片识别为表情包/图片发送。

    Args:
        wechat_window: 微信主窗口控件
        sticker_path: 图片文件路径

    Returns:
        是否发送成功
    """
    try:
        if not os.path.isfile(sticker_path):
            print(f"[表情包] 文件不存在: {sticker_path}")
            return False

        # 确保微信窗口在前台并激活聊天
        if not bring_window_to_front(wechat_window):
            return False
        time.sleep(0.3)

        # 获取输入框
        edit = get_chat_input_edit(wechat_window)
        if not edit:
            print(f"[表情包] 无法获取聊天输入框")
            return False

        # 点击输入框获取焦点
        edit.Click()
        time.sleep(0.2)

        # 使用 PowerShell 将图片文件复制到剪贴板
        abs_path = os.path.abspath(sticker_path)
        ps = subprocess.Popen(
            ["powershell", "-NoProfile", "-Command",
             f"Add-Type -AssemblyName System.Windows.Forms; "
             f"$img = [System.Drawing.Image]::FromFile('{abs_path}'); "
             f"[System.Windows.Forms.Clipboard]::SetImage($img); "
             f"$img.Dispose()"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        _, err = ps.communicate(timeout=10)

        if ps.returncode != 0:
            # PowerShell 方式失败，回退到文件复制方式
            print(f"[表情包] PowerShell 设置剪贴板失败，尝试文件复制方式: {err.strip()}")
            ps2 = subprocess.Popen(
                ["powershell", "-NoProfile", "-Command",
                 f"Set-Clipboard -Path '{abs_path}'"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            ps2.communicate(timeout=10)

        time.sleep(0.3)

        # Ctrl+V 粘贴图片
        edit.SendKeys("{Ctrl}v")
        time.sleep(0.5)

        # 按 Enter 发送
        edit.SendKeys("{Enter}")
        time.sleep(0.5)

        print(f"[表情包] ✅ 已发送表情包: {sticker_path}")
        return True

    except Exception as e:
        import traceback
        print(f"[表情包] ❌ 发送表情包失败: {e}")
        print(f"[表情包]    详细错误: {traceback.format_exc()}")
        return False


def set_llm_client(client: Optional[LLMClient]):
    """
    设置大模型客户端实例

    Args:
        client: LLMClient 实例，None 表示不使用大模型
    """
    global _llm_client
    _llm_client = client


def is_in_time_range(time_ranges: List[dict]) -> bool:
    """
    判断当前时间是否在配置的时间段内

    Args:
        time_ranges: 时间段列表，格式 [{"start": "HH:MM", "end": "HH:MM"}, ...]

    Returns:
        是否在时间段内
    """
    if not time_ranges:
        return False

    now = datetime.datetime.now()
    current_time = now.strftime("%H:%M")

    for tr in time_ranges:
        try:
            start = tr["start"]
            end = tr["end"]
            if start <= current_time <= end:
                return True
        except (KeyError, TypeError):
            continue

    return False


def should_reply(contact_name: str, config: Config) -> bool:
    """
    判断是否应对指定联系人进行自动回复

    Args:
        contact_name: 联系人名称
        config: 配置对象

    Returns:
        是否应该回复
    """
    # 检查总开关
    if not config.enabled:
        return False

    # 检查是否在时间段内
    if not is_in_time_range(config.time_ranges):
        return False

    # 检查联系人是否在监控列表中（contacts 现在是 ContactConfig 列表）
    contact_names = [c.name for c in config.contacts]
    if contact_name not in contact_names:
        return False

    return True


def has_new_message(wechat_window, contact_name: str) -> bool:
    """
    检测指定联系人是否有新消息

    通过对比当前最后一条消息与之前记录的最后一条消息来判断。
    切换联系人后，会验证当前激活的聊天窗口确实是目标联系人，
    避免因 UI 切换延迟导致读到上一个联系人的消息（误发）。

    Args:
        wechat_window: 微信主窗口控件
        contact_name: 联系人名称

    Returns:
        是否有新消息
    """
    global _last_messages

    try:
        # 激活联系人聊天窗口以获取最新消息
        if not activate_chat(wechat_window, contact_name):
            return False

        time.sleep(0.3)

        # === 验证当前激活的聊天窗口确实是目标联系人 ===
        # 防止 UI 切换延迟导致读到上一个联系人的消息
        active_name = get_active_chat_name(wechat_window)
        if active_name is None:
            # 无法获取当前聊天名称，可能是 UI 尚未切换完成
            # 等待更长时间后重试一次
            print(f"[检测] 无法确认当前聊天窗口，等待后重试 [{contact_name}]...")
            time.sleep(0.5)
            active_name = get_active_chat_name(wechat_window)

        if active_name is not None and active_name != contact_name:
            # 当前激活的聊天窗口不是目标联系人 → UI 切换失败或延迟
            # 跳过本次检测，避免误读
            print(f"[检测] ⚠️ 当前聊天窗口为 [{active_name}]，"
                  f"非目标 [{contact_name}]，跳过本次检测")
            return False

        # 获取当前最后一条消息
        current_last = get_last_message_text(wechat_window)
        if current_last is None:
            return False

        # 获取之前记录的最后一条消息
        previous_last = _last_messages.get(contact_name)

        if previous_last is None:
            # 首次检测，记录当前消息但不触发回复
            _last_messages[contact_name] = current_last
            print(f"[检测] 首次记录 [{contact_name}] 的最后消息: {current_last[:30]}...")
            return False

        if current_last != previous_last:
            # 消息发生了变化，说明有新消息
            _last_messages[contact_name] = current_last
            print(f"[检测] 🔔 [{contact_name}] 发来新消息: {current_last[:30]}...")
            return True

        return False

    except Exception as e:
        print(f"[检测] 检测新消息失败 ({contact_name}): {e}")
        return False


def _generate_llm_reply(
    contact_name: str,
    user_message: str,
    contact_relation: str = "",
) -> Optional[str]:
    """
    使用大模型生成回复

    Args:
        contact_name: 联系人名称
        user_message: 用户发送的消息内容
        contact_relation: 与对方的关系描述（如"男朋友"），用于个性化回复

    Returns:
        生成的回复文本，失败返回 None
    """
    global _llm_client

    if _llm_client is None or not _llm_client.is_ready:
        return None

    relation_hint = f" (关系: {contact_relation})" if contact_relation else ""
    print(f"[LLM] 正在为 [{contact_name}]{relation_hint} 生成回复...")
    success, reply = _llm_client.chat(contact_name, user_message, contact_relation)

    if success:
        print(f"[LLM] ✅ 生成回复成功: {reply[:50]}...")
        return reply
    else:
        print(f"[LLM] ❌ 生成回复失败")
        return None


def send_reply(
    wechat_window,
    contact_name: str,
    message: str
) -> bool:
    """
    向指定联系人发送回复消息

    Args:
        wechat_window: 微信主窗口控件
        contact_name: 联系人名称
        message: 回复消息内容

    Returns:
        是否发送成功
    """
    global _last_messages

    try:
        # 将微信窗口置于前台
        if not bring_window_to_front(wechat_window):
            print(f"[回复] 无法将微信窗口置于前台")
            return False

        time.sleep(0.3)

        # 激活联系人聊天窗口
        if not activate_chat(wechat_window, contact_name):
            print(f"[回复] 无法激活联系人聊天窗口: {contact_name}")
            return False

        time.sleep(0.5)

        # 获取输入框
        edit = get_chat_input_edit(wechat_window)
        if not edit:
            print(f"[回复] 无法获取聊天输入框")
            return False

        # 点击输入框获取焦点
        edit.Click()
        time.sleep(0.2)

        # 清空输入框（全选 + 删除）
        edit.SendKeys("{Ctrl}a")
        time.sleep(0.1)
        edit.SendKeys("{Delete}")
        time.sleep(0.1)

        # 输入回复消息
        # 使用剪贴板 + Ctrl+V 方式输入，避免 uiautomation 的 SendKeys
        # 对 {} 等特殊字符的解析 bug（string index out of range）
        _input_via_clipboard(edit, message)

        time.sleep(0.2)

        # 按 Enter 发送
        edit.SendKeys("{Enter}")
        time.sleep(0.5)

        # 发送成功后，更新追踪记录为刚刚发送的消息内容
        # 这样下次检测时不会把刚发的回复当作新消息
        _last_messages[contact_name] = message
        print(f"[回复] ✅ 已向 [{contact_name}] 发送自动回复")
        return True

    except Exception as e:
        import traceback
        print(f"[回复] ❌ 发送回复失败 ({contact_name}): {e}")
        print(f"[回复]    详细错误: {traceback.format_exc()}")
        return False


def log_reply(contact_name: str, log_file: str, is_llm: bool = False):
    """
    记录回复日志

    Args:
        contact_name: 联系人名称
        log_file: 日志文件路径
        is_llm: 是否为大模型生成的回复
    """
    try:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        mode = "LLM" if is_llm else "预设"
        log_entry = f"[{now}] [{mode}] 已向 [{contact_name}] 发送自动回复\n"

        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception as e:
        print(f"[回复] 写入日志失败: {e}")


def process_auto_reply(config: Config) -> int:
    """
    执行一次自动回复检查和处理

    采用"活跃联系人锁定"策略：
    - 当检测到某个联系人发消息后，锁定该联系人为"活跃联系人"
    - 持续检测该联系人的新消息并回复（对方发一条回一条）
    - 直到其他联系人发消息，才切换到新联系人
    - 避免多个联系人同时发消息时频繁切换窗口导致发送失败或串话

    优先使用大模型生成回复，失败时降级到预设消息。
    每次会话中，对每个联系人的首次回复会先发送指定表情包/GIF。
    支持按联系人关系个性化回复语气。
    支持按联系人配置静默时间（silent_before）和自定义回复（custom_reply）。

    Args:
        config: 配置对象

    Returns:
        本次处理的回复数量
    """
    global _active_contact

    # 如果不在时间段内，跳过
    if not is_in_time_range(config.time_ranges):
        return 0

    # 查找微信窗口
    wechat_window = find_wechat_window()
    if not wechat_window:
        return 0

    reply_count = 0

    # ============================================================
    # 第一步：如果有活跃联系人，优先检测该联系人是否有新消息
    # ============================================================
    if _active_contact is not None:
        # 查找活跃联系人的配置
        active_cfg = None
        for c in config.contacts:
            if c.name == _active_contact:
                active_cfg = c
                break

        if active_cfg is not None:
            contact_name = active_cfg.name
            contact_relation = active_cfg.relation

            # 检查是否需要回复（时间段、静默期等）
            if (should_reply(contact_name, config)
                    and not is_silent_now(active_cfg)
                    and has_new_message(wechat_window, contact_name)):

                # 活跃联系人发来了新消息 → 回复它，保持锁定
                user_message = _last_messages.get(contact_name, "")
                _handle_contact_reply(
                    wechat_window, config, active_cfg,
                    contact_name, contact_relation, user_message
                )
                reply_count += 1
                return reply_count
            else:
                # 活跃联系人没有新消息 → 解锁，检查其他联系人
                _active_contact = None

    # ============================================================
    # 第二步：检测其他联系人是否有新消息
    # ============================================================
    for contact_cfg in config.contacts:
        contact_name = contact_cfg.name
        contact_relation = contact_cfg.relation

        # 跳过已经是活跃联系人的（上面已经检测过了）
        if _active_contact == contact_name:
            continue

        # 判断是否需要回复
        if not should_reply(contact_name, config):
            continue

        # === 静默期检查 ===
        if is_silent_now(contact_cfg):
            continue

        # 检测是否有新消息
        if has_new_message(wechat_window, contact_name):
            # 有其他联系人发消息 → 锁定该联系人为新的活跃联系人
            _active_contact = contact_name
            relation_info = f" (关系: {contact_relation})" if contact_relation else ""
            print(f"[回复] 🔒 锁定活跃联系人 [{contact_name}]{relation_info}")

            # 获取对方发送的消息内容
            user_message = _last_messages.get(contact_name, "")

            _handle_contact_reply(
                wechat_window, config, contact_cfg,
                contact_name, contact_relation, user_message
            )
            reply_count += 1
            # 找到第一个有消息的联系人就锁定并返回，不再继续遍历
            break

    return reply_count


def _handle_contact_reply(
    wechat_window,
    config: Config,
    contact_cfg,
    contact_name: str,
    contact_relation: str,
    user_message: str,
):
    """
    处理对指定联系人的回复（发送 sticker + 文字）

    个性化优先级：联系人 personalization > 全局配置 > 默认值
    个性化配置统一通过 personalization 模块读取。

    Args:
        wechat_window: 微信窗口控件
        config: 配置对象
        contact_cfg: 联系人配置
        contact_name: 联系人名称
        contact_relation: 与对方的关系
        user_message: 对方发送的消息内容
    """
    relation_info = f" (关系: {contact_relation})" if contact_relation else ""
    print(f"[回复] 检测到 [{contact_name}]{relation_info} 的新消息，准备回复")

    # === 首次回复：发送表情包/GIF ===
    # 优先使用联系人的个性化 sticker_path，没有则使用全局配置
    contact_sticker = get_sticker_path(contact_cfg, config.sticker_path)
    if (contact_sticker
            and contact_name not in _first_reply_sent):
        print(f"[回复] [{contact_name}] 首次回复，发送表情包...")
        _send_sticker(wechat_window, contact_sticker)
        _first_reply_sent.add(contact_name)
        time.sleep(0.5)

    # === 决定回复内容 ===
    # 优先使用联系人的个性化 reply_message，没有则使用全局配置
    reply_message = get_reply_message(contact_cfg, config.reply_message)
    is_llm_reply = False

    # 从 personalization 中读取 custom_reply
    custom_reply = get_custom_reply(contact_cfg)

    # 如果该联系人配置了 custom_reply 且尚未在本会话中执行过
    # 仅首次触发时执行一次（发固定语句，不走 LLM），后续走正常 LLM 流程
    if (custom_reply
            and contact_name not in _custom_reply_sent):
        reply_message = custom_reply
        _custom_reply_sent.add(contact_name)
        print(f"[回复] [{contact_name}] 使用自定义回复（仅首次，该轮次不调用 LLM）")
    # 否则走 LLM 生成
    elif config.llm.enabled and _llm_client and _llm_client.is_ready:
        llm_reply = _generate_llm_reply(
            contact_name, user_message, contact_relation
        )
        if llm_reply:
            reply_message = llm_reply
            is_llm_reply = True
        else:
            print(f"[回复] 大模型回复失败，降级到预设消息")

    # 发送回复
    success = send_reply(
        wechat_window,
        contact_name,
        reply_message
    )

    if success:
        log_reply(contact_name, config.log_file, is_llm=is_llm_reply)


def reset_tracking():
    """重置消息追踪记录（退出时间段时调用）"""
    global _last_messages, _first_reply_sent, _custom_reply_sent, _active_contact
    _last_messages.clear()
    _first_reply_sent.clear()
    _custom_reply_sent.clear()
    _active_contact = None
    # 同时重置 LLM 对话历史
    if _llm_client is not None:
        _llm_client.reset_conversation()
    print("[检测] 消息追踪记录和首次回复标记已重置")
