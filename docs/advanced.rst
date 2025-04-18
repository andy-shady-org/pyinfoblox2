Advanced Usage
##############

Object Types
============

There are 3 class types provided by PyInfoblox2.

* Client Class
* Object Classes
* List Classes

.. note::

    Object classes represent single Infoblox Object such as a network or TXT object

    When retrieving a single record, that data is loaded into a single ``object class``.

.. note::

    List classes represent multiple Infoblox Objects such as a list of networks or TXT objects

    When retrieving a multiple records, that data is loaded into a single ``list class``.

.. note::

    For every Infoblox object, an object class and a list class have been supplied

.. list-table:: Object and List Classes
   :widths: 25 25 50
   :header-rows: 1

   * - Object Class Name
     - List Class Name
     - Infoblox Record Type
   * - ARecord
     - ARecords
     - A Records
   * - AuthZone
     - AuthZones
     - Authoritative Zones
   * - Cname
     - Cnames
     - CNAMES
   * - Container
     - Containers
     - Infoblox IPv4 Containers
   * - Containerv6
     - Containersv6
     - Infoblox IPv6 Containers
   * - DelegatedZone
     - DelegatedZones
     - Delegated Zones
   * - DHCPRange
     - DHCPRanges
     - DHCP Ranges
   * - FixedAddress
     - FixedAddresses
     - Fixed Addresses
   * - ForwardZone
     - ForwardZones
     - Forward Zones
   * - Host
     - Hosts
     - Infoblox Hosts
   * - IPv4Address
     - IPv4Addresses
     - IPv4 Addresses
   * - MacFilter
     - MacFilters
     - MAC Filters
   * - MacFilterAddress
     - MacFilterAddresses
     - MAC Filter Addresses
   * - MXRecord
     - MXRecords
     - MX Records
   * - NameServer
     - NameServers
     - Name Servers
   * - Network
     - Networks
     - IPv4 Networks
   * - Networkv6
     - Networksv6
     - IPv6 Networks
   * - NSGroup
     - NSGroups
     - Name Server Groups
   * - PTRRecord
     - PTRRecords
     - PTR Records
   * - RoamingHost
     - RoamingHosts
     - Roaming Hosts
   * - ScheduledTask
     - ScheduledTasks
     - Scheduled Tasks
   * - SRVRecord
     - SRVRecords
     - SRV Record
   * - TXTRecord
     - TXTRecords
     - TXT Records

Infoblox Client
===============

The InfobloxClient class acts as an HTTP Rest Client for all Infoblox objects.
It can also be used for searching for items within Infoblox.

The InfobloxClient takes a variety of parameters. These are described as follows::

    server - this is either the hostname or IP of your Infoblox instance. It can be in HTTP format, e.g. http://localhost or localhost
    username - this is the username used to log into your Infoblox instance
    password - this is the password used to log into your Infoblox instance
    version - this is the WAPI version, e.g. **'2.12.2'**
    candidate - a read only server if different from the **server** parameter
    ssl_check - this parameter is used to toggle ``verify`` when using SSL enabled instances
    verbose - this parameter is used to set logging levels, e.g. 1 for warning, 2 for info, 3 for debug
    simulation - this parameter is used to toggle a simulation of the client. When set to true, no connections will be made to the instances
    add_audit - this feature is used to specify whether to add a log message to an Infoblox EA. The

.. note::

    **GET** requests are sent to the candidate option if this is specified and different from the **server** parameter

    All other requests are sent to the **server** (POST/PUT/DELETE)

.. warning::

    The audit feature requires an Infoblox EA named ChangeControl


Examples
--------

This is a simple example of how to call the InfobloxClient class.

.. code-block:: python

    from pyinfoblox2 import *
    client = InfobloxClient(server, username, password, version)

Below is a complete example of calling the InfobloxClient class.

.. code-block:: python

    from pyinfoblox2 import *
    client = InfobloxClient(server, username, password,
                            version, candidate=None, ssl_check=False,
                            verbose=False, simulation=False, add_audit=False)



The infoblox client can be used to perform searches against infoblox objects. The below example would match a partial MAC address:

.. code-block:: python

    from pyinfoblox2 import *
    client = InfobloxClient(server, username, password,
                            version, candidate=None, ssl_check=False,
                            verbose=False, simulation=False, add_audit=False)
    client.search('mac_address', 'xx:xx:xx', regex=True)


The infoblox client can also be used to get data directly without using the **object classes** if required.

