# coding: utf-8
"""
Description: Infoblox Python REST Client
    Function: To facilitate connections to Infoblox WAPI REST API
"""

import datetime
import json
import logging
import timeit

import httpx

from .errors import InfobloxClientError


class InfobloxClient(object):
    """
    Connection class that simplifies and unifies all access to Infoblox WAPI API.
    """
    def __init__(self, server, username, password, version, candidate=None, ssl_check=False, verbose=False, simulation=False, add_audit=False):
        """
        Standard constructor.

        :param server: server BASE URL e.g. https://my-gridmaster.com:8080
        :param username: Infoblox username
        :param password: Infoblox password
        :param version: WAPI version to be used
        :param candidate: RO candidate server URL
        :param ssl_check: whether to perform SSL validation or not
        :param verbose: enable debugging (1 for INFO, 2 for DEBUG)
        :param add_audit: add audit log to this record (Requires EA ChangeControl to be on and objects used)
        """
        self._reply = None
        self._error = None
        self._error_code = None
        self._record = None
        self._params = None
        self.rw_wapi_url = None
        self.ro_wapi_url = None

        self._setup_logging(verbose)

        self.server = server
        self.candidate = candidate if candidate else self.server
        self.username = username
        self.password = password
        self.version = version
        self.simulation = simulation
        self.add_audit = add_audit

        # set up HTTP/S session
        self.session = httpx.Client(verify=ssl_check, transport=httpx.HTTPTransport(retries=3))
        self.headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}

        # prepare the WAPI URL
        if self.server[-1:] == '/':
            self.server = self.server[:-1]
        if self.candidate:
            if self.candidate[-1:] == '/':
                self.candidate = self.candidate[:-1]
        else:
            self.candidate = self.server

        if self.version[:1].lower() == 'v':
            self.version = self.version[1:]
        self.rw_wapi_url = self.server + '/wapi/v' + self.version
        self.ro_wapi_url = self.candidate + '/wapi/v' + self.version
        self.session.auth = httpx.BasicAuth(username=self.username, password=self.password)
        self.logger.debug('Infoblox Load Complete, loglevel set to %s', logging.getLevelName(self.logger.getEffectiveLevel()))

    def _setup_logging(self, verbose=False):
        logging.basicConfig(level=logging.ERROR)
        self.logger = logging.getLogger('pyinfoblox')
        self.logger.setLevel(logging.ERROR)
        self.debug = verbose if verbose else 0
        if self.debug is True:
            self.logger.setLevel(logging.WARNING)
            self.logger.warning('Setting level to WARNING')
        if self.debug == 2:
            self.logger.setLevel(logging.INFO)
            self.logger.info('Setting level to INFO')
        elif self.debug > 2:
            self.logger.setLevel(logging.DEBUG)
            self.logger.debug('Setting level to DEBUG')

    def __getattr__(self, item):
        """
        Overload of getattr method to handle HTTP method calls

        :param item: a self method
        :return: a wrapped query function or None
        """
        opname = item.split('_')

        def func(*args, **kwargs):
            fragments = None
            if isinstance(args, (list, tuple)):
                fragments = [x for x in opname[1:] if x]
                fragments.extend([x for x in args if x])
            elif isinstance(args, str):
                fragments = [args]

            if not fragments:
                return self.query('', opname[0], **kwargs)

            return self.query('/'.join(fragments), opname[0], **kwargs)

        if opname[0] in ['get', 'post', 'put', 'delete']:
            return func
        return None

    def timeit(self, method, *args, **kwargs):
        """
        Method for testing timing of request

        :param method:
        :return: cnt
        :rtype: float|int
        """
        tic = timeit.default_timer()
        m = getattr(self, method)
        res = m(*args, **kwargs)
        self.logger.debug(res)
        toc = timeit.default_timer()
        cnt = toc - tic  # elapsed time in seconds
        return cnt

    @property
    def error_msg(self):
        """ Method for storing and returning error messages """
        return self._error

    @property
    def error_code(self):
        return self._error_code

    @property
    def reply_msg(self):
        """ Method for storing and returning reply messages """
        return self._reply

    def _login(self):
        if not self.session:
            self.session = httpx.Client()
        if not self.session.auth:
            self.session.auth = httpx.BasicAuth(username=self.username, password=self.password)
        result = self.query(resource='?_schema')
        return result

    def _parse_error(self, response):
        self.logger.debug('Parsing error response and raising exception')
        if response:
            if not hasattr(response, 'status_code'):
                self._error = 'Invalid response object, no status code is this a bug?'
                self._error_code = 410
            else:
                self._error = response.text
                self._error_code = response.status_code
        else:
            self._error = 'Invalid response object, is this a bug?'
            self._error_code = 500
        raise InfobloxClientError(self.__class__.__name__, self.error_code, self.error_msg)

    def _parse_response(self, response):
        if response and hasattr(response, 'status_code'):
            if 200 <= response.status_code <= 299:
                reply = dict(status_code=response.status_code, data=response.json())
                return reply
        self.logger.debug('Response is not good, parsing error...')
        return self._parse_error(response)

    def query(self, resource, method='get', payload=''):
        """
        Wrapper method to join all the REST stuff in a single place.

        self._reply holds the response of a successful WAPI call.
        self._error holds the error message of a failed WAPI call.

        :param resource: string containing the Infoblox object name. e.g. host:ipv4address
        :type resource: str
        :param method: string containing either 'get', 'post', 'put' or 'delete'. Defaults to 'get'.
        :type method: str
        :param payload: Python dictionary that gets send as a json string.
        :type payload: dict
        :return: Result dictionary on success; False on error.
        :rtype: dict
        """
        self._error = None
        resource = resource.strip()
        method = method.strip().lower()
        if resource:
            url = self.rw_wapi_url + resource
        else:
            return False

        self.logger.debug(url)
        if payload:
            self.logger.debug('Payload: %s', payload)

        if self.simulation:
            return dict(status_code=200, data=payload, ok=1)

        # Infoblox doesn't return the supported http verbs in the OPTIONS call thus setting them here.
        http_verbs = ['get', 'post', 'put', 'delete']
        if method not in http_verbs:
            method = 'get'
        start_time = datetime.datetime.now()
        try:
            if method == 'get':
                url = self.ro_wapi_url + resource
                self._reply = self.session.get(url, timeout=httpx.Timeout(10.0, connect=60.0))
            elif method == 'post':
                self._reply = self.session.post(url, json=json.dumps(payload), headers=self.headers, timeout=httpx.Timeout(10.0, connect=30.0))
            elif method == 'put':
                self._reply = self.session.put(url, json=json.dumps(payload), headers=self.headers, timeout=httpx.Timeout(10.0, connect=30.0))
            elif method == 'delete':
                self._reply = self.session.delete(url, timeout=httpx.Timeout(10.0, connect=30.0))
        except httpx.HTTPError as e:
            self._reply.raise_for_status()
            if hasattr(e.request, 'status_code'):
                raise InfobloxClientError(self.__class__.__name__, e.request.status_code, str(e))
            else:
                raise InfobloxClientError(self.__class__.__name__, 503, str(e))

        completed = datetime.datetime.now()
        duration = completed - start_time
        minutes, seconds = divmod(duration.total_seconds(), 60)
        self.logger.warning(f'Request Complete, Request time: {int(minutes)} minutes, {seconds:.2f} seconds')

        # Validate response
        if self._reply:
            return self._parse_response(self._reply)
        else:
            self._error = "Infoblox Server Error: %s" % self._reply.text
            self._error_code = self._reply.status_code
            raise InfobloxClientError(self.__class__.__name__, self.error_code, self.error_msg)

    def parse_result_data(self, data):
        if data is None:
            self._error = "Infoblox Server Error: Data Missing"
            self._error_code = 400
            raise InfobloxClientError(self.__class__.__name__, self.error_code, self.error_msg)

        if not isinstance(data, list):
            logging.error(data)
            self._error = "Infoblox Server Error: Invalid Record Response: Not List"
            self._error_code = 410
            raise InfobloxClientError(self.__class__.__name__, self.error_code, self.error_msg)

        if len(data) != 1:
            self._error = "Infoblox Server Error: Record Not Found"
            self._error_code = 404
            raise InfobloxClientError(self.__class__.__name__,  self.error_code, self.error_msg)

        if '_ref' not in data[0]:
            self._error = "Infoblox Server Error: Record reference not returned"
            self._error_code = 412
            raise InfobloxClientError(self.__class__.__name__,  self.error_code, self.error_msg)

        return data[0].get('_ref', None)

    def create_audit(self, href, user):
        """
        This method adds am audit point

        :param href: URL for puts (includes fields so that PUT does not overwrite existing data
        :param user: username that is performing the action
        :return: True on success
        :rtype: dict
        """
        timestamp = f"Infoblox Audit Entry: Changed by {user} on {datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')}"
        response = self.query(href)
        if response and isinstance(response, dict):
            if 'status_code' in response and 200 <= response.get('status_code') <= 299:
                self.logger.debug('Found record via supplied ref: %s', href)
                if 'data' in response and isinstance(response.get('data'), dict):
                    self.logger.debug('Found data key in record and it is a dict')
                    payload = response.get('data')
                    new_ref = payload.get('_ref')
                    del payload['_ref']
                    payload['extattrs']['ChangeControl'] = dict(value=str(timestamp))
                    response = self.query(resource=new_ref, payload=payload, method='PUT')
                    if response and isinstance(response, dict):
                        if 'status_code' in response and 200 <= response.get('status_code') <= 299:
                            self.logger.debug('The update was good')
                            return True
                        else:
                            self.logger.error('client audit response is invalid: %s', response)
                            raise InfobloxClientError(self.__class__.__name__, 500, 'response is not valid: %s' % response)
                    else:
                        self.logger.error('client audit response is not a "dict": %s', response)
                        raise InfobloxClientError(self.__class__.__name__,  500, 'response is not a "dict": %s' % response)
                else:
                    self.logger.debug('data is %s', response)
            else:
                self.logger.error('client response is invalid: %s', response)
                raise InfobloxClientError(self.__class__.__name__, 500, 'response is not valid: %s' % response)
        else:
            self.logger.error('client response is not a "dict": %s', response)
            raise InfobloxClientError(self.__class__.__name__, 500, 'response is not a "dict": %s' % response)
        return False

    def search(self, item, value, regex=False):
        """
        Search method allowing searching for data items:

        eg: result = client.search('mac_address', 'xx:xx:xx:xx:xx:xx') - matches whole mac address

        eg: result = client.search('mac_address', 'xx:xx:xx', True) - searches for REGEX matches

        :param item: item to search for
        :param value: value to match against
        :param regex: whether to use regex
        :return:
        """
        match = '='
        if regex:
            match = '~='
        ref = 'search?{0}{1}{2}'.format(item, match, value)
        response = self.query(ref)
        if response and isinstance(response, dict):
            if 'status_code' in response and 200 <= response.get('status_code') <= 299:
                if 'data' in response and isinstance(response.get('data'), dict):
                    self.logger.debug('Found data key in record and it is a dict')
                    return response.get('data')
                else:
                    self.logger.debug('data is %s', response)
            else:
                self.logger.error('client response is invalid: %s', response)
                raise InfobloxClientError(self.__class__.__name__, 500, 'response is not valid: %s' % response)
        else:
            self.logger.error('client response is not a "dict": %s', response)
            raise InfobloxClientError(self.__class__.__name__, 500, 'response is not a "dict": %s' % response)
        return False


class InfobloxDummyClient(object):
    def __init__(self, verbose=False):
        logging.basicConfig(level=logging.ERROR)
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.ERROR)
        self.debug = verbose if verbose else 0
        if self.debug is True:
            self.logger.setLevel(logging.WARNING)
            self.logger.warning('Setting level to WARNING')
        if self.debug == 2:
            self.logger.setLevel(logging.INFO)
            self.logger.info('Setting level to INFO')
        elif self.debug > 2:
            self.logger.setLevel(logging.DEBUG)
            self.logger.debug('Setting level to DEBUG')
