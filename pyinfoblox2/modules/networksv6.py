# coding: utf-8

import ipaddress
import logging
from typing import List

from .base import IPHelpers, BaseList, networkv6_check
from ..errors import InfobloxClientError, InfobloxError, InfobloxDataError, IPError
from .ipv4addr import IPv4Addresses


class Networkv6(IPHelpers):
    """
    Abstraction class that simplifies and unifies all access to Infoblox Network objects.
    """
    FIELDS = 'options,extattrs,bootfile,bootserver,nextserver,network,members,network_view,comment,network_container'
    RECORD_TYPE = 'ipv6network'

    def __init__(self, client, network, view='default', **kwargs):
        super(Networkv6, self).__init__(client)
        self.network = None
        if network:
            self.network = self.is_valid_networkv6(network)
        self.description = None
        self.container = None
        self.options = list()
        self.members = list()
        self.pxe = None
        self.view = view
        self.hosts = IPv4Addresses(client)  # type: IPv4Addresses
        self.data = kwargs
        self.logger.debug('Network Load Complete, loglevel set to %s', logging.getLevelName(self.logger.getEffectiveLevel()))

    def to_json(self, original_format=False):
        """
        Returns class items as dict structure

        :param original_format: keep original formal
        :type original_format: bool
        :return: class as dict structure
        :rtype: dict
        """
        if original_format:
            return dict(network=str(self.network), comment=self.description, _ref=self.ref, network_container=str(self.container) if self.container else None,
                        network_view=self.view, extattrs=self.extattrs.to_json(), options=self.options, members=self.members,
                        bootfile=self.pxe.get('bootfile'), bootserver=self.pxe.get('bootserver'), nextserver=self.pxe.get('nextserver'))
        return dict(network=str(self.network), description=self.description, ref=self.ref, container=str(self.container),
                    view=self.view, extattrs=self.extattrs.to_json(), options=self.options, members=self.members, hosts=self.hosts.to_json() if self.hosts else None)

    @classmethod
    def load(cls, client, value, callout=True):
        """
        Static method to load a given Network either by value of using an existing object

        :param client: pyinfoblox client class
        :param value: a valid network value string or Network class
        :param callout: Call out to WAPI to retrieve data, default=True
        :return: Network class, fully populated or False if network does not exist
        """
        try:
            if value and isinstance(value, str) and cls.is_valid_networkv6(value):
                return cls.load_by_prefix(client, value)
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
    def load_by_prefix(cls, client, network):
        """
        Static method to load a given network as a Network object and return it for use

        :param client: pyinfoblox client class
        :param network: a valid IPv6 network prefix
        :return: Network class, fully populated
        """
        net = cls.is_valid_networkv6(network)
        n = cls(client, str(net))
        try:
            n.get()
        except (InfobloxError, InfobloxClientError):
            return False
        return n

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
                    if isinstance(h, Networkv6):
                        self.network = h.network
                        self.view = h.view
                        self.description = h.description
                        self.container = h.container
                        self.ref = h.ref
                        self.extattrs = h.extattrs
                        self.options = h.options
                        self.members = h.members
                        self.loaded = True
                except InfobloxError:
                    return False
            elif 'network' in json_data and json_data.get('network', '').strip():
                self.network = json_data.get('network', '').strip()
                try:
                    self.get()
                except InfobloxError:
                    return False
            else:
                if not self.ref:
                    raise InfobloxDataError(self.__class__.__name__, '"network" attribute missing in data structure', 400)

    @networkv6_check
    def get(self):
        """
        Checks Infoblox for the network record

        :return: Infoblox Network record in dict if exists else False
        :rtype: dict|bool
        :raises: Exception on error
        :raise: InfobloxError
        """
        fields = f'&_return_fields={self.FIELDS}&_return_as_object=1'
        if self.view:
            fields = fields + f'&network_view={self.view}'
        self.response = self.client.get(f'{self.RECORD_TYPE}?network={self.network}{fields}')
        self.parse_reply()

    def parse_reply(self):
        result = self.parse_response(self.response)
        if isinstance(result, dict):
            if '_ref' in result:
                self.description = result.get('comment', 'No description')
                self.view = result.get('network_view')
                self.network = self.is_valid_networkv6(result.get('network'))
                if result.get('network_container') != '/' and result.get('network_container'):
                    self.container = self.is_valid_networkv6(result.get('network_container'))
                self.ref = result.get('_ref')
                self.pxe = dict(bootfile=result.get('bootfile'), bootserver=result.get('bootserver'), nextserver=result.get('nextserver'))
                self.parse_extattr(result)
                if 'options' in result and isinstance(result.get('options'), list):
                    self.options = self.parse_options(result)
                if 'members' in result and isinstance(result.get('members'), list):
                    self.members = list()
                    for x in result.get('members'):
                        self.add_member(x.get('name'))
            else:
                self.logger.error('reference not returned by item addition or update: %s' % self.response)
                raise InfobloxError(self.__class__.__name__, 'reference not returned by item addition or update: %s' % self.response)
        elif isinstance(result, str):
            self.ref = result
        else:
            self.logger.error('invalid data type, not dict or string: %s' % self.response)
            raise InfobloxError(self.__class__.__name__, 'invalid data type, not dict or string: %s' % self.response)
        self.loaded = True

    @networkv6_check
    def create(self, username=None, **kwargs):
        """
        Create a network record

        :param username: username of person performing add for audit purposes
        :param kwargs: any extra attributes for the host record in key/value pairs
        :return:
        """
        super().create(username, **kwargs)
        fields = f'?_return_fields={self.FIELDS}&_return_as_object=1'
        payload = {
            "network": str(self.network),
            "netmask": int(self.network.prefixlen),
            "ipv4addr": str(self.network.network_address),
            "comment": self.description,
            "extattrs": self.extattrs.to_json(),
        }
        if self.members:
            payload.update({"members": self.members})

        if self.options:
            payload.update({"options": self.options})

        if self.pxe:
            payload.update(self.pxe)

        self.response = self.client.post(f'{self.RECORD_TYPE}{fields}', payload=payload)
        self.parse_reply()

    @networkv6_check
    def save(self, username=None, **kwargs):
        """
        Update a network record

        :param username: username of person performing add for audit purposes
        :param kwargs: any extra attributes for the host record in key/value pairs
        :return:
        """
        super().save(username, **kwargs)
        fields = f'?_return_fields={self.FIELDS}&_return_as_object=1'
        payload = {
            "network": str(self.network),
            "netmask": int(self.network.prefixlen),
            "ipv4addr": str(self.network.network_address),
            "comment": self.description,
            "extattrs": self.extattrs.to_json(),
        }
        if self.members:
            payload.update({"members": self.members})

        if self.options:
            payload.update({"options": self.options})

        if self.pxe:
            payload.update(self.pxe)

        self.response = self.client.put(self.ref + fields, payload=payload)
        self.parse_reply()

    @classmethod
    def add(cls, client, network, description=None, options=None, members=None, pxe=None,
            view='default', username=None, **extattrs):
        """
        Create a network record within Infoblox

        :param client: pyinfoblox client class
        :param network: IPv4 network
        :param username: username of person performing add for audit purposes
        :param description: description for the record
        :param options: list of DHCP Options or tuple of options (5 params per option)
        :type options: list
        :param members: DHCP members
        :type members: list|str
        :param pxe: PXE Server Class
        :type pxe: PXEServer
        :param view: the view to place the host in
        :param extattrs: any extra attributes for the host record in key/value pairs
        :return: Network Object
        :rtype: Network
        """
        network = cls(client, network, view=view)
        network.description = description if description else ''

        if isinstance(members, list):
            for x in members:
                if isinstance(x, tuple) and len(x) == 1:
                    network.add_member(x[0])
                elif isinstance(x, dict):
                    network.add_member(x.get('name'))
                elif isinstance(x, str):
                    network.add_member(x)
                else:
                    raise InfobloxDataError(cls.__class__.__name__, 'members', 400)
        elif isinstance(members, str):
            network.add_member(members)
        else:
            raise InfobloxDataError(cls.__class__.__name__, 'members', 400)

        # Process default options for a network
        network.add_option('broadcast-address', 28, True, str(network.network.broadcast_address), 'DHCP')
        network.add_option('routers', 3, True, str(network.network[1]), 'DHCP')
        network._parse_options(options)
        if pxe:
            network.pxe = pxe
        network.create(username, **extattrs)
        return network

    def add_member(self, member):
        """
        Add a DHCP option to Infoblox

        :param member: name of member
        """
        if not self.members:
            self.members = list()

        if any(v.get('name') == member for v in self.members):
            raise InfobloxError(self.__class__.__name__, 'member %s already exists in members list: %s' % (member, self.members))

        self.members.append({"_struct": "dhcpmember", "name": member})

    def set_pxe(self, bootfile, bootserver, nextserver):
        """
        Set PXE information

        :param bootfile: PXE Boot file
        :param bootserver: PXE Boot Server
        :param nextserver: Next PXE Boot Server
        :return:
        """
        self.pxe = {'bootfile': bootfile, 'bootserver': bootserver, 'nextserver': nextserver}

    def load_hosts(self):
        """
        Load all hosts for the given network

        :return:
        """
        self.hosts = IPv4Addresses.search_by_network(self.client, str(self.network), limit=512, paging=True)
        while self.hosts.next_page:
            self.hosts.get_next(self.hosts.next_page)

    def match(self, network):
        return network == str(self.network)

    def __str__(self):
        return str(self.network)

    def __eq__(self, other):
        if isinstance(other, self.__class__) and str(self.network) == str(other.network):
            return True
        return False

    def __len__(self):
        return len(self.hosts) if self.hosts else True

    def __getitem__(self, item):
        for x in self.hosts:
            if x.match(item):
                return x
        raise IndexError('Host Not found')

    def __iter__(self):
        result = []
        for x in self.hosts:
            result.append(x)
        return result.__iter__()

    def __contains__(self, item):
        result = [str(x.network) for x in self.hosts]
        return result.__contains__(item)


