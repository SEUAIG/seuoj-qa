# """
# 文档分层解析器

# 将解析后的 Markdown 按照教学层级进行分割和结构化处理。
# 支持按 PPT 页面分割 Markdown 文件。
# """

# import re
# import json
# from pathlib import Path
# from typing import List, Dict
# from dataclasses import dataclass, field


# @dataclass
# class SlideChunk:
#     """幻灯片内容块"""
#     title: str
#     content: str
#     level: int
#     slide_number: int = 0
#     keywords: List[str] = field(default_factory=list)
#     images: List[str] = field(default_factory=list)
#     subsections: List[str] = field(default_factory=list)


# @dataclass
# class DocumentStructure:
#     """文档结构"""
#     title: str
#     author: str = ""
#     institution: str = ""
#     chunks: List[SlideChunk] = field(default_factory=list)
#     outline: List[Dict] = field(default_factory=list)

#     def get_teaching_chain(self) -> str:
#         """获取教学流程描述"""
#         key_titles = [
#             {"title": c.title, "level": c.level}
#             for c in self.chunks
#             if c.level <= 2
#         ]
#         return " → ".join([t["title"] for t in key_titles[:6]])

#     def get_sections(self) -> List[Dict]:
#         """获取章节结构"""
#         return [
#             {"title": c.title, "slide_number": c.slide_number, "level": c.level}
#             for c in self.chunks if c.level <= 2
#         ]


# class DocumentSplitter:
#     """文档分层解析器"""

#     def __init__(self):
#         """初始化分割器"""
#         # 匹配 Markdown 标题的正则
#         self.header_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
#         # 匹配图片链接
#         self.image_pattern = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
#         # 匹配图片行 (用于分页)
#         self.image_line_pattern = re.compile(r'^!\[([^\]]*)\]\(([^)]+)\)$', re.MULTILINE)

#     def parse(self, markdown_content: str) -> DocumentStructure:
#         """
#         解析 Markdown 文档为结构化数据

#         Args:
#             markdown_content: Markdown 格式的文档内容

#         Returns:
#             DocumentStructure 对象
#         """
#         lines = markdown_content.split('\n')

#         # 解析封面信息
#         structure = self._parse_cover(lines)

#         # 解析正文内容块
#         chunks = self._parse_content_blocks(lines)
#         structure.chunks = chunks

#         # 生成大纲
#         structure.outline = self._generate_outline(chunks)

#         # 编号幻灯片
#         for i, chunk in enumerate(chunks):
#             chunk.slide_number = i

#         return structure

#     def _parse_cover(self, lines: List[str]) -> DocumentStructure:
#         """解析封面信息"""
#         structure = DocumentStructure(title="未命名课件")

#         # 前几行通常是封面信息
#         for line in lines[:10]:
#             if line.strip().startswith("# ") and not structure.title:
#                 structure.title = line.strip().replace("# ", "").strip()
#             elif not structure.institution and ("学院" in line or "大学" in line):
#                 structure.institution = line.strip()
#             elif not structure.author and len(line.strip()) < 20 and line.strip():
#                 # 假设较短的行是作者名
#                 structure.author = line.strip()

#         return structure

#     def _parse_content_blocks(self, lines: List[str]) -> List[SlideChunk]:
#         """解析内容块"""
#         chunks = []
#         current_title = "封面"
#         current_level = 1
#         current_content = []
#         current_keywords = []

#         for line in lines:
#             header_match = self.header_pattern.match(line)

#             if header_match:
#                 # 保存之前的块
#                 if current_content or current_title != "封面":
#                     content_text = "\n".join(current_content).strip()
#                     chunks.append(SlideChunk(
#                         title=current_title,
#                         content=content_text,
#                         level=current_level,
#                         keywords=current_keywords.copy(),
#                         images=self._extract_images(content_text)
#                     ))

#                 # 开始新块
#                 current_level = len(header_match.group(1))
#                 current_title = header_match.group(2).strip()
#                 current_content = []
#                 current_keywords = []
#             else:
#                 current_content.append(line)

