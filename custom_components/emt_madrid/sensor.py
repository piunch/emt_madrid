"""Sensor platform for EMT Madrid integration."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .bicimad import BicimadEMT
from .buses import BusesEMT
from .const import (
    ATTR_BIKES,
    ATTR_DESTINATION,
    ATTR_DISTANCE,
    ATTR_END_TIME,
    ATTR_FREE_BASES,
    ATTR_LATITUDE,
    ATTR_LINE,
    ATTR_LONGITUDE,
    ATTR_MAX_FREQ,
    ATTR_MIN_FREQ,
    ATTR_NEXT_BUS,
    ATTR_ORIGIN,
    ATTR_START_TIME,
    ATTR_STATION_ADDRESS,
    ATTR_STATION_ID,
    ATTR_STATION_NAME,
    ATTR_STATION_NUMBER,
    ATTR_STOP_ADDRESS,
    ATTR_STOP_ID,
    ATTR_STOP_NAME,
    ATTRIBUTION,
    CONF_EMAIL,
    CONF_LINES,
    CONF_PASSWORD,
    CONF_STATION_ID,
    CONF_STOP_ID,
    CONF_SENSOR_TYPE,
    DEFAULT_BICIMAD_ICON,
    DEFAULT_BUS_ICON,
    DOMAIN,
    SENSOR_TYPE_BICIMAD,
    SENSOR_TYPE_BUS,
)

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=1)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up EMT Madrid sensors from a config entry."""
    data = entry.data
    sensor_type = data[CONF_SENSOR_TYPE]

    if sensor_type == SENSOR_TYPE_BUS:
        email = data[CONF_EMAIL]
        password = data[CONF_PASSWORD]
        stop_id = data[CONF_STOP_ID]
        lines = data.get(CONF_LINES, [])

        buses_emt = BusesEMT(email, password, stop_id)

        await hass.async_add_executor_job(buses_emt.authenticate)
        await hass.async_add_executor_job(buses_emt.update_stop_info, stop_id)

        stop_info = buses_emt.get_stop_info()
        if not lines:
            lines = list(stop_info["lines"].keys())

        entities: list[EMTBusSensor] = []
        for line in lines:
            if line in stop_info["lines"]:
                await hass.async_add_executor_job(buses_emt.update_arrival_times, stop_id)
                entities.append(
                    EMTBusSensor(
                        buses_emt,
                        entry.entry_id,
                        stop_id,
                        line,
                        stop_info.get("bus_stop_name", ""),
                    )
                )
            else:
                _LOGGER.error(
                    "Sensor setup failed. Line %s not serviced at stop %s", line, stop_id
                )

        async_add_entities(entities)

    elif sensor_type == SENSOR_TYPE_BICIMAD:
        email = data[CONF_EMAIL]
        password = data[CONF_PASSWORD]
        station_id = data[CONF_STATION_ID]

        bicimad_emt = BicimadEMT(email, password, station_id)

        await hass.async_add_executor_job(bicimad_emt.authenticate)
        await hass.async_add_executor_job(bicimad_emt.update_station_info, station_id)

        station_info = bicimad_emt.get_station_info()

        async_add_entities(
            [
                EMTBicimadSensor(
                    bicimad_emt,
                    entry.entry_id,
                    station_id,
                    station_info.get("station_name", ""),
                )
            ]
        )


class EMTBusSensor(SensorEntity):
    """Implementation of an EMT-Madrid bus line sensor."""

    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_icon = DEFAULT_BUS_ICON

    def __init__(
        self,
        buses_emt: BusesEMT,
        entry_id: str,
        stop_id: int,
        line: str,
        stop_name: str,
    ) -> None:
        """Initialize the sensor."""
        self._buses_emt = buses_emt
        self._stop_id = stop_id
        self._bus_line = line
        self._stop_name = stop_name

        self._attr_name = f"Bus {line} - {stop_name}"
        self._attr_unique_id = f"{DOMAIN}_bus_{entry_id}_{stop_id}_{line}"

    @property
    def native_value(self) -> int | None:
        """Return the state of the sensor."""
        arrival_time = self._buses_emt.get_arrival_time(self._bus_line)
        return arrival_time[0]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the device state attributes."""
        arrival_time = self._buses_emt.get_arrival_time(self._bus_line)
        stop_info = self._buses_emt.get_stop_info()
        line_info = self._buses_emt.get_line_info(self._bus_line)
        coordinates = stop_info.get("bus_stop_coordinates")
        latitude = coordinates[1] if coordinates and len(coordinates) > 1 else None
        longitude = coordinates[0] if coordinates else None

        return {
            ATTR_NEXT_BUS: arrival_time[1],
            ATTR_LINE: self._bus_line,
            ATTR_DISTANCE: line_info.get("distance", [None])[0],
            ATTR_DESTINATION: line_info.get("destination"),
            ATTR_ORIGIN: line_info.get("origin"),
            ATTR_START_TIME: line_info.get("start_time"),
            ATTR_END_TIME: line_info.get("end_time"),
            ATTR_MAX_FREQ: line_info.get("max_freq"),
            ATTR_MIN_FREQ: line_info.get("min_freq"),
            ATTR_STOP_ID: self._stop_id,
            ATTR_STOP_NAME: stop_info.get("bus_stop_name"),
            ATTR_STOP_ADDRESS: stop_info.get("bus_stop_address"),
            ATTR_LATITUDE: latitude,
            ATTR_LONGITUDE: longitude,
            ATTR_ATTRIBUTION: ATTRIBUTION,
        }

    async def async_update(self) -> None:
        """Fetch new state data for the sensor."""
        await self.hass.async_add_executor_job(
            self._buses_emt.update_arrival_times, self._stop_id
        )


class EMTBicimadSensor(SensorEntity):
    """Implementation of an EMT-Madrid BiciMad station sensor."""

    _attr_icon = DEFAULT_BICIMAD_ICON
    _attr_native_unit_of_measurement = "bikes"

    def __init__(
        self,
        bicimad_emt: BicimadEMT,
        entry_id: str,
        station_id: int,
        station_name: str,
    ) -> None:
        """Initialize the sensor."""
        self._bicimad_emt = bicimad_emt
        self._station_id = station_id
        self._station_name = station_name

        self._attr_name = f"Bicimad {station_name}"
        self._attr_unique_id = f"{DOMAIN}_bicimad_{entry_id}_{station_id}"

    @property
    def native_value(self) -> int | None:
        """Return the number of available bikes."""
        return self._bicimad_emt.get_docked_bikes()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the device state attributes."""
        station_info = self._bicimad_emt.get_station_info()
        coordinates = station_info.get("station_coordinates")
        latitude = coordinates[1] if coordinates and len(coordinates) > 1 else None
        longitude = coordinates[0] if coordinates else None

        return {
            ATTR_STATION_ID: self._station_id,
            ATTR_STATION_NUMBER: station_info.get("station_number"),
            ATTR_STATION_NAME: station_info.get("station_name"),
            ATTR_LATITUDE: latitude,
            ATTR_LONGITUDE: longitude,
            ATTR_STATION_ADDRESS: station_info.get("station_address"),
            ATTR_FREE_BASES: station_info.get("free_bases"),
            ATTR_BIKES: self._bicimad_emt.get_docked_bikes(),
            ATTR_ATTRIBUTION: ATTRIBUTION,
        }

    async def async_update(self) -> None:
        """Fetch new state data for the sensor."""
        await self.hass.async_add_executor_job(
            self._bicimad_emt.update_station_info, self._station_id
        )
