"""
decision_engine/capital_engine.py
資本配分エンジン — Claude Max $200/月 予算制約下でのROI最大化

制約:
  - Claude Max: $200/月（定額 — Anthropic API従量課金は使用禁止）
  - VPS: ConoHa（現在のコスト範囲で運用）
  - 新規API課金は事前承認が必要

配分原則（Geneen第3原則: 数字は言語）:
  予算は「感覚」で分けない。ROIスコアで分ける。
"""

import sys
import json
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# 月間予算定義（USD）
MONTHLY_BUDGET = {
    "claude_max": 200.0,    # 定額（AI作業コスト — この枠内で全て運用）
    "vps_conoha": 15.0,     # VPS（概算）
    "domain": 2.0,          # ドメイン月割
    "misc": 10.0,           # 雑費（DNS等）
    "total_fixed": 227.0,   # 固定費合計
    "discretionary": 50.0,  # 裁量予算（新APIテスト等）
}

# 支出カテゴリ定義
SPEND_CATEGORIES = {
    "content_pipeline": {
        "name": "コンテンツパイプライン（NEO執筆）",
        "roi_multiplier": 2.5,    # 高ROI: 記事→読者→収益
        "priority": 1,
        "fixed_monthly": 0.0,     # Claude Max内でカバー
        "variable": True,
    },
    "vps_infra": {
        "name": "VPSインフラ",
        "roi_multiplier": 3.0,    # 高ROI: 基盤なければ何もできない
        "priority": 1,
        "fixed_monthly": 15.0,
        "variable": False,
    },
    "prediction_engine": {
        "name": "予測エンジン（Polymarket/Grok検索）",
        "roi_multiplier": 4.0,    # 最高ROI: Oracleモートの核心
        "priority": 1,
        "fixed_monthly": 0.0,     # Grok $5クレジット内
        "variable": True,
    },
    "distribution": {
        "name": "配信（X/note/Substack）",
        "roi_multiplier": 1.5,    # 中ROI: 波及効果
        "priority": 2,
        "fixed_monthly": 0.0,
        "variable": True,
    },
    "analytics": {
        "name": "アナリティクス（Umami等）",
        "roi_multiplier": 1.2,    # 低ROI: 計測のみ
        "priority": 3,
        "fixed_monthly": 0.0,     # セルフホスト
        "variable": False,
    },
    "new_api": {
        "name": "新規API/実験的機能",
        "roi_multiplier": 0.8,    # 不確実（要承認）
        "priority": 4,
        "fixed_monthly": 0.0,
        "variable": True,
    },
}


@dataclass
class BudgetAllocation:
    """月間予算配分案"""
    category: str
    allocated_usd: float
    roi_score: float
    justification: str
    requires_approval: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ROIProject:
    """ROI評価対象プロジェクト"""
    id: str
    title: str
    category: str
    estimated_cost_usd: float           # 月間コスト
    expected_revenue_impact_usd: float   # 期待収益インパクト（月）
    time_to_revenue_months: int          # 収益化まで何ヶ月
    confidence: float                    # 確信度（0〜1）
    requires_approval: bool = False
    approved: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def roi_score(self) -> float:
        """ROI = 期待収益 / コスト × 確信度 / 期間補正"""
        if self.estimated_cost_usd <= 0:
            return 0.0
        time_discount = 1.0 / max(1, self.time_to_revenue_months ** 0.5)
        return (self.expected_revenue_impact_usd / self.estimated_cost_usd) * self.confidence * time_discount

    @property
    def payback_months(self) -> Optional[float]:
        if self.expected_revenue_impact_usd <= 0:
            return None
        return self.estimated_cost_usd / self.expected_revenue_impact_usd

    def to_dict(self) -> Dict:
        d = asdict(self)
        d["roi_score"] = round(self.roi_score, 3)
        d["payback_months"] = self.payback_months
        return d


