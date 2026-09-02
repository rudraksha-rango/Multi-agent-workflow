import logging
from datetime import datetime
from typing import List, Optional
from core.dag import DAG, DAGVersion, TaskNode

logger = logging.getLogger(__name__)

class DAGManager:
    def __init__(self, dag: DAG):
        self.dag = dag
        self.version_history: List[DAGVersion] = []
        self._snapshot("Initial DAG created")

    def _snapshot(self, reason: str, modified_nodes: List[str] = None):
        version = DAGVersion(
            version_id=self.dag.version,
            parent_version=self.dag.version - 1 if self.dag.version > 1 else None,
            modified_nodes=modified_nodes or [],
            reason=reason,
            timestamp=datetime.utcnow().isoformat(),
            planner_id="system"
        )
        self.version_history.append(version)
        logger.info(f"DAG snapshot v{version.version_id}: {reason}")

    def add_node(self, node: TaskNode, insert_before: str = None):
        self.dag.add_node(node)
        if insert_before and insert_before in self.dag.nodes:
            target = self.dag.nodes[insert_before]
            node.dependencies = list(target.dependencies)
            target.dependencies = [node.task_id]
        self.dag.version += 1
        self._snapshot(
            f"Added node {node.task_id} ({node.agent_type})",
            modified_nodes=[node.task_id]
        )
        logger.info(f"DAGManager: Added node {node.task_id}")

    def remove_node(self, task_id: str):
        if task_id not in self.dag.nodes:
            return
        self.dag.remove_node(task_id)
        self.dag.version += 1
        self._snapshot(
            f"Removed node {task_id}",
            modified_nodes=[task_id]
        )
        logger.info(f"DAGManager: Removed node {task_id}")

    def modify_dependencies(self, task_id: str, new_deps: List[str]):
        node = self.dag.get_node(task_id)
        if not node:
            return
        old_deps = list(node.dependencies)
        node.dependencies = new_deps
        self.dag.version += 1
        self._snapshot(
            f"Modified deps for {task_id}: {old_deps} -> {new_deps}",
            modified_nodes=[task_id]
        )
        logger.info(f"DAGManager: Modified dependencies for {task_id}")

    def retry_with_alternative(self, failed_task_id: str, new_task: TaskNode):
        failed = self.dag.get_node(failed_task_id)
        if not failed:
            return
        new_task.dependencies = list(failed.dependencies)
        self.dag.add_node(new_task)
        for other in self.dag.nodes.values():
            if failed_task_id in other.dependencies:
                other.dependencies = [
                    new_task.task_id if d == failed_task_id else d
                    for d in other.dependencies
                ]
        self.dag.version += 1
        self._snapshot(
            f"Retry: replaced {failed_task_id} with {new_task.task_id}",
            modified_nodes=[failed_task_id, new_task.task_id]
        )
        logger.info(f"DAGManager: Retrying {failed_task_id} with {new_task.task_id}")

    def create_branch(self, parent_task_id: str, new_tasks: List[TaskNode]):
        for task in new_tasks:
            task.dependencies = [parent_task_id]
            self.dag.add_node(task)
        self.dag.version += 1
        new_ids = [t.task_id for t in new_tasks]
        self._snapshot(
            f"Branched from {parent_task_id}: {new_ids}",
            modified_nodes=[parent_task_id] + new_ids
        )
        logger.info(f"DAGManager: Created branch from {parent_task_id}")

    def get_version_history(self) -> List[dict]:
        return [v.model_dump() for v in self.version_history]
