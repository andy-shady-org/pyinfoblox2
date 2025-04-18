# coding: utf-8

import asyncio
import datetime
import functools
import ipaddress
import json
import logging
import re
import socket
import timeit

import aiofiles
import ijson
from alive_progress import alive_bar

from ..client import InfobloxDummyClient
from ..errors import IPError, InfobloxError, InfobloxDataError, InfobloxClientError
from .misc import ExtraAttr, AttrObj

RECORD_LIMIT = 10000


def hostname_check(value=False, wildcards=False):
    """
    Hostname Check decorator that checks for valid hostnames
    :param value: set to true to allow for underscore characters
    :param wildcards: set to true to allow for wildcard characters
    :return: inner function
    """
    def decorator(func):
        """
        Hostname checker decorator function
        :param func: wrapped function
        :return: inner function
        """
        @functools.wraps(func)
        def check_hostname(ref, username=None, **kwargs):
            if not ref.is_valid_hostname(ref.name, value, wildcards):
                raise IPError('Invalid hostname format: Failed REGEX checks')
            if username:
                result = func(ref, username, **kwargs)
            else:
                result = func(ref, **kwargs)
            return result
        return check_hostname
    return decorator


def fqdn_check(value=False, wildcards=False):
    """
    Hostname Check decorator that checks for valid FQDNs
    :param value: set to true to allow for underscore characters
    :param wildcards: set to true to allow for wildcard characters
    :return: inner function
    """
    def decorator(func):
        """
        FQDN checker decorator function
        :param func: wrapped function
        :return: inner function
        """
        @functools.wraps(func)
        def check_fqdn(ref, username=None, **kwargs):
            if not ref.is_valid_fqdn(ref.name, value, wildcards):
                raise IPError('Invalid FQDN format: Failed REGEX checks')
            if username:
                result = func(ref, username, **kwargs)
            else:
                result = func(ref, **kwargs)
            return result
        return check_fqdn
    return decorator


def mac_check(func):
    """
    Hostname checker decorator function
    :param func: wrapped function
    :return: inner function
    """
    def check_mac(ref, username=None, **kwargs):
        if not ref.is_valid_mac_address(ref.mac_address):
            raise IPError('Invalid MAC Address format: Failed REGEX checks')
        if username:
            result = func(ref, username, **kwargs)
        else:
            result = func(ref, **kwargs)
        return result
    return check_mac


def ip_check(func):
    """
    IP checker decorator function
    :param func: wrapped function
    :return: inner function
    """
    def check_ip(ref, username=None, **kwargs):
        if '-' in str(ref.ip_address):
            try:
                ip1, ip2 = ref.ip_address.split('-')
            except ValueError as e:
                raise IPError('Invalid IP Address pair format: %s' % str(e))
            ref.is_valid_ipaddress(str(ip1))
            ref.is_valid_ipaddress(str(ip2))
        elif '/' in str(ref.ip_address):
            ref.is_valid_network(str(ref.ip_address))
        else:
            ref.is_valid_ipaddress(str(ref.ip_address))
        if username:
            result = func(ref, username, **kwargs)
        else:
            result = func(ref, **kwargs)
        return result
    return check_ip


def network_check(func):
    """
    Network checker decorator function
    :param func: wrapped function
    :return: inner function
    """
    def check_network(ref, username=None, **kwargs):
        ref.is_valid_network(str(ref.network))
        if username:
            result = func(ref, username, **kwargs)
        else:
            result = func(ref, **kwargs)
        return result
    return check_network


def networkv6_check(func):
    """
    Network checker decorator function
    :param func: wrapped function
    :return: inner function
    """
    def check_network(ref, username=None, **kwargs):
        ref.is_valid_networkv6(str(ref.network))
        if username:
            result = func(ref, username, **kwargs)
        else:
            result = func(ref, **kwargs)
        return result
    return check_network


