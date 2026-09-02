import asyncio
import logging
import re
from typing import Any
from ddgs import DDGS
from langsmith import traceable
from agents.base_agent import BaseAgent
from core.dag import TaskNode

logger = logging.getLogger(__name__)


def _build_context_string(dependency_context: dict) -> str:
    if not dependency_context:
        return ""
    parts = []
    for task_id, info in dependency_context.items():
        parts.append(f"--- Result from [{task_id}]: {info['description']} ---\n{info['result']}")
    return "\n\n".join(parts)


class WebAgent(BaseAgent):
    
    @staticmethod
    def _extract_search_query(description: str) -> str:
        patterns = [
            r'^search\s+(?:the\s+)?(?:web|internet)\s+(?:for|about)\s+',
            r'^find\s+(?:the\s+)?(?:latest\s+)?',
            r'^look\s+up\s+',
            r'^retrieve\s+',
            r'^get\s+',
        ]
        query = description
        for pattern in patterns:
            query = re.sub(pattern, '', query, flags=re.IGNORECASE)
        query = query.rstrip('.')
        return query.strip() if query.strip() else description
    
    @traceable(name="WebAgent Execution")
    async def execute(self, task: TaskNode, dependency_context: dict = None) -> Any:
        logger.info(f"WebAgent executing: {task.description}")
        search_query = self._extract_search_query(task.description)
        logger.info(f"WebAgent search query: {search_query}")
        try:
            def search_func():
                with DDGS() as ddgs:
                    results = list(ddgs.text(search_query, max_results=5))
                if not results:
                    return "No search results found."
                formatted = []
                for i, r in enumerate(results, 1):
                    formatted.append(
                        f"{i}. {r.get('title', 'N/A')}\n"
                        f"   {r.get('body', 'No summary available.')}\n"
                        f"   Source: {r.get('href', 'N/A')}"
                    )
                return "\n\n".join(formatted)

            search_results = await asyncio.to_thread(search_func)
            return f"Web Search Results for: '{search_query}'\n\n{search_results}"
        except Exception as e:
            logger.error(f"WebAgent search failed: {e}")
            return f"Web search encountered an error: {e}. Please try again."

    @property
    def agent_type(self) -> str:
        return "WebAgent"


class ContentAgent(BaseAgent):
    @traceable(name="ContentAgent Execution")
    async def execute(self, task: TaskNode, dependency_context: dict = None) -> Any:
        logger.info(f"ContentAgent executing: {task.description}")
        
        upstream_data = _build_context_string(dependency_context)
        
        if self.llm_pool:
            if upstream_data:
                prompt = (
                    f"You are a content analysis agent. Your task is:\n"
                    f"{task.description}\n\n"
                    f"Here is the data from previous steps that you must work with:\n\n"
                    f"{upstream_data}\n\n"
                    f"Based on the above data, produce a clear, detailed, and well-structured summary."
                )
            else:
                prompt = (
                    f"You are a content analysis agent. Perform the following task:\n"
                    f"{task.description}\n\n"
                    f"Provide a detailed and well-structured response."
                )
            return await self.llm_pool.generate(prompt)
        
        return f"ContentAgent completed (no LLM): {task.description}"

    @property
    def agent_type(self) -> str:
        return "ContentAgent"


class SystemAgent(BaseAgent):
    @traceable(name="SystemAgent Execution")
    async def execute(self, task: TaskNode, dependency_context: dict = None) -> Any:
        logger.info(f"SystemAgent executing: {task.description}")
        
        upstream_data = _build_context_string(dependency_context)
        
        if self.llm_pool:
            if upstream_data:
                prompt = (
                    f"You are a system aggregation agent. Your task is:\n"
                    f"{task.description}\n\n"
                    f"Here is the data from previous steps:\n\n"
                    f"{upstream_data}\n\n"
                    f"Aggregate and format this data into a clean, readable final output for the user."
                )
            else:
                prompt = (
                    f"You are a system agent. Perform the following task:\n"
                    f"{task.description}\n\n"
                    f"Provide a clean, formatted output."
                )
            return await self.llm_pool.generate(prompt)
            
        return f"SystemAgent completed (no LLM): {task.description}"

    @property
    def agent_type(self) -> str:
        return "SystemAgent"


class FileAgent(BaseAgent):
    @traceable(name="FileAgent Execution")
    async def execute(self, task: TaskNode, dependency_context: dict = None) -> Any:
        logger.info(f"FileAgent executing: {task.description}")
        await asyncio.sleep(0.5)
        return f"Simulated File Action for: {task.description}"

    @property
    def agent_type(self) -> str:
        return "FileAgent"


class MemoryAgent(BaseAgent):
    @traceable(name="MemoryAgent Execution")
    async def execute(self, task: TaskNode, dependency_context: dict = None) -> Any:
        logger.info(f"MemoryAgent executing: {task.description}")
        await asyncio.sleep(0.2)
        return f"Simulated Memory Access for: {task.description}"

    @property
    def agent_type(self) -> str:
        return "MemoryAgent"
