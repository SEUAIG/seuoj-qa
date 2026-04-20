"""
课程备课智能体配置管理

从项目配置文件加载 LLM 和其他配置。
"""

import yaml
import os
from pathlib import Path

# 获取项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "base.yaml"


def load_config(config_path: str = None) -> dict:
    """
    加载配置文件

    Args:
        config_path: 配置文件路径

    Returns:
        配置字典
    """
    path = Path(config_path) if config_path else CONFIG_PATH
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_llm_model(cfg: dict = None):
    """
    获取配置的 LLM 模型

    Args:
        cfg: 配置字典，如果不提供则从默认配置文件加载

    Returns:
        OpenAIModel 实例
    """
    from camel.models import OpenAIModel

    if cfg is None:
        cfg = load_config()

    # 获取当前使用的 LLM 配置
    llm_provider = cfg["llm"][cfg["llm"]["use"]]

    model_name = llm_provider["model"]
    api_key = llm_provider["api_key"]
    url = llm_provider["api_base"].rstrip("/")

    model_config = {
        "temperature": llm_provider.get("temperature"),
        "top_p": llm_provider.get("top_p"),
        "max_tokens": llm_provider.get("max_tokens")
    }
    model_config = {k: v for k, v in model_config.items() if v is not None}

    model = OpenAIModel(
        model_type=model_name,
        model_config_dict=model_config,
        api_key=api_key,
        url=url
    )
    return model


# 默认 LLM 模型单例
_llm_model = None


def get_llm_client():
    """获取 LLM 客户端单例"""
    global _llm_model
    if _llm_model is None:
        _llm_model = get_llm_model()
    return _llm_model


def get_data_dir(subdir: str = None) -> Path:
    """
    获取数据目录路径

    Args:
        subdir: 子目录名称

    Returns:
        数据目录路径
    """
    data_dir = PROJECT_ROOT / "data" / "preparation"
    if subdir:
        return data_dir / subdir
    return data_dir
