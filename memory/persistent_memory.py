import json
import os
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

class PersistentMemory:
    def __init__(self, file_path="memory_store.json"):
        self.file_path = file_path
        self._store = {}
        self._load()
        
    def _load(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r") as f:
                    self._store = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load persistent memory: {e}")
                self._store = {}
                
    def _save(self):
        try:
            with open(self.file_path, "w") as f:
                json.dump(self._store, f)
        except Exception as e:
            logger.error(f"Failed to save persistent memory: {e}")
            
    def set(self, key: str, value: Any):
        self._store[key] = value
        self._save()
        
    def get(self, key: str) -> Optional[Any]:
        return self._store.get(key)