#                 # 检测关键词行
#                 if "关键词:" in line or "关键词：" in line:
#                     # 下一行可能是关键词
#                     pass

#         # 添加最后一个块
#         if current_content:
#             content_text = "\n".join(current_content).strip()
#             chunks.append(SlideChunk(
#                 title=current_title,
#                 content=content_text,
#                 level=current_level,
#                 keywords=current_keywords,
#                 images=self._extract_images(content_text)
#             ))

#         return chunks

#     def _extract_images(self, content: str) -> List[str]:
#         """提取图片链接"""
#         return self.image_pattern.findall(content)

#     def _generate_outline(self, chunks: List[SlideChunk]) -> List[Dict]:
#         """生成文档大纲"""
#         outline = []
#         current_level_1 = None

#         for chunk in chunks:
#             if chunk.level == 1:
#                 current_level_1 = chunk.title
#                 outline.append({
#                     "title": chunk.title,
#                     "level": 1,
#                     "slide_number": chunk.slide_number
#                 })
#             elif chunk.level == 2:
#                 outline.append({
#                     "title": chunk.title,
#                     "parent": current_level_1,
#                     "level": 2,
#                     "slide_number": chunk.slide_number
#                 })

#         return outline

#     def load_markdown(self, file_path: str) -> str:
#         """
#         加载 Markdown 文件

#         Args:
#             file_path: Markdown 文件路径

#         Returns:
#             文件内容
#         """
#         return Path(file_path).read_text(encoding="utf-8")

#     def parse_file(self, file_path: str) -> DocumentStructure:
#         """
#         从文件解析

#         Args:
#             file_path: Markdown 文件路径

#         Returns:
#             DocumentStructure 对象
#         """
#         content = self.load_markdown(file_path)
#         return self.parse(content)

#     def save_structure(self, structure: DocumentStructure, output_path: str) -> None:
#         """
#         保存结构化数据

#         Args:
#             structure: 文档结构
#             output_path: 输出文件路径（JSON）
#         """
#         import json

#         data = {
#             "title": structure.title,
#             "author": structure.author,
#             "institution": structure.institution,
#             "teaching_chain": structure.get_teaching_chain(),
#             "outline": structure.outline,
#             "sections": structure.get_sections(),
#             "slides": [
#                 {
#                     "slide_number": c.slide_number,
#                     "title": c.title,
#                     "content": c.content,
#                     "level": c.level,
#                     "keywords": c.keywords,
#                     "images": c.images
#                 }
#                 for c in structure.chunks
#             ]
#         }

#         Path(output_path).write_text(
#             json.dumps(data, ensure_ascii=False, indent=2),
#             encoding="utf-8"
#         )

#     def get_content_context(self, structure: DocumentStructure, slide_number: int) -> str:
#         """
#         获取指定幻灯片的上下文信息

#         Args:
#             structure: 文档结构
#             slide_number: 幻灯片编号

#         Returns:
#             上下文描述
#         """
#         chunks = structure.chunks
#         n = len(chunks)

#         context_parts = []

#         # 课程标题
#         context_parts.append(f"【课程】{structure.title}")

#         # 教学流程
#         context_parts.append(f"【流程】{structure.get_teaching_chain()}")

#         # 前一页
#         if slide_number > 0:
#             prev_chunk = chunks[slide_number - 1]
#             context_parts.append(f"【前一页】{prev_chunk.title}")

#         # 当前页
#         current_chunk = chunks[slide_number]
#         context_parts.append(f"【当前页】{current_chunk.title}")

#         # 后一页
#         if slide_number < n - 1:
#             next_chunk = chunks[slide_number + 1]
#             context_parts.append(f"【后一页】{next_chunk.title}")

#         return "\n".join(context_parts)

#     # ========== 新增：按 PPT 页面分割 ==========

