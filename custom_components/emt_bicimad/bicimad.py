from emt_madrid import APIEMT
from emt_madrid import BASE_URL, _LOGGER


ENDPOINT_BICIMAD_STATIONS = "v3/transport/bicimad/stations/"

class BicimadEMT(APIEMT):

    def __init__(self, user, password, station_id) -> None:
        super().__init__(user, password)
        self._station_info = {
            "station_id": station_id,
            "station_number": None,
            "station_name": None,
            "station_coordinates": None,
            "station_address": None,
            "free_bases": None,
            "bikes": None
        }
    
    def update_station_info(self, station_id):
        """Update all the information from the bicimad station."""
        url = f"{BASE_URL}{ENDPOINT_BICIMAD_STATIONS}{station_id}"
        headers = {"accessToken": self._token}
        data = {"idStation": station_id}
        if self._token != "Invalid token":
            response = self._make_request(url, headers=headers, data=data, method="GET")
            self._parse_station_info(response)

    def retry_update_station_info(self):
        """Update the information from the Bicimad station."""
        station_id = self._station_info["station_id"]
        url = f"{BASE_URL}{ENDPOINT_BICIMAD_STATIONS}{station_id}"
        headers = {"accessToken": self._token}
        data = {"idStation": station_id}
        if self._token != "Invalid token":
            response = self._make_request(url, headers=headers, data=data, method="GET")
            return response

    def get_docked_bikes(self):
        """Retrieve the number of docked bikes on the Bicimad station."""
        try:
            docked_bikes = self._station_info["docked_bikes"]
        except KeyError:
            return None
        return docked_bikes

    def get_free_bases(self):
        """Retrieve the number of free bases on the Bicimad station."""
        try:
            free_bases = self._station_info["free_bases"]
        except KeyError:
            return None
        return free_bases

    def get_station_info(self):
        """Retrieve all the information from the Bicimad station."""
        return self._station_info

    def _parse_station_info(self, response):
        """Parse the station info from the API response."""
        try:
            response_code = response.get("code")
            if response_code == "90":
                _LOGGER.warning("Bicimad station disabled or does not exist")
            elif response_code == "80":
                _LOGGER.warning("Invalid token")
            elif response_code == "98":
                _LOGGER.warning("API limit reached")
            elif response_code == "81":
                response = self.retry_update_station_info()

                station_info = response["data"][0]
                self._station_info.update(
                    {
                        "station_number": station_info.get('number'),
                        "station_name": station_info.get('number'),
                        "station_coordinates": station_info.get('geometry').get('coordinates'),
                        "station_address": station_info.get('address'),
                        "docked_bikes": station_info.get('dock_bikes'),
                        "free_bases": station_info.get('free_bases'),
                    }
                )
            else:
                station_info = response["data"][0]
                self._station_info.update(
                    {
                        "station_number": station_info.get('number'),
                        "station_name": station_info.get('number'),
                        "station_coordinates": station_info.get('number'),
                        "station_address": station_info.get('address'),
                        "docked_bikes": station_info.get('dock_bikes'),
                        "free_bases": station_info.get('free_bases'),
                    }
                )
        except (KeyError, IndexError) as e:
            raise ValueError("Unable to get Bicimad station information") from e
