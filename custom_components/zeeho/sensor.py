"""Support for Traccar device tracking."""
import logging
from datetime import timedelta

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)

from homeassistant.const import UnitOfLength
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_QUERYTIME,
    CONF_NAME,
    COORDINATOR,
    DOMAIN,
    KEY_ADDRESS,
    KEY_BMSSOC,
    KEY_CHARGESTATE,
    KEY_HEADLOCKSTATE,
    KEY_LOCATIONTIME,
    KEY_TOTALRIDEMILE,
)

from . import get_device_info

_LOGGER = logging.getLogger(__name__)

SENSOR_TYPES: dict[str, SensorEntityDescription] = {
    KEY_BMSSOC: SensorEntityDescription(
        key=KEY_BMSSOC,
        native_unit_of_measurement='%',
        device_class=SensorDeviceClass.BATTERY,
        name="Battery Level",
        icon="mdi:battery"  # Icon for battery level
    ),
    KEY_CHARGESTATE: SensorEntityDescription(
        key=KEY_CHARGESTATE,
        name="Charging Status",
        icon="mdi:battery-charging"  # Icon for charging status
    ),
    KEY_HEADLOCKSTATE: SensorEntityDescription(
        key=KEY_HEADLOCKSTATE,
        name="Lock Status",
        icon="mdi:lock"  # Icon for lock status
    ),
    KEY_LOCATIONTIME: SensorEntityDescription(
        key=KEY_LOCATIONTIME,
        name="Last Parking Time",
        icon="mdi:timer"  # Icon for time
    ),
    KEY_TOTALRIDEMILE: SensorEntityDescription(
        key=KEY_TOTALRIDEMILE,
        name="Total Ride Distance",
        native_unit_of_measurement='km',
        icon="mdi:map-marker-distance",  # Icon for distance
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
}

SCAN_INTERVAL = timedelta(seconds=60)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add Zeeho entities from a config_entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
    device_name = config_entry.data.get(CONF_NAME, "ZEEHO-EV")

    sensors = []
    for sensor_type, description in SENSOR_TYPES.items():
        sensors.append(ZeehoSensorEntity(device_name, description, coordinator))

    sensors.extend([
        ZeehoDiagnosticSensor(device_name, coordinator),
    ])

    async_add_entities(sensors, False)

class ZeehoSensorEntity(CoordinatorEntity):
    """Define a Zeeho sensor entity."""
    
    _attr_has_entity_name = True
      
    def __init__(self, device_name, description, coordinator):
        """Initialize."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}-{description.key}"
        self._attr_device_info = get_device_info(coordinator)
        self._device_name = device_name
        self._attr_translation_key = f"{self.entity_description.name}"
        self._state = None
        self._attrs = {}
        self._update_state()

    def _update_state(self):
        _LOGGER.debug("Updating state for sensor: %s", self.entity_description.key)
        # _LOGGER.debug("Current coordinator data: %s", self.coordinator.data)

        if self.entity_description.key == KEY_BMSSOC:
            self._state = self.coordinator.data.get(KEY_BMSSOC)
        elif self.entity_description.key == KEY_CHARGESTATE:
            self._state = self.coordinator.data.get(KEY_CHARGESTATE)
        elif self.entity_description.key == KEY_HEADLOCKSTATE:
            self._state = self.coordinator.data.get(KEY_HEADLOCKSTATE)
        elif self.entity_description.key == KEY_LOCATIONTIME:
            self._state = self.coordinator.data.get(KEY_LOCATIONTIME)
        elif self.entity_description.key == KEY_TOTALRIDEMILE:
            self._state = self.coordinator.data.get(KEY_TOTALRIDEMILE)
        else:
            _LOGGER.warning("Unknown sensor key: %s", self.entity_description.key)

        self._attrs = {ATTR_QUERYTIME: self.coordinator.data.get(ATTR_QUERYTIME)}
        
        _LOGGER.debug("Updated state for %s: %s", self.entity_description.key, self._state)

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def state(self):
        """Return the state."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return extra state attributes."""
        return self._attrs

    async def async_update(self):
        """Update Zeeho entity."""
        _LOGGER.debug("Refreshing sensor data")
        self._update_state()

class ZeehoDiagnosticSensor(ZeehoSensorEntity):
    _attr_name = "Zeeho Diagnostic"
    _attr_icon = "mdi:motorcycle-electric"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["🟢 Online", "🔴 Offline"]
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    
    def __init__(self, device_name, coordinator):
        description = SensorEntityDescription(
            key="diagnostic",
            name="Diagnostic",
            device_class=SensorDeviceClass.ENUM,
        )
        super().__init__(device_name, description, coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}-diagnostic"

    def _update_state(self):
        self._state = "🟢 Online" if self.coordinator.data.get("rideState") == "Online" else "🔴 Offline"
        _LOGGER.debug("Updated diagnostic state: %s", self._state)

    @property
    def native_value(self):
        self._update_state()
        return self._state

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data
        if not data:
            return {}

        return {
            "Vehicle Name": data.get("vehicleName"),
            "OTA Version": data.get("otaVersion"),
            "Car Lock Status": data.get("headLockState"),
            "Bluetooth Address": data.get("bluetoothAddress"),
            "Vehicle Battery Level": f"{data.get('bmssoc', 0)}%",
            "Charging Status": data.get("chargeState"),
            "Full Charge Time": data.get("fullChargeTime"),
            "Max Mileage": f"{data.get('maxMileage', 0)} {UnitOfLength.KILOMETERS}",
            "Total Ride Mileage": f"{data.get('totalRideMile', 0)} {UnitOfLength.KILOMETERS}",
            "Ride State": data.get("rideState"),
            "Last Parking Time": data.get("locationTime"),
            "Querytime": data.get("querytime"),
            "Address": data.get("address"),
            "Data Source": "GPS Positioning",
            "Latitude": data.get("latitude"),
            "Longitude": data.get("longitude"),
            "GPS Accuracy": "0 m",
            "Gaode Map Latitude": data.get("map_gcj_lat"),
            "Gaode Map Longitude": data.get("map_gcj_lng"),
            "Baidu Map Latitude": data.get("map_bd_lat"),
            "Baidu Map Longitude": data.get("map_bd_lng"),
            "Max Range": f"{data.get('maxMileage', 0)} {UnitOfLength.KILOMETERS}",
            "Green Contribution": f"{data.get('greenContribution', 0)} kg CO₂",
        }

# class ZeehoVehiclePhotoSensor(ZeehoSensorEntity):
#     _attr_name = "Zeeho Vehicle Photo"
#     _attr_icon = "mdi:image"

#     def __init__(self, device_name, coordinator):
#         description = SensorEntityDescription(
#             key="vehicle_photo",
#             name="Zeeho Vehicle Photo",
#         )
#         super().__init__(device_name, description, coordinator)
#         self._attr_unique_id = f"{coordinator.config_entry.entry_id}-vehicle_photo"

#     @property
#     def native_value(self):
#         return self.coordinator.data.get("vehiclePicUrl")

#     @property
#     def entity_picture(self):
#         return self.native_value
