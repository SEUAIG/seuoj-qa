from fastapi import FastAPI, UploadFile, File, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, List, Literal
import tempfile
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.retrieval.retrieval import (
    faiss_search,
    bm25_search,
    pre_knowledge_search,
)

from src.agent import agent_framework, format_response

from src.retrieval.qa_retrieval.qa_retrieval_advanced import (
    AdvancedQARetriever,
    AdvancedRetrievalConfig,
)

from src.controller import (
    recommend_controller,
    format_prerequisite_results,
    format_qa_results,
)

# ========== PPT 备课智能体 API ==========
from src.preparation.api import LessonPreparationAPI

# ========== 题库 API ==========
from src.program.problem_bank import (
    get_problem_list_for_frontend,
    get_problem_detail_for_frontend,
)

# ========== 代码生成 API ==========
from src.program.code_generator import code_generator

# ========== 代码运行 API ==========
from src.program.code_runner import code_runner as run_code

# ========== 数据库 (SQLite) ==========
from src.database import (
    init_db,
    create_session,
    get_session,
    list_sessions,
    update_session,
    delete_session,
    create_message,
    get_messages,
    create_assistant_message_with_citations,
)


qa_retriever = AdvancedQARetriever(
    AdvancedRetrievalConfig(
        search_mode="hybrid"
    )
)

app = FastAPI()
agent_router = APIRouter(prefix="/agent")

# 启动时初始化数据库（建表，幂等操作）
init_db()

# 允许跨域（前端可直接访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- 请求体 ----------
class Query(BaseModel):
    query: str
    top_k: int = 10


# ---------- Root ----------
@agent_router.get("/")
def root():
    return {"status": "RAG API running"}


# ---------- 原有 RAG API ----------
@agent_router.post("/faiss_search")
def api_faiss(req: Query):
    return {"results": faiss_search(req.query, req.top_k)}


@agent_router.post("/bm25_search")
def api_bm25(req: Query):
    return {"results": bm25_search(req.query, req.top_k)}


@agent_router.post("/rag_answer")
def api_rag(req: Query):
    response = agent_framework(req.query)
    answer, citations = format_response(response)

    return {
            "answer": answer,
            "citations": citations
    }


@agent_router.post("/pre_knowledge_search")
def api_pre_knowledge(req: Query):
    raw_results = pre_knowledge_search(req.query)

    prerequisites = []
    seen = set()

    for concept, chunk in raw_results:
        if concept in seen:
            continue
        seen.add(concept)

        prerequisites.append({
            "concept": concept,
            "content": chunk.get("content", "")
        })

    return {
        "query": req.query,
        "prerequisites": prerequisites
    }


@agent_router.post("/qa_search")
def api_qa_search(req: Query):
    """
    高级题库检索接口
    """
    results = qa_retriever.search(
        query=req.query,
        top_k=req.top_k
    )

    return {
        "results": [
            {
                "score": score,
                "question": item.get("question"),
                "chapter": item.get("chapter"),
                "answer": item.get("answer", "")
            }
            for item, score in results
        ]
    }


@agent_router.post("/smart_answer")
def api_smart_answer(req: Query):
    """
    智能推荐接口 - 根据 query 自动决定返回内容

    返回内容可能包括：
    - answer: 基础答案（始终返回）
    - citations: 参考文献（始终返回）
    - decision: 推荐决策信息
    - prerequisites: 前置知识点（如果 recommend_prerequisite=True）
    - related_questions: 相关题库（如果 recommend_qa_bank=True）
    """
    # 1. 推荐判断
    decision = recommend_controller(req.query)

    # 2. 基础答案 (始终返回)
    response = agent_framework(req.query)
    answer, citations = format_response(response)

    result = {
        "answer": answer,
        "citations": citations,
        "decision": {
            "recommend_prerequisite": decision["recommend_prerequisite"],
            "recommend_qa_bank": decision["recommend_qa_bank"],
            "detected_concepts": decision["detected_concepts"],
            "reason": decision["reason"]
        }
    }

    # 3. 根据决策添加额外内容
    if decision["recommend_prerequisite"]:
        prereq_raw = pre_knowledge_search(req.query)
        result["prerequisites"] = format_prerequisite_results(prereq_raw)

    if decision["recommend_qa_bank"]:
        qa_raw = qa_retriever.search(req.query, top_k=5)
        result["related_questions"] = format_qa_results(qa_raw)

    return result


# ========== 题库 API ==========

class CodeGenerationRequest(BaseModel):
    problem_description: str
    user_solution: str
    language: Literal["python", "java", "c++"]


