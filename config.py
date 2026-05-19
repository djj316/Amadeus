"""
配置管理模块 - 负责读取/写入 JSON 配置文件
"""

import json
import os
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Union
from datetime import datetime


@dataclass
class TimeRange:
    """时间段配置"""
    start: str  # 格式: "HH:MM"
    end: str    # 格式: "HH:MM"

    def __post_init__(self):
        """验证时间格式"""
        try:
            datetime.strptime(self.start, "%H:%M")
            datetime.strptime(self.end, "%H:%M")
        except ValueError:
            raise ValueError(f"时间格式错误，应为 HH:MM，当前值: {self.start} - {self.end}")


@dataclass
class ContactConfig:
    """联系人配置数据类

    每个联系人可以有自己的个性化配置，覆盖全局默认行为。
    未设置的字段使用全局默认值。
    """
    name: str  # 微信联系人名称
    relation: str = ""  # 与对方的关系描述（如"男朋友"、"导师"），留空则使用默认语气

    # 个性化配置字典
    # 支持以下键（未设置的键使用全局默认行为）：
    #   silent_before : str  - 在此时间点之前保持静默（如"22:30"），空字符串=不限制
    #   custom_reply  : str  - 自定义回复内容（首次回复发完图片后发送此内容，不走 LLM）
    #   sticker_path  : str  - 该联系人专属表情包路径（覆盖全局 sticker_path）
    #   reply_message : str  - 该联系人专属预设消息（覆盖全局 reply_message）
    personalization: dict = field(default_factory=dict)

    def __post_init__(self):
        """确保 name 不为空"""
        if not self.name.strip():
            raise ValueError("联系人名称不能为空")
        # 验证 personalization 中的 silent_before 格式
        silent = self.personalization.get("silent_before", "")
        if silent:
            try:
                from datetime import datetime
                datetime.strptime(silent, "%H:%M")
            except ValueError:
                raise ValueError(
                    f"联系人 '{self.name}' 的 personalization.silent_before 时间格式错误，"
                    f"应为 HH:MM，当前值: {silent}"
                )


@dataclass
class LLMConfig:
    """大模型配置数据类"""
    enabled: bool = False  # 是否启用大模型回复
    provider: str = "doubao"  # 大模型提供商（doubao/openai/deepseek/qwen/moonshot/glm）
    api_endpoint: str = ""  # API 端点地址（留空则使用提供商默认端点）
    model: str = ""  # 模型名称（留空则使用提供商默认模型）
    max_tokens: int = 500  # 最大生成 token 数
    temperature: float = 0.8  # 温度参数（0-1）
    character: str = "kurisu"  # 角色名称
    enable_context: bool = True  # 是否启用对话上下文记忆
    context_window: int = 10  # 上下文记忆轮数


@dataclass
class Config:
    """程序配置数据类"""
    enabled: bool = True
    check_interval: float = 2.0  # 消息检测间隔（秒）
    contacts: List[ContactConfig] = field(default_factory=lambda: [ContactConfig(name="文件传输助手")])
    time_ranges: List[dict] = field(default_factory=lambda: [
        {"start": "09:00", "end": "12:00"},
        {"start": "13:00", "end": "18:00"},
    ])
    reply_message: str = (
        "您好，我现在正在忙，暂时无法回复消息。\n"
        "如有急事请电话联系我，谢谢！"
    )
    log_file: str = "reply_log.txt"
    llm: LLMConfig = field(default_factory=LLMConfig)  # 大模型配置
    sticker_path: str = ""  # 首次回复时发送的表情包/GIF 图片路径（空字符串表示不发送）


def get_default_config_path() -> str:
    """获取默认配置文件路径（与脚本同目录）"""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def _parse_contacts(contacts_data: list) -> List[ContactConfig]:
    """
    解析联系人配置，支持多种格式

    格式1（旧）: ["hane", "何璇"]
    格式2（旧）: [{"name": "hane", "relation": "朋友"}, ...]
    格式3（新）: [{"name": "何璇", "personalization": {"silent_before": "22:30", ...}}, ...]
    格式4（兼容）: [{"name": "何璇", "silent_before": "22:30", "custom_reply": "..."}, ...]

    Args:
        contacts_data: 原始联系人数据

    Returns:
        ContactConfig 列表
    """
    result = []
    for item in contacts_data:
        if isinstance(item, str):
            # 格式1：纯字符串
            result.append(ContactConfig(name=item, relation=""))
        elif isinstance(item, dict):
            name = item.get("name", "")
            relation = item.get("relation", "")

            # 收集 personalization 字典
            # 优先使用显式的 personalization 字段
            personalization = item.get("personalization", {})

            # 兼容旧格式：如果 silent_before/custom_reply 直接在联系人对象中，
            # 但不在 personalization 里，则迁移过去
            if "silent_before" in item and "silent_before" not in personalization:
                personalization["silent_before"] = item["silent_before"]
            if "custom_reply" in item and "custom_reply" not in personalization:
                personalization["custom_reply"] = item["custom_reply"]

            result.append(ContactConfig(
                name=name,
                relation=relation,
                personalization=personalization,
            ))
    return result


