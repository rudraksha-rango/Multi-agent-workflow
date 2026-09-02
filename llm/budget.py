import logging
import time

logger = logging.getLogger(__name__)

class BudgetManager:
    def __init__(self, max_cost: float = 1.0, max_runtime: float = 120.0,
                 max_llm_calls: int = 20):
        self.max_cost = max_cost
        self.max_runtime = max_runtime
        self.max_llm_calls = max_llm_calls
        self.current_cost = 0.0
        self.current_llm_calls = 0
        self.start_time = time.time()

    def can_proceed(self) -> bool:
        if self.current_cost >= self.max_cost:
            logger.warning(f"Budget exhausted: cost {self.current_cost:.6f} >= {self.max_cost}")
            return False
        if self.current_llm_calls >= self.max_llm_calls:
            logger.warning(f"Budget exhausted: LLM calls {self.current_llm_calls} >= {self.max_llm_calls}")
            return False
        elapsed = time.time() - self.start_time
        if elapsed >= self.max_runtime:
            logger.warning(f"Budget exhausted: runtime {elapsed:.1f}s >= {self.max_runtime}s")
            return False
        return True

    def record_usage(self, cost: float, llm_calls: int = 1):
        self.current_cost += cost
        self.current_llm_calls += llm_calls
        logger.info(f"Budget: cost={self.current_cost:.6f}/{self.max_cost}, calls={self.current_llm_calls}/{self.max_llm_calls}")

    def remaining_budget(self) -> dict:
        elapsed = time.time() - self.start_time
        return {
            "remaining_cost": max(0, self.max_cost - self.current_cost),
            "remaining_runtime": max(0, self.max_runtime - elapsed),
            "remaining_llm_calls": max(0, self.max_llm_calls - self.current_llm_calls),
            "total_cost": self.current_cost,
            "total_llm_calls": self.current_llm_calls,
            "elapsed_time": elapsed
        }

    def get_summary(self) -> dict:
        elapsed = time.time() - self.start_time
        return {
            "max_cost": self.max_cost,
            "used_cost": round(self.current_cost, 6),
            "max_llm_calls": self.max_llm_calls,
            "used_llm_calls": self.current_llm_calls,
            "max_runtime": self.max_runtime,
            "elapsed_runtime": round(elapsed, 2)
        }
