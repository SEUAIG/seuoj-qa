import json
import re
from pathlib import Path
from typing import List, Dict, Any

import yaml
from openai import OpenAI

# 加载配置（复用 agent.py 的模式）
_config_path = Path(__file__).parent.parent / "config" / "base.yaml"
with open(_config_path, "r", encoding="utf-8") as f:
    _CONFIG = yaml.safe_load(f)

_LLM_PROVIDER = _CONFIG["llm"][_CONFIG["llm"]["use"]]

_llm_client = OpenAI(
    api_key=_LLM_PROVIDER["api_key"],
    base_url=_LLM_PROVIDER["api_base"].rstrip("/"),
)

# 内置默认 prompt（当 prompts.yaml 中缺少 classify_tags 时使用）
_DEFAULT_SYSTEM_PROMPT = """你是一个算法竞赛题目标签分类专家。你的任务是根据题目内容，从给定的标签列表中选择最合适的算法标签。

规则：
1. 优先从给定的标签列表中选择，尽量使用已有标签
2. 可以选择多个标签，也可以不选择任何标签
3. 选择与题目核心算法思想最相关的标签
4. 如果题目涉及多种算法，选择所有适用的标签
5. 如果题目是纯粹的模拟/暴力，不涉及特定算法思想，返回空列表
6. 如果你认为现有标签都不能准确描述该题目涉及的算法，可以在 new_tags 中建议新的标签名（仅建议，不会自动创建）
7. 输出必须是严格的 JSON 格式"""

_DEFAULT_USER_PROMPT = """请分析以下题目内容，从给定的标签列表中选择合适的算法标签。

题目内容：
{problem_text}

可用标签列表：
{tag_list}

请以 JSON 格式输出，格式为：
{{"tag_ids": [已有标签id1, 已有标签id2], "new_tags": ["建议的新标签名1"]}}

- tag_ids: 从上面可用标签中选择的标签id列表
- new_tags: 如果现有标签都不够准确，在这里填写你建议的新标签名（字符串列表）。如果没有新标签建议，输出空列表 []

重要：优先使用已有标签。只有在现有标签确实无法覆盖题目涉及的算法时，才建议新标签。"""

# 尝试从 prompts.yaml 加载，失败则使用内置默认值
_prompts_path = Path(__file__).parent.parent / "config" / "prompts.yaml"
try:
    with open(_prompts_path, "r", encoding="utf-8") as f:
        _all_prompts = yaml.safe_load(f).get("prompts", {})
    _classify_prompts = _all_prompts.get("classify_tags")
    if _classify_prompts and "system" in _classify_prompts and "user" in _classify_prompts:
        SYSTEM_PROMPT = _classify_prompts["system"]
        USER_PROMPT_TEMPLATE = _classify_prompts["user"]
    else:
        raise KeyError("classify_tags not found in prompts.yaml")
except Exception:
    SYSTEM_PROMPT = _DEFAULT_SYSTEM_PROMPT
    USER_PROMPT_TEMPLATE = _DEFAULT_USER_PROMPT


def _build_problem_text(
    title: str,
    description: str,
    input_fmt: str,
    output_fmt: str,
    hint: str,
    examples: List[Dict[str, str]],
) -> str:
    parts = [f"题目标题：{title}"]
    if description:
        parts.append(f"题目描述：{description}")
    if input_fmt:
        parts.append(f"输入格式：{input_fmt}")
    if output_fmt:
        parts.append(f"输出格式：{output_fmt}")
    if hint:
        parts.append(f"提示：{hint}")
    if examples:
        ex_lines = []
        for i, ex in enumerate(examples, 1):
            in_val = ex.get("in", "")
            ans_val = ex.get("ans", "")
            ex_lines.append(f"样例{i}：输入 {in_val}  输出 {ans_val}")
        parts.append("样例：\n" + "\n".join(ex_lines))
    return "\n".join(parts)


def _parse_response(content: str) -> dict:
    """从 LLM 返回内容中提取 tag_id 列表和新标签建议。"""
    content = re.sub(r"^```json\s*", "", content.strip())
    content = re.sub(r"^```\s*", "", content.strip())
    content = re.sub(r"\s*```$", "", content.strip())

    default_result = {"tag_ids": [], "new_tags": []}

    try:
        data = json.loads(content)
        tag_ids = data.get("tag_ids", [])
        new_tags = data.get("new_tags", [])
        return {
            "tag_ids": [int(t) for t in tag_ids if isinstance(t, (int, float))],
            "new_tags": [str(t) for t in new_tags if isinstance(t, str) and t.strip()],
        }
    except (json.JSONDecodeError, ValueError):
        # 宽松提取 tag_ids
        match = re.search(r'"tag_ids"\s*:\s*\[(.*?)\]', content)
        if match:
            nums = re.findall(r"\d+", match.group(1))
            default_result["tag_ids"] = [int(n) for n in nums]
        # 宽松提取 new_tags
        match = re.search(r'"new_tags"\s*:\s*\[(.*?)\]', content)
        if match:
            tags = re.findall(r'"([^"]+)"', match.group(1))
            default_result["new_tags"] = [t for t in tags if t.strip()]
        return default_result


def classify_problem_tags(
    title: str,
    description: str,
    input_fmt: str,
    output_fmt: str,
    hint: str,
    examples: List[Dict[str, str]],
    available_tags: List[Dict[str, Any]],
) -> dict:
    """
    对一道题目进行算法标签分类。

    Returns:
        {"tag_ids": [已有标签id], "new_tags": ["建议的新标签名"]}
    """
    if not available_tags:
        return {"tag_ids": [], "new_tags": []}

    problem_text = _build_problem_text(title, description, input_fmt, output_fmt, hint, examples)
    tag_list_text = "\n".join(
        f"- {t['tag_id']}: {t['tag_name']}" for t in available_tags
    )

    user_content = USER_PROMPT_TEMPLATE.format(
        problem_text=problem_text,
        tag_list=tag_list_text,
    )

    resp = _llm_client.chat.completions.create(
        model=_LLM_PROVIDER["model"],
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.1,
        max_tokens=1000,
    )

    return _parse_response(resp.choices[0].message.content)
