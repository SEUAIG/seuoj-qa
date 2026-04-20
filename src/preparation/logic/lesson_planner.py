# -*- coding: utf-8 -*-
"""
教学链路规划器

使用 LLM 根据解析后的内容，决策哪些页面需要优化。
"""

import sys
from pathlib import Path

# 添加项目根目录到路径（支持直接运行）
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import json
from typing import List, Dict, Optional
from dataclasses import dataclass, field

from camel.agents import ChatAgent

try:
    from ..parser.document_splitter import DocumentStructure, SlideChunk
    from ..config import get_llm_client
except ImportError:
    # 直接运行时的导入
    from src.preparation.parser.document_splitter import DocumentStructure, SlideChunk
    from src.preparation.config import get_llm_client


@dataclass
class OptimizationPoint:
    """页面优化决策（LLM 决策结果）"""
    slide_number: int
    title: str
    should_optimize: bool
    reason: str = ""
    suggested_keywords: List[str] = field(default_factory=list)
    optimization_strategy: str = ""  # LLM 建议的优化方式

    def __post_init__(self):
        if not self.suggested_keywords:
            self.suggested_keywords = []


# 保留别名用于兼容
InsertionPoint = OptimizationPoint


class LessonPlanner:
    """教学链路规划器 - 使用 LLM 进行决策"""

    # 用于 LLM 决策的 Prompt 模板
    DECISION_PROMPT = """你是一位教学设计专家，擅长分析课件内容并判断哪些页面适合优化（融入思政教育元素）。

# 任务

分析以下课件内容，判断每一页是否需要优化（融入思政内容），并给出具体建议。

{user_requirement}

# 判断原则

1. **自然融入**：思政内容要与专业知识有机融合，不生硬
2. **适度原则**：不是每一页都需要优化，选择合适的页面
3. **价值引领**：优先选择可以体现价值观、社会责任、家国情怀的页面
4. **避免过度**：避免在纯技术性、过渡性页面强行优化

# 不需要优化的页面类型

- 封面、目录、致谢页
- 纯技术定义、公式推导页
- 简单的过渡页
- 内容过于简单的页面

# 需要优化的页面特征

- 涉及价值观、社会现象、历史背景的页面
- 可以联系现实、引发思考的页面
- 与国家发展、社会进步相关的主题

# 输出格式

请严格按照以下 JSON 格式输出：

```json
{{
  "analysis": "整体分析：课程主题和思政融入的总体思路",
  "pages": [
    {{
      "slide_number": 0,
      "title": "页面标题",
      "should_optimize": false,
      "reason": "不需要的原因（如：封面页）",
      "suggested_keywords": [],
      "optimization_strategy": ""
    }},
    {{
      "slide_number": 4,
      "title": "马克思主义的诞生",
      "should_optimize": true,
      "reason": "可以联系当代中国马克思主义的发展",
      "suggested_keywords": ["马克思主义", "当代中国", "理论创新"],
      "optimization_strategy": "在介绍马克思主义诞生背景后，自然延伸到当代中国马克思主义的发展历程"
    }}
  ]
}}
```

# 课件内容

{slides_info}

请开始分析："""

    def __init__(self, model=None):
        """初始化规划器"""
        self.model = model or get_llm_client()
        self.agent = ChatAgent(
            system_message="你是一位教学设计专家，擅长分析课件并规划思政内容的融入。",
            model=self.model
        )

    def analyze_document(self, structure: DocumentStructure) -> Dict:
        """
        分析完整文档结构

        Args:
            structure: 文档结构

        Returns:
            分析结果字典
        """
        return {
            "title": structure.title,
            "author": structure.author,
            "total_slides": len(structure.chunks),
            "teaching_chain": structure.get_teaching_chain(),
            "sections": structure.get_sections(),
            "outline": structure.outline
        }

    def plan_teaching_chain(self, structure: DocumentStructure) -> Dict:
        """
        构建完整教学链路

        Args:
            structure: 文档结构

        Returns:
            教学链路字典
        """
        return {
            "total_slides": len(structure.chunks),
            "flow": structure.get_teaching_chain(),
        }

    def decide_insertion_points(
        self,
        structure: DocumentStructure,
        user_prompt: str = None,
        policy_contents: List[Dict] = None
    ) -> List[OptimizationPoint]:
        """
        使用 LLM 决策哪些页面需要优化

        Args:
            structure: 文档结构
            user_prompt: 用户自定义需求，如"侧重算法伦理"
            policy_contents: 可用的思政内容（可选，用于参考）

        Returns:
            优化决策点列表
        """
        # 构建页面信息
        slides_info = self._build_slides_info(structure)

        # 生成决策 Prompt
        if user_prompt:
            prompt = self.DECISION_PROMPT.format(
                slides_info=slides_info,
                user_requirement=f"\n\n# 用户需求\n\n{user_prompt}\n\n请根据用户需求来判断哪些页面需要优化。"
            )
        else:
            prompt = self.DECISION_PROMPT.format(
                slides_info=slides_info,
                user_requirement=""
            )

        # 调用 LLM
        try:
            response = self.agent.step(prompt)
            result = self._parse_decision_response(response.msg.content)
        except Exception as e:
            print(f"  [LLM 决策失败: {e}]，使用默认规则")
            result = self._fallback_decision(structure)

        # 转换为 OptimizationPoint 列表
        optimization_points = []
        for page_decision in result.get("pages", []):
            optimization_points.append(OptimizationPoint(
                slide_number=page_decision["slide_number"],
                title=page_decision["title"],
                should_optimize=page_decision.get("should_optimize", page_decision.get("should_insert", False)),
                reason=page_decision.get("reason", ""),
                suggested_keywords=page_decision.get("suggested_keywords", []),
                optimization_strategy=page_decision.get("optimization_strategy", page_decision.get("insertion_strategy", ""))
            ))

        return optimization_points

    def _build_slides_info(self, structure: DocumentStructure) -> str:
        """构建用于 LLM 决策的页面信息"""
        slides_info = f"## 课程信息\n\n标题：{structure.title}\n总页数：{len(structure.chunks)}\n\n"
        slides_info += "## 页面列表\n\n"

        for i, chunk in enumerate(structure.chunks):
            # 截取内容，避免太长
            content_preview = chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content

            slides_info += f"""### 页面 {i + 1}: {chunk.title}

- 页码: {i}
- 层级: {chunk.level}
- 内容预览: {content_preview}

"""

        return slides_info

    def _parse_decision_response(self, response: str) -> Dict:
        """解析 LLM 决策响应"""
        # 尝试提取 JSON
        try:
            # 查找 JSON 块
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            elif "```" in response:
                json_start = response.find("```") + 3
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            else:
                json_str = response.strip()

            parsed = json.loads(json_str)
            return parsed
        except (json.JSONDecodeError, ValueError) as e:
            print(f"  [JSON 解析失败: {e}]")
            return {"analysis": "", "pages": []}

    def _fallback_decision(self, structure: DocumentStructure) -> Dict:
        """LLM 失败时的备用决策（简单规则）"""
        pages = []
        for i, chunk in enumerate(structure.chunks):
            # 简单规则：排除封面、目录
            exclude_keywords = ["封面", "目录", "致谢", "结束", "序言"]
            should_optimize = (
                not any(kw in chunk.title for kw in exclude_keywords)
                and len(chunk.content) > 50
                and chunk.level >= 2
            )

            pages.append({
                "slide_number": i,
                "title": chunk.title,
                "should_optimize": should_optimize,
                "reason": "备用规则决策" if should_optimize else "备用规则：不需要",
                "suggested_keywords": [],
                "optimization_strategy": ""
            })

        return {"analysis": "使用备用规则", "pages": pages}

    def get_global_context(self, structure: DocumentStructure, slide_number: int) -> str:
        """
        获取当前幻灯片的全局上下文

        Args:
            structure: 文档结构
            slide_number: 当前幻灯片编号

        Returns:
            全局上下文描述
        """
        chunks = structure.chunks
        n = len(chunks)

        context_parts = []

        # 课程信息
        context_parts.append(f"【课程】{structure.title}")
        if structure.author:
            context_parts.append(f"【授课教师】{structure.author}")

        # 教学流程
        flow = structure.get_teaching_chain()
        context_parts.append(f"【教学流程】{flow}")

        # 前一页
        if slide_number > 0:
            prev_chunk = chunks[slide_number - 1]
            context_parts.append(f"【前一页】{prev_chunk.title}")

        # 当前页
        current_chunk = chunks[slide_number]
        context_parts.append(f"【当前页】{current_chunk.title}（{self._get_level_name(current_chunk.level)}）")

        # 后一页
        if slide_number < n - 1:
            next_chunk = chunks[slide_number + 1]
            context_parts.append(f"【后一页】{next_chunk.title}")

        return "\n".join(context_parts)

    def _get_level_name(self, level: int) -> str:
        """获取层级名称"""
        level_names = {1: "章", 2: "节", 3: "小节", 4: "知识点"}
        return level_names.get(level, "内容")

    def generate_slide_prompt(
        self,
        structure: DocumentStructure,
        slide_number: int,
        policy_content: Optional[Dict] = None,
        insertion_strategy: str = ""
    ) -> str:
        """
        生成用于单页幻灯片内容生成的 Prompt

        Args:
            structure: 文档结构
            slide_number: 幻灯片编号
            policy_content: 思政内容（可选）
            insertion_strategy: LLM 建议的融入策略（可选）

        Returns:
            完整的 Prompt
        """
        chunk = structure.chunks[slide_number]
        global_context = self.get_global_context(structure, slide_number)

        prompt = f"""# 幻灯片内容生成任务

{global_context}

## 原始内容

**标题**: {chunk.title}
**层级**: {chunk.level}
**内容**:
```
{chunk.content}
```
"""

        if policy_content:
            prompt += f"""

## 思政融合点

**思政主题**: {policy_content.get('title', '')}
**思政内容**: {policy_content.get('content', '')}
"""

            if insertion_strategy:
                prompt += f"""
**融入策略**: {insertion_strategy}
"""

            prompt += """

请将上述思政内容自然融入本页幻灯片中，要求：
1. 保持专业知识的准确性和完整性
2. 思政元素要自然融入，不生硬
3. 可以通过案例、引言、问题引导等方式融入
"""

        prompt += """

## 输出要求

请按以下格式输出：

**标题**: [优化后的标题]
**内容**: [融合后的内容，使用 Markdown 格式]
**思政融合说明**: [说明思政内容如何融入，如果没有则填"无"]
"""

        return prompt

    # ============ 已移除的硬编码方法 ============
    # _identify_key_slides
    # _get_insertion_reason
    # _suggest_keywords
    # 这些功能现在由 LLM 在 decide_insertion_points 中完成


