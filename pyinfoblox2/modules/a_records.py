# coding: utf-8

import logging
from typing import List

from .base import hostname_check, ip_check, IPHelpers, BaseList
from ..errors import InfobloxClientError, InfobloxError, InfobloxDataError, IPError


class ARecord(IPHelpers):
    """
    Abstraction class that simplifies and unifies all access to Infoblox A Record objects.
    """
    FIELDS = 'name,extattrs,comment,ipv4addr,view,dns_name,zone'
    RECORD_TYPE = 'record:a'

    def __init__(self, client, ip_address=None, name=None, view='default', **kwargs):
        """
        Standard constructor.

        :param client: Infoblox REST Client
        :type client: pyinfoblox.InfobloxClient
        :param ip_address: IPv4 Address
        :param name: A valid A record hostname
        :param view: An Infoblox View
        :param kwargs: Any additional arguments
        """
        super(ARecord, self).__init__(client)
        self.ip_address = None
        if ip_address:
            self.ip_address = self.is_valid_ipaddress(ip_address)
        self.name = name
        self.description = None
        self.zone = None
        self.dns_name = None
        self.view = view
        self.logger.debug('A Record Load Complete, loglevel set to %s', logging.getLevelName(self.logger.getEffectiveLevel()))
        self.data = kwargs
        self.remove_flags = 'remove_associated_ptr=True'

    def to_json(self, original_format=False):
        """
        Returns class items as dict structure

        :param original_format: keep original formal
        :type original_format: bool
        :return: class as dict structure
        :rtype: dict
        """
        if original_format:
            return dict(name=self.name, _ref=self.ref, comment=self.description if self.description else '', ipv4addr=str(self.ip_address) if self.ip_address else None,
                        zone=self.zone, dns_name=self.dns_name, view=self.view, extattrs=self.extattrs.to_json())
        return dict(name=self.name, ref=self.ref, description=self.description if self.description else '', ip_address=str(self.ip_address) if self.ip_address else None,
                    zone=self.zone, dns_name=self.dns_name, view=self.view, extattrs=self.extattrs.to_json())

    @classmethod
    def load(cls, client, value, callout=True):
        """
        Static method to load a given Infoblox Record either by value of using an existing object

        :param client: pyinfoblox client class
        :param value: a valid ip_address or hostname value string or object class
        :param callout: Call out to WAPI to retrieve data, default=True
        """
        try:
            if value and cls.is_valid_ipaddress(value):
                return cls.load_by_prefix(client, value)
        except IPError:
            pass
        return super(cls, cls).load(client, value, callout)

    @classmethod
    def load_by_prefix(cls, client, ip_address):
        """
        Static method to load a given IP as a ARecord object and return it for use

        :param client: pyinfoblox client class
        :param ip_address: a valid ip_address
        :return: Host class, fully populated
        """
        cls.is_valid_ipaddress(ip_address)
        h = cls(client, ip_address)
        try:
            h.get()
        except (InfobloxError, InfobloxClientError):
            return False
        return h

    @classmethod
    def load_by_name(cls, client, name):
        """
        Static method to load a given name as object and return it for use

        :param client: pyinfoblox client class
        :param name: a valid hostname
        :return: ARecord class, fully populated
        """
        if not IPHelpers.is_valid_hostname(name):
            raise IPError('Invalid hostname format: Failed REGEX checks')
        return super(cls, cls).load_by_name(client, name)

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
                    if isinstance(h, ARecord):
                        self.name = h.name
                        self.ip_address = h.ip_address
                        self.view = h.view
                        self.description = h.description
                        self.dns_name = h.dns_name
                        self.zone = h.zone
                        self.ref = h.ref
                        self.extattrs = h.extattrs
                        self.loaded = True
                except InfobloxError:
                    return False
            elif 'name' in json_data and json_data.get('name', '').strip():
                self.name = json_data.get('name', '').strip()
                try:
                    self.get()
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
                    raise InfobloxDataError(self.__class__.__name__, 'ARecord "name" or "ip_address" attribute missing in data structure', 400)

    @hostname_check(True)
    def get_by_name(self, fields):
        response = self.client.get(f'{self.RECORD_TYPE}?name={self.name}{fields}&_return_as_object=1')
        self.logger.debug('response is: %s', response)
        return response

    @ip_check
    def get_by_ip(self, fields):
        response = self.client.get(f'{self.RECORD_TYPE}?ipv4addr={str(self.ip_address)}{fields}&_return_as_object=1')
        self.logger.debug('response is: %s', response)
        return response

    def get(self):
        """
        Checks Infoblox for the A record

        :return: Infoblox A record in dict if exists else False
        :rtype: dict|bool
        :raises: Exception on error
        :raise: InfobloxError
        """
        fields = f'&_return_fields={self.FIELDS}'
        if self.view:
            fields = fields + f'&view={self.view}'
        if self.name:
            self.response = self.get_by_name(fields)
        elif self.ip_address:
            self.response = self.get_by_ip(fields)
        else:
            raise InfobloxDataError(self.__class__.__name__, 'name', 400)
        self.parse_reply()

    def parse_reply(self):
        result = self.parse_response(self.response)
        if isinstance(result, dict):
            if '_ref' in result:
                self.logger.debug('Record found, now setting details...')
                self.ip_address = self.is_valid_ipaddress(result.get('ipv4addr'))
                self.logger.debug('Set IP address successfully..')
                self.name = result.get('name')
                self.description = result.get('comment', '')
                self.dns_name = result.get('dns_name')
                self.zone = result.get('zone')
                self.view = result.get('view')
                self.ref = result.get('_ref')
                self.parse_extattr(result)
                self.loaded = True
            else:
                self.logger.error('reference not returned by item addition or update: %s' % self.response)
                raise InfobloxError(self.__class__.__name__, 'reference not returned by item addition or update: %s' % self.response)
        elif isinstance(result, str):
            self.ref = result
            self.loaded = True
        else:
            self.logger.error('invalid data type, not dict or string: %s' % self.response)
            raise InfobloxError(self.__class__.__name__, 'invalid data type, not dict or string: %s' % self.response)

    @hostname_check(True)
    @ip_check
    def create(self, username=None, **kwargs):
        """
        Create an A record

        :param username: username of person performing add for audit purposes
        :param kwargs: any extra attributes for the host record in key/value pairs
        :return:
        """
        super().create(username, **kwargs)
        fields = f'?_return_fields={self.FIELDS}&_return_as_object=1'
        payload = {"ipv4addr": str(self.ip_address), "extattrs": self.extattrs.to_json(), "name": self.name, "comment": self.description}
        self.response = self.client.post(f'{self.RECORD_TYPE}{fields}', payload=payload)
        self.parse_reply()

    @hostname_check(True)
    @ip_check
    def save(self, username=None, **kwargs):
        """
        Update an A record

        :param username: username of person performing add for audit purposes
        :param kwargs: any extra attributes for the host record in key/value pairs
        :return:
        """
        super().save(username, **kwargs)
        fields = f'?_return_fields={self.FIELDS}&_return_as_object=1'
        payload = {"ipv4addr": str(self.ip_address), "extattrs": self.extattrs.to_json(), "name": self.name, "comment": self.description}
        self.response = self.client.put(self.ref + fields, payload=payload)
        self.parse_reply()

    @classmethod
    def add(cls, client, name, ip_address, description=None, view='default', username=None, **extattrs):
        """
        Create a host record within Infoblox

        :param client: pyinfoblox client class
        :param name: name of host record
        :param ip_address: IPv4 IP address to assign to host
        :param description: description for the host record
        :param view: the view to place the host in
        :param username: username of person performing add for audit purposes
        :param extattrs: any extra attributes for the host record in key/value pairs
        :return: ARecord Class
        :rtype: ARecord
        """
        obj = cls(client, ip_address, name, view=view)
        obj.description = description if description else ''
        obj.create(username, **extattrs)
        return obj

    def match(self, name):
        return name == self.name

    def __str__(self):
        return self.name

    def __eq__(self, other):
        if isinstance(other, self.__class__) and self.name == other.name:
            return True
        return False


class ARecords(BaseList):
    """
    Abstraction class that should be used when dealing with lists of Infoblox A record objects.
    """
    CHILD = ARecord
    RECORD_TYPE = 'record:a'

    def __init__(self, client, **kwargs):
        super(ARecords, self).__init__(client, **kwargs)
        self.items = list()  # type: List[ARecord]
        self.logger.debug('A Records Load Complete, loglevel set to %s', logging.getLevelName(self.logger.getEffectiveLevel()))

    @classmethod
    def search_by_address(cls, client, value, view='default', limit=100, paging=0):
        return cls.search(client, 'ipv4addr', value, view=view, limit=limit, paging=paging)

    @classmethod
    def search_by_name(cls, client, value, view='default', limit=100, paging=0):
        return cls.search(client, 'name', value, view=view, regex=True, limit=limit, paging=paging)

    def __getitem__(self, item):
        super().__getitem__(item)

        for x in self.items:
            if isinstance(item, self.CHILD):
                if x.match(item.name) and item.view == x.view:
                    return x
            elif isinstance(item, str):
                if x.match(item):
                    return x
            elif isinstance(item, int):
                return self.items[item]
        raise IndexError(f'{self.CHILD.__name__} Not found')
