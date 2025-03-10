# coding: utf-8

import logging
from typing import List

from .base import mac_check, fqdn_check, IPHelpers, BaseList
from ..errors import InfobloxError, InfobloxDataError, IPError


class RoamingHost(IPHelpers):
    """
    Abstraction class that simplifies and unifies all access to Infoblox Roaming Host objects.
    """
    FIELDS = 'name,extattrs,comment,options,mac,ddns_domainname,options,network_view'
    RECORD_TYPE = 'roaminghost'

    def __init__(self, client, name, view='default', **kwargs):
        super(RoamingHost, self).__init__(client)
        self.name = name.lower()
        self.shortname = None
        self.domainname = None
        if self.name:
            self.shortname = self.name.split('.')[0]
            self.domainname = '.'.join(self.name.split('.')[1:])
        self.mac_address = None
        self.description = None
        self.options = list()
        self.view = view
        self.data = kwargs
        self.logger.debug('RoamingHost Load Complete, loglevel set to %s', logging.getLevelName(self.logger.getEffectiveLevel()))

    def to_json(self, original_format=False):
        """
        Returns class items as dict structure

        :param original_format: keep original formal
        :type original_format: bool
        :return: class as dict structure
        :rtype: dict
        """
        if original_format:
            return dict(name=self.shortname, _ref=self.ref, ddns_domainname=self.domainname, comment=self.description,
                        mac=self.mac_address, network_view=self.view, options=self.options, extattrs=self.extattrs.to_json())
        return dict(name=self.name, ref=self.ref, shortname=self.shortname, domainname=self.domainname, description=self.description,
                    mac_address=self.mac_address, view=self.view, options=self.options, extattrs=self.extattrs.to_json())

    @classmethod
    def load_by_name(cls, client, name):
        """
        Static method to load a given hostname as a RoamingHost object and return it for use

        :param client: pyinfoblox client class
        :param name: a valid hostname
        :return: RoamingHost class, fully populated
        """
        if not IPHelpers.is_valid_hostname(name.lower()):
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
                    if isinstance(h, RoamingHost):
                        self.shortname = h.shortname
                        self.domainname = h.domainname
                        self.name = h.name
                        self.mac_address = h.mac_address
                        self.view = h.view
                        self.description = h.description
                        self.ref = h.ref
                        self.options = h.options
                        self.extattrs = h.extattrs
                        self.loaded = True
                except InfobloxError:
                    return False
            elif 'hostname' in json_data and json_data.get('hostname', '').strip():
                self.name = json_data.get('hostname', '').strip()
                self.shortname = self.name.split('.')[0]
                try:
                    self.get()
                except InfobloxError:
                    return False
            else:
                if not self.ref:
                    raise InfobloxDataError(self.__class__.__name__, 'RomaingHost "hostname" attribute missing in data structure', 400)

    def get(self):
        """
        Checks Infoblox for the RoamingHost record

        :return: Infoblox RoamingHost record in dict if exists else False
        :rtype: dict|bool
        :raises: Exception on error
        :raise: InfobloxError
        """
        if self.shortname:
            if self.is_valid_hostname(self.shortname):
                fields = f'&_return_fields={self.FIELDS}&_return_as_object=1'
                if self.view:
                    fields = fields + f'&network_view={self.view}'
                self.response = self.client.get(f'{self.RECORD_TYPE}?name={self.shortname}{fields}&_return_as_object=1')
            else:
                raise IPError('Invalid hostname format: Failed REGEX checks')
        else:
            raise InfobloxDataError(self.__class__.__name__, 'name', 400)
        self.parse_reply()

    def parse_reply(self):
        result = self.parse_response(self.response)
        if isinstance(result, dict):
            if '_ref' in result:
                self.logger.debug('Record found, now setting details...')
                if result.get('ddns_domainname') and result.get('name'):
                    if not self.is_valid_hostname('.'.join([result.get('name'), result.get('ddns_domainname')])):
                        raise IPError('Invalid hostname format: Failed REGEX checks')
                    self.name = '.'.join([result.get('name'), result.get('ddns_domainname')])
                elif result.get('name'):
                    if not self.is_valid_hostname(result.get('name')):
                        raise IPError('Invalid hostname format: Failed REGEX checks')
                    self.name = result.get('name')
                else:
                    raise InfobloxError(self.__class__.__name__, 'name or ddns_domainname not returned: %s' % self.response)
                self.shortname = result.get('name')
                self.domainname = result.get('ddns_domainname')
                self.description = result.get('comment', '')
                self.view = result.get('network_view')
                self.ref = result.get('_ref')
                if 'mac' in result and self.is_valid_mac_address(result.get('mac')):
                    self.mac_address = result.get('mac')
                self.parse_extattr(result)
                if 'options' in result:
                    self.options = self.parse_options(result)
            else:
                self.logger.error('reference not returned by item addition or update: %s' % self.response)
                raise InfobloxError(self.__class__.__name__, 'reference not returned by item addition or update: %s' % self.response)
        elif isinstance(result, str):
            self.ref = result
        else:
            self.logger.error('invalid data type, not dict or string: %s' % self.response)
            raise InfobloxError(self.__class__.__name__, 'invalid data type, not dict or string: %s' % self.response)
        self.loaded = True

    @fqdn_check()
    @mac_check
    def create(self, username=None, **kwargs):
        """
        Create Roaming Host record in Infoblox

        :param username: username of person performing add for audit purposes
        :param kwargs: any extra attributes for the RoamingHost record in key/value pairs
        :return:
        """
        super().create(username, **kwargs)
        fields = f'?_return_fields={self.FIELDS}&_return_as_object=1'
        payload = {"ddns_domainname": self.domainname, "deny_bootp": False, "extattrs": self.extattrs.to_json(), "name": self.shortname, "comment": self.description,
                   "mac": self.mac_address, "use_bootfile": False, "use_bootserver": False, "use_ddns_domainname": True, "enable_ddns": True,
                   "use_ignore_dhcp_option_list_request": False, "use_nextserver": False, "use_options": True, "match_client": "MAC_ADDRESS", "force_roaming_hostname": True}

        self._parse_options([('dhcp-lease-time', 51, True, '691200', 'DHCP'),
                             ('domain-name', 15, True, self.domainname, 'DHCP')])

        if self.options:
            payload.update({"options": self.options})

        self.response = self.client.post(f'{self.RECORD_TYPE}{fields}', payload=payload)
        self.parse_reply()

    @fqdn_check()
    @mac_check
    def save(self, username=None, **kwargs):
        """
        Update Roaming Host record in Infoblox

        :param username: username of person performing add for audit purposes
        :param kwargs: any extra attributes for the RoamingHost record in key/value pairs
        :return:
        """
        super().save(username, **kwargs)
        fields = f'?_return_fields={self.FIELDS}&_return_as_object=1'
        payload = {"ddns_domainname": self.domainname, "deny_bootp": False, "extattrs": self.extattrs.to_json(), "name": self.shortname, "comment": self.description,
                   "mac": self.mac_address, "use_bootfile": False, "use_bootserver": False, "use_ddns_domainname": True, "enable_ddns": True,
                   "use_ignore_dhcp_option_list_request": False,
                   "use_nextserver": False, "use_options": True, "match_client": "MAC_ADDRESS", "force_roaming_hostname": True}

        self._parse_options([('dhcp-lease-time', 51, True, '691200', 'DHCP'),
                             ('domain-name', 15, True, self.domainname, 'DHCP')])

        if self.options:
            payload.update({"options": self.options})

        self.response = self.client.put(self.ref + fields, payload=payload)
        self.parse_reply()

    @classmethod
    def add(cls, client, name, domainname=None, description=None, mac=None, options=None, view='default', username=None, **extattrs):
        """
        Create Roaming Host record in Infoblox

        :param client: pyinfoblox client class
        :param name: name of zone record
        :param domainname: domain name of the record if short hostname used
        :param description: description for the zone record
        :param mac: MAC address for the roaming host
        :param options: DHCP Options Object or tuple of options (5 params per option)
        :type options: list
        :param view: the view to place the host in
        :param username: username of person performing add for audit purposes
        :param extattrs: any extra attributes for the host record in key/value pairs
        :return: RoamingHost Class
        :rtype: RoamingHost
        """
        obj = cls(client, name, view=view)
        obj.mac_address = mac if mac else '00:00:00:00:00:01'
        obj.description = description if description else ''
        if domainname and not obj.domainname:
            obj.name = '.'.join([name.lower(), domainname.lower()])
            obj.domainname = domainname.lower()
        elif not obj.domainname and not domainname:
            raise InfobloxDataError(cls.__class__.__name__, 'domainname required if using short hostname format', 400)
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


class RoamingHosts(BaseList):
    """
    Abstraction class that should be used when dealing with lists of Infoblox RoamingHost objects.
    """
    CHILD = RoamingHost
    RECORD_TYPE = 'roaminghost'
    NETWORK_VIEW = True

    def __init__(self, client, **kwargs):
        super(RoamingHosts, self).__init__(client, **kwargs)
        self.items = list()  # type: List[RoamingHost]
        self.logger.debug('RoamingHosts Load Complete, loglevel set to %s', logging.getLevelName(self.logger.getEffectiveLevel()))

    @classmethod
    def search(cls, client, search_key, value, view=None, regex=False, limit=100, paging=0):
        value = value.split(".")[0].lower() if search_key == "name" else value
        return super(cls, cls).search(client, search_key, value, view=view, limit=limit, paging=paging)

    @classmethod
    def search_by_name(cls, client, value, view='default', limit=100, paging=0):
        return cls.search(client, 'name', value.lower(), view=view, regex=True, limit=limit, paging=paging)

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
