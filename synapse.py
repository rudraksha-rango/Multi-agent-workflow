import asyncio
import logging
from langsmith import traceable
from config import config
from llm.gemini_llm import GeminiLLM
from llm.groq_llm import GroqLLM
from llm.llm_pool import LLMPool
from llm.model_stats import ModelStats
from llm.budget import BudgetManager
from llm.cost_scheduler import CostScheduler
from core.a2a_bus import A2ABus
from core.dag_validator import DAGValidator
from agents.planner_agent import PlannerAgent
from agents.interaction_agent import InteractionAgent
from agents.orchestrator_agent import OrchestratorAgent
from agents.worker_agents import WebAgent, ContentAgent, SystemAgent, FileAgent, MemoryAgent
from memory.persistent_memory import PersistentMemory
from memory.vector_memory import VectorMemory

logging.basicConfig(level=logging.INFO if not config.DEBUG else logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SynapseX:
    def __init__(self):
        self.persistent_memory = PersistentMemory()
        self.vector_memory = VectorMemory()
        self.model_stats = ModelStats()
        
        self.models = []
        if config.GROQ_API_KEY:
            self.models.append(GroqLLM())
        if config.GEMINI_API_KEY:
            self.models.append(GeminiLLM())
            
        if not self.models:
            logger.warning("No API keys found. System will run in simulated mode.")
            self.models.append(GeminiLLM()) 

        self.scheduler = CostScheduler(
            models=self.models,
            model_stats=self.model_stats,
            alpha=config.SCHEDULER_ALPHA,
            beta=config.SCHEDULER_BETA,
            gamma=config.SCHEDULER_GAMMA,
            delta=config.SCHEDULER_DELTA
        )

        self.llm_pool = LLMPool(
            models=self.models,
            model_stats=self.model_stats
        )
        
        self.a2a_bus = A2ABus()
        self._register_workers()
        
        self.interaction_agent = InteractionAgent(llm_pool=self.llm_pool)
        self.planner_agent = PlannerAgent(llm_pool=self.llm_pool)
        self.orchestrator_agent = OrchestratorAgent(a2a_bus=self.a2a_bus, llm_pool=self.llm_pool)

    def _register_workers(self):
        self.a2a_bus.register_agent("WebAgent", WebAgent(self.llm_pool))
        self.a2a_bus.register_agent("ContentAgent", ContentAgent(self.llm_pool))
        self.a2a_bus.register_agent("SystemAgent", SystemAgent(self.llm_pool))
        self.a2a_bus.register_agent("FileAgent", FileAgent(self.llm_pool))
        self.a2a_bus.register_agent("MemoryAgent", MemoryAgent(self.llm_pool))

    @traceable(name="Synapse-X Pipeline")
    async def process_request(self, user_request: str) -> str:
        result = await self.process_request_detailed(user_request)
        return result["final_response"]

    @traceable(name="Synapse-X Pipeline Detailed")
    async def process_request_detailed(self, user_request: str,
                                        max_cost: float = None,
                                        max_runtime: float = None,
                                        max_llm_calls: int = None) -> dict:
        logger.info(f"Processing Request: {user_request}")
        
        budget_manager = BudgetManager(
            max_cost=max_cost or config.DEFAULT_MAX_COST,
            max_runtime=max_runtime or config.DEFAULT_MAX_RUNTIME,
            max_llm_calls=max_llm_calls or config.DEFAULT_MAX_LLM_CALLS
        )
        
        self.llm_pool.scheduler = self.scheduler
        self.llm_pool.budget_manager = budget_manager

        output = {
            "user_request": user_request,
            "dag_plan": [],
            "task_results": {},
            "final_response": "",
            "error": None,
            "dag_versions": [],
            "evaluation_log": [],
            "cost_summary": {},
            "scheduler_decisions": [],
            "model_stats": {}
        }
        
        try:
            cleaned_request = await self.interaction_agent.process_user_input(user_request)
            
            dag = await self.planner_agent.create_dag(cleaned_request)
            
            for task_id, node in dag.nodes.items():
                output["dag_plan"].append({
                    "task_id": task_id,
                    "description": node.description,
                    "agent_type": node.agent_type,
                    "dependencies": node.dependencies,
                })
            
            DAGValidator.validate(dag)
            logger.info("DAG validation successful.")
                
            execution_result = await self.orchestrator_agent.run_dag(dag, budget_manager)
            output["task_results"] = execution_result["task_results"]
            output["dag_versions"] = execution_result["dag_versions"]
            output["evaluation_log"] = execution_result["evaluation_log"]
            
            final_response = await self.interaction_agent.generate_final_response(
                user_request, output["task_results"]
            )
            output["final_response"] = final_response
            
            output["cost_summary"] = budget_manager.get_summary()
            output["scheduler_decisions"] = self.scheduler.get_selection_log()
            output["model_stats"] = self.model_stats.get_all_stats()
            
            self.persistent_memory.set("last_request", user_request)
            self.vector_memory.add_document(f"Request: {user_request}\nResponse: {final_response}")
            
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            output["error"] = str(e)
            output["final_response"] = f"Sorry, an error occurred: {e}"
            output["cost_summary"] = budget_manager.get_summary()
        
        self.llm_pool.scheduler = None
        self.llm_pool.budget_manager = None
        
        return output

if __name__ == "__main__":
    async def main():
        synapse = SynapseX()
        print("Synapse-X initialized. Type 'exit' to quit.")
        while True:
            try:
                user_input = input("\nUser: ")
                if user_input.lower() in ["exit", "quit"]:
                    break
                
                response = await synapse.process_request(user_input)
                print(f"\nSynapse-X:\n{response}")
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Execution error: {e}")

    asyncio.run(main())
