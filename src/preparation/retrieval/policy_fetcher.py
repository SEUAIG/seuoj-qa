"""
实时政策/思政内容获取器

负责从网络或本地数据源获取最新的思政教育内容。
"""

import json
from pathlib import Path
from typing import List, Dict, Optional


class PolicyFetcher:
    """思政内容获取器"""

    def __init__(self, cache_dir: str = "data/preparation/policies"):
        """
        初始化获取器

        Args:
            cache_dir: 本地缓存目录
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "policies_cache.json"
        self.manual_file = self.cache_dir / "manual_policies.json"

    def fetch_by_keywords(self, keywords: List[str], limit: int = 3) -> List[Dict[str, str]]:
        """
        根据关键词获取相关思政内容

        Args:
            keywords: 关键词列表
            limit: 返回结果数量

        Returns:
            思政内容列表，每个包含 title 和 content
        """
        results = []

        # 1. 先从手动添加的内容查找
        manual_policies = self._load_manual_policies()
        for keyword in keywords:
            for policy in manual_policies:
                if keyword in policy.get("keywords", []) or keyword in policy.get("title", ""):
                    results.append({
                        "title": policy["title"],
                        "content": policy["content"],
                        "source": "manual"
                    })
                    if len(results) >= limit:
                        return results

        # 2. 从本地缓存查找
        cached = self._load_cache()
        for keyword in keywords:
            if keyword in cached:
                for item in cached[keyword]:
                    results.append({
                        "title": item["title"],
                        "content": item["content"],
                        "source": "cache"
                    })
                    if len(results) >= limit:
                        return results

        # 3. 如果缓存不足，从预设库获取
        if len(results) < limit:
            preset_results = self._fetch_from_preset(keywords, limit - len(results))
            results.extend(preset_results)

        return results[:limit]

    def _load_cache(self) -> Dict[str, List[Dict]]:
        """加载本地缓存"""
        if self.cache_file.exists():
            return json.loads(self.cache_file.read_text(encoding="utf-8"))
        return {}

    def _load_manual_policies(self) -> List[Dict]:
        """加载手动添加的思政内容"""
        if self.manual_file.exists():
            return json.loads(self.manual_file.read_text(encoding="utf-8"))
        return []

    def _fetch_from_preset(self, keywords: List[str], limit: int) -> List[Dict[str, str]]:
        """
        从预设库获取思政内容

        Args:
            keywords: 关键词列表
            limit: 返回结果数量

        Returns:
            思政内容列表
        """
        # 预设思政内容库
        preset_contents = {
            "马克思主义": {
                "title": "马克思主义的当代价值",
                "content": "马克思主义不仅是关于无产阶级解放的学说，更是关于人类全面发展的理论。在新时代，我们要坚持马克思主义基本原理同中国具体实际相结合，不断推进马克思主义中国化时代化。"
            },
            "社会主义": {
                "title": "社会主义核心价值观",
                "content": "社会主义核心价值观是当代中国精神的集中体现，凝结着全体人民共同的价值追求。要坚持用社会主义核心价值观凝魂聚力，培养担当民族复兴大任的时代新人。"
            },
            "共产主义": {
                "title": "共产主义的理想信念",
                "content": "共产主义远大理想和中国特色社会主义共同理想，是中国共产党人的精神支柱和政治灵魂。我们要坚定理想信念，牢记党的宗旨，为实现共产主义远大理想而奋斗。"
            },
            "解放": {
                "title": "人类解放的终极关怀",
                "content": "马克思主义追求的人类解放，不仅是政治解放和经济解放，更是人的自由全面发展。这体现了对人类命运的深切关怀和对美好社会的执着追求。"
            },
            "阶级": {
                "title": "阶级分析的历史意义",
                "content": "阶级分析方法是我们认识社会、分析社会的重要工具。在新时代，我们要运用马克思主义立场观点方法，正确认识和处理社会各阶层关系，凝聚起实现民族复兴的磅礴力量。"
            },
            "资本主义": {
                "title": "当代资本主义的特征与挑战",
                "content": "当代资本主义发生了许多新变化，但其基本矛盾没有改变。我们要深入认识资本主义发展规律，坚定社会主义必然代替资本主义的信念。"
            },
            "工人": {
                "title": "劳动者的主体地位",
                "content": "劳动者是社会物质财富和精神财富的创造者，是社会发展的主体力量。我们要尊重劳动、尊重知识、尊重人才、尊重创造，让全体劳动者共享发展成果。"
            },
            "人民": {
                "title": "以人民为中心的发展思想",
                "content": "人民是历史的创造者，是决定党和国家前途命运的根本力量。坚持以人民为中心的发展思想，把人民对美好生活的向往作为奋斗目标，是中国共产党的根本立场。"
            },
            "发展": {
                "title": "新发展理念的哲学意蕴",
                "content": "创新、协调、绿色、开放、共享的新发展理念，是马克思主义发展理论在当代中国的具体体现，深刻回答了关于发展的目的、动力、方式、路径等一系列理论和实践问题。"
            },
            "历史": {
                "title": "历史唯物主义的当代启示",
                "content": "历史唯物主义揭示了人类社会发展的一般规律，为我们认识世界、改造世界提供了科学方法论。要坚持用历史唯物主义观察问题、分析问题、解决问题。"
            },
            "理论": {
                "title": "理论创新与实践创新",
                "content": "实践是理论之源，理论是实践的先导。我们要在实践中检验真理、发展真理，用发展着的理论指导发展着的实践，实现理论创新和实践创新的良性互动。"
            },
            "实践": {
                "title": "实践观点的哲学意义",
                "content": "实践是认识的来源、动力、目的和检验标准。马克思主义的实践观告诉我们，要在实践中发现真理、检验真理、发展真理，做到知行合一。"
            },
            "革命": {
                "title": "革命精神的传承与弘扬",
                "content": "革命精神是党和国家的宝贵精神财富。我们要传承红色基因，弘扬革命精神，保持艰苦奋斗的作风，以昂扬的精神状态投身全面建设社会主义现代化国家的伟大实践。"
            },
            "制度": {
                "title": "中国特色社会主义制度优势",
                "content": "中国特色社会主义制度是当代中国发展进步的根本制度保障。要坚定制度自信，把我国制度优势转化为治理效能，为实现中华民族伟大复兴提供有力保证。"
            },
            "经济": {
                "title": "马克思主义政治经济学的当代价值",
                "content": "马克思主义政治经济学揭示了人类社会经济发展规律，为我国经济发展提供了根本遵循。要运用马克思主义政治经济学基本原理指导中国特色社会主义经济实践。"
            },
            "政治": {
                "title": "全过程人民民主",
                "content": "全过程人民民主是社会主义民主政治的本质属性。要发展全过程人民民主，保障人民当家作主，体现人民意志，保障人民权益，激发人民创造活力。"
            }
        }

        results = []
        for keyword in keywords:
            for key, value in preset_contents.items():
                if key in keyword or keyword in key:
                    results.append(value)
                    if len(results) >= limit:
                        return results

        # 如果没有匹配，返回默认内容
        if not results:
            results.append({
                "title": "课程思政融入",
                "content": "在学习本节内容时，要培养正确的世界观、人生观、价值观，坚持理论联系实际，将专业知识学习与思想品德修养相结合，努力成为德才兼备的高素质人才。"
            })

        return results

    def add_manual_policy(
        self,
        title: str,
        content: str,
        keywords: List[str] = None
    ) -> None:
        """
        手动添加思政内容

        Args:
            title: 标题
            content: 内容
            keywords: 关联关键词列表
        """
        manual_policies = self._load_manual_policies()

        new_policy = {
            "id": f"manual_{len(manual_policies) + 1}",
            "title": title,
            "content": content,
            "keywords": keywords or [],
            "created_at": str(Path(__file__).stat().st_mtime)
        }

        manual_policies.append(new_policy)

        self.manual_file.write_text(
            json.dumps(manual_policies, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def list_manual_policies(self) -> List[Dict]:
        """列出所有手动添加的思政内容"""
        return self._load_manual_policies()

    def delete_manual_policy(self, policy_id: str) -> bool:
        """
        删除指定的手动添加内容

        Args:
            policy_id: 内容ID

        Returns:
            是否删除成功
        """
        manual_policies = self._load_manual_policies()
        original_len = len(manual_policies)

        manual_policies = [p for p in manual_policies if p.get("id") != policy_id]

        if len(manual_policies) < original_len:
            self.manual_file.write_text(
                json.dumps(manual_policies, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            return True
        return False

    def get_all_keywords(self) -> List[str]:
        """获取所有可用的关键词"""
        keywords = set(self._load_cache().keys())

        for policy in self._load_manual_policies():
            keywords.update(policy.get("keywords", []))

        return sorted(list(keywords))
