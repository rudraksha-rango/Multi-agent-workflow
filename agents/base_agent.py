from abc import ABC, abstractmethod
from typing import Any, Optional
from core.dag import TaskNode
from llm.llm_pool import LLMPool

class BaseAgent(ABC):
    def __init__(self, llm_pool: LLMPool = None):
        self.llm_pool = llm_pool

    @abstractmethod
    async def execute(self, task: TaskNode, dependency_context: dict = None) -> Any:
        pass
        
    @property
    @abstractmethod
    def agent_type(self) -> str:
        pass
