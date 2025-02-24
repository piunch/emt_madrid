from emt_madrid import APIEMT
from emt_madrid import BASE_URL, _LOGGER


ENDPOINT_ARRIVAL_TIME = "v3/transport/busemtmad/stops/"
ENDPOINT_STOP_INFO = "v3/transport/busemtmad/stops/"
ENDPOINT_STOPS_ARROUND_STOP = "v3/transport/busemtmad/stops/arroundstop/"


class BusesEMT(APIEMT):

    def __init__(self, user, password, stop_id) -> None:
        super().__init__(user, password)
        self._stop_info = {
            "bus_stop_id": stop_id,
            "bus_stop_name": None,
            "bus_stop_coordinates": None,
            "bus_stop_address": None,
            "lines": {},
        }

    
    def update_stop_info(self, stop_id):
        """Update all the lines and information from the bus stop."""
        url = f"{BASE_URL}{ENDPOINT_STOP_INFO}{stop_id}/detail/"
        headers = {"accessToken": self._token}
        data = {"idStop": stop_id}
        if self._token != "Invalid token":
            response = self._make_request(url, headers=headers, data=data, method="GET")
            self._parse_stop_info(response)

    def retry_update_stop_info(self):
        """Update all the lines and information from the bus stop."""
        stop_id = self._stop_info["bus_stop_id"]
        url = f"{BASE_URL}{ENDPOINT_STOPS_ARROUND_STOP}{stop_id}/0/"
        headers = {"accessToken": self._token}
        data = {"idStop": stop_id}
        if self._token != "Invalid token":
            response = self._make_request(url, headers=headers, data=data, method="GET")
            return response

    def get_stop_info(
        self,
    ):
        """Retrieve all the information from the bus stop."""
        return self._stop_info

    def _parse_stop_info(self, response):
        """Parse the stop info from the API response."""
        try:
            response_code = response.get("code")
            if response_code == "90":
                _LOGGER.warning("Bus stop disabled or does not exist")
            elif response_code == "80":
                _LOGGER.warning("Invalid token")
            elif response_code == "98":
                _LOGGER.warning("API limit reached")
            elif response_code == "81":
                response = self.retry_update_stop_info()

                stop_info = response["data"][0]
                self._stop_info.update(
                    {
                        "bus_stop_name": stop_info["stopName"],
                        "bus_stop_coordinates": stop_info["geometry"]["coordinates"],
                        "bus_stop_address": stop_info["address"],
                        "lines": self._parse_lines(stop_info["lines"], "basic"),
                    }
                )
            else:
                stop_info = response["data"][0]["stops"][0]
                self._stop_info.update(
                    {
                        "bus_stop_name": stop_info["name"],
                        "bus_stop_coordinates": stop_info["geometry"]["coordinates"],
                        "bus_stop_address": stop_info["postalAddress"],
                        "lines": self._parse_lines(stop_info["dataLine"], "full"),
                    }
                )
        except (KeyError, IndexError) as e:
            raise ValueError("Unable to get bus stop information") from e

    def _parse_lines(self, lines, mode):
        """Parse the line info from the API response."""
        if mode == "full":
            line_info = {}
            for line in lines:
                line_number = line["label"]
                line_info[line_number] = {
                    "destination": line["headerA"]
                    if line["direction"] == "A"
                    else line["headerB"],
                    "origin": line["headerA"]
                    if line["direction"] == "B"
                    else line["headerB"],
                    "max_freq": int(line["maxFreq"]),
                    "min_freq": int(line["minFreq"]),
                    "start_time": line["startTime"],
                    "end_time": line["stopTime"],
                    "day_type": line["dayType"],
                    "distance": [],
                    "arrivals": [],
                }
        elif mode == "basic":
            line_info = {}
            for line in lines:
                line_number = line["label"]
                line_info[line_number] = {
                    "destination": line["nameA"]
                    if line["to"] == "A"
                    else line["nameB"],
                    "origin": line["nameA"] if line["to"] == "B" else line["nameB"],
                    "distance": [],
                    "arrivals": [],
                }
        return line_info

    def update_arrival_times(self, stop):
        """Update the arrival times for the specified bus stop and line."""
        url = f"{BASE_URL}{ENDPOINT_ARRIVAL_TIME}{stop}/arrives/"
        headers = {"accessToken": self._token}
        data = {"stopId": stop, "Text_EstimationsRequired_YN": "Y"}
        if self._token != "Invalid token":
            response = self._make_request(
                url, headers=headers, data=data, method="POST"
            )
            self._parse_arrivals(response)

    def get_arrival_time(self, line):
        """Retrieve arrival times in minutes for the specified bus line."""
        try:
            arrivals = self._stop_info["lines"][line].get("arrivals")
        except KeyError:
            return [None, None]
        while len(arrivals) < 2:
            arrivals.append(None)
        return arrivals

    def get_line_info(self, line):
        """Retrieve the information for a specific line."""
        lines = self._stop_info["lines"]
        if line in lines:
            line_info = lines.get(line)
            if "distance" in line_info and len(line_info["distance"]) == 0:
                line_info["distance"].append(None)
            return line_info

        _LOGGER.warning(f"The bus line {line} does not exist at this stop.")
        line_info = {
            "destination": None,
            "origin": None,
            "max_freq": None,
            "min_freq": None,
            "start_time": None,
            "end_time": None,
            "day_type": None,
            "distance": [None],
            "arrivals": [None, None],
        }
        return line_info

    def _parse_arrivals(self, response):
        """Parse the arrival times and distance from the API response."""
        try:
            if response.get("code") == "80":
                _LOGGER.warning("Bus Stop disabled or does not exist")
            else:
                for line_info in self._stop_info["lines"].values():
                    line_info["arrivals"] = []
                    line_info["distance"] = []
                arrivals = response["data"][0].get("Arrive", [])
                for arrival in arrivals:
                    line = arrival.get("line")
                    line_info = self._stop_info["lines"].get(line)
                    arrival_time = min(
                        math.trunc(arrival.get("estimateArrive") / 60), 45
                    )
                    if line_info:
                        line_info["arrivals"].append(arrival_time)
                        line_info["distance"].append(arrival.get("DistanceBus"))
        except (KeyError, IndexError) as e:
            raise ValueError("Unable to get the arrival times from the API") from e
        except TypeError as e:
            _LOGGER.error(f"ERROR {e} --> RESPONSE: {response}")