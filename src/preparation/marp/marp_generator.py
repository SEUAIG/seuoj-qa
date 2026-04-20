"""
Marp Markdown 生成器

将生成的内容转换为符合 Marp 语法的 Markdown 格式。
"""

from typing import List, Dict, Optional
from datetime import datetime


class MarpGenerator:
    """Marp Markdown 生成器"""

    def __init__(self, theme: str = "default"):
        """
        初始化生成器

        Args:
            theme: Marp 主题
        """
        self.theme = theme

    def generate(
        self,
        slides: List[Dict[str, str]],
        metadata: Optional[Dict] = None
    ) -> str:
        """
        生成完整的 Marp Markdown

        Args:
            slides: 幻灯片内容列表
            metadata: 元数据（标题、作者等）

        Returns:
            Marp 格式的 Markdown 字符串
        """
        lines = []

        # 添加 Marp 头部
        lines.extend(self._generate_header(metadata))

        # 添加封面
        if metadata and metadata.get("title"):
            lines.extend(self._generate_cover(metadata))

        # 添加目录（可选）
        lines.extend(self._generate_toc(slides))

        # 添加内容页
        for slide in slides:
            lines.extend(self._generate_slide(slide))

        return "\n\n".join(lines)

    def _generate_header(self, metadata: Optional[Dict]) -> List[str]:
        """生成 Marp 头部配置"""
        header = [
            "---",
            f"marp: true",
            f"theme: {self.theme}",
            f"paginate: true",
            f"style: |",
            f"  /* 自定义样式 */",
            f"  .si-zheng {{",
            f"    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);",
            f"    padding: 0.5em;",
            f"    border-radius: 8px;",
            f"    color: white;",
            f"    font-size: 0.9em;",
            f"    margin: 0.5em 0;",
            f"  }}",
            "---",
            ""
        ]
        return header

    def _generate_cover(self, metadata: Dict) -> List[str]:
        """生成封面页"""
        title = metadata.get("title", "课程课件")
        subtitle = metadata.get("subtitle", "")
        author = metadata.get("author", "")
        date = metadata.get("date", datetime.now().strftime("%Y年%m月%d日"))

        cover = [
            "<!-- _class: lead -->",
            "",
            f"# {title}",
            f"### {subtitle}" if subtitle else "",
            f"",
            f"**{author}**" if author else "",
            f"{date}" if date else "",
            ""
        ]
        return [line for line in cover if line]

    def _generate_toc(self, slides: List[Dict]) -> List[str]:
        """生成目录页"""
        # 提取一级标题
        first_level_titles = [
            s["title"] for s in slides
            if s.get("original_level", 1) == 1
        ]

        if not first_level_titles:
            return []

        toc = [
            "<!-- _class: lead -->",
            "",
            "# 目录",
            ""
        ]

        for i, title in enumerate(first_level_titles[:10], 1):
            toc.append(f"{i}. {title}")

        toc.append("")
        return toc

    def _generate_slide(self, slide: Dict) -> List[str]:
        """生成单页幻灯片"""
        title = slide.get("title", "未命名")
        content = slide.get("content", "")
        si_zheng = slide.get("si_zheng_note", "")

        slide_lines = [
            "---",
            "",
            f"# {title}",
            ""
        ]

        # 添加内容
        if content:
            slide_lines.append(content)
            slide_lines.append("")

        # 添加思政融合点标注
        if si_zheng:
            slide_lines.extend([
                f"",
                f"<div class='si-zheng'>",
                f"📚 思政融合点: {si_zheng}",
                f"</div>",
                ""
            ])

        return slide_lines

    def save(self, marp_content: str, output_path: str) -> None:
        """
        保存 Marp 文件

        Args:
            marp_content: Marp Markdown 内容
            output_path: 输出文件路径
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(marp_content)

    def update_slide(
        self,
        existing_marp: str,
        slide_number: int,
        new_content: Dict
    ) -> str:
        """
        更新指定页面的内容

        Args:
            existing_marp: 现有 Marp 内容
            slide_number: 幻灯片编号
            new_content: 新内容

        Returns:
            更新后的 Marp 内容
        """
        # 这个功能比较复杂，暂时返回原内容
        # 完整实现需要解析 Markdown 中的幻灯片分隔符
        return existing_marp
