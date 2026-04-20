"""
题库模块 - 存储题目数据并提供读取接口
"""

import json
from typing import Dict, List, Optional


# =========================
# 写死的 JSON 题库
# =========================
PROBLEM_BANK: List[Dict] = [
    {
        "id": 1,
        "title": "两数之和",
        "description": "给定一个整数数组 nums 和一个整数目标值 target，请你在该数组中找出和为目标值 target 的那两个整数，并返回它们的数组下标。",
        "type": "编程题",
        "difficulty": "简单",
        "tags": ["数组", "哈希表"],
        "examples": [
            {
                "input": "nums = [2,7,11,15], target = 9",
                "output": "[0,1]",
                "explanation": "因为 nums[0] + nums[1] == 9 ，返回 [0, 1]"
            }
        ],
        "constraints": [
            "2 <= nums.length <= 10^4",
            "-10^9 <= nums[i] <= 10^9",
            "-10^9 <= target <= 10^9",
            "只会存在一个有效答案"
        ],
        "template_code": {
            "python": "def two_sum(nums: List[int], target: int) -> List[int]:\n    pass",
            "cpp": "vector<int> twoSum(vector<int>& nums, int target) {\n    \n}"
        },
        "hints": ["考虑使用哈希表来降低时间复杂度"],
        "test_cases": [
            {"input": {"nums": [2, 7, 11, 15], "target": 9}, "expected_output": [0, 1]},
            {"input": {"nums": [3, 2, 4], "target": 6}, "expected_output": [1, 2]},
            {"input": {"nums": [3, 3], "target": 6}, "expected_output": [0, 1]},
            {"input": {"nums": [1, 5, 3, 2], "target": 4}, "expected_output": [0, 3]}
        ]
    },
    {
        "id": 2,
        "title": "反转链表",
        "description": "给你单链表的头节点 head，请你反转链表，并返回反转后的链表。",
        "type": "编程题",
        "difficulty": "简单",
        "tags": ["链表", "递归"],
        "examples": [
            {
                "input": "head = [1,2,3,4,5]",
                "output": "[5,4,3,2,1]",
                "explanation": None
            }
        ],
        "constraints": [
            "链表节点数目范围是 [0, 5000]",
            "-5000 <= Node.val <= 5000"
        ],
        "template_code": {
            "python": "class ListNode:\n    def __init__(self, val=0, next=None):\n        self.val = val\n        self.next = next\n\ndef reverseList(head: ListNode) -> ListNode:\n    pass",
            "cpp": "struct ListNode {\n    int val;\n    ListNode *next;\n    ListNode() : val(0), next(nullptr) {}\n};\n\nListNode* reverseList(ListNode* head) {\n    \n}"
        },
        "hints": ["可以使用迭代或递归两种方式"],
        "test_cases": [
            {"input": {"head": [1, 2, 3, 4, 5]}, "expected_output": [5, 4, 3, 2, 1]},
            {"input": {"head": [1, 2]}, "expected_output": [2, 1]},
            {"input": {"head": [1]}, "expected_output": [1]},
            {"input": {"head": []}, "expected_output": []}
        ]
    },
    {
        "id": 3,
        "title": "合并两个有序数组",
        "description": "给你两个按 非递减顺序 排列的整数数组 nums1 和 nums2，另有两个整数 m 和 n ，分别表示 nums1 和 nums2 中的元素数目。请你将 nums2 合并至 nums1 中，使合并后的数组同样按 非递减顺序 排列。",
        "type": "编程题",
        "difficulty": "简单",
        "tags": ["数组", "双指针", "排序"],
        "examples": [
            {
                "input": "nums1 = [1,2,3], m = 3, nums2 = [2,5,6], n = 3",
                "output": "[1,2,2,3,5,6]",
                "explanation": None
            }
        ],
        "constraints": [
            "nums1.length == m + n",
            "nums2.length == n",
            "0 <= m, n <= 200",
            "1 <= m + n <= 200",
            "-10^9 <= nums1[i], nums2[i] <= 10^9"
        ],
        "template_code": {
            "python": "def merge(nums1: List[int], m: int, nums2: List[int], n: int) -> None:\n    pass",
            "cpp": "void merge(vector<int>& nums1, int m, vector<int>& nums2, int n) {\n    \n}"
        },
        "hints": ["从后往前比较，避免移动大量元素"],
        "test_cases": [
            {"input": {"nums1": [1, 2, 3], "m": 3, "nums2": [2, 5, 6], "n": 3}, "expected_output": [1, 2, 2, 3, 5, 6]},
            {"input": {"nums1": [1], "m": 1, "nums2": [], "n": 0}, "expected_output": [1]},
            {"input": {"nums1": [0], "m": 0, "nums2": [1], "n": 1}, "expected_output": [1]},
            {"input": {"nums1": [1, 2, 5, 0, 0], "m": 3, "nums2": [3, 6], "n": 2}, "expected_output": [1, 2, 3, 5, 6]}
        ]
    },
    {
        "id": 4,
        "title": "二叉树的中序遍历",
        "description": "给定一个二叉树的根节点 root，返回它的中序遍历结果。",
        "type": "编程题",
        "difficulty": "中等",
        "tags": ["树", "栈", "DFS"],
        "examples": [
            {
                "input": "root = [1,null,2,3]",
                "output": "[1,3,2]",
                "explanation": None
            }
        ],
        "constraints": [
            "树中节点数目范围是 [0, 100]",
            "-100 <= Node.val <= 100"
        ],
        "template_code": {
            "python": "class TreeNode:\n    def __init__(self, val=0, left=None, right=None):\n        self.val = val\n        self.left = left\n        self.right = right\n\ndef inorderTraversal(root: TreeNode) -> List[int]:\n    pass",
            "cpp": "struct TreeNode {\n    int val;\n    TreeNode *left;\n    TreeNode *right;\n    TreeNode() : val(0), left(nullptr), right(nullptr) {}\n};\n\nvector<int> inorderTraversal(TreeNode* root) {\n    \n}"
        },
        "hints": ["中序遍历顺序是左-根-右"],
        "test_cases": [
            {"input": {"root": [1, None, 2, 3]}, "expected_output": [1, 3, 2]},
            {"input": {"root": []}, "expected_output": []},
            {"input": {"root": [1]}, "expected_output": [1]},
            {"input": {"root": [1, 2, 3]}, "expected_output": [2, 1, 3]},
            {"input": {"root": [5, 3, 7, 1, 4, 6, 8]}, "expected_output": [1, 3, 4, 5, 6, 7, 8]}
        ]
    },
    {
        "id": 5,
        "title": "爬楼梯",
        "description": "假设你正在爬楼梯。需要 n 阶你才能到达楼顶。每次你可以爬 1 或 2 个台阶。有多少种不同的方法可以爬到楼顶？",
        "type": "编程题",
        "difficulty": "简单",
        "tags": ["动态规划", "记忆化搜索"],
        "examples": [
            {
                "input": "n = 2",
                "output": "2",
                "explanation": "有2种方法可以爬到楼顶：1. 1阶 + 1阶  2. 2阶"
            },
            {
                "input": "n = 3",
                "output": "3",
                "explanation": "有3种方法可以爬到楼顶：1. 1阶 + 1阶 + 1阶  2. 1阶 + 2阶  3. 2阶 + 1阶"
            }
        ],
        "constraints": [
            "1 <= n <= 45"
        ],
        "template_code": {
            "python": "def climbStairs(n: int) -> int:\n    pass",
            "cpp": "int climbStairs(int n) {\n    \n}"
        },
        "hints": ["这是一个经典的斐波那契数列问题"],
        "test_cases": [
            {"input": {"n": 2}, "expected_output": 2},
            {"input": {"n": 3}, "expected_output": 3},
            {"input": {"n": 1}, "expected_output": 1},
            {"input": {"n": 5}, "expected_output": 8},
            {"input": {"n": 10}, "expected_output": 89}
        ]
    },
    {
        "id": 6,
        "title": "快速排序",
        "description": "实现快速排序算法，对给定数组进行升序排序。",
        "type": "编程题",
        "difficulty": "中等",
        "tags": ["排序", "分治", "快速排序"],
        "examples": [
            {
                "input": "nums = [5,2,3,1]",
                "output": "[1,2,3,5]",
                "explanation": None
            }
        ],
        "constraints": [
            "1 <= nums.length <= 50000",
            "-10^5 <= nums[i] <= 10^5"
        ],
        "template_code": {
            "python": "def quickSort(nums: List[int]) -> List[int]:\n    pass",
            "cpp": "void quickSort(vector<int>& nums, int left, int right) {\n    \n}\n\nvector<int> sortArray(vector<int>& nums) {\n    \n}"
        },
        "hints": ["注意基准数的选择和分区过程"],
        "test_cases": [
            {"input": {"nums": [5, 2, 3, 1]}, "expected_output": [1, 2, 3, 5]},
            {"input": {"nums": [5, 1, 1, 2, 0, 0]}, "expected_output": [0, 0, 1, 1, 2, 5]},
            {"input": {"nums": [3, 2, 1]}, "expected_output": [1, 2, 3]},
            {"input": {"nums": [1]}, "expected_output": [1]},
            {"input": {"nums": [-1, 2, -3, 4]}, "expected_output": [-3, -1, 2, 4]}
        ]
    },
    {
        "id": 7,
        "title": "判断回文数",
        "description": "给你一个整数 x，如果 x 是一个回文整数，返回 true。否则，返回 false。回文数是指正序（从左向右）和倒序（从右向左）读都是一样的整数。",
        "type": "编程题",
        "difficulty": "简单",
        "tags": ["数学"],
        "examples": [
            {
                "input": "x = 121",
                "output": "true",
                "explanation": "121 从左向右读是 121，从右向左读也是 121"
            },
            {
                "input": "x = -121",
                "output": "false",
                "explanation": "从左向右读是 -121，从右向左读是 121-"
            }
        ],
        "constraints": [
            "-2^31 <= x <= 2^31 - 1"
        ],
        "template_code": {
            "python": "def isPalindrome(x: int) -> bool:\n    pass",
            "cpp": "bool isPalindrome(int x) {\n    \n}"
        },
        "hints": ["负数一定不是回文数，考虑不转换为字符串如何判断"],
        "test_cases": [
            {"input": {"x": 121}, "expected_output": True},
            {"input": {"x": -121}, "expected_output": False},
            {"input": {"x": 10}, "expected_output": False},
            {"input": {"x": 12321}, "expected_output": True},
            {"input": {"x": 0}, "expected_output": True}
        ]
    },
    {
        "id": 8,
        "title": "二叉树层序遍历",
        "description": "给你二叉树的根节点 root，返回其节点值的层序遍历结果（即逐层地从左到右访问所有节点）。",
        "type": "编程题",
        "difficulty": "中等",
        "tags": ["树", "BFS", "队列"],
        "examples": [
            {
                "input": "root = [3,9,20,null,null,15,7]",
                "output": "[[3],[9,20],[15,7]]",
                "explanation": None
            }
        ],
        "constraints": [
            "树中节点数目范围是 [0, 2000]",
            "-1000 <= Node.val <= 1000"
        ],
        "template_code": {
            "python": "from collections import deque\n\nclass TreeNode:\n    def __init__(self, val=0, left=None, right=None):\n        self.val = val\n        self.left = left\n        self.right = right\n\ndef levelOrder(root: TreeNode) -> List[List[int]]:\n    pass",
            "cpp": "struct TreeNode {\n    int val;\n    TreeNode *left;\n    TreeNode *right;\n    TreeNode() : val(0), left(nullptr), right(nullptr) {}\n};\n\nvector<vector<int>> levelOrder(TreeNode* root) {\n    \n}"
        },
        "hints": ["使用队列实现 BFS，每层节点单独存放"],
        "test_cases": [
            {"input": {"root": [3, 9, 20, None, None, 15, 7]}, "expected_output": [[3], [9, 20], [15, 7]]},
            {"input": {"root": [1]}, "expected_output": [[1]]},
            {"input": {"root": []}, "expected_output": []},
            {"input": {"root": [1, 2, 3, 4, 5]}, "expected_output": [[1], [2, 3], [4, 5]]},
            {"input": {"root": [1, 2, 3, None, 4, 5, None]}, "expected_output": [[1], [2, 3], [4, 5]]}
        ]
    }
]


