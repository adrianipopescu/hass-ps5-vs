from homeassistant.helpers.device_registry import DeviceInfo
from .const import DOMAIN


def ps5_device_info(coordinator) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, coordinator.host)},
        name="PlayStation 5",
        manufacturer="Sony Interactive Entertainment",
        model="PlayStation 5",
        configuration_url=f"http://{coordinator.host}:{coordinator.port}",
    )
