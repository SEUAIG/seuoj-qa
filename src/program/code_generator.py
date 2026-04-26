"""
基于题目+用户解答（伪代码/文字），生成：
1. 核心函数代码
2. 内置测试版完整程序（test_code）
3. 可从 stdin 读取输入的完整程序（stdin_code）
4. 结构化测试用例（test_cases）
5. 优化建议
6. 最优解及其对应程序
7. 统一的输入输出格式说明（io_format）

设计目标：
- 真正可扩展的多语言方案
- 默认规则 + 少量语言覆盖
- 未知语言也能走默认协议
- test_cases 和 stdin_code 共用同一份 IO 协议，避免格式不匹配
"""

import re
import json
import os
import requests
import yaml
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor


# =========================
# Prompt 模板加载
# =========================
def _load_prompts():
    config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config")
    prompts_path = os.path.join(config_dir, "prompts.yaml")
    with open(prompts_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)["prompts"]

PROMPTS = _load_prompts()


# =========================
# 工具函数
# =========================
def strip_markdown_code_block(text: str) -> str:
    if not text:
        return text

    text = text.strip()
    text = re.sub(r"^```[^\n]*\n", "", text)
    text = re.sub(r"\n```$", "", text)
    return text.strip()


def safe_parse_json(text: str, default):
    if not text:
        return default

    text = strip_markdown_code_block(text)

    try:
        return json.loads(text)
    except Exception:
        pass

    array_match = re.search(r"(\[[\s\S]*\])", text)
    if array_match:
        try:
            return json.loads(array_match.group(1))
        except Exception:
            pass

    obj_match = re.search(r"(\{[\s\S]*\})", text)
    if obj_match:
        try:
            return json.loads(obj_match.group(1))
        except Exception:
            pass

    return default


# =========================
# 语言标准化与策略
# =========================
LANGUAGE_ALIAS_MAP = {
    "c++": "cpp",
    "cc": "cpp",
    "cxx": "cpp",
    "cpp": "cpp",
    "py": "python",
    "python3": "python",
    "js": "javascript",
    "node": "javascript",
    "nodejs": "javascript",
    "javascript": "javascript",
    "ts": "typescript",
    "typescript": "typescript",
    "c#": "csharp",
    "cs": "csharp",
    "csharp": "csharp",
    "golang": "go",
    "go": "go",
    "rs": "rust",
    "rust": "rust",
    "kt": "kotlin",
    "kotlin": "kotlin",
}


DEFAULT_LANGUAGE_POLICY = {
    "stdin_protocol": "plain_text",
    "forbid_json_stdin": True,
    "needs_class_name_match": False,
    "public_class_name": None,
    "main_function_hint": "use the language's standard runnable entrypoint",
    "prefer_token_based_parsing": True,
    "extra_constraints": [],
}


