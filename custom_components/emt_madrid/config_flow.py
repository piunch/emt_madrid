"""Config flow for EMT Madrid integration."""

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_LINES,
    CONF_SENSOR_TYPE,
    CONF_STATION_ID,
    CONF_STOP_ID,
    DOMAIN,
    SENSOR_TYPE_BICIMAD,
    SENSOR_TYPE_BUS,
)
from .emt_madrid import APIEMT

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA_USER = vol.Schema(
    {
        vol.Required(CONF_EMAIL): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
    }
)

DATA_SCHEMA_SENSOR_TYPE = vol.Schema(
    {
        vol.Required(CONF_SENSOR_TYPE): vol.In(
            {SENSOR_TYPE_BUS: "Bus (EMT)", SENSOR_TYPE_BICIMAD: "BiciMad"}
        )
    }
)

DATA_SCHEMA_BUS = vol.Schema(
    {
        vol.Required(CONF_STOP_ID): cv.positive_int,
        vol.Optional(CONF_LINES, default=""): cv.string,
    }
)


class EMTMadridConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for EMT Madrid."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize config flow."""
        self._email: str | None = None
        self._password: str | None = None
        self._token: str | None = None
        self._sensor_type: str | None = None
        self._api: APIEMT | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        existing_entries = self._async_current_entries()
        if existing_entries and user_input is None:
            first_entry = existing_entries[0]
            email = first_entry.data.get(CONF_EMAIL)
            password = first_entry.data.get(CONF_PASSWORD)
            if email and password:
                self._api = APIEMT(email, password)
                try:
                    token = await self.hass.async_add_executor_job(
                        self._api.authenticate
                    )
                    if token and token != "Invalid token":
                        self._email = email
                        self._password = password
                        self._token = token
                        return await self.async_step_sensor_type()
                except Exception:
                    _LOGGER.exception("Error reusing stored credentials")

        if user_input is not None:
            email = user_input[CONF_EMAIL]
            password = user_input[CONF_PASSWORD]

            self._api = APIEMT(email, password)
            try:
                token = await self.hass.async_add_executor_job(
                    self._api.authenticate
                )
                if token == "Invalid token" or token is None:
                    errors["base"] = "invalid_auth"
                else:
                    self._email = email
                    self._password = password
                    self._token = token
                    await self._update_existing_entries(email, password)
                    return await self.async_step_sensor_type()
            except Exception:
                _LOGGER.exception("Error authenticating with EMT API")
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA_USER,
            errors=errors,
        )

    async def _update_existing_entries(self, email: str, password: str) -> None:
        """Update credentials in all existing config entries."""
        for entry in self._async_current_entries():
            if (
                entry.data.get(CONF_EMAIL) != email
                or entry.data.get(CONF_PASSWORD) != password
            ):
                new_data = dict(entry.data)
                new_data[CONF_EMAIL] = email
                new_data[CONF_PASSWORD] = password
                self.hass.config_entries.async_update_entry(
                    entry, data=new_data
                )

    async def async_step_sensor_type(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle sensor type selection."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._sensor_type = user_input[CONF_SENSOR_TYPE]
            if self._sensor_type == SENSOR_TYPE_BUS:
                return await self.async_step_bus()
            return await self.async_step_bicimad()

        return self.async_show_form(
            step_id="sensor_type",
            data_schema=DATA_SCHEMA_SENSOR_TYPE,
            errors=errors,
        )

    async def async_step_bus(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle bus stop configuration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            stop_id = user_input[CONF_STOP_ID]
            lines_raw = user_input.get(CONF_LINES, "")
            lines = (
                [line.strip() for line in lines_raw.split(",") if line.strip()]
                if lines_raw
                else []
            )

            await self.async_set_unique_id(f"emt_bus_{stop_id}")
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=f"EMT Bus Stop {stop_id}",
                data={
                    CONF_EMAIL: self._email,
                    CONF_PASSWORD: self._password,
                    CONF_SENSOR_TYPE: SENSOR_TYPE_BUS,
                    CONF_STOP_ID: stop_id,
                    CONF_LINES: lines,
                },
            )

        return self.async_show_form(
            step_id="bus",
            data_schema=DATA_SCHEMA_BUS,
            errors=errors,
        )

    async def async_step_bicimad(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle BiciMad station configuration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            station_id = user_input[CONF_STATION_ID]

            await self.async_set_unique_id(f"emt_bicimad_{station_id}")
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=f"EMT BiciMad Station {station_id}",
                data={
                    CONF_EMAIL: self._email,
                    CONF_PASSWORD: self._password,
                    CONF_SENSOR_TYPE: SENSOR_TYPE_BICIMAD,
                    CONF_STATION_ID: station_id,
                },
            )

        data_schema = vol.Schema(
            {vol.Required(CONF_STATION_ID): cv.positive_int}
        )

        if self._api is not None and self._api.get_token():
            stations = await self.hass.async_add_executor_job(
                self._api.get_all_bicimad_stations
            )
            if stations:
                stations.sort(key=lambda s: s.get("id", 0))
                station_options = {
                    station["id"]: (
                        f"{station.get('number', '?')} - "
                        f"{station.get('name', 'Unknown')}"
                    )
                    for station in stations
                    if "id" in station
                }
                if station_options:
                    data_schema = vol.Schema(
                        {
                            vol.Required(CONF_STATION_ID): vol.In(
                                station_options
                            )
                        }
                    )

        return self.async_show_form(
            step_id="bicimad",
            data_schema=data_schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return EMTMadridOptionsFlowHandler(config_entry)


class EMTMadridOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for EMT Madrid."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        sensor_type = self._config_entry.data.get(CONF_SENSOR_TYPE)

        if sensor_type == SENSOR_TYPE_BUS:
            if user_input is not None:
                lines_raw = user_input.get(CONF_LINES, "")
                lines = (
                    [line.strip() for line in lines_raw.split(",") if line.strip()]
                    if lines_raw
                    else []
                )
                return self.async_create_entry(
                    title="",
                    data={
                        CONF_LINES: lines,
                    },
                )

            current_lines = self._config_entry.data.get(CONF_LINES, [])
            lines_str = ", ".join(current_lines) if current_lines else ""

            data_schema = vol.Schema(
                {
                    vol.Optional(CONF_LINES, default=lines_str): cv.string,
                }
            )

            return self.async_show_form(
                step_id="init",
                data_schema=data_schema,
            )

        return self.async_create_entry(title="", data={})
