from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class LoyaltyRecommendationService:
    """Generate fast, personalized loyalty offers using lightweight heuristics."""

    def __init__(self) -> None:
        self._tier_thresholds = {
            "bronze": 0,
            "silver": 1500,
            "gold": 3000,
            "platinum": 6000,
        }

    def generate(self, account_id: str, balance: int = 0, transactions: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        txs = list(transactions or [])
        if txs:
            total_volume = sum(float(item.get("amount", 0)) for item in txs)
            average_ticket = total_volume / len(txs)
            frequency = len(txs)
        else:
            total_volume = 0.0
            average_ticket = 0.0
            frequency = 0

        tier = self._tier_for(balance)
        recommendations: list[dict[str, Any]] = []

        if balance < 1500:
            recommendations.append(
                {
                    "id": "balance-boost",
                    "title": "Balance boost offer",
                    "description": f"Earn 250 bonus points by adding {max(100, 1500 - balance)} more points to your balance.",
                    "offer_type": "balance_based",
                    "points_cost": 0,
                    "expected_acceptance_rate": 0.48,
                    "reason": "Your balance is still below the silver tier threshold.",
                    "eligible": True,
                }
            )

        if average_ticket >= 250 or frequency >= 3:
            recommendations.append(
                {
                    "id": "high-value-reward",
                    "title": "High-value reward",
                    "description": "Unlock a premium reward on your next high-value transaction.",
                    "offer_type": "personalized",
                    "points_cost": 500,
                    "expected_acceptance_rate": 0.44,
                    "reason": "Recent activity suggests you respond well to larger purchases.",
                    "eligible": True,
                }
            )
        else:
            recommendations.append(
                {
                    "id": "small-step-reward",
                    "title": "Small-step reward",
                    "description": "Earn a quick bonus on your next purchase to keep momentum going.",
                    "offer_type": "personalized",
                    "points_cost": 150,
                    "expected_acceptance_rate": 0.41,
                    "reason": "You have a steady but lower-volume pattern.",
                    "eligible": True,
                }
            )

        if tier in {"silver", "gold", "platinum"}:
            recommendations.append(
                {
                    "id": "tier-upgrade",
                    "title": "Tier upgrade bonus",
                    "description": "Keep your streak alive with a bonus that accelerates your next tier upgrade.",
                    "offer_type": "balance_based",
                    "points_cost": 0,
                    "expected_acceptance_rate": 0.43,
                    "reason": "You are already close to the next tier and benefit from milestone offers.",
                    "eligible": True,
                }
            )

        recommendations.append(
            {
                "id": "cashback-surprise",
                "title": "Cashback surprise",
                "description": "Claim a surprise cashback-style reward with your next eligible transaction.",
                "offer_type": "seasonal",
                "points_cost": 0,
                "expected_acceptance_rate": 0.42,
                "reason": "A lightweight, broad offer is ideal for users with mixed behavior.",
                "eligible": True,
            }
        )

        analysis_summary = (
            f"Account {account_id} shows {frequency} recent transactions with an average ticket of "
            f"${average_ticket:.2f}; current balance places them in {tier} tier."
        )

        return {
            "account_id": account_id,
            "balance": balance,
            "analysis_summary": analysis_summary,
            "recommendations": recommendations[:4],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _tier_for(self, balance: int) -> str:
        if balance >= self._tier_thresholds["platinum"]:
            return "platinum"
        if balance >= self._tier_thresholds["gold"]:
            return "gold"
        if balance >= self._tier_thresholds["silver"]:
            return "silver"
        return "bronze"
