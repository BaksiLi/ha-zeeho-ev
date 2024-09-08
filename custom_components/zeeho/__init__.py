import asyncio
import datetime
import json
import logging
import os
import re
import time
from datetime import timedelta

import homeassistant.helpers.config_validation as cv
import homeassistant.util.dt as dt_util
import pytz
import requests
import voluptuous as vol
from aiohttp.client_exceptions import ClientConnectorError
from async_timeout import timeout
from dateutil.relativedelta import relativedelta
from homeassistant.components import zone
from homeassistant.components.device_tracker import PLATFORM_SCHEMA
from homeassistant.components.device_tracker.const import CONF_SCAN_INTERVAL
from homeassistant.components.device_tracker.legacy import DeviceScanner
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (ATTR_GPS_ACCURACY, ATTR_LATITUDE,
                                 ATTR_LONGITUDE, CONF_API_KEY, CONF_NAME,
                                 MAJOR_VERSION, MINOR_VERSION, STATE_HOME,
                                 STATE_NOT_HOME, Platform)
from homeassistant.core import Config, HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import (async_track_time_interval,
                                         track_utc_time_change)
from homeassistant.helpers.json import save_json
from homeassistant.helpers.update_coordinator import (DataUpdateCoordinator,
                                                      UpdateFailed)
from homeassistant.util import slugify
from homeassistant.util.json import load_json
from homeassistant.util.location import distance
from requests import (ConnectionError, ConnectTimeout, HTTPError, ReadTimeout,
                      Timeout)

from .const import (CONF_ATTR_SHOW, CONF_UPDATE_INTERVAL, CONF_XUHAO,
                    COORDINATOR, DOMAIN, UNDO_UPDATE_LISTENER, CONF_Appid,
                    CONF_Authorization, CONF_Cfmoto_X_Sign, CONF_Nonce,
                    CONF_Signature)

TYPE_GEOFENCE = "Geofence"
__version__ = '2023.11.16'

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.DEVICE_TRACKER, Platform.SENSOR]

USER_AGENT = 'okhttp/4.9.2'
API_URL = "https://tapi.zeehoev.com/v1.0/app/cfmotoserverapp/vehicleHomePage"

varstinydict = {}


async def async_setup(hass: HomeAssistant, config: Config) -> bool:
    """Set up configured autoamap."""
    # if (MAJOR_VERSION, MINOR_VERSION) < (2022, 4):
    # _LOGGER.error("Minimum supported Hass version 2022.4")
    # return False
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass, config_entry) -> bool:
    """Set up autoamap as config entry."""
    global varstinydict
    #user_id = config_entry.data[CONF_USER_ID]
    Authorization = config_entry.data[CONF_Authorization]
    Cfmoto_X_Sign = config_entry.data[CONF_Cfmoto_X_Sign]
    Appid = config_entry.data[CONF_Appid]
    Nonce = config_entry.data[CONF_Nonce]
    Signature = config_entry.data[CONF_Signature]
    #api_key = config_entry.data[CONF_API_KEY]
    #paramadata = config_entry.data[CONF_PARAMDATA]
    xuhao = config_entry.data[CONF_XUHAO]
    update_interval_seconds = config_entry.options.get(CONF_UPDATE_INTERVAL,
                                                       90)
    attr_show = config_entry.options.get(CONF_ATTR_SHOW, True)
    location_key = config_entry.unique_id

    def save_to_file(filename, data):
        with open(filename, 'w') as f:
            json.dump(data, f)

    def read_from_file(filename):
        with open(filename, 'r') as f:
            data = json.load(f)
        return data

    path = hass.config.path(f'.storage')

    if not os.path.exists(f'{path}/zeeho.json'):
        save_to_file(f'{path}/zeeho.json', {})
    varstinydict = read_from_file(f'{path}/zeeho.json')
    #_LOGGER.debug("varstinydict: %s", varstinydict)

    #_LOGGER.debug("Using location_key: %s, user_id: %s, update_interval_seconds: %s", location_key, user_id, update_interval_seconds)

    websession = async_get_clientsession(hass)

    coordinator = autoamapDataUpdateCoordinator(hass, websession,
                                                Authorization, Cfmoto_X_Sign,
                                                Appid, Nonce,
                                                Signature, xuhao, location_key,
                                                update_interval_seconds)
    await coordinator.async_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    undo_listener = config_entry.add_update_listener(update_listener)

    hass.data[DOMAIN][config_entry.entry_id] = {
        COORDINATOR: coordinator,
        UNDO_UPDATE_LISTENER: undo_listener,
    }

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(
                config_entry, component))

    return True


async def async_unload_entry(hass, config_entry):
    """Unload a config entry."""
    unload_ok = all(await asyncio.gather(*[
        hass.config_entries.async_forward_entry_unload(config_entry, component)
        for component in PLATFORMS
    ]))

    hass.data[DOMAIN][config_entry.entry_id][UNDO_UPDATE_LISTENER]()

    if unload_ok:
        hass.data[DOMAIN].pop(config_entry.entry_id)

    return unload_ok


async def update_listener(hass, config_entry):
    """Update listener."""
    await hass.config_entries.async_reload(config_entry.entry_id)


class autoamapDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching autoamap data API."""

    def __init__(self, hass, session, Authorization, Cfmoto_X_Sign,
                 Appid, Nonce, Signature, xuhao, location_key,
                 update_interval_seconds):
        """Initialize."""
        self.location_key = location_key
        #self.user_id = user_id
        #self.api_key = api_key
        #self.api_paramdata = paramdata
        self.Authorization = Authorization
        self.Cfmoto_X_Sign = Cfmoto_X_Sign
        self.Appid = Appid
        self.Nonce = Nonce
        self.Signature = Signature
        self.api_xuhao = xuhao

        self.path = hass.config.path(f'.storage')

        # if not os.path.exists(f'{self.path}/zeeho.json'):
        # self.save_to_file(f'{self.path}/zeeho.json', {})
        # varstinydict = self.read_from_file(f'{self.path}/zeeho.json')
        # _LOGGER.debug("varstinydict: %s", varstinydict)

        update_interval = (datetime.timedelta(
            seconds=int(update_interval_seconds)))
        _LOGGER.debug("Data will be update every %s", update_interval)

        super().__init__(hass,
                         _LOGGER,
                         name=DOMAIN,
                         update_interval=update_interval)

    def save_to_file(self, filename, data):
        with open(filename, 'w') as f:
            json.dump(data, f)

    def read_from_file(self, filename):
        with open(filename, 'r') as f:
            data = json.load(f)
        return data

    # @asyncio.coroutine
    def get_data(self, url, headerstr):
        json_text = requests.get(url, headers=headerstr).content
        json_text = json_text.decode('utf-8')
        resdata = json.loads(json_text)
        return resdata

    def post_data(self, url, headerstr, datastr):
        json_text = requests.post(url, headers=headerstr, data=datastr).content
        json_text = json_text.decode('utf-8')
        resdata = json.loads(json_text)
        return resdata

    async def _async_update_data(self):
        """Update data via library."""
        global varstinydict
        _LOGGER.debug("varstinydict: %s", varstinydict)

        try:
            async with timeout(10):
                headers = {
                    'Host': 'tapi.zeehoev.com',
                    'Authorization': self.Authorization,
                    'Accept-Language': 'zh-CN',
                    'Cfmoto-X-Sign': self.Cfmoto_X_Sign,
                    'Cfmoto-X-Sign-Type': '0',
                    'Appid': self.Appid,
                    'Nonce': self.Nonce,
                    'Signature': self.Signature,
                    'Timestamp': '1725006411408',
                    'X-App-Info':
                    'MOBILE|Android|12|KLICEN_APP|2.5.21|Dalvik/2.1.0 (Linux; U; Android 12; ELS-AN00 Build/HUAWEIELS-AN00)|1200*2486|1|100|wifi|huawei',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'User-Agent': 'okhttp/4.9.2',
                }
                url = str.format(API_URL)
                #Data = self.api_paramdata
                #resdata =  await self.hass.async_add_executor_job(self.post_data, url, headers, Data)
                resdata = await self.hass.async_add_executor_job(
                    self.get_data, url, headers)
        except (ClientConnectorError) as error:
            raise UpdateFailed(error)
        _LOGGER.debug("Requests remaining: %s", url)

        #data = resdata["data"]["carLinkInfoList"][self.api_xuhao]
        data = resdata["data"][self.api_xuhao]
        _LOGGER.debug("result data: %s", data)

        if data:
            querytime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            device_model = "ZEEHO"
            #sw_version = data["sysInfo"]["autodiv"]

            vehicleName = data["vehicleName"]
            vehiclePicUrl = data["vehiclePicUrl"]
            bmssoc = data["bmssoc"]

            bluetoothAddress = data["bluetoothAddress"]

            fullChargeTime = data["fullChargeTime"]
            otaVersion = data["otaVersion"]

            supportNetworkUnlock = data["supportNetworkUnlock"]
            totalRideMile = data["totalRideMile"]
            supportUnlock = data["supportUnlock"]
            whetherChargeState = data["whetherChargeState"]

            thislat = data["location"]["latitude"]
            thislon = data["location"]["longitude"]
            altitude = data["location"]["altitude"]
            locationTime = data["location"]["locationTime"]

            if data["rideState"] == "在线":
                rideState = "🟢 Online"
            else:
                rideState = "🔴 Offline"

            if data["chargeState"] == "1":
                chargeState = "🔋 Charging"
            else:
                if bmssoc == "100":
                    chargeState = "🔌 Fully Charged"
                else:
                    chargeState = "⚡ Not Charging"

            if data["headLockState"] == "0":
                headLockState = "🔓 Unlocked"
            elif data["headLockState"] == "1":
                headLockState = "🔒 Locked"
            else:
                headLockState = "❓ Unknown"


        return {
            "location_key": self.location_key,
            "device_model": device_model,
            "vehicleName": vehicleName,
            "vehiclePicUrl": vehiclePicUrl,
            "bmssoc": bmssoc,
            "fullChargeTime": fullChargeTime,
            "otaVersion": otaVersion,
            "supportNetworkUnlock": supportNetworkUnlock,
            "totalRideMile": totalRideMile,
            "supportUnlock": supportUnlock,
            "whetherChargeState": whetherChargeState,
            "locationTime": locationTime,
            "thislat": thislat,
            "thislon": thislon,
            "altitude": altitude,
            "querytime": querytime,
            "rideState": rideState,
            "bluetoothAddress": bluetoothAddress,
            "chargeState": chargeState,
            "headLockState": headLockState
        }
