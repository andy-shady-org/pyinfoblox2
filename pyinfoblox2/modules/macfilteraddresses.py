# coding: utf-8

import logging
from typing import List

from .base import IPHelpers, BaseList, mac_check
from ..errors import InfobloxClientError, InfobloxError, InfobloxDataError


class MacFilterAddress(IPHelpers):
    """
    Abstraction class that simplifies and unifies all access to Infoblox MacFilterAddress objects.
    """
    FIELDS = 'mac,filter,comment,extattrs'
    RECORD_TYPE = 'macfilteraddress'

    def __init__(self, client, mac, filter_name=None, **kwargs):
        super(MacFilterAddress, self).__init__(client)
        self.mac_address = None
        if mac and self.is_valid_mac_address(mac):
            self.mac_address = mac
        self.filter = filter_name
        self.description = None
        self.data = kwargs
        self.logger.debug('MacFilterAddress Load Complete, loglevel set to %s', logging.getLevelName(self.logger.getEffectiveLevel()))

    def to_json(self, original_format=False):
        """
        Returns class items as dict structure

        :param original_format: keep original formal
        :type original_format: bool
        :return: class as dict structure
        :rtype: dict
        """
        if original_format:
            return dict(filter=self.filter, _ref=self.ref, comment=self.description, mac=self.mac_address, extattrs=self.extattrs.to_json())
        return dict(filter=self.filter, ref=self.ref, description=self.description, mac=self.mac_address, extattrs=self.extattrs.to_json())

    @classmethod
    def load(cls, client, value, callout=True):
        """
        Static method to load a given MacFilterAddress either by value of using an existing object

        :param client: pyinfoblox client class
        :param value: a valid mac address value string or MacFilterAddress class
        :param callout: Call out to WAPI to retrieve data, default=True
        :return: MacFilterAddress class, fully populated or False if macfilter does not exist
        """
        if value and isinstance(value, str):
            if cls.is_valid_mac_address(value):
                return cls.load_by_mac(client, value)
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
    def load_by_mac(cls, client, mac_address):
        """
        Static method to load a given prefix as a MacFilterAddress object and return it for use

        :param client: pyinfoblox client class
        :param mac_address: mac address
        :return: MacFilterAddress class, fully populated
        """
        if cls.is_valid_mac_address(mac_address):
            c = cls(client, mac_address)
        else:
            return False
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
                    if isinstance(h, MacFilterAddress):
                        self.mac_address = h.mac_address
                        self.filter = h.filter
                        self.description = h.description
                        self.ref = h.ref
                        self.extattrs = h.extattrs
                        self.loaded = True
                except InfobloxError:
                    raise
            elif 'mac_address' in json_data and json_data.get('mac_address', '').strip():
                self.mac_address = json_data.get('mac_address', '').strip()
                try:
                    self.get()
                except InfobloxError:
                    return False
            else:
                if not self.ref:
                    raise InfobloxDataError(self.__class__.__name__, 'MacFilterAddress "mac_address" attribute missing in data structure', 400)

    @mac_check
    def get(self):
        """
        Checks Infoblox for the MAC filter address record

        :return: Infoblox MacFilterAddress record in dict if exists else False
        :rtype: dict|bool
        :raises: Exception on error
        :raise: InfobloxError
        """

        fields = f'?_return_fields={self.FIELDS}&_return_as_object=1&mac={self.mac_address}'
        self.response = self.client.get(f'{self.RECORD_TYPE}{fields}')
        self.parse_reply()

    def parse_reply(self):
        result = self.parse_response(self.response)
        if isinstance(result, dict):
            if '_ref' in result:
                self.logger.debug('Record found, now setting details...')
                self.description = result.get('comment', '')
                self.filter = result.get('filter')
                if self.is_valid_mac_address(result.get('mac')):
                    self.mac_address = result.get('mac')
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

    @mac_check
    def create(self, username=None, **kwargs):
        """
        Create MAC filter address record in Infoblox

        :param username: username of person performing add for audit purposes
        :param kwargs: any extra attributes for the mac filter record in key/value pairs
        :return:
        """
        super().create(username, **kwargs)
        fields = f'?_return_fields={self.FIELDS}&_return_as_object=1'
        payload = {"extattrs": self.extattrs.to_json(), "mac": self.mac_address, "comment": self.description, "filter": self.filter}
        self.response = self.client.post(f'{self.RECORD_TYPE}{fields}', payload=payload)
        self.parse_reply()

    @mac_check
    def save(self, username=None, **kwargs):
        """
        Update MAC filter address record

        :param username: username of person performing add for audit purposes
        :param kwargs: any extra attributes for the mac filter record in key/value pairs
        :return:
        """
        super().save(username, **kwargs)
        fields = f'?_return_fields={self.FIELDS}&_return_as_object=1'
        payload = {"extattrs": self.extattrs.to_json(), "comment": self.description, "filter": self.filter, "mac": self.mac_address}
        self.response = self.client.put(self.ref + fields, payload=payload)
        self.parse_reply()

    @classmethod
    def add(cls, client, mac_address, filter_name, description=None, username=None, **extattrs):
        """
        Adds a MAC filter address entry

        :param client: pyinfoblox client class
        :param mac_address: mac address
        :param filter_name: name of mac filter
        :param description: description for the MAC filter address record
        :param username: username of person performing add for audit purposes
        :param extattrs: any extra attributes for the mac filter record in key/value pairs
        :return: MacFilterAddress class
        :rtype: MacFilterAddress
        """
        obj = cls(client, mac_address, filter_name)
        obj.description = description if description else ''
        obj.create(username, **extattrs)
        return obj

    def match(self, mac_address):
        return mac_address == str(self.mac_address)

    def __str__(self):
        return str(self.mac_address)

    def __eq__(self, other):
        if isinstance(other, self.__class__) and self.mac_address == other.mac_address:
            return True
        return False


class MacFilterAddresses(BaseList):
    """
    Abstraction class that should be used when dealing with lists of Infoblox MacFilter Address objects.
    """
    CHILD = MacFilterAddress
    RECORD_TYPE = 'macfilteraddress'

    def __init__(self, client, **kwargs):
        super(MacFilterAddresses, self).__init__(client, **kwargs)
        self.items = list()  # type: List[MacFilterAddress]
        self.logger.debug('MacFilterAddresses Load Complete, loglevel set to %s', logging.getLevelName(self.logger.getEffectiveLevel()))

    def get(self, limit=100, paging=0, view=None, short=False):
        return super().get(limit=limit, paging=paging, view=view, short=short)

    @classmethod
    def search(cls, client, search_key, value, view=None, regex=False, limit=100, paging=0):
        return super(cls, cls).search(client, search_key, value, view=view, limit=limit, paging=paging)

    @classmethod
    def search_by_mac(cls, client, value, limit=100, paging=0):
        return cls.search(client, 'mac', value, limit=limit, paging=paging)

    def __getitem__(self, item):
        super().__getitem__(item)

        for x in self.items:
            if isinstance(item, self.CHILD):
                if x.match(item.mac_address):
                    return x
            elif isinstance(item, str):
                if x.match(item):
                    return x
            elif isinstance(item, int):
                return self.items[item]
        raise IndexError(f'{self.CHILD.__name__} Not found')

    def __contains__(self, item):
        result = [x.mac_address for x in self.items]
        return result.__contains__(item)
