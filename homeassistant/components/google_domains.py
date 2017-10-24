"""
Integrate with Google Domains.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/google_domains/
"""
import aiohttp
import async_timeout
import asyncio
import logging
from datetime import timedelta

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.const import (
    CONF_DOMAIN, CONF_PASSWORD, CONF_TIMEOUT, CONF_USERNAME)

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'google_domains'

INTERVAL = timedelta(minutes=5)

DEFAULT_TIMEOUT = 10

UPDATE_URL = 'https://{}:{}@domains.google.com/nic/update'

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_DOMAIN): cv.string,
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): cv.positive_int,
    })
}, extra=vol.ALLOW_EXTRA)


@asyncio.coroutine
def async_setup(hass, config):
    """Initialize the Google Domains component."""
    domain = config[DOMAIN].get(CONF_DOMAIN)
    user = config[DOMAIN].get(CONF_USERNAME)
    password = config[DOMAIN].get(CONF_PASSWORD)
    timeout = config[DOMAIN].get(CONF_TIMEOUT)

    session = hass.helpers.aiohttp_client.async_get_clientsession()

    result = yield from _update_google_domains(
        hass, session, domain, user, password, timeout)

    if not result:
        return False

    @asyncio.coroutine
    def update_domain_interval(now):
        """Update the Google Domains entry."""
        yield from _update_google_domains(
            hass, session, domain, user, password, timeout)

    hass.helpers.event.async_track_time_interval(
        update_domain_interval, INTERVAL)

    return result


@asyncio.coroutine
def _update_google_domains(hass, session, domain, user, password, timeout):
    """Update Google Domains."""
    url = UPDATE_URL.format(user, password)

    params = {
        'hostname': domain
    }

    try:
        with async_timeout.timeout(timeout, loop=hass.loop):
            resp = yield from session.get(url, params=params)
            body = yield from resp.text()

            if body.startswith('good') or body.startswith('nochg'):
                return True

            _LOGGER.warning('Updating Google Domains failed: %s => %s',
                            domain, body)

    except aiohttp.ClientError:
        _LOGGER.warning("Can't connect to Google Domains API")

    except asyncio.TimeoutError:
        _LOGGER.warning("Timeout from Google Domains API for domain: %s",
                        domain)

    return False
