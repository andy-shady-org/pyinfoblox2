# coding: utf-8

import ipaddress
import logging
from typing import List

from .base import network_check, IPHelpers, BaseList
from ..errors import InfobloxClientError, InfobloxError, InfobloxDataError, IPError
from .networks import Networks


class Container(IPHelpers):
    """
    Abstraction class that simplifies and unifies all access to Infoblox Container objects.
    """
    FIELDS = 'comment,network,network_view,network_container,options,extattrs'
    RECORD_TYPE = 'networkcontainer'

    def __init__(self, client, network, view='default', **kwargs):
        super(Container, self).__init__(client)
        self.network = None
        if network:
            self.network = self.is_valid_network(network)
        self.description = None
        self.networks = Networks(client)  # type: Networks
        self.options = dict()
        self.network_container = None
        self.view = view
        self.data = kwargs
        self.logger.debug('Container Load Complete, loglevel set to %s', logging.getLevelName(self.logger.getEffectiveLevel()))

    def to_json(self, original_format=False):
        """
        Returns class items as dict structure

        :param original_format: keep original formal
        :type original_format: bool
        :return: class as dict structure
        :rtype: dict
        """
        if original_format:
            return dict(network=str(self.network), _ref=self.ref, comment=self.description, network_view=self.view, networks=self.networks.to_json() if self.networks else None, options=self.options,
                        network_container=self.network_container, extattrs=self.extattrs.to_json())
        return dict(network=str(self.network), ref=self.ref, description=self.description, view=self.view, networks=self.networks.to_json() if self.networks else None, options=self.options,
                    network_container=self.network_container, extattrs=self.extattrs.to_json())

    @classmethod
    def load(cls, client, value, callout=True):
        """
        Static method to load a given Container either by value of using an existing object

        :param client: pyinfoblox client class
        :param value: a valid container value string or Container class
        :param callout: Call out to WAPI to retrieve data, default=True
        :return: Container class, fully populated or False if container does not exist
        """
        try:
            if value and isinstance(value, str) and cls.is_valid_network(value):
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
        Static method to load a given network as a Container object and return it for use

        :param client: pyinfoblox client class
        :param network: container IP network
        :return: Container class, fully populated
        """
        net = cls.is_valid_network(network)
        c = cls(client, str(net))
        try:
            c.get()
        except (InfobloxError, InfobloxClientError):
            return False
        return c

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
                    if isinstance(h, Container):
                        self.network = h.network
                        self.view = h.view
                        self.description = h.description
                        self.network_container = h.network_container
                        self.ref = h.ref
                        self.options = h.options
                        self.extattrs = h.extattrs
                        self.loaded = True
                except InfobloxError:
                    return False
            elif 'network' in json_data and json_data.get('network', '').strip():
                self.network = self.is_valid_network(json_data.get('network', '').strip())
                try:
                    self.get()
                except InfobloxError:
                    return False
            else:
                if not self.ref:
                    raise InfobloxDataError(self.__class__.__name__, 'Container "network" attribute missing in data structure', 400)

    @network_check
    def get(self):
        """
        Checks Infoblox for the container record

        :return: Infoblox Container record in dict if exists else False
        :rtype: dict|bool
        :raises: Exception on error
        :raise: InfobloxError
        """

        fields = f'?_return_fields={self.FIELDS}&_return_as_object=1&network={self.network}'
        if self.view:
            fields = fields + f'&network_view={self.view}'
        self.response = self.client.get(f'{self.RECORD_TYPE}{fields}')
        self.parse_reply()

    def parse_reply(self):
        result = self.parse_response(self.response)
        if isinstance(result, dict):
            if '_ref' in result:
                self.logger.debug('Record found, now setting details...')
                self.description = result.get('comment', '')
                self.view = result.get('network_view')
                self.network = self.is_valid_network(result.get('network'))
                self.network_container = result.get('network_container')
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

    @network_check
    def create(self, username=None, **kwargs):
        """
        Create Container record in Infoblox

        :param username: username of person performing add for audit purposes
        :param kwargs: any extra attributes for the host record in key/value pairs
        :return:
        """
        super().create(username, **kwargs)
        fields = f'?_return_fields={self.FIELDS}&_return_as_object=1'
        payload = {"extattrs": self.extattrs.to_json(), "network": str(self.network), "comment": self.description}

        if self.options:
            payload.update({"options": self.options})

        self.response = self.client.post(f'{self.RECORD_TYPE}{fields}', payload=payload)
        self.parse_reply()

    @network_check
    def save(self, username=None, **kwargs):
        """
        Update container record

        :param username: username of person performing add for audit purposes
        :param kwargs: any extra attributes for the host record in key/value pairs
        :return:
        """
        super().save(username, **kwargs)
        fields = f'?_return_fields={self.FIELDS}&_return_as_object=1'
        payload = {"extattrs": self.extattrs.to_json(), "comment": self.description}

        if self.options:
            payload.update({"options": self.options})

        self.response = self.client.put(self.ref + fields, payload=payload)
        self.parse_reply()

    @classmethod
    def add(cls, client, network, description=None, options=None, view='default', username=None, **extattrs):
        """
        Adds a container entry

        :param client: pyinfoblox client class
        :param network: IPv4 network for the container
        :param description: description for the container record
        :param options: DHCP Options Object or tuple of options (5 params per option)
        :type options: list
        :param view: the view to place the container in
        :param username: username of person performing add for audit purposes
        :param extattrs: any extra attributes for the host record in key/value pairs
        :return: Container class
        :rtype: Container
        """
        obj = cls(client, network, view=view)
        obj.description = description if description else ''
        obj._parse_options(options)
        obj.create(username, **extattrs)
        return obj

    def load_networks(self):
        """
        Load all networks for the given container

        :return:
        """
        self.networks = Networks.search_container(self.client, str(self.network), limit=512, paging=True)
        while self.networks.next_page:
            self.networks.get_next(self.networks.next_page)

    def match(self, network):
        return network == str(self.network)

    def __eq__(self, other):
        if isinstance(other, self.__class__) and str(self.network) == str(other.network):
            return True
        return False

    def __str__(self):
        return str(self.network)

    def __len__(self):
        return len(self.networks) if self.networks else True

    def __getitem__(self, item):
        for x in self.networks:
            if x.match(item):
                return x
        raise IndexError('Network Not found')

    def __iter__(self):
        result = []
        for x in self.networks:
            result.append(x)
        return result.__iter__()

    def __contains__(self, item):
        result = []
        for x in self.networks:
            result.append(str(x.network))

        return result.__contains__(item)


class Containers(BaseList):
    """
    Abstraction class that should be used when dealing with lists of Infoblox Container objects.
    """
    CHILD = Container
    RECORD_TYPE = 'networkcontainer'
    NETWORK_VIEW = True

    def __init__(self, client, **kwargs):
        super(Containers, self).__init__(client, **kwargs)
        self.items = list()  # type: List[Container]
        self.logger.debug('Containers Load Complete, loglevel set to %s', logging.getLevelName(self.logger.getEffectiveLevel()))

    @classmethod
    def search_subcontainers(cls, client, value, view='default', limit=100, paging=0):
        return cls.search(client, 'network_container', value, view=view, limit=limit, paging=paging)

    @classmethod
    def search_containers(cls, client, value, view='default', limit=100, paging=0):
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
            elif isinstance(item, ipaddress.IPv4Network):
                if x.match(str(item)):
                    return x
            elif isinstance(item, int):
                return self.items[item]
        raise IndexError(f'{self.CHILD.__name__} Not found')

    def __contains__(self, item):
        result = [str(x.network) for x in self.items]
        return result.__contains__(item)
