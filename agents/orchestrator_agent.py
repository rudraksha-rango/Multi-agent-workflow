import logging
from typing import Any
from agents.base_agent import BaseAgent
from core.dag import DAG, TaskNode
from core.dag_manager import DAGManager
from core.dag_evaluator import DAGEvaluator
from core.dag_executor import DAGExecutor
from core.a2a_bus import A2ABus

logger = logging.getLogger(__name__)

class OrchestratorAgent(BaseAgent):
    def __init__(self, a2a_bus: A2ABus, llm_pool=None):
        super().__init__(llm_pool=llm_pool)
        self.a2a_bus = a2a_bus
        
    async def run_dag(self, dag: DAG, budget_manager=None) -> dict:
        logger.info("OrchestratorAgent starting execution of DAG.")
        
        dag_manager = DAGManager(dag)
        evaluator = DAGEvaluator(self.llm_pool) if self.llm_pool else None
        
        executor = DAGExecutor(
            dag_manager=dag_manager,
            a2a_bus=self.a2a_bus,
            evaluator=evaluator,
            budget_manager=budget_manager
        )
        await executor.execute()
        
        results = {}
        for task_id, task in dag.nodes.items():
            results[task.description] = {
                "status": task.status,
                "result": task.result
            }
            
        logger.info("OrchestratorAgent finished execution.")
        return {
            "task_results": results,
            "dag_versions": dag_manager.get_version_history(),
            "evaluation_log": executor.evaluation_log,
            "final_dag_version": dag.version
        }

    async def execute(self, task: TaskNode, dependency_context: dict = None) -> Any:
        pass

    @property
    def agent_type(self) -> str:
        return "OrchestratorAgent"
