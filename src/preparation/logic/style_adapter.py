"""
教师风格适配器

根据教师上传的内容判断风格，并调整生成内容的风格。
"""

from typing import Dict, List, Optional
from collections import Counter
import re


class StyleAdapter:
    """教师风格适配器"""

    def __init__(self):
        """初始化适配器"""
        # 风格特征词库
        self.style_indicators = {
            "formal": ["综上所述", "由此可见", "因此", "因而", "基于上述分析"],
            "casual": ["简单来说", "其实就是", "好比", "可以这么理解"],
            "example_heavy": ["例如", "比如", "以...为例", "举例说明"],
            "concise": ["简言之", "换句话说", "总之", "核心是"],
            "detailed": ["具体来说", "详细分析", "深入探讨", "进一步"]
        }

    def analyze_style(self, sample_contents: List[str]) -> Dict[str, bool]:
        """
        分析教师写作风格

        Args:
            sample_contents: 样本文本列表

        Returns:
            风格特征字典
        """
        if not sample_contents:
            return self._default_style()

        combined_text = " ".join(sample_contents)

        style = {}
        for style_name, indicators in self.style_indicators.items():
            score = sum(1 for ind in indicators if ind in combined_text)
            style[style_name] = score >= 2  # 至少出现2次认为有该特征

        return style

    def analyze_from_chunks(self, chunks: List) -> Dict[str, bool]:
        """
        从幻灯片块分析风格

        Args:
            chunks: 幻灯片块列表

        Returns:
            风格特征字典
        """
        # 采样前5页内容
        samples = [chunk.content for chunk in chunks[:5]]
        return self.analyze_style(samples)

    def get_style_prompt(self, style: Dict[str, bool]) -> str:
        """
        根据风格生成 Prompt 指导

        Args:
            style: 风格特征字典

        Returns:
            风格指导 Prompt
        """
        hints = []

        if style.get("formal"):
            hints.append("使用正式、学术化的表达方式")
        elif style.get("casual"):
            hints.append("使用通俗易懂、口语化的表达方式")

        if style.get("example_heavy"):
            hints.append("多使用具体案例和实例说明")
        elif style.get("concise"):
            hints.append("保持内容简洁，突出核心要点")

        if style.get("detailed"):
            hints.append("内容可以较为详尽，提供深入分析")

        if not hints:
            hints.append("使用标准的教学风格，平衡专业性和可读性")

        return "【风格指导】\n" + "\n".join(f"- {h}" for h in hints)

    def _default_style(self) -> Dict[str, bool]:
        """返回默认风格"""
        return {
            "formal": True,
            "casual": False,
            "example_heavy": True,
            "concise": False,
            "detailed": True
        }

    def apply_style_to_content(
        self,
        content: str,
        style: Dict[str, bool]
    ) -> str:
        """
        将风格应用到内容（后期处理）

        Args:
            content: 原始内容
            style: 风格特征

        Returns:
            调整后的内容
        """
        # 这里可以实现一些简单的风格转换规则
        # 目前仅返回原内容，复杂转换可以后续通过 LLM 实现
        return content
