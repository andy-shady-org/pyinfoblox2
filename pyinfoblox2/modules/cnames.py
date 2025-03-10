# coding: utf-8

import logging
from typing import List

from .base import fqdn_check, IPHelpers, BaseList
from ..errors import InfobloxClientError, InfobloxError, InfobloxDataError, IPError


class Cname(IPHelpers):
    """
    Abstraction class that simplifies and unifies all access to Infoblox CNAME objects.
    """
    FIELDS = 'name,extattrs,comment,canonical,ttl,view,disable,zone'
    RECORD_TYPE = 'record:cname'

    def __init__(self, client, name, view='default', **kwargs):
        super(Cname, self).__init__(client)
        self.client = client
        self.name = name
        self.canonical = None
        self.description = None
        self.ttl = 0
        self.disable = False
        self.zone = None
        self.view = view
        self.data = kwargs
        self.logger.debug('Cname Load Complete, loglevel set to %s', logging.getLevelName(self.logger.getEffectiveLevel()))

    def to_json(self, original_format=False):
        """
        Returns class items as dict structure

        :param original_format: keep original formal
        :type original_format: bool
        :return: class as dict structure
        :rtype: dict
        """
        if original_format:
            return dict(name=self.name, _ref=self.ref, canonical=self.canonical, ttl=self.ttl, view=self.view, comment=self.description, diable=self.disable, zone=self.zone, extattrs=self.extattrs.to_json())
        return dict(name=self.name, ref=self.ref, canonical=self.canonical, ttl=self.ttl, view=self.view, description=self.description, diable=self.disable, zone=self.zone, extattrs=self.extattrs.to_json())

    @classmethod
    def load_by_name(cls, client, name):
        """
        Static method to load a given cname as a CNAME object and return it for use

        :param client: pyinfoblox client class
        :param name: a valid hostname
        :return: CNAME class, fully populated
        """
        if not IPHelpers.is_valid_hostname(name, True, True):
            raise IPError('Invalid hostname format: Failed REGEX checks')
        return super(cls, cls).load_by_name(client, name)

    @classmethod
    def load_by_canonical(cls, client, canonical):
        """
        Static method to load a given cname as a CNAME object and return it for use

        :param client: pyinfoblox client class
        :param canonical: a valid hostname
        :return: CNAME class, fully populated
        """
        if not cls.is_valid_hostname(canonical, True, True):
            raise IPError('Invalid hostname format: Failed REGEX checks')
        h = cls(client, None)
        h.canonical = canonical
        try:
            h.get_by_canonical()
        except (InfobloxError, InfobloxClientError):
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
                    if isinstance(h, Cname):
                        self.name = h.name
                        self.view = h.view
                        self.description = h.description
                        self.ref = h.ref
                        self.canonical = h.canonical
                        self.ttl = h.ttl
                        self.disable = h.disable
                        self.zone = h.zone
                        self.extattrs = h.extattrs
                        self.loaded = True
                except InfobloxError:
                    return False
            elif 'hostname' in json_data and json_data.get('hostname', '').strip():
                self.name = json_data.get('hostname', '').strip()
                try:
                    self.is_valid_fqdn(self.name)
                except IPError:
                    return False
                try:
                    self.get()
                except InfobloxError:
                    return False
            else:
                if not self.ref:
                    raise InfobloxDataError(self.__class__.__name__, 'Cname "hostname" attribute missing in data structure', 400)

    @fqdn_check(True, True)
    def get(self):
        """
        Checks Infoblox for the CNAME record

        :return: Infoblox CNAME record in dict if exists else False
        :rtype: dict|bool
        :raises: Exception on error
        :raise: InfobloxError
        """
        fields = f'&_return_fields={self.FIELDS}&_return_as_object=1'
        if self.view:
            fields = fields + f'&view={self.view}'
        self.response = self.client.get(f'{self.RECORD_TYPE}?name={self.name}{fields}')
        self.parse_reply()

    @fqdn_check(True, True)
    def get_by_canonical(self):
        """
        Checks Infoblox for the CNAME record

        :return: Infoblox CNAME record in dict if exists else False
        :rtype: dict|bool
        :raises: Exception on error
        :raise: InfobloxError
        """
        fields = f'&_return_fields={self.FIELDS}&_return_as_object=1'
        if self.view:
            fields = fields + f'&view={self.view}'
        self.response = self.client.get(f'{self.RECORD_TYPE}?canonical={self.canonical}{fields}')
        self.parse_reply()

    def parse_reply(self):
        result = self.parse_response(self.response)
        if isinstance(result, dict):
            if '_ref' in result:
                self.logger.debug('Record found, now setting details...')
                if not self.is_valid_hostname(result.get('name'), True, True):
                    raise InfobloxError(self.__class__.__name__, '"name"')
                self.canonical = result.get('canonical')
                self.ttl = result.get('ttl', 0)
                self.description = result.get('comment', '')
                self.view = result.get('view')
                self.name = result.get('name')
                self.disable = result.get('disable')
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

    @fqdn_check(True, True)
    def create(self, username=None, **kwargs):
        """
        Create CNAME record

        :param username: username of person performing add for audit purposes
        :param kwargs: any extra attributes for the CNAME record in key/value pairs
        :return:
        """
        super().create(username, **kwargs)
        fields = f'?_return_fields={self.FIELDS}&_return_as_object=1'
        payload = {"extattrs": self.extattrs.to_json(), "name": self.name, "canonical": self.canonical, "comment": self.description, "disable": self.disable}
        self.response = self.client.post(f'{self.RECORD_TYPE}{fields}', payload=payload)
        self.parse_reply()

    @fqdn_check(True, True)
    def save(self, username=None, **kwargs):
        """
        Update CNAME record

        :param username: username of person performing add for audit purposes
        :param kwargs: any extra attributes for the CNAME record in key/value pairs
        :return:
        """
        super().save(username, **kwargs)
        fields = f'?_return_fields={self.FIELDS}&_return_as_object=1'
        payload = {"extattrs": self.extattrs.to_json(), "name": self.name, "canonical": self.canonical, "comment": self.description, "disable": self.disable}
        self.response = self.client.put(self.ref + fields, payload=payload)
        self.parse_reply()

    @classmethod
    def add(cls, client, cname, canonical, description=None, disable=False, view='default', username=None, **extattrs):
        """
        Add a CNAME Record

        :param client: pyinfoblox client class
        :param cname: cname record string
        :param canonical: the host name string that it should point to
        :param description: description for the record
        :param disable: whether the record should be disabled
        :param view: the view to place the host in
        :param username: username of person performing add for audit purposes
        :param extattrs: any extra attributes for the CNAME record in key/value pairs
        :return: Cname class
        :rtype: Cname
        """
        obj = cls(client, cname, view=view)
        obj.canonical = canonical
        obj.description = description if description else ''
        obj.disable = disable
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


class Cnames(BaseList):
    """
    Abstraction class that should be used when dealing with lists of Infoblox CNAME objects.
    """
    CHILD = Cname
    RECORD_TYPE = 'record:cname'

    def __init__(self, client, **kwargs):
        super().__init__(client, **kwargs)
        self.items = list()  # type: List[Cname]
        self.logger.debug('Canonical Names Load Complete, loglevel set to %s', logging.getLevelName(self.logger.getEffectiveLevel()))

    @classmethod
    def search_by_name(cls, client, value, view='default', limit=100, paging=0):
        return cls.search(client, 'name', value, view=view, regex=True, limit=limit, paging=paging)

    @classmethod
    def search_by_canonical(cls, client, value, view='default', limit=100, paging=0):
        return cls.search(client, 'canonical', value, view=view, regex=True, limit=limit, paging=paging)

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
