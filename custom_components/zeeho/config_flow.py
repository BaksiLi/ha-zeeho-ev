"""Adds config flow for zeeho."""
import logging
import asyncio
import json
import time, datetime
import requests
import re
import homeassistant.helpers.config_validation as cv
from homeassistant.const import CONF_API_KEY, CONF_NAME
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig, SelectSelectorMode
from collections import OrderedDict
from homeassistant import config_entries
from homeassistant.core import callback
from .const import (
    CONF_Authorization,
    CONF_Cfmoto_X_Sign,
    CONF_Cfmoto_X_Param,
    CONF_Appid,
    CONF_Nonce,
    CONF_Signature,
    #CONF_USER_ID,
    #CONF_PARAMDATA,
    CONF_XUHAO,
    CONF_GPS_CONVER,
    CONF_UPDATE_INTERVAL,
    CONF_ATTR_SHOW,
    DOMAIN,
    CONF_SENSORS,
    KEY_QUERYTIME,
    KEY_PARKING_TIME,
    KEY_LASTSTOPTIME,
    KEY_ADDRESS,
    CONF_ADDRESSAPI,
    CONF_ADDRESSAPI_KEY,
    CONF_PRIVATE_KEY,
)

import voluptuous as vol

USER_AGENT = 'okhttp/4.9.2'
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
    
    #def post_data(self, url, headerstr, datastr):
    #    json_text = requests.post(url, headers=headerstr, data = datastr).content
    #    json_text = json_text.decode('utf-8')
    #    resdata = json.loads(json_text)
    #    return resdata
    def get_data(self, url, headerstr):
        json_text = requests.get(url, headers=headerstr).content
        json_text = json_text.decode('utf-8')
        resdata = json.loads(json_text)
        return resdata

    async def async_step_user(self, user_input={}):
        self._errors = {}
        if user_input is not None:
            # Check if entered host is already in HomeAssistant
            existing = await self._check_existing(user_input[CONF_NAME])
            if existing:
                return self.async_abort(reason="already_configured")

            # If it is not, continue with communication test  
            headers = {
                    #'Host': 'tapi.zeehoev.com:443',
                    #'Accept': 'application/json',
                    #'sessionid': self.user_id,

                    #'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8',
                    #'Cookie': 'sessionid=' + self.user_id,
                    'Host': 'tapi.zeehoev.com',
                    'Authorization': user_input["Authorization"],
                    'Accept-Language': 'zh-CN',
                    'Cfmoto-X-Sign': user_input["Cfmoto_X_Sign"],
                    'Cfmoto-X-Param': user_input["Cfmoto_X_Param"],
                    'Cfmoto-X-Sign-Type': '0',
                    'Appid': user_input["Appid"],
                    'Nonce': user_input["Nonce"],
                    'Signature': user_input["Signature"],
                    'Timestamp': '1725006411408',
                    'X-App-Info': 'MOBILE|Android|12|KLICEN_APP|2.5.21|Dalvik/2.1.0 (Linux; U; Android 12; ELS-AN00 Build/HUAWEIELS-AN00)|1200*2486|1|100|wifi|huawei',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'User-Agent': 'okhttp/4.9.2',
                    }
            url = str.format(API_URL)
            #Data = user_input["paramdata"]
            xuhao = user_input["xuhao"]

            redata =  await self.hass.async_add_executor_job(self.get_data, url, headers)         
            _LOGGER.info("Requests: %s", redata)
            
            status = redata["code"]=="10000" and len(redata["data"]) > user_input['xuhao']
            if status == True:
                await self.async_set_unique_id(f"zeeho-{user_input['Cfmoto_X_Sign']}--{user_input['xuhao']}".replace(".","_"))
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_NAME], data=user_input
                )
            else:
                self._errors["base"] = "communication"

            return await self._show_config_form(user_input)

        return await self._show_config_form(user_input)

    async def _show_config_form(self, user_input):

        # Defaults
        device_name = "ZEEHO"
        data_schema = OrderedDict()
        data_schema[vol.Required(CONF_NAME, default=device_name)] = str
        data_schema[vol.Required(CONF_Authorization ,default ="")] = str
        data_schema[vol.Required(CONF_Cfmoto_X_Sign ,default ="")] = str
        data_schema[vol.Required(CONF_Cfmoto_X_Param ,default ="")] = str
        data_schema[vol.Required(CONF_Appid ,default ="")] = str
        data_schema[vol.Required(CONF_Nonce ,default ="")] = str
        data_schema[vol.Required(CONF_Signature ,default ="")] = str
        data_schema[vol.Required(CONF_XUHAO ,default =0 )] = int

        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(data_schema), errors=self._errors
        )

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
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_UPDATE_INTERVAL,
                        default=self.config_entry.options.get(CONF_UPDATE_INTERVAL, 60),
                    ): vol.All(vol.Coerce(int), vol.Range(min=10, max=3600)), 
                    vol.Optional(
                        CONF_GPS_CONVER,
                        default=self.config_entry.options.get(CONF_GPS_CONVER, True),
                    ): bool, 
                    vol.Optional(
                        CONF_ATTR_SHOW,
                        default=self.config_entry.options.get(CONF_ATTR_SHOW, True),
                    ): bool,
                    vol.Optional(
                        CONF_SENSORS, 
                        default=self.config_entry.options.get(CONF_SENSORS,[])
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                {"value": KEY_PARKING_TIME, "label": "parkingtime"},
                                {"value": KEY_LASTSTOPTIME, "label": "laststoptime"}
                            ], 
                            multiple=True,translation_key=CONF_SENSORS
                        )
                    ),
                    vol.Optional(
                        CONF_ADDRESSAPI, 
                        default=self.config_entry.options.get(CONF_ADDRESSAPI,"none")
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                {"value": "none", "label": "none"},
                                {"value": "free", "label": "free"},
                                {"value": "gaode", "label": "gaode"},
                                {"value": "baidu", "label": "baidu"},
                                {"value": "tencent", "label": "tencent"}
                            ], 
                            multiple=False,translation_key=CONF_ADDRESSAPI
                        )
                    ),                    
                    vol.Optional(
                        CONF_ADDRESSAPI_KEY, 
                        default=self.config_entry.options.get(CONF_ADDRESSAPI_KEY,"")
                    ): str,
                    vol.Optional(
                        CONF_PRIVATE_KEY, 
                        default=self.config_entry.options.get(CONF_PRIVATE_KEY,"")
                    ): str,
                }
            ),
        )