@agent_router.post("/code_generation")
def api_code_generation(req: CodeGenerationRequest):
    """
    代码生成接口

    根据题目描述和用户的解答（伪代码/文字），生成：
    - 用户解答的理解
    - 按用户解答生成的代码和测试代码
    - 优化建议
    - 最优解代码和测试代码
    """
    result = code_generator(
        req.problem_description,
        req.user_solution,
        req.language
    )
    return result


@agent_router.get("/problem/list")
def api_problem_list():
    """
    获取题目列表（id + 标题 + 描述）

    供前端展示题目列表用
    """
    problems = get_problem_list_for_frontend(
        fields=["id", "title", "description"]
    )
    return {
        "total": len(problems),
        "problems": problems
    }


@agent_router.get("/problem/detail/{problem_id}")
def api_problem_detail(problem_id: int):
    """
    获取题目详情

    - problem_id: 题目ID
    """
    problem = get_problem_detail_for_frontend(problem_id)
    if problem is None:
        return {
            "status": "error",
            "message": f"题目 {problem_id} 不存在"
        }
    return {
        "status": "success",
        "problem": problem
    }


# ========== 代码运行 API ==========

# 语言映射：前端格式 -> code_runner 服务格式
LANGUAGE_MAP = {
    "python": "Python3_12",
    "java": "Java17",
    "c++": "Cpp17",
}


class CodeRunnerRequest(BaseModel):
    code: str
    language: Literal["python", "java", "c++"] = "python"
    test_cases: Optional[List[str]] = None  # 每个测试用例作为一行 stdin 输入


@agent_router.post("/code_runner")
def api_code_runner(req: CodeRunnerRequest):
    """
    代码运行/测试接口

    接受代码和测试用例，运行并返回结果。
    - 如果提供 test_cases，则逐个运行并返回所有结果
    - 否则直接运行代码（stdin 为空）
    """
    # 转换为服务格式
    service_language = LANGUAGE_MAP.get(req.language, "Python3_12")

    if req.test_cases:
        # 逐个运行测试用例
        results = []
        for i, stdin_input in enumerate(req.test_cases):
            result = run_code(
                code=req.code,
                stdin=stdin_input,
                language=service_language
            )
            results.append({
                "test_case_index": i,
                "stdin": stdin_input,
                **result
            })
        return {
            "success": True,
            "total": len(results),
            "results": results
        }
    else:
        # 直接运行代码
        return run_code(
            code=req.code,
            stdin="",
            language=service_language
        )


# ========== PPT 备课智能体路由 ==========

# 用户会话存储（session_id -> API 实例）
_ppt_sessions: Dict[str, LessonPreparationAPI] = {}


def get_ppt_api(session_id: str = None) -> LessonPreparationAPI:
    """获取指定 session 的 PPT 备课 API 实例"""
    if session_id and session_id in _ppt_sessions:
        return _ppt_sessions[session_id]
    # 创建新实例
    api = LessonPreparationAPI()
    if session_id:
        _ppt_sessions[session_id] = api
    return api


def clear_session(session_id: str):
    """清除指定 session"""
    if session_id in _ppt_sessions:
        del _ppt_sessions[session_id]


# 请求体模型
class ParseRequest(BaseModel):
    ppt_file: Optional[str] = None
    pdf_file: Optional[str] = None
    markdown_file: Optional[str] = None


class DecideRequest(BaseModel):
    session_id: Optional[str] = None
    structure: Optional[Dict] = None
    user_prompt: Optional[str] = None  # 用户自定义需求


class RetrieveRequest(BaseModel):
    session_id: Optional[str] = None


class OptimizeRequest(BaseModel):
    session_id: Optional[str] = None
    mode: Literal["full", "prompts"] = "full"
    limit: Optional[int] = None


class RunRequest(BaseModel):
    ppt_file: Optional[str] = None
    pdf_file: Optional[str] = None
    markdown_file: Optional[str] = None
    mode: Literal["full", "analyze", "prompts"] = "full"
    limit: Optional[int] = None


import uuid


