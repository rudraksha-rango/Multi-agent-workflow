import logging

logger = logging.getLogger(__name__)

class MCPServer:
    def __init__(self):
        self.tools = {}
        
    def register_tool(self, tool_id: str, description: str, handler):
        self.tools[tool_id] = {
            "description": description,
            "handler": handler
        }
        logger.info(f"Registered MCP tool: {tool_id}")
        
    async def execute_tool(self, tool_id: str, **kwargs):
        if tool_id not in self.tools:
            raise ValueError(f"Tool {tool_id} not found.")
            
        logger.info(f"Executing MCP tool: {tool_id}")
        return await self.tools[tool_id]["handler"](**kwargs)
