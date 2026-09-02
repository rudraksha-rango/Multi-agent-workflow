import logging
from typing import List, Optional
from llm.base_llm import BaseLLM, LLMResponse
from llm.cost_scheduler import CostScheduler
from llm.model_stats import ModelStats
from llm.budget import BudgetManager

logger = logging.getLogger(__name__)

class LLMPool:
    def __init__(self, models: List[BaseLLM], scheduler: CostScheduler = None,
                 model_stats: ModelStats = None, budget_manager: BudgetManager = None):
        self.models = models
        self.scheduler = scheduler
        self.model_stats = model_stats
        self.budget_manager = budget_manager
        
    async def generate(self, prompt: str, task_description: str = "", **kwargs) -> str:
        response = await self.generate_with_metadata(prompt, task_description, **kwargs)
        return response.text

    async def generate_with_metadata(self, prompt: str, task_description: str = "", **kwargs) -> LLMResponse:
        if self.scheduler and self.budget_manager:
            if not self.budget_manager.can_proceed():
                return LLMResponse(
                    text="[Budget Exhausted] Cannot make further LLM calls.",
                    model_name="none"
                )
            selected = self.scheduler.select_model(task_description, self.budget_manager)
            if selected:
                try:
                    response = await selected.generate(prompt, **kwargs)
                    if self.model_stats:
                        self.model_stats.record_call(
                            selected.name, response.input_tokens,
                            response.output_tokens, response.latency_ms,
                            True, response.estimated_cost
                        )
                    if self.budget_manager:
                        self.budget_manager.record_usage(response.estimated_cost)
                    return response
                except Exception as e:
                    logger.warning(f"Scheduler-selected model {selected.name} failed: {e}")
                    if self.model_stats:
                        self.model_stats.record_call(selected.name, 0, 0, 0, False, 0)

        last_exception = None
        for model in self.models:
            try:
                logger.debug(f"Attempting generation with {model.name}")
                response = await model.generate(prompt, **kwargs)
                if self.model_stats:
                    self.model_stats.record_call(
                        model.name, response.input_tokens,
                        response.output_tokens, response.latency_ms,
                        True, response.estimated_cost
                    )
                if self.budget_manager:
                    self.budget_manager.record_usage(response.estimated_cost)
                return response
            except Exception as e:
                logger.warning(f"Model {model.name} failed: {str(e)}. Falling back to next model.")
                if self.model_stats:
                    self.model_stats.record_call(model.name, 0, 0, 0, False, 0)
                last_exception = e
                
        logger.error("All models in LLMPool failed.")
        raise RuntimeError(f"LLMPool generation failed. Last error: {str(last_exception)}")
