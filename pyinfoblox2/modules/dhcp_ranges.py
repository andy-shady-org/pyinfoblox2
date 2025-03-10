# coding: utf-8

import logging
from typing import List

from .base import IPHelpers, BaseList, ip_check
from ..errors import InfobloxClientError, InfobloxError, InfobloxDataError, IPError


class DHCPRange(IPHelpers):
    """
    Abstraction class that simplifies and unifies all access to Infoblox DHCP Range objects.
    """
    FIELDS = 'network,failover_association,start_addr,end_addr,name,comment,network_view,extattrs,options'
    RECORD_TYPE = 'range'

    def __init__(self, client, start_address, view='default', **kwargs):
        super(DHCPRange, self).__init__(client)
        self.start_address = None
        if start_address:
            self.start_address = self.is_valid_ipaddress(start_address)
        self.end_address = None
        self.network = None
        self.failover = None
        self.name = None
        self.description = None
        self.options = list()
        self.view = view
        self.data = kwargs
        self.logger.debug('DHCPRange Load Complete, loglevel set to %s', logging.getLevelName(self.logger.getEffectiveLevel()))

    def to_json(self, original_format=False):
        """
        Returns class items as dict structure

        :param original_format: keep original formal
        :type original_format: bool
        :return: class as dict structure
        :rtype: dict
        """
        if original_format:
            return dict(name=self.name, _ref=self.ref, start_addr=str(self.start_address), end_addr=str(self.end_address), network=str(self.network),
                        failover_association=self.failover, network_view=self.view, comment=self.description, options=self.options, extattrs=self.extattrs.to_json())
        return dict(name=self.name, ref=self.ref, start_address=str(self.start_address), end_addr=str(self.end_address), network=str(self.network),
                    failover_association=self.failover, view=self.view, description=self.description, options=self.options, extattrs=self.extattrs.to_json())

    @classmethod
    def load(cls, client, value, callout=True):
        """
        Static method to load a given DHCP Range either by value of using an existing object

        :param client: pyinfoblox client class
        :param value: a valid start address value string or DHCP Range class
        :param callout: Call out to WAPI to retrieve data, default=True
        :return: Host class, fully populated or False if network does not exist
        """
        try:
            if value and cls.is_valid_ipaddress(value):
                return cls.load_by_address(client, value)
        except IPError:
            pass
        if isinstance(value, dict):
            a = cls(client, None)
            if callout:
                a.from_json(value)
            else:
                a.response = value
                a.parse_reply()
            if a.ref and a.loaded:
                return a
        elif isinstance(value, cls):
            value.get()
            return value
        return False

    @classmethod
    def load_by_address(cls, client, ip_address):
        """
        Static method to load a given DHCP Range as a DHCP Range object and return it for use

        :param client: pyinfoblox client class
        :param ip_address: a valid start IP address
        :return: Host class, fully populated
        """
        cls.is_valid_ipaddress(ip_address)
        h = cls(client, ip_address)
        try:
            h.get()
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
                    if isinstance(h, DHCPRange):
                        self.start_address = h.start_address
                        self.view = h.view
                        self.description = h.description
                        self.end_address = h.end_address
                        self.failover = h.failover
                        self.network = h.network
                        self.name = h.name
                        self.ref = h.ref
                        self.options = h.options
                        self.extattrs = h.extattrs
                        self.loaded = True
                except InfobloxError:
                    return False
            elif 'start_address' in json_data and json_data.get('start_address', '').strip():
                self.start_address = self.is_valid_ipaddress(json_data.get('start_address', '').strip())
                try:
                    self.get()
                except InfobloxError:
                    return False
            else:
                if not self.ref:
                    raise InfobloxDataError(self.__class__.__name__, 'DHCPRange "start_address" attribute missing in data structure', 400)

    @ip_check
    def get(self):
        """
        Checks Infoblox for the DHCP Range record

        :return: Infoblox DHCP Range record in dict if exists else False
        :rtype: dict|bool
        :raises: Exception on error
        :raise: InfobloxError
        """

        fields = f'&_return_fields={self.FIELDS}&_return_as_object=1'
        if self.view:
            fields = fields + f'&network_view={self.view}'
        self.response = self.client.get(f'{self.RECORD_TYPE}?start_addr={self.ip_address}{fields}')
        self.parse_reply()

    def parse_reply(self):
        result = self.parse_response(self.response)
        if isinstance(result, dict):
            if '_ref' in result:
                self.logger.debug('Record found, now setting details...')
                self.start_address = self.is_valid_ipaddress(result.get('start_addr'))
                self.end_address = self.is_valid_ipaddress(result.get('end_addr'))
                self.network = self.is_valid_network(result.get('network'))
                self.description = result.get('comment', '')
                self.failover = result.get('failover_association')
                self.view = result.get('network_view')
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

    @ip_check
    def create(self, username=None, **kwargs):
        """
        Create DHCP Range record

        :param username: username of person performing add for audit purposes
        :param kwargs: any extra attributes for the host record in key/value pairs
        :return:
        """
        super().create(username, **kwargs)
        fields = f'?_return_fields={self.FIELDS}&_return_as_object=1'
        payload = {"extattrs": self.extattrs.to_json(), "name": self.name if self.name else 'Client DHCP range',
                   "start_addr": str(self.start_address), "end_addr": str(self.end_address),
                   "failover_association": self.failover if self.failover else '', "network": str(self.network),
                   "comment": self.description}

        self.response = self.client.post(f'{self.RECORD_TYPE}{fields}', payload=payload)
        self.parse_reply()

    def save(self, username=None, **kwargs):
        """
        Update DHCP Range record

        :param username: username of person performing add for audit purposes
        :param kwargs: any extra attributes for the host record in key/value pairs
        :return:
        """
        super().save(username, **kwargs)
        fields = f'?_return_fields={self.FIELDS}&_return_as_object=1'
        payload = {"extattrs": self.extattrs.to_json(), "name": self.name if self.name else 'Client DHCP range',
                   "start_addr": str(self.start_address), "end_addr": str(self.end_address),
                   "failover_association": self.failover if self.failover else '', "network": str(self.network),
                   "comment": self.description}

        self.response = self.client.put(self.ref + fields, payload=payload)
        self.parse_reply()

    @classmethod
    def add(cls, client, network, start_address, end_address, name=None, failover=None, description=None, options=None, view='default', username=None, **extattrs):
        """
        Add a DHCP Range record

        :param client: pyinfoblox client class
        :param network: IPv4 network
        :param start_address: IPv4 DHCP Range start address
        :param end_address: IPv4 DHCP Range end address
        :param name: Name for DHCP Range
        :param failover: DHCP Failover group
        :param description: description for the record
        :param options: DHCP Options Object or tuple of options (5 params per option)
        :type options: list
        :param view: the view to place the host in
        :param username: username of person performing add for audit purposes
        :param extattrs: any extra attributes for the host record in key/value pairs
        :return: DHCPRange Class
        :rtype: DHCPRange
        """
        obj = cls(client, start_address, view=view)
        obj.end_address = obj.is_valid_ipaddress(end_address)
        obj.network = obj.is_valid_network(network)
        obj.name = name if name else 'DHCP Range'
        obj.failover = failover
        obj.description = description if description else ''
        obj._parse_options(options)
        obj.create(username, **extattrs)
        return obj

    def match(self, start_address):
        return start_address == str(self.start_address)

    def __str__(self):
        return str(self.start_address)

    def __eq__(self, other):
        if isinstance(other, self.__class__) and str(self.start_address) == str(other.start_address):
            return True
        return False