class Base(object):
    """
    Abstraction class that should be used as a top level parent class for all Infoblox class objects.

    """
    FIELDS = None

    def __init__(self, client, *args, **kwargs):
        """
        Standard constructor.

        :param client: Infoblox REST Client Instance
        :type client: Client
        """
        self.ref = None
        self.logger = logging.getLogger()
        self.client = client
        self.extattrs = ExtraAttr()  # type: ExtraAttr
        self.options = list()
        self.response = None
        self.loaded = False

    @classmethod
    def load(cls, client, value, callout=True):
        """
        Static method to load a given Infoblox Record either by value of using an existing object

        :param client: pyinfoblox client class
        :param value: a valid value string or object class
        :param callout: Call out to WAPI to retrieve data, default=True
        """
        if value and isinstance(value, str):
            try:
                a = cls.load_by_name(client, value)
                return a
            except IPError:
                pass
        elif isinstance(value, dict):
            a = cls(client, None)
            if callout:
                a.from_json(value)
            else:
                a.response = value
                a.parse_reply()
            if a.ref and a.loaded:
                return a
        elif isinstance(value, cls):
            value.get()
            return value
        return False

    @classmethod
    def load_by_ref(cls, client, ref):
        """
        Static method to load a given Infoblox reference as an object and return it for use

        :param client: pyinfoblox client class
        :param ref: a valid Infoblox A record reference
        """
        if ref and isinstance(ref, str):
            fields = f'?_return_fields={cls.FIELDS}&_return_as_object=1'
            response = client.get(ref + fields)
        else:
            raise InfobloxDataError(cls.__class__.__name__, 'ref', 400)

        z = cls(client, None)
        z.response = response
        z.parse_reply()
        return z

    @classmethod
    def load_by_name(cls, client, name):
        """
        Static method to load a given name as a TXT Record object and return it for use

        :param client: pyinfoblox client class
        :param name: a TXT record name
        :return: Host class, fully populated
        """

        h = cls(client, name=name)
        try:
            h.get()
        except (InfobloxError, InfobloxClientError) as err:
            h.logger.debug(err)
            return False
        return h

    @staticmethod
    def parse_options(result):
        options = list()
        if 'options' in result:
            for x in result.get('options'):
                if 'inherited' in x:
                    if 'values' in x:
                        for y in x.get('values'):
                            if y not in options:
                                options.append(y)
                else:
                    if x not in options:
                        options.append(x)
            options = sorted(options, key=lambda z: z.get('num'))
        return options

    def to_json(self, original_format=False):
        raise NotImplementedError

    def from_json(self, json_data):
        raise NotImplementedError

    def get(self):
        raise NotImplementedError

    def timeit(self, method, *args, **kwargs):
        """
        Method for testing timing of request

        :param method: method to run timeit against
        :return: cnt
        :rtype: float|int
        """
        tic = timeit.default_timer()
        m = getattr(self, method)
        m(*args, **kwargs)
        toc = timeit.default_timer()
        cnt = toc - tic  # elapsed time in seconds
        return cnt

    def save(self, username=None, **kwargs):
        if kwargs:
            for k in kwargs:
                self.extattrs + AttrObj(k, kwargs[k])
        if username and self.client.add_audit:
            timestamp = f"Infoblox Audit Entry: Changed by {username} on {datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')}"
            self.extattrs + AttrObj('ChangeControl', timestamp)

    def create(self, username=None, **kwargs):
        if kwargs:
            for k in kwargs:
                self.extattrs + AttrObj(k, kwargs[k])
        if username and self.client.add_audit:
            timestamp = f"Infoblox Audit Entry: Changed by {username} on {datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')}"
            self.extattrs + AttrObj('ChangeControl', timestamp)

    def parse_response(self, response):
        self.logger.debug(f'Response is: {response}')
        if response and isinstance(response, dict) and 'status_code' in response and 200 <= response.get('status_code') <= 299:
            if 'data' in response and isinstance(response.get('data'), dict):
                result = response.get('data', {})
                if 'result' in result:
                    if isinstance(result['result'], list) and len(result['result']) > 0:
                        result = result.get('result')[-1]
                    elif isinstance(result['result'], (str, dict)):
                        result = result.get('result')
                    else:
                        raise InfobloxError(self.__class__.__name__, f'{self.__class__.__name__} not found: %s' % response)
            elif 'data' in self.response and isinstance(self.response.get('data'), str):
                result = self.response.get('data')
            else:
                raise InfobloxError(self.__class__.__name__, 'Invalid response - Expected dict or string: %s' % response)
        else:
            raise InfobloxError(self.__class__.__name__, 'Invalid response - Expected dict: %s' % response)
        return result

    def parse_reply(self):
        raise NotImplementedError

    def parse_extattr(self, result):
        if 'extattrs' in result:
            for x in result.get('extattrs'):
                if result['extattrs'][x] and 'value' in result['extattrs'][x]:
                    if x not in self.extattrs:
                        self.extattrs + AttrObj(x, result['extattrs'][x]['value'])
                    else:
                        self.extattrs[x].value = result['extattrs'][x]['value']

    def add_audit(self, username):
        """
        Adds an updated change control timestamp record to this record

        :param username: username making the change
        :return: True
        :raises: InfobloxError on failure
        :rtype: bool
        """
        if not self.ref:
            raise InfobloxDataError(self.__class__.__name__, 'no reference to perform audit', 400)
        fields = '?_return_fields=extattrs'
        if not self.client.create_audit(self.ref + fields, username):
            raise InfobloxError(self.__class__.__name__, 'Could not add audit log')
        self.get()
        return True

    def remove(self, username=None, remove_on=False, remove_flags=False):
        """
        Removes the attached record from Infoblox

        :param username: Username making the change for the purposes of audit logs
        :param remove_on: datetime to remove the record on in '%Y-%m-%d %H:%M:%S' format
        :type: remove_on: str
        :param remove_flags: process any additional remove flags
        :type: remove_flags: bool
        :return: True on success else false
        :rtype: bool
        """
        if username and self.client.add_audit:
            self.add_audit(username)
        epoch = None
        if remove_on and isinstance(remove_on, str):
            p = '%Y-%m-%d %H:%M:%S'
            epoch = datetime.datetime.strptime(remove_on, p).strftime("%s")
            self.ref += f'?_schedinfo.scheduled_time={epoch}'
        if remove_flags and hasattr(self, 'remove_flags'):
            if epoch:
                self.ref += f'&{self.remove_flags}'
            else:
                self.ref += f'?{self.remove_flags}'
        response = self.client.delete(self.ref)
        self.logger.debug('response is: %s', response)
        if response and response is not None:
            if 'status_code' in response and 200 <= response.get('status_code') <= 299:
                self.loaded = False
                self.ref = None
                return True
        self.logger.error('response is: %s', response)
        return False


