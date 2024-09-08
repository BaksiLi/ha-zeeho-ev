import logging
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .const import DOMAIN, ATTR_HEADLOCKSTATE, API_BASE_URL, CONF_SECRET, CONF_Appid, CONF_Authorization, CONF_Nonce, CONF_Cfmoto_X_Sign, CONF_Signature, CONF_User_agent

import datetime

_LOGGER = logging.getLogger(__name__)

API_PATH_VEHICLE_HOME = "vehicleSet/network/unlock"
API_URL = f"{API_BASE_URL}/{API_PATH_VEHICLE_HOME}"

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Zeeho switch."""
    _LOGGER.debug("Setting up Zeeho switch")
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    async_add_entities([ZeehoLockSwitch(coordinator, config_entry)], True)

class ZeehoLockSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a Zeeho lock switch."""

    def __init__(self, coordinator, config_entry):
        """Initialize the switch."""
        super().__init__(coordinator)
        _LOGGER.debug("Initializing ZeehoLockSwitch")
        self._attr_name = "Zeeho Lock"
        self._attr_unique_id = f"{config_entry.entry_id}-lock"
        self.entity_id = f"switch.{DOMAIN}_lock"
        self._state = self.coordinator.data.get(ATTR_HEADLOCKSTATE) == "0"
        self._config_entry = config_entry
        _LOGGER.debug(f"Initial state: {self._state}")

    @property
    def is_on(self):
        """Return true if the switch is on (unlocked)."""
        return self._state

    async def async_turn_on(self, **kwargs):
        """Turn the switch on (unlock the vehicle)."""
        _LOGGER.debug("Attempting to unlock vehicle")
        await self._unlock_vehicle()

    async def async_turn_off(self, **kwargs):
        """Turn the switch off (lock the vehicle)."""
        _LOGGER.debug("Attempting to lock vehicle")
        await self._lock_vehicle()

    async def _unlock_vehicle(self):
        """Unlock the vehicle."""
        secret = self._config_entry.options.get(CONF_SECRET)
        if not secret:
            _LOGGER.error("No secret available for unlocking the vehicle. Please set it in the integration options.")
            return

        headers = {
            "content-type": "application/json",
            "appid": self._config_entry.data.get(CONF_Appid),
            "cfmoto-x-sign-type": "0",
            "authorization": self._config_entry.data.get(CONF_Authorization),
            "accept": "*/*",
            "timestamp": str(int(datetime.datetime.now().timestamp() * 1000)),
            "nonce": self._config_entry.data.get(CONF_Nonce),
            "cfmoto-x-sign": self._config_entry.data.get(CONF_Cfmoto_X_Sign),
            "signature": self._config_entry.data.get(CONF_Signature),
            "user-agent": self._config_entry.data.get(CONF_User_agent),
            "interfaceversion": "2",
        }

        payload = {"secret": secret}

        session = async_get_clientsession(self.hass)
        try:
            async with session.post(API_URL, headers=headers, json=payload) as response:
                if response.status != 200:
                    response_text = await response.text()
                    _LOGGER.error(f"Failed to unlock vehicle. Status: {response.status}, Response: {response_text}")
                else:
                    result = await response.json()
                    if result.get("code") == "10000":
                        self._state = True
                        self.async_write_ha_state()
                        _LOGGER.info("Vehicle unlocked successfully")
                    else:
                        _LOGGER.error(f"Failed to unlock vehicle: {result.get('message')}")
        except Exception as e:
            _LOGGER.error(f"Error unlocking vehicle: {str(e)}")

    async def _lock_vehicle(self):
        """Lock the vehicle."""
        # Implement the lock vehicle functionality if available
        _LOGGER.debug("Locking vehicle (not implemented)")
        self._state = False
        self.async_write_ha_state()

    async def async_update(self):
        """Update the switch state."""
        _LOGGER.debug("Updating ZeehoLockSwitch state")
        self._state = self.coordinator.data.get(ATTR_HEADLOCKSTATE) == "0"
        _LOGGER.debug(f"Updated state: {self._state}")
        self.async_write_ha_state()