"""
Support for Navien Component.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/Navien/
"""
import asyncio
import datetime
import json
import hashlib
import logging
import os

import aiofiles
import httpx
import requests
import voluptuous as vol
import requests
from bs4 import BeautifulSoup
import re
import codecs
from datetime import timedelta
import homeassistant.helpers.config_validation as cv
from homeassistant.components.climate import PLATFORM_SCHEMA, ClimateEntity
from homeassistant.components.climate.const import (
    HVAC_MODE_HEAT, HVAC_MODE_OFF, HVAC_MODE_DRY, SUPPORT_TARGET_TEMPERATURE,
    SUPPORT_PRESET_MODE, SUPPORT_TARGET_TEMPERATURE_RANGE, HVAC_MODES)
from homeassistant.const import (
    TEMP_CELSIUS, ATTR_TEMPERATURE, CONF_TOKEN, CONF_DEVICE_ID)
from homeassistant.exceptions import PlatformNotReady
from homeassistant.util import Throttle

_LOGGER = logging.getLogger(__name__)

Navien_API_URL = 'https://igs.krb.co.kr/api'
DEFAULT_NAME = 'Navien'

MAX_TEMP = 45
MIN_TEMP = 10
HVAC_MODE_BATH = '목욕'
STATE_HEAT = '난방'
STATE_ONDOL = '온돌'
STATE_AWAY = '외출'
STATE_OFF = '종료'

