import asyncio
import logging
from core.distributed_state import DistributedStateBus
from agents.orchestrator_agent import OrchestratorAgent
from core.dag import DAG
from core.dag_manager import DAGManager
from core.dag_evaluator import DAGEvaluator
from core.dag_executor import DAGExecutor
from security.identity import AgentIdentity

logger = logging.getLogger(__name__)


class OrchestratorNode:
    def __init__(self, node_id: str, state_bus: DistributedStateBus, a2a_bus, llm_pool, identity: AgentIdentity):
        self.node_id = node_id
        self.state_bus = state_bus
        self.a2a_bus = a2a_bus
        self.llm_pool = llm_pool
        self.identity = identity
        self.is_running = False

    async def _execute_dag(self, dag: DAG, budget_manager=None) -> dict:
        dag_manager = DAGManager(dag)
        evaluator = DAGEvaluator(self.llm_pool) if self.llm_pool else None
        ledger = getattr(self.a2a_bus, 'ledger', None)

        executor = DAGExecutor(
            dag_manager=dag_manager,
            a2a_bus=self.a2a_bus,
            evaluator=evaluator,
            budget_manager=budget_manager,
            ledger=ledger,
            orchestrator_identity=self.identity
        )
        await executor.execute()

        results = {}
        for task_id, task in dag.nodes.items():
            results[task.description] = {
                "status": task.status,
                "result": task.result
            }

        return {
            "task_results": results,
            "dag_versions": dag_manager.get_version_history(),
            "evaluation_log": executor.evaluation_log,
            "final_dag_version": dag.version
        }

    async def run(self, dag: DAG, budget_manager=None):
        self.is_running = True
        logger.info(f"Node {self.node_id} started.")

        while self.is_running:
            self.state_bus.heartbeat(self.node_id)
            all_nodes = self.state_bus.get("all_nodes") or [self.node_id]
            leader = self.state_bus.elect_leader(all_nodes)

            if leader == self.node_id:
                is_executing = self.state_bus.get("dag_is_executing")
                is_complete = self.state_bus.get("dag_is_complete")

                if not is_executing and not is_complete:
                    self.state_bus.set("dag_is_executing", True)
                    logger.info(f"Leader {self.node_id} taking ownership of DAG execution.")

                    try:
                        self.a2a_bus.identity_registry.register(
                            self.identity.agent_id, self.identity.get_public_key_b64()
                        )
                        result = await self._execute_dag(dag, budget_manager)
                        self.state_bus.set("dag_result", result)
                        self.state_bus.set("dag_is_complete", True)
                        logger.info(f"Leader {self.node_id} completed DAG execution.")
                    except Exception as e:
                        logger.error(f"Leader {self.node_id} failed during execution: {e}")
                    finally:
                        self.state_bus.set("dag_is_executing", False)
                        self.is_running = False
            else:
                if self.state_bus.get("dag_is_complete"):
                    self.is_running = False

            await asyncio.sleep(1.0)

        logger.info(f"Node {self.node_id} shutting down.")


class ClusterManager:
    def __init__(self, num_nodes: int, a2a_bus, llm_pool, policy_engine):
        self.state_bus = DistributedStateBus()
        self.nodes = []
        self.node_ids = [f"orchestrator_node_{i+1}" for i in range(num_nodes)]
        self.state_bus.set("all_nodes", self.node_ids)

        for node_id in self.node_ids:
            identity = AgentIdentity(node_id)
            policy_engine.assign_role(node_id, "orchestrator")
            node = OrchestratorNode(node_id, self.state_bus, a2a_bus, llm_pool, identity)
            self.nodes.append(node)

    def get_cluster_status(self) -> dict:
        return {
            "nodes": self.node_ids,
            "active_nodes": self.state_bus.get_active_nodes(),
            "leader": self.state_bus.get_leader(),
            "dag_is_executing": self.state_bus.get("dag_is_executing") or False,
            "dag_is_complete": self.state_bus.get("dag_is_complete") or False,
        }

    async def run_cluster(self, dag: DAG, budget_manager=None) -> dict:
        logger.info(f"Starting ClusterManager with {len(self.nodes)} nodes.")
        self.state_bus.set("dag_is_executing", False)
        self.state_bus.set("dag_is_complete", False)
        self.state_bus.set("dag_result", None)

        node_tasks = [asyncio.create_task(node.run(dag, budget_manager)) for node in self.nodes]

        # Poll until DAG is done
        while not self.state_bus.get("dag_is_complete"):
            # Check if all node tasks are done (failed cluster — all nodes exited without completing)
            if all(t.done() for t in node_tasks):
                break
            await asyncio.sleep(0.5)

        for node in self.nodes:
            node.is_running = False

        await asyncio.gather(*node_tasks, return_exceptions=True)

        result = self.state_bus.get("dag_result")
        if not result:
            raise RuntimeError("Cluster failed: no node completed the DAG execution.")

        return result
