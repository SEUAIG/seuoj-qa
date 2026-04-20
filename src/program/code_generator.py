# """
# 基于题目+伪代码，生成正确代码 + 测试用例

# def code_generator(problem_description: str, pseudo_code: str, language: str) -> Tuple[str, List[Tuple]]:
#     # 基于react框架，调用llm api生成代码和测试用例

#     code, test_cases = generate_code(problem_description, pseudo_code, language)

#     return code, test_cases


# """

# import re
# import requests
# from typing import Dict

# def strip_markdown_code_block(text: str) -> str:
#     if not text:
#         return text

#     text = text.strip()
#     text = re.sub(r"^```[^\n]*\n", "", text)
#     text = re.sub(r"\n```$", "", text)
#     return text.strip()

# # =========================
# # LLM API 封装
# # =========================
# class LLMClient:
#     def __init__(self):
#         self.api_key = "sk-zeBMnqw4L58EseM8nxCRvO4Iqz7kO6rmrxU5hQOmktKCBhOJ"
#         self.api_base = "https://www.dmxapi.cn/v1"
#         self.model = "gpt-4o-mini"
#         self.temperature = 0.3
#         self.top_p = 0.9

#     def chat(self, messages):
#         url = f"{self.api_base}/chat/completions"

#         headers = {
#             "Authorization": f"Bearer {self.api_key}",
#             "Content-Type": "application/json",
#         }

#         payload = {
#             "model": self.model,
#             "messages": messages,
#             "temperature": self.temperature,
#             "top_p": self.top_p,
#         }

#         response = requests.post(url, headers=headers, json=payload, timeout=120)
#         response.raise_for_status()

#         return response.json()["choices"][0]["message"]["content"]


# # =========================
# # Code Generation Agent
# # =========================
# class CodeGenAgent:
#     def __init__(self):
#         self.llm = LLMClient()

#     def run(self, problem_description: str, user_solution: str, language: str) -> Dict[str, str]:
#         """
#         返回：
#         {
#             "solution_understanding": 对用户解答的结构化理解,
#             "code": 按用户解答生成的核心函数代码,
#             "test_code": 按用户解答生成的完整测试代码,
#             "suggestion": 对当前解法的优化建议,
#             "best_code": 最优解核心函数代码,
#             "best_test_code": 最优解完整测试代码
#         }
#         """
#         # Step 1: 理解用户解答（兼容伪代码 / 文字解法）
#         solution_understanding = self._understand_solution(problem_description, user_solution)

#         # Step 2: 分析实现逻辑
#         thought = self._reason(problem_description, solution_understanding)

#         # Step 3: 按用户解答生成代码
#         code = self._generate_code(problem_description, solution_understanding, thought, language)

#         # Step 4: 生成测试代码
#         test_code = self._generate_test_code(problem_description, solution_understanding, code, language)

#         # Step 5: 生成优化建议
#         suggestion = self._generate_suggestion(problem_description, solution_understanding, code, language)

#         # Step 6: 生成最优解代码
#         best_code = self._generate_best_code(problem_description, solution_understanding, language)

#         # Step 7: 生成最优解测试代码
#         best_test_code = self._generate_best_test_code(problem_description, best_code, language)

#         return {
#             "solution_understanding": solution_understanding,
#             "code": code,
#             "test_code": test_code,
#             "suggestion": suggestion,
#             "best_code": best_code,
#             "best_test_code": best_test_code,
#         }

#     # =========================
#     # Step 1: 理解用户解答
#     # =========================
#     def _understand_solution(self, problem_description: str, user_solution: str) -> str:
#         prompt = f"""
# 你是一个算法理解专家。

# 用户给出的“解答”可能是：
# 1. 伪代码
# 2. 文字版题解
# 3. 伪代码和文字混合
# 4. 不太规范但表达了解题步骤

# 你的任务：
# - 准确理解用户的解题思路
# - 整理成结构化算法说明
# - 不要优化，不要擅自替换成更优解
# - 如果用户表述不够规范，请在不改变核心思路的前提下合理补全