BOILER_STATUS = {
    'deviceAlias': '경동 나비엔 보일러',
    'Date': f"{datetime.datetime.now()}",
    'mode': 'indoor',
    'switch': 'on',
    'currentTemperature': '0',
    'spaceheatingSetpoint': '0',
    'currentHotwaterTemperature': '0',
    'hotwaterSetpoint': '0',
    'floorheatingSetpoint': '0'
}


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up a Navien."""
    scriptpath = os.path.dirname(__file__)
    with open(scriptpath + "/commands.json", "r") as f:
        data = json.load(f)

    _LOGGER.debug("start navien_boiler :{0} {1} {2} ".format(config, discovery_info, data))

    device = SmartThingsApi(data)
    add_entities([Navien(device, hass)], True)


class SmartThingsApi:

    def __init__(self, data):
        """Initialize the Air Korea API.."""
        self.result = {}
        self.data = data
        self.token = data['token']
        self.deviceId = data['deviceId']
        self.headers = {
            'Authorization': 'Bearer {}'.format(self.token)
        }

    def send(self, cmd, args) -> bool:
        print("send : {0}  {1}  {2}".format(cmd, args, self.data))
        _LOGGER.debug("send : {0}  {1}  {2}".format(cmd, args, self.data))

        if cmd is None or args is None or self.data is None:
            return False

        try:

            if cmd == "switch" or cmd == "setThermostatMode":
                self.data[cmd]['arguments'] = [args]

            command = "{\"commands\": [" + json.dumps(self.data[cmd]) + "]}"
            print("command : " + command)
            _LOGGER.debug("command : " + command)

            SMARTTHINGS_API_URL = f'https://api.smartthings.com/v1/devices/{self.deviceId}/commands'

            response = requests.post(SMARTTHINGS_API_URL, timeout=10, headers=self.headers, data=command)

            print(" Call to Navien Boiler API {} ".format(response))
            _LOGGER.debug(" Call to Navien Boiler API {} ".format(response))

            if response.status_code != 200:
                print("error send command : {}".format(response))
                _LOGGER.error("error send command : {}".format(response))
                return False

        except Exception as ex:
            _LOGGER.error('Failed to send Navien Boiler API Error: %s', ex)
            print(" Failed to send Navien Boiler API Error: {} ".format(ex))
            raise
        return True

    def switch_on(self) -> None:
        print("switch_on : ")
        _LOGGER.debug("switch_on : ")

        self.send("switch","")

    def switch_off(self) -> None:
        print("switch_off : ")
        _LOGGER.debug("switch_off : ")

        self.setThermostatMode('OFF')

    def setCurrentSetpoint(self, temperature) -> None:
        print("setCurrentSetpoint :{}".format(temperature))
        _LOGGER.debug("setCurrentSetpoint : {}".format(temperature))
        self.send("setCurrentSetpoint", temperature)

    def setThermostatMode(self, mode) -> None:
        print("setThermostatMode : " + mode)
        _LOGGER.debug("setThermostatMode : " + mode)

        if mode == 'indoor' or mode == 'away' or mode == 'ondol' or mode == 'OFF':
            self.send("setThermostatMode", mode)
            BOILER_STATUS['mode'] = mode
        else:
            _LOGGER.error("Unsupported Thermostat Mode : " + mode)

    def ondol(self):
        self.setThermostatMode("ondol")

    def away(self):
        self.setThermostatMode("away")

    def indoor(self):
        self.setThermostatMode("indoor")

    def setThermostatSpaceHeatingSetpoint(self, temperature) -> None:
        print("setThermostatSpaceHeatingSetpoint : {}".format(temperature))
        _LOGGER.debug("setThermostatSpaceHeatingSetpoint : {}".format(temperature))
        BOILER_STATUS['spaceheatingSetpoint'] = temperature
        self.send("setThermostatSpaceHeatingSetpoint", temperature)

    def setThermostatFloorHeatingSetpoint(self, temperature) -> None:
        print("setThermostatFloorHeatingSetpoint : {}".format(temperature))
        _LOGGER.debug("setThermostatFloorHeatingSetpoint : {}".format(temperature))
        BOILER_STATUS['floorheatingSetpoint'] = temperature
        self.send("setThermostatFloorHeatingSetpoint", temperature)

    # unsupported method
    # def setCurrentHotwaterTemperature(self, temperature) -> None:
    #     print("setCurrentHotwaterTemperature : " + temperature)
    #     _LOGGER.debug("setCurrentHotwaterTemperature : " + temperature)
    #     BOILER_STATUS['currentHotwaterTemperature'] = temperature
    #     self.send("setCurrentHotwaterTemperature", temperature)

    def setThermostatHotwaterSetpoint(self, temperature) -> None:
        print("setThermostatHotwaterSetpoint : {}".format(temperature))
        _LOGGER.debug("setThermostatHotwaterSetpoint : {}".format(temperature))
        BOILER_STATUS['hotwaterSetpoint'] = temperature

        self.send("setThermostatHotwaterSetpoint", temperature)

    def update(self):
        """Update function for updating api information."""
        try:
            SMARTTHINGS_API_URL = 'https://graph-ap02-apnortheast2.api.smartthings.com/device/{0}/events'.format(self.deviceId)

            response = requests.get(SMARTTHINGS_API_URL, timeout=10, headers=self.headers)

            if response.status_code == 200:

                soup = BeautifulSoup(response.text, 'html.parser')
                event_table = soup.find_all('td')

                title = ['Date', 'Source', 'Type', 'Name', 'Value', 'User', 'Displayed Text']
                json_list = []
                appendString = dict()

                index = 0
                for tr in event_table:
                    cleantext = re.sub(re.compile('<.*?>|&([a-z0-9]+|#[0-9]{1,6}|#x[0-9a-f]{1,6});'), '',
                                       tr.text).strip()
                    appendString[title[index]] = cleantext.split('\n')[0]
                    index = index + 1
                    if index % len(title) == 0:
                        index = 0
                        json_list.append(appendString)
                        appendString = dict()

                _LOGGER.debug('C : type %s, %s', type(json_list), json_list)
                print('C : type %s, %s', type(json_list), json_list)

                for key in BOILER_STATUS.keys():
                    for index, value in enumerate(json_list):
                        # print(" index {0} value {1} ".format(index, value['Name']))
                        if key == value['Name'] and value['Value'] != '0':
                            _LOGGER.debug(" Value : {} ".format(value['Value']))
                            BOILER_STATUS[key] = value['Value']
                            break

                self.result = BOILER_STATUS
                _LOGGER.debug('JSON Response : type %s, %s', type(BOILER_STATUS), BOILER_STATUS)
                print('JSON Response: type %s, %s', type(BOILER_STATUS), BOILER_STATUS)

            else:
                _LOGGER.debug(f'Error Code: {response.status_code}')
                print(f'Error Code: {response.status_code}')

        except Exception as ex:
            _LOGGER.error('Failed to update Navien Boiler API status Error: %s', ex)
            print(" Failed to update Navien Boiler API status Error:  ")
            raise


class Navien(ClimateEntity):

    def __init__(self, device, hass):
        """Initialize the thermostat."""
        self._hass = hass
        self._name = '경동 나비엔 보일러'
        self.device = device
        self.node_id = 'navien_climate'
        self.result = {}

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self.node_id

    @property
    def name(self):
        """Return the name of the entity."""
        return self._name

    @property
    def device_info(self):
        """Return information about the device."""
        return {
            'node_id': self.node_id,
            'device_alias': self._name
        }

    @property
    def device_state_attributes(self):
        """Return the state attributes of the device."""
        return {
            'node_id': self.node_id,
            'device_mode': BOILER_STATUS['mode']
        }

    @property
    def supported_features(self):
        """Return the list of supported features."""
        features = 0
        if self.is_on:
            features |= SUPPORT_PRESET_MODE # 프리셋 모드
        if BOILER_STATUS['mode'] != 'OFF':
            features |= SUPPORT_TARGET_TEMPERATURE # 온도 조절 모드로 되어 있지 않으면 un support set_temperature 오류 발생
        return features

    @property
    def available(self):
        """Return True if entity is available."""
        return BOILER_STATUS['switch'] == 'on'

    @property
    def temperature_unit(self):
        """Return the unit of measurement which this thermostat uses."""
        return TEMP_CELSIUS

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return 1

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return MIN_TEMP

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return MAX_TEMP

    @property
    def is_on(self):
        """Return true if heater is on."""
        return BOILER_STATUS['switch'] == 'on'
        # return True

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return int(BOILER_STATUS['currentTemperature'])

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        operation_mode = BOILER_STATUS['mode']
        if operation_mode == 'indoor':
            return int(BOILER_STATUS['spaceheatingSetpoint'])
        elif operation_mode == 'away':
            return int(BOILER_STATUS['currentHotwaterTemperature'])
        elif operation_mode == 'ondol':
            return int(BOILER_STATUS['floorheatingSetpoint'])
        else:
            return int(BOILER_STATUS['hotwaterSetpoint'])


    @property
    def hvac_mode(self):
        """Return hvac operation ie. heat, cool mode.
        Need to be one of HVAC_MODE_*.
        """
        if self.is_on:
            return HVAC_MODE_HEAT
        return HVAC_MODE_OFF

    @property
    def hvac_modes(self):
        """Return the list of available hvac operation modes.
        Need to be a subset of HVAC_MODES.
        """
        return [HVAC_MODE_OFF, HVAC_MODE_HEAT]

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        _LOGGER.debug(f" async_set_temperature >>>>>>>>>>>> {kwargs}")
        if self.is_on is False:
            self.device.switch_on()
        temperature = kwargs.get(ATTR_TEMPERATURE)
        _LOGGER.debug(f" temperature >>>>>>>>>>>> {temperature}")

        if temperature is None:
            return None

        # todo 난방 모드에 따른 온도 변경
        operation_mode = BOILER_STATUS['mode']
        if operation_mode == 'indoor':
            BOILER_STATUS['spaceheatingSetpoint'] = temperature
            self.device.setThermostatSpaceHeatingSetpoint(temperature)
        elif operation_mode == 'away':
            BOILER_STATUS['hotwaterSetpoint'] = temperature
            self.device.setThermostatHotwaterSetpoint(temperature)
        elif operation_mode == 'ondol':
            BOILER_STATUS['floorheatingSetpoint'] = temperature
            self.device.setThermostatFloorHeatingSetpoint(temperature)
        self.device.setCurrentSetpoint(temperature)

    @property
    def preset_modes(self):
        """Return a list of available preset modes.
        Requires SUPPORT_PRESET_MODE.
        """
        return [STATE_HEAT, STATE_ONDOL, STATE_AWAY, STATE_OFF]

    @property
    def preset_mode(self):
        """Return the current preset mode, e.g., home, away, temp.
        Requires SUPPORT_PRESET_MODE.
        """
        operation_mode = BOILER_STATUS['mode']
        if operation_mode == 'indoor':
            return STATE_HEAT
        elif operation_mode == 'away':
            return STATE_AWAY
        elif operation_mode == 'ondol':
            return STATE_ONDOL
        elif operation_mode == 'OFF':
            return STATE_OFF
        else:
            return STATE_AWAY

    def set_preset_mode(self, preset_mode):
        _LOGGER.debug("preset_mode >>>> " + preset_mode)
        """Set new preset mode."""
        if self.is_on is False:
            self.device.switch_on()
            BOILER_STATUS['switch'] = 'on'
        if preset_mode == STATE_HEAT:
            self.device.indoor()
            BOILER_STATUS['mode'] = 'indoor'
        # elif preset_mode == STATE_BATH:
        #     self.device.away()
        #     BOILER_STATUS['mode'] = 'away'
        elif preset_mode == STATE_ONDOL:
            self.device.ondol()
            BOILER_STATUS['mode'] = 'ondol'
        elif preset_mode == STATE_AWAY:
            self.device.away()
            BOILER_STATUS['mode'] = 'away'
        elif preset_mode == STATE_OFF:
            self.device.switch_off()
            BOILER_STATUS['mode'] = 'OFF'
        else:
            _LOGGER.error("Unrecognized operation mode: %s", preset_mode)

    def set_hvac_mode(self, hvac_mode):
        _LOGGER.debug("hvac_mode >>>> " + hvac_mode)
        """Set new target hvac mode."""
        if hvac_mode == HVAC_MODE_HEAT:
            self.device.switch_on()
            BOILER_STATUS['switch'] = 'on'
            BOILER_STATUS['mode'] = 'indoor'
        elif hvac_mode == HVAC_MODE_OFF:
            self.device.switch_off()
            BOILER_STATUS['mode'] = 'OFF'

    def update(self):
        self.result = self.device.update()

if __name__ == '__main__':
    """example_integration sensor 
    platform setup"""
    print(" start navien boiler ")
    with open("commands.json", "r") as f:
        data = json.load(f)
    token = data['token']
    deviceId = data['deviceId']
    print("token : {}".format(token))
    print("deviceId : {}".format(deviceId))
    real_time_api = SmartThingsApi(data)
    real_time_api.away()
    real_time_api.setThermostatHotwaterSetpoint("30")
    print("{}".format(BOILER_STATUS))

