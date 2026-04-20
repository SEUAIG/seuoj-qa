# -*- coding: utf-8 -*-
"""
课程备课智能体 - API 接口封装

提供四个独立接口，串联解析、决策、检索、优化四个模块。
每步返回当前阶段结果，支持前端分步调用。
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Literal
from dataclasses import dataclass, asdict

from src.preparation.parser.ppt_parser import ppt_to_md,pdf_to_md
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


# ============== API 核心类 ==============

class LessonPreparationAPI:
    """
    课程备课 API 接口类

    提供四个独立方法，每步返回当前阶段结果：
    1. parse() - 解析文档结构
    2. decide() - 决策思政融合点
    3. retrieve() - 检索思政内容
    4. optimize() - 优化并生成内容
    """

    def __init__(self, llm_model=None, output_dir: str = None, use_cache: bool = True):
        """
        初始化 API

        Args:
            llm_model: LLM 模型实例
            output_dir: 输出目录
            use_cache: 是否使用缓存
        """
        self.output_dir = Path(output_dir) if output_dir else get_data_dir("output")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.llm_model = llm_model
        self.use_cache = use_cache

        # 初始化各层模块
        self._init_modules()

        # 存储中间状态，支持断点续传
        self._state = {
            "structure": None,        # 解析后的结构
            "insertion_points": None, # 决策结果
            "policy_mapping": None,   # 检索结果
            "retrieval_file": None,   # 检索结果文件
            "teacher_style": None,    # 教师风格
            "generated_slides": None  # 优化结果
        }

    def _init_modules(self):
        """初始化所有模块"""
        # 输入层
        self.splitter = DocumentSplitter()

        # 检索层
        self.keyword_extractor = KeywordExtractor(model=self.llm_model)
        self.policy_fetcher = PolicyFetcher(cache_dir=str(get_data_dir("policies")))
        self.reranker = SemanticReranker(model=self.llm_model)

        # 逻辑层
        self.lesson_planner = LessonPlanner()
        self.content_generator = ContentGenerator(model=self.llm_model)
        self.style_adapter = StyleAdapter()
        self.page_optimizer = PageOptimizer(model=self.llm_model)

        # 输出层
        self.marp_generator = MarpGenerator()

    # ============== 第一步：解析 ==============

    def parse(self, ppt_file: str = None, markdown_file: str = None, pdf_file: str = None) -> Dict:
        """
        解析 PPT 文档结构

        支持两种输入：
        1. PPT 文件 (.ppt/.pptx) - 自动转换为 Markdown 并解析
        2. Markdown 文件 - 直接解析
        3. pdf文件

        Args:
            ppt_file: PPT 文件路径 (优先级高于 markdown_file)
            markdown_file: Markdown 文件路径
            pdf_file: PDF 文件路径 (优先级高于 ppt_file)


        Returns:
            {
                "status": "success",
                "stage": "parse",
                "data": {
                    "title": "课程标题",
                    "author": "作者",
                    "total_pages": 10,
                    "teaching_chain": "导入 → 讲授 → 总结",
                    "pages": [
                        {"page_num": 1, "title": "xxx", "content": "xxx"},
                        ...
                    ],
                    "markdown_file": "/path/to/xxx.md",
                    "image_dir": "/path/to/xxx_img"
                }
            }
        """

        
        try:
            print("==== DEBUG ====")
            print("ppt_file =", ppt_file)
            print("pdf_file =", pdf_file)
            print("markdown_file =", markdown_file)

            if pdf_file:
                input_path = Path(pdf_file)

                if not input_path.exists():
                    return {
                        "status": "error",
                        "stage": "parse",
                        "message": f"PDF 文件不存在: {pdf_file}",
                        "error_code": "FILE_NOT_FOUND"
                    }

                # PDF → Markdown
                markdown_path = pdf_to_md(input_path)
                markdown_file = str(markdown_path)

                # 图片目录
                image_dir = str(input_path.parent / (input_path.stem + "_img"))

            # 确定输入类型
            elif ppt_file:
                input_path = Path(ppt_file)
                if not input_path.exists():
                    return {
                        "status": "error",
                        "stage": "parse",
                        "message": f"PPT 文件不存在: {ppt_file}",
                        "error_code": "FILE_NOT_FOUND"
                    }

                # PPT → Markdown
                markdown_path = ppt_to_md(input_path)
                markdown_file = str(markdown_path)

                # 图片目录
                image_dir = str(input_path.parent / (input_path.stem + "_img"))

            elif markdown_file:
                markdown_path = Path(markdown_file)
                if not markdown_path.exists():
                    return {
                        "status": "error",
                        "stage": "parse",
                        "message": f"Markdown 文件不存在: {markdown_file}",
                        "error_code": "FILE_NOT_FOUND"
                    }
                image_dir = str(markdown_path.parent / (markdown_path.stem + "_img"))

            else:
                return {
                    "status": "error",
                    "stage": "parse",
                    "message": "请提供 ppt_file 或 markdown_file 参数",
                    "error_code": "INVALID_INPUT"
                }

            # Markdown → 结构化
            structure = self.splitter.parse_file(markdown_file)
            teaching_chain = structure.get_teaching_chain()

            # 保存到状态
            self._state["structure"] = structure
            self._state["markdown_file"] = markdown_file
            self._state["image_dir"] = image_dir

            # 构建返回数据
            pages = []
            for i, chunk in enumerate(structure.chunks):
                pages.append({
                    "page_num": i,
                    "title": chunk.title,
                    "content": chunk.content[:500] + "..." if len(chunk.content) > 500 else chunk.content,
                    "level": chunk.level,
                    "images": chunk.images[:3] if chunk.images else []
                })

            return {
                "status": "success",
                "stage": "parse",
                "message": f"解析成功，共 {len(structure.chunks)} 页",
                "data": {
                    "title": structure.title,
                    "author": structure.author,
                    "institution": structure.institution,
                    "total_pages": len(structure.chunks),
                    "teaching_chain": teaching_chain,
                    "pages": pages,
                    "markdown_file": markdown_file,
                    "image_dir": image_dir if Path(image_dir).exists() else None
                }
            }

        except Exception as e:
            return {
                "status": "error",
                "stage": "parse",
                "message": f"解析失败: {str(e)}",
                "error_code": "PARSE_ERROR"
            }

    # ============== 第二步：决策 ==============

    def decide(self, structure: Dict = None, user_prompt: str = None) -> Dict:
        """
        决策思政融合点

        Args:
            structure: 可选，传入解析结果；如果不传则使用上一步结果
            user_prompt: 可选，用户自定义需求，如"侧重算法伦理"

        Returns:
            {
                "status": "success",
                "stage": "decide",
                "data": {
                    "total_pages": 10,
                    "insertion_points": [
                        {
                            "page_num": 2,
                            "title": "算法复杂度",
                            "should_insert": true,
                            "reason": "适合融入算法伦理",
                            "suggested_keywords": ["算法伦理", "技术责任"]
                        }
                    ],
                    "planned_policy_pages": 3
                }
            }
        """
        try:
            # 获取结构
            if structure:
                # 如果传入了新结构，解析它
                from src.preparation.parser.document_splitter import ParsedDocument
                doc = ParsedDocument(
                    title=structure.get("title", ""),
                    author=structure.get("author"),
                    institution=structure.get("institution"),
                    chunks=[]
                )
                for p in structure.get("pages", []):
                    from src.preparation.parser.document_splitter import TextChunk
                    doc.chunks.append(TextChunk(
                        title=p.get("title", ""),
                        content=p.get("content", ""),
                        page_num=p.get("page_num", 0)
                    ))
                self._state["structure"] = doc

            if not self._state["structure"]:
                return {
                    "status": "error",
                    "stage": "decide",
                    "message": "请先执行解析步骤",
                    "error_code": "NO_PARSE_RESULT"
                }

            structure = self._state["structure"]

            # 规划教学链路
            planning_result = self.lesson_planner.plan_teaching_chain(structure)

            # 决策思政插入点
            insertion_points = self.lesson_planner.decide_insertion_points(structure, user_prompt)

            # 保存到状态
            self._state["insertion_points"] = insertion_points

            # 保存决策结果为 JSON 文件（供后续 optimize 步骤使用）
            decision_data = []
            for p in insertion_points:
                decision_data.append({
                    "slide_number": p.slide_number,
                    "title": p.title,
                    "should_optimize": p.should_optimize,
                    "reason": p.reason,
                    "suggested_keywords": p.suggested_keywords or [],
                    "optimization_strategy": getattr(p, 'optimization_strategy', ''),
                    "modification_type": getattr(p, 'modification_type', 'none')
                })

            # 保存决策文件
            decision_file = self.output_dir / f"decision_{Path(structure.title or 'output').stem}.json"
            decision_file.write_text(json.dumps({"decisions": decision_data}, ensure_ascii=False, indent=2), encoding="utf-8")
            self._state["decision_file"] = str(decision_file)

            # 构建返回数据
            points_data = []
            for p in insertion_points:
                points_data.append({
                    "page_num": p.slide_number,
                    "title": p.title,
                    "should_optimize": p.should_optimize,
                    "reason": p.reason,
                    "suggested_keywords": p.suggested_keywords
                })

            planned_count = sum(1 for p in insertion_points if p.should_optimize)

            return {
                "status": "success",
                "stage": "decide",
                "message": f"决策完成，计划插入 {planned_count} 个思政页面",
                "data": {
                    "total_pages": len(structure.chunks),
                    "insertion_points": points_data,
                    "planned_policy_pages": planned_count
                }
            }

        except Exception as e:
            return {
                "status": "error",
                "stage": "decide",
                "message": f"决策失败: {str(e)}",
                "error_code": "DECIDE_ERROR"
            }

    # ============== 第三步：检索 ==============
    def retrieve(self) -> Dict:
        """检索思政内容（本地关键词检索 + 重排序）"""
        try:
            if not self._state["structure"]:
                return {
                    "status": "error",
                    "stage": "retrieve",
                    "message": "请先执行解析步骤",
                    "error_code": "NO_PARSE_RESULT"
                }

            if not self._state["insertion_points"]:
                return {
                    "status": "error",
                    "stage": "retrieve",
                    "message": "请先执行决策步骤",
                    "error_code": "NO_DECIDE_RESULT"
                }

            insertion_points = self._state["insertion_points"]
            structure = self._state["structure"]
            target_points = [p for p in insertion_points if p.should_optimize]

            if not target_points:
                return {
                    "status": "success",
                    "stage": "retrieve",
                    "message": "没有需要检索的页面",
                    "data": {
                        "matched_pages": 0,
                        "policy_mapping": {}
                    }
                }

            policy_mapping = {}
            total_contents = 0
            retrieval_decisions = []

            for point in target_points:
                slide_num = point.slide_number
                chunk = structure.chunks[slide_num] if 0 <= slide_num < len(structure.chunks) else None
                teaching_content = f"{point.title}\n{chunk.content if chunk else ''}".strip()

                keywords = point.suggested_keywords or []
                if not keywords:
                    try:
                        keywords = self.keyword_extractor.extract_keywords(teaching_content, top_k=3)
                    except Exception:
                        keywords = [point.title] if point.title else []

                candidates = self.policy_fetcher.fetch_by_keywords(keywords, limit=3)
                ranked = self.reranker.rerank(teaching_content, candidates) if candidates else []

                keywords_information = {}
                for keyword in keywords:
                    items = []
                    for rank, item in enumerate(ranked):
                        score = max(0.1, 1.0 - rank * 0.1)
                        items.append({
                            "title": item.get("title", ""),
                            "content": item.get("content", ""),
                            "url": item.get("url", ""),
                            "source": item.get("source", "local"),
                            "relevance_score": score
                        })
                    keywords_information[keyword] = items

                retrieval_decisions.append({
                    "slide_number": slide_num,
                    "title": point.title,
                    "keywords_information": keywords_information
                })

                if ranked:
                    best_content = ranked[0]
                    policy_mapping[slide_num] = {
                        "title": best_content.get("title", ""),
                        "content": best_content.get("content", "")[:500] if best_content.get("content") else "",
                        "url": best_content.get("url", ""),
                        "relevance_score": 1.0,
                        "keyword": keywords[0] if keywords else ""
                    }
                    total_contents += 1

            retrieval_output = {"decisions": retrieval_decisions}
            retrieval_file = self.output_dir / f"retrieval_{Path(structure.title or 'output').stem}.json"
            retrieval_file.write_text(
                json.dumps(retrieval_output, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )

            self._state["policy_mapping"] = policy_mapping
            self._state["retrieval_file"] = str(retrieval_file)

            mapping_data = {}
            for page_num, policy in policy_mapping.items():
                mapping_data[str(page_num)] = {
                    "title": policy.get("title"),
                    "content": policy.get("content", ""),
                    "url": policy.get("url"),
                    "relevance_score": policy.get("relevance_score"),
                    "keyword": policy.get("keyword")
                }

            return {
                "status": "success",
                "stage": "retrieve",
                "message": f"检索完成，成功获取 {len(policy_mapping)} 个页面的思政内容",
                "data": {
                    "matched_pages": len(policy_mapping),
                    "total_contents": total_contents,
                    "retrieval_output_file": str(retrieval_file),
                    "policy_mapping": mapping_data
                }
            }

        except Exception as e:
            return {
                "status": "error",
                "stage": "retrieve",
                "message": f"检索失败: {str(e)}",
                "error_code": "RETRIEVAL_ERROR"
            }

    # ============== 第四步：优化 ==============

    def optimize(
        self,
        mode: Literal["full", "prompts"] = "full",
        limit: int = None
    ) -> Dict:
        """
        优化并生成内容

        Args:
            mode: full - 完整生成; prompts - 只生成 prompts
            limit: 可选，限制处理页数

        Returns:
            {
                "status": "success",
                "stage": "optimize",
                "data": {
                    "total_pages": 10,
                    "pages_with_policy": 3,
                    "output_files": {
                        "json": "/path/to/xxx_generated.json",
                        "marp": "/path/to/xxx_marp.md"
                    },
                    "preview": [
                        {"page_num": 1, "title": "xxx", "content": "..."}
                    ]
                }
            }
        """
        try:
            if not self._state["structure"]:
                return {
                    "status": "error",
                    "stage": "optimize",
                    "message": "请先执行解析步骤",
                    "error_code": "NO_PARSE_RESULT"
                }

            structure = self._state["structure"]
            policy_mapping = self._state.get("policy_mapping", {})
            insertion_points = self._state.get("insertion_points", [])

            # 分析教师风格
            teacher_style = self.style_adapter.analyze_from_chunks(structure.chunks)
            self._state["teacher_style"] = teacher_style

            # 根据 mode 生成内容
            if mode == "prompts":
                # 只生成 prompts
                prompts = self.content_generator.batch_generate_prompts(
                    structure, policy_mapping
                )

                # 保存
                input_name = Path(structure.title or "output").stem
                prompts_file = self.output_dir / f"{input_name}_prompts.json"
                prompts_file.write_text(
                    json.dumps(prompts, ensure_ascii=False, indent=2),
                    encoding="utf-8"
                )

                return {
                    "status": "success",
                    "stage": "optimize",
                    "message": "Prompts 生成完成",
                    "data": {
                        "mode": "prompts",
                        "total_pages": len(structure.chunks),
                        "pages_with_policy": len(policy_mapping),
                        "output_files": {
                            "prompts": str(prompts_file)
                        },
                        "preview": prompts[:3] if len(prompts) > 3 else prompts
                    }
                }

            else:
                # 完整生成 - 使用 page_optimizer
                # 将 structure 转换为 pages 列表
                pages = []
                for i, chunk in enumerate(structure.chunks):
                    pages.append({
                        "page_number": i,
                        "title": chunk.title,
                        "content": chunk.content
                    })

                # 获取 decision_json 和 retrieval_json 路径（通过 session 存储）
                decision_json = self._state.get("decision_file")
                retrieval_json = self._state.get("retrieval_file")

                # 调用 page_optimizer 进行优化
                optimized_pages = self.page_optimizer.optimize_pages(
                    pages=pages,
                    decision_json=decision_json,
                    retrieval_json=retrieval_json
                )

                # 转换为 slides 格式
                generated_slides = []
                for page in optimized_pages:
                    generated_slides.append({
                        "slide_number": page.page_number,
                        "original_title": page.original_title,
                        "title": page.optimized_title,
                        "content": page.content,
                        "si_zheng_note": page.si_zheng_note,
                        "has_policy": page.has_policy,
                        "policy_title": page.policy_title,
                        "keywords": page.keywords,
                        "evidence_used": page.evidence_used
                    })

                # 应用限制
                if limit:
                    generated_slides = generated_slides[:limit]

                # 保存结果
                input_name = Path(structure.title or "output").stem

                # JSON
                json_file = self.output_dir / f"{input_name}_generated.json"
                json_file.write_text(
                    json.dumps(generated_slides, ensure_ascii=False, indent=2),
                    encoding="utf-8"
                )

                # Marp
                metadata = {
                    "title": structure.title,
                    "author": structure.author,
                    "institution": structure.institution
                }
                marp_content = self.marp_generator.generate(generated_slides, metadata)
                marp_file = self.output_dir / f"{input_name}_marp.md"
                marp_file.write_text(marp_content, encoding="utf-8")

                # 保存到状态
                self._state["generated_slides"] = generated_slides

                # 构建预览数据
                preview = []
                for i, slide in enumerate(generated_slides[:5]):
                    preview.append({
                        "page_num": i,
                        "title": slide.get("title"),
                        "content": slide.get("content", "")[:200] + "..." if len(slide.get("content", "")) > 200 else slide.get("content", ""),
                        "has_policy": slide.get("has_policy", False)
                    })

                return {
                    "status": "success",
                    "stage": "optimize",
                    "message": "优化完成",
                    "data": {
                        "mode": "full",
                        "total_pages": len(generated_slides),
                        "pages_with_policy": len(policy_mapping),
                        "output_files": {
                            "json": str(json_file),
                            "marp": str(marp_file)
                        },
                        # 前端直接使用的内容
                        "slides": generated_slides,  # 完整 JSON
                        "marp_content": marp_content,  # 完整 Markdown
                        "preview": preview  # 前5页预览
                    }
                }

        except Exception as e:
            return {
                "status": "error",
                "stage": "optimize",
                "message": f"优化失败: {str(e)}",
                "error_code": "GENERATION_ERROR"
            }

    # ============== 便捷方法：一键执行 ==============
    def run(
        self,
        ppt_file: str = None,
        pdf_file: str = None,
        markdown_file: str = None,
        mode: Literal["full", "analyze", "prompts"] = "full",
        limit: int = None
    ) -> Dict:
        """
        一键执行完整流程

        Args:
            ppt_file: PPT 文件路径 (优先级高于 markdown_file)
            pdf_file: PDF 文件路径 (优先级高于 ppt_file)
            markdown_file: Markdown 文件路径
            mode: full - 完整流程; analyze - 只分析; prompts - 只生成 prompts
            limit: 可选，限制处理页数

        Returns:
            完整流程结果
        """
        # Step 1: 解析
        parse_result = self.parse(ppt_file=ppt_file, pdf_file=pdf_file, markdown_file=markdown_file)
        if parse_result["status"] != "success":
            return parse_result

        # Step 2: 决策
        decide_result = self.decide()
        if decide_result["status"] != "success":
            return decide_result

        # analyze 模式只返回分析结果
        if mode == "analyze":
            return {
                "status": "success",
                "stage": "complete",
                "mode": "analyze",
                "message": "分析完成",
                "data": {
                    "parse": parse_result["data"],
                    "decide": decide_result["data"]
                }
            }

        # Step 3: 检索
        retrieve_result = self.retrieve()
        if retrieve_result["status"] != "success":
            return retrieve_result

        # prompts 模式返回 prompts
        if mode == "prompts":
            return self.optimize(mode="prompts", limit=limit)

        # Step 4: 优化
        return self.optimize(limit=limit)

    # ============== 状态管理 ==============

    def get_state(self) -> Dict:
        """获取当前状态"""
        return {
            "has_structure": self._state["structure"] is not None,
            "has_insertion_points": self._state["insertion_points"] is not None,
            "has_policy_mapping": self._state["policy_mapping"] is not None,
            "has_generated_slides": self._state["generated_slides"] is not None
        }

    def reset(self):
        """重置状态"""
        self._state = {
            "structure": None,
            "insertion_points": None,
            "policy_mapping": None,
            "retrieval_file": None,
            "teacher_style": None,
            "generated_slides": None
        }


# ============== FastAPI 路由 ==============

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

# 全局 API 实例（生产环境可用依赖注入）
_api_instance = None


def get_api() -> LessonPreparationAPI:
    """获取 API 实例"""
    global _api_instance
    if _api_instance is None:
        _api_instance = LessonPreparationAPI()
    return _api_instance


class ParseRequest(BaseModel):
    ppt_file: Optional[str] = None
    pdf_file: Optional[str] = None
    markdown_file: Optional[str] = None


class DecideRequest(BaseModel):
    structure: Optional[Dict] = None


class RetrieveRequest(BaseModel):
    pass  # 无需参数，使用前两步的结果


class OptimizeRequest(BaseModel):
    mode: Literal["full", "prompts"] = "full"
    limit: Optional[int] = None


class RunRequest(BaseModel):
    ppt_file: Optional[str] = None
    pdf_file: Optional[str] = None
    markdown_file: Optional[str] = None
    mode: Literal["full", "analyze", "prompts"] = "full"
    limit: Optional[int] = None


@router.post("/ppt_parse")
async def api_parse(request: ParseRequest):
    """Step 1: 解析 PPT 文档

    支持输入 PPT 文件或 Markdown 文件
    """
    api = get_api()
    return api.parse(ppt_file=request.ppt_file, pdf_file=request.pdf_file, markdown_file=request.markdown_file)


@router.post("/decide")
async def api_decide(request: DecideRequest):
    """Step 2: 决策思政融合点"""
    api = get_api()
    return api.decide(request.structure)


@router.post("/retrieve")
async def api_retrieve(request: RetrieveRequest):
    """Step 3: 检索思政内容"""
    api = get_api()
    return api.retrieve()


@router.post("/optimize")
async def api_optimize(request: OptimizeRequest):
    """Step 4: 优化并生成内容"""
    api = get_api()
    return api.optimize(request.mode, request.limit)


@router.post("/run")
async def api_run(request: RunRequest):
    """一键执行完整流程

    支持输入 PPT 文件或 Markdown 文件
    """
    api = get_api()
    return api.run(
        ppt_file=request.ppt_file,
        pdf_file=request.pdf_file,
        markdown_file=request.markdown_file,
        mode=request.mode,
        limit=request.limit
    )



# ============== 启动入口 ==============

def create_app():
    """创建 FastAPI 应用"""
    from fastapi import FastAPI
    app = FastAPI(title="课程备课智能体 API")
    app.include_router(router, prefix="/ppt_optimizer", tags=["备课接口"])
    return app


if __name__ == "__main__":
    import uvicorn
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8001)