# 输出格式：
# 1. 输入输出
# 2. 核心思路
# 3. 算法步骤
# 4. 边界条件
# 5. 实现注意事项

# 题目：
# {problem_description}

# 用户解答：
# {user_solution}
# """
#         return self.llm.chat([
#             {"role": "system", "content": "严谨的算法理解专家"},
#             {"role": "user", "content": prompt}
#         ])

#     # =========================
#     # Step 2: 分析
#     # =========================
#     def _reason(self, problem_description: str, solution_understanding: str) -> str:
#         prompt = f"""
# 你是一个算法分析专家。

# 任务：
# 基于“整理后的用户解答”分析实现逻辑。

# 要求：
# - 不写代码
# - 不优化逻辑
# - 严格按照用户解答来理解

# 输出：
# 1. 输入输出
# 2. 算法流程
# 3. 实现细节
# 4. 边界情况

# 题目：
# {problem_description}

# 整理后的用户解答：
# {solution_understanding}
# """
#         return self.llm.chat([
#             {"role": "system", "content": "严谨的算法分析专家"},
#             {"role": "user", "content": prompt}
#         ])

#     # =========================
#     # Step 3: 生成按用户解答实现的代码
#     # =========================
#     def _generate_code(self, problem_description: str, solution_understanding: str, thought: str, language: str) -> str:
#         prompt = f"""
# 你是一个“受控代码生成器”。

# ⚠️ 强约束：
# - 必须严格按照用户解答实现
# - 禁止擅自优化或替换成更优解
# - 只实现核心函数，不写 main
# - 代码必须可运行
# - 要自动补全必要的类型、导入、函数签名

# 语言：{language}

# 题目：
# {problem_description}

# 整理后的用户解答：
# {solution_understanding}

# 分析：
# {thought}

# 输出要求：
# - 只输出代码
# - 不要解释
# """
#         result =self.llm.chat([
#             {"role": "system", "content": "严格代码生成器"},
#             {"role": "user", "content": prompt}
#         ])
#         return strip_markdown_code_block(result)

#     # =========================
#     # Step 4: 生成测试代码
#     # =========================
#     def _generate_test_code(self, problem_description: str, solution_understanding: str, code: str, language: str) -> str:
#         prompt = f"""
# 你是一个测试工程师。

# 任务：
# 基于当前核心函数代码，生成完整测试程序。

# ⚠️ 要求：
# - 必须生成完整可运行程序
# - 必须包含 main 函数（或等价入口）
# - 测试多个 case
# - 打印结果
# - 覆盖正常情况与边界情况

# 语言：{language}

# 题目：
# {problem_description}

# 整理后的用户解答：
# {solution_understanding}

# 核心代码：
# {code}

# 输出要求：
# - 只输出完整代码（包含 main）
# - 不解释
# """
#         result = self.llm.chat([
#             {"role": "system", "content": "测试代码生成专家"},
#             {"role": "user", "content": prompt}
#         ])
#         return strip_markdown_code_block(result)

#     # =========================
#     # Step 5: 优化建议
#     # =========================
#     def _generate_suggestion(self, problem_description: str, solution_understanding: str, code: str, language: str) -> str:
#         prompt = f"""
# 你是一个算法优化顾问。

# 任务：
# 分析当前这份代码是否是最优解，并给出建议。

# 输出内容必须包含：
# 1. 当前解法的时间复杂度
# 2. 当前解法的空间复杂度
# 3. 是否存在更优解
# 4. 如果不是最优，应该从哪里思考修改
# 5. 优化方向是什么
# 6. 当前解法适合什么场景

# 要求：
# - 不要直接输出完整优化代码
# - 建议要具体
# - 如果已经接近最优，也请明确说明原因

# 题目：
# {problem_description}

# 用户解答整理：
# {solution_understanding}

# 当前代码：
# {code}

