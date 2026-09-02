import json
import logging
from enum import Enum
from typing import Optional, List
from langsmith import traceable
from core.dag import DAG, TaskNode

logger = logging.getLogger(__name__)

class DAGDecision(Enum):
    CONTINUE = "CONTINUE"
    MODIFY = "MODIFY"
    RETRY = "RETRY"
    ADD_TASK = "ADD_TASK"
    REMOVE_TASK = "REMOVE_TASK"
    ABORT = "ABORT"

class EvaluationResult:
    def __init__(self, decision: DAGDecision, reason: str = "",
                 new_tasks: List[dict] = None, remove_task_ids: List[str] = None,
                 modify_deps: dict = None):
        self.decision = decision
        self.reason = reason
        self.new_tasks = new_tasks or []
        self.remove_task_ids = remove_task_ids or []
        self.modify_deps = modify_deps or {}

class DAGEvaluator:
    def __init__(self, llm_pool):
        self.llm_pool = llm_pool

    @traceable(name="DAG Evaluation")
    async def evaluate(self, dag: DAG, completed_task: TaskNode,
                       task_result: str, budget_remaining: dict) -> EvaluationResult:
        logger.info(f"Evaluating DAG after task {completed_task.task_id} completed")

        if completed_task.status == "FAILED":
            return EvaluationResult(
                decision=DAGDecision.RETRY,
                reason=f"Task {completed_task.task_id} failed: {task_result}",
                new_tasks=[{
                    "task_id": f"{completed_task.task_id}_retry",
                    "description": f"Retry: {completed_task.description}",
                    "agent_type": completed_task.agent_type,
                    "dependencies": list(completed_task.dependencies)
                }]
            )

        remaining_tasks = [t for t in dag.nodes.values() if t.status == "PENDING"]
        if not remaining_tasks:
            return EvaluationResult(
                decision=DAGDecision.CONTINUE,
                reason="All tasks completed or in progress"
            )

        if budget_remaining.get("cost", 1.0) <= 0 or budget_remaining.get("llm_calls", 1) <= 0:
            return EvaluationResult(
                decision=DAGDecision.ABORT,
                reason="Budget exhausted"
            )

        completed_tasks_summary = []
        for tid, node in dag.nodes.items():
            if node.status == "COMPLETED":
                completed_tasks_summary.append(
                    f"- {tid} ({node.agent_type}): {node.description} -> {str(node.result)[:200]}"
                )
        pending_tasks_summary = []
        for t in remaining_tasks:
            pending_tasks_summary.append(
                f"- {t.task_id} ({t.agent_type}): {t.description} [deps: {t.dependencies}]"
            )

        prompt = f"""You are a DAG evaluation agent. A multi-agent system is executing a task pipeline.

A task just completed:
- Task ID: {completed_task.task_id}
- Agent: {completed_task.agent_type}
- Description: {completed_task.description}
- Result (truncated): {str(task_result)[:500]}

Completed tasks so far:
{chr(10).join(completed_tasks_summary) if completed_tasks_summary else "None"}

Remaining pending tasks:
{chr(10).join(pending_tasks_summary) if pending_tasks_summary else "None"}

Budget remaining: cost=${budget_remaining.get('cost', 'unlimited'):.4f}, llm_calls={budget_remaining.get('llm_calls', 'unlimited')}

Evaluate whether the current DAG plan is still optimal. Respond with ONLY valid JSON:
{{
    "decision": "CONTINUE" or "ADD_TASK" or "REMOVE_TASK" or "MODIFY" or "ABORT",
    "reason": "brief explanation",
    "new_tasks": [
        {{
            "task_id": "string",
            "description": "string",
            "agent_type": "WebAgent or ContentAgent or SystemAgent",
            "dependencies": ["list of existing task_ids"]
        }}
    ],
    "remove_task_ids": ["list of task_ids to remove"],
    "modify_deps": {{"task_id": ["new_dep1", "new_dep2"]}}
}}

Only include new_tasks if decision is ADD_TASK.
Only include remove_task_ids if decision is REMOVE_TASK.
Only include modify_deps if decision is MODIFY.
For most cases, CONTINUE is correct. Only suggest changes if the result clearly indicates the plan is insufficient."""

        try:
            response = await self.llm_pool.generate(prompt)
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]

            parsed = json.loads(response.strip())
            decision = DAGDecision(parsed.get("decision", "CONTINUE"))

            return EvaluationResult(
                decision=decision,
                reason=parsed.get("reason", ""),
                new_tasks=parsed.get("new_tasks", []),
                remove_task_ids=parsed.get("remove_task_ids", []),
                modify_deps=parsed.get("modify_deps", {})
            )
        except Exception as e:
            logger.warning(f"DAG evaluation failed, defaulting to CONTINUE: {e}")
            return EvaluationResult(
                decision=DAGDecision.CONTINUE,
                reason=f"Evaluation error: {e}"
            )
