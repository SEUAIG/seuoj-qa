import json
import re
import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Tuple
import yaml
from datetime import datetime


# ================================
# Prompt 模板加载
# ================================
_CONFIG_DIR = os.path.join(Path(__file__).parent.parent, "config")
_PROMPTS_PATH = os.path.join(_CONFIG_DIR, "prompts.yaml")

with open(_PROMPTS_PATH, "r", encoding="utf-8") as f:
    _AGENT_PROMPTS = yaml.safe_load(f)["prompts"]["agent"]


def parse_llm_json(content: str) -> dict:
    """从 LLM 返回的内容中提取 JSON，处理 markdown fences 和控制字符。"""
    # 去除 markdown code block 标记
    content = re.sub(r"^```json\s*", "", content.strip())
    content = re.sub(r"^```\s*", "", content.strip())
    content = re.sub(r"\s*```$", "", content.strip())
    # 去除控制字符（换行符、制表符之外的不可见控制字符）
    content = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", content)
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # 宽松模式：把字符串值内未转义的换行符替换为 \n
        # 思路是找到 JSON 中字符串值（"..." 内）里的裸换行，替换为 \n
        result = []
        i = 0
        in_string = False
        escaped = False
        while i < len(content):
            c = content[i]
            if not in_string:
                if c == '"':
                    in_string = True
                    result.append(c)
                else:
                    result.append(c)
            else:
                if escaped:
                    result.append(c)
                    escaped = False
                elif c == '\\':
                    result.append(c)
                    escaped = True
                elif c == '"':
                    in_string = False
                    result.append(c)
                elif c in '\n\r':
                    # 字符串值内未转义的换行 → 替换为转义的 \n
                    result.append('\\n')
                else:
                    result.append(c)
            i += 1
        return json.loads("".join(result))

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Import existing modules
from retrieval.retrieval import faiss_search, bm25_search
from retrieval.qa_retrieval.qa_retrieval_advanced import (
    AdvancedQARetriever,
    AdvancedRetrievalConfig,
)

from openai import OpenAI
from utils import renumber_citations, renumber_citations_both_formats

# 初始化题库检索器
qa_retriever = AdvancedQARetriever(
    AdvancedRetrievalConfig(search_mode="hybrid")
)


def load_config():
    config_path = Path(__file__).parent.parent / "config" / "base.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config

# Initialize LLM client
CONFIG = load_config()
LLM_PROVIDER = CONFIG["llm"][CONFIG["llm"]["use"]]

def create_llm_client():
    """Create OpenAI-compatible LLM client"""
    return OpenAI(
        api_key=LLM_PROVIDER["api_key"],
        base_url=LLM_PROVIDER["api_base"].rstrip("/")
    )

LLM_CLIENT = create_llm_client()


# ================================
# Agent Prompts
# ================================

EXECUTOR_SYNTHESIZE_PROMPT = _AGENT_PROMPTS["executor_synthesize"]["template"]
EXECUTOR_SYNTHESIZE_PROMPT_STREAM = _AGENT_PROMPTS["executor_synthesize_stream"]["template"]


# ================================
# Logging Utility
# ================================

