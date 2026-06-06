"""Tests for the EMT Madrid integration."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.emt_madrid.const import (
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
    CONF_LINES,
    CONF_SENSOR_TYPE,
    CONF_STATION_ID,
    CONF_STOP_ID,
    DOMAIN,
    SENSOR_TYPE_BICIMAD,
    SENSOR_TYPE_BUS,
)

# ---------------------------------------------------------------------------
# Mock API responses
# ---------------------------------------------------------------------------

VALID_LOGIN = {
    "code": "01",
    "description": "Data recovered OK",
    "datetime": "2023-06-29T19:50:08.307475",
    "data": [
        {
            "accessToken": "test-token-abc123",
            "email": "test@mail.com",
            "userName": "testuser",
            "apiCounter": {"current": 0, "dailyUse": 20000},
        }
    ],
}

INVALID_USER_LOGIN = {
    "code": "92",
    "description": "Error: User not found",
    "datetime": "2023-06-29T20:01:09.441986",
    "data": [],
}

INVALID_PASSWORD_LOGIN = {
    "code": "89",
    "description": "Error: Invalid user or Password",
    "datetime": "2023-06-29T20:02:41.901955",
    "data": [],
}

VALID_STOP_INFO = {
    "code": "00",
    "description": "Data recovered OK",
    "datetime": "2023-07-02T15:41:44.008245",
    "data": [
        {
            "stops": [
                {
                    "stop": "72",
                    "name": "Cibeles-Casa de America",
                    "postalAddress": "Paseo de Recoletos 2",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [-3.692144, 40.420361],
                    },
                    "pmv": "60996",
                    "dataLine": [
                        {
                            "line": "027",
                            "label": "27",
                            "direction": "B",
                            "maxFreq": "25",
                            "minFreq": "11",
                            "headerA": "EMBAJADORES",
                            "headerB": "PLAZA CASTILLA",
                            "startTime": "07:00",
                            "stopTime": "00:01",
                            "dayType": "FE",
                        },
                        {
                            "line": "005",
                            "label": "5",
                            "direction": "B",
                            "maxFreq": "33",
                            "minFreq": "16",
                            "headerA": "SOL/SEVILLA",
                            "headerB": "CHAMARTIN",
                            "startTime": "07:00",
                            "stopTime": "22:58",
                            "dayType": "FE",
                        },
                    ],
                }
            ]
        }
    ],
}

VALID_ARRIVALS = {
    "code": "00",
    "description": "Data recovered OK",
    "datetime": "2023-06-29T18:50:13.968932",
    "data": [
        {
            "Arrive": [
                {
                    "line": "27",
                    "stop": "72",
                    "destination": "PLAZA CASTILLA",
                    "estimateArrive": 233,
                    "DistanceBus": 674,
                },
                {
                    "line": "5",
                    "stop": "72",
                    "destination": "CHAMARTIN",
                    "estimateArrive": 345,
                    "DistanceBus": 1777,
                },
                {
                    "line": "27",
                    "stop": "72",
                    "destination": "PLAZA CASTILLA",
                    "estimateArrive": 1556,
                    "DistanceBus": 1777,
                },
            ],
            "StopInfo": [],
            "ExtraInfo": [],
            "Incident": {},
        }
    ],
}

INVALID_STOP_ARRIVALS = {
    "code": "80",
    "description": [{"EN": "Bus Stop disabled or not exists"}],
    "datetime": "2023-06-29T21:34:48.886037",
    "data": [{"Arrive": [], "StopInfo": [], "ExtraInfo": [], "Incident": {}}],
}

INVALID_STOP_INFO = {
    "code": "90",
    "description": "Error managing internal services",
    "datetime": "2023-07-02T15:42:55.210432",
    "data": [],
}

VALID_BICIMAD_STATION = {
    "code": "00",
    "description": "Data recovered OK",
    "datetime": "2024-01-01T12:00:00.000000",
    "data": [
        {
            "id": "2139",
            "number": "2139",
            "name": "Gran Via",
            "address": "Calle Gran Via 1",
            "geometry": {
                "type": "Point",
                "coordinates": [-3.707500, 40.420000],
            },
            "dock_bikes": 5,
            "free_bases": 10,
        }
    ],
}

VALID_BICIMAD_STATIONS_LIST = {
    "code": "00",
    "description": "Data recovered OK",
    "datetime": "2024-01-01T12:00:00.000000",
    "data": [
        {
            "id": "2139",
            "number": "2139",
            "name": "Gran Via",
            "address": "Calle Gran Via 1",
            "geometry": {
                "type": "Point",
                "coordinates": [-3.707500, 40.420000],
            },
            "dock_bikes": 5,
            "free_bases": 10,
        },
        {
            "id": "1001",
            "number": "1001",
            "name": "Sol",
            "address": "Puerta del Sol 1",
            "geometry": {
                "type": "Point",
                "coordinates": [-3.703790, 40.416775],
            },
            "dock_bikes": 12,
            "free_bases": 3,
        },
    ],
}


def _make_request_mock(url, headers=None, data=None, method="POST"):
    """Mock the EMT API requests (v3 endpoints)."""
    base = "https://openapi.emtmadrid.es/"

    if url == f"{base}v3/mobilitylabs/user/login/":
        if headers.get("email") == "invalid@email.com":
            return INVALID_USER_LOGIN
        if headers.get("password") == "invalid_password":
            return INVALID_PASSWORD_LOGIN
        return VALID_LOGIN

    if "/v3/transport/busemtmad/stops/" in url and "/arrives/" in url:
        stop_id = int(url.split("/stops/")[1].split("/arrives")[0])
        if stop_id == 123456:
            return INVALID_STOP_ARRIVALS
        return VALID_ARRIVALS

    if "/v3/transport/busemtmad/stops/" in url and "/detail/" in url:
        stop_id = int(url.split("/stops/")[1].split("/detail")[0])
        if stop_id == 123456:
            return INVALID_STOP_INFO
        return VALID_STOP_INFO

    if "/v3/transport/bicimad/stations/" in url:
        station_id = url.split("/stations/")[1]
        if station_id == "2139":
            return VALID_BICIMAD_STATION
        return VALID_BICIMAD_STATIONS_LIST

    raise ValueError(f"Unexpected URL: {url}")


# ---------------------------------------------------------------------------
# Config flow tests
# ---------------------------------------------------------------------------


@patch(
    "custom_components.emt_madrid.emt_madrid.APIEMT._make_request",
    side_effect=_make_request_mock,
)
async def test_config_flow_valid_auth(
    hass: HomeAssistant,
) -> None:
    """Test config flow with valid credentials."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_EMAIL: "test@mail.com", CONF_PASSWORD: "password123"},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "sensor_type"