class IPHelpers(Base):
    """
    Abstraction class that should be used as a parent class when any IP/Network/Hostname/Mac Address validation is used within the class.

    All methods in this class should be static methods.
    """
    def __init__(self, client):
        super(IPHelpers, self).__init__(client)

    @staticmethod
    def resolve_name(hostname):
        """
        Helper method for resolving DNS names to IP addresses

        :param hostname: string containing hostname
        :type hostname: str|None
        :return: True on success
        :rtype: bool
        """
        import socket
        try:
            ip = socket.gethostbyname(hostname)
            return ip
        except (socket.herror, socket.gaierror):
            logging.debug('Could not resolve %s', hostname)
        return False

    @staticmethod
    def resolve_ip(ip_address):
        """
        Helper method for resolving IP's to DNS names

        :param ip_address: string containing IPv4 address
        :type ip_address: str
        :return: True on success
        :rtype: bool
        """
        import socket
        try:
            socket.inet_aton(ip_address)
        except socket.error:
            logging.debug('Could not resolve %s', ip_address)
        else:
            try:
                name = socket.getfqdn(ip_address)
                return name
            except Exception as exp:
                logging.error('socket.getfqdn', exc_info=exp)
        return False

    @staticmethod
    def calculate_fqdn(ip_address, hostname=None):
        """
        Helper method for resolving IP's to FQDN DNS names and checking that the hostname part is valid if supplied

        :param ip_address: string containing IPv4 address
        :type ip_address: str
        :param hostname: string containing hostname
        :type hostname: str|None
        :return: True on success
        :rtype: bool
        """
        fqdn = False
        if ip_address and IPHelpers.is_valid_ipaddress(ip_address):
            fqdn = IPHelpers.resolve_ip(ip_address)

        if not fqdn:
            logging.error('FQDN not found: %s', str(hostname))
            return False

        if hostname and hostname not in fqdn:
            logging.error('FQDN not found in %s: %s', str(hostname), str(fqdn))
            return False
        return fqdn

    @staticmethod
    def check_reverse_resolve(ip):
        """
        Validator method for ensuring passed IP's reverse resolve
        :param ip: string containing IPv4 address
        :type ip: str
        :return: reversed_dns: tuple containing resolving entry
        :rtype: tuple
        """
        try:
            reversed_dns = socket.gethostbyaddr(ip)
            if isinstance(reversed_dns, tuple):
                return reversed_dns
        except (socket.herror, socket.gaierror):
            return False

    @staticmethod
    def check_forward_resolve(name, ip):
        """
        Validator method for ensuring passed names resolve to passed IP's
        :param name: string containing hostname
        :type name: str
        :param ip: string containing IPv4 address
        :type ip: str
        :return: True on success
        :rtype: bool
        """
        try:
            ip_r = socket.gethostbyname(name)
            if ip == ip_r:
                return ip_r
            else:
                return False
        except (socket.herror, socket.gaierror):
            return False

    @staticmethod
    def is_valid_network(network):
        """
        Validator method for ensuring passed network subnets are valid

        :param network: string containing IPv4 address
        :type network: str
        :return: True on success
        :rtype: ipaddress.IPv4Network
        :raises: IPError
        """

        if network is None or '/' not in network:
            raise IPError('Network address is not in valid format: %s' % str(network))
        try:
            net = ipaddress.IPv4Network(str(network))
        except (ipaddress.AddressValueError, ipaddress.NetmaskValueError) as e:
            raise IPError('Invalid Network address format for %s: %s' % (network, str(e)))
        except Exception as e:
            raise IPError('Invalid Network address format for %s: %s' % (network, str(e)))
        return net

    @staticmethod
    def is_valid_networkv6(network):
        """
        Validator method for ensuring passed network subnets are valid

        :param network: string containing IPv6 address
        :type network: str
        :return: True on success
        :rtype: ipaddress.IPv4Network
        :raises: IPError
        """

        if network is None or '/' not in network:
            raise IPError('Network address is not in valid format: %s' % str(network))
        try:
            net = ipaddress.IPv6Network(str(network))
        except (ipaddress.AddressValueError, ipaddress.NetmaskValueError) as e:
            raise IPError('Invalid Network address format for %s: %s' % (network, str(e)))
        except Exception as e:
            raise IPError('Invalid Network address format for %s: %s' % (network, str(e)))
        return net

    @staticmethod
    def is_valid_hostname(hostname, allow_underscores=False, wildcards=False):
        """
        Validator method for ensuring passed host names are valid

        :param hostname: string containing hostname
        :type hostname: str
        :param allow_underscores: allow names containing underscore characters
        :type allow_underscores: bool
        :param wildcards: allow names containing wildcard characters
        :type wildcards: bool
        :return: True on success
        :rtype: bool
        """

        if not isinstance(hostname, str) or not hostname:
            raise IPError('Invalid hostname format: %s' % hostname)

        if len(hostname) > 255:
            raise IPError('Invalid hostname format: Too Long, Exceeds 255 characters')
        if hostname[-1] == ".":
            hostname = hostname[:-1]  # strip exactly one dot from the right, if present
        allowed = re.compile(r"(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
        if allow_underscores:
            allowed = re.compile(r"(?!-)_?[A-Z_\d-]{1,63}(?<!-)$", re.IGNORECASE)
        if wildcards:
            allowed = re.compile(r"(?!-)\*?[A-Z\d-]{0,63}(?<!-)$", re.IGNORECASE)
        if allow_underscores and wildcards:
            allowed = re.compile(r"(?!-)\*?_?[A-Z_\d-]{0,63}(?<!-)$", re.IGNORECASE)

        for x in hostname.split("."):
            if 1 > len(x) > 63:
                raise IPError('Invalid FQDN part format: Too Long, Exceeds 63 characters')
        return all(allowed.match(x) for x in hostname.split("."))

    @staticmethod
    def is_valid_fqdn(hostname, allow_underscores=False, wildcards=False):
        """
        Validator method for ensuring passed FQDNs are valid

        :param hostname: string containing hostname
        :type hostname: str
        :param allow_underscores: allow names containing underscore characters
        :type allow_underscores: bool
        :param wildcards: allow names containing wildcard characters
        :type wildcards: bool
        :return: True on success
        :rtype: bool
        """
        if not isinstance(hostname, str):
            raise IPError('Invalid FQDN format: %s' % hostname)

        if len(hostname) > 255:
            raise IPError('Invalid FQDN format: Too Long, Exceeds 255 characters')
        if hostname[-1] == ".":
            hostname = hostname[:-1]  # strip exactly one dot from the right, if present
        allowed = re.compile(r"(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
        if allow_underscores:
            allowed = re.compile(r"(?!-)_?[A-Z_\d-]{1,63}(?<!-)$", re.IGNORECASE)
        if wildcards:
            allowed = re.compile(r"(?!-)\*?[A-Z\d-]{0,63}(?<!-)$", re.IGNORECASE)
        if allow_underscores and wildcards:
            allowed = re.compile(r"(?!-)\*?_?[A-Z_\d-]{0,63}(?<!-)$", re.IGNORECASE)
        for x in hostname.split("."):
            if 1 > len(x) > 63:
                raise IPError('Invalid FQDN part format: Too Long, Exceeds 63 characters')
        if len(hostname.split(".")) < 2:
            raise IPError('Invalid FQDN: Only has single host part')
        return all(allowed.match(x) for x in hostname.split("."))

    @staticmethod
    def is_valid_mac_address(mac_address):
        """
        Validator method for ensuring passed MAC Addresses are valid

        :param mac_address: string containing hostname
        :type mac_address: str
        :return: True on success
        :rtype: bool
        """
        if not isinstance(mac_address, str):
            raise IPError('Invalid mac_address format: %s' % mac_address)

        if re.match(r"^((([a-f0-9]{2}:){5})|(([a-f0-9]{2}-){5}))[a-f0-9]{2}$", mac_address.lower()):
            return True
        raise IPError('Invalid MAC Address format: %s' % mac_address)

    @staticmethod
    def is_valid_ipaddress(ip_address):
        """
        Validator method for ensuring passed IP Address is valid

        :param ip_address: string containing IPv4 address
        :type ip_address: str
        :return: True on success
        :rtype: bool
        """

        if isinstance(ip_address, (int, float)):
            raise IPError('Invalid host IP address format')

        try:
            ip = ipaddress.IPv4Address(str(ip_address))
        except ipaddress.AddressValueError as e:
            raise IPError('Invalid host IP address format for %s: %s' % (ip_address, str(e)))
        except Exception as e:
            raise IPError('Invalid host IP address format for %s: %s' % (ip_address, str(e)))
        return ip

    @staticmethod
    def is_valid_ipaddressv6(ip_address):
        """
        Validator method for ensuring passed IP Address is valid

        :param ip_address: string containing IPv6 address
        :type ip_address: str
        :return: True on success
        :rtype: bool
        """

        if isinstance(ip_address, (int, float)):
            raise IPError('Invalid host IP address format')

        try:
            ip = ipaddress.IPv6Address(str(ip_address))
        except ipaddress.AddressValueError as e:
            raise IPError('Invalid host IP address format for %s: %s' % (ip_address, str(e)))
        except Exception as e:
            raise IPError('Invalid host IP address format for %s: %s' % (ip_address, str(e)))
        return ip

    @staticmethod
    def _process_dhcp_option(name=None, num=None, use=None, value=None, vendor_class=None):
        """

        :param name: name of option
        :param num: numeric value of option
        :param use: can be None or True or False
        :param value: string value of option
        :param vendor_class: vendor class string
        :return: dict of option
        :rtype: dict
        """

        if not use or use is None or use == 'None':
            return dict(name=name, num=int(num), value=value, vendor_class=vendor_class)
        else:
            return dict(name=name, num=int(num), use_option=use, value=value, vendor_class=vendor_class)

    def add_option(self, name=None, num=None, use=None, value=None, vendor_class=None):
        """
        Add a DHCP option to Infoblox

        :param name: name of option
        :param num: DHCP numerical value for option (e.g. 82)
        :param use: DHCP use string for option
        :param value: the value for the option
        :param vendor_class: the Vendor class for the option
        """
        if not self.options:
            self.options = list()
        if self._process_dhcp_option(name, num, use, value, vendor_class) not in self.options:
            self.options.append(self._process_dhcp_option(name, num, use, value, vendor_class))

    def _parse_options(self, options):
        if not options:
            options = list()
        if isinstance(options, list):
            for x in options:
                if isinstance(x, tuple) and len(x) == 5:
                    self.add_option(x[0], x[1], x[2], x[3], x[4])
                elif isinstance(x, dict):
                    self.add_option(x.get('name'), x.get('num'), x.get('use'), x.get('value'), x.get('vendor_class'))
                else:
                    raise InfobloxError(self.__class__.__name__, 'options')

    @staticmethod
    def compare_lists(list1, list2):
        return list(set(list1) - set(list2))


class BaseList(object):
    CHILD = None
    RECORD_TYPE = None
    NETWORK_VIEW = False

    def __init__(self, client, **kwargs):
        self.client = client
        self.items = list()
        self.data = kwargs
        self.next_page = None
        self.logger = logging.getLogger()

    @classmethod
    async def async_load_data(cls, file_, debug_):
        """
        Class method to load lists of records from a file

        :param file_: File to load records from
        :param debug_: enable debugging (1 for INFO, 2 for DEBUG)
        :return:
        """
        m = cls(InfobloxDummyClient(debug_))
        failed = 0
        async with aiofiles.open(file_, mode='rb') as f:
            with alive_bar(title=m.__class__.__name__, bar='smooth', spinner='stars', unknown='stars') as bar:
                items = list()
                async for x in ijson.items(f, 'item', buf_size=16384):
                    try:
                        data = dict(status_code=200, data=x)
                        c = cls.CHILD.load(m.client, data, callout=False)
                    except (InfobloxDataError, IPError, InfobloxError) as err:
                        m.logger.error(f'Cannot load: {err}: {x}')
                        failed += 1
                    bar()
                    items.append(c)
                m.items = items
        if failed:
            m.logger.error(f'Failed load {failed} records')
        return m

    @classmethod
    async def async_load_json_data(cls, data, debug_):
        """
        Class method to load lists of records from a file

        :param data: JSON data to load records from
        :param debug_: enable debugging (1 for INFO, 2 for DEBUG)
        :return:
        """
        m = cls(InfobloxDummyClient(debug_))
        failed_list = list()
        failed = 0
        items = list()
        async for x in cls.de_sync(data):
            try:
                data = dict(status_code=200, data=x)
                c = cls.CHILD.load(m.client, data, callout=False)
            except (InfobloxDataError, InfobloxError, IPError) as err:
                m.logger.error(f'Cannot load {x.get("ipv4addr")}: {err}: {x}')
                failed_list.append(x.get("name"))
                failed += 1
                continue
            items.append(c)
        m.items = items
        if failed:
            m.logger.error(f'Failed load {failed} records: {failed_list}')
        return m

    @classmethod
    def load_from_file(cls, filename, verbose=0):
        """
        Method to load A records from a file

        :param filename: a valid filename (full relative path required)
        :param verbose: enable debugging (1 for INFO, 2 for DEBUG)
        """
        async def async_load_from_file(file_name, debug):
            for task in asyncio.as_completed([cls.async_load_data(file_name, debug)]):
                obj = await task
                return obj

        loop = asyncio.new_event_loop()
        records = loop.run_until_complete(async_load_from_file(filename, verbose))
        return records

    @classmethod
    def load_from_json(cls, json_data, verbose=0):
        """
        Method to load A records from a file

        :param json_data: a valid JSON list of objects
        :param verbose: enable debugging (1 for INFO, 2 for DEBUG)
        """

        async def async_load_from_json(data, debug):
            for task in asyncio.as_completed([cls.async_load_json_data(data, debug)]):
                obj = await task
                return obj

        loop = asyncio.new_event_loop()
        records = loop.run_until_complete(async_load_from_json(json_data, verbose))
        return records

    @classmethod
    def search(cls, client, search_key, value, view='default', regex=False, limit=100, paging=0):
        """
        Search Record objects within Infoblox

        :param client: Infoblox REST Client instance
        :type client: Client
        :param search_key: the record field to search
        :param value: a search string value
        :param view: An Infoblox view to use
        :param regex: whether to use regex in the search or not
        :param limit: result record limit
        :param paging: use paging
        """
        m = cls(client)
        m.check_limit(limit)
        paging = 1 if paging else 0
        match = '='
        if regex:
            match = '~='
        if isinstance(search_key, str) and isinstance(value, str):
            fields = f'?{search_key}{match}{value}&_return_as_object=1&_return_fields={cls.CHILD.FIELDS}&_max_results={limit}&_paging={paging}'
            if view:
                if cls.NETWORK_VIEW:
                    fields = fields + f'&network_view={view}'
                else:
                    fields = fields + f'&view={view}'
            m.parse_result(client.get(f'{cls.RECORD_TYPE}{fields}'))
        return m

    @classmethod
    def check_limit(cls, limit):
        try:
            if int(limit) > RECORD_LIMIT:
                raise InfobloxDataError(cls.__class__.__name__, f'Max Limit is {RECORD_LIMIT}, please use paging', 400)
        except (TypeError, ValueError):
            raise InfobloxDataError(cls.__class__.__name__, '"limit"', 400)
        return True

    @staticmethod
    async def de_sync(item):
        for x in item:
            yield x

    async def async_load(self, client, data):
        if client and client.debug >= 2:
            start_time = datetime.datetime.now()
            obj = self.CHILD.load(client, data, callout=False)
            completed = datetime.datetime.now()
            duration = completed - start_time
            minutes, seconds = divmod(duration.total_seconds(), 60)
            self.logger.info(f'Record load time: {int(minutes)} minutes, {seconds:.4f} seconds')
            return obj
        else:
            return self.CHILD.load(client, data, callout=False)

    async def async_get(self, results):
        tasks = list()
        for x in results:
            tasks.append(self.async_load(self.client, dict(status_code=200, data=x)))
        objects = await asyncio.gather(*tasks)
        return objects

    def write_to_file(self, outfile, start=0, length=100000):
        cls = self.__class__(self.client)
        cls.items = self.items[start:length]
        with open(outfile, "w") as fh:
            fh.write(json.dumps(cls.to_json(True)))

    def parse_result(self, result):
        if 'status_code' in result and 200 <= result.get('status_code') <= 299:
            if 'data' in result and result.get('data'):
                if 'next_page_id' in result.get('data'):
                    self.next_page = result.get('data', {}).get('next_page_id')
                else:
                    self.next_page = False
                results = result.get('data', {}).get('result')
                if results and isinstance(results, list) and len(results) > 0:
                    start_time = datetime.datetime.now()
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError as err:
                        if str(err).startswith('There is no current event loop in thread'):
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                        else:
                            raise
                    objects = loop.run_until_complete(self.async_get(results))
                    self.items += [x for x in objects if x not in self.items]
                    completed = datetime.datetime.now()
                    duration = completed - start_time
                    minutes, seconds = divmod(duration.total_seconds(), 60)
                    self.logger.warning(f'Record Set load time: {int(minutes)} minutes, {seconds:.4f} seconds')

    def remove(self, item):
        if isinstance(item, self.CHILD) and str(item) in self:
            self.items.remove(item)
        elif isinstance(item, str) and item in self:
            self.items.remove(self[item])
        else:
            raise TypeError(f'unsupported type(s): {type(item)}')

    def add(self, item):
        if item not in self.items:
            self.items += item,

    def to_json(self, original_format=False):
        """
        Method that returns all items within self as JSON using parallel processing

        :param original_format: keep original formal
        :type original_format: bool
        :return: list of dictionaries
        :rtype: list
        """
        return [x.to_json(original_format) for x in self]

    def timeit(self, method, *args, **kwargs):
        """
        Method for testing timing of request

        :param method:
        :return: cnt
        :rtype: float|int
        """
        tic = timeit.default_timer()
        m = getattr(self, method)
        m(*args, **kwargs)
        toc = timeit.default_timer()
        cnt = toc - tic  # elapsed time in seconds
        return cnt

    def get_next(self, page_id):
        """
        Method to retrieve next page of results from Infoblox

        :param page_id: Infoblox page ID
        :return: True
        """
        self.logger.debug('getting next page: %s', page_id)
        if page_id and isinstance(page_id, str):
            self.parse_result(self.client.get(f'{self.RECORD_TYPE}?_page_id={page_id}'))

    def get(self, limit=100, paging=0, view='default', short=False):
        """
        Method to retrieve records from Infoblox

        :param limit: result record limit
        :param paging: use paging
        :param view: An Infoblox view to use
        :param short: get a shortened version of the data
        """
        self.check_limit(limit)
        paging = 1 if paging else 0
        query = f'{self.RECORD_TYPE}?_return_as_object=1&_return_fields={self.CHILD.FIELDS}&_max_results={limit}&_paging={paging}'
        if view:
            if self.NETWORK_VIEW:
                query = query + f'&network_view={view}'
            else:
                query = query + f'&view={view}'
        if short:
            query = f'{self.RECORD_TYPE}?_return_as_object=1&_max_results={limit}&_paging={paging}'
        self.parse_result(self.client.get(query))

    def find(self, key, value):
        m = self.__class__(self.client)
        matches = list()
        for item in self:
            try:
                if str(value) in str(getattr(item, key)):
                    matches.append(item)
            except AttributeError:
                pass
            try:
                if str(value) in str(item.extattrs.get(key)):
                    matches.append(item)
            except IndexError:
                pass
        m.items = matches
        return m

    def __getitem__(self, item):
        if item == 'get' or item == 'search':
            return self.__getattribute__(item)

    def __contains__(self, item):
        result = [x.name for x in self.items]
        return result.__contains__(item)

    def __len__(self):
        return len(self.items)

    def __iter__(self):
        result = []
        for x in self.items:
            result.append(x)
        return result.__iter__()

    async def __aiter__(self):
        for x in self.items:
            yield x

    async def __anext__(self):
        try:
            item = next(self.items)
        except StopIteration:
            raise StopAsyncIteration
        return item

    def __iadd__(self, other):
        if not isinstance(other, self.__class__):
            raise TypeError(f'unsupported type(s) for +=: {type(self)} and {type(other)}')
        self.items += other.items
        return self