class CapitalEngine:
    """
    資本配分エンジン

    Nowpatternの $200/月 Claude Max 予算を最大ROIで配分する。
    新しい支出提案があれば pending_approvals.json に追加し、
    Naotoの承認なしに課金APIを使用しない。
    """

    PROJECTS_PATH = "data/capital_projects.json"
    ALLOCATION_PATH = "data/capital_allocations.json"
    APPROVAL_PATH = "data/pending_approvals.json"

    def __init__(self):
        self._projects: List[ROIProject] = []
        self._allocations: List[BudgetAllocation] = []
        self._load()

    # ── プロジェクト管理 ──────────────────────────────────────

    def add_project(self,
                    title: str,
                    category: str,
                    estimated_cost_usd: float,
                    expected_revenue_impact_usd: float,
                    time_to_revenue_months: int = 6,
                    confidence: float = 0.7) -> ROIProject:
        """ROI評価プロジェクトを追加する"""
        # $10以上の新規コストは承認必須
        requires_approval = estimated_cost_usd >= 10.0 and category not in ("vps_infra", "content_pipeline")

        project_id = f"ROI-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{len(self._projects)+1:03d}"

        project = ROIProject(
            id=project_id,
            title=title,
            category=category,
            estimated_cost_usd=estimated_cost_usd,
            expected_revenue_impact_usd=expected_revenue_impact_usd,
            time_to_revenue_months=time_to_revenue_months,
            confidence=confidence,
            requires_approval=requires_approval,
            approved=not requires_approval,  # 承認不要なら自動承認
        )

        self._projects.append(project)
        self._save_projects()

        # 承認待ちに追加
        if requires_approval:
            self._add_to_approval_queue(project)

        return project

    def get_approved_projects(self) -> List[ROIProject]:
        """承認済みプロジェクトをROI降順で返す"""
        approved = [p for p in self._projects if p.approved]
        return sorted(approved, key=lambda p: p.roi_score, reverse=True)

    def approve_project(self, project_id: str) -> bool:
        """プロジェクトを承認する"""
        for p in self._projects:
            if p.id == project_id:
                p.approved = True
                self._save_projects()
                return True
        return False

    # ── 予算配分 ──────────────────────────────────────────────

    def generate_monthly_allocation(self) -> Dict:
        """
        月間予算配分案を生成する

        Returns:
            {"total_budget", "fixed_costs", "discretionary_budget",
             "allocations", "roi_ranking", "warnings"}
        """
        fixed_costs = sum(c["fixed_monthly"] for c in SPEND_CATEGORIES.values())
        discretionary = MONTHLY_BUDGET["discretionary"]
        total_budget = MONTHLY_BUDGET["total_fixed"]

        # ROIランキング
        approved = self.get_approved_projects()
        roi_ranking = [p.to_dict() for p in approved[:10]]

        # 配分案（承認済みプロジェクト上位から貪欲法で割当）
        remaining = discretionary
        allocations = []

        for project in approved:
            if project.estimated_cost_usd <= 0:
                continue
            if remaining <= 0:
                break
            allocated = min(project.estimated_cost_usd, remaining)
            remaining -= allocated

            justification = (
                f"ROI={project.roi_score:.2f} | "
                f"期待収益={project.expected_revenue_impact_usd:.0f}$/月 | "
                f"確信度={project.confidence*100:.0f}%"
            )

            alloc = BudgetAllocation(
                category=project.category,
                allocated_usd=round(allocated, 2),
                roi_score=round(project.roi_score, 3),
                justification=justification,
                requires_approval=project.requires_approval,
            )
            allocations.append(alloc)

        self._allocations = allocations
        self._save_allocations()

        # 警告
        warnings = []
        if remaining < 10:
            warnings.append(f"⚠️ 裁量予算残り${remaining:.0f} — 新規API承認は慎重に")
        if not approved:
            warnings.append("⚠️ 承認済みプロジェクトがありません — 全裁量予算が未配分です")

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_budget_usd": total_budget,
            "fixed_costs_usd": fixed_costs,
            "discretionary_budget_usd": discretionary,
            "allocated_discretionary_usd": round(discretionary - remaining, 2),
            "unallocated_usd": round(remaining, 2),
            "allocations": [a.to_dict() for a in allocations],
            "roi_ranking": roi_ranking,
            "warnings": warnings,
        }

    def evaluate_new_spend(self, title: str, cost_usd: float, expected_impact_usd: float,
                           category: str = "new_api") -> Dict:
        """
        新規支出の事前ROI評価（承認リクエスト前の判断材料）

        Returns:
            {"approve_recommended", "roi_score", "payback_months", "reasoning"}
        """
        roi = (expected_impact_usd / cost_usd) if cost_usd > 0 else 0
        payback = (cost_usd / expected_impact_usd) if expected_impact_usd > 0 else None

        # Geneenルール: 数字で判断する
        if roi >= 3.0:
            approve_recommended = True
            reasoning = f"ROI={roi:.1f}x — 強く推奨。月${expected_impact_usd:.0f}のインパクト"
        elif roi >= 1.5:
            approve_recommended = True
            reasoning = f"ROI={roi:.1f}x — 推奨。回収期間{payback:.1f}ヶ月"
        elif roi >= 1.0:
            approve_recommended = None  # 要検討
            reasoning = f"ROI={roi:.1f}x — 判断難。代替案と比較推奨"
        else:
            approve_recommended = False
            reasoning = f"ROI={roi:.1f}x — 非推奨。コストが期待収益を超過"

        return {
            "title": title,
            "cost_usd": cost_usd,
            "expected_impact_usd": expected_impact_usd,
            "roi_score": round(roi, 2),
            "payback_months": round(payback, 1) if payback else None,
            "approve_recommended": approve_recommended,
            "reasoning": reasoning,
            "requires_naoto_approval": cost_usd >= 10.0,
        }

    def get_budget_summary(self) -> Dict:
        """現在の予算サマリーを返す"""
        return {
            "monthly_budget": MONTHLY_BUDGET,
            "categories": SPEND_CATEGORIES,
            "pending_projects": len([p for p in self._projects if p.requires_approval and not p.approved]),
            "approved_projects": len([p for p in self._projects if p.approved]),
            "total_approved_cost_usd": sum(p.estimated_cost_usd for p in self._projects if p.approved),
        }

    # ── 内部処理 ──────────────────────────────────────────────

    def _add_to_approval_queue(self, project: ROIProject):
        """pending_approvals.json に追加する"""
        approval_id = f"cap-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        entry = {
            "id": approval_id,
            "type": "capital_request",
            "title": f"ROI最大化提案: {project.title}",
            "description": (
                f"【コスト】${project.estimated_cost_usd}/月\n"
                f"【期待収益インパクト】${project.expected_revenue_impact_usd}/月\n"
                f"【ROIスコア】{project.roi_score:.2f}\n"
                f"【回収期間】{project.payback_months:.1f}ヶ月" if project.payback_months else ""
            ),
            "project_id": project.id,
            "proposed_by": "capital-engine",
            "proposed_at": datetime.now(timezone.utc).isoformat(),
            "status": "pending",
        }

        os.makedirs("data", exist_ok=True)
        existing = []
        if os.path.exists(self.APPROVAL_PATH):
            try:
                with open(self.APPROVAL_PATH, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except Exception:
                pass

        existing.append(entry)
        try:
            with open(self.APPROVAL_PATH, "w", encoding="utf-8") as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WARNING] Approval queue write error: {e}")

    def _load(self):
        if os.path.exists(self.PROJECTS_PATH):
            try:
                with open(self.PROJECTS_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._projects = [ROIProject(**d) for d in data]
            except Exception as e:
                print(f"[WARNING] CapitalEngine load error: {e}")

    def _save_projects(self):
        os.makedirs("data", exist_ok=True)
        try:
            with open(self.PROJECTS_PATH, "w", encoding="utf-8") as f:
                json.dump([p.to_dict() for p in self._projects], f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WARNING] CapitalEngine save error: {e}")

    def _save_allocations(self):
        os.makedirs("data", exist_ok=True)
        try:
            with open(self.ALLOCATION_PATH, "w", encoding="utf-8") as f:
                json.dump([a.to_dict() for a in self._allocations], f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WARNING] CapitalEngine allocation save error: {e}")


if __name__ == "__main__":
    engine = CapitalEngine()

    # デモ評価
    eval_result = engine.evaluate_new_spend(
        title="DeepSeek R1 Distill API（記事生成コスト削減）",
        cost_usd=5.0,
        expected_impact_usd=20.0,
        category="new_api",
    )
    print(f"ROI評価: {eval_result['title']}")
    print(f"  ROI={eval_result['roi_score']}x | 推奨={eval_result['approve_recommended']}")
    print(f"  理由: {eval_result['reasoning']}")

    # 月間配分
    engine.add_project(
        title="Grok API予測検索（月$5クレジット）",
        category="prediction_engine",
        estimated_cost_usd=5.0,
        expected_revenue_impact_usd=50.0,
        time_to_revenue_months=3,
        confidence=0.8,
    )

    allocation = engine.generate_monthly_allocation()
    print(f"\n月間予算配分:")
    print(f"  合計: ${allocation['total_budget_usd']}")
    print(f"  裁量予算: ${allocation['discretionary_budget_usd']} / 配分済み: ${allocation['allocated_discretionary_usd']}")
    for w in allocation["warnings"]:
        print(f"  {w}")
