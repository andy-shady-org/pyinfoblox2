PyInfoblox2
===========

![image info](https://readthedocs.org/projects/pyinfoblox2/badge/?version=latest)

PyInfoblox2 is a Python client wrapper for connecting to and performing actions against Infoblox appliances. 

Contributions
=============

pyinfoblox2 is hosted on
`Github <https://github.com/andy-shady-org/pyinfoblox2>`_. Please contribute
by reporting issues, suggesting features or by sending patches
using pull requests.

Installation
------------

The easiest way to install pyinfoblox is by using ``pip``:

```bash
pip install pyinfoblox2
```

Or you can run build this locally::

```bash
git clone https://github.com/andy-shady-org/pyinfoblox2.git
cd pyinfoblox2
pip install .
```

Quickstart
----------

###### Example Usage

This package makes connections to an Infoblox appliance(s) for provisioning and obtaining data. 

```python
from pyinfoblox2 import *
client = InfobloxClient('server', 'username', 'password', version='2.12.2')      

# Get container
container = Container.load(client, '10.10.0.0/8')

# Create container
new_container = Container.add(client, '10.10.0.0/8', description='Container for Networks within 10.10.0.0/8')

# remove container
container.remove()

# output
container.to_json()
```

```python
from pyinfoblox2 import *
client = InfobloxClient('server', 'username', 'password', version='2.12.2', verbose=1)      

# searching
containers = Containers.search_containers(client, '10.10.0.0/8')
while containers.next_page:
    containers.get_next(containers.next_page)

# matching
if '10.10.1.0/24' in containers:
    print('true')

# output
containers.to_json()
containers['10.10.1.0/24'].to_json()
```

Please read the documentation for advanced usage.

Supported Elements
------------------

 * Auth Zones
 * Forward Zones
 * Delegated Zones
 * Containers
 * Networks
 * IPv4Addr
 * A Records
 * PTR Records
 * Hosts
 * HostAliases
 * Roaming Hosts
 * CNAMES
 * DHCP Ranges
 * Mac Filter Addresses
 * Mac Filters
 * TXT Records
 * SRV Records
 * MX Records
 * NS Records
 * Fixed Addresses
 * Searches (via Client)
 

Permissions
-----------

Write permissions on most objects are required to use this package with all its functionality.

 * Networks/Containers/Zones/Mac Filters - require restart permission on all Grid members
 * Host/CNAME/A/SRV/MX/PTR/Roaming - Require write permissions on respective containers and objects
    
     
Full Documentation
------------------

[Documentation] (https://pyinfoblox2.readthedocs.io/en/latest)


