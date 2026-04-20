"""
语义对齐重排序器

通过 Prompt Engineering 引导 AI 联系教学内容与思政内容，对检索结果进行重排序。
"""

from typing import List, Dict
from camel.agents import ChatAgent

from ..config import get_llm_client


class SemanticReranker:
    """语义对齐重排序器"""

    def __init__(self, model=None):
        """
        初始化重排序器

        Args:
            model: LLM 模型实例
        """
        self.model = model or get_llm_client()
        self.agent = ChatAgent(
            system_message="你是一个教育内容专家，擅长判断教学内容与思政教育的关联程度。",
            model=self.model
        )

    def rerank(
        self,
        teaching_content: str,
        policy_contents: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """
        对思政内容进行重排序

        Args:
            teaching_content: 教学内容
            policy_contents: 待排序的思政内容列表

        Returns:
            排序后的思政内容列表
        """
        if not policy_contents:
            return []

        # 构建评估 prompt
        content_list = "\n\n".join([
            f"{i+1}. 标题：{item['title']}\n   内容：{item['content']}"
            for i, item in enumerate(policy_contents)
        ])

        prompt = f"""请评估以下思政教育内容与教学内容的关联程度，并按关联度从高到低排序。

教学内容：
{teaching_content}

思政教育内容：
{content_list}

请直接返回排序后的编号（用逗号分隔），例如：3,1,2"""

        try:
            response = self.agent.step(prompt)
            order = self._parse_order(response.msg.content, len(policy_contents))
            return [policy_contents[i] for i in order]
        except Exception as e:
            print(f"重排序失败，使用原始顺序: {e}")
            return policy_contents

    def _parse_order(self, response: str, total: int) -> List[int]:
        """解析排序结果"""
        import re
        numbers = re.findall(r'\d+', response)
        order = [int(n) - 1 for n in numbers if 1 <= int(n) <= total]

        # 如果解析结果不完整，补充缺失的索引
        if len(order) < total:
            missing = [i for i in range(total) if i not in order]
            order.extend(missing)

        return order[:total]

    def select_best(
        self,
        teaching_content: str,
        policy_contents: List[Dict[str, str]],
        top_k: int = 1
    ) -> List[Dict[str, str]]:
        """
        选择最相关的思政内容

        Args:
            teaching_content: 教学内容
            policy_contents: 思政内容列表
            top_k: 返回数量

        Returns:
            最相关的思政内容
        """
        reranked = self.rerank(teaching_content, policy_contents)
        return reranked[:top_k]
