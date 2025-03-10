# coding: utf-8

import logging
from typing import List

from .base import hostname_check, IPHelpers, BaseList
from ..errors import InfobloxError, InfobloxDataError, IPError


class SRVRecord(IPHelpers):
    """
    Abstraction class that simplifies and unifies all access to Infoblox SRV Record objects.
    """
    FIELDS = 'name,port,priority,target,dns_name,dns_target,zone,weight,ttl,use_ttl,extattrs,comment,view'
    RECORD_TYPE = 'record:srv'

    def __init__(self, client, name, port=None, view='default', **kwargs):
        super(SRVRecord, self).__init__(client)
        self.name = name
        self.port = port
        self.priority = None
        self.target = None
        self.weight = None
        self.dns_name = None
        self.dns_target = None
        self.ttl = 0
        self.use_ttl = False
        self.description = None
        self.zone = None
        self.view = view
        self.logger.debug('SRV Record Load Complete, loglevel set to %s', logging.getLevelName(self.logger.getEffectiveLevel()))
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
            return dict(name=self.name, _ref=self.ref, port=self.port, priority=self.priority, target=self.target, weight=self.weight, dns_name=self.dns_name,
                        dns_target=self.dns_target, ttl=self.ttl, use_ttl=self.use_ttl, view=self.view, comment=self.description, zone=self.zone, extattrs=self.extattrs.to_json())
        return dict(name=self.name, ref=self.ref, port=self.port, priority=self.priority, target=self.target, weight=self.weight, dns_name=self.dns_name,
                    dns_target=self.dns_target, ttl=self.ttl, use_ttl=self.use_ttl, view=self.view, description=self.description, zone=self.zone, extattrs=self.extattrs.to_json())

    @classmethod
    def load_by_name(cls, client, name):
        """
        Static method to load a given name as a SRVRecord object and return it for use

        :param client: pyinfoblox client class
        :param name: a valid hostname
        :return: SRVRecord class, fully populated
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
                    if isinstance(h, SRVRecord):
                        self.name = h.name
                        self.port = h.port
                        self.priority = h.priority
                        self.target = h.target
                        self.weight = h.weight
                        self.dns_name = h.dns_name
                        self.dns_target = h.dns_target
                        self.ttl = h.ttl
                        self.use_ttl = h.use_ttl
                        self.view = h.view
                        self.zone = h.zone,
                        self.description = h.description
                        self.ref = h.ref
                        self.extattrs = h.extattrs
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
                    raise InfobloxDataError(self.__class__.__name__, 'SRVRecord "name" attribute missing in data structure', 400)

    @hostname_check(True)
    def get(self):
        """
        Checks Infoblox for the SRV record

        :return: Infoblox SRV record in dict if exists else False
        :rtype: dict|bool
        :raises: Exception on error
        :raise: InfobloxError
        """
        fields = f'&_return_fields={self.FIELDS}&_return_as_object=1'
        if self.view:
            fields = fields + f'&view={self.view}'
        self.response = self.client.get(f'{self.RECORD_TYPE}?name={self.name}{fields}')
        self.parse_reply()

    def parse_reply(self):
        result = self.parse_response(self.response)
        if isinstance(result, dict):
            if '_ref' in result:
                self.name = result.get('name')
                self.port = result.get('port')
                self.priority = result.get('priority')
                self.target = result.get('target')
                self.weight = result.get('weight')
                self.dns_name = result.get('dns_name')
                self.dns_target = result.get('dns_target')
                self.ttl = result.get('ttl')
                self.use_ttl = result.get('use_ttl')
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
    def create(self, username=None, **kwargs):
        """
        Create an SRV record

        :param username: username of person performing add for audit purposes
        :param kwargs: any extra attributes for the SRV record in key/value pairs
        :return:
        """
        super().create(username, **kwargs)
        fields = f'?_return_fields={self.FIELDS}&_return_as_object=1'
        payload = {"extattrs": self.extattrs.to_json(), "name": self.name, "port": self.port, "priority": self.priority, "target": self.target, "ttl": self.ttl, "use_ttl": self.use_ttl,
                   "weight": self.weight, "comment": self.description}
        self.response = self.client.post(f'{self.RECORD_TYPE}{fields}', payload=payload)
        self.parse_reply()

    @hostname_check(True)
    def save(self, username=None, **kwargs):
        """
        Update an SRV record

        :param username: username of person performing add for audit purposes
        :param kwargs: any extra attributes for the SRV record in key/value pairs
        :return:
        """
        super().save(username, **kwargs)
        fields = f'?_return_fields={self.FIELDS}&_return_as_object=1'
        payload = {"extattrs": self.extattrs.to_json(), "name": self.name, "port": self.port, "priority": self.priority, "target": self.target, "ttl": self.ttl, "use_ttl": self.use_ttl,
                   "weight": self.weight, "comment": self.description}
        self.response = self.client.put(self.ref + fields, payload=payload)
        self.parse_reply()

    @classmethod
    def add(cls, client, name, port, target, username, weight=50, priority=100, description=None, view='default', **extattrs):
        """
        Create an SRV record within Infoblox

        :param client: pyinfoblox client class
        :param name: name for SRV record
        :param port: the port for the SRV record
        :param target: the FQDN of the target for the SRV record
        :param username: username of person performing add for audit purposes
        :param weight: integer for weight of SRV record
        :param priority: integer for priority of the SRV record
        :param description: description for the host record
        :param view: the view to place the host in
        :param extattrs: any extra attributes for SRV host record in key/value pairs
        :return: SRVRecord Class
        :rtype: SRVRecord
        """
        obj = cls(client, name, port, view=view)
        obj.description = description if description else ''
        obj.target = target
        obj.weight = weight
        obj.priority = priority
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


class SRVRecords(BaseList):
    """
    Abstraction class that should be used when dealing with lists of Infoblox SRV record objects.
    """
    CHILD = SRVRecord
    RECORD_TYPE = 'record:srv'

    def __init__(self, client, **kwargs):
        super(SRVRecords, self).__init__(client, **kwargs)
        self.items = list()  # type: List[SRVRecord]
        self.logger.debug('SRV Records Load Complete, loglevel set to %s', logging.getLevelName(self.logger.getEffectiveLevel()))

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
