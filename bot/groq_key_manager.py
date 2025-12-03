import os
import logging
import time
from typing import Optional, List
from groq import Groq
from groq import RateLimitError, APIError

logger = logging.getLogger(__name__)

class GroqKeyManager:
    """
    Manages multiple Groq API keys with automatic rotation.
    When a key hits rate limit, automatically switches to next available key.
    """
    
    def __init__(self):
        self.api_keys: List[str] = []
        self.clients: dict = {}
        self.rate_limited_until: dict = {}
        self.current_key_index: int = 0
        self.model = "llama-3.3-70b-versatile"
        self._load_api_keys()
    
    def _load_api_keys(self):
        """Load all available Groq API keys from environment variables."""
        primary_key = os.getenv('GROQ_API_KEY')
        if primary_key:
            self.api_keys.append(primary_key)
            self.clients[primary_key] = Groq(api_key=primary_key)
            logger.info("Loaded primary GROQ_API_KEY")
        
        for i in range(2, 11):
            key_name = f'GROQ_API_KEY_{i}'
            key = os.getenv(key_name)
            if key:
                self.api_keys.append(key)
                self.clients[key] = Groq(api_key=key)
                logger.info(f"Loaded {key_name}")
        
        if not self.api_keys:
            raise ValueError("No Groq API keys found. Please set GROQ_API_KEY environment variable.")
        
        logger.info(f"Total Groq API keys loaded: {len(self.api_keys)}")
    
    def _is_key_available(self, key: str) -> bool:
        """Check if a key is available (not rate limited)."""
        if key not in self.rate_limited_until:
            return True
        
        if time.time() >= self.rate_limited_until[key]:
            del self.rate_limited_until[key]
            logger.info(f"Key {key[:8]}... is now available again")
            return True
        
        remaining = int(self.rate_limited_until[key] - time.time())
        logger.debug(f"Key {key[:8]}... still rate limited for {remaining}s")
        return False
    
    def _mark_key_rate_limited(self, key: str, retry_after: int = 60):
        """Mark a key as rate limited for specified seconds."""
        self.rate_limited_until[key] = time.time() + retry_after
        logger.warning(f"Key {key[:8]}... marked as rate limited for {retry_after}s")
    
    def _get_next_available_key(self) -> Optional[str]:
        """Get the next available API key using round-robin with rate limit check."""
        start_index = self.current_key_index
        
        for _ in range(len(self.api_keys)):
            key = self.api_keys[self.current_key_index]
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
            
            if self._is_key_available(key):
                return key
        
        logger.warning("All API keys are currently rate limited!")
        
        if self.rate_limited_until:
            min_wait = min(self.rate_limited_until.values()) - time.time()
            if min_wait > 0:
                logger.info(f"Shortest wait time: {int(min_wait)}s")
        
        return None
    
    def get_client(self) -> Optional[Groq]:
        """Get a Groq client with an available API key."""
        key = self._get_next_available_key()
        if key:
            return self.clients[key]
        return None
    
    def chat_completion(self, messages: list, temperature: float = 0.7, max_tokens: int = 4096):
        """
        Make a chat completion request with automatic key rotation.
        Tries all available keys before giving up.
        """
        attempts = 0
        max_attempts = len(self.api_keys) * 2
        
        while attempts < max_attempts:
            key = self._get_next_available_key()
            key_index = self.api_keys.index(key) + 1 if key else 0
            
            if not key:
                available_in = None
                if self.rate_limited_until:
                    min_time = min(self.rate_limited_until.values())
                    available_in = max(0, int(min_time - time.time()))
                
                if available_in and available_in <= 120:
                    logger.info(f"All keys rate limited. Waiting {available_in}s for key to become available...")
                    time.sleep(available_in + 1)
                    continue
                else:
                    raise RateLimitError(
                        message=f"All {len(self.api_keys)} API keys are rate limited. Please wait or add more keys.",
                        response=None,
                        body=None
                    )
            
            try:
                client = self.clients[key]
                logger.debug(f"Using API key #{key_index} ({key[:8]}...) for request")
                response = client.chat.completions.create(
                    messages=messages,
                    model=self.model,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                logger.debug(f"Request successful with key #{key_index}")
                return response
                
            except RateLimitError as e:
                error_message = str(e)
                retry_after = 60
                
                if "retry after" in error_message.lower():
                    import re
                    match = re.search(r'(\d+)s', error_message)
                    if match:
                        retry_after = int(match.group(1))
                
                self._mark_key_rate_limited(key, retry_after)
                logger.warning(f"Rate limit hit on key {key[:8]}..., switching to next key")
                attempts += 1
                continue
                
            except APIError as e:
                logger.error(f"API error with key {key[:8]}...: {e}")
                self._mark_key_rate_limited(key, 30)
                attempts += 1
                continue
                
            except Exception as e:
                logger.error(f"Unexpected error with key {key[:8]}...: {e}")
                attempts += 1
                continue
        
        raise Exception(f"Failed to complete request after {max_attempts} attempts with {len(self.api_keys)} keys")
    
    def get_status(self) -> dict:
        """Get current status of all API keys."""
        status = {
            "total_keys": len(self.api_keys),
            "available_keys": 0,
            "rate_limited_keys": 0,
            "keys": []
        }
        
        current_time = time.time()
        
        for i, key in enumerate(self.api_keys):
            key_status = {
                "index": i + 1,
                "key_preview": f"{key[:8]}...{key[-4:]}",
                "available": self._is_key_available(key)
            }
            
            if key in self.rate_limited_until:
                remaining = max(0, int(self.rate_limited_until[key] - current_time))
                key_status["rate_limited_for"] = f"{remaining}s"
                status["rate_limited_keys"] += 1
            else:
                status["available_keys"] += 1
            
            status["keys"].append(key_status)
        
        return status


groq_key_manager = GroqKeyManager()