# =========================
# 题库操作函数
# =========================

def get_all_problems() -> List[Dict]:
    """获取所有题目"""
    return PROBLEM_BANK


def get_problem_by_id(problem_id: int) -> Optional[Dict]:
    """根据题目ID获取单个题目"""
    for problem in PROBLEM_BANK:
        if problem["id"] == problem_id:
            return problem
    return None


def get_problems_by_type(problem_type: str) -> List[Dict]:
    """根据题目类型筛选"""
    return [p for p in PROBLEM_BANK if p["type"] == problem_type]


def get_problems_by_difficulty(difficulty: str) -> List[Dict]:
    """根据难度筛选"""
    return [p for p in PROBLEM_BANK if p["difficulty"] == difficulty]


def get_problems_by_tag(tag: str) -> List[Dict]:
    """根据标签筛选"""
    return [p for p in PROBLEM_BANK if tag in p["tags"]]


def search_problems(keyword: str) -> List[Dict]:
    """根据关键词搜索题目（搜索标题和描述）"""
    keyword_lower = keyword.lower()
    results = []
    for problem in PROBLEM_BANK:
        if (keyword_lower in problem["title"].lower() or
            keyword_lower in problem["description"].lower()):
            results.append(problem)
    return results


def get_problem_fields(problem_id: int, fields: List[str]) -> Optional[Dict]:
    """
    获取题目的指定字段

    Args:
        problem_id: 题目ID
        fields: 需要返回的字段列表，如 ["id", "title", "description"]

    Returns:
        包含指定字段的字典，如果题目不存在返回 None
    """
    problem = get_problem_by_id(problem_id)
    if problem is None:
        return None

    result = {}
    for field in fields:
        if field in problem:
            result[field] = problem[field]
    return result