#     def split_by_slides(self, file_path: str, output_dir: str = None) -> List[Dict]:
#         """
#         按 PPT 页面分割 Markdown 文件

#         分页规则:
#         1. 一级标题 (#) 作为新页面开始
#         2. 图片行 (![image](...)) 通常表示新页面（但属于当前页内容）
#         3. 连续空行分隔不同的内容块

#         Args:
#             file_path: Markdown 文件路径
#             output_dir: 输出目录（如果为 None 则只返回不保存）

#         Returns:
#             页面列表，每个页面包含 title, content, page_number
#         """
#         content = self.load_markdown(file_path)
#         lines = content.split('\n')

#         pages = []
#         current_page_lines = []
#         current_title = "封面"
#         page_number = 0

#         # 封面信息（前几行）
#         cover_end = 0
#         for i, line in enumerate(lines[:15]):
#             if line.strip().startswith("# "):
#                 current_title = line.strip().replace("# ", "").strip()
#             elif re.match(r'^\s*$', line) and i > 3:
#                 cover_end = i
#                 break

#         # 第一页：封面
#         if cover_end > 0:
#             pages.append({
#                 "page_number": page_number,
#                 "title": current_title,
#                 "content": "\n".join(lines[:cover_end]).strip()
#             })
#             page_number += 1
#             current_page_lines = []

#         # 遍历剩余内容进行分页
#         for i in range(cover_end, len(lines)):
#             line = lines[i]

#             # 检测一级标题（新页面开始）
#             if line.strip().startswith("# ") and not line.strip().startswith("##"):
#                 # 保存当前页面
#                 if current_page_lines:
#                     pages.append({
#                         "page_number": page_number,
#                         "title": current_title,
#                         "content": "\n".join(current_page_lines).strip()
#                     })
#                     page_number += 1

#                 # 开始新页面
#                 current_title = line.strip().replace("# ", "").strip()
#                 current_page_lines = [line]

#             # 检测连续空行（可能表示页面分隔）
#             elif self._is_page_break(lines, i):
#                 # 保存当前页面
#                 if current_page_lines:
#                     pages.append({
#                         "page_number": page_number,
#                         "title": current_title,
#                         "content": "\n".join(current_page_lines).strip()
#                     })
#                     page_number += 1

#                 # 找到下一个非空行作为新页面的标题
#                 j = i + 1
#                 while j < len(lines) and not lines[j].strip():
#                     j += 1

#                 if j < len(lines):
#                     next_line = lines[j].strip()
#                     if next_line.startswith("#"):
#                         current_title = next_line.replace("#", "").strip()
#                     else:
#                         current_title = next_line[:50]  # 取前50字符作为标题

#                 current_page_lines = []
#                 i = j - 1  # 跳过空行

#             else:
#                 current_page_lines.append(line)

#         # 添加最后一页
#         if current_page_lines:
#             pages.append({
#                 "page_number": page_number,
#                 "title": current_title,
#                 "content": "\n".join(current_page_lines).strip()
#             })

#         # 保存结果
#         if output_dir:
#             self._save_split_pages(pages, file_path, output_dir)

#         return pages

#     def _is_page_break(self, lines: List[str], current_idx: int) -> bool:
#         """
#         判断当前位置是否为页面分隔点

#         规则:
#         1. 当前行是空行
#         2. 后面有2个或更多连续空行
#         3. 或者后面有图片但当前行不是图片
#         """
#         if not lines[current_idx].strip():
#             # 检查后面连续空行数量
#             empty_count = 0
#             for i in range(current_idx, min(current_idx + 5, len(lines))):
#                 if not lines[i].strip():
#                     empty_count += 1
#                 else:
#                     break

#             # 3个或更多连续空行认为是分页
#             if empty_count >= 3:
#                 return True

#         return False

#     def _save_split_pages(self, pages: List[Dict], input_file: str, output_dir: str) -> None:
#         """
#         保存分割后的页面

