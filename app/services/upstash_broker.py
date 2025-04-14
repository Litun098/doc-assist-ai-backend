import json
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple
from kombu.utils.url import parse_url
from celery.backends.base import KeyValueStoreBackend
from celery.utils.log import get_logger
from app.services.redis_client import UpstashRedisClient

logger = get_logger(__name__)

class UpstashRedisBroker(KeyValueStoreBackend):
    """Celery broker using Upstash Redis REST API"""
    
    def __init__(self, url=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Parse the URL
        if url:
            _, host, port, _, password, path, _ = parse_url(url)
            db = path.strip('/') if path else '0'
        else:
            host = kwargs.get('host', 'localhost')
            port = kwargs.get('port', 6379)
            password = kwargs.get('password', None)
            db = kwargs.get('db', 0)
        
        # Create the Upstash Redis client
        self.client = UpstashRedisClient(
            url=kwargs.get('rest_url'),
            token=kwargs.get('rest_token')
        )
        
        # Set up queue names
        self.task_queue = 'celery_tasks'
        self.result_queue = 'celery_results'
        self.task_key_prefix = 'celery_task:'
        self.result_key_prefix = 'celery_result:'
    
    def _get_task_key(self, task_id):
        return f"{self.task_key_prefix}{task_id}"
    
    def _get_result_key(self, task_id):
        return f"{self.result_key_prefix}{task_id}"
    
    def publish_task(self, task_id, task_name, args=None, kwargs=None, **options):
        """Publish a task to the queue"""
        task_data = {
            'id': task_id,
            'task': task_name,
            'args': args or [],
            'kwargs': kwargs or {},
            'options': options,
            'created_at': time.time()
        }
        
        # Store task data
        task_key = self._get_task_key(task_id)
        self.client.set(task_key, json.dumps(task_data))
        
        # Add to task queue
        self.client.rpush(self.task_queue, task_id)
        
        return task_id
    
    def get_task(self):
        """Get a task from the queue"""
        task_id = self.client.lpop(self.task_queue)
        if not task_id:
            return None
        
        task_key = self._get_task_key(task_id)
        task_data = self.client.get(task_key)
        
        if not task_data:
            return None
        
        return json.loads(task_data)
    
    def store_result(self, task_id, result, status, traceback=None):
        """Store a task result"""
        result_data = {
            'task_id': task_id,
            'result': result,
            'status': status,
            'traceback': traceback,
            'completed_at': time.time()
        }
        
        # Store result data
        result_key = self._get_result_key(task_id)
        self.client.set(result_key, json.dumps(result_data))
        
        # Add to result queue
        self.client.rpush(self.result_queue, task_id)
        
        return result
    
    def get_result(self, task_id):
        """Get a task result"""
        result_key = self._get_result_key(task_id)
        result_data = self.client.get(result_key)
        
        if not result_data:
            return None
        
        return json.loads(result_data)
    
    def _get(self, key):
        """Get a value from the store"""
        return self.client.get(key)
    
    def _set(self, key, value):
        """Set a value in the store"""
        return self.client.set(key, value)
    
    def _delete(self, key):
        """Delete a value from the store"""
        return self.client.delete(key)
