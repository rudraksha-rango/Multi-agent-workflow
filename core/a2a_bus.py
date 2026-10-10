import asyncio
import logging
from core.dag import TaskNode
from security.identity import IdentityRegistry, AgentIdentity
from security.policy_engine import PolicyEngine

logger = logging.getLogger(__name__)

class A2ABus:
    def __init__(self, identity_registry: IdentityRegistry = None, policy_engine: PolicyEngine = None):
        self.agents = {}
        self.identity_registry = identity_registry or IdentityRegistry()
        self.policy_engine = policy_engine or PolicyEngine()
        
        # Security metrics for the UI
        self.security_metrics = {
            "authenticated_requests": 0,
            "rejected_requests": 0,
            "unauthorized_attempts": 0,
            "signature_failures": 0
        }
        
    def register_agent(self, agent_type: str, agent_instance):
        self.agents[agent_type] = agent_instance
        logger.info(f"Registered agent: {agent_type}")
        
    async def dispatch_task(self, task: TaskNode, dependency_context: dict = None, caller_identity: AgentIdentity = None):
        agent = self.agents.get(task.agent_type)
        if not agent:
            raise ValueError(f"No agent registered for type: {task.agent_type}")
            
        # If no caller identity is provided, assume it's an insecure internal dispatch (e.g. from tests)
        if caller_identity:
            # 1. Authentication: Sign the task payload
            payload = {
                "task_id": task.task_id,
                "agent_type": task.agent_type,
                "description": task.description
            }
            signature = caller_identity.sign_message(payload)
            
            # Verify the signature
            is_valid = self.identity_registry.verify_signature(caller_identity.agent_id, payload, signature)
            if not is_valid:
                self.security_metrics["signature_failures"] += 1
                self.security_metrics["rejected_requests"] += 1
                raise PermissionError(f"Authentication failed: Invalid signature from {caller_identity.agent_id}")
                
            # 2. Authorization: Check if caller is allowed to execute this agent type
            is_authorized = self.policy_engine.is_authorized(caller_identity.agent_id, task.agent_type)
            if not is_authorized:
                self.security_metrics["unauthorized_attempts"] += 1
                self.security_metrics["rejected_requests"] += 1
                raise PermissionError(f"Authorization failed: {caller_identity.agent_id} cannot execute {task.agent_type}")
                
            self.security_metrics["authenticated_requests"] += 1
            logger.info(f"Secure dispatch: {caller_identity.agent_id} authorized to execute {task.agent_type} (task {task.task_id})")

        return await agent.execute(task, dependency_context)
