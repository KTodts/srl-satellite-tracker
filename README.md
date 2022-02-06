# SR Linux Satellite Tracker
![](./img/header.jpg)
With SR Linux we provide a NetOps Development Kit (NDK) for writing your own on-box applications which we refer to as agents. This protobuf-based gRPC framework allows users to interact with 
the NOS on a whole new level: directly installing routes or MPLS routes in the FIB, receiving notifications when state changes for interfaces, BFD sessions or LLDP neighborships. Or, you make an application that can track the international space station location. But why on earth would you make such application for a router you may ask? Just because we can :sunglasses:

The satellite tracker agent fetches every x seconds the current location of the ISS from the internet by making an http request to https://api.wheretheiss.at/v1/satellites/25544. Once the data is fetched the agent will store this information in the state data store as described by its YANG model. The `show satellite` command will retrieve the geo location from the state datastore and present it in an ASCII world map where it is. The python-based cli has been extended to display the map and geolocation in a custom way by using a custom formatter which is part of the cli-plugin framework SR Linux offers. Learn more about SR Linux [here](https://learn.srlinux.dev/).
## Installing the SRL agent
Clone the repository and copy the rpm file to your SR Linux node
```
scp rpm/srl-satellite-tracker-0.1.0.x86_64.rpm admin@clab-basic-srlinux1:/tmp
```
Install the rpm package by logging into SR Linux cli and enter the linux bash shell
```
[root@pod75 kevin]# ssh admin@clab-basic-srlinux1
Last login: Thu Feb  3 08:26:08 2022 from 2001:172:20:20::1
Using configuration file(s): []
Welcome to the srlinux CLI.
Type 'help' (and press <ENTER>) if you need any help using this.
--{ + running }--[  ]--
A:srlinux1# bash
[admin@srlinux1 ~]$ 
```
```
[admin@srlinux1 ~]$ sudo rpm -U /tmp/srl-satellite-tracker-0.1.0.x86_64.rpm
```

## Configuration
Make sure you have internet connectivity through mgmt network-instance. Once the agent is installed we have to activate it before we can use it.
### Loading the agent
We activate the agent by reloading the app_mgr process
```
A:srlinux1# / tools system app-management application app_mgr reload
```
Verify that the agent is running. In this example it has PID of 3624
```
A:srlinux1# show system application satellite
  +-----------+------+---------+---------+--------------------------+
  |   Name    | PID  |  State  | Version |       Last Change        |
  +===========+======+=========+=========+==========================+
  | satellite | 3624 | running |         | 2022-02-02T19:18:39.546Z |
  +-----------+------+---------+---------+--------------------------+
```
### Configuring DNS
DNS needs to be configured for the mgmt network-instance to make sure the agent can find the api end point. In this example we use Google DNS servers.

```
enter candidate
set / system dns network-instance mgmt
set / system dns server-list [ 8.8.8.8 8.8.4.4]
commit stay
```

Sometimes it's needed to set the local DNS entries

```
enter candidate
set /system dns host-entry api.wheretheiss.at ipv4-address 69.164.207.240
commit now
```
**[Note]:** If you are running SR Linux with a docker image you may also need to add the DNS servers to `/etc/resolv.conf` manually.
### Configure sample interval
The agent will fetch data every 10 seconds by default. This can be changed by setting the satellite interval
```
enter candidate
set / satellite interval 100
commit now
```
## Usage
The ISS is represented on the map as a '#' character when the show satellite command is invoked. The longitude and latitude locations are converted to 2D coordinates on the ASCII map.

![](./img/esa.PNG)
![](./img/satellite-cli.gif)
### State
The agent stores all retrieved information in the state data store. This allows us to do telemetry with [gNMIc](https://gnmic.kmrd.dev/) for example or visualize the data as json or in table view.
![](./img/satellite-state.gif)
### Start/Stop application
```
A:srlinux1# / tools system app-management application satellite stop
```
```
A:srlinux1# / tools system app-management application satellite start
```
