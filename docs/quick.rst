Quick Start Guide
#################

Example Usage (Container(s) Objects)
====================================

This package makes connections to an Infoblox appliance(s) for provisioning and obtaining data:

.. code-block:: python

    from pyinfoblox2 import *
    client = InfobloxClient('server', 'candidate', 'username', 'password', ssl_check=False, version='7.2.3', verbose=1)

    # Get container
    container = Container.load(client, '10.10.0.0/8')

    # Create container
    container = Container.add(client, '10.10.0.0/8', username='user', description='Container for Networks within 10.10.0.0/8')

    # remove container
    container.remove(username='user')

    # output
    container.to_json()

    # searching
    containers = Containers.search_containers(client, '10.10.0.0/8')
    while containers.next_page:
        containers.get_next(containers.next_page)

    # matching
    '10.10.1.0/24' in containers

    # output
    containers.to_json()
    containers['10.10.1.0/24'].to_json()
