# -*- coding: utf-8 -*-
"""
内容生成器

根据决策结果 (decision_result.json) 优化原始页面内容。
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Optional
from camel.agents import ChatAgent

# 添加项目根目录到路径（支持直接运行）
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from ..config import get_llm_client
    from ..parser.document_splitter import DocumentStructure, SlideChunk
    from ..retrieval.policy_fetcher import PolicyFetcher
except ImportError:
    from src.preparation.config import get_llm_client
    from src.preparation.parser.document_splitter import DocumentStructure, SlideChunk
    from src.preparation.retrieval.policy_fetcher import PolicyFetcher


class ContentGenerator:
    """内容生成器"""

    # 系统提示词
    SYSTEM_PROMPT = """你是一位专业的教育内容创作专家，擅长将思政元素自然地融入专业课程内容中。

你的任务是根据原始教学内容，生成融合了思政元素的幻灯片内容。

## 创作原则

1. **自然融入**：思政元素要与专业内容有机融合，不生硬、不突兀
2. **保持专业**：不能因为融入思政而影响专业知识的准确性和完整性
3. **适度原则**：根据优化策略调整内容，不过度修改
4. **价值引领**：通过案例、比喻、问题引导等方式实现价值观引导

## 融入方式

- **引用式**：引用领导人讲话、经典著作
- **案例式**：使用现实案例说明理论
- **问题式**：提出引导学生思考的问题
- **对比式**：通过对比体现价值观
- **延伸式**：在知识点基础上延伸思考

## 输出格式

请严格按照以下格式输出：

