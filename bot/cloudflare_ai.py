import os
import logging
import time
import requests
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

class CloudflareAIError(Exception):
    """Base exception for Cloudflare AI errors."""
    pass

class CloudflareRateLimitError(CloudflareAIError):
    """Rate limit error for Cloudflare AI."""
    pass

class CloudflareAPIError(CloudflareAIError):
    """API error for Cloudflare AI."""
    pass

class CloudflareAIManager:
    """
    Manages Cloudflare Workers AI API with automatic rate limiting and retry.
    Replaces GroqKeyManager for Cloudflare AI integration.
    """
    
    def __init__(self):
        self.account_id = os.getenv('CLOUDFLARE_ACCOUNT_ID')
        self.api_token = os.getenv('CLOUDFLARE_API_TOKEN')
        self.model = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"
        self.rate_limited_until: float = 0
        self._validate_credentials()
    
    def _validate_credentials(self):
        """Validate that Cloudflare credentials are available."""
        if not self.account_id:
            raise ValueError("CLOUDFLARE_ACCOUNT_ID environment variable is required")
        if not self.api_token:
            raise ValueError("CLOUDFLARE_API_TOKEN environment variable is required")
        logger.info("Cloudflare AI credentials loaded successfully")
    
    def _get_api_url(self, model: Optional[str] = None) -> str:
        """Get the API URL for the specified model."""
        model_id = model or self.model
        return f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/ai/run/{model_id}"
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API request."""
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
    
    def _is_rate_limited(self) -> bool:
        """Check if currently rate limited."""
        if time.time() < self.rate_limited_until:
            remaining = int(self.rate_limited_until - time.time())
            logger.debug(f"Rate limited for {remaining}s more")
            return True
        return False
    
    def _mark_rate_limited(self, retry_after: int = 60):
        """Mark as rate limited for specified seconds."""
        self.rate_limited_until = time.time() + retry_after
        logger.warning(f"Marked as rate limited for {retry_after}s")
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        model: Optional[str] = None
    ) -> 'CloudflareResponse':
        """
        Make a chat completion request to Cloudflare Workers AI.
        Returns a response object compatible with Groq's response format.
        """
        if self._is_rate_limited():
            wait_time = max(0, int(self.rate_limited_until - time.time()))
            if wait_time <= 120:
                logger.info(f"Waiting {wait_time}s for rate limit to clear...")
                time.sleep(wait_time + 1)
            else:
                raise CloudflareRateLimitError(f"Rate limited. Please wait {wait_time}s")
        
        url = self._get_api_url(model)
        headers = self._get_headers()
        
        payload = {
            "messages": messages,
            "max_tokens": max_tokens
        }
        
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                logger.debug(f"Making Cloudflare AI request (attempt {attempt + 1})")
                response = requests.post(url, headers=headers, json=payload, timeout=120)
                
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    self._mark_rate_limited(retry_after)
                    if attempt < max_attempts - 1:
                        logger.warning(f"Rate limited, waiting {retry_after}s before retry")
                        time.sleep(retry_after)
                        continue
                    raise CloudflareRateLimitError(f"Rate limit exceeded. Retry after {retry_after}s")
                
                if response.status_code != 200:
                    error_msg = response.text
                    logger.error(f"Cloudflare API error: {response.status_code} - {error_msg}")
                    if attempt < max_attempts - 1:
                        time.sleep(2 ** attempt)
                        continue
                    raise CloudflareAPIError(f"API error: {response.status_code} - {error_msg}")
                
                result = response.json()
                
                if not result.get('success', False):
                    errors = result.get('errors', [])
                    error_msg = errors[0].get('message', 'Unknown error') if errors else 'Unknown error'
                    raise CloudflareAPIError(f"Request failed: {error_msg}")
                
                response_data = result.get('result', {}).get('response', '')
                
                if isinstance(response_data, list):
                    if len(response_data) > 0 and isinstance(response_data[0], dict):
                        response_text = response_data[0].get('content', '') or response_data[0].get('text', '')
                    else:
                        response_text = ' '.join(str(item) for item in response_data)
                elif isinstance(response_data, dict):
                    response_text = response_data.get('content', '') or response_data.get('text', '') or str(response_data)
                else:
                    response_text = str(response_data) if response_data else ''
                
                logger.debug(f"Request successful, response length: {len(response_text)}")
                
                return CloudflareResponse(response_text)
                
            except requests.exceptions.Timeout:
                logger.error(f"Request timeout on attempt {attempt + 1}")
                if attempt < max_attempts - 1:
                    continue
                raise CloudflareAPIError("Request timed out after multiple attempts")
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error: {e}")
                if attempt < max_attempts - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise CloudflareAPIError(f"Request failed: {e}")
        
        raise CloudflareAPIError(f"Failed after {max_attempts} attempts")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the Cloudflare AI client."""
        is_limited = self._is_rate_limited()
        remaining = max(0, int(self.rate_limited_until - time.time())) if is_limited else 0
        
        return {
            "provider": "cloudflare",
            "model": self.model,
            "account_id_preview": f"{self.account_id[:8]}..." if self.account_id else "Not set",
            "rate_limited": is_limited,
            "rate_limited_for": f"{remaining}s" if is_limited else None,
            "available": not is_limited
        }


class CloudflareResponse:
    """
    Response wrapper that mimics Groq's response format for compatibility.
    """
    
    def __init__(self, content: str):
        self.choices = [CloudflareChoice(content)]


class CloudflareChoice:
    """Choice wrapper for compatibility with Groq's format."""
    
    def __init__(self, content: str):
        self.message = CloudflareMessage(content)


class CloudflareMessage:
    """Message wrapper for compatibility with Groq's format."""
    
    def __init__(self, content: str):
        self.content = content


cloudflare_ai_manager = None

def get_cloudflare_ai_manager() -> CloudflareAIManager:
    """Get or create the Cloudflare AI manager singleton."""
    global cloudflare_ai_manager
    if cloudflare_ai_manager is None:
        cloudflare_ai_manager = CloudflareAIManager()
    return cloudflare_ai_manager
