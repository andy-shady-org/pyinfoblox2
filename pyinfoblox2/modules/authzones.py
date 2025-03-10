# coding: utf-8

import logging
from typing import List

from .base import IPHelpers, BaseList
from ..errors import InfobloxError, InfobloxDataError, IPError


class AuthZone(IPHelpers):
    """

    Abstraction class that simplifies and unifies all access to Infoblox AuthZone objects.

    """
    FIELDS = 'fqdn,ns_group,zone_format,grid_primary,external_primaries,external_secondaries,extattrs,comment,view'
    RECORD_TYPE = 'zone_auth'

    def __init__(self, client, fqdn, view='default', **kwargs):
        super(AuthZone, self).__init__(client)
        self.fqdn = fqdn
        self.ns_group = None
        self.zone_format = None
        self.grid_primary = list()
        self.external_primaries = list()
        self.external_secondaries = list()
        self.description = None
        self.view = view
        self.data = kwargs
        self.logger.debug('AuthZone Load Complete, loglevel set to %s', logging.getLevelName(self.logger.getEffectiveLevel()))

    def to_json(self, original_format=False):
        """
        Returns class items as dict structure

        :param original_format: keep original formal
        :type original_format: bool
        :return: class as dict structure
        :rtype: dict
        """
        if original_format:
            return dict(fqdn=self.fqdn, _ref=self.ref, comment=self.description, ns_group=self.ns_group,
                        zone_format=self.zone_format, grid_primary=self.grid_primary, external_primaries=self.external_primaries,
                        external_secondaries=self.external_secondaries, view=self.view, extattrs=self.extattrs.to_json())
        return dict(name=self.fqdn, ref=self.ref, description=self.description, ns_group=self.ns_group,
                    zone_format=self.zone_format, grid_primary=self.grid_primary, external_primaries=self.external_primaries,
                    external_secondaries=self.external_secondaries, view=self.view, extattrs=self.extattrs.to_json())

    @classmethod
    def load_by_name(cls, client, name):
        """
        Static method to load a given name as AuthZone object and return it for use

        :param client: pyinfoblox client class
        :param name: a valid AuthZone FQDN
        :return: AuthZone class, fully populated
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
                    if isinstance(h, AuthZone):
                        self.fqdn = h.fqdn
                        self.ns_group = h.ns_group
                        self.zone_format = h.zone_format
                        self.grid_primary = h.grid_primary
                        self.external_primaries = h.external_primaries
                        self.external_secondaries = h.external_secondaries
                        self.view = h.view
                        self.description = h.description
                        self.ref = h.ref
                        self.extattrs = h.extattrs
                        self.loaded = True
                except InfobloxError:
                    return False
            elif 'fqdn' in json_data and json_data.get('fqdn', '').strip():
                self.fqdn = json_data.get('fqdn', '').strip()
                try:
                    self.get()
                except InfobloxError:
                    return False
            else:
                if not self.ref:
                    raise InfobloxDataError(self.__class__.__name__, 'AuthZone "fqdn" attribute missing in data structure', 400)

    def get(self):
        """
        Checks Infoblox for the zone record

        :return: Infoblox AuthZone record in dict if exists else False
        :rtype: dict|bool
        :raises: Exception on error
        :raise: InfobloxError
        """

        fields = f'?_return_fields={self.FIELDS}&_return_as_object=1&fqdn={self.fqdn}'
        if self.view:
            fields = fields + f'&view={self.view}'
        self.response = self.client.get(f'{self.RECORD_TYPE}{fields}')
        self.parse_reply()

    def parse_reply(self, direct=False):
        if direct:
            result = self.response
        else:
            result = self.parse_response(self.response)
        if isinstance(result, dict):
            if '_ref' in result:
                self.logger.debug('Record found, now setting details...')
                self.description = result.get('comment', '')
                self.view = result.get('view')
                self.fqdn = result.get('fqdn')
                self.ns_group = result.get('ns_group')
                self.zone_format = result.get('zone_format')
                self.grid_primary = result.get('grid_primary')
                self.external_primaries = result.get('external_primaries')
                self.external_secondaries = result.get('external_secondaries')
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

    def create(self, username=None, **kwargs):
        """
        Create AuthZone record in Infoblox

        :param username: username of person performing add for audit purposes
        :param kwargs: any extra attributes for the host record in key/value pairs
        :return:
        """
        super().create(username, **kwargs)
        fields = f'?_return_fields={self.FIELDS}&_return_as_object=1'
        payload = {"extattrs": self.extattrs.to_json(), "fqdn": self.fqdn, "ns_group": self.ns_group, "zone_format": self.zone_format, "comment": self.description}
        self.response = self.client.post(f'{self.RECORD_TYPE}{fields}', payload=payload)
        self.parse_reply()

    def save(self, username=None, **kwargs):
        """
        Update a AuthZone record

        :param username: username of person performing add for audit purposes
        :param kwargs: any extra attributes for the host record in key/value pairs
        :return:
        """
        super().save(username, **kwargs)
        fields = f'?_return_fields={self.FIELDS}&_return_as_object=1'
        payload = {"extattrs": self.extattrs.to_json(), "fqdn": self.fqdn, "ns_group": self.ns_group, "zone_format": self.zone_format, "comment": self.description}
        self.response = self.client.put(self.ref + fields, payload=payload)
        self.parse_reply()

    @classmethod
    def add(cls, client, fqdn, ns_group, zone_format='IPv4', description=None, view='default', username=None, **extattrs):
        """
        Create a AuthZone record within Infoblox

        :param client: pyinfoblox client class
        :param fqdn: fqdn of zone record
        :param ns_group: the name server group that serves DNS for this zone
        :param zone_format: the format of the zone, IPv4, IPv6 or FORWARD
        :param description: description for the zone record
        :param view: the view to place the host in
        :param username: username of person performing add for audit purposes
        :param extattrs: any extra attributes for the host record in key/value pairs
        :return: AuthZone class
        :rtype: AuthZone
        """
        obj = cls(client, fqdn, view=view)
        obj.description = description if description else ''
        obj.ns_group = ns_group
        obj.zone_format = zone_format
        obj.create(username, **extattrs)
        return obj

    def match(self, fqdn):
        return fqdn == self.fqdn

    def __str__(self):
        return self.fqdn

    def __eq__(self, other):
        if isinstance(other, self.__class__) and self.fqdn == other.fqdn:
            return True
        return False


class AuthZones(BaseList):
    """
    Abstraction class that should be used when dealing with lists of Infoblox AuthZone objects.
    """
    CHILD = AuthZone
    RECORD_TYPE = 'zone_auth'

    def __init__(self, client, **kwargs):
        super(AuthZones, self).__init__(client, **kwargs)
        self.items = list()  # type: List[AuthZone]
        self.logger.debug('AuthZones Load Complete, loglevel set to %s', logging.getLevelName(self.logger.getEffectiveLevel()))

    @classmethod
    def search_by_name(cls, client, value, view='default', limit=100, paging=0):
        return cls.search(client, 'fqdn', value, view=view, limit=limit, paging=paging)

    def __getitem__(self, item):
        super().__getitem__(item)

        for x in self.items:
            if isinstance(item, self.CHILD):
                if x.match(item.fqdn) and item.view == x.view:
                    return x
            elif isinstance(item, str):
                if x.match(item):
                    return x
            elif isinstance(item, int):
                return self.items[item]
        raise IndexError(f'{self.CHILD.__name__} Not found')

    def __contains__(self, item):
        result = [x.fqdn for x in self.items]
        return result.__contains__(item)
