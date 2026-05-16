"""Support for EMT Madrid API."""

import json
import logging

BASE_URL = "https://openapi.emtmadrid.es/"
ENDPOINT_LOGIN = "v3/mobilitylabs/user/login/"

_LOGGER = logging.getLogger(__name__)


class APIEMT:
    """A class representing an API client for EMT (Empresa Municipal de Transportes) services."""

    def __init__(self, user: str, password: str) -> None:
        """Initialize an instance of the APIEMT class."""
        self._user = user
        self._password = password
        self._token: str | None = None

    def authenticate(self) -> str | None:
        """Authenticate the user using the provided credentials."""
        headers = {"email": self._user, "password": self._password}
        url = f"{BASE_URL}{ENDPOINT_LOGIN}"
        response = self._make_request(url, headers=headers, method="GET")
        self._token = self._extract_token(response)
        return self._token

    def get_token(self) -> str | None:
        """Return the current access token."""
        return self._token

    def get_all_bicimad_stations(self) -> list[dict] | None:
        """Fetch all available BiciMad stations."""
        url = f"{BASE_URL}v3/transport/bicimad/stations/"
        headers = {"accessToken": self._token}
        if self._token is None:
            _LOGGER.warning("Cannot fetch stations: not authenticated")
            return None
        try:
            response = self._make_request(url, headers=headers, method="GET")
            if response.get("code") in ("00", "01"):
                return response.get("data", [])
            _LOGGER.warning(
                "Failed to fetch BiciMad stations list (code: %s)",
                response.get("code"),
            )
            return None
        except Exception:
            _LOGGER.exception("Error fetching BiciMad stations list")
            return None

    def _extract_token(self, response: dict) -> str | None:
        """Extract the access token from the API response."""
        try:
            if response.get("code") != "01":
                _LOGGER.error("Invalid email or password")
                return None
            return response["data"][0]["accessToken"]
        except (KeyError, IndexError):
            _LOGGER.exception("Unable to get token from the API")
            return None

    def _make_request(
        self, url: str, headers: dict | None = None, data: dict | None = None, method: str = "POST"
    ) -> dict:
        """Send an HTTP request to the specified URL."""
        import requests

        if method not in ("POST", "GET"):
            raise ValueError(f"Invalid HTTP method: {method}")
        kwargs = {"url": url, "headers": headers, "timeout": 10}
        if method == "POST":
            kwargs["data"] = json.dumps(data)
        try:
            response = requests.request(method, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            raise requests.HTTPError(f"Error while connecting to EMT API: {e}") from e
