"""
大模型客户端模块 - 支持多提供商 API 调用

支持以下大模型提供商（OpenAI 兼容接口）：
- 豆包（火山引擎）- doubao
- OpenAI - openai
- DeepSeek - deepseek
- 通义千问（阿里云）- qwen
- 月之暗面（Moonshot / Kimi）- moonshot
- 智谱（GLM）- glm
- 任何兼容 OpenAI 接口的 API

管理对话上下文历史，实现角色扮演自动回复。
"""

import os
import json
import time
from typing import List, Dict, Optional, Tuple

from openai import OpenAI
from openai import APIError, RateLimitError, APITimeoutError

from character_prompts import get_character_prompt


# ============================================================
# 提供商配置映射
# ============================================================

PROVIDER_CONFIGS = {
    "doubao": {
        "name": "豆包（火山引擎）",
        "default_endpoint": "https://ark.cn-beijing.volces.com/api/v3",
        "default_model": "doubao-pro-32k",
        "env_key": "DOUBAO_API_KEY",
        "env_endpoint": "DOUBAO_API_ENDPOINT",
        "doc_url": "https://console.volcengine.com/ark",
    },
    "openai": {
        "name": "OpenAI",
        "default_endpoint": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "env_key": "OPENAI_API_KEY",
        "env_endpoint": "OPENAI_API_ENDPOINT",
        "doc_url": "https://platform.openai.com/api-keys",
    },
    "deepseek": {
        "name": "DeepSeek",
        "default_endpoint": "https://api.deepseek.com",
        "default_model": "deepseek-chat",
        "env_key": "DEEPSEEK_API_KEY",
        "env_endpoint": "DEEPSEEK_API_ENDPOINT",
        "doc_url": "https://platform.deepseek.com/api_keys",
    },
    "qwen": {
        "name": "通义千问（阿里云）",
        "default_endpoint": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model": "qwen-plus",
        "env_key": "QWEN_API_KEY",
        "env_endpoint": "QWEN_API_ENDPOINT",
        "doc_url": "https://help.aliyun.com/zh/model-studio/",
    },
    "moonshot": {
        "name": "月之暗面（Kimi）",
        "default_endpoint": "https://api.moonshot.cn/v1",
        "default_model": "moonshot-v1-8k",
        "env_key": "MOONSHOT_API_KEY",
        "env_endpoint": "MOONSHOT_API_ENDPOINT",
        "doc_url": "https://platform.moonshot.cn/console/api-keys",
    },
    "glm": {
        "name": "智谱（GLM）",
        "default_endpoint": "https://open.bigmodel.cn/api/paas/v4",
        "default_model": "glm-4-flash",
        "env_key": "GLM_API_KEY",
        "env_endpoint": "GLM_API_ENDPOINT",
        "doc_url": "https://open.bigmodel.cn/usercenter/apikeys",
    },
}

DEFAULT_PROVIDER = "doubao"
DEFAULT_MAX_TOKENS = 500
DEFAULT_TEMPERATURE = 0.8
DEFAULT_CONTEXT_WINDOW = 10  # 保留最近 N 轮对话


def get_provider_names() -> List[str]:
    """获取所有支持的提供商名称列表"""
    return list(PROVIDER_CONFIGS.keys())


def get_provider_display_name(provider: str) -> str:
    """获取提供商的显示名称"""
    config = PROVIDER_CONFIGS.get(provider)
    return config["name"] if config else provider