@patch(
    "custom_components.emt_madrid.emt_madrid.APIEMT._make_request",
    side_effect=_make_request_mock,
)
async def test_config_flow_invalid_auth(
    hass: HomeAssistant,
) -> None:
    """Test config flow with invalid credentials."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_EMAIL: "invalid@email.com", CONF_PASSWORD: "wrong"},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


@patch(
    "custom_components.emt_madrid.emt_madrid.APIEMT._make_request",
    side_effect=_make_request_mock,
)
async def test_config_flow_bus_sensor(
    hass: HomeAssistant,
) -> None:
    """Test full config flow for a bus sensor."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_EMAIL: "test@mail.com", CONF_PASSWORD: "password123"},
    )
    assert result["step_id"] == "sensor_type"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_SENSOR_TYPE: SENSOR_TYPE_BUS},
    )
    assert result["step_id"] == "bus"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_STOP_ID: 72, CONF_LINES: "27, 5"},
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_STOP_ID] == 72
    assert result["data"][CONF_LINES] == ["27", "5"]
    assert result["data"][CONF_SENSOR_TYPE] == SENSOR_TYPE_BUS


@patch(
    "custom_components.emt_madrid.emt_madrid.APIEMT._make_request",
    side_effect=_make_request_mock,
)
async def test_config_flow_bus_no_lines(
    hass: HomeAssistant,
) -> None:
    """Test config flow for a bus sensor without specifying lines."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_EMAIL: "test@mail.com", CONF_PASSWORD: "password123"},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_SENSOR_TYPE: SENSOR_TYPE_BUS},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_STOP_ID: 72, CONF_LINES: ""},
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_LINES] == []


@patch(
    "custom_components.emt_madrid.emt_madrid.APIEMT._make_request",
    side_effect=_make_request_mock,
)
async def test_config_flow_bicimad_sensor(
    hass: HomeAssistant,
) -> None:
    """Test full config flow for a BiciMad sensor."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_EMAIL: "test@mail.com", CONF_PASSWORD: "password123"},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_SENSOR_TYPE: SENSOR_TYPE_BICIMAD},
    )
    assert result["step_id"] == "bicimad"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_STATION_ID: 2139},
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_STATION_ID] == 2139
    assert result["data"][CONF_SENSOR_TYPE] == SENSOR_TYPE_BICIMAD


