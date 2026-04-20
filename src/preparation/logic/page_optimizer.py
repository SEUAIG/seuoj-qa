# -*- coding: utf-8 -*-
"""
页面内容优化器

基于分页的 JSON 数据，完成完整的优化流程：

1. 调用 lesson_planner.py：
   - 将 JSON 页面转换为 DocumentStructure
   - 分析教学链路
   - 决策哪些页面需要修改
   - 为每个需要修改的页面提供建议（关键词、思政内容）

2. 调用 content_generator.py：
   - 根据决策结果，对需要修改的页面进行内容生成
   - 保持不需要修改的页面原样

优化思路（来自项目需求文档）：
1. 局部修改：根据标题明确教学链路，AI 决策思政插入位置
2. 上下文模式：一次调用生成一页 + 局部上下文模式
3. Marp 格式生成：强制输出符合 Marp 语法的 Markdown
4. 教师风格迁移：根据原内容判断风格，调整生成风格
"""

import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

from .lesson_planner import LessonPlanner, OptimizationPoint
from .content_generator import ContentGenerator
from .style_adapter import StyleAdapter
from ..parser.document_splitter import DocumentStructure, SlideChunk
from ..retrieval.policy_fetcher import PolicyFetcher


@dataclass
class OptimizationPlan:
    """优化方案"""
    page_number: int
    title: str
    should_modify: bool
    reason: str
    suggested_keywords: List[str] = field(default_factory=list)
    policy_content: Optional[Dict] = None
    modification_type: str = "none"  # none, minor, major
    insertion_strategy: str = ""  # LLM 建议的融入策略


@dataclass
class OptimizedPage:
    """优化后的页面"""
    page_number: int
    original_title: str
    optimized_title: str
    content: str
    si_zheng_note: str
    has_policy: bool = False
    policy_title: str = ""
    modification_type: str = "none"  # none, minor, major
    keywords: List[str] = field(default_factory=list)  # 检索使用的关键词
    evidence_used: List[Dict] = field(default_factory=list)  # 检索引用的来源信息