if __name__ == "__main__":
    """
    测试入口 - 使用 LLM 决策哪些页面需要优化

    输入: MinerU_markdown_1.导言_pages.json
    输出: tmp/ 目录下的决策结果

    运行方式:
        python -m src.preparation.logic.lesson_planner
    """
    import json
    import sys
    from pathlib import Path

    # 添加项目根目录到路径
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

    # 配置
    INPUT_JSON = "/home/guoziyang/AIgorithm_Agent/src/preparation/parser/tmp/WEEK1-1 Chap01-25-1_pages.json"
    OUTPUT_DIR = Path("/home/guoziyang/AIgorithm_Agent/src/preparation/logic/tmp")

    # 创建输出目录
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("教学链路规划器 - LLM 决策测试")
    print("=" * 60)
    print(f"输入: {INPUT_JSON}")
    print(f"输出: {OUTPUT_DIR}")
    print("-" * 60)

    # 加载页面数据
    with open(INPUT_JSON, 'r', encoding='utf-8') as f:
        pages = json.load(f)

    print(f"\n加载了 {len(pages)} 个页面")

    # 转换为 DocumentStructure (已在文件顶部导入)

    structure = DocumentStructure(
        title=pages[0].get("title", "未命名课件") if pages else "未命名课件",
        author="",
        institution="",
        chunks=[],
        outline=[]
    )

    for page in pages:
        # 推断层级
        title = page.get("title", "")
        if title.startswith("# ") or title.startswith("第一讲") or title.startswith("一、"):
            level = 1
        elif "、" in title[:3] or title.startswith("（") or title.startswith("(2)"):
            level = 2
        else:
            level = 2

        chunk = SlideChunk(
            title=title,
            content=page.get("content", ""),
            level=level,
            slide_number=page.get("page_number", 0),
            keywords=[],
            images=[],
            subsections=[]
        )
        structure.chunks.append(chunk)

    print(f"课程标题: {structure.title}")
    print(f"教学链路: {structure.get_teaching_chain()}")

    # 使用 LLM 决策
    print("\n[LLM 决策中...]")

    planner = LessonPlanner()
    insertion_points = planner.decide_insertion_points(structure=structure,user_prompt="请侧重算法伦理方面的思政内容")

    # 统计
    should_optimize_count = sum(1 for p in insertion_points if p.should_optimize)
    print(f"\n决策结果:")
    print(f"  总页面: {len(insertion_points)}")
    print(f"  需要优化: {should_optimize_count} 页")
    print(f"  不需要: {len(insertion_points) - should_optimize_count} 页")

    # 打印详细结果
    print(f"\n详细决策:")
    for point in insertion_points:
        status = "✓ 需要优化" if point.should_optimize else "  不需要"
        print(f"  [{status}] 页面 {point.slide_number}: {point.title}")
        if point.should_optimize:
            print(f"         原因: {point.reason}")
            if point.suggested_keywords:
                print(f"         关键词: {', '.join(point.suggested_keywords)}")
            if point.optimization_strategy:
                print(f"         优化策略: {point.optimization_strategy}")

    # 保存结果
    output_file = OUTPUT_DIR / "decision_result.json"

    # 转换为可序列化的格式
    result_data = {
        "input_file": INPUT_JSON,
        "total_pages": len(insertion_points),
        "should_optimize_count": should_optimize_count,
        "teaching_chain": structure.get_teaching_chain(),
        "decisions": [
            {
                "slide_number": p.slide_number,
                "title": p.title,
                "should_optimize": p.should_optimize,
                "reason": p.reason,
                "suggested_keywords": p.suggested_keywords,
                "optimization_strategy": p.optimization_strategy
            }
            for p in insertion_points
        ]
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)

    print(f"\n结果已保存: {output_file}")

    # 同时保存一个可读的 Markdown 版本
    md_file = OUTPUT_DIR / "decision_result.md"
    md_content = f"# 页面优化决策结果\n\n"
    md_content += f"## 课程信息\n\n"
    md_content += f"- 标题: {structure.title}\n"
    md_content += f"- 总页数: {len(insertion_points)}\n"
    md_content += f"- 需要优化: {should_optimize_count} 页\n"
    md_content += f"- 教学链路: {structure.get_teaching_chain()}\n\n"
    md_content += f"## 详细决策\n\n"

    for point in insertion_points:
        if point.should_optimize:
            md_content += f"### ✓ 页面 {point.slide_number}: {point.title}\n\n"
            md_content += f"- **原因**: {point.reason}\n"
            if point.suggested_keywords:
                md_content += f"- **关键词**: {', '.join(point.suggested_keywords)}\n"
            if point.optimization_strategy:
                md_content += f"- **优化策略**: {point.optimization_strategy}\n"
            md_content += "\n"

    md_file.write_text(md_content, encoding='utf-8')
    print(f"Markdown 版本: {md_file}")

    print("=" * 60)