LANGUAGE_OVERRIDES = {
    "python": {
        "extra_constraints": [
            "必须使用 input()、sys.stdin.readline()、或 sys.stdin.read().split() 等普通文本方式读取 stdin",
            "禁止使用 json.loads(sys.stdin.read())",
            "不要假设输入是 JSON",
            "优先使用 token 解析方式，不要死板假设每一行只对应一个整数",
        ],
        "main_function_hint": "use top-level script or if __name__ == '__main__'",
    },
    "java": {
        "needs_class_name_match": True,
        "public_class_name": "Main",
        "extra_constraints": [
            "公共类名必须是 Main，因为后端保存文件名通常为 Main.java",
            "使用 Scanner 或 BufferedReader 读取标准输入",
            "不要假设输入是 JSON",
            "不要把整行数组文本例如 '2 7 11 15' 当成一个整数去 parseInt",
            "如果某一行包含多个整数，必须先 split 再逐个解析，或直接使用 Scanner/token 流读取",
            "优先使用 token 解析方式，不要死板假设每一行只对应一个整数",
        ],
        "main_function_hint": "public static void main(String[] args)",
    },
    "cpp": {
        "extra_constraints": [
            "使用 cin / getline 等标准输入方式读取普通文本 stdin",
            "不要假设输入是 JSON",
            "优先使用 token 解析方式",
        ],
        "main_function_hint": "int main()",
    },
    "c": {
        "extra_constraints": [
            "使用 scanf / fgets / getchar 等标准输入方式读取普通文本 stdin",
            "不要假设输入是 JSON",
            "优先使用 token 解析方式",
        ],
        "main_function_hint": "int main()",
    },
    "javascript": {
        "extra_constraints": [
            "使用 Node.js 标准输入读取方式处理普通文本 stdin",
            "不要假设输入是 JSON",
            "优先按空白字符切分 token 来解析输入",
        ],
        "main_function_hint": "Node.js executable script entry",
    },
    "typescript": {
        "extra_constraints": [
            "使用标准输入读取方式处理普通文本 stdin",
            "不要假设输入是 JSON",
            "优先按空白字符切分 token 来解析输入",
        ],
        "main_function_hint": "TypeScript runnable entry for Node.js style stdin handling",
    },
    "go": {
        "extra_constraints": [
            "必须包含 package main",
            "必须包含 func main()",
            "使用 bufio / fmt / os.Stdin 等标准方式读取普通文本 stdin",
            "不要假设输入是 JSON",
            "优先使用 token 解析方式",
        ],
        "main_function_hint": "func main()",
    },
    "rust": {
        "extra_constraints": [
            "必须包含 fn main()",
            "使用 std::io 读取普通文本 stdin",
            "不要假设输入是 JSON",
            "优先按空白字符切分 token 来解析输入",
        ],
        "main_function_hint": "fn main()",
    },
    "csharp": {
        "extra_constraints": [
            "使用 Console.ReadLine() 等标准输入方式读取普通文本 stdin",
            "不要假设输入是 JSON",
            "如果某一行包含多个整数，必须 split 后逐个解析，或实现 token 读取器",
        ],
        "main_function_hint": "static void Main(string[] args)",
    },
    "php": {
        "extra_constraints": [
            "使用 STDIN 或 trim(fgets(STDIN)) 等方式读取普通文本 stdin",
            "不要假设输入是 JSON",
            "优先按空白字符切分 token 来解析输入",
        ],
        "main_function_hint": "PHP runnable script entry",
    },
    "kotlin": {
        "extra_constraints": [
            "使用 readLine()!! 等标准输入方式读取普通文本 stdin",
            "不要假设输入是 JSON",
            "优先实现 token 解析，不要假设每行只有一个整数",
        ],
        "main_function_hint": "fun main()",
    },
    "ruby": {
        "extra_constraints": [
            "使用 gets 或 STDIN.read 等方式读取普通文本 stdin",
            "不要假设输入是 JSON",
            "优先按空白字符切分 token 来解析输入",
        ],
        "main_function_hint": "Ruby runnable script entry",
    },
    "swift": {
        "extra_constraints": [
            "使用 readLine() 等标准输入方式读取普通文本 stdin",
            "不要假设输入是 JSON",
            "优先实现 token 解析，不要假设每行只有一个整数",
        ],
        "main_function_hint": "Swift runnable entry",
    },
    "scala": {
        "extra_constraints": [
            "使用 Scala 标准输入方式读取普通文本 stdin",
            "不要假设输入是 JSON",
            "优先按空白字符切分 token 来解析输入",
        ],
        "main_function_hint": "object Main / standard Scala entry",
    },
    "dart": {
        "extra_constraints": [
            "使用 stdin.readLineSync() 或等价方式读取普通文本 stdin",
            "不要假设输入是 JSON",
            "优先实现 token 解析，不要假设每行只有一个整数",
        ],
        "main_function_hint": "void main()",
    },
}