def log_agent(agent_name: str, message: str, data: Any = None):
    """Print structured logging for debugging"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{agent_name}] {message}")
    if data is not None:
        if isinstance(data, dict):
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            print(data)


# ================================
# Core Agent Functions
# ================================

def agent_framework_stream(user_query: str, history_context: str = ""):
    """
    流式版本：先完整生成答案，再逐chunk流式输出，最后发 citations。
    每个 chunk 格式为 SSE: "data: {...}\n\n"
    """
    import json
    import re
    from concurrent.futures import ThreadPoolExecutor

    log_agent("CONTROLLER", "Starting streaming execution", f"Query: {user_query}")

    # 并行检索
    with ThreadPoolExecutor(max_workers=2) as pool:
        faiss_future = pool.submit(faiss_search, user_query, 5)
        bm25_future = pool.submit(bm25_search, user_query, 5)
        faiss_docs = faiss_future.result()
        bm25_docs = bm25_future.result()

    all_docs = faiss_docs + bm25_docs

    # 构建 observations（用于 build_citation_display_index）
    observations = [
        {"step_id": 1, "action": "faiss_search", "query": user_query, "results": faiss_docs},
        {"step_id": 2, "action": "bm25_search", "query": user_query, "results": bm25_docs},
    ]

    # 去重
    unique_docs = {}
    for doc in all_docs:
        chunk_id = doc.get("chunk_id")
        if chunk_id not in unique_docs:
            unique_docs[chunk_id] = doc

    # 格式化 observations
    MAX_CONTENT_LEN = 300
    formatted_observations = []
    for i, (_, doc) in enumerate(unique_docs.items(), 1):
        content = doc.get('content', '')
        if len(content) > MAX_CONTENT_LEN:
            content = content[:MAX_CONTENT_LEN] + "..."
        obs_str = f"[{i}] 标题：{doc.get('title', '')}\n章节：{doc.get('path_titles', [])}\n内容：{content}"
        formatted_observations.append(obs_str)

    observations_text = "\n\n".join(formatted_observations)

    # 流式调用 LLM（纯文本输出，不含 JSON）
    if history_context:
        user_content = f"对话历史：\n{history_context}\n\n请基于以下证据回答问题：\n{observations_text}"
    else:
        user_content = f"Observations：\n{observations_text}"
    messages = [
        {"role": "system", "content": EXECUTOR_SYNTHESIZE_PROMPT_STREAM},
        {"role": "user", "content": user_content}
    ]

    log_agent("EXECUTOR", "Streaming answer")
    stream = LLM_CLIENT.chat.completions.create(
        model=LLM_PROVIDER["model"],
        messages=messages,
        temperature=LLM_PROVIDER.get("temperature", 0.85),
        max_tokens=LLM_PROVIDER.get("max_tokens", 4000),
        stream=True
    )

    # 边吐 token 边 yield，累积文本用于后续解析 citations
    answer_text = ""
    for chunk in stream:
        content = chunk.choices[0].delta.content
        if content:
            answer_text += content
            yield f"data: {json.dumps({'type': 'content', 'text': content}, ensure_ascii=False)}\n\n"

    # 答案生成完毕，解析 citations（从 answer 全文提取 [n] 引用编号）
    raw_citations = list(range(1, len(unique_docs) + 1))
    try:
        found = set(int(m) for m in re.findall(r'\[(\d+)\]', answer_text))
        raw_citations = list(found) if found else list(range(1, len(unique_docs) + 1))
    except Exception:
        pass

    _, used_citations = renumber_citations(answer_text, raw_citations)

    # 构建 citation 详情（title、chapter、content）
    response = {"observations": observations}
    display_index = build_citation_display_index(response)
    citations_display = [display_index.get(cid, {}) for cid in used_citations]

    # 最后发送 citations
    yield f"data: {json.dumps({'type': 'done', 'citations': citations_display}, ensure_ascii=False)}\n\n"
    log_agent("CONTROLLER", "Stream finished")

def agent_framework(user_query: str, history_context: str = "") -> Dict[str, Any]:
    """
    Main controller — 直接执行，跳过 PLANNER 和 VERIFIER 以节省时间。
    faiss_search 和 bm25_search 并行执行以节省检索时间。
    """
    from concurrent.futures import ThreadPoolExecutor

    log_agent("CONTROLLER", "Starting direct execution", f"Query: {user_query}")

    # 并行执行 faiss + bm25 检索
    observations = []
    all_docs = []

    with ThreadPoolExecutor(max_workers=2) as pool:
        faiss_future = pool.submit(faiss_search, user_query, 5)
        bm25_future = pool.submit(bm25_search, user_query, 5)

        faiss_docs = faiss_future.result()
        bm25_docs = bm25_future.result()

    observations.append({"step_id": 1, "action": "faiss_search", "query": user_query, "results": faiss_docs})
    observations.append({"step_id": 2, "action": "bm25_search", "query": user_query, "results": bm25_docs})
    all_docs.extend(faiss_docs)
    all_docs.extend(bm25_docs)

    log_agent("EXECUTOR", f"Hybrid search done", f"faiss={len(faiss_docs)}, bm25={len(bm25_docs)}")

    # Deduplicate
    unique_docs = {}
    for doc in all_docs:
        chunk_id = doc.get("chunk_id")
        if chunk_id not in unique_docs:
            unique_docs[chunk_id] = doc

    # Format observations for LLM (截断每条 content 减少 token)
    MAX_CONTENT_LEN = 300
    formatted_observations = []
    for i, (_, doc) in enumerate(unique_docs.items(), 1):
        content = doc.get('content', '')
        if len(content) > MAX_CONTENT_LEN:
            content = content[:MAX_CONTENT_LEN] + "..."
        obs_str = f"[{i}] 标题：{doc.get('title', '')}\n"
        obs_str += f"章节：{doc.get('path_titles', [])}\n"
        obs_str += f"内容：{content}"
        formatted_observations.append(obs_str)

    observations_text = "\n\n".join(formatted_observations)

    # Synthesize
    log_agent("EXECUTOR", "Synthesizing answer")
    if history_context:
        user_content = f"对话历史：\n{history_context}\n\n请基于以下证据回答问题：\n{observations_text}"
    else:
        user_content = f"Observations：\n{observations_text}"
    messages = [
        {"role": "system", "content": EXECUTOR_SYNTHESIZE_PROMPT},
        {"role": "user", "content": user_content}
    ]
    resp = LLM_CLIENT.chat.completions.create(
        model=LLM_PROVIDER["model"],
        messages=messages,
        temperature=LLM_PROVIDER.get("temperature", 0.85),
        max_tokens=LLM_PROVIDER.get("max_tokens", 4000)
    )
    synthesis_result = parse_llm_json(resp.choices[0].message.content)
    final_answer = synthesis_result.get("answer", "")
    raw_citations = synthesis_result.get("citations", list(range(1, len(unique_docs) + 1)))

    final_answer, used_citations = renumber_citations(final_answer, raw_citations)

    log_agent("CONTROLLER", "Answer ready")
    return {
        "final_answer": final_answer,
        "used_citations": used_citations,
        "iterations": 1,
        "observations": observations
    }


# ================================
# CLI Interface
# ================================
def build_citation_display_index(response: Dict[str, Any]) -> Dict[int, Dict[str, str]]:
    """
    citation_id -> {title, chapter, content}
    citation_id 按 observations.results 首次出现的 chunk 去重顺序递增
    """
    idx: Dict[int, Dict[str, str]] = {}
    seen_chunk_ids = set()
    citation_id = 1

    for obs in response.get("observations", []):
        for r in obs.get("results", []):
            chunk_id = r.get("chunk_id")
            if chunk_id is None or chunk_id in seen_chunk_ids:
                continue

            meta = r.get("metadata", {}) or {}
            book = meta.get("title") or meta.get("source") or "未知来源"
            chapter = r.get("title") or "未命名条目"
            content = r.get("content", "")

            idx[citation_id] = {
                "title": f"《{book}》",
                "chapter": chapter,
                "content": content
            }

            seen_chunk_ids.add(chunk_id)
            citation_id += 1

    return idx


def format_response(response: Dict[str, Any]) -> Tuple[str, List[Dict[str, str]]]:
    answer = response.get("final_answer", "")
    used = response.get("used_citations", [])

    # 1. 重新编号 answer 中的引用（支持 [] 和 【】）
    answer, old_to_new_mapping = renumber_citations_both_formats(answer, used)

    # 2. 构建原始编号 -> 文献信息的映射
    display_index = build_citation_display_index(response)

    # 3. 按 used 的顺序获取文献信息
    citations = []
    for old_idx in sorted(display_index.keys()):
        if old_idx in old_to_new_mapping:
            citations.append(display_index[old_idx])

    return answer, citations


def get_prompt_data_dir() -> Path:
    """获取 prompt 实验数据目录"""
    data_dir = Path(__file__).parent / "data" / "v1_prompt"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_log_path() -> Path:
    """获取交互日志文件路径"""
    log_dir = get_prompt_data_dir() / "prompt_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d")
    return log_dir / f"query_log_{timestamp}.xlsx"


def log_query_result(query: str, response: Dict[str, Any]) -> None:
    """
    将问答结果记录到 Excel 文件，方便调 prompt 的同学查看效果。

    记录内容：
    - timestamp: 时间戳
    - query: 用户问题
    - final_answer: 最终答案
    - used_citations: 引用的文献
    - iterations: 迭代次数
    - verification_passed: 验证是否通过
    - observations_count: 检索到的文档数量
    - observation_contents: 检索到的文档内容摘要
    """
    if not PANDAS_AVAILABLE:
        print("[警告] pandas 未安装，无法记录到 Excel")
        return

    log_path = get_log_path()

    # 提取数据
    final_answer = response.get("final_answer", "")
    used_citations = response.get("used_citations", [])
    iterations = response.get("iterations", 0)
    verification = response.get("verification", {})
    observations = response.get("observations", [])

    verification_passed = verification.get("verdict") == "pass" if verification else False

    # 摘要 observations
    obs_summaries = []
    for obs in observations[:5]:  # 最多取 5 个 observation
        results = obs.get("results", [])
        for doc in results[:3]:  # 每个 observation 最多取 3 个 doc
            content = doc.get("content", "")[:80].replace("\n", " ")
            chunk_id = doc.get("chunk_id", "?")
            obs_summaries.append(f"[{chunk_id}] {content}...")
    observation_contents = "\n".join(obs_summaries)

    row = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "query": query,
        "final_answer": final_answer,
        "used_citations": "\n".join([str(c) for c in used_citations]),
        "iterations": iterations,
        "verification_passed": "是" if verification_passed else "否",
        "observations_count": len(observations),
        "observation_contents": observation_contents,
    }

    # 追加到 Excel
    new_df = pd.DataFrame([row])
    if log_path.exists():
        existing_df = pd.read_excel(log_path)
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
    else:
        combined_df = new_df

    combined_df.to_excel(log_path, index=False)
    print(f"[日志] 已记录到 {log_path}")


def run_batch_experiment(input_excel: str, output_csv: str = None) -> None:
    """
    批量运行实验，读取 Excel 中的 query，输出结果到 CSV。

    Args:
        input_excel: 输入 Excel 路径，包含 query 列
        output_csv: 输出 CSV 路径，默认为 input_excel 同目录下 result_*.csv
    """
    if not PANDAS_AVAILABLE:
        print("[错误] pandas 未安装，无法运行批量实验")
        return

    input_path = Path(input_excel)
    if not input_path.exists():
        print(f"[错误] 输入文件不存在: {input_excel}")
        return

    # 读取 Excel
    df = pd.read_excel(input_path)
    if "query" not in df.columns:
        print("[错误] Excel 中没有 'query' 列")
        return

    # 确定输出路径
    if output_csv is None:
        output_dir = get_prompt_data_dir() / "results"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_csv = output_dir / f"result_{input_path.stem}.csv"

    print(f"\n===== 批量实验开始 =====")
    print(f"输入: {input_excel}")
    print(f"输出: {output_csv}")
    print(f"共 {len(df)} 条 query\n")

    results = []
    for i, row in df.iterrows():
        query = row["query"]
        print(f"[{i+1}/{len(df)}] 正在处理: {query[:50]}...")

        try:
            response = agent_framework(query)
            answer, citations = format_response(response)

            results.append({
                "query": query,
                "final_answer": answer,
                "used_citations": "\n".join([str(c) for c in citations]),
                "iterations": response.get("iterations", 0),
                "verification_passed": "是" if response.get("verification", {}).get("verdict") == "pass" else "否",
                "observations_count": len(response.get("observations", [])),
            })
        except Exception as e:
            print(f"  [错误] {str(e)}")
            results.append({
                "query": query,
                "final_answer": f"[错误] {str(e)}",
                "used_citations": "",
                "iterations": 0,
                "verification_passed": "否",
                "observations_count": 0,
            })

    # 保存 CSV
    result_df = pd.DataFrame(results)
    result_df.to_csv(output_csv, index=False, encoding="utf-8-sig")
    print(f"\n===== 实验完成 =====")
    print(f"结果已保存到: {output_csv}")


def main():
    """Command-line interface for the PEV agent"""
    print("输入您的问题，输入 'exit' 或 'quit' 退出\n")

    while True:
        try:
            query = input("\n请输入您的问题：\n> ").strip()

            if query.lower() in ["exit", "quit", "退出", "q"]:
                print("\n感谢使用！")
                break

            if not query:
                continue

            print("\n正在处理您的问题...")
            print("-" * 40)

            # Run the PEV framework
            response = agent_framework(query)

            answer, citations = format_response(response)
            print("answer:", answer)
            print("citations:", citations)
            # Display result
            print("-" * 40)

            # 记录到 Excel（方便调 prompt 的同学查看效果）
            log_query_result(query, response)

        except KeyboardInterrupt:
            print("\n\n感谢使用！")
            break
        except Exception as e:
            print(f"\n处理出错：{str(e)}")
            print("请重试或联系系统管理员")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="PEV Agent 问答系统")
    parser.add_argument("--input", "-i", type=str, help="输入 Excel 文件路径（包含 query 列），指定后进入批量实验模式")
    parser.add_argument("--output", "-o", type=str, help="输出 CSV 文件路径")
    args = parser.parse_args()

    if args.input:
        # 批量实验模式
        run_batch_experiment(args.input, args.output)
    else:
        # 交互式模式
        main()