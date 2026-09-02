from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import time

@dataclass
class LLMResponse:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    model_name: str = ""
    estimated_cost: float = 0.0

class BaseLLM(ABC):
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        pass
        
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def cost_per_input_token(self) -> float:
        pass

    @property
    @abstractmethod
    def cost_per_output_token(self) -> float:
        pass
