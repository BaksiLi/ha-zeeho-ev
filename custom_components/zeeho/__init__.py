import datetime
import logging

from async_timeout import timeout
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .api import ZeehoVehicleHomePageClient
from .const import (
    CONF_UPDATE_INTERVAL, CONF_XUHAO, MANUFACTURER,
    COORDINATOR, DOMAIN, UNDO_UPDATE_LISTENER, CONF_Appid,
    CONF_Authorization, CONF_Cfmoto_X_Sign, CONF_Nonce,
    CONF_Signature, API_BASE_URL
)
from homeassistant.exceptions import ConfigEntryAuthFailed

from homeassistant.helpers.entity import DeviceInfo

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.SWITCH, Platform.DEVICE_TRACKER]

USER_AGENT = 'okhttp/4.9.2'
API_PATH_VEHICLE_HOME = "v1.0/app/cfmotoserverapp/vehicleHomePage"
API_URL = f"{API_BASE_URL}/{API_PATH_VEHICLE_HOME}"

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Zeeho component."""
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Zeeho from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    vehicle_home_page_client = ZeehoVehicleHomePageClient(
        entry.data[CONF_Authorization],
        entry.data[CONF_Cfmoto_X_Sign],
        entry.data[CONF_Appid],
        entry.data[CONF_Nonce],
        entry.data[CONF_Signature],
        USER_AGENT
    )
    xuhao = entry.data[CONF_XUHAO]
    update_interval_seconds = entry.options.get(CONF_UPDATE_INTERVAL, 90)
    location_key = entry.unique_id

    coordinator = ZeehoDataUpdateCoordinator(
        hass,
        _LOGGER,
        vehicle_home_page_client,
        xuhao,
        location_key,
        update_interval=datetime.timedelta(seconds=update_interval_seconds),
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        COORDINATOR: coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Set up update listener
    update_listener = entry.add_update_listener(async_update_options)
    hass.data[DOMAIN][entry.entry_id][UNDO_UPDATE_LISTENER] = update_listener

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Remove update listener
        update_listener = hass.data[DOMAIN][entry.entry_id].pop(UNDO_UPDATE_LISTENER, None)
        if update_listener is not None:
            update_listener()

        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options."""
    await hass.config_entries.async_reload(entry.entry_id)

class ZeehoDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, logger, vehicle_home_page_client, xuhao, location_key, update_interval):
        super().__init__(hass, logger, name=DOMAIN, update_interval=update_interval)
        self.vehicle_home_page_client = vehicle_home_page_client
        self.api_xuhao = xuhao
        self.location_key = location_key
        self._cached_data = None  # Variable to store cached data
        self._last_update = None   # Variable to store last update timestamp

    async def _async_update_data(self):
        """Fetch and process data from the ZEEHO API with caching."""
        current_time = datetime.datetime.now()

        # Check if cached data is still valid (e.g., within the last 5 minutes)
        if self._cached_data and (current_time - self._last_update).total_seconds() < self.update_interval.total_seconds() / 10:
            _LOGGER.debug("Using cached data")
            return self._cached_data

        try:
            async with timeout(10):
                resdata = await self.hass.async_add_executor_job(self.vehicle_home_page_client.get_data)

            if not resdata or "data" not in resdata:
                raise UpdateFailed("Invalid data structure received from API")

            if resdata.get("code") != "10000":
                raise ConfigEntryAuthFailed("API returned error code")

            data = resdata["data"][self.api_xuhao]
            if not data:
                raise UpdateFailed("Empty data received from API")

            # Process the data and log the processed output for debugging
            processed_data = self.process_data(data)
            _LOGGER.debug("Processed data: %s", processed_data)

            # Update cache
            self._cached_data = processed_data
            self._last_update = current_time  # Update the last update timestamp

            return processed_data

        except Exception as error:
            _LOGGER.error("Error updating data: %s", error)
            raise UpdateFailed(f"Unexpected error: {error}")

    def process_data(self, data):
        """Process the raw data from the API."""
        querytime = datetime.datetime.now(tz=datetime.timezone.utc).isoformat()
        rideState = "Online" if data.get("rideState") == "在线" else "Offline"
        chargeState = "Charging" if data.get("chargeState") == "1" else "Fully Charged" if data.get("bmssoc") == "100" else "On Battery"
        headLockState = "Unlocked" if data.get("headLockState") == "0" else "Locked" if data.get("headLockState") == "1" else f"Unknown {data.get('headLockState', 'Unknown')}"

        return {
            "location_key": self.location_key,
            "device_model": data.get("vehicleModel", "ZeehoEV"),
            "vehicleName": data.get("vehicleName", "ZeehoEV"),
            "querytime": querytime,
            # "latitude": self._safe_float(data.get("latitude")),
            # "longitude": self._safe_float(data.get("longitude")),
            "latitude": self._safe_float(data.get("location", {}).get("latitude")),
            "longitude": self._safe_float(data.get("location", {}).get("longitude")),
            "headLockState": headLockState,
            "bmssoc": self._safe_int(data.get("bmssoc")),
            "chargeState": chargeState,
            "locationTime": data.get("location", {}).get("locationTime"),
            "vinNo": data.get("vinNo"),
            "deviceName": data.get("deviceName"),
            "hmiRidableMile": self._safe_int(data.get("hmiRidableMile")),
            "rideState": rideState,
            "greenContribution": self._safe_float(data.get("greenContribution")),
            "otaVersion": data.get("otaVersion"),
            "vehicleType": data.get("vehicleType"),
            "vehicleTypeName": data.get("vehicleTypeName"),
            "totalRideMile": self._safe_float(data.get("totalRideMile")),
            "maxMileage": self._safe_int(data.get("maxMileage")),
            "onlineStatus": data.get("onlineStatus"),
        }

    @staticmethod
    def _safe_float(value):
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _safe_int(value):
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

def get_device_info(coordinator):
    """Generate device info from coordinator data."""
    return DeviceInfo(
        identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
        name=coordinator.data.get("device_name", "Zeeho EV"),
        model=coordinator.data.get("vehicleName"),
        manufacturer=MANUFACTURER,
        sw_version=coordinator.data.get("otaVersion"),
        hw_version=coordinator.data.get("vinNo"),
        configuration_url="https://www.zeehoev.com",
    )