# 语言：
# {language}
# """
#         return self.llm.chat([
#             {"role": "system", "content": "资深算法优化顾问"},
#             {"role": "user", "content": prompt}
#         ])

#     # =========================
#     # Step 6: 最优解代码
#     # =========================
#     def _generate_best_code(self, problem_description: str, solution_understanding: str, language: str) -> str:
#         prompt = f"""
# 你是一个算法竞赛专家。

# 任务：
# 针对题目生成最佳解法代码。

# 要求：
# - 不受用户原始解答限制
# - 直接采用更优的时间复杂度/空间复杂度方案
# - 如果没有更优解，则给出公认最佳实践
# - 只输出核心函数，不写 main
# - 代码必须可运行
# - 补全必要导入、类型、函数签名

# 语言：{language}

# 题目：
# {problem_description}

# 用户解答整理（仅用于理解题意）：
# {solution_understanding}

# 输出要求：
# - 只输出代码
# - 不要解释
# """
#         result = self.llm.chat([
#             {"role": "system", "content": "最优算法代码生成专家"},
#             {"role": "user", "content": prompt}
#         ])
#         return  strip_markdown_code_block(result)

#     # =========================
#     # Step 7: 最优解测试代码
#     # =========================
#     def _generate_best_test_code(self, problem_description: str, best_code: str, language: str) -> str:
#         prompt = f"""
# 你是一个测试工程师。

# 任务：
# 基于最佳解代码，生成完整测试程序。

# ⚠️ 要求：
# - 必须生成完整可运行程序
# - 必须包含 main 函数（或等价入口）
# - 测试多个 case
# - 打印结果
# - 覆盖正常情况和边界情况

# 语言：{language}

# 题目：
# {problem_description}

# 最佳解代码：
# {best_code}

# 输出要求：
# - 只输出完整代码（包含 main）
# - 不解释
# """
#         result = self.llm.chat([
#             {"role": "system", "content": "最佳解测试代码生成专家"},
#             {"role": "user", "content": prompt}
#         ])
#         return strip_markdown_code_block(result)


# # =========================
# # 外部接口
# # =========================
# def generate_code(problem_description: str, user_solution: str, language: str) -> Dict[str, str]:
#     agent = CodeGenAgent()
#     return agent.run(problem_description, user_solution, language)


# def code_generator(problem_description: str, user_solution: str, language_button: str) -> Dict[str, str]:
#     return generate_code(problem_description, user_solution, language_button)


# # =========================
# # Example
# # =========================
# if __name__ == "__main__":
#     problem = "给定一个数组，使用冒泡排序排序"

#     # 用户只传一个“解答”即可，可以是伪代码，也可以是文字描述
#     user_solution = """
# 一种简单做法是重复遍历数组。
# 每次比较相邻两个元素，如果前一个比后一个大，就交换它们。
# 这样每一轮都会把当前最大的元素移动到末尾。
# 重复多轮之后数组就有序了。
# """

#     result = code_generator(problem, user_solution, "C++")

#     # print("=== 用户解答理解 ===")
#     # print(result["solution_understanding"])

#     # print("\n=== 按用户解答生成的核心函数 ===")
#     # print(result["code"])

#     print("\n=== 按用户解答生成的测试代码（含main） ===")
#     print(result["test_code"])

#     print("\n=== 优化建议 ===")
#     print(result["suggestion"])

#     # print("\n=== 最优解核心函数 ===")
#     # print(result["best_code"])

#     print("\n=== 最优解测试代码（含main） ===")
#     print(result["best_test_code"])

