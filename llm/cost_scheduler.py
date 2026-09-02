import logging
from typing import List, Optional
from llm.base_llm import BaseLLM, LLMResponse
from llm.model_stats import ModelStats, ModelRecord
from llm.budget import BudgetManager

logger = logging.getLogger(__name__)

class CostScheduler:
    def __init__(self, models: List[BaseLLM], model_stats: ModelStats,
                 alpha: float = 0.4, beta: float = 0.3,
                 gamma: float = 0.2, delta: float = 0.1):
        self.models = models
        self.model_stats = model_stats
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.delta = delta
        self.selection_log = []

    def _normalize(self, value: float, min_val: float, max_val: float) -> float:
        if max_val == min_val:
            return 1.0
        return (value - min_val) / (max_val - min_val)

    def estimate_complexity(self, task_description: str) -> str:
        length = len(task_description)
        complex_keywords = ["compare", "analyze", "aggregate", "synthesize", "evaluate", "multi"]
        has_complex = any(kw in task_description.lower() for kw in complex_keywords)
        if has_complex or length > 200:
            return "HIGH"
        elif length > 100:
            return "MEDIUM"
        return "LOW"

    def select_model(self, task_description: str = "",
                     budget_manager: BudgetManager = None) -> Optional[BaseLLM]:
        if not self.models:
            return None

        complexity = self.estimate_complexity(task_description)
        candidates = []

        for model in self.models:
            stats = self.model_stats.get_stats(model.name)
            if not stats:
                stats = ModelRecord(
                    model_name=model.name,
                    avg_cost=model.cost_per_input_token * 500 + model.cost_per_output_token * 200,
                    avg_latency=1000.0,
                    success_rate=0.8,
                    quality_score=0.8,
                )

            if budget_manager:
                remaining = budget_manager.remaining_budget()
                if stats.avg_cost > remaining["remaining_cost"]:
                    logger.info(f"Skipping {model.name}: avg_cost {stats.avg_cost:.6f} > remaining {remaining['remaining_cost']:.6f}")
                    continue

            quality = stats.quality_score
            cost = stats.avg_cost
            latency = stats.avg_latency / 1000.0
            resource = 1.0 if stats.total_calls > 10 else 0.5

            candidates.append({
                "model": model,
                "stats": stats,
                "quality": quality,
                "cost": cost,
                "latency": latency,
                "resource": resource,
                "complexity": complexity
            })

        if not candidates:
            logger.warning("No models within budget, falling back to first available")
            return self.models[0]

        costs = [c["cost"] for c in candidates]
        latencies = [c["latency"] for c in candidates]
        min_cost, max_cost = min(costs), max(costs)
        min_lat, max_lat = min(latencies), max(latencies)

        best_score = -float("inf")
        best_model = None
        for c in candidates:
            norm_cost = self._normalize(c["cost"], min_cost, max_cost)
            norm_latency = self._normalize(c["latency"], min_lat, max_lat)
            
            score = (
                self.alpha * c["quality"]
                - self.beta * norm_cost
                - self.gamma * norm_latency
                - self.delta * (1.0 - c["resource"])
            )

            logger.info(
                f"Scheduler: {c['model'].name} -> score={score:.4f} "
                f"(quality={c['quality']:.2f}, cost={norm_cost:.2f}, "
                f"latency={norm_latency:.2f}, complexity={c['complexity']})"
            )

            if score > best_score:
                best_score = score
                best_model = c["model"]
                best_candidate = c

        self.selection_log.append({
            "task": task_description[:80],
            "selected_model": best_model.name,
            "score": round(best_score, 4),
            "complexity": best_candidate["complexity"],
            "reason": f"Highest utility score ({best_score:.4f}) among {len(candidates)} candidates"
        })

        logger.info(f"Scheduler selected: {best_model.name} (score={best_score:.4f})")
        return best_model

    def get_selection_log(self) -> list:
        return self.selection_log