---
**标题**: [优化后的标题]
**内容**: [融合后的内容，使用 Markdown 格式]
**思政融合说明**: [说明思政内容如何融入，如果没有则填"无"]
---
"""

    def __init__(self, model=None):
        """初始化生成器"""
        self.model = model or get_llm_client()
        self.agent = ChatAgent(
            system_message=self.SYSTEM_PROMPT,
            model=self.model
        )
        self.policy_fetcher = PolicyFetcher()

    def optimize_by_decision(
        self,
        pages_json: str,
        decision_json: str,
        retrieval_json: str = None,
        output_dir: str = None,
        callback=None
    ) -> List[Dict]:
        """
        根据决策结果优化页面内容

        Args:
            pages_json: 原始分页 JSON 文件路径
            decision_json: 决策结果 JSON 文件路径
            output_dir: 输出目录
            callback: 进度回调 callback(current, total, info)

        Returns:
            优化后的页面列表
        """
        # 加载数据
        with open(pages_json, 'r', encoding='utf-8') as f:
            pages = json.load(f)

        # 空值检查，防止 None 导致 len() 报错
        if pages is None:
            pages = []

        with open(decision_json, 'r', encoding='utf-8') as f:
            decision = json.load(f)

        # 构建决策映射
        decisions_map = {
            d["slide_number"]: d
            for d in decision.get("decisions", [])
        }
        
        retrieval_map = {}
        if retrieval_json:
            with open(retrieval_json, 'r', encoding='utf-8') as f:
                retrieval = json.load(f)
            # 兼容：如果 retrieval 文件本身就带 decisions
            for d in retrieval.get("decisions", []):
                sn = d.get("slide_number")
                if sn is None:
                    continue
                retrieval_map[sn] = d.get("keywords_information", {}) or {}

        decisions_map = {d["slide_number"]: d for d in decision.get("decisions", [])}

        results = []
        total = len(pages)

        for i, page in enumerate(pages):
            slide_number = page.get("page_number", i)
            decision_info = decisions_map.get(slide_number, {})
            retrieved_info = retrieval_map.get(slide_number, {})  # NEW

            # 判断是否需要优化
            should_optimize = decision_info.get("should_optimize", False)

            if should_optimize:
                # 需要优化：调用 LLM
                result = self._optimize_page(page, decision_info,retrieved_info)  # Pass retrieved_info
            else:
                # 不需要优化：保持原样
                result = {
                    "slide_number": slide_number,
                    "original_title": page.get("title", ""),
                    "optimized_title": page.get("title", ""),
                    "content": page.get("content", ""),
                    "si_zheng_note": "无（保持原样）",
                    "has_policy": False,
                    "reason": decision_info.get("reason", "不需要优化")
                }

            results.append(result)

            if callback:
                callback(i + 1, total, {
                    "title": page.get("title", ""),
                    "has_policy": result.get("has_policy", False)
                })

        return results
    
    def _build_evidence_blocks(self, retrieved_info: Optional[Dict], keywords: List[str], top_k: int = 4) -> List[Dict]:
        """
        retrieved_info: 来自 retrieval_json 的 keywords_information:
        { keyword: [ {url,title,content,relevance_score,reason}, ... ], ... }
        """
        if not retrieved_info:
            return []
        candidates = []
        # 只优先用当前 decision 建议的关键词，避免灌太多噪声
        for kw in (keywords or []):
            for item in retrieved_info.get(kw, []) or []:
                candidates.append({
                    "keyword": kw,
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "content": (item.get("content", "") or "").strip(),
                    "score": item.get("relevance_score", 0),
                    "reason": item.get("reason", ""),
                })

        # 排序：score 高的优先；再做长度截断避免 prompt 爆
        candidates.sort(key=lambda x: (x["score"], len(x["content"])), reverse=True)
        picked = []
        for c in candidates[:top_k]:
            text = c["content"]
            if len(text) > 2000:  # 你可以调小/调大
                text = text[:2000] + "..."
            picked.append({**c, "content": text})

        return picked

    def _optimize_page(self, page: Dict, decision_info: Dict, retrieved_info: Optional[Dict] = None) -> Dict:
        """优化单页内容"""
        title = page.get("title", "")
        content = page.get("content", "")
        reason = decision_info.get("reason", "")
        keywords = decision_info.get("suggested_keywords", [])
        strategy = decision_info.get("optimization_strategy", "")

        # 1) 优先用检索文件里的证据
        evidence_blocks = self._build_evidence_blocks(retrieved_info, keywords, top_k=4)

        # 2) 兜底：如果没有任何证据，再走你原来的 PolicyFetcher
        policy_content = None
        if not evidence_blocks and keywords:
            policies = self.policy_fetcher.fetch_by_keywords(keywords, limit=1)
            if policies:
                policy_content = policies[0]

        prompt = self._build_prompt(
            title, content, reason, strategy,
            policy_content=policy_content,
            evidence_blocks=evidence_blocks,  
        )

        # 调用 LLM
        try:
            response = self.agent.step(prompt)
            parsed = self._parse_response(response.msg.content)

            return {
                "slide_number": page.get("page_number", 0),
                "original_title": title,
                "optimized_title": parsed.get("title", title),
                "content": parsed.get("content", content),
                "si_zheng_note": parsed.get("si_zheng_note", reason),
                "has_policy": True,
                "reason": reason,
                "keywords": keywords,
                "evidence_used": evidence_blocks,
                "policy_title": policy_content.get("title", "") if policy_content else ""
            }
        except Exception as e:
            print(f"  [Error] 优化页面 '{title}' 失败: {e}")
            return {
                "slide_number": page.get("page_number", 0),
                "original_title": title,
                "optimized_title": title,
                "content": content,
                "si_zheng_note": f"优化失败，保留原内容: {e}",
                "has_policy": False,
                "reason": reason
            }

    def _build_prompt(
        self,
        title: str,
        content: str,
        reason: str,
        strategy: str,
        policy_content: Optional[Dict] = None,
        evidence_blocks: Optional[List[Dict]] = None,
    ) -> str:
        """构建优化 Prompt"""
        prompt_parts = [
            f"# 页面优化任务",
            f"",
            f"## 原始内容",
            f"",
            f"**标题**: {title}",
            f"**内容**:",
            f"```",
            f"{content}",
            f"```",
        ]
        if evidence_blocks:
            prompt_parts.extend(["", "## 检索参考材料（可用于思政融合/案例/引用，务必“自然融入”）", ""])
            for idx, e in enumerate(evidence_blocks, 1):
                prompt_parts.extend([
                    f"### 证据 {idx}",
                    f"- 关键词: {e.get('keyword','')}",
                    f"- 标题: {e.get('title','')}",
                    f"- URL: {e.get('url','')}",
                    f"- 相关性: {e.get('score','')}",
                    f"- 备注: {e.get('reason','')}",
                    f"- 摘要/正文片段:\n{e.get('content','')}",
                    ""
                ])


        if policy_content:
            prompt_parts.extend([
                f"",
                f"## 思政内容",
                f"",
                f"**主题**: {policy_content.get('title', '')}",
                f"**内容**: {policy_content.get('content', '')}",
            ])

        prompt_parts.extend([
            f"",
            f"## 优化指导",
            f"",
            f"**优化原因**: {reason}",
            f"",
        ])

        if strategy:
            prompt_parts.append(f"**优化策略**: {strategy}")

        prompt_parts.extend([
            f"",
            f"## 输出要求",
            f"",
            f"请严格按照以下格式输出：",
            f"",
            f"---",
            f"**标题**: [优化后的标题]",
            f"**内容**: [优化后的内容，使用 Markdown 格式]",
            f"**思政融合说明**: [说明如何融入思政内容]",
            f"---",
        ])

        return "\n".join(prompt_parts)

    def _parse_response(self, response: str) -> Dict[str, str]:
        """解析 LLM 响应"""
        result = {
            "title": "",
            "content": "",
            "si_zheng_note": ""
        }

        lines = response.split('\n')
        current_section = None
        content_lines = []

        for line in lines:
            line = line.rstrip()

            # 检测标题
            if "**标题**" in line or "标题：" in line or "标题:" in line:
                current_section = "title"
                for marker in ["**标题**:", "**标题**: ", "标题：", "标题:"]:
                    if marker in line:
                        result["title"] = line.split(marker, 1)[-1].strip().strip("*").strip()
                        break

            # 检测内容
            elif "**内容**" in line or "内容：" in line or "内容:" in line:
                current_section = "content"
                for marker in ["**内容**:", "**内容**: ", "内容：", "内容:"]:
                    if marker in line and len(line.split(marker, 1)[-1].strip()) > 0:
                        content_lines.append(line.split(marker, 1)[-1].strip())

            # 检测思政融合说明
            elif "**思政融合说明**" in line or "思政融合说明：" in line or "思政融合说明:" in line:
                current_section = "si_zheng"
                for marker in ["**思政融合说明**:", "**思政融合说明**: ", "思政融合说明：", "思政融合说明:"]:
                    if marker in line:
                        result["si_zheng_note"] = line.split(marker, 1)[-1].strip()
                        break

            # 收集内容行
            elif current_section == "content" and line.strip():
                content_lines.append(line)

        result["content"] = "\n".join(content_lines).strip()

        # 如果没有解析到内容，使用原始响应
        if not result["content"] and not result["title"]:
            result["content"] = response

        return result

    def save_results(
        self,
        results: List[Dict],
        output_dir: str,
        base_name: str = "optimized"
    ):
        """
        保存优化结果

        Args:
            results: 优化结果列表
            output_dir: 输出目录
            base_name: 基础文件名
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # 保存 JSON 格式
        json_file = output_path / f"{base_name}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        # 保存 Markdown 格式
        md_file = output_path / f"{base_name}.md"
        md_lines = [
            f"# 优化后的课件内容\n\n",
            f"## 统计信息\n\n",
            f"- 总页面: {len(results)}\n",
            f"- 含思政: {sum(1 for r in results if r.get('has_policy'))} 页\n",
            f"- 保持原样: {sum(1 for r in results if not r.get('has_policy'))} 页\n\n",
            f"## 优化内容\n\n"
        ]

        for r in results:
            md_lines.append(f"### 页面 {r['slide_number'] + 1}: {r['optimized_title']}\n\n")
            md_lines.append(f"{r['content']}\n\n")
            if r.get('has_policy'):
                md_lines.append(f"> 💡 {r.get('si_zheng_note', '')}\n\n")
            md_lines.append("---\n\n")

        md_file.write_text("".join(md_lines), encoding='utf-8')

        return json_file, md_file


