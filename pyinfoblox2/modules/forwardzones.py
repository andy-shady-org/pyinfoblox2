# coding: utf-8

import logging
from typing import List

from .base import IPHelpers, BaseList, fqdn_check
from ..errors import InfobloxError, InfobloxDataError, IPError


class ForwardZone(IPHelpers):
    """

    Abstraction class that simplifies and unifies all access to Infoblox ForwardZone objects.

    """
    FIELDS = 'fqdn,extattrs,comment,forwarders_only,forwarding_servers,ns_group,parent,zone_format,disable,view'
    RECORD_TYPE = 'zone_forward'

    def __init__(self, client, fqdn, view='default', **kwargs):
        super(ForwardZone, self).__init__(client)
        self.fqdn = fqdn
        self.description = None
        self.disable = False
        self.forwarders_only = True
        self.forwarding_servers = list()
        self.ns_group = None
        self.parent = None
        self.zone_format = None
        self.view = view
        self.data = kwargs
        self.logger.debug('ForwardZone Load Complete, loglevel set to %s', logging.getLevelName(self.logger.getEffectiveLevel()))

    def to_json(self, original_format=False):
        """
        Returns class items as dict structure

        :param original_format: keep original formal
        :type original_format: bool
        :return: class as dict structure
        :rtype: dict
        """
        if original_format:
            return dict(fqdn=self.fqdn, _ref=self.ref, comment=self.description, view=self.view, extattrs=self.extattrs.to_json(), disable=self.disable, forwarders_only=self.forwarders_only,
                        forwarding_servers=self.forwarding_servers, ns_group=self.ns_group, parent=self.parent, zone_format=self.zone_format)
        return dict(fqdn=self.fqdn, ref=self.ref, description=self.description, view=self.view, extattrs=self.extattrs.to_json(), disable=self.disable, forwarders_only=self.forwarders_only,
                    forwarding_servers=self.forwarding_servers, ns_group=self.ns_group, parent=self.parent, zone_format=self.zone_format)

    @classmethod
    def load_by_name(cls, client, name):
        """
        Static method to load a given hostname as a ForwardZone object and return it for use

        :param client: pyinfoblox client class
        :param name: a valid zone name
        :return: ForwardZone class, fully populated
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
                    if isinstance(h, ForwardZone):
                        self.fqdn = h.fqdn
                        self.view = h.view
                        self.description = h.description
                        self.disable = h.disable
                        self.forwarders_only = h.forwarders_only
                        self.forwarding_servers = h.forwarding_servers
                        self.ns_group = h.ns_group
                        self.parent = h.parent
                        self.zone_format = h.zone_format
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
                    raise InfobloxDataError(self.__class__.__name__, 'ForwardZone "fqdn" attribute missing in data structure', 400)

    @fqdn_check()
    def get(self):
        """
        Checks Infoblox for the zone record

        :return: Infoblox ForwardZones record in dict if exists else False
        :rtype: dict|bool
        :raises: Exception on error
        :raise: InfobloxError
        """

        fields = f'?_return_fields={self.FIELDS}&_return_as_object=1&fqdn={self.fqdn}'
        if self.view:
            fields = fields + f'&view={self.view}'
        self.response = self.client.get(f'{self.RECORD_TYPE}{fields}')
        self.parse_reply()

    def parse_reply(self):
        result = self.parse_response(self.response)
        if isinstance(result, dict):
            if '_ref' in result:
                self.logger.debug('Record found, now setting details...')
                self.description = result.get('comment', '')
                self.view = result.get('view')
                self.fqdn = result.get('fqdn')
                self.disable = result.get('disable')
                self.forwarders_only = result.get('forwarders_only')
                self.forwarding_servers = result.get('forwarding_servers')
                self.ns_group = result.get('ns_group')
                self.parent = result.get('parent')
                self.zone_format = result.get('zone_format')
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

    def match(self, fqdn):
        return fqdn == self.fqdn

    def __str__(self):
        return self.fqdn

    def __eq__(self, other):
        if isinstance(other, self.__class__) and self.fqdn == other.fqdn:
            return True
        return False


class ForwardZones(BaseList):
    """
    Abstraction class that should be used when dealing with lists of Infoblox ForwardZone objects.
    """
    CHILD = ForwardZone
    RECORD_TYPE = 'zone_forward'

    def __init__(self, client, **kwargs):
        super(ForwardZones, self).__init__(client, **kwargs)
        self.items = list()  # type: List[ForwardZone]
        self.logger.debug('ForwardZones Load Complete, loglevel set to %s', logging.getLevelName(self.logger.getEffectiveLevel()))

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
