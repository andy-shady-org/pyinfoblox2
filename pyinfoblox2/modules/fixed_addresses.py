# coding: utf-8

import ipaddress
import logging
from typing import List

from .base import IPHelpers, BaseList, mac_check, ip_check
from ..errors import InfobloxClientError, InfobloxError, InfobloxDataError, IPError


class FixedAddress(IPHelpers):
    """
    Abstraction class that simplifies and unifies all access to Infoblox Fixed Address objects.
    """
    FIELDS = 'ipv4addr,extattrs,options,comment,mac,name,network,match_client,network_view'
    RECORD_TYPE = 'fixedaddress'

    def __init__(self, client, ip_address, view='default', **kwargs):
        super(FixedAddress, self).__init__(client)
        self._ip_address = None
        if ip_address:
            self.ip_address = ip_address
        self.description = None
        self.mac_address = None
        self.name = None
        self.network = None
        self.options = list()
        self.match_client = 'MAC_ADDRESS'
        self.view = view
        self.logger.debug('Fixed Address Load Complete, loglevel set to %s', logging.getLevelName(self.logger.getEffectiveLevel()))
        self.data = kwargs

    @property
    def ip_address(self):
        return self._ip_address

    @ip_address.setter
    def ip_address(self, value):
        if isinstance(value, str):
            if '/' in value or '-' in value:
                if '-' in value:
                    try:
                        ip1, ip2 = value.split('-')
                    except ValueError as e:
                        raise IPError(f'Invalid IP Address pair format: {e}')
                    self.is_valid_ipaddress(ip1)
                    self.is_valid_ipaddress(ip2)
                elif '/' in value and self.is_valid_network(value):
                    self.network = self.is_valid_network(value)
                self._ip_address = f"func:nextavailableip:{str(value)}"
            else:
                self._ip_address = self.is_valid_ipaddress(value)
        elif isinstance(value, ipaddress.IPv4Address):
            self._ip_address = value
        else:
            raise InfobloxDataError(self.__class__.__name__, "ip_address", 400)

    def to_json(self, original_format=False):
        """
        Returns class items as dict structure

        :param original_format: keep original formal
        :type original_format: bool
        :return: class as dict structure
        :rtype: dict
        """
        if original_format:
            return dict(name=self.name, _ref=self.ref, comment=self.description if self.description else '', ipv4addr=str(self.ip_address), options=self.options,
                        network_view=self.view, network=str(self.network), mac=self.mac_address, match_client=self.match_client, extattrs=self.extattrs.to_json())
        return dict(name=self.name, ref=self.ref, description=self.description if self.description else '', ip_address=str(self.ip_address), options=self.options,
                    view=self.view, network=str(self.network), mac_address=self.mac_address, match_client=self.match_client, extattrs=self.extattrs.to_json())

    @classmethod
    def load(cls, client, value, callout=True):
        """
        Static method to load a given Fixed Address either by value of using an existing object

        :param client: pyinfoblox client class
        :param value: a valid ip_address or hostname value string or FixedAddress class
        :param callout: Call out to WAPI to retrieve data, default=True
        :return: FixedAddress class, fully populated or False if record does not exist
        """

        try:
            if value and isinstance(value, str) and cls.is_valid_ipaddress(value):
                return cls.load_by_address(client, value)
        except IPError:
            pass
        if isinstance(value, dict):
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
    def load_by_address(cls, client, ip_address):
        """
        Static method to load a given name as a FixedAddress object and return it for use

        :param client: pyinfoblox client class
        :param ip_address: a Fixed IPv4 Address
        :return: Host class, fully populated
        """

        h = cls(client, ip_address)
        try:
            h.get()
        except (InfobloxError, InfobloxClientError) as err:
            h.logger.debug(err)
            return False
        return h

    def from_json(self, json_data):
        """
        Load direct from JSON data

        :param json_data: dict of parameters
        :type json_data: dict
        :return:
        :raises: Exception on error
        :raise: InfobloxError
        """
        if not self.ref:
            if 'ref' in json_data and json_data['ref']:
                try:
                    h = self.load_by_ref(self.client, json_data['ref'])
                    if isinstance(h, FixedAddress):
                        self.ip_address = h.ip_address
                        self.network = h.network
                        self.mac_address = h.mac_address
                        self.view = h.view
                        self.description = h.description
                        self.name = h.name
                        self.match_client = h.match_client
                        self.ref = h.ref
                        self.options = h.options
                        self.extattrs = h.extattrs
                        self.loaded = True
                except InfobloxError:
                    return False
            elif 'ip_address' in json_data and json_data.get('ip_address', '').strip():
                self.ip_address = json_data.get('ip_address', '').strip()
                try:
                    self.get()
                except InfobloxError:
                    return False
            else:
                if not self.ref:
                    raise InfobloxDataError(self.__class__.__name__, 'FixedAddress "ip_address" attribute missing in data structure', 400)

    @ip_check
    def get_by_ip(self, fields):
        response = self.client.get(f'{self.RECORD_TYPE}?ipv4addr={str(self.ip_address)}{fields}&_return_as_object=1')
        self.logger.debug('response is: %s', response)
        return response

    def get(self):
        """
        Checks Infoblox for the Fixed Address

        :return: Infoblox Fixed Address in dict if exists else False
        :rtype: dict|bool
        :raises: Exception on error
        :raise: InfobloxError
        """
        fields = f'&_return_fields={self.FIELDS}&_return_as_object=1'
        if self.view:
            fields = fields + f'&network_view={self.view}'
        if self.ip_address:
            self.response = self.get_by_ip(fields)
        else:
            raise InfobloxDataError(self.__class__.__name__, 'name', 400)
        self.parse_reply()

    def parse_reply(self):
        result = self.parse_response(self.response)
        if isinstance(result, dict):
            if '_ref' in result:
                self.logger.debug('Record found, now setting details...')
                self.ip_address = result.get('ipv4addr')
                self.description = result.get('comment', '')
                self.name = result.get('name')
                if result.get('network'):
                    self.network = self.is_valid_network(result.get('network'))
                self.mac_address = result.get('mac')
                self.match_client = result.get('match_client')
                self.view = result.get('network_view')
                self.ref = result.get('_ref')
                if 'options' in result and isinstance(result.get('options'), list):
                    self.options = self.parse_options(result)
                self.parse_extattr(result)
            else:
                self.logger.error('reference not returned by item addition or update: %s' % self.response)
                raise InfobloxError(self.__class__.__name__, 'reference not returned by item addition or update: %s' % self.response)
        elif isinstance(result, str):
            self.ref = result
        else:
            self.logger.error('invalid data type, not dict or string: %s' % self.response)
            raise InfobloxError(self.__class__.__name__, 'invalid data type, not dict or string: %s' % self.response)
        self.loaded = True

    @ip_check
    @mac_check
    def create(self, username=None, **kwargs):
        """
        Create a Fixed Address

        :param username: username of person performing add for audit purposes
        :param kwargs: any extra attributes for the host record in key/value pairs
        :return:
        """
        super().create(username, **kwargs)
        if self.name:
            if not self.is_valid_hostname(self.name):
                raise IPError('Invalid hostname format: Failed REGEX checks')
        fields = f'?_return_fields={self.FIELDS}&_return_as_object=1'
        payload = {"extattrs": self.extattrs.to_json(), "ipv4addr": str(self.ip_address),
                   "match_client": self.match_client, "mac": self.mac_address, "comment": self.description, "use_ddns_domainname": True, "enable_ddns": True,
                   "use_options": True}
        if self.name:
            payload["name"] = str(self.name)
        if self.options:
            payload.update({"options": self.options})

        self.response = self.client.post(f'{self.RECORD_TYPE}{fields}', payload=payload)
        self.parse_reply()

    @ip_check
    @mac_check
    def save(self, username=None, **kwargs):
        """
        Update a Fixed Address

        :param username: username of person performing add for audit purposes
        :param kwargs: any extra attributes for the host record in key/value pairs
        :return:
        """
        super().save(username, **kwargs)
        if self.name:
            if not self.is_valid_hostname(self.name):
                raise IPError('Invalid hostname format: Failed REGEX checks')
        fields = f'?_return_fields={self.FIELDS}&_return_as_object=1'
        payload = {"extattrs": self.extattrs.to_json(), "ipv4addr": str(self.ip_address),
                   "match_client": self.match_client, "mac": self.mac_address, "comment": self.description, "use_ddns_domainname": True, "enable_ddns": True,
                   "use_options": True}
        if self.name:
            payload["name"] = str(self.name)

        if self.options:
            payload.update({"options": self.options})

        self.response = self.client.put(self.ref + fields, payload=payload)
        self.parse_reply()

    @classmethod
    def add(cls, client, ip_address, name=None, mac_address=None, match_client='MAC_ADDRESS', description=None, options=None, view='default', username=None, **extattrs):
        """
        Create a Fixed Address record within Infoblox

        :param client: pyinfoblox client class
        :param ip_address: IPv4 IP address or list of IPv4 Addresses to assign to host
          (If network is passed in CIDR format e.g. x.x.x.x/xx, a new IP will be allocated from the passed network using "nextavailableip" functionality)
          (If ip_address is passed in "ip-ip" a new IP will be allocated from between the 2 IPs listed using "nextavailableip" functionality)
        :param name: name of host record
        :param mac_address: mac address for the host record
        :param match_client: string for match client, must be 'MAC_ADDRESS' or 'RESERVED'
        :param description: description for the host record
        :param options: DHCP Options Object or tuple of options (5 params per option)
        :param view: the view to place the host in
        :param username: username of person performing add for audit purposes
        :param extattrs: any extra attributes for the host record in key/value pairs
        :return: FixedAddress Class
        :rtype: FixedAddress
        """
        obj = cls(client, ip_address, view=view)
        obj.description = description if description else ''
        obj.name = name
        obj.mac_address = mac_address if mac_address else '00:00:00:00:00:01'
        obj.match_client = match_client
        if obj.match_client == 'RESERVED':
            obj.mac_address = '00:00:00:00:00:00'
        obj._parse_options(options)
        obj.create(username, **extattrs)
        return obj

    def match(self, ip_address):
        return ip_address == str(self.ip_address)

    def __str__(self):
        return str(self.ip_address)

    def __eq__(self, other):
        if isinstance(other, self.__class__) and str(self.ip_address) == str(other.ip_address):
            return True
        return False


