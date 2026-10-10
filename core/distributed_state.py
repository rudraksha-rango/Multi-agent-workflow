import time
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class DistributedStateBus:
    """
    Simulates a distributed key-value store (like Redis or etcd)
    used for cluster coordination in a decentralized architecture.
    """
    def __init__(self):
        self._state: Dict[str, Any] = {}
        self._heartbeats: Dict[str, float] = {}
        self._leader_id = None
        self._leader_timeout = 5.0  

    def set(self, key: str, value: Any):
        self._state[key] = value

    def get(self, key: str) -> Any:
        return self._state.get(key)

    def heartbeat(self, node_id: str):
        self._heartbeats[node_id] = time.time()
        
    def get_active_nodes(self) -> list:
        current_time = time.time()
        active = []
        for node_id, last_beat in self._heartbeats.items():
            if current_time - last_beat < self._leader_timeout:
                active.append(node_id)
        return active

    def elect_leader(self, candidates: list) -> str:
        current_time = time.time()
        
        # If we have a leader and they are still alive, keep them
        if self._leader_id:
            last_beat = self._heartbeats.get(self._leader_id, 0)
            if current_time - last_beat < self._leader_timeout:
                return self._leader_id
                
        # Leader is dead or missing, elect a new one
        active_nodes = self.get_active_nodes()
        valid_candidates = [c for c in candidates if c in active_nodes]
        
        if valid_candidates:
            # Simple consensus: lowest string ID wins
            self._leader_id = sorted(valid_candidates)[0]
            logger.info(f"Leader election: {self._leader_id} is the new leader.")
        else:
            self._leader_id = None
            
        return self._leader_id

    def get_leader(self) -> str:
        return self._leader_id
