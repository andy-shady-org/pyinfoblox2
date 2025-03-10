# coding: utf-8

import logging
from typing import List

from .base import IPHelpers, BaseList, ip_check
from ..errors import InfobloxClientError, InfobloxError, InfobloxDataError, IPError


class IPv4Address(IPHelpers):
    """
    Abstraction class that simplifies and unifies all access to Infoblox IPv4Address objects.
    """
    FIELDS = 'ip_address,mac_address,status,usage,network,names,extattrs,network_view,comment'
    RECORD_TYPE = 'ipv4address'

    def __init__(self, client, ip_address, view='default', **kwargs):
        super(IPv4Address, self).__init__(client)
        self.ip_address = None
        if ip_address:
            self.ip_address = self.is_valid_ipaddress(ip_address)
        self.network = None
        self.mac = None
        self.usage = None
        self.status = None
        self.description = None
        self.names = list()
        self.view = view
        self.data = kwargs
        self.logger.debug('IPv4Address Load Complete, loglevel set to %s', logging.getLevelName(self.logger.getEffectiveLevel()))

    def to_json(self, original_format=False):
        """
        Returns class items as dict structure

        :param original_format: keep original formal
        :type original_format: bool
        :return: class as dict structure
        :rtype: dict
        """
        if original_format:
            return dict(ip_address=str(self.ip_address), _ref=self.ref, mac_address=self.mac, status=self.status, network=str(self.network), names=self.names,
                        usage=self.usage, comment=self.description if self.description else '', network_view=self.view, extattrs=self.extattrs.to_json())
        return dict(ip_address=str(self.ip_address), ref=self.ref, mac_address=self.mac, status=self.status, network=str(self.network), names=self.names,
                    usage=self.usage, description=self.description if self.description else '', view=self.view, extattrs=self.extattrs.to_json())

    @classmethod
    def load(cls, client, value, callout=True):
        """
        Static method to load a given IPv4Address either by value of using an existing object

        :param client: pyinfoblox client class
        :param value: a valid IP Address value string or IPv4Address class
        :param callout: Call out to WAPI to retrieve data, default=True
        :return: IPv4Address class, fully populated or False if IP Address does not exist
        """
        try:
            if value and cls.is_valid_ipaddress(value):
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
        Static method to load a given prefix as a IPv4Address object and return it for use

        :param client: pyinfoblox client class
        :param ip_address: IPv4 address
        :return: IPv4Address class, fully populated
        """
        ip_address = cls.is_valid_ipaddress(ip_address)
        c = cls(client, str(ip_address))
        try:
            c.get()
        except (InfobloxError, InfobloxClientError):
            return False
        return c

    def from_json(self, json_data):
        """
        Load direct from JSON data

        :param json_data: dict of parameters
        :return:
        :raises: Exception on error
        :raise: InfobloxError
        """
        if not self.ref:
            if 'ref' in json_data and json_data['ref']:
                try:
                    h = self.load_by_ref(self.client, json_data['ref'])
                    if isinstance(h, IPv4Address):
                        self.ip_address = h.ip_address
                        self.view = h.view
                        self.ref = h.ref
                        self.mac = h.mac
                        self.status = h.status
                        self.description = h.description
                        self.network = h.network
                        self.names = h.names
                        self.usage = h.usage
                        self.extattrs = h.extattrs
                        self.loaded = True
                except InfobloxError:
                    return False
            elif 'ip_address' in json_data and json_data.get('ip_address', '').strip():
                self.ip_address = self.is_valid_ipaddress(json_data.get('ip_address', '').strip())
                try:
                    self.get()
                except InfobloxError:
                    return False
            else:
                if not self.ref:
                    raise InfobloxDataError(self.__class__.__name__, 'IPv4Address "ip_address" attribute missing in data structure', 400)

    @ip_check
    def get(self):
        """
        Checks Infoblox for the USED IP Address record

        :return: Infoblox IPv4Address record in dict if exists else False
        :rtype: dict|bool
        :raises: Exception on error
        :raise: InfobloxError
        """

        fields = f'?_return_fields={self.FIELDS}&_return_as_object=1&ip_address={str(self.ip_address)}&status=USED'
        if self.view:
            fields = fields + f'&network_view={self.view}'
        self.response = self.client.get(f'{self.RECORD_TYPE}{fields}')
        self.parse_reply()

    def parse_reply(self):
        result = self.parse_response(self.response)
        if isinstance(result, dict):
            if '_ref' in result:
                self.view = result.get('network_view')
                self.ip_address = self.is_valid_ipaddress(result.get('ip_address'))
                self.network = self.is_valid_network(result.get('network'))
                self.mac = result.get('mac_address')
                self.status = result.get('status')
                self.description = result.get('comment', '')
                self.names = result.get('names')
                self.usage = result.get('usage')
                self.ref = result.get('_ref')
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

    def match(self, ip_address):
        return ip_address == str(self.ip_address)

    def __str__(self):
        return str(self.ip_address)

    def __eq__(self, other):
        if isinstance(other, self.__class__) and str(self.ip_address) == str(other.ip_address):
            return True
        return False


class IPv4Addresses(BaseList):
    """
    Abstraction class that should be used when dealing with lists of Infoblox IPv4Address objects.
    """
    CHILD = IPv4Address
    RECORD_TYPE = 'ipv4address'
    NETWORK_VIEW = True

    def __init__(self, client, **kwargs):
        super(IPv4Addresses, self).__init__(client, **kwargs)
        self.items = list()  # type: List[IPv4Address]
        self.logger.debug('IPv4Addresses Load Complete, loglevel set to %s', logging.getLevelName(self.logger.getEffectiveLevel()))

    @classmethod
    def search_by_network(cls, client, value, view='default', limit=100, paging=0, status='USED'):
        return cls.search(client, f'status={status}&network', value, view=view, limit=limit, paging=paging)

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
        result = [str(x.ip_address) for x in self.items]
        return result.__contains__(item)