"""
基于题目+用户解答，生成：
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
import requests
from typing import Dict, Any, List


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

        solution_understanding = self._understand_solution(problem_description, user_solution)
        thought = self._reason(problem_description, solution_understanding)

        code = self._generate_code(problem_description, solution_understanding, thought, normalized_language)

        io_format = self._infer_io_format(
            problem_description=problem_description,
            solution_understanding=solution_understanding,
            code=code,
            language=normalized_language
        )

        test_cases = self._generate_test_cases(
            problem_description=problem_description,
            solution_understanding=solution_understanding,
            code=code,
            io_format=io_format,
            language=normalized_language
        )

        test_code = self._generate_test_code(
            problem_description=problem_description,
            solution_understanding=solution_understanding,
            code=code,
            io_format=io_format,
            test_cases=test_cases,
            language=normalized_language
        )

        stdin_code = self._generate_stdin_code(
            problem_description=problem_description,
            solution_understanding=solution_understanding,
            code=code,
            io_format=io_format,
            language=normalized_language
        )

        suggestion = self._generate_suggestion(
            problem_description,
            solution_understanding,
            code,
            normalized_language
        )

        best_code = self._generate_best_code(
            problem_description,
            solution_understanding,
            normalized_language
        )

        best_test_code = self._generate_best_test_code(
            problem_description=problem_description,
            best_code=best_code,
            io_format=io_format,
            language=normalized_language
        )

        best_stdin_code = self._generate_best_stdin_code(
            problem_description=problem_description,
            best_code=best_code,
            io_format=io_format,
            language=normalized_language
        )

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
        prompt = f"""
你是一个算法理解专家。

用户给出的“解答”可能是：
1. 伪代码
2. 文字版题解
3. 伪代码和文字混合
4. 不太规范但表达了解题步骤

你的任务：
- 准确理解用户的解题思路
- 整理成结构化算法说明
- 不要优化，不要擅自替换成更优解
- 如果用户表述不够规范，请在不改变核心思路的前提下合理补全

输出格式：
1. 输入输出
2. 核心思路
3. 算法步骤
4. 边界条件
5. 实现注意事项

题目：
{problem_description}

用户解答：
{user_solution}
"""
        return self.llm.chat([
            {"role": "system", "content": "严谨的算法理解专家"},
            {"role": "user", "content": prompt}
        ])

    # =========================
    # Step 2: 分析
    # =========================
    def _reason(self, problem_description: str, solution_understanding: str) -> str:
        prompt = f"""
你是一个算法分析专家。

任务：
基于“整理后的用户解答”分析实现逻辑。

要求：
- 不写代码
- 不优化逻辑
- 严格按照用户解答来理解

输出：
1. 输入输出
2. 算法流程
3. 实现细节
4. 边界情况

题目：
{problem_description}

整理后的用户解答：
{solution_understanding}
"""
        return self.llm.chat([
            {"role": "system", "content": "严谨的算法分析专家"},
            {"role": "user", "content": prompt}
        ])

    # =========================
    # Step 3: 核心函数
    # =========================
    def _generate_code(self, problem_description: str, solution_understanding: str, thought: str, language: str) -> str:
        prompt = f"""
你是一个受控代码生成器。

