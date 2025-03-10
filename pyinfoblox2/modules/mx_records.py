# coding: utf-8

import logging
from typing import List

from .base import hostname_check, IPHelpers, BaseList
from ..errors import InfobloxError, InfobloxDataError, IPError


class MXRecord(IPHelpers):
    """
    Abstraction class that simplifies and unifies all access to Infoblox MX Record objects.
    """
    FIELDS = 'name,mail_exchanger,preference,dns_name,dns_mail_exchanger,ttl,use_ttl,zone,extattrs,comment,view'
    RECORD_TYPE = 'record:mx'

    def __init__(self, client, name, mail_exchanger=None, pref=None, view='default', **kwargs):
        super(MXRecord, self).__init__(client)
        self.name = name
        self.mail_exchanger = mail_exchanger
        self.preference = pref
        self.dns_name = None
        self.dns_mail_exchanger = None
        self.ttl = 0
        self.use_ttl = False
        self.description = None
        self.view = view
        self.zone = None
        self.logger.debug('MX Record Load Complete, loglevel set to %s', logging.getLevelName(self.logger.getEffectiveLevel()))
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
            return dict(name=self.name, _ref=self.ref, mail_exchanger=self.mail_exchanger, preference=self.preference, dns_name=self.dns_name, zone=self.zone,
                        dns_mail_exchanger=self.dns_mail_exchanger, ttl=self.ttl, use_ttl=self.use_ttl, view=self.view, comment=self.description, extattrs=self.extattrs.to_json())
        return dict(name=self.name, ref=self.ref, mail_exchanger=self.mail_exchanger, preference=self.preference, dns_name=self.dns_name, zone=self.zone,
                    dns_mail_exchanger=self.dns_mail_exchanger, ttl=self.ttl, use_ttl=self.use_ttl, view=self.view, description=self.description, extattrs=self.extattrs.to_json())

    @classmethod
    def load_by_name(cls, client, name):
        """
        Static method to load a given name as a MXRecord object and return it for use

        :param client: pyinfoblox client class
        :param name: a valid hostname
        :return: MXRecord class, fully populated
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
                    if isinstance(h, MXRecord):
                        self.name = h.name
                        self.mail_exchanger = h.mail_exchanger
                        self.preference = h.preference
                        self.dns_name = h.dns_name
                        self.dns_mail_exchanger = h.dns_mail_exchanger
                        self.ttl = h.ttl
                        self.use_ttl = h.use_ttl
                        self.view = h.view
                        self.zone = h.zone
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
                    raise InfobloxDataError(self.__class__.__name__, 'MXRecord "name" attribute missing in data structure', 400)

    @hostname_check()
    def get(self):
        """
        Checks Infoblox for the MX record

        :return: Infoblox MX record in dict if exists else False
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
                self.mail_exchanger = result.get('mail_exchanger')
                self.preference = result.get('preference')
                self.dns_name = result.get('dns_name')
                self.dns_mail_exchanger = result.get('dns_mail_exchanger')
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

    @hostname_check()
    def create(self, username=None, **kwargs):
        """
        Create an MX record

        :param username: username of person performing add for audit purposes
        :param kwargs: any extra attributes for the MX record in key/value pairs
        :return:
        """
        super().create(username, **kwargs)
        fields = f'?_return_fields={self.FIELDS}&_return_as_object=1'
        payload = {"extattrs": self.extattrs.to_json(), "name": self.name, "mail_exchanger": self.mail_exchanger, "preference": self.preference, "ttl": self.ttl, "use_ttl": self.use_ttl,
                   "comment": self.description}
        self.response = self.client.post(f'{self.RECORD_TYPE}{fields}', payload=payload)
        self.parse_reply()

    @hostname_check()
    def save(self, username=None, **kwargs):
        """
        Update an MX record

        :param username: username of person performing add for audit purposes
        :param kwargs: any extra attributes for the MX record in key/value pairs
        :return:
        """
        super().save(username, **kwargs)
        fields = f'?_return_fields={self.FIELDS}&_return_as_object=1'
        payload = {"extattrs": self.extattrs.to_json(), "name": self.name, "mail_exchanger": self.mail_exchanger, "preference": self.preference, "ttl": self.ttl, "use_ttl": self.use_ttl,
                   "comment": self.description}
        self.response = self.client.put(self.ref + fields, payload=payload)
        self.parse_reply()

    @classmethod
    def add(cls, client, name, mail_exchanger, username, preference=100, description=None, view='default', **extattrs):
        """
        Create an MX record within Infoblox

        :param client: pyinfoblox client class
        :param name: name for MX record
        :param mail_exchanger: the mail_exchanger for the MX record
        :param username: username of person performing add for audit purposes
        :param preference: integer for preference of the MX record
        :param description: description for the host record
        :param view: the view to place the host in
        :param extattrs: any extra attributes for the MX record in key/value pairs
        :return: MXRecord Class
        :rtype: MXRecord
        """
        obj = cls(client, name, mail_exchanger, view=view)
        obj.description = description if description else ''
        obj.preference = preference
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


class MXRecords(BaseList):
    """
    Abstraction class that should be used when dealing with lists of Infoblox MX record objects.
    """
    CHILD = MXRecord
    RECORD_TYPE = 'record:mx'

    def __init__(self, client, **kwargs):
        super(MXRecords, self).__init__(client, **kwargs)
        self.items = list()  # type: List[MXRecord]
        self.logger.debug('MX Records Load Complete, loglevel set to %s', logging.getLevelName(self.logger.getEffectiveLevel()))

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
