import hashlib
import json
import logging
from datetime import datetime
from typing import List, Dict

logger = logging.getLogger(__name__)

class Block:
    def __init__(self, index: int, previous_hash: str, timestamp: str, data: dict):
        self.index = index
        self.previous_hash = previous_hash
        self.timestamp = timestamp
        self.data = data
        self.hash = self.calculate_hash()

    def calculate_hash(self) -> str:
        block_string = json.dumps({
            "index": self.index,
            "previous_hash": self.previous_hash,
            "timestamp": self.timestamp,
            "data": self.data
        }, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

class LedgerManager:
    def __init__(self):
        self.chain: List[Block] = []
        self.create_genesis_block()
        
    def create_genesis_block(self):
        genesis_block = Block(0, "0", datetime.utcnow().isoformat(), {"info": "Genesis Block"})
        self.chain.append(genesis_block)
        logger.info("Genesis block created in Blockchain Ledger.")

    def get_latest_block(self) -> Block:
        return self.chain[-1]

    def add_transaction(self, agent_id: str, task_hash: str, dag_hash: str, result_hash: str, status: str):
        data = {
            "agent_id": agent_id,
            "task_hash": task_hash,
            "dag_hash": dag_hash,
            "result_hash": result_hash,
            "status": status
        }
        
        latest_block = self.get_latest_block()
        new_block = Block(
            index=latest_block.index + 1,
            previous_hash=latest_block.hash,
            timestamp=datetime.utcnow().isoformat(),
            data=data
        )
        
        self.chain.append(new_block)
        logger.info(f"Block {new_block.index} added to Ledger: Task {task_hash[:8]}... status: {status}")

    def is_chain_valid(self) -> bool:
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i-1]
            
            if current_block.hash != current_block.calculate_hash():
                return False
            if current_block.previous_hash != previous_block.hash:
                return False
                
        return True

    def get_chain_data(self) -> List[dict]:
        return [
            {
                "index": block.index,
                "hash": block.hash,
                "previous_hash": block.previous_hash,
                "timestamp": block.timestamp,
                "data": block.data
            }
            for block in self.chain
        ]
