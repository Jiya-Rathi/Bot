# ─── utils/financial_scorer_rules.py ───────────────────────────────────────────

import numpy as np

class FinancialScorerRules:
    """
    Uses purely rules (no LLM) to calculate a score from 0–100 based on cash flow, margins, anomalies, etc.
    Same logic as before, but isolated here.
    """
    def __init__(self):
        pass

    def score(self, cash_flow_stats: dict, overdue_count: int, anomalies: list) -> int:
        """
        cash_flow_stats: {'profit_margin': float, …}
        overdue_count: int
        anomalies: list of anomaly dicts
        """
        score = 50
        pm = cash_flow_stats.get('profit_margin', 0)
        if pm > 20:
            score += 30
        elif pm > 10:
            score += 20
        elif pm > 0:
            score += 10
        else:
            score -= 10

        weekly = list(cash_flow_stats.get('weekly_trend', {}).values())
        if len(weekly) > 1:
            vol = np.std(weekly) / (np.mean(weekly) if np.mean(weekly) != 0 else 1)
            if vol < 0.2:
                score += 20
            elif vol < 0.5:
                score += 10

        if overdue_count == 0:
            score += 20
        elif overdue_count < 3:
            score += 10

        return max(0, min(100, int(score)))
