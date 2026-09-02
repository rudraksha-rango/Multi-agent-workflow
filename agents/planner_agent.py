import json
import logging
from typing import Dict, Any
from langsmith import traceable
from agents.base_agent import BaseAgent
from core.dag import DAG, TaskNode
from llm.llm_pool import LLMPool

logger = logging.getLogger(__name__)

class PlannerAgent(BaseAgent):
    def __init__(self, llm_pool: LLMPool):
        super().__init__(llm_pool=llm_pool)
        
    @traceable(name="PlannerAgent Create DAG")
    async def create_dag(self, request: str) -> DAG:
        logger.info(f"Planner Agent creating DAG for request: {request}")
        
        prompt = f"""
        You are a Planner Agent in a multi-agent system.
        Decompose the following user request into a JSON representation of a Directed Acyclic Graph (DAG) of tasks.
        
        Available Worker Agents:
        - WebAgent: For searching the web.
        - ContentAgent: For summarizing or analyzing content.
        - SystemAgent: For general data manipulation or aggregation.
        
        Output MUST be valid JSON matching this structure exactly (do not wrap in markdown):
        {{
            "tasks": [
                {{
                    "task_id": "string",
                    "description": "string",
                    "agent_type": "string",
                    "dependencies": ["list of task_ids"]
                }}
            ]
        }}
        
        User Request: {request}
        """
        
        try:
            response = await self.llm_pool.generate(prompt)
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]
                
            parsed = json.loads(response.strip())
            
            dag = DAG()
            for t in parsed.get("tasks", []):
                node = TaskNode(
                    task_id=t["task_id"],
                    description=t["description"],
                    agent_type=t["agent_type"],
                    dependencies=t.get("dependencies", [])
                )
                dag.add_node(node)
            return dag
            
        except Exception as e:
            logger.error(f"Failed to create DAG: {e}")
            raise RuntimeError(f"Planner failed to parse DAG from LLM output: {e}")

    async def execute(self, task: TaskNode, dependency_context: dict = None) -> Any:
        pass

    @property
    def agent_type(self) -> str:
        return "PlannerAgent"
