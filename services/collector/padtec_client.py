"""
Padtec API Client
Cliente para comunicação com a API Padtec NMS
"""
import logging
from typing import List, Optional, Dict, Any
import httpx
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)


class PadtecClient:
    """Client for Padtec NMS API"""

    def __init__(self, base_url: str, token: str, timeout: int = 30):
        """
        Initialize Padtec client
        
        Args:
            base_url: Base URL of Padtec API
            token: Bearer token for authentication
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.timeout = timeout
        self.headers = {
            "Authorization": f"Token {token}",
            "Content-Type": "application/json"
        }

    def update_credentials(
        self,
        base_url: Optional[str] = None,
        token: Optional[str] = None
    ):
        """Update API base URL and/or token at runtime."""
        if base_url:
            self.base_url = base_url.rstrip('/')
        if token is not None:
            self.token = token
        if self.token:
            self.headers["Authorization"] = f"Token {self.token}"
        else:
            self.headers.pop("Authorization", None)

    async def _request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict] = None,
        retries: int = 3
    ) -> Dict[str, Any]:
        """
        Make HTTP request with retry logic and CSRF handling
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            params: Query parameters
            retries: Number of retry attempts
            
        Returns:
            Response data as dictionary
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        # State for CSRF handling
        cookies = None
        csrf_headers = {}
        
        for attempt in range(retries):
            try:
                # Prepare headers
                request_headers = self.headers.copy()
                request_headers.update(csrf_headers)

                async with httpx.AsyncClient(timeout=self.timeout, cookies=cookies) as client:
                    response = await client.request(
                        method=method,
                        url=url,
                        headers=request_headers,
                        params=params
                    )
                    
                    # Check for CSRF error (403 with "csrf" in body)
                    if response.status_code == 403 and "csrf" in response.text.lower():
                        if attempt < retries - 1:
                            logger.warning("CSRF token missing or invalid, attempting to refresh...")
                            
                            try:
                                # Try to get CSRF token from base URL
                                csrf_resp = await client.get(f"{self.base_url}/", headers=self.headers)
                                
                                # Extract CSRF token
                                csrf_token = None
                                
                                # From cookies
                                for cookie in client.cookies:
                                    if 'csrf' in cookie.name.lower():
                                        csrf_token = cookie.value
                                        break
                                
                                # From headers
                                if not csrf_token:
                                    csrf_token = csrf_resp.headers.get('X-CSRF-Token') or \
                                                 csrf_resp.headers.get('CSRF-Token')
                                
                                if csrf_token:
                                    logger.info("CSRF token obtained")
                                    csrf_headers['X-CSRF-Token'] = csrf_token
                                    csrf_headers['X-Requested-With'] = 'XMLHttpRequest'
                                    cookies = client.cookies # Save cookies for next attempt
                                    continue # Retry immediately with new token
                                else:
                                    logger.error("Failed to obtain CSRF token")
                            except Exception as e:
                                logger.error(f"Error refreshing CSRF token: {e}")
                    
                    response.raise_for_status()
                    return response.json()

            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500 and attempt < retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(
                        f"Server error {e.response.status_code}, retrying in {wait_time}s (attempt {attempt + 1}/{retries})"
                    )
                    await asyncio.sleep(wait_time)
                    continue
                raise
            except httpx.RequestError as e:
                if attempt < retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"Request error: {e}, retrying in {wait_time}s (attempt {attempt + 1}/{retries})"
                    )
                    await asyncio.sleep(wait_time)
                    continue
                raise
        
        raise Exception("Max retries exceeded")

    async def get_cards(self) -> List[Dict[str, Any]]:
        """
        Get all cards from Padtec Smart API
        
        Uses: /api/v1/inventory/state (Smart API documented endpoint)
        
        Returns:
            List of card dictionaries
        """
        all_cards = []
        page = 0
        size = 100  # Fetch 100 cards per page
        
        try:
            while True:
                # Try Smart API endpoint first (documented)
                params = {"page": page, "size": size}
                response = await self._request("GET", "/v1/inventory/state", params=params)
                
                current_batch = []
                
                # Handle different response formats
                if isinstance(response, dict):
                    if "data" in response:
                        current_batch = response["data"]
                    elif "content" in response:  # Paginated response
                        current_batch = response["content"]
                    elif "items" in response:
                        current_batch = response["items"]
                    elif "cards" in response:
                        current_batch = response["cards"]
                elif isinstance(response, list):
                    current_batch = response
                    
                if not current_batch:
                    break
                    
                all_cards.extend(current_batch)
                
                # If we got fewer items than requested, we've reached the end
                if len(current_batch) < size:
                    break
                    
                # If response is a list (not paginated wrapper), assume no pagination or single page
                if isinstance(response, list):
                    break
                    
                page += 1
                
            return all_cards

        except Exception as e:
            logger.warning(f"Error fetching cards from Smart API, trying legacy endpoint: {e}")
            # Fallback to legacy endpoint (usually not paginated or different structure)
            try:
                response = await self._request("GET", "/cards")
                if isinstance(response, dict):
                    if "data" in response:
                        return response["data"]
                    elif "cards" in response:
                        return response["cards"]
                if isinstance(response, list):
                    return response
            except Exception as e2:
                logger.error(f"Error fetching cards from legacy endpoint: {e2}")
            return []

    async def get_measurements(
        self, 
        card_serial: Optional[str] = None,
        limit: int = 1000,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get measurements from Padtec Smart API
        
        Uses: /api/v1/measures/state (Smart API documented endpoint)
        Note: Measures are collected with 30-second interval and normalized
        
        Args:
            card_serial: Optional card serial to filter
            limit: Maximum number of results (maps to 'size' parameter)
            offset: Offset for pagination (maps to 'page' parameter)
            
        Returns:
            List of measurement dictionaries
        """
        try:
            # Smart API uses 'page' and 'size' instead of 'offset' and 'limit'
            page = offset // limit if limit > 0 else 0
            params = {"size": limit, "page": page}
            if card_serial:
                params["cardSerial"] = card_serial
            
            # Try Smart API endpoint first (documented)
            response = await self._request("GET", "/v1/measures/state", params=params)
            
            # Handle different response formats
            if isinstance(response, dict):
                if "data" in response:
                    return response["data"]
                elif "content" in response:  # Paginated response
                    return response["content"]
                elif "measurements" in response:
                    return response["measurements"]
                elif isinstance(response.get("items"), list):
                    return response["items"]
            
            if isinstance(response, list):
                return response
            
            logger.warning(f"Unexpected response format: {type(response)}")
            return []
        except Exception as e:
            logger.warning(f"Error fetching measurements from Smart API, trying legacy endpoint: {e}")
            # Fallback to legacy endpoint
            try:
                params = {"limit": limit, "offset": offset}
                if card_serial:
                    params["cardSerial"] = card_serial
                response = await self._request("GET", "/measurements", params=params)
                if isinstance(response, dict):
                    if "data" in response:
                        return response["data"]
                    elif "measurements" in response:
                        return response["measurements"]
                if isinstance(response, list):
                    return response
            except Exception as e2:
                logger.error(f"Error fetching measurements from legacy endpoint: {e2}")
            return []

    async def get_alarms(
        self,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        card_serial: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get alarms from Padtec Smart API
        
        Uses: /api/v1/alarm/state (Smart API documented endpoint)
        
        Args:
            status: Filter by alarm status
            severity: Filter by severity
            card_serial: Filter by card serial
            
        Returns:
            List of alarm dictionaries
        """
        try:
            params = {}
            if status:
                params["status"] = status
            if severity:
                params["severity"] = severity
            if card_serial:
                params["cardSerial"] = card_serial
            
            # Try Smart API endpoint first (documented)
            response = await self._request("GET", "/v1/alarm/state", params=params)
            
            # Handle different response formats
            if isinstance(response, dict):
                if "data" in response:
                    return response["data"]
                elif "content" in response:  # Paginated response
                    return response["content"]
                elif "alarms" in response:
                    return response["alarms"]
                elif isinstance(response.get("items"), list):
                    return response["items"]
            
            if isinstance(response, list):
                return response
            
            logger.warning(f"Unexpected response format: {type(response)}")
            return []
        except Exception as e:
            logger.warning(f"Error fetching alarms from Smart API, trying legacy endpoint: {e}")
            # Fallback to legacy endpoint
            try:
                params = {}
                if status:
                    params["status"] = status
                if severity:
                    params["severity"] = severity
                if card_serial:
                    params["cardSerial"] = card_serial
                response = await self._request("GET", "/alarms", params=params)
                if isinstance(response, dict):
                    if "data" in response:
                        return response["data"]
                    elif "alarms" in response:
                        return response["alarms"]
                if isinstance(response, list):
                    return response
            except Exception as e2:
                logger.error(f"Error fetching alarms from legacy endpoint: {e2}")
            return []




