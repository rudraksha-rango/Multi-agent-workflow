import logging
from typing import List

logger = logging.getLogger(__name__)

class VectorMemory:
    def __init__(self):
        self.documents = []
        
    def add_document(self, text: str, metadata: dict = None):
        self.documents.append({
            "text": text,
            "metadata": metadata or {}
        })
        logger.info(f"Added document to vector memory: {text[:30]}...")
        
    def search(self, query: str, limit: int = 5) -> List[dict]:
        logger.info(f"Searching vector memory for: {query}")
        return self.documents[-limit:]
