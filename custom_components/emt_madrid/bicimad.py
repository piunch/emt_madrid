"""BiciMad-related API client for EMT Madrid."""

from .emt_madrid import BASE_URL, APIEMT, _LOGGER

ENDPOINT_BICIMAD_STATIONS = "v3/transport/bicimad/stations/"


class BicimadEMT(APIEMT):
    """API client for BiciMad station information."""

    def __init__(self, user: str, password: str, station_id: int) -> None:
        """Initialize the BicimadEMT instance."""
        super().__init__(user, password)
        self._station_info: dict = {
            "station_id": station_id,
            "station_number": None,
            "station_name": None,
            "station_coordinates": None,
            "station_address": None,
            "free_bases": None,
            "docked_bikes": None,
        }

    def update_station_info(self, station_id: int) -> None:
        """Update all the information from the BiciMad station."""
        url = f"{BASE_URL}{ENDPOINT_BICIMAD_STATIONS}{station_id}"
        headers = {"accessToken": self._token}
        data = {"idStation": station_id}
        if self._token is not None:
            response = self._make_request(url, headers=headers, data=data, method="GET")
            self._parse_station_info(response)

    def retry_update_station_info(self) -> dict | None:
        """Retry updating the information from the BiciMad station."""
        station_id = self._station_info["station_id"]
        url = f"{BASE_URL}{ENDPOINT_BICIMAD_STATIONS}{station_id}"
        headers = {"accessToken": self._token}
        data = {"idStation": station_id}
        if self._token is not None:
            response = self._make_request(url, headers=headers, data=data, method="GET")
            return response
        return None

    def get_docked_bikes(self) -> int | None:
        """Retrieve the number of docked bikes on the BiciMad station."""
        try:
            return self._station_info["docked_bikes"]
        except KeyError:
            return None

    def get_free_bases(self) -> int | None:
        """Retrieve the number of free bases on the BiciMad station."""
        try:
            return self._station_info["free_bases"]
        except KeyError:
            return None

    def get_station_info(self) -> dict:
        """Retrieve all the information from the BiciMad station."""
        return self._station_info

    def _parse_station_info(self, response: dict) -> None:
        """Parse the station info from the API response."""
        try:
            response_code = response.get("code")
            if response_code == "90":
                _LOGGER.warning("BiciMad station disabled or does not exist")
            elif response_code == "80":
                _LOGGER.warning("Invalid token")
            elif response_code == "98":
                _LOGGER.warning("API limit reached")
            elif response_code == "81":
                retry_response = self.retry_update_station_info()
                if retry_response is None:
                    return

                station_info = retry_response["data"][0]
                self._station_info.update(
                    {
                        "station_number": station_info.get("number"),
                        "station_name": station_info.get("name"),
                        "station_coordinates": station_info.get("geometry", {}).get("coordinates"),
                        "station_address": station_info.get("address"),
                        "docked_bikes": station_info.get("dock_bikes"),
                        "free_bases": station_info.get("free_bases"),
                    }
                )
            else:
                station_info = response["data"][0]
                self._station_info.update(
                    {
                        "station_number": station_info.get("number"),
                        "station_name": station_info.get("name"),
                        "station_coordinates": station_info.get("geometry", {}).get("coordinates"),
                        "station_address": station_info.get("address"),
                        "docked_bikes": station_info.get("dock_bikes"),
                        "free_bases": station_info.get("free_bases"),
                    }
                )
        except (KeyError, IndexError) as e:
            raise ValueError("Unable to get Bicimad station information") from e
