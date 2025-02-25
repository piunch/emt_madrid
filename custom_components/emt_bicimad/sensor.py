"""Support for EMT Madrid (Empresa Municipal de Transportes de Madrid) to get next departures."""

import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    CONF_EMAIL,
    CONF_ICON,
    CONF_PASSWORD,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from ..emt_bicimad.bicimad import BicimadEMT

_LOGGER = logging.getLogger(__name__)


CONF_BICIMAD_STATION_ID = "station_id"

DEFAULT_BICIMAD_ICON = "mdi:bike"

ATTR_BICIMAD_STATION_ID = "station_id"
ATTR_BICIMAD_STATION_NUMBER = "station_number"
ATTR_BICIMAD_STATION_NAME = "station_name"
ATTR_BICIMAD_STATION_COORDINATES = "station_coordinates"
ATTR_BICIMAD_STATION_ADDRESS = "station_address"
ATTR_BICIMAD_STATION_FREE_BASES = "free_bases"
ATTR_BICIMAD_STATION_BIKES = "bikes"

ATTRIBUTION = "Data provided by EMT Madrid MobilityLabs"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_EMAIL): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_BICIMAD_STATION_ID): cv.positive_int,
        vol.Optional(CONF_ICON, default=DEFAULT_BICIMAD_ICON): cv.string,
    }
)


class BicimadStationSensor(Entity):
    """Implementation of an EMT-Madrid bicimad station sensor."""

    def __init__(self, bicimad_emt: BicimadEMT, station_id, name, icon) -> None:
        """Initialize the sensor."""
        self._state = None
        self._bicimad_emt = bicimad_emt
        self._station_id = station_id
        self._icon = icon
        self._name = name

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self) -> int:
        """Return the state of the sensor (Number of bikes on the Bicimad station)."""
        docked_bikes = self._bicimad_emt.get_docked_bikes(self._station_id)
        return docked_bikes

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return 'bikes'

    @property
    def icon(self) -> str:
        """Return sensor specific icon."""
        return self._icon

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the device state attributes."""
        docked_bikes = self._bicimad_emt.get_docked_bikes()
        station_info = self._bicimad_emt.get_station_info()

        return {
            ATTR_BICIMAD_STATION_ID: self._station_id,
            ATTR_BICIMAD_STATION_NUMBER: station_info.get("station_number"),
            ATTR_BICIMAD_STATION_NAME: station_info.get("station_name"),
            ATTR_BICIMAD_STATION_COORDINATES: station_info.get("station_coordinates"),
            ATTR_BICIMAD_STATION_ADDRESS: station_info.get("station_address"),
            ATTR_BICIMAD_STATION_FREE_BASES: station_info.get("free_bases"),
            ATTR_BICIMAD_STATION_BIKES: docked_bikes,
            ATTR_ATTRIBUTION: ATTRIBUTION,
        }

    def update(self) -> None:
        """Fetch new state data for the sensor."""
        self._bicimad_emt.update_station_info(self._station_id)



def get_bicimad_emt_instance(config: ConfigType) -> BicimadEMT:
    """Create an instance of the BicimadEMT class with the provided configuration."""
    email = config.get(CONF_EMAIL)
    password = config.get(CONF_PASSWORD)
    station_id = config.get(CONF_BICIMAD_STATION_ID)
    bicimad_emt = BicimadEMT(email, password, station_id)
    bicimad_emt.authenticate()
    bicimad_emt.update_station_info(station_id)
    return bicimad_emt

def create_bicimad_station_sensor(
    bicimad_emt: BicimadEMT, station_id, name, icon, config: ConfigType
) -> BicimadStationSensor:
    """Create a BicimadStationSensor instance with the provided BicimadEMT instance and configuration."""
    bicimad_emt.update_station_info(station_id)
    return BicimadStationSensor(bicimad_emt, station_id, name, icon)


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the sensor platform."""
    bicimad_emt = get_bicimad_emt_instance(config)
    station_id = config.get(CONF_BICIMAD_STATION_ID)
    station_info = bicimad_emt.get_station_info()
    bicimad_station_sensors = []

    name = f"Bicimad - {station_info['station_name']}"
    icon = config.get(CONF_ICON)
    bicimad_station_sensors.append(
        create_bicimad_station_sensor(bicimad_emt, station_id, name, icon, config)
    )
       
    add_entities(bicimad_station_sensors)
