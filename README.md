# tuya-homeassistant

**THIS WILL ONLY WORK FOR SWITCHES. WILL NOT WORK WITH DIMMERS.**

This is a simple platform to control **SOME** switch devices that use the Tuya cloud for control.

It uses the pytuya library (https://github.com/clach04/python-tuya) to directly control the switch device. (No need to install as Home Assistant automatically installs it.)

Most switch devices that use the Tuya cloud should work. If port 6668 is open on the switch device then it will work.

See here for how to find localKey and devId: http://seandev.org/tuyainst

To use, copy tuya.py to "<home assistant config dir>/custom_components/switch" and add config below to configuration.yaml

Config Example:
```
switch:
  - platform: tuya
    # if host is 0.0.0.0,
    # then module will find out ip address for the given device id
    host: xxx.xxx.xxx.xxx
    local_key: xxxxxxxxxxxxxxxx
    device_id: xxxxxxxxxxxxxxxxxxxx
    switches:
      switch1:
        friendly_name: Switch 1
        # id can be omitted in case of single switch on a single device
        id: 1
```

Multiple switches on a single device:
```
switch:
  - platform: tuya
    # if host is 0.0.0.0,
    # then module will find out ip address for the given device id
    host: xxx.xxx.xxx.xxx
    local_key: xxxxxxxxxxxxxxxx
    device_id: xxxxxxxxxxxxxxxxxxxx
    switches:
      switch1:
        friendly_name: Switch 1
        id: 1
      switch2:
        friendly_name: Switch 2
        id: 2
      switch3:
        friendly_name: Switch 3
        id: 3
      switch4:
        friendly_name: Switch 4
        id: 4
```
