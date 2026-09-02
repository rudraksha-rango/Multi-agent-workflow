import logging
from typing import Any
from langsmith import traceable
from agents.base_agent import BaseAgent
from core.dag import TaskNode

logger = logging.getLogger(__name__)

class InteractionAgent(BaseAgent):
    def __init__(self, llm_pool=None):
        super().__init__(llm_pool=llm_pool)
        
    async def process_user_input(self, request: str) -> str:
        logger.info(f"InteractionAgent received user request: {request}")
        return request

    @traceable(name="Generate Final Response")
    async def generate_final_response(self, user_request: str, results: dict) -> str:
        logger.info("InteractionAgent generating final response.")
        
        if not self.llm_pool:
            return f"Execution complete. Results:\n{results}"
        
        context_parts = []
        for desc, info in results.items():
            status = info.get("status", "UNKNOWN")
            result = info.get("result", "No result")
            context_parts.append(f"[{status}] {desc}\n{result}")
        
        context_block = "\n\n---\n\n".join(context_parts)
        
        prompt = (
            f"You are a helpful AI assistant. The user asked:\n"
            f'"{user_request}"\n\n'
            f"To answer this, a multi-agent system searched the web, analyzed the content, "
            f"and aggregated the results. Here is all the data that was gathered:\n\n"
            f"{context_block}\n\n"
            f"Using ONLY the data above, write a clear, direct, and informative response "
            f"to the user's original question. Do NOT mention the internal pipeline, "
            f"task statuses, or agent names. Just answer the question naturally as if you "
            f"gathered this information yourself. Use bullet points or short paragraphs. "
            f"If the data is insufficient, say so honestly."
        )
        
        return await self.llm_pool.generate(prompt)

    async def execute(self, task: TaskNode, dependency_context: dict = None) -> Any:
        pass

    @property
    def agent_type(self) -> str:
        return "InteractionAgent"
