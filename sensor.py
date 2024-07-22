import datetime
import json
import logging
import os
from typing import Dict, Any

import requests
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
import sys
import requests
from bs4 import BeautifulSoup
import re
import codecs
from datetime import timedelta

from homeassistant.components.climate import HVAC_MODE_HEAT, HVAC_MODE_OFF
from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.const import (CONF_NAME, CONF_MONITORED_CONDITIONS, TEMP_CELSIUS)
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle

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

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """example_integration sensor platform setup"""
    _LOGGER.info(" start navien boiler ")

    scriptpath = os.path.dirname(__file__)
    with open(scriptpath + "/commands.json", "r") as f:
        data = json.load(f)

    _LOGGER.debug("start navien_boiler :{0} {1} {2} ".format(config, discovery_info, data))

    entitie = []
    for key in BOILER_STATUS.keys():
        api = SmartThingsApi(key, data)
        entitie += [Sensor(hass, api, key)]
    add_entities(entitie)


class SmartThingsApi:

    def __init__(self, key, data):
        """Initialize the Air Korea API.."""
        self.result = {}
        self._key = key
        self.data = data
        self.token = data['token']
        self.deviceId = data['deviceId']
        self.headers = {
            'Authorization': 'Bearer {}'.format(self.token)
        }

    def update(self):
        """Update function for updating api information."""
        try:
            SMARTTHINGS_API_URL = f'https://api.smartthings.com/v1/devices/{self.deviceId}/status'

            response = requests.get(SMARTTHINGS_API_URL, timeout=10, headers=self.headers)

            if response.status_code == 200:

                response_json = response.json()

                BOILER_STATUS['switch'] = response_json['components']['main'][
                    'switch']['switch']['value']

                BOILER_STATUS['currentTemperature'] = response_json['components']['main'][
                    'voiceaddress44089.currenttemperature']['currentTemperature']['value']

                BOILER_STATUS['currentHotwaterTemperature'] = response_json['components']['HotwaterTemperatureSetting'][
                    'voiceaddress44089.currenthotwatertemperature']['currentHotwaterTemperature']['value']

                BOILER_STATUS['hotwaterSetpoint'] = response_json['components']['HotwaterTemperatureSetting'][
                    'voiceaddress44089.thermostatHotwaterSetpoint']['hotwaterSetpoint']['value']

                BOILER_STATUS['spaceheatingSetpoint'] = response_json['components']['RoomTemperatureSetting'][
                    'voiceaddress44089.thermostatSpaceHeatingSetpoint']['spaceheatingSetpoint']['value']

                BOILER_STATUS['floorheatingSetpoint'] = response_json['components']['RoomTemperatureSetting'][
                    'voiceaddress44089.thermostatFloorHeatingSetpoint']['floorheatingSetpoint']['value']

                BOILER_STATUS['mode'] = response_json['components']['RoomTemperatureSetting'][
                    'voiceaddress44089.thermostatMode']['mode']['value']

                self.result = BOILER_STATUS

                print('JSON Response: type %s, %s', type(self.result), self.result)

            else:
                _LOGGER.debug(f'Error Code: {response.status_code}')
                print(f'Error Code: {response.status_code}')

        except Exception as ex:
            _LOGGER.error('Failed to update Navien Boiler API status Error: %s', ex)
            print(" Failed to update Navien Boiler API status Error:  ")
            raise


class Sensor(SensorEntity):
    """sensor platform class"""
    def __init__(self, hass, api, key):
        """sensor init"""
        self._state = None
        self._hass = hass
        self._api = api
        self._key = key
        self.var_icon = 'mdi:bathtub'

    async def async_update(self):
        """Retrieve latest state."""
        await self._hass.async_add_executor_job(self.update)

    def update(self):
        """sensor update"""
        _LOGGER.debug(' update !! ')

        self._api.update()
        if self._api.result is None:
            _LOGGER.error(' not updated !! API is None ')
            return

        self._state = self._api.result[self._key]
        _LOGGER.debug(f' {self._key} : {self._state}')

    @property
    def name(self):
        """return sensor name"""
        return "navien_"+self._key

    @property
    def state(self):
        """return sensor state"""
        return self._state

    @property
    def unique_id(self):
        """Return a unique ID."""
        return "navien_"+self._key

    @property
    def device_info(self):
        """Return information about the device."""
        return {
            'node_id': "navien_"+self._key,
            "name": BOILER_STATUS['deviceAlias'],
            "DeviceEntryType": "service"
        }

    @property
    def device_state_attributes(self):
        """Return the state attributes of the device."""
        return BOILER_STATUS

    @property
    def available(self):
        """Return True if entity is available."""
        if BOILER_STATUS['switch'] == 'off':
            return False
        return True

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        if BOILER_STATUS['mode'] == 'indoor':
            return 'mdi:home-thermometer-outline'
        elif BOILER_STATUS['mode'] == 'ondol':
            return 'mdi:heating-coil'
        elif BOILER_STATUS['mode'] == 'away':
            return 'mdi:exit-run'
        else:
            return 'mdi:bathtub'

    @property
    def state_class(self):
        if self._key == 'mode' or self._key == 'switch' or self._key == 'deviceAlias' or self._key == 'Date':
            return None
        else:
            return 'measurement'

    @property
    def unit_of_measurement(self):
        if self._key == 'mode' or self._key == 'switch' or self._key == 'deviceAlias' or self._key == 'Date':
            return None
        else:
            return TEMP_CELSIUS

    @property
    def device_class(self):
        if self._key == 'mode' or self._key == 'switch' or self._key == 'deviceAlias':
            return None
        elif self._key == 'Date':
            return 'timestamp'
        else:
            return 'temperature'


if __name__ == '__main__':
    """example_integration sensor platform setup"""
    print(" start navien boiler ")

    scriptpath = os.path.dirname(__file__)
    with open(scriptpath + "/commands.json", "r") as f:
        data = json.load(f)

    real_time_api = SmartThingsApi('currentTemperature', data)
    real_time_api.update()
    real_time_api = SmartThingsApi('spaceheatingSetpoint', data)
    real_time_api.update()
    real_time_api = SmartThingsApi('currentHotwaterTemperature', data)
    real_time_api.update()
    real_time_api = SmartThingsApi('hotwaterSetpoint', data)
    real_time_api.update()
    real_time_api = SmartThingsApi('floorheatingSetpoint', data)
    real_time_api.update()
    real_time_api = SmartThingsApi('Date', data)
    real_time_api.update()
    print(real_time_api.result)
    # add_entities([Sensor(real_time_api)])
