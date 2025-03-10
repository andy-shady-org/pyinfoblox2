# coding: utf-8

import logging
from typing import List

from .base import IPHelpers, BaseList, fqdn_check
from ..errors import InfobloxError, InfobloxDataError, IPError


class TXTRecord(IPHelpers):
    """
    Abstraction class that simplifies and unifies all access to Infoblox TXT Record objects.
    """
    FIELDS = 'name,extattrs,comment,text,view,dns_name,zone'
    RECORD_TYPE = 'record:txt'

    def __init__(self, client, name, text=None, view='default', **kwargs):
        super(TXTRecord, self).__init__(client)
        self.name = name
        self.text = text
        self.description = None
        self.zone = None
        self.dns_name = None
        self.view = view
        self.logger.debug('TXT Record Load Complete, loglevel set to %s', logging.getLevelName(self.logger.getEffectiveLevel()))
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
            return dict(name=self.name, _ref=self.ref, comment=self.description if self.description else '', text=self.text if self.text else '',
                        zone=self.zone, dns_name=self.dns_name, view=self.view, extattrs=self.extattrs.to_json())
        return dict(name=self.name, ref=self.ref, description=self.description if self.description else '', text=self.text if self.text else '',
                    zone=self.zone, dns_name=self.dns_name, view=self.view, extattrs=self.extattrs.to_json())

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
                    if isinstance(h, TXTRecord):
                        self.name = h.name
                        self.text = h.text
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
                    self.is_valid_fqdn(self.name)
                except IPError:
                    return False
                try:
                    self.get()
                except InfobloxError:
                    return False
            else:
                if not self.ref:
                    raise InfobloxDataError(self.__class__.__name__, 'TXTRecord "name" attribute missing in data structure', 400)

    @fqdn_check(True)
    def get(self):
        """
        Checks Infoblox for the TXT record

        :return: Infoblox TXT record in dict if exists else False
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
                if not result.get('name'):
                    raise InfobloxError(self.__class__.__name__, '"name"')
                self.logger.debug('Record found, now setting details...')
                self.name = result.get('name')
                self.text = result.get('text')
                self.description = result.get('comment', '')
                self.dns_name = result.get('dns_name')
                self.zone = result.get('zone')
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

    @fqdn_check(True)
    def create(self, username=None, **kwargs):
        """
        Create a TXT record

        :param username: username of person performing add for audit purposes
        :param kwargs: any extra attributes for the host record in key/value pairs
        :return:
        """
        super().create(username, **kwargs)
        fields = f'?_return_fields={self.FIELDS}&_return_as_object=1'
        payload = {"text": str(self.text), "extattrs": self.extattrs.to_json(), "name": self.name, "comment": self.description}
        self.response = self.client.post(f'{self.RECORD_TYPE}{fields}', payload=payload)
        self.parse_reply()

    @fqdn_check()
    def save(self, username=None, **kwargs):
        """
        Update a TXT record

        :param username: username of person performing add for audit purposes
        :param kwargs: any extra attributes for the host record in key/value pairs
        :return:
        """
        super().save(username, **kwargs)
        fields = f'?_return_fields={self.FIELDS}&_return_as_object=1'
        payload = {"text": str(self.text), "extattrs": self.extattrs.to_json(), "name": self.name, "comment": self.description}
        self.response = self.client.put(self.ref + fields, payload=payload)
        self.parse_reply()

    @classmethod
    def add(cls, client, name, text, username, description=None, view='default', **extattrs):
        """
        Create a TXT Record within Infoblox

        :param client: pyinfoblox client class
        :param name: name of TXT Record
        :param text: text string to apply to the record
        :param username: username of person performing add for audit purposes
        :param description: description for the host record
        :param view: the view to place the host in
        :param extattrs: any extra attributes for the TXT Record in key/value pairs
        :return: TXTRecord Class
        :rtype: TXTRecord
        """
        obj = cls(client, name, text, view=view)
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


class TXTRecords(BaseList):
    """
    Abstraction class that should be used when dealing with lists of Infoblox TXT Record objects.
    """
    CHILD = TXTRecord
    RECORD_TYPE = 'record:txt'

    def __init__(self, client, **kwargs):
        super(TXTRecords, self).__init__(client, **kwargs)
        self.items = list()  # type: List[TXTRecord]
        self.logger.debug('TXT Records Load Complete, loglevel set to %s', logging.getLevelName(self.logger.getEffectiveLevel()))

    @classmethod
    def search_by_name(cls, client, value, view='default', limit=100, paging=0):
        return cls.search(client, 'name', value, view=view, regex=True, limit=limit, paging=paging)

    def __getitem__(self, item):
        if item == 'get' or item == 'search':
            return self.__getattribute__(item)

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
