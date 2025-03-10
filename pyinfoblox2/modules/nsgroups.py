# coding: utf-8

import logging
from typing import List

from .base import IPHelpers, BaseList
from ..errors import InfobloxError, InfobloxDataError


class NSGroup(IPHelpers):
    """
    Abstraction class that simplifies and unifies all access to Infoblox NS Group Record objects.
    """
    FIELDS = 'name,external_primaries,external_secondaries,grid_primary,grid_secondaries,is_grid_default,is_multimaster,use_external_primary,comment,extattrs,view'
    RECORD_TYPE = 'nsgroup'

    def __init__(self, client, name, view='default', **kwargs):
        super(NSGroup, self).__init__(client)
        self.name = name
        self.description = None
        self.external_primaries = list()
        self.external_secondaries = list()
        self.grid_primary = list()
        self.grid_secondaries = list()
        self.is_grid_default = False
        self.is_multimaster = False
        self.use_external_primary = False
        self.view = view
        self.logger.debug('NS Group Record Load Complete, loglevel set to %s', logging.getLevelName(self.logger.getEffectiveLevel()))
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
            return dict(name=self.name, _ref=self.ref, description=self.description, external_primaries=self.external_primaries, external_secondaries=self.external_secondaries,
                        grid_primary=self.grid_primary, grid_secondaries=self.grid_secondaries, is_grid_default=self.is_grid_default,
                        is_multimaster=self.is_multimaster, use_external_primary=self.use_external_primary, view=self.view, extattrs=self.extattrs.to_json())
        return dict(name=self.name, ref=self.ref, description=self.description, external_primaries=self.external_primaries, external_secondaries=self.external_secondaries,
                    grid_primary=self.grid_primary, grid_secondaries=self.grid_secondaries, is_grid_default=self.is_grid_default,
                    is_multimaster=self.is_multimaster, use_external_primary=self.use_external_primary, view=self.view, extattrs=self.extattrs.to_json())

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
                    if isinstance(h, NSGroup):
                        self.name = h.name
                        self.external_primaries = h.external_primaries
                        self.external_secondaries = h.external_secondaries
                        self.grid_primary = h.grid_primary
                        self.grid_secondaries = h.grid_secondaries
                        self.is_grid_default = h.is_grid_default
                        self.is_multimaster = h.is_multimaster
                        self.use_external_primary = h.use_external_primary
                        self.view = h.view
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
                    raise InfobloxDataError(self.__class__.__name__, 'NSGroup "name" attribute missing in data structure', 400)

    def get(self):
        """
        Checks Infoblox for the NS Group record

        :return: Infoblox NS Group record in dict if exists else False
        :rtype: dict|bool
        :raises: Exception on error
        :raise: InfobloxError
        """
        fields = f'&_return_fields={self.FIELDS}&_return_as_object=1'
        if self.view:
            fields = fields + f'&view={self.view}'
        if self.name:
            self.response = self.client.get(f'{self.RECORD_TYPE}?name={self.name}{fields}&_return_as_object=1')
        else:
            raise InfobloxDataError(self.__class__.__name__, 'name', 400)
        self.parse_reply()

    def parse_reply(self):
        result = self.parse_response(self.response)
        if isinstance(result, dict):
            if '_ref' in result:
                self.name = result.get('name')
                self.external_primaries = result.get('external_primaries')
                self.external_secondaries = result.get('external_secondaries')
                self.grid_primary = result.get('grid_primary')
                self.grid_secondaries = result.get('grid_secondaries')
                self.is_grid_default = result.get('is_grid_default')
                self.is_multimaster = result.get('is_multimaster')
                self.use_external_primary = result.get('use_external_primary')
                self.description = result.get('comment', '')
                self.view = result.get('view')
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

    def match(self, name):
        return name == self.name

    def __str__(self):
        return self.name

    def __eq__(self, other):
        if isinstance(other, self.__class__) and self.name == other.name:
            return True
        return False


class NSGroups(BaseList):
    """
    Abstraction class that should be used when dealing with lists of Infoblox NS Group record objects.
    """
    CHILD = NSGroup
    RECORD_TYPE = 'nsgroup'

    def __init__(self, client, **kwargs):
        super(NSGroups, self).__init__(client, **kwargs)
        self.items = list()  # type: List[NSGroup]
        self.logger.debug('NS Group Records Load Complete, loglevel set to %s', logging.getLevelName(self.logger.getEffectiveLevel()))

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