#         Args:
#             pages: 页面列表
#             input_file: 输入文件路径
#             output_dir: 输出目录
#         """
#         output_path = Path(output_dir)
#         output_path.mkdir(parents=True, exist_ok=True)

#         input_name = Path(input_file).stem

#         # 保存为 JSON
#         json_file = output_path / f"{input_name}_pages.json"
#         json_file.write_text(
#             json.dumps(pages, ensure_ascii=False, indent=2),
#             encoding="utf-8"
#         )
#         print(f"Saved: {json_file}")

#         # 保存为分开的 Markdown 文件
#         md_dir = output_path / f"{input_name}_pages"
#         md_dir.mkdir(parents=True, exist_ok=True)

#         for page in pages:
#             page_file = md_dir / f"page_{page_number_to_roman(page['page_number'])}.md"
#             content = f"# Page {page['page_number'] + 1}: {page['title']}\n\n"
#             content += page['content']
#             page_file.write_text(content, encoding="utf-8")

#         print(f"Saved {len(pages)} pages to: {md_dir}")

#         # 保存为合并的 Markdown（带分页标记）
#         merged_file = output_path / f"{input_name}_split.md"
#         merged_content = []
#         for page in pages:
#             merged_content.append(f"\n---\n")
#             merged_content.append(f"## 第 {page['page_number'] + 1} 页: {page['title']}\n")
#             merged_content.append(page['content'])

#         merged_file.write_text("\n".join(merged_content), encoding="utf-8")
#         print(f"Saved merged file: {merged_file}")


# def page_number_to_roman(n: int) -> str:
#     """将页码转换为罗马数字"""
#     if n == 0:
#         return "i"
#     roman_numerals = [
#         (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
#         (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
#         (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")
#     ]
#     result = ""
#     for value, numeral in roman_numerals:
#         while n >= value:
#             result += numeral
#             n -= value
#     return result.lower()


# # ========== 便捷函数 ==========

# def split_markdown_by_slides(
#     input_file: str,
#     output_dir: str = "data/preparation/split"
# ) -> List[Dict]:
#     """
#     快捷函数：按 PPT 页面分割 Markdown

#     Args:
#         input_file: 输入 Markdown 文件
#         output_dir: 输出目录

#     Returns:
#         页面列表
#     """
#     splitter = DocumentSplitter()
#     return splitter.split_by_slides(input_file, output_dir)


import re
import json
from pathlib import Path
from typing import List, Dict
from dataclasses import dataclass, field


@dataclass
class SlideChunk:
    """幻灯片内容块"""
    title: str
    content: str
    level: int
    slide_number: int = 0
    keywords: List[str] = field(default_factory=list)
    images: List[str] = field(default_factory=list)
    subsections: List[str] = field(default_factory=list)


@dataclass
class DocumentStructure:
    """文档结构"""
    title: str
    author: str = ""
    institution: str = ""
    chunks: List[SlideChunk] = field(default_factory=list)
    outline: List[Dict] = field(default_factory=list)

    def get_teaching_chain(self) -> str:
        """获取教学流程描述"""
        key_titles = [
            {"title": c.title, "level": c.level}
            for c in self.chunks
            if c.level <= 2
        ]
        return " → ".join([t["title"] for t in key_titles[:6]])

    def get_sections(self) -> List[Dict]:
        """获取章节结构"""
        return [
            {"title": c.title, "slide_number": c.slide_number, "level": c.level}
            for c in self.chunks if c.level <= 2
        ]


