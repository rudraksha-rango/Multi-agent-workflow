import logging

logger = logging.getLogger(__name__)

class PolicyEngine:
    def __init__(self):
        # Default policy: which roles can execute which agent types
        self.roles = {
            "orchestrator": ["*"],  # Orchestrator can execute anything
            "web_worker": ["WebAgent"],
            "content_worker": ["ContentAgent"],
            "system_worker": ["SystemAgent", "FileAgent", "MemoryAgent"],
            "guest": []
        }
        
        # Mapping of agent_id to role
        self.agent_roles = {
            "orchestrator_node_1": "orchestrator",
            "orchestrator_node_2": "orchestrator",
            "orchestrator_node_3": "orchestrator",
        }

    def assign_role(self, agent_id: str, role: str):
        if role not in self.roles:
            logger.warning(f"Attempted to assign unknown role '{role}' to {agent_id}")
            return False
        self.agent_roles[agent_id] = role
        logger.info(f"Assigned role '{role}' to {agent_id}")
        return True

    def is_authorized(self, agent_id: str, target_agent_type: str) -> bool:
        role = self.agent_roles.get(agent_id, "guest")
        allowed_types = self.roles.get(role, [])
        
        if "*" in allowed_types:
            return True
            
        if target_agent_type in allowed_types:
            return True
            
        logger.warning(f"Authorization denied: {agent_id} (role: {role}) cannot execute {target_agent_type}")
        return False
