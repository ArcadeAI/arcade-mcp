import json
import os
import time
from typing import Any, ClassVar, Dict, Optional
from urllib.parse import quote

import requests


class BrightDataClient:
    """Engine for interacting with Bright Data API with connection management."""
    
    _clients: ClassVar[dict[str, "BrightDataClient"]] = {}

    def __init__(self, api_key: str, zone: str = "web_unlocker1") -> None:
        """
        Initialize with API token and default zone.
        Args:
            api_key (str): Your Bright Data API token
            zone (str): Bright Data zone name
        """
        self.api_key = api_key
        self.headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}
        self.zone = zone
        self.endpoint = "https://api.brightdata.com/request"

    @classmethod
    def create_client(cls, api_key: str, zone: str = "web_unlocker1") -> "BrightDataClient":
        """Create or get cached client instance using API key only."""
        if api_key not in cls._clients:
            cls._clients[api_key] = cls(api_key, zone)
        
        # Update zone for this request (user controls zone per request)
        client = cls._clients[api_key] 
        client.zone = zone
        return client

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the client cache."""
        cls._clients.clear()

    def make_request(self, payload: Dict) -> str:
        """
        Make a request to Bright Data API.
        Args:
            payload (Dict): Request payload
        Returns:
            str: Response text
        """
        response = requests.post(self.endpoint, headers=self.headers, data=json.dumps(payload))

        if response.status_code != 200:
            raise Exception(f"Failed to scrape: {response.status_code} - {response.text}")

        return response.text

    @staticmethod
    def encode_query(query: str) -> str:
        """URL encode a search query."""
        return quote(query)