import copy
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import uuid

class TaskNode(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    description: str
    agent_type: str
    dependencies: List[str] = Field(default_factory=list)
    priority: int = 1
    estimated_cost: float = 0.0
    estimated_latency: float = 0.0
    expected_output: str = ""
    retry_policy: str = "default"
    security_level: str = "low"
    status: str = "PENDING"
    result: Optional[Any] = None

class DAGVersion(BaseModel):
    version_id: int
    parent_version: Optional[int] = None
    modified_nodes: List[str] = Field(default_factory=list)
    reason: str = ""
    timestamp: str = ""
    planner_id: str = "system"

class DAG(BaseModel):
    nodes: Dict[str, TaskNode] = Field(default_factory=dict)
    version: int = 1
    
    def add_node(self, node: TaskNode):
        self.nodes[node.task_id] = node
        
    def get_node(self, task_id: str) -> Optional[TaskNode]:
        return self.nodes.get(task_id)

    def remove_node(self, task_id: str):
        if task_id not in self.nodes:
            return
        for other in self.nodes.values():
            if task_id in other.dependencies:
                removed_node = self.nodes[task_id]
                upstream_deps = [d for d in removed_node.dependencies if d != task_id]
                other.dependencies = [d for d in other.dependencies if d != task_id]
                for dep in upstream_deps:
                    if dep not in other.dependencies:
                        other.dependencies.append(dep)
        del self.nodes[task_id]

    def get_ready_tasks(self) -> List[TaskNode]:
        ready = []
        for task in self.nodes.values():
            if task.status != "PENDING":
                continue
            deps_met = all(
                self.nodes[dep_id].status == "COMPLETED" 
                for dep_id in task.dependencies if dep_id in self.nodes
            )
            if deps_met:
                ready.append(task)
        return ready

    def deep_copy(self) -> "DAG":
        return DAG.model_validate(copy.deepcopy(self.model_dump()))