@patch(
    "custom_components.emt_madrid.emt_madrid.APIEMT._make_request",
    side_effect=_make_request_mock,
)
async def test_config_flow_credential_reuse(
    hass: HomeAssistant,
) -> None:
    """Test that credentials are reused on subsequent config flows."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_EMAIL: "test@mail.com", CONF_PASSWORD: "password123"},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_SENSOR_TYPE: SENSOR_TYPE_BUS},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_STOP_ID: 72, CONF_LINES: "27"},
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "sensor_type"


# ---------------------------------------------------------------------------
# Sensor tests via config entries
# ---------------------------------------------------------------------------


@patch(
    "custom_components.emt_madrid.emt_madrid.APIEMT._make_request",
    side_effect=_make_request_mock,
)
async def test_bus_sensor_attributes(
    hass: HomeAssistant,
) -> None:
    """Test bus sensor attributes including latitude/longitude."""
    entry = Mock()
    entry.entry_id = "test_bus_entry"
    entry.data = {
        CONF_EMAIL: "test@mail.com",
        CONF_PASSWORD: "password123",
        CONF_SENSOR_TYPE: SENSOR_TYPE_BUS,
        CONF_STOP_ID: 72,
        CONF_LINES: ["27"],
    }

    entities = []
    add_entities = Mock(side_effect=entities.extend)

    from custom_components.emt_madrid.sensor import async_setup_entry

    await async_setup_entry(hass, entry, add_entities)
    await hass.async_block_till_done()

    assert len(entities) == 1
    sensor = entities[0]

    assert sensor.name == "Bus 27 - Cibeles-Casa de America"
    assert sensor.native_value == 3
    assert sensor.native_unit_of_measurement == "min"

    attrs = sensor.extra_state_attributes
    assert attrs[ATTR_NEXT_BUS] == 25
    assert attrs[ATTR_STOP_ID] == 72
    assert attrs[ATTR_LINE] == "27"
    assert attrs[ATTR_DISTANCE] == 674
    assert attrs[ATTR_DESTINATION] == "PLAZA CASTILLA"
    assert attrs[ATTR_ORIGIN] == "EMBAJADORES"
    assert attrs[ATTR_START_TIME] == "07:00"
    assert attrs[ATTR_END_TIME] == "00:01"
    assert attrs[ATTR_MAX_FREQ] == 25
    assert attrs[ATTR_MIN_FREQ] == 11
    assert attrs[ATTR_STOP_NAME] == "Cibeles-Casa de America"
    assert attrs[ATTR_STOP_ADDRESS] == "Paseo de Recoletos 2"
    assert attrs[ATTR_LATITUDE] == 40.420361
    assert attrs[ATTR_LONGITUDE] == -3.692144
    assert attrs[ATTRIBUTION] == ATTRIBUTION


@patch(
    "custom_components.emt_madrid.emt_madrid.APIEMT._make_request",
    side_effect=_make_request_mock,
)
async def test_bus_sensor_all_lines(
    hass: HomeAssistant,
) -> None:
    """Test bus sensor creates entities for all lines when none specified."""
    entry = Mock()
    entry.entry_id = "test_bus_all"
    entry.data = {
        CONF_EMAIL: "test@mail.com",
        CONF_PASSWORD: "password123",
        CONF_SENSOR_TYPE: SENSOR_TYPE_BUS,
        CONF_STOP_ID: 72,
        CONF_LINES: [],
    }

    entities = []
    add_entities = Mock(side_effect=entities.extend)

    from custom_components.emt_madrid.sensor import async_setup_entry

    await async_setup_entry(hass, entry, add_entities)
    await hass.async_block_till_done()

    assert len(entities) == 2
    line_labels = {e.name for e in entities}
    assert "Bus 27 - Cibeles-Casa de America" in line_labels
    assert "Bus 5 - Cibeles-Casa de America" in line_labels


@patch(
    "custom_components.emt_madrid.emt_madrid.APIEMT._make_request",
    side_effect=_make_request_mock,
)
async def test_bicimad_sensor_attributes(
    hass: HomeAssistant,
) -> None:
    """Test BiciMad sensor attributes including latitude/longitude."""
    entry = Mock()
    entry.entry_id = "test_bici_entry"
    entry.data = {
        CONF_EMAIL: "test@mail.com",
        CONF_PASSWORD: "password123",
        CONF_SENSOR_TYPE: SENSOR_TYPE_BICIMAD,
        CONF_STATION_ID: 2139,
    }

    entities = []
    add_entities = Mock(side_effect=entities.extend)

    from custom_components.emt_madrid.sensor import async_setup_entry

    await async_setup_entry(hass, entry, add_entities)
    await hass.async_block_till_done()

    assert len(entities) == 1
    sensor = entities[0]

    assert sensor.name == "Bicimad Gran Via"
    assert sensor.native_value == 5
    assert sensor.native_unit_of_measurement == "bikes"

    attrs = sensor.extra_state_attributes
    assert attrs[ATTR_STATION_ID] == 2139
    assert attrs[ATTR_STATION_NUMBER] == "2139"
    assert attrs[ATTR_STATION_NAME] == "Gran Via"
    assert attrs[ATTR_STATION_ADDRESS] == "Calle Gran Via 1"
    assert attrs[ATTR_FREE_BASES] == 10
    assert attrs[ATTR_BIKES] == 5
    assert attrs[ATTR_LATITUDE] == 40.420000
    assert attrs[ATTR_LONGITUDE] == -3.707500
    assert attrs[ATTRIBUTION] == ATTRIBUTION