class FixedAddresses(BaseList):
    """
    Abstraction class that should be used when dealing with lists of Infoblox Fixed Address objects.
    """
    CHILD = FixedAddress
    RECORD_TYPE = 'fixedaddress'
    NETWORK_VIEW = True

    def __init__(self, client, **kwargs):
        super(FixedAddresses, self).__init__(client, **kwargs)
        self.items = list()  # type: List[FixedAddress]
        self.logger.debug('Fixed Addresses Load Complete, loglevel set to %s', logging.getLevelName(self.logger.getEffectiveLevel()))

    @classmethod
    def search_by_name(cls, client, value, view='default', limit=100, paging=0):
        return cls.search(client, 'name', value, view=view, regex=True, limit=limit, paging=paging)

    @classmethod
    def search_by_ip_address(cls, client, value, view='default', limit=100, paging=0):
        return cls.search(client, 'ipv4addr', value, view=view, regex=True, limit=limit, paging=paging)

    @classmethod
    def search_by_network(cls, client, value, view='default', limit=100, paging=0):
        return cls.search(client, 'network', value, view=view, regex=True, limit=limit, paging=paging)

    def __getitem__(self, item):
        super().__getitem__(item)

        for x in self.items:
            if isinstance(item, self.CHILD):
                if x.match(str(item.ip_address)) and item.view == x.view:
                    return x
            elif isinstance(item, str):
                if x.match(item):
                    return x
            elif isinstance(item, int):
                return self.items[item]
        raise IndexError(f'{self.CHILD.__name__} Not found')

    def __contains__(self, item):
        result = [x.ip_address for x in self.items]
        return result.__contains__(item)