.. tip::

    HTTP methods (get, post, put, delete) can be called directly and the resulting output would be JSON.

.. code-block:: python

    from pyinfoblox2 import *
    client = InfobloxClient(server, username, password,
                            version, candidate=None, ssl_check=False,
                            verbose=False, simulation=False, add_audit=False)
    result = client.get('record:txt', name='txt.example.com')



Creating Records
================

Infoblox Records can be created by using the ``add`` method on any Object Class.

Examples
--------

.. code-block:: python

    from pyinfoblox2 import *
    client = InfobloxClient(server, username, password, version)
    obj = ObjectClass.add(*args, **kwargs, **extattrs)


Removing Records
================

Infoblox Records can be removed either immediately or at a scheduled time.

.. note::
    The ``remove_on`` parameter allows the record to be removed at a specific time.
    This uses an Infoblox ``Scheduled Task`` set to the date/time provided.

.. note::
    The ``remove_flags`` parameter allows the record to be removed and any remove flags that are associated with the object to be be triggered.

    For A Records, there is a single flag, which requires enabling the feature on the Infoblox Grid: ``remove_associated_ptr=True``

Examples
--------

.. code-block:: python

    from pyinfoblox2 import *
    client = InfobloxClient(server, username, password, version)
    obj = ObjectClass.load(client, 'test.example.com')
    obj.remove(username=None, remove_on=False, remove_flags=False)




Loading Records
===============

Infoblox Records can be loaded in four ways::

    Load Single Record using an object class which represents the record
    Loading Multiple Records using a list class, either by getting all, or by searching for records
    Loading Multiple records from a text file
    Loading Multiple records from JSON data

.. note::

    Loading data in bulk can be slow, so data is loaded asynchronously to speed up the process.

Examples
--------

Loading a single record:

.. code-block:: python

    from pyinfoblox2 import *
    client = InfobloxClient(server, username, password, version)
    obj = ObjectClass.load(client, value)

Load all records of a given type using a list class:

.. code-block:: python

    from pyinfoblox2 import *
    client = InfobloxClient(server, username, password, version)
    obj = ListClass(client)
    obj.get()
        while obj.next_page:
        obj.get_next(obj.next_page)


Load records of a given type using a search:

.. code-block:: python

    from pyinfoblox2 import *
    client = InfobloxClient(server, username, password, version)
    obj = ListClass.search(client, search_key, value, view='default', regex=False, limit=100, paging=0)


Loading records of a given type from a text file

.. code-block:: python

    from pyinfoblox2 import *
    records = ListClass.load_from_file(filename, verbose=0)


Loading records of a given type from JSON

.. code-block:: python

    from pyinfoblox2 import *
    records = ListClass.load_from_json(data, verbose=0)


Outputting data
===============

Data can be output in 2 ways, either as JSON from either a list class or an object class, or to a file as JSON from a list class:

Examples
--------

.. code-block:: python

    from pyinfoblox2 import *
    client = InfobloxClient(server, username, password, version)
    obj = ObjectClass.load(client, value)
    json_data = obj.to_json()

.. code-block:: python

    from pyinfoblox2 import *
    client = InfobloxClient(server, username, password, version)
    obj = ListClass.search(client, search_key, value, view='default', regex=False, limit=100, paging=0)
    json_data = obj.to_json()

    containers.write_to_file(filename, start=0, length=100)

.. code-block:: python

    from pyinfoblox2 import *
    client = InfobloxClient(server, username, password, version)
    obj = ListClass.search(client, search_key, value, view='default', regex=False, limit=100, paging=0)
    obj.write_to_file(filename, start=0, length=100)


Extra Attributes
================

Infoblox EAs are highly flexible and can be used by all object types.

In order to handle this, EA's are passed into any given PyInfoblox2 object class as a series of keyword arguments when creating an object.

.. tip::

    Infoblox EA's can be passed as parameters and will be created if the EA exists within Infoblox.

    If the ``ChangeControl`` EA exists, and the ``add_audit`` parameter is set to true when initializing the client object,
    the username parameter is used to populate this EA.


.. note::

    The 2 helper classes handle all references to Infoblox EA values (ExtraAttr and AttrObj) and create lists of EA dictionaries: dict(name={"value": value})

    ObjectClass in the below examples can be any object class supplied with the PyInfoblox2 library


Examples
--------

Infoblox EA's can be added to any object at time of creation like so:

.. code-block:: python

    from pyinfoblox2 import *
    client = InfobloxClient(server, username, password, version)
    obj = ObjectClass.add(client, *args, **kwargs, **extattrs)

Infoblox EAs can be added to any existing object class in the following manner:

.. code-block:: python

    from pyinfoblox2 import *
    client = InfobloxClient(server, username, password, version)
    obj = ObjectClass.load(client, value)
    obj.extattrs += AttrObj(name, value)
    obj.save()

Infoblox EAs can be removed from any existing object class in the following manner:

.. code-block:: python

    from pyinfoblox2 import *
    client = InfobloxClient(server, username, password, version)
    obj = ObjectClass.load(client, value)
    obj.extattrs -= name
    obj.save()


Infoblox Functions
==================

For certain object types, Infoblox provides internal functions to assist with record creation. For Host and Network objects, some of these are currently supported.

Examples
--------

When wishing to create a host record using the next IP address within a given network, we can pass the networkk into the IP Address parameter when creating the host:

.. note::

    If network is passed in CIDR format e.g. x.x.x.x/xx, a new IP will be allocated from the passed network using "nextavailableip" functionality

    If ip_address is passed in "ip-ip" a new IP will be allocated from between the 2 IPs listed using "nextavailableip" functionality


.. code-block:: python

    from pyinfoblox2 import *
    client = InfobloxClient(server, username, password, version)
    host1 = Host.add(client, name='test.example.com', ip_address='10.10.10.0/24', description=None, mac=None, conf_dhcp=True, pxe=None, options=[], view='default', username=None, **extattrs)
    host2 = Host.add(client, name='test.example.com', ip_address='10.10.10.1-10.10.10.5', description=None, mac=None, conf_dhcp=True, pxe=None, options=[], view='default', username=None, **extattrs)


When creating a network, as above, we can utilize the internal Infoblox functionality to select the next available network within a given container.

.. code-block:: python

    from pyinfoblox2 import *
    client = InfobloxClient(server, username, password, version)
    network = Network.add(client, None, description=None, options=None, members=None, pxe=None,
            view='default', create_next=True, mask=24, container='10.10.0.0/16', username=None, **extattrs)


Other Features
==============

There are plenty of other helper methods that are object specific, such as adding an IP Address to an exist host record or adding an alias:

.. code-block:: python

    from pyinfoblox2 import *
    client = InfobloxClient(server, username, password, version)
    host = Host.add(client, ip_address, description=None, mac=None, conf_dhcp=True, pxe=None, options=[], view='default', username=None, **extattrs)
    host.add_ip(ip_address, mac=None, conf_dhcp=True, options=[], username=None)
    host.remove_ip(ip_address, username=None)
    host.create_alias(alias, username=None)
    host.remove_alias(alias, username=None)



Record(s) Examples
==================

A Record(s)
-----------

This example shows how to load a single A Record from Infoblox into a object class.

.. code-block:: python

    from pyinfoblox2 import *
    client = InfobloxClient(server, username, password, version)
    record = ARecord.load(client, 'test.example.com')
    record = ARecord.load(client, '1.1.1.1')

Creating an A Record is also done using the object class.

.. code-block:: python

    from pyinfoblox2 import *
    client = InfobloxClient(server, username, password, version)
    record = ARecord.add(client, name, ip_address, description=None, view='default', username=None, **extattrs)

Removing an A Record is also done using the object class.

.. note::
    The ``remove_on`` parameter allows the record to be removed at a specific time.
    This uses an Infoblox ``Scheduled Task`` set to the date/time provided.

.. note::
    The ``remove_flags`` parameter allows the record to be removed and any remove flags that are associated with the object to be be triggered.

    For A Records, there is a single flag, which requires enabling the feature on the Infoblox Grid: ``remove_associated_ptr=True``


.. code-block:: python

    from pyinfoblox2 import *
    client = InfobloxClient(server, username, password, version)
    record = ARecord.load(client, 'test.example.com')
    record.remove(username=None, remove_on=False, remove_flags=False)


This example shows how to load all A Records into a list class.

.. code-block:: python

    from pyinfoblox2 import *
    client = InfobloxClient(server, username, password, version)
    records = ARecords(client)
    records.get()
    while records.next_page:
        records.get_next(records.next_page)

This example shows how to search for A Records.

.. code-block:: python

    from pyinfoblox2 import *
    client = InfobloxClient(server, username, password, version)
    records = ARecords.search(client, search_key, value, view='default', regex=False, limit=100, paging=0)