class DHCPRanges(BaseList):
    """
    Abstraction class that should be used when dealing with lists of Infoblox DHCP Range objects.
    """
    CHILD = DHCPRange
    RECORD_TYPE = 'range'
    NETWORK_VIEW = True

    def __init__(self, client, **kwargs):
        super(DHCPRanges, self).__init__(client, **kwargs)
        self.items = list()  # type: List[DHCPRange]
        self.logger.debug('DHCPRanges Load Complete, loglevel set to %s', logging.getLevelName(self.logger.getEffectiveLevel()))

    @classmethod
    def search_by_network(cls, client, value, view='default', limit=100, paging=0):
        return cls.search(client, 'network', value, view=view, limit=limit, paging=paging)

    @classmethod
    def search_by_start_address(cls, client, value, view='default', limit=100, paging=0):
        return cls.search(client, 'start_addr', value, view=view, limit=limit, paging=paging)

    def __getitem__(self, item):
        super().__getitem__(item)

        for x in self.items:
            if isinstance(item, self.CHILD):
                if x.match(str(item.start_address)) and item.view == x.view:
                    return x
            elif isinstance(item, str):
                if x.match(item):
                    return x
            elif isinstance(item, int):
                return self.items[item]
        raise IndexError(f'{self.CHILD.__name__} Not found')

    def __contains__(self, item):
        result = [str(x.start_address) for x in self.items]
        return result.__contains__(item)
