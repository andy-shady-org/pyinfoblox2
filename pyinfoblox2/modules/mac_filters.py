# coding: utf-8

import logging
from typing import List

from .base import IPHelpers, BaseList
from ..errors import InfobloxError, InfobloxDataError


class MacFilter(IPHelpers):
    """
    Abstraction class that simplifies and unifies all access to Infoblox MacFilter objects.
    """
    FIELDS = 'comment,name,options,extattrs'
    RECORD_TYPE = 'filtermac'

    def __init__(self, client, name=None, **kwargs):
        super(MacFilter, self).__init__(client)
        self.name = name
        self.description = None
        self.options = list()
        self.data = kwargs
        self.logger.debug('MacFilter Load Complete, loglevel set to %s', logging.getLevelName(self.logger.getEffectiveLevel()))

    def to_json(self, original_format=False):
        """
        Returns class items as dict structure

        :param original_format: keep original formal
        :type original_format: bool
        :return: class as dict structure
        :rtype: dict
        """
        if original_format:
            return dict(name=self.name, _ref=self.ref, comment=self.description, extattrs=self.extattrs.to_json(), options=self.options)
        return dict(name=self.name, ref=self.ref, description=self.description, extattrs=self.extattrs.to_json(), options=self.options)

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
                    if isinstance(h, MacFilter):
                        self.name = h.name
                        self.description = h.description
                        self.ref = h.ref
                        self.extattrs = h.extattrs
                        self.options = h.options
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
                    raise InfobloxDataError(self.__class__.__name__, 'MacFilter "name" attribute missing in data structure', 400)

    def get(self):
        """
        Checks Infoblox for the macfilter record

        :return: Infoblox MacFilter record in dict if exists else False
        :rtype: dict|bool
        :raises: Exception on error
        :raise: InfobloxError
        """

        if self.name and self.name is not None:
            fields = f'?_return_fields={self.FIELDS}&_return_as_object=1&name={self.name}'
            self.response = self.client.get(f'{self.RECORD_TYPE}{fields}')
        else:
            raise InfobloxDataError(self.__class__.__name__, 'name', 400)
        self.parse_reply()

    def parse_reply(self):
        result = self.parse_response(self.response)
        if isinstance(result, dict):
            if '_ref' in result:
                self.logger.debug('Record found, now setting details...')
                self.description = result.get('comment', '')
                self.name = result.get('name')
                self.ref = result.get('_ref')
                if 'options' in result and isinstance(result.get('options'), list):
                    self.options = self.parse_options(result)
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
        Create mac filter record in Infoblox

        :param username: username of person performing add for audit purposes
        :param kwargs: any extra attributes for the mac filter record in key/value pairs
        :return:
        """
        super().create(username, **kwargs)
        fields = f'?_return_fields={self.FIELDS}&_return_as_object=1'
        payload = {"extattrs": self.extattrs.to_json(), "name": self.name, "comment": self.description, "options": self.options}
        self.response = self.client.post(f'{self.RECORD_TYPE}{fields}', payload=payload)
        self.parse_reply()

    def save(self, username=None, **kwargs):
        """
        Update macfilter record

        :param username: username of person performing add for audit purposes
        :param kwargs: any extra attributes for the mac filter record in key/value pairs
        :return:
        """
        super().save(username, **kwargs)
        fields = f'?_return_fields={self.FIELDS}&_return_as_object=1'
        payload = {"extattrs": self.extattrs.to_json(), "name": self.name, "comment": self.description, "options": self.options}
        self.response = self.client.put(self.ref + fields, payload=payload)
        self.parse_reply()

    @classmethod
    def add(cls, client, name, options=None, description=None, username=None, **extattrs):
        """
        Adds a MAC filter entry

        :param client: pyinfoblox client class
        :param name: name of mac filter
        :param options: DHCP Options Object or tuple of options (5 params per option)
        :type options: list
        :param description: description for the MAC filter record
        :param username: username of person performing add for audit purposes
        :param extattrs: any extra attributes for the mac filter record in key/value pairs
        :return: MacFilter class
        :rtype: MacFilter
        """
        obj = MacFilter(client, name)
        obj.description = description if description else ''
        obj._parse_options(options)
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


class MacFilters(BaseList):
    """
    Abstraction class that should be used when dealing with lists of Infoblox MacFilter objects.
    """
    CHILD = MacFilter
    RECORD_TYPE = 'filtermac'

    def __init__(self, client, **kwargs):
        super(MacFilters, self).__init__(client, **kwargs)
        self.items = list()  # type: List[MacFilter]
        self.logger.debug('MacFilters Load Complete, loglevel set to %s', logging.getLevelName(self.logger.getEffectiveLevel()))

    def get(self, limit=100, paging=0, view=None, short=False):
        return super().get(limit=limit, paging=paging, view=view, short=short)

    @classmethod
    def search(cls, client, search_key, value, view=None, regex=False, limit=100, paging=0):
        return super(cls, cls).search(client, search_key, value, view=view, limit=limit, paging=paging)

    @classmethod
    def search_by_name(cls, client, value, limit=100, paging=0):
        return cls.search(client, 'name', value, limit=limit, paging=paging)

    def __getitem__(self, item):
        super().__getitem__(item)

        for x in self.items:
            if isinstance(item, self.CHILD):
                if x.match(item.name):
                    return x
            elif isinstance(item, str):
                if x.match(item):
                    return x
            elif isinstance(item, int):
                return self.items[item]
        raise IndexError(f'{self.CHILD.__name__} Not found')