class DocumentSplitter:
    """文档分层解析器"""

    def __init__(self):
        """初始化分割器"""
        # 匹配 Markdown 标题的正则
        self.header_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
        # 匹配图片链接
        self.image_pattern = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
        # 匹配图片行 (用于分页)
        self.image_line_pattern = re.compile(r'^!\[([^\]]*)\]\(([^)]+)\)$', re.MULTILINE)
        # 匹配 PPT 分页符 ---
        self.slide_break_pattern = re.compile(r'^\s*---\s*$', re.MULTILINE)

    def parse(self, markdown_content: str) -> DocumentStructure:
        """
        解析 Markdown 文档为结构化数据

        Args:
            markdown_content: Markdown 格式的文档内容

        Returns:
            DocumentStructure 对象
        """
        lines = markdown_content.split('\n')

        # 解析封面信息
        structure = self._parse_cover(lines)

        # 解析正文内容块
        chunks = self._parse_content_blocks(lines)
        structure.chunks = chunks

        # 编号幻灯片（先编号，再生成大纲）
        for i, chunk in enumerate(chunks):
            chunk.slide_number = i

        # 生成大纲
        structure.outline = self._generate_outline(chunks)

        return structure

    def _parse_cover(self, lines: List[str]) -> DocumentStructure:
        """解析封面信息"""
        structure = DocumentStructure(title="未命名课件")

        # 修正：如果遇到 # 标题，优先作为文档标题
        for line in lines[:10]:
            stripped = line.strip()
            if stripped.startswith("# "):
                structure.title = stripped.replace("# ", "", 1).strip()
                break

        for line in lines[:10]:
            stripped = line.strip()
            if not structure.institution and ("学院" in stripped or "大学" in stripped):
                structure.institution = stripped
            elif not structure.author and len(stripped) < 20 and stripped and not stripped.startswith("#"):
                # 假设较短的行是作者名
                structure.author = stripped

        return structure

    def _parse_content_blocks(self, lines: List[str]) -> List[SlideChunk]:
        """解析内容块"""
        chunks = []
        current_title = "封面"
        current_level = 1
        current_content = []
        current_keywords = []

        for line in lines:
            header_match = self.header_pattern.match(line)

            if header_match:
                # 保存之前的块
                if current_content or current_title != "封面":
                    content_text = "\n".join(current_content).strip()
                    chunks.append(SlideChunk(
                        title=current_title,
                        content=content_text,
                        level=current_level,
                        keywords=current_keywords.copy(),
                        images=self._extract_images(content_text)
                    ))

                # 开始新块
                current_level = len(header_match.group(1))
                current_title = header_match.group(2).strip()
                current_content = []
                current_keywords = []
            else:
                current_content.append(line)

                # 检测关键词行
                if "关键词:" in line or "关键词：" in line:
                    pass

        # 添加最后一个块
        if current_content:
            content_text = "\n".join(current_content).strip()
            chunks.append(SlideChunk(
                title=current_title,
                content=content_text,
                level=current_level,
                keywords=current_keywords,
                images=self._extract_images(content_text)
            ))

        return chunks

    def _extract_images(self, content: str) -> List[str]:
        """提取图片链接"""
        return self.image_pattern.findall(content)

    def _generate_outline(self, chunks: List[SlideChunk]) -> List[Dict]:
        """生成文档大纲"""
        outline = []
        current_level_1 = None

        for chunk in chunks:
            if chunk.level == 1:
                current_level_1 = chunk.title
                outline.append({
                    "title": chunk.title,
                    "level": 1,
                    "slide_number": chunk.slide_number
                })
            elif chunk.level == 2:
                outline.append({
                    "title": chunk.title,
                    "parent": current_level_1,
                    "level": 2,
                    "slide_number": chunk.slide_number
                })

        return outline

    def load_markdown(self, file_path: str) -> str:
        """
        加载 Markdown 文件

        Args:
            file_path: Markdown 文件路径

        Returns:
            文件内容
        """
        return Path(file_path).read_text(encoding="utf-8")

    def parse_file(self, file_path: str) -> DocumentStructure:
        """
        从文件解析

        Args:
            file_path: Markdown 文件路径

        Returns:
            DocumentStructure 对象
        """
        content = self.load_markdown(file_path)
        return self.parse(content)

    def save_structure(self, structure: DocumentStructure, output_path: str) -> None:
        """
        保存结构化数据

        Args:
            structure: 文档结构
            output_path: 输出文件路径（JSON）
        """
        data = {
            "title": structure.title,
            "author": structure.author,
            "institution": structure.institution,
            "teaching_chain": structure.get_teaching_chain(),
            "outline": structure.outline,
            "sections": structure.get_sections(),
            "slides": [
                {
                    "slide_number": c.slide_number,
                    "title": c.title,
                    "content": c.content,
                    "level": c.level,
                    "keywords": c.keywords,
                    "images": c.images
                }
                for c in structure.chunks
            ]
        }

        Path(output_path).write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def get_content_context(self, structure: DocumentStructure, slide_number: int) -> str:
        """
        获取指定幻灯片的上下文信息

        Args:
            structure: 文档结构
            slide_number: 幻灯片编号

        Returns:
            上下文描述
        """
        chunks = structure.chunks
        n = len(chunks)

        context_parts = []

        context_parts.append(f"【课程】{structure.title}")
        context_parts.append(f"【流程】{structure.get_teaching_chain()}")

        if slide_number > 0:
            prev_chunk = chunks[slide_number - 1]
            context_parts.append(f"【前一页】{prev_chunk.title}")

        current_chunk = chunks[slide_number]
        context_parts.append(f"【当前页】{current_chunk.title}")

        if slide_number < n - 1:
            next_chunk = chunks[slide_number + 1]
            context_parts.append(f"【后一页】{next_chunk.title}")

        return "\n".join(context_parts)

    # ========== 修改：按文档类型分页 ==========

    def split_by_slides(self, file_path: str, output_dir: str = None) -> List[Dict]:
        """
        按页面分割 Markdown 文件

        规则:
        - PPT markdown: 以 --- 分页
        - PDF markdown: 以 # 一级标题分页

        Args:
            file_path: Markdown 文件路径
            output_dir: 输出目录（如果为 None 则只返回不保存）

        Returns:
            页面列表，每个页面包含 title, content, page_number
        """
        content = self.load_markdown(file_path)
        doc_type = self._detect_markdown_type(content)

        if doc_type == "ppt":
            pages = self._split_ppt_markdown(content)
        else:
            pages = self._split_pdf_markdown(content)

        if output_dir:
            self._save_split_pages(pages, file_path, output_dir)

        return pages

    def _detect_markdown_type(self, content: str) -> str:
        """
        自动判断 markdown 来源类型

        判断逻辑:
        - 若存在明显的 --- 分页符，则判定为 ppt
        - 否则判定为 pdf
        """
        lines = content.splitlines()

        separator_count = sum(
            1 for line in lines
            if re.match(r'^\s*---\s*$', line)
        )

        if separator_count >= 1:
            return "ppt"
        return "pdf"

    def _extract_title_from_page(self, page_content: str, default_title: str = "未命名页面") -> str:
        """
        从单页内容中提取标题：
        优先取第一个一级标题 # xxx
        否则取第一个非空行
        """
        lines = page_content.splitlines()

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("# "):
                return stripped.replace("# ", "", 1).strip()

        for line in lines:
            stripped = line.strip()
            if stripped:
                return stripped[:50]

        return default_title

    def _split_ppt_markdown(self, content: str) -> List[Dict]:
        """
        PPT markdown 分页：
        以 --- 为分页符
        """
        raw_pages = re.split(r'^\s*---\s*$', content, flags=re.MULTILINE)
        pages = []

        for idx, page_text in enumerate(raw_pages):
            page_text = page_text.strip()
            if not page_text:
                continue

            title = self._extract_title_from_page(page_text, default_title=f"第 {idx + 1} 页")
            pages.append({
                "page_number": len(pages),
                "title": title,
                "content": page_text
            })

        return pages

    def _split_pdf_markdown(self, content: str) -> List[Dict]:
        """
        PDF markdown 分页：
        以一级标题 # 开始新页
        注意：
        - ### / #### 不分页
        - 每个页面保留其对应的 # 标题在内容里
        """
        lines = content.splitlines()
        pages = []

        current_page_lines = []
        current_title = "封面"

        for line in lines:
            stripped = line.strip()

            # 仅一级标题作为新页起点
            if stripped.startswith("# ") and not stripped.startswith("##"):
                if current_page_lines:
                    page_content = "\n".join(current_page_lines).strip()
                    if page_content:
                        pages.append({
                            "page_number": len(pages),
                            "title": current_title,
                            "content": page_content
                        })

                current_title = stripped.replace("# ", "", 1).strip()
                current_page_lines = [line]
            else:
                current_page_lines.append(line)

        # 最后一页
        if current_page_lines:
            page_content = "\n".join(current_page_lines).strip()
            if page_content:
                pages.append({
                    "page_number": len(pages),
                    "title": current_title,
                    "content": page_content
                })

        return pages

    def _save_split_pages(self, pages: List[Dict], input_file: str, output_dir: str) -> None:
        """
        保存分割后的页面

        Args:
            pages: 页面列表
            input_file: 输入文件路径
            output_dir: 输出目录
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        input_name = Path(input_file).stem

        # 保存为 JSON
        json_file = output_path / f"{input_name}_pages.json"
        json_file.write_text(
            json.dumps(pages, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print(f"Saved: {json_file}")

        # 保存为分开的 Markdown 文件
        md_dir = output_path / f"{input_name}_pages"
        md_dir.mkdir(parents=True, exist_ok=True)

        for page in pages:
            page_file = md_dir / f"page_{page_number_to_roman(page['page_number'])}.md"
            content = f"# Page {page['page_number'] + 1}: {page['title']}\n\n"
            content += page['content']
            page_file.write_text(content, encoding="utf-8")

        print(f"Saved {len(pages)} pages to: {md_dir}")

        # 保存为合并的 Markdown（带分页标记）
        merged_file = output_path / f"{input_name}_split.md"
        merged_content = []
        for page in pages:
            merged_content.append(f"\n---\n")
            merged_content.append(f"## 第 {page['page_number'] + 1} 页: {page['title']}\n")
            merged_content.append(page['content'])

        merged_file.write_text("\n".join(merged_content), encoding="utf-8")
        print(f"Saved merged file: {merged_file}")


def page_number_to_roman(n: int) -> str:
    """将页码转换为罗马数字"""
    if n == 0:
        return "i"
    roman_numerals = [
        (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
        (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
        (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")
    ]
    result = ""
    for value, numeral in roman_numerals:
        while n >= value:
            result += numeral
            n -= value
    return result.lower()


def split_markdown_by_slides(
    input_file: str,
    output_dir: str = "data/preparation/split"
) -> List[Dict]:
    """
    快捷函数：按页面分割 Markdown

    Args:
        input_file: 输入 Markdown 文件
        output_dir: 输出目录

    Returns:
        页面列表
    """
    splitter = DocumentSplitter()
    return splitter.split_by_slides(input_file, output_dir)

if __name__ == "__main__":
    """
    Main function - hardcoded markdown splitting test
    """
    INPUT_FILE = "/home/guoziyang/AIgorithm_Agent/input/WEEK1-1 Chap01-25-1.md"
    OUTPUT_DIR = "/home/guoziyang/AIgorithm_Agent/src/preparation/parser/tmp"

    print("=" * 60)
    print("Markdown Splitter by PPT Pages")
    print("=" * 60)
    print(f"Input file: {INPUT_FILE}")
    print(f"Output dir: {OUTPUT_DIR}")
    print("-" * 60)

    splitter = DocumentSplitter()
    pages = splitter.split_by_slides(INPUT_FILE, OUTPUT_DIR)

    print("-" * 60)
    print(f"Split completed! Total pages: {len(pages)}")
    print()

    for i, page in enumerate(pages):
        title = page["title"]
        content_len = len(page["content"])
        print(f"  Page {i+1:2d}: {title[:40]:40s} ({content_len} chars)")
