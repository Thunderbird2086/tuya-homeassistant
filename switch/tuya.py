"""
Simple platform to control **SOME** Tuya switch devices.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/switch.tuya/
"""
import voluptuous as vol
from homeassistant.components.switch import SwitchDevice, PLATFORM_SCHEMA
from homeassistant.const import (CONF_NAME, CONF_HOST, CONF_ID, CONF_SWITCHES,
                                 CONF_FRIENDLY_NAME)
import homeassistant.helpers.config_validation as cv
import json
import logging
import socket
from time import time
from threading import Lock

_LOGGER = logging.getLogger(__name__)

REQUIREMENTS = ['pytuya==7.0.2']

CONF_DEVICE_ID = 'device_id'
CONF_LOCAL_KEY = 'local_key'

DEFAULT_ID = '1'

SWITCH_SCHEMA = vol.Schema({
    vol.Optional(CONF_ID, default=DEFAULT_ID): cv.string,
    vol.Optional(CONF_FRIENDLY_NAME): cv.string,
})


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME): cv.string,
    vol.Optional(CONF_HOST): cv.string,
    vol.Required(CONF_DEVICE_ID): cv.string,
    vol.Required(CONF_LOCAL_KEY): cv.string,
    vol.Optional(CONF_ID, default=DEFAULT_ID): cv.string,
    vol.Optional(CONF_SWITCHES, default={}):
        vol.Schema({cv.slug: SWITCH_SCHEMA}),
})


_ALL_IP = '0.0.0.0'
_UDP_PORT = 6666
_DEVICE_CACHE = {}


def get_host(device_id, refresh=False):
    """Get host IP address from device_id"""
    global _DEVICE_CACHE
    ip_addr = _DEVICE_CACHE.get(device_id)
    if ip_addr and not refresh:
        return ip_addr

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((_ALL_IP, _UDP_PORT))

    cnt = 0
    # added counter in case of typo in device id
    while (not ip_addr and (cnt < 10)):
        data, _ = sock.recvfrom(512)
        str_data = data[20:-8]
        if not isinstance(str_data, str):
            str_data = str_data.decode()
        info = json.loads(str_data)
        gw_id = info.get('gwId')
        a_ip_addr = info.get('ip')
        if gw_id not in _DEVICE_CACHE:
            _DEVICE_CACHE[gw_id] = a_ip_addr
        else:
            if _DEVICE_CACHE[gw_id] != a_ip_addr:
                _DEVICE_CACHE[gw_id] = a_ip_addr

        if gw_id == device_id:
            ip_addr = a_ip_addr

        cnt += 1

    return ip_addr


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up of the Tuya switch."""
    import pytuya

    devices = config.get(CONF_SWITCHES)
    switches = []

    host = config.get(CONF_HOST)
    device_id = config.get(CONF_DEVICE_ID)
    if host in (_ALL_IP, None):
        host = get_host(device_id)

    _LOGGER.debug("device_id=(%s), host=(%s)", device_id, host)
    outlet_device = TuyaCache(
        pytuya.OutletDevice(
            device_id,
            host,
            config.get(CONF_LOCAL_KEY)
        )
    )

    for object_id, device_config in devices.items():
        switches.append(
            TuyaDevice(
                outlet_device,
                device_config.get(CONF_FRIENDLY_NAME, object_id),
                device_config.get(CONF_ID),
            )
        )

    name = config.get(CONF_NAME)
    if name:
        switches.append(
            TuyaDevice(
                outlet_device,
                name,
                config.get(CONF_ID)
            )
        )

    add_devices(switches)


class TuyaCache:
    """Cache wrapper for pytuya.OutletDevice"""

    def __init__(self, device):
        """Initialize the cache."""
        self._cached_status = ''
        self._cached_status_time = 0
        self._device = device
        self._lock = Lock()

    def __get_status(self):
        for i in range(3):
            self.get_host()
            try:
                status = self._device.status()
                return status
            except socket.timeout:
                if i+1 == 3:
                    self._device.address = _ALL_IP
                    _DEVICE_CACHE.pop(self._device.id)
                    raise ConnectionError("Failed to update status.")
            except ConnectionError:
                if i+1 == 3:
                    self._device.address = _ALL_IP
                    _DEVICE_CACHE.pop(self._device.id)
                    raise ConnectionError("Failed to update status.")

    def has_host(self):
        """check if host is valid"""
        return self._device.address not in (_ALL_IP, None)

    def get_host(self, refresh=False):
        """get host"""
        if refresh or not self.has_host():
            self._device.address = get_host(self._device.id, refresh)
            _LOGGER.debug("device_id=(%s), host=(%s)",
                          self._device.id, self._device.address)

    def set_status(self, state, switchid):
        """Change the Tuya switch status and clear the cache."""
        self._cached_status = ''
        self._cached_status_time = 0
        self.get_host()
        return self._device.set_status(state, switchid)

    def status(self):
        """Get state of Tuya switch and cache the results."""
        self._lock.acquire()
        try:
            now = time()
            if not self._cached_status or now - self._cached_status_time > 20:
                self._cached_status = self.__get_status()
                self._cached_status_time = time()
            return self._cached_status
        finally:
            self._lock.release()


class TuyaDevice(SwitchDevice):
    """Representation of a Tuya switch."""

    def __init__(self, device, name, switchid):
        """Initialize the Tuya switch."""
        self._device = device
        self._name = name
        self._state = False
        self._switchid = switchid

    @property
    def name(self):
        """Get name of Tuya switch."""
        return self._name

    @property
    def is_on(self):
        """Check if Tuya switch is on."""
        return self._state

    def turn_on(self, **kwargs):
        """Turn Tuya switch on."""
        # self._device.get_host()
        self._device.set_status(True, self._switchid)

    def turn_off(self, **kwargs):
        """Turn Tuya switch off."""
        # self._device.get_host()
        self._device.set_status(False, self._switchid)

    def update(self):
        """Get state of Tuya switch."""
        if self._device.has_host():
            try:
                status = self._device.status()
                dps = status.get('dps')
                if dps is not None:
                    self._state = dps[self._switchid]
            except OSError as e:
                _LOGGER.debug(e)
                # _LOGGER.error("failed to get status for device=(%s)",
                #              self._device.id)
                self._device.get_host(True)
