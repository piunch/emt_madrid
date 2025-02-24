"""Support for EMT Madrid API."""

import json
import logging
import math

import requests

BASE_URL = "https://openapi.emtmadrid.es/"
ENDPOINT_LOGIN = "v3/mobilitylabs/user/login/"

_LOGGER = logging.getLogger(__name__)


class APIEMT:
    """A class representing an API client for EMT (Empresa Municipal de Transportes) services.

    This class provides methods to authenticate with the EMT API.
    """

    def __init__(self, user, password) -> None:
        """Initialize an instance of the APIEMT class."""
        self._user = user
        self._password = password
        self._token = None

    def authenticate(self):
        """Authenticate the user using the provided credentials."""
        headers = {"email": self._user, "password": self._password}
        url = f"{BASE_URL}{ENDPOINT_LOGIN}"
        response = self._make_request(url, headers=headers, method="GET")
        self._token = self._extract_token(response)

    def _extract_token(self, response):
        """Extract the access token from the API response."""
        try:
            if response.get("code") != "01":
                _LOGGER.error("Invalid email or password")
                return "Invalid token"
            return response["data"][0]["accessToken"]
        except (KeyError, IndexError) as e:
            raise ValueError("Unable to get token from the API") from e


    def _make_request(self, url: str, headers=None, data=None, method="POST"):
        """Send an HTTP request to the specified URL."""
        try:
            if method not in ["POST", "GET"]:
                raise ValueError(f"Invalid HTTP method: {method}")
            kwargs = {"url": url, "headers": headers, "timeout": 10}
            if method == "POST":
                kwargs["data"] = json.dumps(data)
            response = requests.request(method, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            raise requests.HTTPError(f"Error while connecting to EMT API: {e}") from e
