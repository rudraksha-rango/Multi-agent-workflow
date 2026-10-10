import asyncio
import hashlib
import json
import logging
from langsmith import traceable
from core.dag import DAG, TaskNode
from core.dag_manager import DAGManager
from core.dag_evaluator import DAGEvaluator, DAGDecision
from core.a2a_bus import A2ABus
from blockchain.ledger import LedgerManager
from security.identity import AgentIdentity

logger = logging.getLogger(__name__)

class DAGExecutor:
    def __init__(self, dag_manager: DAGManager, a2a_bus: A2ABus,
                 evaluator: DAGEvaluator = None, budget_manager=None,
                 ledger: LedgerManager = None, orchestrator_identity: AgentIdentity = None):
        self.dag_manager = dag_manager
        self.dag = dag_manager.dag
        self.a2a_bus = a2a_bus
        self.evaluator = evaluator
        self.budget_manager = budget_manager
        self.ledger = ledger
        self.orchestrator_identity = orchestrator_identity
        
        self.running_tasks = set()
        self.evaluation_log = []
        self._abort = False

    def _hash_data(self, data: dict) -> str:
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode('utf-8')).hexdigest()

    @traceable(name="DAG Execution")
    async def execute(self):
        logger.info("Starting DAG Execution")
        while True:
            if self._abort:
                logger.info("DAG Execution Aborted")
                break

            ready_tasks = self.dag.get_ready_tasks()
            
            if not ready_tasks and not self.running_tasks:
                break
                
            for task in ready_tasks:
                if self._abort:
                    break
                task.status = "RUNNING"
                self.running_tasks.add(task.task_id)
                
                dependency_context = {}
                for dep_id in task.dependencies:
                    dep_node = self.dag.get_node(dep_id)
                    if dep_node and dep_node.status == "COMPLETED" and dep_node.result:
                        dependency_context[dep_id] = {
                            "description": dep_node.description,
                            "result": dep_node.result
                        }
                
                asyncio.create_task(self._run_task(task, dependency_context))
                
            await asyncio.sleep(0.1)
            
        logger.info("DAG Execution Completed")
        
    async def _run_task(self, task: TaskNode, dependency_context: dict = None):
        try:
            logger.info(f"Task {task.task_id} ({task.description}) dispatched to {task.agent_type}")
            
            # Use Orchestrator identity if provided to sign requests on the bus
            result = await self.a2a_bus.dispatch_task(task, dependency_context, caller_identity=self.orchestrator_identity)
            task.result = result
            task.status = "COMPLETED"
            logger.info(f"Task {task.task_id} COMPLETED.")
        except Exception as e:
            logger.error(f"Task {task.task_id} FAILED: {str(e)}")
            task.status = "FAILED"
            task.result = str(e)
        finally:
            self.running_tasks.remove(task.task_id)
            
            # Phase 3B: Record on Blockchain Ledger
            if self.ledger:
                task_hash = self._hash_data({
                    "task_id": task.task_id, 
                    "description": task.description, 
                    "agent_type": task.agent_type
                })
                dag_hash = self._hash_data([t.task_id for t in self.dag.nodes.values()])
                result_hash = self._hash_data({"result": str(task.result)})
                
                agent_id = self.orchestrator_identity.agent_id if self.orchestrator_identity else "system"
                self.ledger.add_transaction(agent_id, task_hash, dag_hash, result_hash, task.status)

        if self.evaluator and not self._abort:
            await self._evaluate_and_adapt(task)

    async def _evaluate_and_adapt(self, completed_task: TaskNode):
        budget_remaining = {}
        if self.budget_manager:
            remaining = self.budget_manager.remaining_budget()
            budget_remaining = {
                "cost": remaining["remaining_cost"],
                "llm_calls": remaining["remaining_llm_calls"]
            }
        else:
            budget_remaining = {"cost": 999.0, "llm_calls": 999}

        eval_result = await self.evaluator.evaluate(
            self.dag, completed_task, str(completed_task.result), budget_remaining
        )

        self.evaluation_log.append({
            "task_id": completed_task.task_id,
            "decision": eval_result.decision.value,
            "reason": eval_result.reason
        })

        logger.info(f"DAG Evaluation after {completed_task.task_id}: {eval_result.decision.value} - {eval_result.reason}")

        if eval_result.decision == DAGDecision.CONTINUE:
            return

        if eval_result.decision == DAGDecision.ABORT:
            self._abort = True
            logger.warning(f"DAG Execution ABORTED: {eval_result.reason}")
            return

        if eval_result.decision == DAGDecision.RETRY:
            for task_data in eval_result.new_tasks:
                new_task = TaskNode(
                    task_id=task_data["task_id"],
                    description=task_data["description"],
                    agent_type=task_data["agent_type"],
                    dependencies=task_data.get("dependencies", [])
                )
                self.dag_manager.retry_with_alternative(completed_task.task_id, new_task)

        elif eval_result.decision == DAGDecision.ADD_TASK:
            for task_data in eval_result.new_tasks:
                new_task = TaskNode(
                    task_id=task_data["task_id"],
                    description=task_data["description"],
                    agent_type=task_data["agent_type"],
                    dependencies=task_data.get("dependencies", [])
                )
                self.dag_manager.add_node(new_task)

        elif eval_result.decision == DAGDecision.REMOVE_TASK:
            for tid in eval_result.remove_task_ids:
                self.dag_manager.remove_node(tid)

        elif eval_result.decision == DAGDecision.MODIFY:
            for tid, new_deps in eval_result.modify_deps.items():
                self.dag_manager.modify_dependencies(tid, new_deps)