强约束：
- 必须严格按照用户解答实现
- 禁止擅自优化或替换成更优解
- 只实现核心函数，不写 main
- 自动补全必要的类型、导入、函数签名
- 代码必须可运行
- 只输出纯代码，不要 markdown 代码块，不要 ``` 标记

语言：{language}

题目：
{problem_description}

整理后的用户解答：
{solution_understanding}

分析：
{thought}

输出要求：
- 只输出代码
- 不要解释
"""
        result = self.llm.chat([
            {"role": "system", "content": "严格代码生成器"},
            {"role": "user", "content": prompt}
        ])
        return post_process_generated_code(result, language, is_stdin_code=False)

    # =========================
    # Step 4: 推断统一 IO 格式
    # =========================
    def _infer_io_format(self, problem_description: str, solution_understanding: str, code: str, language: str) -> str:
        prompt = f"""
你是一个算法题 I/O 设计专家。

任务：
根据题目、用户解答和核心代码，推断一份统一且自然的输入输出格式说明。
后续 test_cases 和 stdin_code 都必须严格遵循这份说明。

要求：
- 不要返回 JSON
- 不要返回代码
- 只返回简洁、明确、可执行的“输入格式 + 输出格式”说明
- 优先选择最自然、最常见、最适合在线判题的格式
- 如果存在数组、矩阵等一行多个值的情况，要明确说明“空格分隔”
- 不要含糊，不要给多个备选格式
- 格式说明必须足够明确，以便不同语言都能一致实现

语言：{language}

题目：
{problem_description}

用户解答整理：
{solution_understanding}

核心代码：
{code}

输出示例风格（仅示例风格，不要照抄）：
输入格式：
第一行输入整数 n，表示数组长度。
第二行输入 n 个整数，表示数组元素，元素之间用空格分隔。
第三行输入整数 target。

输出格式：
输出两个下标组成的数组。
"""
        return self.llm.chat([
            {"role": "system", "content": "I/O 格式设计专家"},
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
        prompt = f"""
你是一个测试数据设计专家。

任务：
根据下面给定的输入格式说明，为这道题和代码生成多组“标准输入字符串”测试数据。

要求：
- 输出必须是 JSON 数组
- 数组中的每个元素都必须是字符串
- 每个字符串都代表一次完整 stdin 输入
- 每个字符串都必须严格符合下面给定的输入格式说明
- 每个字符串都必须是普通多行文本输入，不是 JSON 对象，不是字典，不是嵌套 JSON
- 不要返回任何解释、说明、markdown 或代码块
- 测试数据总数不要超过 6 组，优先控制在 5 组以内
- 在数量尽量精简的前提下，选择最有代表性的测试数据，尽可能覆盖关键边界情况
- 尽量覆盖：
  1. 正常情况
  2. 边界情况
  3. 极小规模情况
  4. 特殊情况
- 如果输入格式说明中某一行是“多个整数空格分隔”，就必须按该格式生成，不能改成每个整数单独一行

语言：{language}

题目：
{problem_description}

用户解答整理：
{solution_understanding}

当前核心代码：
{code}

输入输出格式说明：
{io_format}

输出示例（仅示例格式，不要照抄）：
["5\\n5 3 8 4 2\\n9\\n", "0\\n"]
"""
        result = self.llm.chat([
            {"role": "system", "content": "测试数据生成专家"},
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

        prompt = f"""
你是一个测试工程师。

任务：
基于当前核心函数代码，生成一份“内置测试数据”的完整测试程序。

要求：
- 生成完整可运行程序
- 必须包含 main 函数（或等价入口）
- 程序里直接写死测试样例，不要从 stdin 读取
- 测试多个 case
- 打印结果
- 覆盖正常情况与边界情况
- 打印结果时，必须确保最终答案实际输出到标准输出，不能漏打
- 只输出纯代码，不要 markdown 代码块，不要 ``` 标记
{chr(10).join(extra)}

语言：{language}

题目：
{problem_description}

整理后的用户解答：
{solution_understanding}

核心代码：
{code}

输入输出格式说明：
{io_format}

可参考的测试输入样例（如果适用）：
{json.dumps(test_cases, ensure_ascii=False, indent=2)}

输出要求：
- 只输出完整代码（包含 main）
- 不解释
"""
        result = self.llm.chat([
            {"role": "system", "content": "测试代码生成专家"},
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

        prompt = f"""
你是一个在线判题代码包装专家。

任务：
把下面的核心函数包装成一份“从 stdin 读取输入”的完整可运行程序。

