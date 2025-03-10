# coding: utf-8

import ipaddress
import logging
from typing import List

from .base import hostname_check, ip_check, IPHelpers, BaseList
from ..errors import InfobloxError, IPError, InfobloxDataError


class Host(IPHelpers):
    """
    Abstraction class that simplifies and unifies all access to Infoblox Host objects.
    """
    FIELDS = 'name,extattrs,ipv4addrs.bootfile,ipv4addrs.bootserver,ipv4addrs.nextserver,comment,aliases,network_view,ipv4addrs,ipv4addrs.mac,ipv4addrs.network,ipv4addrs.configure_for_dhcp,ipv4addrs.ipv4addr,ipv4addrs.host,ipv4addrs.options,ipv6addrs,ipv6addrs.network,ipv6addrs.ipv6addr,ipv6addrs.host,ipv6addrs.options'
    RECORD_TYPE = 'record:host'

    def __init__(self, client, name, view='default', **kwargs):
        super(Host, self).__init__(client)
        self.name = None
        if name:
            self.name = name.lower()
        self._ip_address = None
        self._ipv6_address = None
        self._mac_address = None
        self.description = None
        self.network = None
        self.networkv6 = None
        self.ip_addresses = list()
        self.ipv6_addresses = list()
        self.aliases = list()
        self.configure_for_dhcp = False
        self.options = list()
        self.pxe = None
        self.view = view
        self.logger.debug('Host Load Complete, loglevel set to %s', logging.getLevelName(self.logger.getEffectiveLevel()))
        self.data = kwargs

    @property
    def mac_address(self):
        return self._mac_address

    @mac_address.setter
    def mac_address(self, value):
        if isinstance(value, str):
            if not self.is_valid_mac_address(value):
                raise InfobloxDataError(self.__class__.__name__, 'mac_address', 400)
            if self.ip_addresses:
                for x in self.ip_addresses:
                    if x.get('mac') == self._mac_address and x.get('ipv4addr') == str(self.ip_address):
                        x['mac'] = value
                        break
            self._mac_address = value
        elif isinstance(value, list):
            if not all([self.is_valid_mac_address(x) for x in value]):
                raise InfobloxDataError(self.__class__.__name__, 'mac_address', 400)
            if len(value) != len(self.ip_addresses):
                raise InfobloxDataError(self.__class__.__name__, 'Host "mac_address" length of list does not match number of addresses', 400)
            count = 0
            for x in self.ip_addresses:
                x['mac'] = value[count]
                count += 1
            self._mac_address = value[0]
        else:
            raise InfobloxDataError(self.__class__.__name__, 'Host "mac_address"', 400)

    @property
    def ip_address(self):
        return self._ip_address

    @property
    def ipv6_address(self):
        return self._ipv6_address

    @ip_address.setter
    def ip_address(self, value):
        if isinstance(value, list) and len(value) > 0:
            if isinstance(value[0], str):
                if not all([self.is_valid_ipaddress(x) for x in value]):
                    raise InfobloxDataError(self.__class__.__name__, 'Host "ip_address"', 400)
                self.ip_addresses = [{"ipv4addr": x,
                                      "configure_for_dhcp": self.configure_for_dhcp,
                                      "mac": self.mac_address,
                                      "network": str(self.network),
                                      "options": self.options} for x in value]
                self._ip_address = value[0]
            elif isinstance(value[0], dict):
                if not all([self.is_valid_ipaddress(x.get('ipv4addr')) for x in value]):
                    raise InfobloxDataError(self.__class__.__name__, 'Host "ip_address"', 400)
                self.ip_addresses = [{"ipv4addr": x.get('ipv4addr'),
                                      "_ref": x.get('_ref'),
                                      "bootfile": x.get('bootfile', ''), "bootserver": x.get('bootserver', ''), "nextserver": x.get('nextserver', ''),
                                      "configure_for_dhcp": x.get('configure_for_dhcp', self.configure_for_dhcp),
                                      "mac": x.get('mac') if x.get('mac') else '00:00:00:00:00:00',
                                      "network": x.get('network'),
                                      "options": x.get('options', [])} for x in sorted(value, key=lambda k: k['ipv4addr'])]
                self.configure_for_dhcp = value[0].get('configure_for_dhcp', self.configure_for_dhcp)
                self._ip_address = self.is_valid_ipaddress(value[0].get("ipv4addr"))
                if value[0].get('network'):
                    self.network = self.is_valid_network(value[0].get('network'))
                self.mac_address = value[0].get('mac', '00:00:00:00:00:00')
                self.options = value[0].get('options', [])
                self.pxe = dict(bootfile=value[0].get('bootfile', ''), bootserver=value[0].get('bootserver', ''), nextserver=value[0].get('nextserver', ''))
            else:
                raise InfobloxDataError(self.__class__.__name__, 'Host "ip_address"', 400)
        elif isinstance(value, str):
            if '/' in value or '-' in value:
                if '-' in value:
                    try:
                        ip1, ip2 = value.split('-')
                    except ValueError as e:
                        raise IPError(f'Invalid IP Address pair format: {e}')
                    self.is_valid_ipaddress(ip1)
                    self.is_valid_ipaddress(ip2)
                elif '/' in value:
                    self.network = self.is_valid_network(value)
                self._ip_address = value
                self.ip_addresses = [{"ipv4addr": f"func:nextavailableip:{str(self._ip_address)}",
                                      "configure_for_dhcp": self.configure_for_dhcp,
                                      "mac": self.mac_address,
                                      "options": self.options}]
            else:
                old_ip = str(self._ip_address)
                self._ip_address = self.is_valid_ipaddress(value)
                found = False
                if self.ip_addresses:
                    for x in self.ip_addresses:
                        if x.get('ipv4addr') == old_ip:
                            x['ipv4addr'] = str(self._ip_address)
                            found = True
                            break
                    if not found and not any([x for x in self.ip_addresses if x.get('ipv4addr') == str(self._ip_address)]):
                        self.ip_addresses = [{"ipv4addr": str(self._ip_address),
                                              "configure_for_dhcp": self.configure_for_dhcp,
                                              "mac": self.mac_address,
                                              "options": self.options}]
        elif isinstance(value, ipaddress.IPv4Address):
            old_ip = str(self._ip_address)
            self._ip_address = value
            found = False
            if self.ip_addresses:
                for x in self.ip_addresses:
                    if x.get('ipv4addr') == old_ip:
                        x['ipv4addr'] = str(self._ip_address)
                        found = True
                        break
                if not found and not any([x for x in self.ip_addresses if x.get('ipv4addr') == str(self._ip_address)]):
                    self.ip_addresses = [{"ipv4addr": str(self._ip_address),
                                          "configure_for_dhcp": self.configure_for_dhcp,
                                          "mac": self.mac_address,
                                          "options": self.options}]
        else:
            raise InfobloxDataError(self.__class__.__name__, 'Host "ip_address"', 400)

    @ipv6_address.setter
    def ipv6_address(self, value):
        if isinstance(value, list) and len(value) > 0:
            if isinstance(value[0], str):
                if not all([self.is_valid_ipaddressv6(x) for x in value]):
                    raise InfobloxDataError(self.__class__.__name__, 'Host "ipv6_address"', 400)
                self.ipv6_addresses = [{"ipv6addr": x, "network": str(self.network), "options": self.options} for x in value]
                self._ipv6_address = value[0]
            elif isinstance(value[0], dict):
                if not all([self.is_valid_ipaddressv6(x.get('ipv6addr')) for x in value]):
                    raise InfobloxDataError(self.__class__.__name__, 'Host "ip_address"', 400)
                self.ipv6_addresses = [{"ipv6addr": x.get('ipv6addr'),
                                        "_ref": x.get('_ref'),
                                        "network": x.get('network'),
                                        "options": x.get('options', [])} for x in sorted(value, key=lambda k: k['ipv6addr'])]
                self._ipv6_address = self.is_valid_ipaddressv6(value[0].get("ipv6addr"))
                if value[0].get('network'):
                    self.networkv6 = self.is_valid_networkv6(value[0].get('network'))
                self.options = value[0].get('options', [])
            else:
                raise InfobloxDataError(self.__class__.__name__, 'Host "ipv6_address"', 400)
        elif isinstance(value, str):
            if '/' in value or '-' in value:
                if '-' in value:
                    try:
                        ip1, ip2 = value.split('-')
                    except ValueError as e:
                        raise IPError(f'Invalid IP Address pair format: {e}')
                    self.is_valid_ipaddressv6(ip1)
                    self.is_valid_ipaddressv6(ip2)
                elif '/' in value:
                    self.networkv6 = self.is_valid_networkv6(value)
                self._ipv6_address = value
                self.ipv6_addresses = [{"ipv6addr": f"func:nextavailableip:{str(self._ipv6_address)}", "options": self.options}]
            else:
                old_ip = str(self._ipv6_address)
                self._ipv6_address = self.is_valid_ipaddressv6(value)
                found = False
                if self.ipv6_addresses:
                    for x in self.ipv6_addresses:
                        if x.get('ipv6addr') == old_ip:
                            x['ipv6addr'] = str(self._ip_address)
                            found = True
                            break
                    if not found and not any([x for x in self.ip_addresses if x.get('ipv6addr') == str(self._ipv6_address)]):
                        self.ipv6_addresses = [{"ipv6addr": str(self._ipv6_address), "options": self.options}]
        elif isinstance(value, ipaddress.IPv6Address):
            old_ip = str(self._ipv6_address)
            self._ipv6_address = value
            found = False
            if self.ip_addresses:
                for x in self.ipv6_addresses:
                    if x.get('ipv6addr') == old_ip:
                        x['ipv6addr'] = str(self._ipv6_address)
                        found = True
                        break
                if not found and not any([x for x in self.ip_addresses if x.get('ipv6addr') == str(self._ipv6_address)]):
                    self.ipv6_addresses = [{"ipv6addr": str(self._ipv6_address), "options": self.options}]
        elif value is None:
            pass
        else:
            raise InfobloxDataError(self.__class__.__name__, 'Host "ipv6_address"', 400)

    def to_json(self, original_format=False):
        """
        Returns class items as dict structure

        :param original_format: keep original formal
        :type original_format: bool
        :return: class as dict structure
        :rtype: dict
        """
        if original_format:
            return dict(name=self.name, _ref=self.ref, comment=self.description, ipv4addrs=self.ip_addresses if self.ip_addresses else [],
                        ipv6addrs=self.ipv6_addresses if self.ipv6_addresses else [], view=self.view, extattrs=self.extattrs.to_json(), aliases=self.aliases)
        return dict(name=self.name, ref=self.ref, description=self.description, ip_address=str(self.ip_address) if self.ip_address else None, ipv6_address=str(self.ipv6_address) if self.ipv6_address else None,
                    mac_address=self.mac_address, configured_for_dhcp=self.configure_for_dhcp, view=self.view, extattrs=self.extattrs.to_json(), network=str(self.network) if self.network else None,
                    networkv6=str(self.networkv6) if self.networkv6 else None, options=self.options, pxe=self.pxe,
                    ip_addresses=self.ip_addresses if self.ip_addresses else [],
                    ipv6_addresses=self.ipv6_addresses if self.ipv6_addresses else [], aliases=self.aliases)

    @classmethod
    def load_by_name(cls, client, name):
        """
        Static method to load a given hostname as a Host object and return it for use

        :param client: pyinfoblox client class
        :param name: a valid hostname
        :return: Host class, fully populated
        """
        if not IPHelpers.is_valid_hostname(name.lower()):
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
                    if isinstance(h, Host):
                        self.name = h.name
                        self.ip_addresses = h.ip_addresses
                        self.ip_address = h.ip_address
                        self.ipv6_address = h.ipv6_address
                        self.network = h.network
                        self.networkv6 = h.networkv6
                        self.view = h.view
                        self.description = h.description
                        self.ref = h.ref
                        self.mac_address = h.mac_address
                        self.configure_for_dhcp = h.configure_for_dhcp
                        self.options = h.options
                        self.extattrs = h.extattrs
                        self.aliases = h.aliases
                        self.pxe = h.pxe
                        self.loaded = True
                except InfobloxError:
                    return False
            elif 'hostname' in json_data and json_data.get('hostname', '').strip():
                self.name = json_data.get('hostname', '').strip()
                try:
                    self.is_valid_hostname(self.name)
                except IPError:
                    return False
                try:
                    self.get()
                except InfobloxError:
                    return False
            else:
                if not self.ref:
                    raise InfobloxDataError(self.__class__.__name__, 'Host "hostname" attribute missing in data structure', 400)

    @hostname_check()
    def get(self):
        """
        Checks Infoblox for the host record

        :return: Infoblox Host record in dict if exists else False
        :rtype: dict|bool
        :raises: Exception on error
        :raise: InfobloxError
        """
        fields = f'&_return_fields={self.FIELDS}&_return_as_object=1'
        if self.view:
            fields = fields + f'&network_view={self.view}&view={self.view}'
        self.response = self.client.get(f'{self.RECORD_TYPE}?name={self.name}{fields}')
        self.parse_reply()

    def parse_reply(self):
        result = self.parse_response(self.response)
        if isinstance(result, dict):
            if '_ref' in result:
                self.logger.debug('Record found, now setting details...')
                self.name = result.get('name')
                self.description = result.get('comment', '')
                if result.get('network_view'):
                    self.view = result.get('network_view')
                elif result.get('view'):
                    self.view = result.get('view')
                self.ref = result.get('_ref')
                if 'ipv4addrs' in result and isinstance(result.get('ipv4addrs'), list) and len(result.get('ipv4addrs')) > 0:
                    self.ip_address = result.get('ipv4addrs')
                if 'ipv6addrs' in result and isinstance(result.get('ipv6addrs'), list) and len(result.get('ipv6addrs')) > 0:
                    self.ipv6_address = result.get('ipv6addrs')
                if 'aliases' in result and isinstance(result.get('aliases'), list):
                    self.aliases = result.get('aliases')
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
    @ip_check
    def create(self, username=None, **kwargs):
        """
        Create a host record

        :param username: username of person performing add for audit purposes
        :param kwargs: any extra attributes for the host record in key/value pairs
        :return:
        """
        super().create(username, **kwargs)
        payload = {"name": self.name, "comment": self.description, "extattrs": self.extattrs.to_json()}
        if self.ip_address:
            payload.update(ipv4addrs=self.ip_addresses if self.ip_addresses else [{"ipv4addr": str(self.ip_address),
                                                                                  "configure_for_dhcp": self.configure_for_dhcp,
                                                                                   "mac": self.mac_address,
                                                                                   "options": self.options}])
        if self.ipv6_address:
            payload.update(ipv6addrs=self.ipv6_addresses if self.ipv6_addresses else [{"ipv6addr": str(self.ipv6_address)}])
        if 'exclude' in kwargs and self.network:
            self.extattrs - 'exclude'
            if isinstance(kwargs.get('exclude'), list):
                payload = {'ipv4addrs': [{'ipv4addr': {'_object_function': 'next_available_ip', "_parameters": {"exclude": kwargs.get('exclude')},
                                                       "_result_field": "ips", "_object": "network", "_object_parameters": {"network": str(self.network)},
                                                       "configure_for_dhcp": self.configure_for_dhcp, "mac": self.mac_address, "options": self.options}}],
                           "name": self.name, "comment": self.description, "extattrs": self.extattrs.to_json()}
            else:
                raise InfobloxError(self.__class__.__name__, '"exclude" parameter needs to be a list')

        if 'excludev6' in kwargs and self.networkv6:
            self.extattrs - 'excludev6'
            if isinstance(kwargs.get('excludev6'), list):
                payload = {'ipv6addrs': [{'ipv6addr': {'_object_function': 'next_available_ip', "_parameters": {"exclude": kwargs.get('exclude')},
                                                       "_result_field": "ips", "_object": "network", "_object_parameters": {"network": str(self.networkv6),
                                                                                                                            "options": self.options}}}],
                           "name": self.name, "comment": self.description, "extattrs": self.extattrs.to_json()}
            else:
                raise InfobloxError(self.__class__.__name__, '"exclude" parameter needs to be a list')

        if payload.get('ipv4addrs'):
            for x in payload['ipv4addrs']:
                if 'network' in x:
                    del x['network']
                if self.pxe:
                    x.update(self.pxe)

        if payload.get('ipv6addrs'):
            for x in payload['ipv6addrs']:
                if 'network' in x:
                    del x['network']

        fields = f'?_return_fields={self.FIELDS}&_return_as_object=1'
        self.response = self.client.post(f'{self.RECORD_TYPE}{fields}', payload=payload)
        self.parse_reply()

    @hostname_check()
    @ip_check
    def save(self, username=None, **kwargs):
        """
        Update a host record

        :param username: username of person performing add for audit purposes
        :param kwargs: any extra attributes for the host record in key/value pairs
        :return:
        """
        super().save(username, **kwargs)
        payload = {"name": self.name, "comment": self.description, "extattrs": self.extattrs.to_json()}
        if self.ip_address:
            payload.update(ipv4addrs=self.ip_addresses if self.ip_addresses else [{"ipv4addr": str(self.ip_address),
                                                                                   "configure_for_dhcp": self.configure_for_dhcp,
                                                                                   "mac": self.mac_address,
                                                                                   "options": self.options}])

        if self.ipv6_address:
            payload.update(ipv6addrs=self.ipv6_addresses if self.ipv6_addresses else [{"ipv6addr": str(self.ipv6_address), "options": self.options}])
        if payload.get('ipv4addrs'):
            for x in payload['ipv4addrs']:
                if 'network' in x:
                    del x['network']
                if self.pxe:
                    x.update(self.pxe)

        if payload.get('ipv6addrs'):
            for x in payload['ipv6addrs']:
                if 'network' in x:
                    del x['network']

        fields = f'?_return_fields={self.FIELDS}&_return_as_object=1'
        self.response = self.client.put(self.ref + fields, payload=payload)
        self.parse_reply()

    @classmethod
    def add(cls, client, name, ip_address, description=None, mac='00:00:00:00:00:00', conf_dhcp=True, pxe=None, options=None, view='default', username=None, **extattrs):
        """
        Create a host record within Infoblox

        :param client: pyinfoblox client class
        :param name: name of host record
        :param ip_address: IPv4 IP address or list of IPv4 Addresses to assign to host

            .. note::

                If network is passed in CIDR format e.g. x:x:x:x:x:x/xx, a new IP will be allocated from the passed network using "nextavailableip" functionality

                If ip_address is passed in "ip-ip" a new IP will be allocated from between the 2 IP's listed using "nextavailableip" functionality

        :param description: description for the host record
        :param mac: mac address for the host record
        :param conf_dhcp: configure the host record for DHCP? (bool)
        :param pxe: a dict of PXE options
        :type pxe: dict or None
        :param options: A list of DHCP options
        :type options: list
        :param view: the view to place the host in
        :param username: username of person performing add for audit purposes
        :param extattrs: any extra attributes for the host record in key/value pairs
        :return: Host Class
        :rtype: Host
        """
        host = cls(client, name, view=view)
        host.configure_for_dhcp = conf_dhcp
        host.mac_address = mac
        host.options = options
        host.ip_address = ip_address
        host.description = description if description else ''
        if pxe and isinstance(pxe, dict):
            host.pxe = pxe
        host.create(username, **extattrs)
        return host

    @classmethod
    def addv6(cls, client, name, ip_address, description=None, mac='00:00:00:00:00:00', conf_dhcp=True, pxe=None, options=None, view='default', username=None, **extattrs):
        """
        Create a host record within Infoblox

        :param client: pyinfoblox client class
        :param name: name of host record
        :param ip_address: IPv6 IP address or list of IPv6 Addresses to assign to host

            .. note::

                If network is passed in CIDR format e.g. x:x:x:x:x:x/xx, a new IP will be allocated from the passed network using "nextavailableip" functionality

                If ip_address is passed in "ip-ip" a new IP will be allocated from between the 2 IP's listed using "nextavailableip" functionality

        :param description: description for the host record
        :param mac: mac address for the host record
        :param conf_dhcp: configure the host record for DHCP? (bool)
        :param pxe: a dict of PXE options
        :type pxe: dict or None
        :param options: A list of DHCP options
        :type options: list
        :param view: the view to place the host in
        :param username: username of person performing add for audit purposes
        :param extattrs: any extra attributes for the host record in key/value pairs
        :return: Host Class
        :rtype: Host
        """
        host = cls(client, name, view=view)
        host.configure_for_dhcp = conf_dhcp
        host.mac_address = mac
        host.options = options
        host.ipv6_address = ip_address
        host.description = description if description else ''
        if pxe and isinstance(pxe, dict):
            host.pxe = pxe
        host.create(username, **extattrs)
        return host

    def add_ip(self, ip_address, mac=None, conf_dhcp=True, options=[], username=None):
        """
        Adds a single IP to a host record

        :param ip_address: IPv4 IP address to assign to host
        :param username: username of person performing add for audit purposes
        :param mac: mac address for the host record
        :param conf_dhcp: configure the host record for DHCP? (bool)
        :param options: list of DHCP options to add to the IP
        :return:
        """
        if any([x.get('ipv4addr') == ip_address for x in self.ip_addresses]):
            raise InfobloxDataError(self.__class__.__name__, 'Host "ip_address" is already assigned to this host', 400)
        self.ip_addresses.append({"ipv4addr": ip_address, "configure_for_dhcp": conf_dhcp, "mac": mac if mac else '00:00:00:00:00:00', "options": options})
        self.ip_address = self.ip_addresses
        self.save(username)

    def remove_ip(self, ip_address, username=None):
        """
        Removes a single IP from a host record if more than 1 IP exists.

            .. note::

                If the primary IP is removed, the next assigned IP will be reassigned as the primary IP of the object

        :param ip_address: IPv4 IP address to assign to host
        :param username: username of person performing add for audit purposes
        :return:
        """
        if not any([x.get('ipv4addr') == ip_address for x in self.ip_addresses]):
            raise InfobloxDataError(self.__class__.__name__, 'Host "ip_address" is not assigned to this host', 400)
        ip_list = [x for x in sorted(self.ip_addresses, key=lambda k: k['ipv4addr']) if x.get('ipv4addr') != ip_address]
        if not ip_list:
            raise InfobloxError(self.__class__.__name__, 'Host "ip_address" is last IP on host, remove host instead')
        self.ip_address = ip_list
        self.mac_address = self.ip_addresses[0].get('mac')
        self.configure_for_dhcp = self.ip_addresses[0].get('configure_for_dhcp')
        self.save(username)

    def add_ipv6(self, ip_address, mac=None, conf_dhcp=True, options=[], username=None):
        """
        Adds a single IP to a host record

        :param ip_address: IPv4 IP address to assign to host
        :param mac: mac address for the host record
        :param conf_dhcp: configure the host record for DHCP? (bool)
        :param options: list of DHCP options to add to the IP
        :param username: username of person performing add for audit purposes
        :return:
        """
        if any([x.get('ipv6addr') == ip_address for x in self.ipv6_addresses]):
            raise InfobloxDataError(self.__class__.__name__, 'Host "ip_address" is already assigned to this host', 400)
        self.ipv6_addresses.append({"ipv6addr": ip_address, "configure_for_dhcp": conf_dhcp, "mac": mac if mac else '00:00:00:00:00:00', "options": options})
        self.ipv6_address = self.ipv6_addresses
        self.save(username)

    def remove_ipv6(self, ip_address, username=None):
        """
        Removes a single IP from a host record if more than 1 IP exists.

            .. note::

                If the primary IP is removed, the next assigned IP will be reassigned as the primary IP of the object

        :param ip_address: IPv4 IP address to assign to host
        :param username: username of person performing add for audit purposes
        :return:
        """
        if not any([x.get('ipv6addr') == ip_address for x in self.ipv6_addresses]):
            raise InfobloxDataError(self.__class__.__name__, 'Host "ip_address" is not assigned to this host', 400)
        ip_list = [x for x in sorted(self.ipv6_addresses, key=lambda k: k['ipv6addr']) if x.get('ipv6addr') != ip_address]
        if not ip_list:
            raise InfobloxError(self.__class__.__name__, 'Host "ip_address" is last IP on host, remove host instead')
        self.ipv6_address = ip_list
        self.mac_address = self.ipv6_addresses[0].get('mac')
        self.configure_for_dhcp = self.ipv6_addresses[0].get('configure_for_dhcp')
        self.save(username)

    def set_pxe(self, bootfile, bootserver, nextserver):
        """
        Set PXE information

        :param bootfile: PXE Boot file
        :param bootserver: PXE Boot Server
        :param nextserver: Next PXE Boot Server
        :return:
        """
        self.pxe = {'bootfile': bootfile, 'bootserver': bootserver, 'nextserver': nextserver}

    def get_aliases(self):
        """
        Checks Infoblox for the host record and returns list of all 'Host Aliases' for this given host record

        :return: Infoblox Host record in dict if exists else False
        :rtype: dict|bool
        :raises: Exception on error
        :raise: InfobloxError
        """

        if not self.name:
            raise InfobloxDataError(self.__class__.__name__, 'name', 400)
        if not self.is_valid_hostname(self.name):
            raise IPError('Invalid hostname format: Failed REGEX checks')

        fields = f'&_return_fields={self.FIELDS}&_return_as_object=1'
        if self.view:
            fields = fields + f'&network_view={self.view}'
        self.response = self.client.get(f'{self.RECORD_TYPE}?name={self.name}{fields}')
        self.parse_reply()

    def create_alias(self, alias, username=None):
        """
        Creates a Host Alias for the current host

        :param alias: host alias to apply
        :param username: username of person performing add for audit purposes
        :return:
        """
        if not self.aliases:
            self.get_aliases()
        if alias in self.aliases:
            raise InfobloxError('Host', 'alias already exists: %s' % alias)

        if isinstance(alias, str):
            self.aliases.append(alias)
        if isinstance(alias, list):
            self.aliases.extend(alias)
        super().save(username)
        payload = {"extattrs": self.extattrs.to_json(), "aliases": self.aliases, "name": self.name}
        self.response = self.client.put(self.ref + '?_return_as_object=1', payload=payload)
        self.ref = self.parse_response(self.response)
        return self.aliases

    def remove_alias(self, alias, username=None):
        """
        Removes the attached record from Infoblox

        :param alias: alias to add to the host
        :param username: username of person performing add for audit purposes
        :return: update list of aliases
        :rtype: list
        """
        if not self.aliases:
            self.get_aliases()
        if alias not in self.aliases:
            raise InfobloxError('Host', 'alias does not exist: %s' % alias)

        self.aliases.remove(alias)
        super().save(username)
        payload = {"extattrs": self.extattrs.to_json(), "aliases": self.aliases, "name": self.name}
        self.response = self.client.put(self.ref + '?_return_as_object=1', payload=payload)
        self.ref = self.parse_response(self.response)
        return self.aliases

    def match(self, name):
        return name == self.name

    def __str__(self):
        if self.name:
            return self.name

    def __eq__(self, other):
        if isinstance(other, self.__class__) and self.name == other.name:
            return True
        return False