if __name__ == "__main__":
    """
    测试入口 - 根据决策结果优化页面内容

    输入:
        - parser/tmp/MinerU_markdown_1.导言_pages.json (原始页面)
        - logic/tmp/decision_result.json (决策结果)

    输出:
        - logic/tmp/optimized.json
        - logic/tmp/optimized.md

    运行方式:
        python /home/guoziyang/AIgorithm_Agent/src/preparation/logic/content_generator.py
        或
        python -m src.preparation.logic.content_generator
    """
    # 配置
    PAGES_JSON = "/home/guoziyang/AIgorithm_Agent/src/preparation/parser/tmp/WEEK1-1 Chap01-25-1_pages.json"
    RETRIEVAL_JSON = "/home/guoziyang/AIgorithm_Agent/src/preparation/logic/tmp/slide_content_20260211_110129.json"  
    DECISION_JSON = "/home/guoziyang/AIgorithm_Agent/src/preparation/logic/tmp/decision_result.json"
    OUTPUT_DIR = "/home/guoziyang/AIgorithm_Agent/src/preparation/logic/tmp"

    print("=" * 60)
    print("内容生成器 - 根据决策结果优化页面")
    print("=" * 60)
    print(f"原始页面: {PAGES_JSON}")
    print(f"决策结果: {DECISION_JSON}")
    print(f"输出目录: {OUTPUT_DIR}")
    print("-" * 60)

    # 创建生成器
    generator = ContentGenerator()

    # 进度回调
    def progress_callback(current, total, info):
        status = "(含思政)" if info.get('has_policy') else ""
        print(f"  [{current}/{total}] {info['title']} {status}")

    # 执行优化
    print("\n[开始优化...]\n")
    results = generator.optimize_by_decision(
        pages_json=PAGES_JSON,
        decision_json=DECISION_JSON,
        retrieval_json=RETRIEVAL_JSON,
        output_dir=OUTPUT_DIR,
        callback=progress_callback
    )

    # 保存结果
    print(f"\n[保存结果...]")
    json_file, md_file = generator.save_results(results, OUTPUT_DIR, "optimized")

    # 统计
    total = len(results)
    with_policy = sum(1 for r in results if r.get('has_policy'))
    keep_original = total - with_policy

    print("\n" + "=" * 60)
    print("优化完成!")
    print(f"  总页面: {total}")
    print(f"  含思政: {with_policy} 页")
    print(f"  保持原样: {keep_original} 页")
    print(f"\n输出文件:")
    print(f"  JSON: {json_file}")
    print(f"  Markdown: {md_file}")
    print("=" * 60)
