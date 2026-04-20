"""
逻辑模块 - 逻辑层

负责教学链路规划、内容生成和教师风格迁移。
"""

import json
from pathlib import Path
from typing import List, Dict, Optional

from .lesson_planner import LessonPlanner
from .content_generator import ContentGenerator
from .style_adapter import StyleAdapter
from .page_optimizer import PageOptimizer


__all__ = [
    "LessonPlanner",
    "ContentGenerator",
    "StyleAdapter",
    "PageOptimizer",
    "process_pages",  # 新增：统一处理函数
]


def process_pages(
    pages_json: str | List[Dict],
    output_path: Optional[str] = None,
    llm_model=None,
    verbose: bool = True
) -> List[Dict]:
    """
    统一处理函数：输入 _pages.json，输出优化后的 JSON

    这是 logic 层的统一入口，串联本目录下所有模块的功能。

    流程：
        1. PageOptimizer: 页面内容优化（核心）
        2. 内部会调用：
           - PolicyFetcher 获取思政内容
           - 提取关键词、匹配思政内容
           - 调用 LLM 生成优化内容

    Args:
        pages_json: 输入，可以是 JSON 文件路径或页面列表
        output_path: 输出文件路径（可选），不保存则只返回结果
        llm_model: LLM 模型实例（可选）
        verbose: 是否打印处理进度

    Returns:
        优化后的页面列表，格式：
        [
            {
                "page_number": 0,
                "original_title": "原标题",
                "optimized_title": "优化后标题",
                "content": "优化后内容",
                "si_zheng_note": "思政融合说明",
                "has_policy": true,
                "policy_title": "使用的思政主题"
            },
            ...
        ]

    Example:
        >>> from src.preparation.logic import process_pages
        >>>
        >>> # 方式1：直接传入文件路径
        >>> result = process_pages("xxx_pages.json", output_path="xxx_optimized.json")
        >>>
        >>> # 方式2：传入已加载的列表
        >>> with open("xxx_pages.json") as f:
        >>>     pages = json.load(f)
        >>> result = process_pages(pages)
    """
    # ========== 输入处理 ==========
    if isinstance(pages_json, str):
        # 从文件加载
        json_path = Path(pages_json)
        if not json_path.exists():
            raise FileNotFoundError(f"文件不存在: {pages_json}")

        with open(json_path, 'r', encoding='utf-8') as f:
            pages = json.load(f)

        if verbose:
            print(f"[输入] 从文件加载: {pages_json}")
            print(f"[输入] 共 {len(pages)} 个页面\n")
    else:
        # 直接使用传入的列表
        pages = pages_json

    if not isinstance(pages, list):
        raise TypeError("pages_json 必须是文件路径字符串或页面列表")

    # ========== 初始化模块 ==========
    optimizer = PageOptimizer(model=llm_model)

    # ========== 构建教学链路（用于上下文）==========
    teaching_chain = " → ".join([p.get("title", "") for p in pages[:6]])

    if verbose:
        print(f"[上下文] 教学链路: {teaching_chain}\n")
        print(f"[处理] 开始优化页面...\n")

    # ========== 进度回调函数 ==========
    def progress_callback(current: int, total: int, info: Dict):
        if verbose:
            status = "(含思政)" if info.get('has_policy') else ""
            print(f"  [{current}/{total}] {info['title']} {status}")

    # ========== 执行优化 ==========
    optimized_pages = optimizer.optimize_pages(
        pages=pages,
        teaching_chain=teaching_chain,
        callback=progress_callback
    )

    # ========== 统计信息 ==========
    total = len(optimized_pages)
    with_policy = sum(1 for p in optimized_pages if p.has_policy)

    if verbose:
        print()
        print(f"[完成] 共处理 {total} 个页面")
        print(f"[完成] 含思政内容: {with_policy} 页\n")

    # ========== 转换为字典格式输出 ==========
    result = [
        {
            "page_number": p.page_number,
            "original_title": p.original_title,
            "optimized_title": p.optimized_title,
            "content": p.content,
            "si_zheng_note": p.si_zheng_note,
            "has_policy": p.has_policy,
            "policy_title": p.policy_title
        }
        for p in optimized_pages
    ]

    # ========== 保存结果 ==========
    if output_path:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        if verbose:
            print(f"[保存] {output_path}")

    return result


def quick_optimize(
    json_file: str,
    output_file: str = None
) -> str:
    """
    快捷函数：输入 JSON 文件，输出 JSON 文件

    Args:
        json_file: 输入 JSON 文件路径
        output_file: 输出 JSON 文件路径（默认在输入文件同目录，添加 _optimized 后缀）

    Returns:
        输出文件路径

    Example:
        >>> from src.preparation.logic import quick_optimize
        >>>
        >>> result_path = quick_optimize("xxx_pages.json")
        >>> # 自动保存为 xxx_optimized.json
    """
    input_path = Path(json_file)

    # 默认输出路径
    if output_file is None:
        output_file = str(input_path.parent / f"{input_path.stem.replace('_pages', '')}_optimized.json")

    # 执行处理
    process_pages(
        pages_json=json_file,
        output_path=output_file,
        verbose=True
    )

    return output_file


if __name__ == "__main__":
    """
    测试入口

    使用方式：
        python -m src.preparation.logic
    """
    import sys

    # 默认测试文件
    DEFAULT_INPUT = "/home/guoziyang/AIgorithm_Agent/src/preparation/parser/tmp/MinerU_markdown_1.导言_pages.json"

    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = DEFAULT_INPUT

    print("=" * 60)
    print("逻辑层统一处理测试")
    print("=" * 60)

    result = quick_optimize(input_file)

    print("=" * 60)
    print(f"测试完成！结果已保存到: {result}")
