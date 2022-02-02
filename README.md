# SR Linux Satellite Tracker
![](./img/srl2.jpg)
With SR Linux we provide a NetOps Development Kit (NDK) for writing your own on-box applications which we refer to as agents. This protobuf-based gRPC framework allows users to interact with 
the NOS on a whole new level: directly installing routes and MPLS routes in the FIB, receiving notifications when state changes for interfaces, BFD sessions and LLDP neighborships. Or you make an application that can track the international space station location. But why on earth would you make such an application for a router you may ask? Just because we can :sunglasses:

The satellite tracker agent fetches every x seconds the current location of the ISS from the internet by making an http request to https://api.wheretheiss.at/v1/satellites/25544. Once the data is fetched the agent will store this information in the state data store as described by its YANG model. The show satellite command will retrieve the geo location from the state datastore and present it in an ASCII world map where it is. The python-based cli has been extended to display the map and geolocation in a custom way by using a custom formatter which is part of the cli-plugin framework SR Linux offers.
## Installing the SRL agent

## Configuration
DNS needs to be configured for the mgmt network-instance to make sure the agent can find the api end point. In this example we use Google DNS servers

Sometime it's needed to set the local DNS entries

