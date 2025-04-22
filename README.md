PyInfoblox2
===========

<div align="center">
<a href="https://pypi.org/project/pyinfoblox2/"><img src="https://img.shields.io/pypi/v/netbox-security" alt="PyPi"/></a>
<a href="https://github.com/andy-shady-org/pyinfoblox2/stargazers"><img src="https://img.shields.io/github/stars/andy-shady-org/pyinfoblox2?style=flat" alt="Stars Badge"/></a>
<a href="https://github.com/andy-shady-org/pyinfoblox2/network/members"><img src="https://img.shields.io/github/forks/andy-shady-org/pyinfoblox2?style=flat" alt="Forks Badge"/></a>
<a href="https://github.com/andy-shady-org/pyinfoblox2/issues"><img src="https://img.shields.io/github/issues/andy-shady-org/pyinfoblox2" alt="Issues Badge"/></a>
<a href="https://github.com/andy-shady-org/pyinfoblox2/pulls"><img src="https://img.shields.io/github/issues-pr/andy-shady-org/pyinfoblox2" alt="Pull Requests Badge"/></a>
<a href="https://github.com/andy-shady-org/pyinfoblox2/graphs/contributors"><img alt="GitHub contributors" src="https://img.shields.io/github/contributors/andy-shady-org/pyinfoblox2?color=2b9348"></a>
<a href="https://github.com/andy-shady-org/pyinfoblox2/blob/master/LICENSE"><img src="https://img.shields.io/github/license/andy-shady-org/pyinfoblox2?color=2b9348" alt="License Badge"/></a>
<a href="https://pepy.tech/project/pyinfoblox2"><img alt="Downloads" src="https://static.pepy.tech/badge/pyinfoblox2"></a>
<a href="https://pepy.tech/project/pyinfoblox2"><img alt="Downloads/Week" src="https://static.pepy.tech/badge/pyinfoblox2/month"></a>
<a href="https://pepy.tech/project/pyinfoblox2"><img alt="Downloads/Month" src="https://static.pepy.tech/badge/pyinfoblox2/week"></a>
</div>

PyInfoblox2 is a Python client wrapper for connecting to and performing actions against Infoblox appliances. 

Contributions
=============

Please contribute by reporting issues, suggesting features or by sending patches using pull requests.

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