关键要求：
{language_constraints}
- 如果输入格式说明中出现“第二行输入 n 个整数，空格分隔”这类描述，必须正确解析这一整行的多个整数
- 优先使用 token 流式解析，这样可以同时兼容空格和换行
- 不要写出“把整行数组字符串直接 parse 成单个整数”的代码
- 最终结果必须实际打印到 stdout
- 只输出纯代码，不要 markdown 代码块，不要 ``` 标记

语言：{language}

题目：
{problem_description}

整理后的用户解答：
{solution_understanding}

核心代码：
{code}

输出要求：
- 只输出完整代码（包含 main 或等价入口）
- 不解释
"""
        result = self.llm.chat([
            {"role": "system", "content": "stdin 包装代码生成专家"},
            {"role": "user", "content": prompt}
        ])
        return post_process_generated_code(result, language, is_stdin_code=True)

    # =========================
    # Step 8: 优化建议
    # =========================
    def _generate_suggestion(self, problem_description: str, solution_understanding: str, code: str, language: str) -> str:
        prompt = f"""
你是一个算法优化顾问。

任务：
分析当前这份代码是否是最优解，并给出建议。

输出内容必须包含：
1. 当前解法的时间复杂度
2. 当前解法的空间复杂度
3. 是否存在更优解
4. 如果不是最优，应该从哪里思考修改
5. 优化方向是什么
6. 当前解法适合什么场景

要求：
- 不要直接输出完整优化代码
- 建议要具体
- 如果已经接近最优，也请明确说明原因

题目：
{problem_description}

用户解答整理：
{solution_understanding}

当前代码：
{code}

语言：
{language}
"""
        return self.llm.chat([
            {"role": "system", "content": "资深算法优化顾问"},
            {"role": "user", "content": prompt}
        ])

    # =========================
    # Step 9: 最优解核心函数
    # =========================
    def _generate_best_code(self, problem_description: str, solution_understanding: str, language: str) -> str:
        prompt = f"""
你是一个算法竞赛专家。

任务：
针对题目生成最佳解法代码。

要求：
- 不受用户原始解答限制
- 直接采用更优的时间复杂度/空间复杂度方案
- 如果没有更优解，则给出公认最佳实践
- 只输出核心函数，不写 main
- 补全必要导入、类型、函数签名
- 代码必须可运行
- 只输出纯代码，不要 markdown 代码块，不要 ``` 标记

语言：{language}

题目：
{problem_description}

用户解答整理（仅用于理解题意）：
{solution_understanding}

输出要求：
- 只输出代码
- 不要解释
"""
        result = self.llm.chat([
            {"role": "system", "content": "最优算法代码生成专家"},
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

        prompt = f"""
你是一个测试工程师。

任务：
基于最佳解代码，生成完整测试程序。

要求：
- 必须生成完整可运行程序
- 必须包含 main 函数（或等价入口）
- 使用内置测试数据，不要读取 stdin
- 测试多个 case
- 打印结果
- 覆盖正常情况和边界情况
- 最终答案必须实际输出到标准输出
- 只输出纯代码，不要 markdown 代码块，不要 ``` 标记
{chr(10).join(extra)}

语言：{language}

题目：
{problem_description}

最佳解代码：
{best_code}

输入输出格式说明：
{io_format}

输出要求：
- 只输出完整代码（包含 main）
- 不解释
"""
        result = self.llm.chat([
            {"role": "system", "content": "最佳解测试代码生成专家"},
            {"role": "user", "content": prompt}
        ])
        return post_process_generated_code(result, language, is_stdin_code=False)

    # =========================
    # Step 11: 最优解 stdin 程序
    # =========================
    def _generate_best_stdin_code(self, problem_description: str, best_code: str, io_format: str, language: str) -> str:
        language_constraints = build_stdin_prompt_constraints(language, io_format)

        prompt = f"""
你是一个在线判题代码包装专家。

任务：
把最佳解核心函数包装成一份“从 stdin 读取输入”的完整可运行程序。

关键要求：
{language_constraints}
- 如果输入格式说明中出现“多个整数空格分隔”的数组行，必须正确 split / token 化解析
- 优先使用 token 流式解析，这样可以同时兼容空格和换行
- 最终结果必须实际打印到 stdout
- 只输出纯代码，不要 markdown 代码块，不要 ``` 标记

语言：{language}

题目：
{problem_description}

最佳解代码：
{best_code}

输出要求：
- 只输出完整代码（包含 main 或等价入口）
- 不解释
"""
        result = self.llm.chat([
            {"role": "system", "content": "最佳解 stdin 包装代码生成专家"},
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