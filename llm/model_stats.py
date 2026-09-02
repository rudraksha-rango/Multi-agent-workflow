import json
import os
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, Optional

logger = logging.getLogger(__name__)

@dataclass
class ModelRecord:
    model_name: str
    avg_input_tokens: float = 0.0
    avg_output_tokens: float = 0.0
    avg_cost: float = 0.0
    avg_latency: float = 0.0
    success_rate: float = 1.0
    quality_score: float = 1.0
    total_calls: int = 0
    total_successes: int = 0
    total_cost: float = 0.0
    total_latency: float = 0.0
    total_input_tokens: int = 0
    total_output_tokens: int = 0

class ModelStats:
    def __init__(self, file_path="model_stats.json"):
        self.file_path = file_path
        self.records: Dict[str, ModelRecord] = {}
        self._load()

    def _load(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r") as f:
                    data = json.load(f)
                for name, rec in data.items():
                    self.records[name] = ModelRecord(**rec)
            except Exception as e:
                logger.error(f"Failed to load model stats: {e}")

    def _save(self):
        try:
            with open(self.file_path, "w") as f:
                json.dump({k: asdict(v) for k, v in self.records.items()}, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save model stats: {e}")

    def record_call(self, model_name: str, input_tokens: int, output_tokens: int,
                    latency_ms: float, success: bool, cost: float):
        if model_name not in self.records:
            self.records[model_name] = ModelRecord(model_name=model_name)
        
        rec = self.records[model_name]
        rec.total_calls += 1
        rec.total_input_tokens += input_tokens
        rec.total_output_tokens += output_tokens
        rec.total_cost += cost
        rec.total_latency += latency_ms
        if success:
            rec.total_successes += 1

        rec.avg_input_tokens = rec.total_input_tokens / rec.total_calls
        rec.avg_output_tokens = rec.total_output_tokens / rec.total_calls
        rec.avg_cost = rec.total_cost / rec.total_calls
        rec.avg_latency = rec.total_latency / rec.total_calls
        rec.success_rate = rec.total_successes / rec.total_calls
        rec.quality_score = rec.success_rate

        self._save()
        logger.info(f"Recorded stats for {model_name}: cost={cost:.6f}, latency={latency_ms:.0f}ms, success={success}")

    def get_stats(self, model_name: str) -> Optional[ModelRecord]:
        return self.records.get(model_name)

    def get_all_stats(self) -> Dict[str, dict]:
        return {k: asdict(v) for k, v in self.records.items()}
