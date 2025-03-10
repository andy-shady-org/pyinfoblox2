# coding: utf-8

import logging
from typing import List

from .base import hostname_check, ip_check, IPHelpers, BaseList
from ..errors import InfobloxClientError, InfobloxError, InfobloxDataError, IPError


class PTRRecord(IPHelpers):
    """
    Abstraction class that simplifies and unifies all access to Infoblox PTR Record objects.
    """
    FIELDS = 'ptrdname,name,ipv4addr,ipv6addr,zone,view'
    RECORD_TYPE = 'record:ptr'

    def __init__(self, client, ptrdname, ip_address=None, ip_address_v6=None, view='default', **kwargs):
        super(PTRRecord, self).__init__(client)
        self.ptrdname = ptrdname
        self.name = None
        self.ip_address = None
        self.ip_address_v6 = None
        if ip_address:
            self.ip_address = PTRRecord.is_valid_ipaddress(ip_address)
        if ip_address_v6:
            self.ip_address_v6 = PTRRecord.is_valid_ipaddressv6(ip_address_v6)
        self.description = None
        self.view = view
        self.zone = None
        self.logger.debug('PTR Record Load Complete, loglevel set to %s', logging.getLevelName(self.logger.getEffectiveLevel()))
        self.data = kwargs

    def to_json(self, original_format=False):
        """
        Returns class items as dict structure

        :param original_format: keep original formal
        :type original_format: bool
        :return: class as dict structure
        :rtype: dict
        """
        if original_format:
            return dict(name=self.name, _ref=self.ref, description=self.description, ipv4addr=str(self.ip_address) if self.ip_address else None,
                        ipv6addr=str(self.ip_address_v6) if self.ip_address_v6 else None, ptrdname=self.ptrdname, view=self.view, zone=self.zone, extattrs=self.extattrs.to_json())
        return dict(name=self.name, ref=self.ref, description=self.description, ip_address=str(self.ip_address) if self.ip_address else None,
                    ip_address_v6=str(self.ip_address_v6) if self.ip_address_v6 else None, ptrdname=self.ptrdname, view=self.view, zone=self.zone, extattrs=self.extattrs.to_json())

    @classmethod
    def load(cls, client, value, callout=True):
        """
        Static method to load a given PTR Record either by value of using an existing object

        :param client: pyinfoblox client class
        :param value: a valid ip_address or hostname value string or PTRRecord class
        :param callout: Call out to WAPI to retrieve data, default=True
        :return: PTRRecord class, fully populated or False if record does not exist
        """
        try:
            if value and PTRRecord.is_valid_ipaddress(value):
                a = PTRRecord.load_by_address(client, value)
                return a
        except IPError:
            pass
        return super(cls, cls).load(client, value, callout)

    @classmethod
    def load_by_address(cls, client, ip_address):
        """
        Static method to load a given PTR object and return it for use

        :param client: pyinfoblox client class
        :param ip_address: IPv4 address
        :return: PTRRecord class, fully populated
        """
        ip_address = cls.is_valid_ipaddress(ip_address)
        c = cls(client, None, str(ip_address))
        try:
            c.get()
        except (InfobloxError, InfobloxClientError):
            return False
        return c

    @classmethod
    def load_by_name(cls, client, name):
        """
        Static method to load a given name as a PTRRecord object and return it for use

        :param client: pyinfoblox client class
        :param name: a valid hostname
        :return: PTRRecord class, fully populated
        """
        if not cls.is_valid_hostname(name):
            raise IPError('Invalid hostname format: Failed REGEX checks')
        return super(cls, cls).load_by_name(client, name)

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
                    if isinstance(h, PTRRecord):
                        self.ip_address = h.ip_address
                        self.ip_address_v6 = h.ip_address_v6
                        self.ptrdname = h.ptrdname
                        self.name = h.name
                        self.view = h.view
                        self.zone = h.zone
                        self.description = h.description
                        self.ref = h.ref
                        self.extattrs = h.extattrs
                        self.loaded = True
                except InfobloxError:
                    raise
            elif 'ptrdname' in json_data and json_data.get('ptrdname', '').strip():
                self.ptrdname = json_data.get('ptrdname', '').strip()
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
            elif 'ip_address_v6' in json_data and json_data.get('ip_address_v6', '').strip():
                self.ip_address_v6 = json_data.get('ip_address_v6', '').strip()
                try:
                    self.get()
                except InfobloxError:
                    return False
            elif 'name' in json_data and json_data.get('name', '').strip():
                self.name = json_data.get('name', '').strip()
                try:
                    self.get()
                except InfobloxError:
                    return False
            else:
                if not self.ref:
                    raise InfobloxDataError(self.__class__.__name__, 'PTRRecord "hostname" attribute missing in data structure', 400)

    def get(self):
        """
        Checks Infoblox for the PTR record

        :return: Infoblox PTR record in dict if exists else False
        :rtype: dict|bool
        :raises: Exception on error
        :raise: InfobloxError
        """
        fields = f'&_return_fields={self.FIELDS}&_return_as_object=1'
        if self.view:
            fields = fields + f'&view={self.view}'
        if self.pname and self.is_valid_hostname(self.pname):
            self.response = self.client.get(f'{self.RECORD_TYPE}?ptrdname={self.pname}{fields}')
        elif self.ip_address:
            self.response = self.client.get(f'{self.RECORD_TYPE}?ipv4addr={self.ip_address}{fields}')
        elif self.ip_address_v6:
            self.response = self.client.get(f'{self.RECORD_TYPE}?ipv6addr={self.ip_address_v6}{fields}')
        elif self.name:
            self.response = self.client.get(f'{self.RECORD_TYPE}?name={self.name}{fields}')
        else:
            raise InfobloxDataError(self.__class__.__name__, 'name', 400)
        self.parse_reply()

    def parse_reply(self):
        result = self.parse_response(self.response)
        if isinstance(result, dict):
            if '_ref' in result:
                if result.get('ipv4addr'):
                    self.ip_address = self.is_valid_ipaddress(result.get('ipv4addr'))
                elif result.get('ipv6addr'):
                    self.ip_address_v6 = self.is_valid_ipaddressv6(result.get('ipv6addr'))
                self.ptrdname = result.get('ptrdname')
                self.name = result.get('name')
                self.description = result.get('comment', '')
                self.view = result.get('view')
                self.zone = result.get('zone')
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

    @hostname_check(True)
    @ip_check
    def create(self, username=None, **kwargs):
        """
        Create a PTR record

        :param username: username of person performing add for audit purposes
        :param kwargs: any extra attributes for the PTR record in key/value pairs
        :return:
        """
        super().create(username, **kwargs)
        fields = f'?_return_fields={self.FIELDS}&_return_as_object=1'
        payload = {"extattrs": self.extattrs.to_json(), "ptrdname": self.ptrdname, "name": self.name, "comment": self.description}
        if self.ip_address:
            payload.update(ipv4addr=str(self.ip_address))
        if self.ip_address_v6:
            payload.update(ipv6addr=str(self.ip_address_v6))
        self.response = self.client.post(f'{self.RECORD_TYPE}{fields}', payload=payload)
        self.parse_reply()

    @hostname_check(True)
    @ip_check
    def save(self, username=None, **kwargs):
        """
        Update a PTR record

        :param username: username of person performing add for audit purposes
        :param kwargs: any extra attributes for the PTR record in key/value pairs
        :return:
        """
        super().save(username, **kwargs)
        fields = f'?_return_fields={self.FIELDS}&_return_as_object=1'
        payload = {"extattrs": self.extattrs.to_json(), "ptrdname": self.ptrdname, "name": self.name, "comment": self.description}
        if self.ip_address:
            payload.update(ipv4addr=str(self.ip_address))
        if self.ip_address_v6:
            payload.update(ipv6addr=str(self.ip_address_v6))
        self.response = self.client.put(self.ref + fields, payload=payload)
        self.parse_reply()

    @classmethod
    def add(cls, client, ptrdname, ip_address, description=None, view='default', v6=False, username=None, **extattrs):
        """
        Create a PTR record within Infoblox

        :param client: pyinfoblox client class
        :param ptrdname: ptrdname for PTR record
        :param ip_address: IPv4 IP address to assign to PTR record
        :param description: description for the PTR record
        :param view: the view to place the PTR record in
        :param v6: is the record a v6 address
        :param username: username of person performing add for audit purposes
        :param extattrs: any extra attributes for the PTR record in key/value pairs
        :return: PTRRecord Class
        :rtype: PTRRecord
        """
        if v6:
            obj = cls(client, ptrdname, None, ip_address, view=view)
        else:
            obj = cls(client, ptrdname, ip_address, view=view)
        obj.description = description if description else ''
        obj.create(username, **extattrs)
        return obj

    def match(self, ptrdname):
        return ptrdname == self.ptrdname

    def __str__(self):
        return self.ptrdname

    def __eq__(self, other):
        if isinstance(other, self.__class__) and self.name == other.name:
            return True
        return False


