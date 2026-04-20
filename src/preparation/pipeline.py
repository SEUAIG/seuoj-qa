# -*- coding: utf-8 -*-
"""
课程备课智能体 - 统一流水线

将所有模块串联起来，提供完整的数据处理流程。

支持两种输入模式：
1. 从 Markdown 文件开始 → 解析 → 分页 → 优化 → 输出 Marp/JSON
2. 从 _pages.json 开始 → 直接优化 → 输出 Marp/JSON

使用示例：
    # 从 Markdown 开始
    python -m src.preparation.pipeline --input input/MinerU_markdown_1.导言.md

    # 从 JSON 开始
    python -m src.preparation.pipeline --input src/preparation/parser/tmp/MinerU_markdown_1.导言_pages.json

    # 只分析不生成
    python -m src.preparation.pipeline --input xxx.md --analyze-only

    # 生成 Prompt 不调用 LLM
    python -m src.preparation.pipeline --input xxx.md --prompts-only
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Literal
from dataclasses import dataclass, field

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.preparation.parser.document_splitter import DocumentSplitter
from src.preparation.retrieval.keyword_extractor import KeywordExtractor
from src.preparation.retrieval.policy_fetcher import PolicyFetcher
from src.preparation.retrieval.reranker import SemanticReranker
from src.preparation.logic.lesson_planner import LessonPlanner
from src.preparation.logic.content_generator import ContentGenerator
from src.preparation.logic.style_adapter import StyleAdapter
from src.preparation.logic.page_optimizer import PageOptimizer, OptimizedPage
from src.preparation.marp.marp_generator import MarpGenerator
from src.preparation.config import get_data_dir


@dataclass
class PipelineResult:
    """流水线执行结果"""
    input_file: str
    output_dir: str
    total_pages: int
    pages_with_policy: int
    output_files: List[str] = field(default_factory=list)
    teaching_chain: str = ""
    analysis: Dict = field(default_factory=dict)


class LessonPreparationPipeline:
    """
    课程备课智能体流水线

    完整流程：
    1. 输入层：解析 PPT/Markdown → 分页
    2. 检索层：提取关键词 → 获取思政内容 → 语义重排序
    3. 逻辑层：教学链路规划 → 页面优化 → 内容生成
    4. 输出层：生成 Marp Markdown → 转换 PPT/PDF
    """

    def __init__(
        self,
        output_dir: str = None,
        llm_model=None,
        use_cache: bool = True
    ):
        """
        初始化流水线

        Args:
            output_dir: 输出目录
            llm_model: LLM 模型实例
            use_cache: 是否使用缓存
        """
        # 目录设置
        self.output_dir = Path(output_dir) if output_dir else get_data_dir("output")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 初始化各层模块
        self._init_modules(llm_model)

        self.use_cache = use_cache

    def _init_modules(self, llm_model):
        """初始化所有模块"""
        # 输入层
        self.splitter = DocumentSplitter()

        # 检索层
        self.keyword_extractor = KeywordExtractor(model=llm_model)
        self.policy_fetcher = PolicyFetcher(cache_dir=str(get_data_dir("policies")))
        self.reranker = SemanticReranker(model=llm_model)

        # 逻辑层
        self.lesson_planner = LessonPlanner()
        self.content_generator = ContentGenerator(model=llm_model)
        self.style_adapter = StyleAdapter()
        self.page_optimizer = PageOptimizer(model=llm_model)

        # 输出层
        self.marp_generator = MarpGenerator()

    def run_from_markdown(
        self,
        markdown_file: str,
        mode: Literal["full", "analyze", "prompts"] = "full",
        limit: int = None
    ) -> PipelineResult:
        """
        从 Markdown 文件开始处理

        Args:
            markdown_file: Markdown 文件路径
            mode: 处理模式
                - "full": 完整流程，调用 LLM 生成内容
                - "analyze": 仅分析文档结构
                - "prompts": 生成 Prompt，不调用 LLM
            limit: 限制处理的页面数量

        Returns:
            PipelineResult
        """
        print(f"\n{'='*60}")
        print(f"课程备课智能体流水线")
        print(f"{'='*60}")
        print(f"输入文件: {markdown_file}")
        print(f"处理模式: {mode}")
        print(f"{'='*60}\n")

        result = PipelineResult(
            input_file=markdown_file,
            output_dir=str(self.output_dir)
        )

        # ========== 第一阶段：输入层 - 解析与分页 ==========
        print("[1/5] 解析文档结构...")
        structure = self.splitter.parse_file(markdown_file)

        print(f"      课程标题: {structure.title}")
        print(f"      授课教师: {structure.author or '未知'}")
        print(f"      总页数: {len(structure.chunks)}")

        result.teaching_chain = structure.get_teaching_chain()
        print(f"      教学流程: {result.teaching_chain}\n")

        # ========== 第二阶段：逻辑层 - 教学链路规划 ==========
        print("[2/5] 规划教学链路...")
        planning_result = self.lesson_planner.plan_teaching_chain(structure)

        # 决策思政内容插入点
        insertion_points = self.lesson_planner.decide_insertion_points(structure)
        print(f"      识别到 {len(insertion_points)} 个潜在思政融合点")

        should_insert_count = sum(1 for p in insertion_points if p.should_insert)
        print(f"      计划插入: {should_insert_count} 个页面\n")

        result.analysis = {
            "structure": planning_result,
            "insertion_points": [
                {
                    "slide_number": p.slide_number,
                    "title": p.title,
                    "should_insert": p.should_insert,
                    "reason": p.reason,
                    "suggested_keywords": p.suggested_keywords
                }
                for p in insertion_points
            ]
        }

        # 仅分析模式
        if mode == "analyze":
            self._save_analysis(result)
            return result

        # ========== 第三阶段：检索层 - 获取思政内容 ==========
        print("[3/5] 检索思政内容...")

        # 构建页面到思政内容的映射
        policy_mapping = {}
        for point in insertion_points:
            if point.should_insert:
                chunk = structure.chunks[point.slide_number]

                # 提取关键词
                keywords = point.suggested_keywords
                if not keywords:
                    keywords = self.lesson_planner._suggest_keywords(chunk)

                # 获取思政内容
                policies = self.policy_fetcher.fetch_by_keywords(keywords, limit=3)

                # 语义重排序
                if len(policies) > 1:
                    policies = self.reranker.select_best(
                        chunk.content,
                        policies,
                        top_k=1
                    )

                if policies:
                    policy_mapping[point.slide_number] = policies[0]
                    print(f"      第{point.slide_number}页 ({chunk.title}): {policies[0]['title']}")

        print(f"\n      成功匹配 {len(policy_mapping)} 个思政内容\n")

        result.pages_with_policy = len(policy_mapping)
        result.total_pages = len(structure.chunks)

        # 仅生成 Prompt 模式
        if mode == "prompts":
            prompts = self.content_generator.batch_generate_prompts(
                structure, policy_mapping
            )
            self._save_prompts(result, prompts)
            return result

        # ========== 第四阶段：逻辑层 - 分析教师风格 ==========
        print("[4/5] 分析教师风格...")
        teacher_style = self.style_adapter.analyze_from_chunks(structure.chunks)
        style_desc = self._describe_style(teacher_style)
        print(f"      风格特征: {style_desc}\n")

        # ========== 第五阶段：逻辑层 - 生成内容 ==========
        print("[5/5] 生成优化内容...")

        def progress_callback(current, total, info):
            status = "(含思政)" if info.get('has_policy') else ""
            print(f"      [{current}/{total}] {info['title']} {status}")

        generated_slides = self.content_generator.generate_lesson(
            structure,
            policy_mapping,
            teacher_style,
            progress_callback
        )

        # 应用限制
        if limit:
            generated_slides = generated_slides[:limit]
            result.total_pages = limit

        print()

        # ========== 输出层：保存结果 ==========
        output_files = self._save_generation_result(result, generated_slides, structure)
        result.output_files = output_files

        print(f"{'='*60}")
        print(f"流水线执行完成!")
        print(f"  处理页面: {result.total_pages}")
        print(f"  含思政: {result.pages_with_policy} 页")
        print(f"  输出目录: {self.output_dir}")
        print(f"{'='*60}\n")

        return result

    def run_from_json(
        self,
        json_file: str,
        mode: Literal["full", "analyze"] = "full",
        limit: int = None
    ) -> PipelineResult:
        """
        从分页 JSON 文件开始处理

        Args:
            json_file: 分页 JSON 文件路径（如 xxx_pages.json）
            mode: 处理模式
            limit: 限制处理的页面数量

        Returns:
            PipelineResult
        """
        print(f"\n{'='*60}")
        print(f"课程备课智能体流水线 (从 JSON 开始)")
        print(f"{'='*60}")
        print(f"输入文件: {json_file}")
        print(f"处理模式: {mode}")
        print(f"{'='*60}\n")

        # 加载分页数据
        with open(json_file, 'r', encoding='utf-8') as f:
            pages = json.load(f)

        print(f"[信息] 加载了 {len(pages)} 个页面\n")

        result = PipelineResult(
            input_file=json_file,
            output_dir=str(self.output_dir),
            total_pages=len(pages)
        )

        # 仅分析模式
        if mode == "analyze":
            result.teaching_chain = " → ".join([p["title"] for p in pages[:6]])
            result.analysis = {"pages": pages}
            self._save_analysis(result)
            return result

        # 构建教学链路
        teaching_chain = " → ".join([p["title"] for p in pages[:6]])
        result.teaching_chain = teaching_chain

        # 使用 PageOptimizer 批量优化
        print("[处理] 开始优化页面内容...\n")

        def progress_callback(current, total, info):
            status = "(含思政)" if info.get('has_policy') else ""
            print(f"  [{current}/{total}] {info['title']} {status}")

        optimized_pages = self.page_optimizer.optimize_pages(
            pages,
            teaching_chain,
            progress_callback
        )

        # 应用限制
        if limit:
            optimized_pages = optimized_pages[:limit]
            result.total_pages = limit

        result.pages_with_policy = sum(1 for p in optimized_pages if p.has_policy)

        print()

        # 保存结果
        output_files = self._save_optimized_result(result, optimized_pages)
        result.output_files = output_files

        print(f"{'='*60}")
        print(f"流水线执行完成!")
        print(f"  处理页面: {result.total_pages}")
        print(f"  含思政: {result.pages_with_policy} 页")
        print(f"  输出目录: {self.output_dir}")
        print(f"{'='*60}\n")

        return result

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

    def _save_analysis(self, result: PipelineResult):
        """保存分析结果"""
        input_name = Path(result.input_file).stem
        analysis_file = self.output_dir / f"{input_name}_analysis.json"

        analysis_file.write_text(
            json.dumps(result.analysis, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print(f"\n[保存] 分析结果: {analysis_file}")

    def _save_prompts(self, result: PipelineResult, prompts: List):
        """保存 Prompt 结果"""
        input_name = Path(result.input_file).stem

        # JSON 格式
        json_file = self.output_dir / f"{input_name}_prompts.json"
        json_file.write_text(
            json.dumps(prompts, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        # Markdown 格式
        md_file = self.output_dir / f"{input_name}_prompts.md"
        with open(md_file, 'w', encoding='utf-8') as f:
            for item in prompts:
                f.write(f"\n\n{'='*60}\n")
                f.write(f"第 {item['slide_number']+1} 页: {item['title']}\n")
                f.write(f"{'='*60}\n\n")
                f.write(item['prompt'])

        print(f"\n[保存] Prompts (JSON): {json_file}")
        print(f"[保存] Prompts (MD): {md_file}")

    def _save_generation_result(
        self,
        result: PipelineResult,
        slides: List[Dict],
        structure=None
    ) -> List[str]:
        """保存生成结果"""
        input_name = Path(result.input_file).stem
        output_files = []

        # 1. 保存 JSON 格式
        json_file = self.output_dir / f"{input_name}_generated.json"
        json_file.write_text(
            json.dumps(slides, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        output_files.append(str(json_file))
        print(f"[保存] JSON: {json_file}")

        # 2. 生成 Marp Markdown
        metadata = None
        if structure:
            metadata = {
                "title": structure.title,
                "author": structure.author,
                "institution": structure.institution
            }

        marp_content = self.marp_generator.generate(slides, metadata)
        marp_file = self.output_dir / f"{input_name}_marp.md"
        marp_file.write_text(marp_content, encoding="utf-8")
        output_files.append(str(marp_file))
        print(f"[保存] Marp: {marp_file}")

        return output_files

    def _save_optimized_result(
        self,
        result: PipelineResult,
        pages: List[OptimizedPage]
    ) -> List[str]:
        """保存优化结果（从 JSON 输入）"""
        input_name = Path(result.input_file).stem.replace("_pages", "")
        output_files = []

        # 1. 保存 JSON 格式
        json_file = self.output_dir / f"{input_name}_optimized.json"
        self.page_optimizer.save_results(pages, str(json_file), format="json")
        output_files.append(str(json_file))
        print(f"[保存] JSON: {json_file}")

        # 2. 保存 Marp Markdown
        marp_file = self.output_dir / f"{input_name}_optimized_marp.md"
        self.page_optimizer.save_results(pages, str(marp_file), format="marp")
        output_files.append(str(marp_file))
        print(f"[保存] Marp: {marp_file}")

        return output_files


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="课程备课智能体 - 统一流水线",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 从 Markdown 开始，完整流程
  python -m src.preparation.pipeline --input input/xxx.md

  # 从 JSON 开始，完整流程
  python -m src.preparation.pipeline --input xxx_pages.json

  # 仅分析不生成
  python -m src.preparation.pipeline --input xxx.md --analyze-only

  # 生成 Prompt 不调用 LLM
  python -m src.preparation.pipeline --input xxx.md --prompts-only

  # 限制处理页数
  python -m src.preparation.pipeline --input xxx.md --limit 5
        """
    )

    parser.add_argument(
        "--input", "-i",
        required=True,
        help="输入文件路径（Markdown 或 _pages.json）"
    )
    parser.add_argument(
        "--output", "-o",
        help="输出目录（默认：data/preparation/output）"
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        help="限制处理的页面数量"
    )
    parser.add_argument(
        "--analyze-only", "-a",
        action="store_true",
        help="仅分析文档结构，不生成内容"
    )
    parser.add_argument(
        "--prompts-only", "-p",
        action="store_true",
        help="仅生成 Prompt，不调用 LLM"
    )

    args = parser.parse_args()

    # 确定输入文件类型
    input_path = PROJECT_ROOT / args.input
    if not input_path.exists():
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"错误: 文件不存在 - {args.input}")
            return

    # 确定处理模式
    if args.analyze_only:
        mode = "analyze"
    elif args.prompts_only:
        mode = "prompts"
    else:
        mode = "full"

    # 创建流水线
    pipeline = LessonPreparationPipeline(output_dir=args.output)

    # 根据输入文件类型选择流程
    if input_path.suffix == ".json" or "_pages.json" in input_path.name:
        # 从 JSON 开始
        result = pipeline.run_from_json(
            str(input_path),
            mode=mode,
            limit=args.limit
        )
    else:
        # 从 Markdown 开始
        result = pipeline.run_from_markdown(
            str(input_path),
            mode=mode,
            limit=args.limit
        )


if __name__ == "__main__":
    main()
