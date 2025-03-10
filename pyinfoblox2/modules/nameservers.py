# coding: utf-8

import logging
from typing import List

from .base import IPHelpers, BaseList, hostname_check
from ..errors import InfobloxError, InfobloxDataError, IPError


class NameServer(IPHelpers):
    """
    Abstraction class that simplifies and unifies all access to Infoblox NS Record objects.
    """
    FIELDS = 'name,addresses,creator,nameserver,zone,view'
    RECORD_TYPE = 'record:ns'

    def __init__(self, client, name, view='default', **kwargs):
        super(NameServer, self).__init__(client)
        self.name = name
        self.addresses = None
        self.creator = None
        self.nameserver = None
        self.zone = None
        self.view = view
        self.logger.debug('NS Record Load Complete, loglevel set to %s', logging.getLevelName(self.logger.getEffectiveLevel()))
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
            return dict(name=self.name, _ref=self.ref, addresses=self.addresses, creator=self.creator, nameserver=self.nameserver,
                        zone=self.zone, view=self.view)
        return dict(name=self.name, ref=self.ref, addresses=self.addresses, creator=self.creator, nameserver=self.nameserver,
                    zone=self.zone, view=self.view)

    @classmethod
    def load_by_name(cls, client, name):
        """
        Static method to load a given name as a NSRecord object and return it for use

        :param client: pyinfoblox client class
        :param name: a valid hostname
        :return: NSRecord class, fully populated
        """
        if not IPHelpers.is_valid_hostname(name):
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
                    if isinstance(h, NameServer):
                        self.name = h.name
                        self.addresses = h.addresses
                        self.creator = h.creator
                        self.nameserver = h.nameserver
                        self.zone = h.zone
                        self.view = h.view
                        self.ref = h.ref
                        self.loaded = True
                except InfobloxError:
                    raise
            elif 'name' in json_data and json_data.get('name', '').strip():
                self.name = json_data.get('name', '').strip()
                try:
                    self.get()
                except InfobloxError:
                    return False
            else:
                if not self.ref:
                    raise InfobloxDataError(self.__class__.__name__, 'NameServer "name" attribute missing in data structure', 400)

    @hostname_check()
    def get(self):
        """
        Checks Infoblox for the NS record

        :return: Infoblox NS record in dict if exists else False
        :rtype: dict|bool
        :raises: Exception on error
        :raise: InfobloxError
        """
        fields = f'&_return_fields={self.FIELDS}&_return_as_object=1'
        if self.view:
            fields = fields + f'&view={self.view}'
        self.response = self.client.get(f'{self.RECORD_TYPE}?name={self.name}{fields}&_return_as_object=1')
        self.parse_reply()

    def parse_reply(self):
        result = self.parse_response(self.response)
        if isinstance(result, dict):
            if '_ref' in result:
                self.name = result.get('name')
                self.addresses = result.get('addresses')
                self.creator = result.get('creator')
                self.nameserver = result.get('nameserver')
                self.zone = result.get('zone')
                self.view = result.get('view')
                self.ref = result.get('_ref')
            else:
                self.logger.error('reference not returned by item addition or update: %s' % self.response)
                raise InfobloxError(self.__class__.__name__, 'reference not returned by item addition or update: %s' % self.response)
        elif isinstance(result, str):
            self.ref = result
        else:
            self.logger.error('invalid data type, not dict or string: %s' % self.response)
            raise InfobloxError(self.__class__.__name__, 'invalid data type, not dict or string: %s' % self.response)
        self.loaded = True

    def create(self, username=None, **kwargs):
        """
        Create an NS record

        :param username: username of person performing add for audit purposes
        :param kwargs: any extra attributes for the NS record in key/value pairs
        :return:
        """
        super().create(username, **kwargs)
        self.is_valid_hostname(self.nameserver)
        self.is_valid_ipaddress(self.addresses.get('ip_address'))
        fields = f'?_return_fields={self.FIELDS}&_return_as_object=1'
        payload = {"name": self.name, "addresses": self.addresses, "creator": self.creator, "nameserver": self.nameserver, "zone": self.zone}
        self.response = self.client.post(f'{self.RECORD_TYPE}{fields}', payload=payload)
        self.parse_reply()

    def save(self, username=None, **kwargs):
        """
        Update an NS record

        :param username: username of person performing add for audit purposes
        :param kwargs: any extra attributes for the NS record in key/value pairs
        :return:
        """
        super().save(username, **kwargs)
        self.is_valid_hostname(self.nameserver)
        self.is_valid_ipaddress(self.addresses.get('ip_address'))
        fields = f'?_return_fields={self.FIELDS}&_return_as_object=1'
        payload = {"name": self.name, "addresses": self.addresses, "creator": self.creator, "nameserver": self.nameserver, "zone": self.zone}
        self.response = self.client.put(self.ref + fields, payload=payload)
        self.parse_reply()

    @classmethod
    def add(cls, client, name, nameserver, ip_address, zone, days=1, view='default', username=None):
        """
        Create a NS record within Infoblox

        :param client: pyinfoblox client class
        :param name: name for NS record
        :param nameserver: the name of the NS server
        :param ip_address: the IP of the NS server
        :param days: the number of days that the record should roll over in
        :param zone: the name of the zone
        :param view: the view to place the host in
        :param username: username of person performing add for audit purposes
        :return: NameServer Class
        :rtype: NameServer
        """
        obj = cls(client, name, view=view)
        obj.nameserver = nameserver
        obj.addresses = dict(address=str(NameServer.is_valid_ipaddress(ip_address)), zone=zone, days=days)
        obj.create(username)
        return obj

    def match(self, name):
        return name == self.name

    def __str__(self):
        return self.name

    def __eq__(self, other):
        if isinstance(other, self.__class__) and self.name == other.name:
            return True
        return False


class NameServers(BaseList):
    """
    Abstraction class that should be used when dealing with lists of Infoblox NS Record objects.
    """
    CHILD = NameServer
    RECORD_TYPE = 'record:ns'

    def __init__(self, client, **kwargs):
        super(NameServers, self).__init__(client, **kwargs)
        self.items = list()  # type: List[NameServer]
        self.logger.debug('Nameserver Records Load Complete, loglevel set to %s', logging.getLevelName(self.logger.getEffectiveLevel()))

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
