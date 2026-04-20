"""
Marp 模块 - Marp 生成与转换

负责生成符合 Marp 语法的 Markdown，并将其转换为 PPT/PDF。
"""

from .marp_generator import MarpGenerator
from .ppt_converter import PPTConverter

__all__ = ["MarpGenerator", "PPTConverter"]
