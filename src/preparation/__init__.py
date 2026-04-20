"""
课程备课智能体模块

提供智能备课功能，包括：
- 文档解析（MinerU）
- 思政内容检索
- 教学内容生成
- PPT生成（Marp格式）

使用示例：
    from src.preparation import LessonPreparationPipeline

    pipeline = LessonPreparationPipeline()
    result = pipeline.run_from_markdown("input/xxx.md")
    # 或
    result = pipeline.run_from_json("xxx_pages.json")
"""

__version__ = "0.1.0"

from .pipeline import LessonPreparationPipeline, PipelineResult

__all__ = ["LessonPreparationPipeline", "PipelineResult"]
