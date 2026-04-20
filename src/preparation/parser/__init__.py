"""
解析模块 - 数据层

负责将教师上传的PPT、大纲、教材等资源解析为结构化的Markdown格式。
"""

from .mineru_parser import MinerUParser
from .document_splitter import DocumentSplitter

__all__ = ["MinerUParser", "DocumentSplitter"]