class PTRRecords(BaseList):
    """
    Abstraction class that should be used when dealing with lists of Infoblox PTR record objects.
    """
    CHILD = PTRRecord
    RECORD_TYPE = 'record:ptr'

    def __init__(self, client, **kwargs):
        super(PTRRecords, self).__init__(client, **kwargs)
        self.items = list()  # type: List[PTRRecord]
        self.logger.debug('PTR Records Load Complete, loglevel set to %s', logging.getLevelName(self.logger.getEffectiveLevel()))

    @classmethod
    def search_by_address(cls, client, value, view='default', limit=100, paging=0):
        return cls.search(client, 'ipv4addr', value, view=view, limit=limit, paging=paging)

    @classmethod
    def search_by_v6_address(cls, client, value, view='default', limit=100, paging=0):
        return cls.search(client, 'ipv6addr', value, view=view, limit=limit, paging=paging)

    @classmethod
    def search_by_name(cls, client, value, view='default', limit=100, paging=0):
        return cls.search(client, 'name', value, view=view, regex=True, limit=limit, paging=paging)

    @classmethod
    def search_by_ptrdname(cls, client, value, view='default', limit=100, paging=0):
        return cls.search(client, 'ptrdname', value, view=view, regex=True, limit=limit, paging=paging)

    def __getitem__(self, item):
        super().__getitem__(item)

        for x in self.items:
            if isinstance(item, self.CHILD):
                if x.match(item.ptrdname) and item.view == x.view:
                    return x
            elif isinstance(item, str):
                if x.match(item):
                    return x
            elif isinstance(item, int):
                return self.items[item]
        raise IndexError(f'{self.CHILD.__name__} Not found')

    def __contains__(self, item):
        result = [x.ptrdname for x in self.items]
        return result.__contains__(item)
