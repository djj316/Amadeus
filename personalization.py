"""
个性化配置模块 - 按联系人定制回复行为

提供统一的接口来读取和判断联系人的个性化配置。
每个联系人可以通过 personalization 字典覆盖全局默认行为。

支持的个性化键：
    silent_before : str  - 在此时间点之前保持静默（如"22:30"），空字符串=不限制
    custom_reply  : str  - 自定义回复内容（首次回复发完图片后发送此内容，不走 LLM）
    sticker_path  : str  - 该联系人专属表情包路径（覆盖全局 sticker_path）
    reply_message : str  - 该联系人专属预设消息（覆盖全局 reply_message）

未来扩展：在此模块新增函数即可，无需修改其他文件。
"""

import datetime
from typing import Any, Optional

from config import Config, ContactConfig


# ============================================================
# 通用读取接口
# ============================================================

def get_personalization(contact_cfg: Optional[ContactConfig], key: str, default: Any = "") -> Any:
    """
    从联系人的 personalization 字典中获取个性化配置值

    优先级：联系人 personalization > 传入的 default 值

    Args:
        contact_cfg: ContactConfig 对象，为 None 时直接返回 default
        key: 配置键名（如 "silent_before", "custom_reply", "sticker_path", "reply_message"）
        default: 默认值（通常传入全局配置的对应字段）

    Returns:
        配置值
    """
    if contact_cfg is not None and hasattr(contact_cfg, 'personalization'):
        return contact_cfg.personalization.get(key, default)
    return default


# ============================================================
# 静默期判断
# ============================================================

def is_silent_now(contact_cfg: Optional[ContactConfig]) -> bool:
    """
    检查当前是否处于该联系人的静默期

    从 contact_cfg.personalization 中读取 silent_before 配置。
    如果配置了 silent_before（如"22:30"），且当前时间未达到该时间点，
    则返回 True（保持静默）。

    Args:
        contact_cfg: ContactConfig 对象

    Returns:
        是否应保持静默
    """
    silent_before = get_personalization(contact_cfg, "silent_before", "")
    if not silent_before:
        return False  # 未配置静默时间，不静默

    now = datetime.datetime.now()
    current_time = now.strftime("%H:%M")
    return current_time < silent_before


# ============================================================
# 自定义回复判断
# ============================================================

def get_custom_reply(contact_cfg: Optional[ContactConfig]) -> str:
    """
    获取联系人的自定义回复内容

    Args:
        contact_cfg: ContactConfig 对象

    Returns:
        自定义回复内容，未配置则返回空字符串
    """
    return get_personalization(contact_cfg, "custom_reply", "")


# ============================================================
# 表情包路径
# ============================================================

def get_sticker_path(contact_cfg: Optional[ContactConfig], global_sticker_path: str = "") -> str:
    """
    获取联系人的表情包路径

    优先级：联系人 personalization.sticker_path > 全局 sticker_path

    Args:
        contact_cfg: ContactConfig 对象
        global_sticker_path: 全局配置的 sticker_path

    Returns:
        表情包路径，未配置则返回空字符串
    """
    return get_personalization(contact_cfg, "sticker_path", global_sticker_path)


# ============================================================
# 预设消息
# ============================================================

def get_reply_message(contact_cfg: Optional[ContactConfig], global_reply_message: str = "") -> str:
    """
    获取联系人的预设消息

    优先级：联系人 personalization.reply_message > 全局 reply_message

    Args:
        contact_cfg: ContactConfig 对象
        global_reply_message: 全局配置的 reply_message

    Returns:
        预设消息内容
    """
    return get_personalization(contact_cfg, "reply_message", global_reply_message)


# ============================================================
# 批量获取所有个性化配置（用于调试/展示）
# ============================================================

def get_all_personalization(contact_cfg: Optional[ContactConfig]) -> dict:
    """
    获取联系人的所有个性化配置

    Args:
        contact_cfg: ContactConfig 对象

    Returns:
        个性化配置字典副本
    """
    if contact_cfg is not None and hasattr(contact_cfg, 'personalization'):
        return dict(contact_cfg.personalization)
    return {}


def format_personalization_summary(contact_cfg: Optional[ContactConfig]) -> str:
    """
    格式化显示联系人的个性化配置摘要

    Args:
        contact_cfg: ContactConfig 对象

    Returns:
        可读的配置摘要字符串
    """
    parts = []
    p = get_all_personalization(contact_cfg)

    silent = p.get("silent_before", "")
    if silent:
        parts.append(f"静默至 {silent}")

    custom = p.get("custom_reply", "")
    if custom:
        parts.append(f"自定义回复: {custom[:20]}...")

    sticker = p.get("sticker_path", "")
    if sticker:
        parts.append(f"专属表情包")

    msg = p.get("reply_message", "")
    if msg:
        parts.append(f"专属预设消息")

    return " | ".join(parts) if parts else "无个性化配置"
