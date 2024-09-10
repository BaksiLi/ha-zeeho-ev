"""Support for the autoamap service."""
import logging
import datetime

from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.device_tracker import SourceType
from homeassistant.const import (
    CONF_NAME,
)
from .const import (
    COORDINATOR,
    DOMAIN, 
)
from homeassistant.helpers.entity import DeviceInfo

PARALLEL_UPDATES = 1
_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = datetime.timedelta(seconds=60)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Zeeho device tracker platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
    async_add_entities([ZeehoDeviceTracker(coordinator, config_entry)], True)

class ZeehoDeviceTracker(CoordinatorEntity, TrackerEntity):
    def __init__(self, coordinator, config_entry):
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._attr_unique_id = f"{config_entry.entry_id}_tracker"
        self._attr_name = f"{config_entry.data.get(CONF_NAME, DOMAIN)} Tracker"
        self._attr_device_info = get_device_info(coordinator)

    @property
    def latitude(self):
        return self.coordinator.data.get("thislat")

    @property
    def longitude(self):
        return self.coordinator.data.get("thislon")

    @property
    def source_type(self):
        return SourceType.GPS

    @property
    def battery_level(self):
        return int(self.coordinator.data.get("bmssoc", 0))

    @property
    def icon(self):
        return "mdi:motorbike-electric"