@agent_router.post("/ppt_optimizer/ppt_parser")
async def api_ppt_parse(
    ppt_file: UploadFile = File(None),
    pdf_file: UploadFile = File(None),
    markdown_file: UploadFile = File(None)
):
    """Step 1: 解析 PPT 文档（支持文件上传）"""

    session_id = str(uuid.uuid4())
    api = get_ppt_api(session_id)

    ppt_file_path = None
    pdf_file_path = None
    markdown_file_path = None

    # ✅ 1. 限制只能上传一个文件
    file_count = sum([
        ppt_file is not None,
        pdf_file is not None,
        markdown_file is not None
    ])

    if file_count != 1:
        return {
            "status": "error",
            "message": "必须且只能上传一个文件（ppt/pdf/markdown）"
        }

    # ✅ 2. 不相信字段名，统一处理
    uploaded_file = ppt_file or pdf_file or markdown_file

    filename = uploaded_file.filename.lower()
    suffix = os.path.splitext(filename)[1]

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await uploaded_file.read()
        tmp.write(content)
        file_path = tmp.name

    print(">>> UPLOADED FILE:", filename)
    print(">>> SAVED PATH:", file_path)

    # ✅ 3. 根据后缀判断类型（核心修复）
    if suffix == ".pdf":
        pdf_file_path = file_path
    elif suffix in [".ppt", ".pptx"]:
        ppt_file_path = file_path
    elif suffix in [".md", ".markdown"]:
        markdown_file_path = file_path
    else:
        return {
            "status": "error",
            "message": f"不支持的文件类型: {suffix}"
        }

    # ✅ 4. 调用解析
    try:
        print(">>> BEFORE PARSE")
        print("ppt_file =", ppt_file_path)
        print("pdf_file =", pdf_file_path)
        print("markdown_file =", markdown_file_path)

        result = api.parse(
            ppt_file=ppt_file_path,
            pdf_file=pdf_file_path,
            markdown_file=markdown_file_path
        )

        print(">>> AFTER PARSE")

    finally:
        # ⚠️ 先不要删（避免解析过程中被删）
        pass
        # if ppt_file_path and os.path.exists(ppt_file_path):
        #     os.unlink(ppt_file_path)
        # if pdf_file_path and os.path.exists(pdf_file_path):
        #     os.unlink(pdf_file_path)
        # if markdown_file_path and os.path.exists(markdown_file_path):
        #     os.unlink(markdown_file_path)

    result["session_id"] = session_id
    return result


@agent_router.post("/ppt_optimizer/decide")
async def api_ppt_decide(request: DecideRequest):
    """Step 2: 决策思政融合点"""
    api = get_ppt_api(request.session_id)
    return api.decide(request.structure, request.user_prompt)


class SessionRequest(BaseModel):
    session_id: Optional[str] = None


@agent_router.post("/ppt_optimizer/retrieve")
async def api_ppt_retrieve(request: SessionRequest):
    """Step 3: 检索思政内容（深度爬取）"""
    api = get_ppt_api(request.session_id)
    return api.retrieve()


@agent_router.post("/ppt_optimizer/optimize")
async def api_ppt_optimize(request: OptimizeRequest):
    """Step 4: 优化生成内容"""
    api = get_ppt_api(request.session_id)
    return api.optimize(request.mode, request.limit)


@agent_router.post("/ppt_optimizer/run")
async def api_ppt_run(
    ppt_file: UploadFile = File(None),
    markdown_file: UploadFile = File(None),
    pdf_file: UploadFile = File(None),
    mode: str = "full",
    limit: int = None
):
    """一键执行完整流程（支持文件上传）"""

    session_id = str(uuid.uuid4())
    api = get_ppt_api(session_id)

    ppt_file_path = None
    markdown_file_path = None
    pdf_file_path = None

    # ✅ 1. 限制只能上传一个文件
    file_count = sum([
        ppt_file is not None,
        pdf_file is not None,
        markdown_file is not None
    ])

    if file_count != 1:
        return {
            "status": "error",
            "message": "必须且只能上传一个文件（ppt/pdf/markdown）"
        }

    # ✅ 2. 统一文件入口（关键）
    uploaded_file = ppt_file or pdf_file or markdown_file

    filename = uploaded_file.filename.lower()
    suffix = os.path.splitext(filename)[1]

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await uploaded_file.read()
        tmp.write(content)
        file_path = tmp.name

    print(">>> RUN UPLOADED FILE:", filename)
    print(">>> RUN SAVED PATH:", file_path)

    # ✅ 3. 用后缀判断类型（核心修复）
    if suffix == ".pdf":
        pdf_file_path = file_path
    elif suffix in [".ppt", ".pptx"]:
        ppt_file_path = file_path
    elif suffix in [".md", ".markdown"]:
        markdown_file_path = file_path
    else:
        return {
            "status": "error",
            "message": f"不支持的文件类型: {suffix}"
        }

    # ✅ 4. 执行 run
    try:
        print(">>> BEFORE RUN")
        print("ppt_file =", ppt_file_path)
        print("pdf_file =", pdf_file_path)
        print("markdown_file =", markdown_file_path)

        result = api.run(
            ppt_file=ppt_file_path,
            pdf_file=pdf_file_path,
            markdown_file=markdown_file_path,
            mode=mode,
            limit=limit
        )

        print(">>> AFTER RUN")

    finally:
        # ⚠️ 先不要删文件（避免解析过程中被删）
        pass
        # if ppt_file_path and os.path.exists(ppt_file_path):
        #     os.unlink(ppt_file_path)
        # if pdf_file_path and os.path.exists(pdf_file_path):
        #     os.unlink(pdf_file_path)
        # if markdown_file_path and os.path.exists(markdown_file_path):
        #     os.unlink(markdown_file_path)

    result["session_id"] = session_id
    return result