class LLMClient:
    """
    大模型客户端

    支持多提供商，管理 API 调用和对话上下文，支持多联系人独立对话历史。
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_endpoint: Optional[str] = None,
        provider: str = DEFAULT_PROVIDER,
        model: Optional[str] = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
        character: str = "kurisu",
        enable_context: bool = True,
        context_window: int = DEFAULT_CONTEXT_WINDOW,
    ):
        """
        初始化 LLM 客户端

        Args:
            api_key: API Key，None 则根据 provider 从对应环境变量读取
            api_endpoint: API 端点地址，None 则使用 provider 默认端点
            provider: 大模型提供商名称（doubao/openai/deepseek/qwen/moonshot/glm）
            model: 模型名称，None 则使用 provider 默认模型
            max_tokens: 最大生成 token 数
            temperature: 温度参数（0-1）
            character: 角色名称
            enable_context: 是否启用对话上下文记忆
            context_window: 上下文记忆轮数
        """
        self.provider = provider
        provider_cfg = PROVIDER_CONFIGS.get(provider)

        if not provider_cfg:
            print(f"[LLM] ⚠️ 未知提供商 '{provider}'，使用默认提供商 '{DEFAULT_PROVIDER}'")
            self.provider = DEFAULT_PROVIDER
            provider_cfg = PROVIDER_CONFIGS[DEFAULT_PROVIDER]

        # 获取 API Key：优先使用传入值，否则从对应环境变量读取
        self.api_key = api_key or os.getenv(provider_cfg["env_key"])
        if not self.api_key:
            print(f"[LLM] ⚠️ 未设置 {provider_cfg['name']} 的 API Key")
            print(f"[LLM]    请通过参数传入或在 .env 中设置 {provider_cfg['env_key']}=your_key_here")
            print(f"[LLM]    获取地址: {provider_cfg['doc_url']}")

        # API 配置
        self.api_endpoint = (
            api_endpoint
            or os.getenv(provider_cfg["env_endpoint"])
            or provider_cfg["default_endpoint"]
        )
        self.model = model or provider_cfg["default_model"]
        self.max_tokens = max_tokens
        self.temperature = temperature

        # 角色配置
        self.character = character
        self.system_prompt = get_character_prompt(character)

        # 上下文配置
        self.enable_context = enable_context
        self.context_window = context_window

        # 对话历史: {contact_name: [{"role": "user"/"assistant", "content": "..."}]}
        self._conversations: Dict[str, List[Dict[str, str]]] = {}

        # 初始化 OpenAI 客户端
        self._client = None
        if self.api_key:
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.api_endpoint,
            )
            print(f"[LLM] ✅ 大模型客户端初始化完成")
            print(f"[LLM]    提供商: {provider_cfg['name']}")
            print(f"[LLM]    模型: {self.model}")
            print(f"[LLM]    端点: {self.api_endpoint}")
            print(f"[LLM]    角色: {self.character}")
            print(f"[LLM]    上下文: {'启用' if self.enable_context else '禁用'}")

    @property
    def is_ready(self) -> bool:
        """客户端是否就绪（API Key 已配置）"""
        return self._client is not None

    def chat(
        self,
        contact_name: str,
        user_message: str,
        contact_relation: str = "",
    ) -> Tuple[bool, str]:
        """
        发送消息并获取大模型回复

        Args:
            contact_name: 联系人名称（用于区分对话上下文）
            user_message: 用户发送的消息内容
            contact_relation: 与对方的关系描述（如"男朋友"），用于个性化回复

        Returns:
            (是否成功, 回复文本)
        """
        if not self.is_ready:
            return False, ""

        try:
            # 构建消息列表
            messages = self._build_messages(contact_name, user_message, contact_relation)

            # 调用 API
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )

            # 提取回复内容
            reply_text = response.choices[0].message.content.strip()
            if not reply_text:
                return False, ""

            # 更新对话历史
            if self.enable_context:
                self._update_conversation(contact_name, user_message, reply_text)

            return True, reply_text

        except RateLimitError as e:
            print(f"[LLM] ⚠️ API 速率限制: {e}")
            return False, ""
        except APITimeoutError:
            print(f"[LLM] ⚠️ API 请求超时")
            return False, ""
        except APIError as e:
            print(f"[LLM] ⚠️ API 错误: {e}")
            return False, ""
        except Exception as e:
            print(f"[LLM] ⚠️ 未知错误: {e}")
            return False, ""

    def _build_messages(
        self,
        contact_name: str,
        user_message: str,
        contact_relation: str = "",
    ) -> List[Dict[str, str]]:
        """
        构建发送给 API 的消息列表

        包含系统提示词、当前时间信息、联系人关系描述、对话历史和当前用户消息。

        Args:
            contact_name: 联系人名称
            user_message: 用户消息
            contact_relation: 与对方的关系描述（如"男朋友"），用于个性化回复

        Returns:
            消息列表
        """
        from datetime import datetime

        messages = [{"role": "system", "content": self.system_prompt}]

        # 添加当前时间信息，让 LLM 根据时间调整回复风格
        now = datetime.now()
        time_info = f"[当前时间: {now.strftime('%Y-%m-%d %H:%M')}]"
        messages.append({"role": "system", "content": time_info})

        # 添加联系人关系描述，让 LLM 根据对象关系调整语气
        if contact_relation:
            relation_info = (
                f"[对话对象: {contact_name}，对方是你的{contact_relation}。"
                f"请在保持你性格特点的前提下，根据与对方的关系适当调整语气。"
                f"对方是{contact_relation}，所以可以更{'亲切' if '男' in contact_relation or '女' in contact_relation else '亲近'}一些。]"
            )
            messages.append({"role": "system", "content": relation_info})

        # 添加上下文历史
        if self.enable_context and contact_name in self._conversations:
            history = self._conversations[contact_name]
            # 只取最近 context_window 轮对话
            recent_history = history[-(self.context_window * 2):]
            messages.extend(recent_history)

        # 添加当前用户消息
        messages.append({"role": "user", "content": user_message})

        return messages

    def _update_conversation(
        self,
        contact_name: str,
        user_message: str,
        reply_text: str,
    ):
        """
        更新对话历史

        Args:
            contact_name: 联系人名称
            user_message: 用户消息
            reply_text: 助手回复
        """
        if contact_name not in self._conversations:
            self._conversations[contact_name] = []

        self._conversations[contact_name].append({
            "role": "user",
            "content": user_message,
        })
        self._conversations[contact_name].append({
            "role": "assistant",
            "content": reply_text,
        })

        # 限制上下文窗口大小
        max_history = self.context_window * 2  # user + assistant 为一轮
        if len(self._conversations[contact_name]) > max_history:
            self._conversations[contact_name] = \
                self._conversations[contact_name][-max_history:]

    def reset_conversation(self, contact_name: Optional[str] = None):
        """
        重置对话历史

        Args:
            contact_name: 联系人名称，None 则重置所有对话
        """
        if contact_name:
            self._conversations.pop(contact_name, None)
            print(f"[LLM] 已重置 [{contact_name}] 的对话历史")
        else:
            self._conversations.clear()
            print(f"[LLM] 已重置所有对话历史")

    def get_conversation_length(self, contact_name: str) -> int:
        """
        获取指定联系人的对话历史长度（轮数）

        Args:
            contact_name: 联系人名称

        Returns:
            对话轮数
        """
        if contact_name not in self._conversations:
            return 0
        return len(self._conversations[contact_name]) // 2

    def get_status_string(self) -> str:
        """
        获取客户端状态字符串（用于主程序状态显示）

        Returns:
            状态描述
        """
        if not self.is_ready:
            return "🔴 LLM: 未配置"
        provider_name = get_provider_display_name(self.provider)
        return f"🟢 {provider_name}: {self.model} | 角色: {self.character}"
