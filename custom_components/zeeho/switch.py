import logging
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, ATTR_HEADLOCKSTATE, CONF_SECRET, CONF_Appid, CONF_Authorization, CONF_User_agent
from .api import ZeehoVehicleUnlockClient
from . import get_device_info

_LOGGER = logging.getLogger(__name__)

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
        self.config_entry = config_entry
        self.vehicle_unlock_client = ZeehoVehicleUnlockClient(
            self.config_entry.data[CONF_Authorization],
            self.config_entry.data[CONF_Appid],
            self.config_entry.data[CONF_User_agent]
        )
        self._attr_name = "Lock"
        self._attr_unique_id = f"{DOMAIN}_lock_{self.config_entry.unique_id}"
        self._attr_device_info = get_device_info(coordinator)
        
    @property
    def is_on(self):
        return self.coordinator.data["headLockState"] == "Locked"

    async def async_turn_on(self, **kwargs):
        secret = self.config_entry.data.get(CONF_SECRET)
        if secret:
            await self.hass.async_add_executor_job(self.vehicle_unlock_client.unlock_vehicle, secret)
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Secret key is missing. Unable to unlock the vehicle.")

    async def async_turn_off(self, **kwargs):
        _LOGGER.warning("Locking the vehicle is not supported.")

    @property
    def extra_state_attributes(self):
        return {
            ATTR_HEADLOCKSTATE: self.coordinator.data["headLockState"]
        }