class PageOptimizer:
    """
    页面内容优化器

    流程：
        1. 使用 LessonPlanner 分析并决策
        2. 使用 ContentGenerator 生成内容
    """

    def __init__(self, model=None):
        """
        初始化优化器

        Args:
            model: LLM 模型实例
        """
        # 初始化各模块
        self.lesson_planner = LessonPlanner()
        self.content_generator = ContentGenerator(model=model)
        self.style_adapter = StyleAdapter()
        self.policy_fetcher = PolicyFetcher()

        # 存储分析结果
        self.structure: Optional[DocumentStructure] = None
        self.optimization_plan: List[OptimizationPlan] = []
        self.teacher_style: Dict = {}

    def analyze_pages(
        self,
        pages: List[Dict]
    ) -> Tuple[List[OptimizationPlan], DocumentStructure]:
        """
        第一步：分析页面，生成优化方案

        调用 lesson_planner.py 的功能：
        - 将 JSON 页面转换为 DocumentStructure
        - 分析教学链路
        - 决策哪些页面需要修改
        - 为每个需要修改的页面提供建议

        Args:
            pages: 页面列表（来自 _pages.json）

        Returns:
            (优化方案列表, 文档结构)
        """
        print("\n[第一步] 分析页面结构...")

        # 1. 将 JSON 页面转换为 DocumentStructure
        self.structure = self._pages_to_structure(pages)

        print(f"  - 课程标题: {self.structure.title}")
        print(f"  - 总页数: {len(self.structure.chunks)}")
        print(f"  - 教学链路: {self.structure.get_teaching_chain()}")

        # 2. 使用 LessonPlanner 决策插入点
        insertion_points = self.lesson_planner.decide_insertion_points(self.structure)

        print(f"\n  - 识别到 {len(insertion_points)} 个潜在修改点")

        # 3. 为每个需要修改的页面获取思政内容
        plan_list = []
        for point in insertion_points:
            chunk = self.structure.chunks[point.slide_number]

            # 获取关键词（LLM 已经在决策时提供）
            keywords = point.suggested_keywords

            # 获取思政内容
            policy_content = None
            if point.should_optimize and keywords:
                policies = self.policy_fetcher.fetch_by_keywords(keywords, limit=1)
                policy_content = policies[0] if policies else None

            # 确定修改类型
            if point.should_optimize and policy_content:
                modification_type = "major" if len(chunk.content) > 100 else "minor"
            else:
                modification_type = "none"

            plan = OptimizationPlan(
                page_number=point.slide_number,
                title=point.title,
                should_modify=point.should_optimize and policy_content is not None,
                reason=point.reason,
                suggested_keywords=keywords,
                policy_content=policy_content,
                modification_type=modification_type,
                insertion_strategy=point.optimization_strategy  # 保存 LLM 建议的优化策略
            )
            plan_list.append(plan)

        self.optimization_plan = plan_list

        # 打印优化方案
        print(f"\n  优化方案:")
        for plan in plan_list:
            if plan.should_modify:
                print(f"    [{plan.page_number}] {plan.title}")
                print(f"           原因: {plan.reason}")
                print(f"           关键词: {', '.join(plan.suggested_keywords) if plan.suggested_keywords else '无'}")
                print(f"           思政: {plan.policy_content['title'] if plan.policy_content else '无'}")
                if plan.insertion_strategy:
                    print(f"           优化策略: {plan.insertion_strategy}")

        modify_count = sum(1 for p in plan_list if p.should_modify)
        print(f"\n  - 计划修改: {modify_count} 页")
        print(f"  - 保持原样: {len(plan_list) - modify_count} 页")

        return plan_list, self.structure

    def generate_content(
        self,
        pages: List[Dict],
        decision_json: str = None,
        retrieval_json: str = None,
        callback=None
    ) -> List[OptimizedPage]:
        """
        第二步：根据优化方案生成内容

        调用 content_generator.py 的功能：
        - 对需要修改的页面，使用 LLM 生成优化内容
        - 对不需要修改的页面，保持原样

        Args:
            pages: 原始页面列表
            decision_json: 决策结果 JSON 文件路径（可选，通过 session 传入）
            retrieval_json: 检索结果 JSON 文件路径（可选，通过 session 传入）
            callback: 进度回调函数 callback(current, total, info)

        Returns:
            优化后的页面列表
        """
        print("\n[第二步] 生成优化内容...")

        # 分析教师风格
        self.teacher_style = self.style_adapter.analyze_from_chunks(self.structure.chunks)
        style_desc = self._describe_style(self.teacher_style)
        print(f"  - 教师风格: {style_desc}")

        # 准备临时文件供 optimize_by_decision 使用
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            # 1. 保存原始页面为临时 JSON
            pages_json = os.path.join(tmpdir, "pages.json")
            with open(pages_json, 'w', encoding='utf-8') as f:
                json.dump(pages, f, ensure_ascii=False, indent=2)

            # 2. 处理决策信息：优先使用传入的 decision_json，否则从 self.optimization_plan 构建
            if decision_json and os.path.exists(decision_json):
                print(f"  - 使用已有决策文件: {decision_json}")
                # 直接使用决策文件
                decision_file = decision_json
            else:
                # 从 self.optimization_plan 构建决策 JSON
                decisions = []
                for plan in self.optimization_plan:
                    decision = {
                        "slide_number": plan.page_number,
                        "should_optimize": plan.should_modify,
                        "reason": plan.reason,
                        "suggested_keywords": plan.suggested_keywords,
                        "optimization_strategy": plan.insertion_strategy,
                        "modification_type": plan.modification_type
                    }
                    decisions.append(decision)

                decision_file = os.path.join(tmpdir, "decision.json")
                with open(decision_file, 'w', encoding='utf-8') as f:
                    json.dump({"decisions": decisions}, f, ensure_ascii=False, indent=2)

            # 3. 调用 ContentGenerator.optimize_by_decision
            print(f"\n  开始生成...")
            # 读取检索信息
            retrieval_info = {}
            if retrieval_json and os.path.exists(retrieval_json):
                print(f"  - 使用检索文件: {retrieval_json}")
                with open(retrieval_json, 'r', encoding='utf-8') as f:
                    retrieval_data = json.load(f)
                # 解析每个决策的 keywords_information
                for decision in retrieval_data.get("decisions", []):
                    slide_num = decision.get("slide_number")
                    keywords_info = decision.get("keywords_information", {})
                    keywords = list(keywords_info.keys())
                    # 收集 evidence 信息
                    evidence = []
                    for keyword, contents in keywords_info.items():
                        for item in contents:
                            evidence.append({
                                "keyword": keyword,
                                "title": item.get("title", ""),
                                "url": item.get("url", ""),
                                "relevance_score": item.get("relevance_score", 0)
                            })
                    retrieval_info[slide_num] = {
                        "keywords": keywords,
                        "evidence": evidence
                    }

            optimized_results = self.content_generator.optimize_by_decision(
                pages_json=pages_json,
                decision_json=decision_file,
                retrieval_json=retrieval_json,
                output_dir=tmpdir,
                callback=callback
            )

            # 4. 将结果转换为 OptimizedPage 格式
            result = []
            for slide in optimized_results:
                plan = self._get_plan_by_page_num(slide["slide_number"])
                policy_title = slide.get("policy_title", "") or (plan.policy_content["title"] if plan and plan.policy_content else "")

                # 获取检索信息
                slide_num = slide["slide_number"]
                retrieval_data = retrieval_info.get(slide_num, {})
                keywords = retrieval_data.get("keywords", [])
                evidence = retrieval_data.get("evidence", [])

                result.append(OptimizedPage(
                    page_number=slide["slide_number"],
                    original_title=slide.get("original_title", ""),
                    optimized_title=slide.get("optimized_title", ""),
                    content=slide.get("content", ""),
                    si_zheng_note=slide.get("si_zheng_note", "无"),
                    has_policy=slide.get("has_policy", False),
                    policy_title=policy_title,
                    modification_type=plan.modification_type if plan else "none",
                    keywords=keywords,
                    evidence_used=evidence
                ))

        return result

    def optimize_pages(
        self,
        pages: List[Dict],
        teaching_chain: str = "",
        decision_json: str = None,
        retrieval_json: str = None,
        callback=None
    ) -> List[OptimizedPage]:
        """
        完整流程：分析 + 生成

        这是主入口函数，串联 lesson_planner 和 content_generator

        Args:
            pages: 页面列表（来自 _pages.json）
            teaching_chain: 教学流程描述（可选，会自动生成）
            decision_json: 决策结果 JSON 文件路径（可选，通过 session 传入，跳过分析步骤）
            retrieval_json: 检索结果 JSON 文件路径（可选，通过 session 传入）
            callback: 进度回调函数

        Returns:
            优化后的页面列表
        """
        # 判断是否需要分析
        if decision_json:
            # 有决策文件：跳过分析，直接构建 structure
            print("\n[使用已有决策文件，跳过分析步骤]")
            self.structure = self._pages_to_structure(pages)
            print(f"  - 课程标题: {self.structure.title}")
            print(f"  - 总页数: {len(self.structure.chunks)}")
        else:
            # 无决策文件：执行完整分析
            plan_list, structure = self.analyze_pages(pages)

        # 第二步：生成
        result = self.generate_content(
            pages,
            decision_json=decision_json,
            retrieval_json=retrieval_json,
            callback=callback
        )

        return result

    # ========== 辅助方法 ==========

    def _pages_to_structure(self, pages: List[Dict]) -> DocumentStructure:
        """
        将 JSON 页面列表转换为 DocumentStructure

        这是适配层，让 lesson_planner 和 content_generator
        能够处理 _pages.json 格式的数据
        """
        # 创建一个假的 DocumentStructure
        structure = DocumentStructure(
            title=pages[0]["title"] if pages else "未命名课件",
            author="",
            institution="",
            chunks=[],
            outline=[]
        )

        # 将每个页面转换为 SlideChunk
        for page in pages:
            # 推断层级：简单规则
            title = page.get("title", "")
            content = page.get("content", "")

            # 一级标题判断
            if title.startswith("# ") or title.startswith("第一讲") or title.startswith("一、"):
                level = 1
            elif title.startswith("（") or title.startswith("(2)") or "、" in title[:3]:
                level = 2
            else:
                level = 2

            chunk = SlideChunk(
                title=title,
                content=content,
                level=level,
                slide_number=page.get("page_number", 0),
                keywords=[],
                images=[],
                subsections=[]
            )
            structure.chunks.append(chunk)

        # 生成大纲
        structure.outline = self._generate_outline(structure.chunks)

        return structure

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

    def _get_plan_by_page_num(self, page_number: int) -> Optional[OptimizationPlan]:
        """根据页码获取优化方案"""
        for plan in self.optimization_plan:
            if plan.page_number == page_number:
                return plan
        return None

    def _describe_style(self, style: Dict) -> str:
        """描述风格特征"""
        features = []
        if style.get("formal"):
            features.append("正式学术")
        if style.get("casual"):
            features.append("通俗易懂")
        if style.get("example_heavy"):
            features.append("重案例")
        if style.get("concise"):
            features.append("简洁")
        if style.get("detailed"):
            features.append("详尽")
        return "、".join(features) if features else "标准教学风格"

    def save_results(
        self,
        pages: List[OptimizedPage],
        output_path: str,
        format: str = "json"
    ) -> None:
        """
        保存优化结果

        Args:
            pages: 优化后的页面列表
            output_path: 输出文件路径
            format: 输出格式 (json/marp)
        """
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        if format == "json":
            data = [
                {
                    "page_number": p.page_number,
                    "original_title": p.original_title,
                    "optimized_title": p.optimized_title,
                    "content": p.content,
                    "si_zheng_note": p.si_zheng_note,
                    "has_policy": p.has_policy,
                    "policy_title": p.policy_title,
                    "modification_type": p.modification_type
                }
                for p in pages
            ]
            output.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )

        elif format == "marp":
            # 生成 Marp 格式 Markdown
            lines = []
            lines.append("---")
            lines.append("_class: lead_")
            lines.append("")
            lines.append(f"# {pages[0].optimized_title if pages else '课程'}")
            lines.append("")
            lines.append("---")

            for p in pages:
                if not p.content.strip():
                    continue

                lines.append("")
                lines.append(f"## 第 {p.page_number + 1} 页: {p.optimized_title}")
                lines.append("")
                lines.append(p.content)
                if p.has_policy:
                    lines.append("")
                    lines.append(f"> 💡 思政融合: {p.si_zheng_note}")
                lines.append("")
                lines.append("---")

            output.write_text("\n".join(lines), encoding="utf-8")

    def get_optimization_summary(self) -> Dict:
        """获取优化方案摘要"""
        if not self.optimization_plan:
            return {}

        return {
            "total_pages": len(self.optimization_plan),
            "should_modify": sum(1 for p in self.optimization_plan if p.should_modify),
            "keep_original": sum(1 for p in self.optimization_plan if not p.should_modify),
            "pages_with_policy": [
                {"page_number": p.page_number, "title": p.title, "policy": p.policy_content["title"] if p.policy_content else ""}
                for p in self.optimization_plan if p.should_modify
            ]
        }