def normalize_language_name(language: str) -> str:
    lang = language.strip().lower()
    return LANGUAGE_ALIAS_MAP.get(lang, lang)


def get_language_policy(language: str) -> Dict[str, Any]:
    canonical = normalize_language_name(language)
    policy = dict(DEFAULT_LANGUAGE_POLICY)
    override = LANGUAGE_OVERRIDES.get(canonical, {})
    policy.update(override)
    return policy


def build_stdin_prompt_constraints(language: str, io_format: str) -> str:
    canonical = normalize_language_name(language)
    policy = get_language_policy(canonical)

    constraints = [
        "- test_cases 的每个元素都是普通多行文本 stdin，不是 JSON",
        "- 程序必须按普通 stdin 读取，不允许把整个输入当 JSON 解析",
        "- 不能写死测试样例",
        "- 必须输出到 stdout",
        "- 必须生成完整可运行程序",
        "- stdin_code 的解析逻辑必须严格遵循下方给定的输入格式说明",
        "- 不要自行发明与输入格式说明不一致的读取方式",
        "- 如果输入中某一行可能包含多个整数（例如数组行），必须正确解析这一整行中的多个值，不能把整行当成单个整数",
    ]

    if policy.get("needs_class_name_match") and policy.get("public_class_name"):
        constraints.append(
            f"- 如果该语言存在公共类名要求，公共类名必须是 {policy['public_class_name']}"
        )

    if policy.get("main_function_hint"):
        constraints.append(
            f"- 入口应使用该语言最标准、最常见的可运行写法，例如：{policy['main_function_hint']}"
        )

    for item in policy.get("extra_constraints", []):
        constraints.append(f"- {item}")

    constraints.append(
        f"- 如果语言 {language} 有额外的文件名、模块名、入口函数、类名等规范，请使用最标准、最常见、可直接运行的写法"
    )

    constraints.append("输入格式说明：")
    constraints.append(io_format)

    return "\n".join(constraints)


# =========================
# 语言后处理钩子
# =========================
def fix_java_class_name(code: str, target_class_name: str = "Main") -> str:
    if not code:
        return code

    code = re.sub(
        r"\bpublic\s+class\s+\w+\b",
        f"public class {target_class_name}",
        code,
        count=1
    )
    return code


def fix_python_json_stdin(code: str) -> str:
    if not code:
        return code

    code = re.sub(r"import\s+json\s*,\s*sys", "import sys", code)
    code = re.sub(r"import\s+sys\s*,\s*json", "import sys", code)
    code = re.sub(r"json\.loads\s*\(", "# blocked_json_loads(", code)
    return code


def post_process_generated_code(code: str, language: str, is_stdin_code: bool = False) -> str:
    if not code:
        return code

    code = strip_markdown_code_block(code)

    canonical = normalize_language_name(language)
    policy = get_language_policy(canonical)

    if canonical == "java" and policy.get("public_class_name"):
        code = fix_java_class_name(code, policy["public_class_name"])

    if is_stdin_code and canonical == "python" and policy.get("forbid_json_stdin"):
        code = fix_python_json_stdin(code)

    return code