Helper methods have been added to make searching by name or IP Address easier.

.. code-block:: python

    from pyinfoblox2 import *
    client = InfobloxClient(server, username, password, version)
    records = ARecords.search_by_address(client, value, view='default', limit=100, paging=0)
    records = ARecords.search_by_name(client, value, view='default', limit=100, paging=0)

Searching for a given element within the resulting class:

.. code-block:: python

    from pyinfoblox2 import *
    client = InfobloxClient(server, username, password, version)
    records = ARecords(client)
    records.get()
    containers.get()
    result_obj = records.find('ip_address', '1.1.1.1')

A Records can also be loaded from files, such as a JSON file, or a text file, where the text file contains a list of JSON dictionaries.

.. note::

    Loading data in bulk can be slow, so data is loaded asynchronously to speed up the process.

.. code-block:: python

    from pyinfoblox2 import *
    records = ARecords.load_from_file(filename, verbose=0)
    records = ARecords.load_from_json(data, verbose=0)

Data can be output in 2 ways, either as JSON or to a file as JSON:

.. code-block:: python

    from pyinfoblox2 import *
    client = InfobloxClient(server, username, password, version)
    records = ARecords.search(client, '10.10.10', regex=True)
    records.to_json()
    records.write_to_file(filename, start=0, length=100)


Container(s)
------------

This example shows how to load a single container from Infoblox into a Container object.

.. code-block:: python

    from pyinfoblox2 import *
    client = InfobloxClient(server, username, password, version)
    container = Container.load(client, '10.0.0.0/8')
    co

To load all networks within a given container a helper method is supplied:

.. code-block:: python

    from pyinfoblox2 import *
    client = InfobloxClient(server, username, password, version)
    container = Container.load(client, '10.0.0.0/8')
    container.load_networks()
    container.networks.to_json()


In oder to load multiple containers, you can either search for containers matching a given criteria or load all containers.

.. code-block:: python

    from pyinfoblox2 import *
    client = InfobloxClient(server, username, password, version)
    containers = Containers(client)
    containers.get()
    containers.get_next()
    containers.to_json()

To search for containers:

.. code-block:: python

    from pyinfoblox2 import *
    client = InfobloxClient(server, username, password, version)
    containers = Containers.search(client, search_key, value, view='default', regex=False, limit=100, paging=0)

Containers can also be loaded from files, such as a JSON file, or a text file, where the text file contains a list of JSON dictionaries:

.. code-block:: python

    from pyinfoblox2 import *
    containers = Containers.load_from_file(filename, verbose=0)
    containers = Containers.load_from_json(data, verbose=0)

Searching for a given element within the containers class:

.. code-block:: python

    from pyinfoblox2 import *
    containers.get()
    result_obj = containers.find('network', '10.10.0.0/16')


Data can be output in 2 ways, either as JSON or to a file as JSON:

.. code-block:: python

    from pyinfoblox2 import *
    client = InfobloxClient(server, username, password, version)
    containers = Containers.search(client, '10.10.10', regex=True)
    contains.to_json()
    containers.write_to_file(filename, start=0, length=100)

The following example shows how to create a container in infoblox.

.. note::

    When using DHCP options, the options parameter can be a tuple of 5 values, making up an option, or a list of JSON objects::

        Example 1: options=list(dict(name=name, num=int(num), value=value, vendor_class=vendor_class))
        Example 2: options=list(dict(name=name, num=int(num), use_option=use, value=value, vendor_class=vendor_class))
        Example 3: options=list(tuple(name, num, True, value, vendor_class))


.. code-block:: python

    from pyinfoblox2 import *
    client = InfobloxClient(server, username, password, version)
    container = Container.add(client, network, description=None, options=None, view='default', username=None, **extattrs)

To update a container, the following method is used. In this case, if kwargs are passed, these are translated into EA's and applied to the container.

.. code-block:: python

    from pyinfoblox2 import *
    client = InfobloxClient(server, username, password, version)
    container = Container.load(client, network)
    container.description = 'new description'
    container.save(username=None, ***kwargs)

Infoblox EA's can be applied to existing containers like so:

.. code-block:: python

    from pyinfoblox2 import *
    client = InfobloxClient(server, username, password, version)
    container = Container.load(client, network)
    containers.extattrs += AttrObj(name, value)
    containers.extattrs -= AttrObj(name, value)

