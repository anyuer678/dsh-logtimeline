"""环境变量读取，构造 LLMConfig。"""

from dataclasses import dataclass
from typing import Mapping


class ConfigError(ValueError):
    """配置缺失或非法。"""


@dataclass(frozen=True)
class LLMConfig:
    """OpenAI 兼容 API 连接配置。"""

    base_url: str
    api_key: str
    model: str
    timeout: int


def load_config_from_env(env: Mapping[str, str]) -> LLMConfig:
    """从 Mapping 读取 LLM_BASE_URL/LLM_API_KEY/LLM_MODEL，缺任一抛 ConfigError。"""
    required = ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL")
    missing = [key for key in required if not env.get(key)]
    if missing:
        raise ConfigError("缺少环境变量: " + ", ".join(missing))
    raw_timeout = env.get("LLM_TIMEOUT", "30")
    try:
        timeout = int(raw_timeout)
    except ValueError:
        raise ConfigError("LLM_TIMEOUT 必须为整数")
    if timeout <= 0:
        raise ConfigError("LLM_TIMEOUT 必须为正整数")
    return LLMConfig(
        base_url=env["LLM_BASE_URL"].rstrip("/"),
        api_key=env["LLM_API_KEY"],
        model=env["LLM_MODEL"],
        timeout=timeout,
    )
