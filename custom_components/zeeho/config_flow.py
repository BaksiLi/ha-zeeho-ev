import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig
from homeassistant.helpers.dispatcher import callback

from .account import ZeehoAccount
from .const import (CONF_ADDRESSAPI, CONF_ADDRESSAPI_KEY, CONF_ATTR_SHOW,
                    CONF_GPS_CONVER, CONF_PRIVATE_KEY, CONF_SENSORS,
                    CONF_UPDATE_INTERVAL, CONF_XUHAO, DOMAIN, KEY_BMSSOC,
                    KEY_CHARGESTATE, KEY_HEADLOCKSTATE, KEY_LOCATIONTIME,
                    CONF_Appid, CONF_Authorization, CONF_Cfmoto_X_Sign,
                    CONF_NAME, CONF_Nonce, CONF_Signature, CONF_User_agent,
                    CONF_SECRET, API_BASE_URL)

_LOGGER = logging.getLogger(__name__)
API_PATH_VEHICLE_HOME = "vehicleHomePage"
API_URL = f"{API_BASE_URL}/{API_PATH_VEHICLE_HOME}"

class ZeehoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        errors: Dict[str, str] = {}

        if user_input is not None:
            try:
                account = ZeehoAccount(
                    user_input[CONF_Authorization],
                    user_input[CONF_Cfmoto_X_Sign],
                    user_input[CONF_Appid],
                    user_input[CONF_Nonce],
                    user_input[CONF_Signature],
                    user_input[CONF_User_agent]
                )
                redata = await self.hass.async_add_executor_job(account.get_data, API_URL)

                if redata["code"] == "10000" and len(redata["data"]) > user_input[CONF_XUHAO]:
                    await self.async_set_unique_id(f"zeeho-{user_input[CONF_Cfmoto_X_Sign]}--{user_input[CONF_XUHAO]}".replace(".", "_"))
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)
                else:
                    errors["base"] = "communication"
            except Exception as e:
                _LOGGER.error(f"Error validating input: {str(e)}")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_NAME, default="ZEEHO-EV"): str,
                vol.Required(CONF_Authorization): str,
                vol.Required(CONF_Cfmoto_X_Sign): str,
                vol.Required(CONF_Appid): str,
                vol.Required(CONF_Nonce): str,
                vol.Required(CONF_Signature): str,
                vol.Required(CONF_User_agent, default="okhttp/4.9.2"): str,
                vol.Required(CONF_XUHAO, default=0): int
            }),
            errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        return ZeehoOptionsFlow(config_entry)

class ZeehoOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        if user_input is not None:
            # Ensure that CONF_SECRET is included in the saved options
            if CONF_SECRET in user_input:
                return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_UPDATE_INTERVAL,
                    default=options.get(CONF_UPDATE_INTERVAL, 60),
                ): vol.All(vol.Coerce(int), vol.Range(min=10, max=3600)),
                vol.Optional(
                    CONF_GPS_CONVER,
                    default=options.get(CONF_GPS_CONVER, True),
                ): bool,
                vol.Optional(
                    CONF_ATTR_SHOW,
                    default=options.get(CONF_ATTR_SHOW, True),
                ): bool,
                vol.Optional(CONF_SENSORS,
                             default=options.get(CONF_SENSORS, [])):
                SelectSelector(
                    SelectSelectorConfig(options=[{
                        "value": KEY_BMSSOC,
                        "label": "bmssoc"
                    }, {
                        "value": KEY_LOCATIONTIME,
                        "label": "locationTime"
                    }, {
                        "value": KEY_CHARGESTATE,
                        "label": "chargeState"
                    }, {
                        "value": KEY_HEADLOCKSTATE,
                        "label": "headLockState"
                    }],
                                         multiple=True,
                                         translation_key=CONF_SENSORS)),
                vol.Optional(CONF_ADDRESSAPI,
                             default=options.get(CONF_ADDRESSAPI, "none")):
                SelectSelector(
                    SelectSelectorConfig(options=[{
                        "value": "none",
                        "label": "none"
                    }, {
                        "value": "free",
                        "label": "free"
                    }, {
                        "value": "gaode",
                        "label": "gaode"
                    }, {
                        "value": "baidu",
                        "label": "baidu"
                    }, {
                        "value": "tencent",
                        "label": "tencent"
                    }],
                                         multiple=False,
                                         translation_key=CONF_ADDRESSAPI)),
                vol.Optional(CONF_ADDRESSAPI_KEY,
                             default=options.get(CONF_ADDRESSAPI_KEY, "")):
                str,
                vol.Optional(CONF_PRIVATE_KEY,
                             default=options.get(CONF_PRIVATE_KEY, "")):
                str,
                vol.Optional(
                    CONF_SECRET,
                    default=options.get(CONF_SECRET, "")
                ): str,
            }),
        )