class Hosts(BaseList):
    """
    Abstraction class that should be used when dealing with lists of Infoblox Host objects.
    """
    CHILD = Host
    RECORD_TYPE = 'record:host'

    def __init__(self, client, **kwargs):
        super(Hosts, self).__init__(client, **kwargs)
        self.items = list()  # type: List[Host]
        self.logger.debug('Hosts Load Complete, loglevel set to %s', logging.getLevelName(self.logger.getEffectiveLevel()))

    @classmethod
    def search_by_name(cls, client, value, view='default', limit=100, paging=0):
        return cls.search(client, 'name', value.lower(), view=view, regex=True, limit=limit, paging=paging)

    @classmethod
    def search_by_ip(cls, client, value, view='default', limit=100, paging=0):
        return cls.search(client, 'ipv4addr', value, view=view, regex=True, limit=limit, paging=paging)

    @classmethod
    def search_by_mac(cls, client, value, view='default', limit=100, paging=0):
        return cls.search(client, 'mac', value, view=view, regex=False, limit=limit, paging=paging)

    @classmethod
    def search_by_network(cls, client, value, view='default', limit=100, paging=0):
        """
        Works only with WAPI v2.11.2 and above
        """
        return cls.search(client, 'network', value, view=view, regex=False, limit=limit, paging=paging)

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
