# Domoticz SDM120c ModbusTCP plugin

A Domoticz plugin to collect data from SDM120c power meter ModbusTCP.

## Requirements

You need the SDM120C to be connected over modbus over TCP. Wired or wireless.
Setup that use this on this plugin is using PW21

You need also to find the address of the SDM120C. You can find it using the
push button. Per default the address is 1.

## Installation of the plugin

This guide is based on Ubuntu 20.04 LTS:

Install `pip3`:

``` shell
sudo apt install python3-pip
```

Install `domoticz`:

``` shell
curl -sSL install.domoticz.com | sudo bash
```

Make sure that the `plugins` folder exists in the `domoticz` folder.

Install the plugin:

``` shell
cd domoticz/plugins
git clone https://github.com/xbeaudouin/domoticz-sdm120c-modbus-tcp.git
```

Go to the plugin folder and install all required addons:

``` shell
cd domoticz/plugins/domoticz-sdm120c-modbus-tcp
sudo pip3 install -r requirements.txt
```

Once that is done, restart domoticz:

``` shell
sudo service domoticz.sh restart
```

## Configuration in Domoticz

Once the plugin is installed, a new hardware type will be available: `SDM120c ModbusTCP`.

To add the inverter, go to `Setup` -> `Hardware` and add the counter:

- Enter a `name` for the counter.
- Select `SDM120c ModbusTCP` from the `type` dropdown list.
- Enter the IP address of the PW21 in the `IP Address` field.
- Enter the port number (default: 502) of the PW21 in the `Port Number` field.
- Optionally turn on `Debug`; be aware: this will generate a lot of entries in the Domoticz log!
- `Add` the counter.

This should result in a lot of new devices in the `Setup` -> `Devices` menu.

## Updating the plugin

Go to the plugin folder and get the new verion:

``` shell
cd domoticz/plugins/domoticz-sdm120c-modbus-tcp
git pull
```

Once that is done, restart domoticz:

``` shell
sudo service domoticz.sh restart
```
## ScreenShots

TODO

## Documentation about the registers used.

TODO


