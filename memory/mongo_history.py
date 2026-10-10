import logging
import threading
import datetime
from typing import Dict, Any

from config import config

logger = logging.getLogger(__name__)

class MongoHistory:
    def __init__(self):
        self.client = None
        self.collection = None

        if not config.MONGODB_CONNECTION_STRING:
            logger.info("MONGODB_CONNECTION_STRING not set. MongoDB chat history is disabled.")
            return

        try:
            from pymongo import MongoClient
            self.client = MongoClient(
                config.MONGODB_CONNECTION_STRING,
                connect=False,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                socketTimeoutMS=10000,
            )
            db = self.client[config.MONGODB_DATABASE_NAME]
            self.collection = db[config.MONGODB_COLLECTION_NAME]
            logger.info(f"MongoDB configured for database '{config.MONGODB_DATABASE_NAME}'")
        except Exception as e:
            logger.error(f"Failed to configure MongoDB: {e}")

    def save_chat_threaded(self, output_data: Dict[str, Any]):
        """
        Saves the complete chat output to MongoDB using a background thread
        to avoid blocking the main asyncio event loop.
        """
        if self.collection is None:
            return

        def _save_task(data: dict):
            try:
                data_to_insert = dict(data)
                data_to_insert["_timestamp"] = datetime.datetime.utcnow()
                self.collection.insert_one(data_to_insert)
                logger.info("Successfully saved chat history to MongoDB.")
            except Exception as e:
                logger.error(f"Failed to save chat history to MongoDB: {e}")

        thread = threading.Thread(target=_save_task, args=(output_data,))
        thread.daemon = True
        thread.start()