def load_config(config_path: Optional[str] = None) -> Config:
    """
    从 JSON 文件加载配置

    Args:
        config_path: 配置文件路径，None 则使用默认路径

    Returns:
        Config 对象
    """
    if config_path is None:
        config_path = get_default_config_path()

    if not os.path.exists(config_path):
        print(f"[配置] 配置文件不存在，使用默认配置: {config_path}")
        config = Config()
        save_config(config, config_path)
        return config

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 加载 LLM 配置
        llm_data = data.get("llm", {})
        llm_config = LLMConfig(
            enabled=llm_data.get("enabled", False),
            provider=llm_data.get("provider", "doubao"),
            api_endpoint=llm_data.get("api_endpoint", ""),
            model=llm_data.get("model", ""),
            max_tokens=llm_data.get("max_tokens", 500),
            temperature=llm_data.get("temperature", 0.8),
            character=llm_data.get("character", "kurisu"),
            enable_context=llm_data.get("enable_context", True),
            context_window=llm_data.get("context_window", 10),
        )

        # 解析联系人（兼容新旧格式）
        raw_contacts = data.get("contacts", ["文件传输助手"])
        contacts = _parse_contacts(raw_contacts)

        config = Config(
            enabled=data.get("enabled", True),
            check_interval=data.get("check_interval", 2.0),
            contacts=contacts,
            time_ranges=data.get("time_ranges", [
                {"start": "09:00", "end": "12:00"},
                {"start": "13:00", "end": "18:00"},
            ]),
            reply_message=data.get("reply_message", ""),
            log_file=data.get("log_file", "reply_log.txt"),
            llm=llm_config,
            sticker_path=data.get("sticker_path", ""),
        )
        print(f"[配置] 配置文件加载成功: {config_path}")
        return config

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        print(f"[配置] 配置文件解析失败 ({e})，使用默认配置")
        return Config()


def save_config(config: Config, config_path: Optional[str] = None) -> bool:
    """
    保存配置到 JSON 文件

    Args:
        config: Config 对象
        config_path: 配置文件路径，None 则使用默认路径

    Returns:
        是否保存成功
    """
    if config_path is None:
        config_path = get_default_config_path()

    try:
        data = asdict(config)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[配置] 配置已保存: {config_path}")
        return True
    except Exception as e:
        print(f"[配置] 配置保存失败: {e}")
        return False


def validate_config(config: Config) -> List[str]:
    """
    验证配置合法性

    Args:
        config: Config 对象

    Returns:
        错误信息列表，为空表示配置合法
    """
    errors = []

    if config.check_interval < 0.5:
        errors.append("检测间隔不能小于 0.5 秒")

    if not config.contacts:
        errors.append("联系人列表不能为空")
    else:
        for i, c in enumerate(config.contacts):
            if not c.name.strip():
                errors.append(f"联系人 {i+1}: 名称不能为空")

    if not config.reply_message.strip():
        errors.append("回复消息不能为空")

    for i, tr in enumerate(config.time_ranges):
        try:
            start = datetime.strptime(tr["start"], "%H:%M")
            end = datetime.strptime(tr["end"], "%H:%M")
            if start >= end:
                errors.append(f"时间段 {i+1}: 开始时间 {tr['start']} 必须早于结束时间 {tr['end']}")
        except (ValueError, KeyError) as e:
            errors.append(f"时间段 {i+1}: 时间格式错误 - {e}")

    # 验证 LLM 配置
    if config.llm.enabled:
        if config.llm.temperature < 0 or config.llm.temperature > 2:
            errors.append("LLM temperature 参数应在 0-2 之间")
        if config.llm.max_tokens < 50:
            errors.append("LLM max_tokens 不能小于 50")
        if config.llm.context_window < 1:
            errors.append("LLM context_window 不能小于 1")

        # 验证提供商
        from llm_client import get_provider_names
        valid_providers = get_provider_names()
        if config.llm.provider not in valid_providers:
            errors.append(
                f"LLM provider '{config.llm.provider}' 不支持，"
                f"可选: {', '.join(valid_providers)}"
            )

    return errors