# =========================
# LLM API 封装
# =========================
class LLMClient:
    def __init__(self):
        self.api_key = "sk-zeBMnqw4L58EseM8nxCRvO4Iqz7kO6rmrxU5hQOmktKCBhOJ"
        self.api_base = "https://www.dmxapi.cn/v1"
        self.model = "gpt-4o-mini"
        self.temperature = 0.3
        self.top_p = 0.9

    def chat(self, messages):
        url = f"{self.api_base}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "top_p": self.top_p,
        }

        response = requests.post(url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()

        return response.json()["choices"][0]["message"]["content"]


# =========================
# Code Generation Agent
# =========================
class CodeGenAgent:
    def __init__(self):
        self.llm = LLMClient()

    def run(self, problem_description: str, user_solution: str, language: str) -> Dict[str, Any]:
        normalized_language = normalize_language_name(language)

        # Round 1: 3 个并行调用
        # - _understand_solution: 理解用户解答
        # - _generate_code: 生成核心代码（直接翻译，不依赖 solution_understanding）
        # - _generate_best_code: 生成最优解（依赖 solution_understanding）
        with ThreadPoolExecutor(max_workers=5) as executor:
            f1 = executor.submit(self._understand_solution, problem_description, user_solution)
            f2 = executor.submit(self._generate_code, problem_description, user_solution, normalized_language)
            f8 = executor.submit(self._generate_best_code, problem_description, f1.result(), normalized_language)

            solution_understanding = f1.result()
            code = f2.result()
            best_code = f8.result()

        # Round 2: 2 个并行调用
        # - _infer_io_format: 推断 IO 格式（依赖 solution_understanding + code）
        # - _generate_suggestion: 优化建议（依赖 solution_understanding + code）
        with ThreadPoolExecutor(max_workers=5) as executor:
            f3 = executor.submit(self._infer_io_format, problem_description, solution_understanding, code, normalized_language)
            f7 = executor.submit(self._generate_suggestion, problem_description, solution_understanding, code, normalized_language)

            io_format = f3.result()
            suggestion = f7.result()

        # Round 3: 2 个并行调用
        # - _generate_test_cases: 生成测试用例（依赖 solution_understanding + code + io_format）
        # - _generate_stdin_code: 生成 stdin 程序（依赖 code + io_format）
        with ThreadPoolExecutor(max_workers=5) as executor:
            f4 = executor.submit(self._generate_test_cases, problem_description, solution_understanding, code, io_format, normalized_language)
            f6 = executor.submit(self._generate_stdin_code, problem_description, solution_understanding, code, io_format, normalized_language)

            test_cases = f4.result()
            stdin_code = f6.result()

        # Round 4: 顺序执行（_generate_test_code 依赖 _generate_test_cases 的结果）
        test_code = self._generate_test_code(
            problem_description=problem_description,
            solution_understanding=solution_understanding,
            code=code,
            io_format=io_format,
            test_cases=test_cases,
            language=normalized_language
        )

        # Round 5: 2 个并行调用
        # - _generate_best_test_code: 最优解测试程序（依赖 best_code + io_format）
        # - _generate_best_stdin_code: 最优解 stdin 程序（依赖 best_code + io_format）
        with ThreadPoolExecutor(max_workers=5) as executor:
            f9 = executor.submit(self._generate_best_test_code, problem_description, best_code, io_format, normalized_language)
            f10 = executor.submit(self._generate_best_stdin_code, problem_description, best_code, io_format, normalized_language)

            best_test_code = f9.result()
            best_stdin_code = f10.result()

        return {
            "language": language,
            "normalized_language": normalized_language,
            "solution_understanding": solution_understanding,
            "io_format": io_format,
            "code": code,
            "test_cases": test_cases,
            "test_code": test_code,
            "stdin_code": stdin_code,
            "suggestion": suggestion,
            "best_code": best_code,
            "best_test_code": best_test_code,
            "best_stdin_code": best_stdin_code,
        }

    # =========================
    # Step 1: 理解用户解答
    # =========================
    def _understand_solution(self, problem_description: str, user_solution: str) -> str:
        prompt = PROMPTS["understand_solution"]["template"].format(
            problem_description=problem_description,
            user_solution=user_solution
        )
        return self.llm.chat([
            {"role": "system", "content": PROMPTS["understand_solution"]["system"]},
            {"role": "user", "content": prompt}
        ])

    # =========================
    # Step 2: 分析
    # =========================
    def _reason(self, problem_description: str, solution_understanding: str) -> str:
        prompt = PROMPTS["reason"]["template"].format(
            problem_description=problem_description,
            solution_understanding=solution_understanding
        )
        return self.llm.chat([
            {"role": "system", "content": PROMPTS["reason"]["system"]},
            {"role": "user", "content": prompt}
        ])

    # =========================
    # Step 3: 核心函数（严格按伪代码翻译）
    # =========================
    def _generate_code(self, problem_description: str, user_solution: str, language: str) -> str:
        prompt = PROMPTS["generate_code"]["template"].format(
            problem_description=problem_description,
            user_solution=user_solution,
            language=language
        )
        result = self.llm.chat([
            {"role": "system", "content": PROMPTS["generate_code"]["system"]},
            {"role": "user", "content": prompt}
        ])
        return post_process_generated_code(result, language, is_stdin_code=False)

    # =========================
    # Step 4: 推断统一 IO 格式
    # =========================
    def _infer_io_format(self, problem_description: str, solution_understanding: str, code: str, language: str) -> str:
        prompt = PROMPTS["infer_io_format"]["template"].format(
            problem_description=problem_description,
            solution_understanding=solution_understanding,
            code=code,
            language=language
        )
        return self.llm.chat([
            {"role": "system", "content": PROMPTS["infer_io_format"]["system"]},
            {"role": "user", "content": prompt}
        ]).strip()

    # =========================
    # Step 5: 测试用例
    # =========================
    def _generate_test_cases(
        self,
        problem_description: str,
        solution_understanding: str,
        code: str,
        io_format: str,
        language: str
    ) -> List[str]:
        prompt = PROMPTS["generate_test_cases"]["template"].format(
            problem_description=problem_description,
            solution_understanding=solution_understanding,
            code=code,
            io_format=io_format,
            language=language
        )
        result = self.llm.chat([
            {"role": "system", "content": PROMPTS["generate_test_cases"]["system"]},
            {"role": "user", "content": prompt}
        ])

        parsed = safe_parse_json(result, default=[])

        if isinstance(parsed, list):
            return [str(x) for x in parsed]

        return []

    # =========================
    # Step 6: 内置测试程序
    # =========================
    def _generate_test_code(
        self,
        problem_description: str,
        solution_understanding: str,
        code: str,
        io_format: str,
        test_cases: List[str],
        language: str
    ) -> str:
        language_policy = get_language_policy(language)
        extra = []

        if language_policy.get("needs_class_name_match") and language_policy.get("public_class_name"):
            extra.append(f"- 如果该语言有公共类名约束，公共类名必须是 {language_policy['public_class_name']}")

        prompt = PROMPTS["generate_test_code"]["template"].format(
            problem_description=problem_description,
            solution_understanding=solution_understanding,
            code=code,
            io_format=io_format,
            test_cases=json.dumps(test_cases, ensure_ascii=False, indent=2),
            language=language,
            extra="\n".join(extra) if extra else "- （无特殊约束）"
        )
        result = self.llm.chat([
            {"role": "system", "content": PROMPTS["generate_test_code"]["system"]},
            {"role": "user", "content": prompt}
        ])
        return post_process_generated_code(result, language, is_stdin_code=False)

    # =========================
    # Step 7: stdin 程序
    # =========================
    def _generate_stdin_code(
        self,
        problem_description: str,
        solution_understanding: str,
        code: str,
        io_format: str,
        language: str
    ) -> str:
        language_constraints = build_stdin_prompt_constraints(language, io_format)

        prompt = PROMPTS["generate_stdin_code"]["template"].format(
            problem_description=problem_description,
            solution_understanding=solution_understanding,
            code=code,
            language=language,
            language_constraints=language_constraints
        )
        result = self.llm.chat([
            {"role": "system", "content": PROMPTS["generate_stdin_code"]["system"]},
            {"role": "user", "content": prompt}
        ])
        return post_process_generated_code(result, language, is_stdin_code=True)

    # =========================
    # Step 8: 优化建议
    # =========================
    def _generate_suggestion(self, problem_description: str, solution_understanding: str, code: str, language: str) -> str:
        prompt = PROMPTS["generate_suggestion"]["template"].format(
            problem_description=problem_description,
            solution_understanding=solution_understanding,
            code=code,
            language=language
        )
        return self.llm.chat([
            {"role": "system", "content": PROMPTS["generate_suggestion"]["system"]},
            {"role": "user", "content": prompt}
        ])

    # =========================
    # Step 9: 最优解核心函数
    # =========================
    def _generate_best_code(self, problem_description: str, solution_understanding: str, language: str) -> str:
        prompt = PROMPTS["generate_best_code"]["template"].format(
            problem_description=problem_description,
            solution_understanding=solution_understanding,
            language=language
        )
        result = self.llm.chat([
            {"role": "system", "content": PROMPTS["generate_best_code"]["system"]},
            {"role": "user", "content": prompt}
        ])
        return post_process_generated_code(result, language, is_stdin_code=False)

    # =========================
    # Step 10: 最优解内置测试程序
    # =========================
    def _generate_best_test_code(self, problem_description: str, best_code: str, io_format: str, language: str) -> str:
        language_policy = get_language_policy(language)
        extra = []

        if language_policy.get("needs_class_name_match") and language_policy.get("public_class_name"):
            extra.append(f"- 如果该语言有公共类名约束，公共类名必须是 {language_policy['public_class_name']}")

        prompt = PROMPTS["generate_best_test_code"]["template"].format(
            problem_description=problem_description,
            best_code=best_code,
            io_format=io_format,
            language=language,
            extra="\n".join(extra) if extra else "- （无特殊约束）"
        )
        result = self.llm.chat([
            {"role": "system", "content": PROMPTS["generate_best_test_code"]["system"]},
            {"role": "user", "content": prompt}
        ])
        return post_process_generated_code(result, language, is_stdin_code=False)

    # =========================
    # Step 11: 最优解 stdin 程序
    # =========================
    def _generate_best_stdin_code(self, problem_description: str, best_code: str, io_format: str, language: str) -> str:
        language_constraints = build_stdin_prompt_constraints(language, io_format)

        prompt = PROMPTS["generate_best_stdin_code"]["template"].format(
            problem_description=problem_description,
            best_code=best_code,
            language=language,
            language_constraints=language_constraints
        )
        result = self.llm.chat([
            {"role": "system", "content": PROMPTS["generate_best_stdin_code"]["system"]},
            {"role": "user", "content": prompt}
        ])
        return post_process_generated_code(result, language, is_stdin_code=True)


# =========================
# 外部接口
# =========================
def generate_code(problem_description: str, user_solution: str, language: str) -> Dict[str, Any]:
    agent = CodeGenAgent()
    return agent.run(problem_description, user_solution, language)


def code_generator(problem_description: str, user_solution: str, language_button: str) -> Dict[str, Any]:
    return generate_code(problem_description, user_solution, language_button)


# =========================
# Example
# =========================
if __name__ == "__main__":
    problem = "给定一个整数数组 nums 和一个整数目标值 target，请你在该数组中找出和为目标值 target 的那两个整数，并返回它们的数组下标。"

    user_solution = """
使用哈希表。遍历数组时，先计算 target - nums[i]。
如果这个差值已经在哈希表里，就返回对应下标和当前下标。
否则把当前值和下标存进哈希表。
"""

    result = code_generator(problem, user_solution, "python")

    print("=== language ===")
    print(result["language"])

    print("\n=== normalized_language ===")
    print(result["normalized_language"])

    print("\n=== io_format ===")
    print(result["io_format"])

    print("\n=== test_cases ===")
    print(json.dumps(result["test_cases"], ensure_ascii=False, indent=2))

    print("\n=== stdin_code ===")
    print(result["stdin_code"])

    print("\n=== test_code ===")
    print(result["test_code"])

    print("\n=== suggestion ===")
    print(result["suggestion"])

    print("\n=== best_stdin_code ===")
    print(result["best_stdin_code"])