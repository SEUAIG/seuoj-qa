"""
检索模块 - 检索层

负责触发词生成、思政内容检索和语义对齐重排序。
"""

from .keyword_extractor import KeywordExtractor
from .policy_fetcher import PolicyFetcher
from .reranker import SemanticReranker

__all__ = ["KeywordExtractor", "PolicyFetcher", "SemanticReranker"]
