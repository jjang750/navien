import datetime
import json
import logging
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

token = 'a81c7152-87a0-4f2f-877b-19f4b20936f6'
deviceId = 'c9fbd5c5-63ab-4e9c-9d7d-5c72b599a794'

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
    entitie = []
    for key in BOILER_STATUS.keys():
        api = SmartThingsApi(key)
        entitie += [Sensor(hass, api, key)]
    add_entities(entitie)


class SmartThingsApi:
    headers = {
        'Authorization': 'Bearer {}'.format(token)
    }

    def __init__(self, key):
        """Initialize the Air Korea API.."""
        self.result = {}
        self._key = key

    def update(self):
        """Update function for updating api information."""
        try:
            SMARTTHINGS_API_URL = 'https://graph-ap02-apnortheast2.api.smartthings.com/device/{0}/events'.format(deviceId)

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

                # for key in BOILER_STATUS.keys():
                _LOGGER.debug(" key {0} ".format(self._key))
                for index, value in enumerate(json_list):
                    # print(" index {0} value {1} ".format(index, value['Name']))
                    if self._key == value['Name'] and value['Value'] != '0':
                        _LOGGER.debug(" Value : {} ".format(value['Value']))
                        BOILER_STATUS[self._key] = value['Value']
                        break

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
    real_time_api = SmartThingsApi('currentTemperature')
    real_time_api.update()
    real_time_api = SmartThingsApi('spaceheatingSetpoint')
    real_time_api.update()
    real_time_api = SmartThingsApi('currentHotwaterTemperature')
    real_time_api.update()
    real_time_api = SmartThingsApi('hotwaterSetpoint')
    real_time_api.update()
    real_time_api = SmartThingsApi('floorheatingSetpoint')
    real_time_api.update()
    real_time_api = SmartThingsApi('Date')
    real_time_api.update()
    print(real_time_api.result)
    # add_entities([Sensor(real_time_api)])