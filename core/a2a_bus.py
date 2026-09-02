import asyncio
import logging
from core.dag import TaskNode

logger = logging.getLogger(__name__)

class A2ABus:
    def __init__(self):
        self.agents = {}
        
    def register_agent(self, agent_type: str, agent_instance):
        self.agents[agent_type] = agent_instance
        logger.info(f"Registered agent: {agent_type}")
        
    async def dispatch_task(self, task: TaskNode, dependency_context: dict = None):
        agent = self.agents.get(task.agent_type)
        if not agent:
            raise ValueError(f"No agent registered for type: {task.agent_type}")
            
        return await agent.execute(task, dependency_context)
