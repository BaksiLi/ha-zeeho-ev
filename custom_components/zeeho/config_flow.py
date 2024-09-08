import logging
from collections import OrderedDict

from .account import ZeehoAccount
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers.selector import (SelectSelector,
                                            SelectSelectorConfig)

from .const import (CONF_ADDRESSAPI, CONF_ADDRESSAPI_KEY, CONF_ATTR_SHOW,
                    CONF_GPS_CONVER, CONF_PRIVATE_KEY, CONF_SENSORS,
                    CONF_UPDATE_INTERVAL, CONF_XUHAO, DOMAIN, KEY_BMSSOC, KEY_CHARGESTATE, KEY_HEADLOCKSTATE,
                    KEY_LOCATIONTIME, CONF_Appid, CONF_Authorization,
                    CONF_Cfmoto_X_Sign, CONF_Nonce, CONF_Signature,
                    CONF_User_agent)

API_URL = "https://tapi.zeehoev.com/v1.0/app/cfmotoserverapp/vehicleHomePage"

_LOGGER = logging.getLogger(__name__)


@config_entries.HANDLERS.register(DOMAIN)
class FlowHandler(config_entries.ConfigFlow, domain=DOMAIN):

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlow(config_entry)

    def __init__(self):
        """Initialize."""
        self._errors = {}

    def get_data(self, account: ZeehoAccount) -> dict:
        return account.get_data(API_URL)

    async def async_step_user(self, user_input={}):
        self._errors = {}
        if user_input is not None:
            existing = await self._check_existing(user_input[CONF_NAME])
            if existing:
                return self.async_abort(reason="already_configured")

            account = ZeehoAccount(
                user_input["Authorization"],
                user_input["Cfmoto_X_Sign"],
                user_input["Appid"],
                user_input["Nonce"],
                user_input["Signature"],
                user_input["User_agent"]
            )

            redata = await self.hass.async_add_executor_job(self.get_data, account)
            _LOGGER.info("Requests: %s", redata)

            status = redata["code"] == "10000" and len(redata["data"]) > user_input['xuhao']
            if status:
                await self.async_set_unique_id(f"zeeho-{user_input['Cfmoto_X_Sign']}--{user_input['xuhao']}".replace(".", "_"))
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)
            else:
                self._errors["base"] = "communication"

            return await self._show_config_form(user_input)

        return await self._show_config_form(user_input)

    async def _show_config_form(self, user_input):

        # Defaults
        device_name = "ZEEHO-EV"
        data_schema = OrderedDict()
        data_schema[vol.Required(CONF_NAME, default="ZEEHO-EV")] = str
        data_schema[vol.Required(CONF_Authorization, default="")] = str
        data_schema[vol.Required(CONF_Cfmoto_X_Sign, default="")] = str
        data_schema[vol.Required(CONF_Appid, default="")] = str
        data_schema[vol.Required(CONF_Nonce, default="")] = str
        data_schema[vol.Required(CONF_Signature, default="")] = str
        data_schema[vol.Required(CONF_User_agent,
                                 default="okhttp/4.9.2")] = str
        data_schema[vol.Required(CONF_XUHAO, default=0)] = int

        return self.async_show_form(step_id="user",
                                    data_schema=vol.Schema(data_schema),
                                    errors=self._errors)

    async def async_step_import(self, user_input):
        """Import a config entry.

        Special type of import, we're not actually going to store any data.
        Instead, we're going to rely on the values that are in config file.
        """
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        return self.async_create_entry(title="configuration.yaml", data={})

    async def _check_existing(self, host):
        for entry in self._async_current_entries():
            if host == entry.data.get(CONF_NAME):
                return True


class OptionsFlow(config_entries.OptionsFlow):
    """Config flow options for zeeho."""

    def __init__(self, config_entry):
        """Initialize zeeho options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_UPDATE_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_UPDATE_INTERVAL, 60),
                ):
                vol.All(vol.Coerce(int), vol.Range(min=10, max=3600)),
                vol.Optional(
                    CONF_GPS_CONVER,
                    default=self.config_entry.options.get(
                        CONF_GPS_CONVER, True),
                ):
                bool,
                vol.Optional(
                    CONF_ATTR_SHOW,
                    default=self.config_entry.options.get(
                        CONF_ATTR_SHOW, True),
                ):
                bool,
                vol.Optional(CONF_SENSORS,
                             default=self.config_entry.options.get(
                                 CONF_SENSORS, [])):
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
                             default=self.config_entry.options.get(
                                 CONF_ADDRESSAPI, "none")):
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
                             default=self.config_entry.options.get(
                                 CONF_ADDRESSAPI_KEY, "")):
                str,
                vol.Optional(CONF_PRIVATE_KEY,
                             default=self.config_entry.options.get(
                                 CONF_PRIVATE_KEY, "")):
                str,
            }),
        )