# ========== 便捷函数 ==========

def optimize_from_json(
    json_path: str,
    output_path: str = None,
    format: str = "json"
) -> List[OptimizedPage]:
    """
    从分页 JSON 文件优化内容

    完整流程：
        1. 加载 JSON
        2. 调用 lesson_planner 分析并决策
        3. 调用 content_generator 生成内容
        4. 保存结果

    Args:
        json_path: 分页 JSON 文件路径
        output_path: 输出文件路径
        format: 输出格式 (json/marp)

    Returns:
        优化后的页面列表
    """
    # 加载分页数据
    with open(json_path, 'r', encoding='utf-8') as f:
        pages = json.load(f)

    print("=" * 60)
    print("页面内容优化器")
    print("=" * 60)
    print(f"输入: {json_path}")
    print(f"页数: {len(pages)}")
    print("-" * 60)

    # 创建优化器
    optimizer = PageOptimizer()

    def progress_callback(current, total, info):
        status = "(含思政)" if info.get('has_policy') else ""
        print(f"  [{current}/{total}] {info['title']} {status}")

    # 执行优化
    results = optimizer.optimize_pages(pages, callback=progress_callback)

    # 打印摘要
    summary = optimizer.get_optimization_summary()
    print("\n" + "-" * 60)
    print("优化摘要:")
    print(f"  总页数: {summary.get('total_pages', 0)}")
    print(f"  修改页数: {summary.get('should_modify', 0)}")
    print(f"  保持原样: {summary.get('keep_original', 0)}")
    print(f"  含思政内容: {len(summary.get('pages_with_policy', []))} 页")

    # 保存结果
    if output_path:
        optimizer.save_results(results, output_path, format)
        print(f"\n已保存: {output_path}")

    print("=" * 60)

    return results


if __name__ == "__main__":
    """
    Main function - hardcoded optimization test
    """
    INPUT_JSON = "/home/guoziyang/AIgorithm_Agent/src/preparation/parser/tmp/MinerU_markdown_1.导言_pages.json"
    OUTPUT_JSON = "/home/guoziyang/AIgorithm_Agent/input/MinerU_markdown_1.导言_optimized.json"
    OUTPUT_MARP = "/home/guoziyang/AIgorithm_Agent/input/MinerU_markdown_1.导言_optimized_marp.md"

    # 生成 JSON 格式
    results = optimize_from_json(INPUT_JSON, OUTPUT_JSON, format="json")

    # 生成 Marp 格式
    optimizer = PageOptimizer()
    optimizer.save_results(results, OUTPUT_MARP, format="marp")
    print(f"\n已保存 Marp 格式: {OUTPUT_MARP}")
