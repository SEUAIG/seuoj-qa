"""
触发词/关键词提取器

使用 LLM 分析课件内容，提取用于检索思政相关内容的关键词。
"""

from typing import List
from camel.agents import ChatAgent

from ..config import get_llm_client


class KeywordExtractor:
    """关键词提取器"""

    def __init__(self, model=None):
        """
        初始化关键词提取器

        Args:
            model: LLM 模型实例
        """
        self.model = model or get_llm_client()
        self.agent = ChatAgent(
            system_message="你是一个专业的教育内容分析专家，擅长从教学材料中提取关键词。",
            model=self.model
        )

    def extract_keywords(self, content: str, top_k: int = 5) -> List[str]:
        """
        从课件内容中提取关键词

        Args:
            content: 课件内容
            top_k: 返回关键词数量

        Returns:
            关键词列表
        """
        prompt = f"""请分析以下教学课件内容，提取 {top_k} 个最核心的关键词。

这些关键词将用于检索相关的思政教育内容，因此请优先选择：
1. 与课程主题相关的核心概念
2. 可能与思政教育产生关联的价值观、伦理、社会热点等词汇

课件内容：
{content}

请直接返回关键词列表，用逗号分隔，不要有其他内容。"""

        response = self.agent.step(prompt)
        keywords = [k.strip() for k in response.msg.content.split(",")]
        return keywords[:top_k]

    def extract_with_context(self, title: str, content: str, top_k: int = 5) -> dict:
        """
        带上下文的关键词提取

        Args:
            title: 幻灯片标题
            content: 幻灯片内容
            top_k: 返回关键词数量

        Returns:
            包含关键词和检索上下文的字典
        """
        prompt = f"""请分析以下幻灯片内容，提取用于检索思政教育内容的关键词。

幻灯片标题：{title}
幻灯片内容：{content}

请返回：
1. 核心关键词（3-5个）
2. 检索上下文描述（一句话概括本页主题，用于后续语义对齐）

格式：
关键词：xxx, xxx, xxx
上下文：xxx"""

        response = self.agent.step(prompt)
        return self._parse_response(response.msg.content)

    def _parse_response(self, response: str) -> dict:
        """解析 LLM 响应"""
        lines = response.strip().split('\n')
        result = {"keywords": [], "context": ""}

        for line in lines:
            if line.startswith("关键词：") or line.startswith("关键词:"):
                keywords = line.split("：")[1].split(":")[-1].strip()
                result["keywords"] = [k.strip() for k in keywords.split(",")]
            elif line.startswith("上下文：") or line.startswith("上下文:"):
                result["context"] = line.split("：")[1].split(":")[-1].strip()

        return result