# ========== 聊天会话/消息 API (SQLite) ==========

class CreateSessionRequest(BaseModel):
    user_id: str
    title: str = "新会话"
    course_id: Optional[str] = None


class CreateMessageRequest(BaseModel):
    session_id: str
    role: Literal["USER", "ASSISTANT"] = "USER"
    content: str
    parent_message_id: Optional[str] = None
    citations: Optional[List[Dict]] = None


class RagAnswerRequest(BaseModel):
    session_id: Optional[str] = None
    user_id: str
    query: str


class UpdateSessionRequest(BaseModel):
    title: Optional[str] = None


@agent_router.post("/api/rag/sessions")
@agent_router.post("/api/rag/sessions/")
def api_create_session(req: CreateSessionRequest):
    """创建新聊天会话"""
    session = create_session(req.user_id, req.title, req.course_id)
    return session


@agent_router.get("/api/rag/sessions")
@agent_router.get("/api/rag/sessions/")
def api_list_sessions(user_id: str, course_id: Optional[str] = None,
                      page: int = 1, page_size: int = 50):
    """列出用户的所有会话"""
    sessions = list_sessions(user_id, course_id)
    # 分页
    total = len(sessions)
    start = (page - 1) * page_size
    end = start + page_size
    return {"count": total, "results": sessions[start:end]}


@agent_router.get("/api/rag/sessions/{session_id}")
@agent_router.get("/api/rag/sessions/{session_id}/")
def api_get_session(session_id: str):
    """获取会话详情"""
    session = get_session(session_id)
    if not session:
        return {"error": "Session not found"}
    return session


@agent_router.put("/api/rag/sessions/{session_id}")
@agent_router.put("/api/rag/sessions/{session_id}/")
def api_update_session(session_id: str, req: UpdateSessionRequest):
    """更新会话标题"""
    kwargs = {}
    if req.title is not None:
        kwargs["title"] = req.title
    session = update_session(session_id, **kwargs)
    return session


@agent_router.delete("/api/rag/sessions/{session_id}")
@agent_router.delete("/api/rag/sessions/{session_id}/")
def api_delete_session(session_id: str):
    """删除会话"""
    ok = delete_session(session_id)
    return {"deleted": ok}


@agent_router.get("/api/rag/sessions/{session_id}/messages")
@agent_router.get("/api/rag/sessions/{session_id}/messages/")
def api_get_messages(session_id: str):
    """获取会话的所有消息（含引用）"""
    messages = get_messages(session_id)
    return {"messages": messages}


@agent_router.post("/api/rag/messages")
@agent_router.post("/api/rag/messages/")
def api_create_message(req: CreateMessageRequest):
    """创建消息（支持带引用的 AI 回复）"""
    if req.role == "ASSISTANT" and req.citations:
        msg = create_assistant_message_with_citations(
            session_id=req.session_id,
            content=req.content,
            citations=req.citations,
            parent_message_id=req.parent_message_id,
        )
    else:
        msg = create_message(
            session_id=req.session_id,
            role=req.role,
            content=req.content,
            parent_message_id=req.parent_message_id,
        )
    return msg


@agent_router.post("/api/rag/messages/rag_answer")
@agent_router.post("/api/rag/messages/rag_answer/")
def api_rag_answer_with_history(req: RagAnswerRequest):
    """
    RAG 回答接口（带会话持久化）

    自动创建/复用会话，保存用户问题和 AI 回答到数据库。
    """
    # 获取或创建会话
    if req.session_id:
        session = get_session(req.session_id)
        if not session:
            return {"error": f"Session {req.session_id} not found"}
    else:
        session = create_session(req.user_id, req.query[:50])

    session_id = session["session_id"]

    # 保存用户消息
    user_msg = create_message(session_id, "USER", req.query)

    # 调用 RAG
    response = agent_framework(req.query)
    answer, citations = format_response(response)

    # 保存 AI 回复（含引用）
    ai_msg = create_assistant_message_with_citations(
        session_id=session_id,
        content=answer,
        citations=citations,
        parent_message_id=user_msg["id"],
    )

    return {
        "id": ai_msg["id"],
        "session_id": session_id,
        "role": "ASSISTANT",
        "content": answer,
        "parent_message_id": user_msg["id"],
        "timestamp": ai_msg["timestamp"],
        "citations": ai_msg["citations"],
    }

app.include_router(agent_router)


# ========== 启动入口 ==========
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8002,
        workers=1,          # 关键：显式指定
        loop="uvloop",      # 对齐 CLI 行为（推荐）
        http="httptools"    # 提升性能（可选）
    )