class Networksv6(BaseList):
    """
    Abstraction class that should be used when dealing with lists of Infoblox Network objects.
    """
    CHILD = Networkv6
    RECORD_TYPE = 'network'
    NETWORK_VIEW = True

    def __init__(self, client, **kwargs):
        super(Networksv6, self).__init__(client, **kwargs)
        self.items = list()  # type: List[Networkv6]
        self.logger.debug('Networks Load Complete, loglevel set to %s', logging.getLevelName(self.logger.getEffectiveLevel()))

    @classmethod
    def search_container(cls, client, value, view='default', limit=100, paging=0):
        cls.CHILD.is_valid_networkv6(value)
        return cls.search(client, 'network_container', value, view=view, limit=limit, paging=paging)

    @classmethod
    def search_networks(cls, client, value, view='default', limit=100, paging=0):
        cls.CHILD.is_valid_networkv6(value)
        return cls.search(client, 'network', value, view=view, regex=True, limit=limit, paging=paging)

    def __getitem__(self, item):
        super().__getitem__(item)

        for x in self.items:
            if isinstance(item, self.CHILD):
                if x.match(str(item.network)) and item.view == x.view:
                    return x
            elif isinstance(item, str):
                if x.match(item):
                    return x
            elif isinstance(item, ipaddress.IPv6Network):
                if x.match(str(item)):
                    return x
            elif isinstance(item, int):
                return self.items[item]
        raise IndexError(f'{self.CHILD.__name__} Not found')

    def __contains__(self, item):
        result = [str(x.network) for x in self.items]
        return result.__contains__(item)
