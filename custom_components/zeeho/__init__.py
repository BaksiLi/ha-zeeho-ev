import asyncio
import datetime
import json
import logging
import os

from aiohttp.client_exceptions import ClientConnectorError
from async_timeout import timeout
from homeassistant.const import (Platform)
from homeassistant.core import Config, HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import (DataUpdateCoordinator,
                                                      UpdateFailed)
from .account import ZeehoAccount
from .const import (CONF_ATTR_SHOW, CONF_UPDATE_INTERVAL, CONF_XUHAO,
                    COORDINATOR, DOMAIN, UNDO_UPDATE_LISTENER, CONF_Appid,
                    CONF_Authorization, CONF_Cfmoto_X_Sign, CONF_Nonce,
                    CONF_Signature)

TYPE_GEOFENCE = "Geofence"

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.DEVICE_TRACKER, Platform.SENSOR]

USER_AGENT = 'okhttp/4.9.2'
API_URL = "https://tapi.zeehoev.com/v1.0/app/cfmotoserverapp/vehicleHomePage"

varstinydict = {}

def save_to_file(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f)
def read_from_file(filename):
    with open(filename, 'r') as f:
        data = json.load(f)
    return data       

async def async_setup(hass: HomeAssistant, config: Config) -> bool:
    """Set up configured autoamap."""
    # if (MAJOR_VERSION, MINOR_VERSION) < (2022, 4):
    # _LOGGER.error("Minimum supported Hass version 2022.4")
    # return False
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass, config_entry) -> bool:
    global varstinydict
    account = ZeehoAccount(
        config_entry.data[CONF_Authorization],
        config_entry.data[CONF_Cfmoto_X_Sign],
        config_entry.data[CONF_Appid],
        config_entry.data[CONF_Nonce],
        config_entry.data[CONF_Signature],
        USER_AGENT
    )
    xuhao = config_entry.data[CONF_XUHAO]
    update_interval_seconds = config_entry.options.get(CONF_UPDATE_INTERVAL, 90)
    attr_show = config_entry.options.get(CONF_ATTR_SHOW, True)
    location_key = config_entry.unique_id

    path = hass.config.path('.storage')
    if not os.path.exists(f'{path}/zeeho.json'):
        save_to_file(f'{path}/zeeho.json', {})
    varstinydict = read_from_file(f'{path}/zeeho.json')

    websession = async_get_clientsession(hass)
    coordinator = autoamapDataUpdateCoordinator(hass, websession, account, xuhao, location_key, update_interval_seconds)
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
            hass.config_entries.async_forward_entry_setup(config_entry, component)
        )

    # Register the unlock vehicle service
    hass.services.async_register(DOMAIN, "unlock_vehicle", handle_unlock_vehicle)

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

async def handle_unlock_vehicle(call):
    """Handle the service call to unlock the vehicle."""
    secret = call.data.get("secret")
    account = ZeehoAccount(
        call.data.get("authorization"),
        call.data.get("cfmoto_x_sign"),
        call.data.get("appid"),
        call.data.get("nonce"),
        call.data.get("signature"),
        call.data.get("user_agent")
    )
    result = await hass.async_add_executor_job(account.unlock_vehicle, secret)
    _LOGGER.info("Unlock vehicle result: %s", result)

class autoamapDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, session, account: ZeehoAccount, xuhao, location_key, update_interval_seconds):
        self.account = account
        self.api_xuhao = xuhao
        self.location_key = location_key
        self.path = hass.config.path('.storage')

        update_interval = datetime.timedelta(seconds=int(update_interval_seconds))
        _LOGGER.debug("Data will be updated every %s", update_interval)

        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=update_interval)

    async def _async_update_data(self):
        global varstinydict
        _LOGGER.debug("varstinydict: %s", varstinydict)

        try:
            async with timeout(10):
                resdata = await self.hass.async_add_executor_job(self.account.get_data, API_URL)
        except (ClientConnectorError) as error:
            raise UpdateFailed(error)
        _LOGGER.debug("Requests remaining: %s", API_URL)

        data = resdata["data"][self.api_xuhao]
        _LOGGER.debug("result data: %s", data)

        if data:
            querytime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            device_model = "ZEEHO"
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

            rideState = "🟢 Online" if data["rideState"] == "在线" else "🔴 Offline"
            chargeState = "🔋 Charging" if data["chargeState"] == "1" else "🔌 Fully Charged" if bmssoc == "100" else "⚡ On Battery"
            headLockState = "🔓 Unlocked" if data["headLockState"] == "0" else "🔒 Locked" if data["headLockState"] == "1" else "❓ Unknown"

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