import os
import json
import base64
import logging
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

logger = logging.getLogger(__name__)

class AgentIdentity:
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self._private_key = ed25519.Ed25519PrivateKey.generate()
        self._public_key = self._private_key.public_key()
        
    def get_public_key_bytes(self) -> bytes:
        return self._public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
    def get_public_key_b64(self) -> str:
        return base64.b64encode(self.get_public_key_bytes()).decode('utf-8')

    def sign_message(self, payload: dict) -> str:
        # Sort keys to ensure deterministic serialization
        message_bytes = json.dumps(payload, sort_keys=True).encode('utf-8')
        signature = self._private_key.sign(message_bytes)
        return base64.b64encode(signature).decode('utf-8')

class IdentityRegistry:
    def __init__(self):
        self._identities = {}
        
    def register(self, agent_id: str, public_key_b64: str):
        self._identities[agent_id] = public_key_b64
        logger.info(f"Registered identity for {agent_id}")
        
    def get_public_key(self, agent_id: str) -> str:
        return self._identities.get(agent_id)

    def verify_signature(self, agent_id: str, payload: dict, signature_b64: str) -> bool:
        public_key_b64 = self.get_public_key(agent_id)
        if not public_key_b64:
            logger.warning(f"Verification failed: Agent {agent_id} not found in registry")
            return False
            
        try:
            public_key_bytes = base64.b64decode(public_key_b64)
            public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_key_bytes)
            
            message_bytes = json.dumps(payload, sort_keys=True).encode('utf-8')
            signature_bytes = base64.b64decode(signature_b64)
            
            public_key.verify(signature_bytes, message_bytes)
            return True
        except InvalidSignature:
            logger.warning(f"Verification failed: Invalid signature for {agent_id}")
            return False
        except Exception as e:
            logger.error(f"Verification error for {agent_id}: {e}")
            return False