def get_problem_list_for_frontend(
    problem_type: Optional[str] = None,
    difficulty: Optional[str] = None,
    tag: Optional[str] = None,
    keyword: Optional[str] = None,
    fields: Optional[List[str]] = None
) -> List[Dict]:
    """
    获取题库列表（供前端使用）

    Args:
        problem_type: 题目类型筛选（如 "编程题"）
        difficulty: 难度筛选（如 "简单"、"中等"、"困难"）
        tag: 标签筛选
        keyword: 关键词搜索
        fields: 指定返回字段，None 则返回所有字段

    Returns:
        题目列表
    """
    problems = PROBLEM_BANK

    # 应用筛选条件
    if problem_type:
        problems = get_problems_by_type(problem_type)
    if difficulty:
        problems = get_problems_by_difficulty(difficulty)
    if tag:
        problems = get_problems_by_tag(tag)
    if keyword:
        problems = search_problems(keyword)

    # 如果指定了 fields，则只返回指定字段
    if fields:
        return [get_problem_fields(p["id"], fields) for p in problems]

    return problems


def get_problem_detail_for_frontend(problem_id: int) -> Optional[Dict]:
    """
    获取题目详情（供前端使用）

    Args:
        problem_id: 题目ID

    Returns:
        题目详情字典，包含所有字段；如果不存在返回 None
    """
    problem = get_problem_by_id(problem_id)
    if problem is None:
        return None

    return {
        "id": problem["id"],
        "title": problem["title"],
        "description": problem["description"],
        "type": problem["type"],
        "difficulty": problem["difficulty"],
        "tags": problem["tags"],
        "examples": problem["examples"],
        "constraints": problem["constraints"],
        "template_code": problem.get("template_code", {}),
        "hints": problem.get("hints", []),
        "test_cases": problem.get("test_cases", [])
    }


# =========================
# Example / 测试
# =========================
if __name__ == "__main__":
    # 测试获取所有题目
    print("=== 所有题目 ===")
    for p in get_all_problems():
        print(f"[{p['id']}] {p['title']} - {p['difficulty']}")

    print("\n=== 根据难度筛选（简单）===")
    for p in get_problems_by_difficulty("简单"):
        print(f"[{p['id']}] {p['title']}")

    print("\n=== 关键词搜索（链表）===")
    for p in search_problems("链表"):
        print(f"[{p['id']}] {p['title']}")

    print("\n=== 前端获取题目列表（只返回id, title, difficulty）===")
    result = get_problem_list_for_frontend(
        difficulty="简单",
        fields=["id", "title", "difficulty"]
    )
    print(result)

    print("\n=== 前端获取题目详情（id=1）===")
    detail = get_problem_detail_for_frontend(1)
    print(f"标题: {detail['title']}")
    print(f"描述: {detail['description']}")
    print(f"示例: {detail['examples']}")
    print(f"模板代码: {detail['template_code']}")
