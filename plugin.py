#!/usr/bin/env python
"""
SDM120c Energy Meter
Author: Xavier Beaudouin
Requirements: 
    1. modbus over TCP adapter like PW21
    2. pymodbus AND pymodbusTCP
"""
"""
<plugin key="DS238_ModbusTCP" name="SDM120c ModbusTCP" author="Xavier Beaudouin" version="0.0.1" externallink="https://github.com/xbeaudouin/domoticz-sdm120c-modbus-tcp">
    <params>
        <param field="Address" label="IP Address" width="150px" required="true" />
        <param field="Port" label="Port Number" width="100px" required="true" default="502" />
        <param field="Mode3" label="Modbus address" width="100px" required="true" default="1" />
        <param field="Mode6" label="Debug" width="100px">
            <options>
                <option label="True" value="Debug"/>
                <option label="False" value="Normal" default="true" />
            </options>
        </param>
    </params>
</plugin>
"""

import Domoticz
import sys

sys.path.append('/usr/local/lib/python3.4/dist-packages')
sys.path.append('/usr/local/lib/python3.5/dist-packages')
sys.path.append('/usr/local/lib/python3.6/dist-packages')
sys.path.append('/usr/local/lib/python3.7/dist-packages')
sys.path.append('/usr/local/lib/python3.8/dist-packages')
sys.path.append('/usr/local/lib/python3.9/dist-packages')

import sdm_modbus

#
# Domoticz shows graphs with intervals of 5 minutes.
# When collecting information from the inverter more frequently than that, then it makes no sense to only show the last value.
#
# The Average class can be used to calculate the average value based on a sliding window of samples.
# The number of samples stored depends on the interval used to collect the value from the inverter itself.
#

class Average:

    def __init__(self):
        self.samples = []
        self.max_samples = 30

    def set_max_samples(self, max):
        self.max_samples = max
        if self.max_samples < 1:
            self.max_samples = 1

    def update(self, new_value, scale = 0):
        self.samples.append(new_value * (10 ** scale))
        while (len(self.samples) > self.max_samples):
            del self.samples[0]

        Domoticz.Debug("Average: {} - {} values".format(self.get(), len(self.samples)))

    def get(self):
        return sum(self.samples) / len(self.samples)

#
# Domoticz shows graphs with intervals of 5 minutes.
# When collecting information from the inverter more frequently than that, then it makes no sense to only show the last value.
#
# The Maximum class can be used to calculate the highest value based on a sliding window of samples.
# The number of samples stored depends on the interval used to collect the value from the inverter itself.
#

class Maximum:

    def __init__(self):
        self.samples = []
        self.max_samples = 30

    def set_max_samples(self, max):
        self.max_samples = max
        if self.max_samples < 1:
            self.max_samples = 1

    def update(self, new_value, scale = 0):
        self.samples.append(new_value * (10 ** scale))
        while (len(self.samples) > self.max_samples):
            del self.samples[0]

        Domoticz.Debug("Maximum: {} - {} values".format(self.get(), len(self.samples)))

    def get(self):
        return max(self.samples)

# Plugin itself
class BasePlugin:
    #enabled = False
    def __init__(self):
        # Voltage for last 5 minutes
        self.voltage=Average()
        # Current for last 5 minutes
        self.current=Average()
        # Active power for last 5 minutes
        self.active_power=Average()
	# Apparent Power for last 5 minutes
	self.apparent_power=Average()
        # Reactive power for last 5 minutes
        self.reactive_power=Average()
        # Power factor for last 5 minutes
        self.power_factor=Average()
	# Phase Angle for last 5 minutes
	self.phase_angle=Average()
        # Frequency for last 5 minutes
        self.frequency=Average()

        return

    def onStart(self):
        Domoticz.Log("SDM120c Energy Meter TCP loaded!")

        # Check dependancies
        try:
            if (float(Parameters["DomoticzVersion"][:6]) < float("2020.2")): Domoticz.Error("WARNING: Domoticz version is outdated or not supported. Please update!")
            if (float(sys.version[:1]) < 3): Domoticz.Error("WARNING: Python3 should be used !")
        except:
            Domoticz.Error("Warning ! Dependancies could not be checked !")

        # Parse parameters
        
        # Debug
        if Parameters["Mode6"] == "Debug":
            Domoticz.Debugging(1)
        else:
            Domoticz.Debugging(0)

        self.IPAddress = Parameters["Address"]
        self.IPPort    = Parameters["Port"]
        self.MBAddr    = int(Parameters["Mode3"])

        Domoticz.Debug("Query IP " + self.IPAddress + ":" + str(self.IPPort) +" on device : "+str(self.MBAddr))

        # Create the devices if they does not exists
        # TODO: refactor this.
	if 1 not in Devices:
            Domoticz.Device(Name="Voltage",                      Unit=1,  TypeName="Voltage", Used=0).Create()
	if 2 not in Devices:
            Domoticz.Device(Name="Current",                      Unit=2,  TypeName="Current (Single)", Used=0).Create()
	if 3 not in Devices:
            Options = { "Custom": "1;W" }
            Domoticz.Device(Name="Active Power",                 Unit=3,  TypeName="Custom", Used=0, Options=Options).Create()
	if 4 not in Devices:
            Options = { "Custom": "1;VA" }
            Domoticz.Device(Name="Apparent Power",               Unit=4,  TypeName="Custom", Used=0, Options=Options).Create()
	if 5 not in Devices:
            Options = { "Custom": "1;VAr" }
            Domoticz.Device(Name="Reactive Power",               Unit=5,  TypeName="Custom", Used=0, Options=Options).Create()
	if 6 not in Devices:
            Options = { "Custom": "1;PF" }
            Domoticz.Device(Name="Power Factor",                 Unit=6,  TypeName="Custom", Used=0, Options=Options).Create()
	if 7 not in Devices:
            Options = { "Custom": "1;Deg" }
            Domoticz.Device(Name="Phase Angle",                  Unit=7,  TypeName="Custom", Used=0, Options=Options).Create()
        if 8 not in Devices:
            Options = { "Custom": "1;Hz" }
            Domoticz.Device(Name="Frequency",                    Unit=8,  TypeName="Custom", Used=0, Options=Options).Create()
        if 9 not in Devices:
            Domoticz.Device(Name="Import Energy",                Unit=9,  Type=0xfa, Subtype=0x01, Used=0).Create()
        if 10 not in Devices:
            Domoticz.Device(Name="Export Energy",                Unit=10, Type=0xfa, Subtype=0x01, Used=0).Create()
	# 11 will be not used Import Energy (Reactive) / kVArh
	# 12 will be not used Export Energy (Reactive) / kVArh
	if 13 not in Devices:
            Options = { "Custom": "1;W" }
            Domoticz.Device(Name="Total Demand Power",           Unit=13, TypeName="Custom", Used=0, Options=Options).Create()
	if 14 not in Devices:
            Options = { "Custom": "1;W" }
            Domoticz.Device(Name="Maximum Total Demand Power",   Unit=14, TypeName="Custom", Used=0, Options=Options).Create()
	if 15 not in Devices:
            Options = { "Custom": "1;W" }
            Domoticz.Device(Name="Import Demand Power",          Unit=15, TypeName="Custom", Used=0, Options=Options).Create()
	if 16 not in Devices:
            Options = { "Custom": "1;W" }
            Domoticz.Device(Name="Maximum Import Demand Power",  Unit=16, TypeName="Custom", Used=0, Options=Options).Create()
	if 17 not in Devices:
            Options = { "Custom": "1;W" }
            Domoticz.Device(Name="Export Demand Power",          Unit=17, TypeName="Custom", Used=0, Options=Options).Create()
	if 18 not in Devices:
            Options = { "Custom": "1;W" }
            Domoticz.Device(Name="Maximum Export Demand Power",  Unit=18, TypeName="Custom", Used=0, Options=Options).Create()
        if 19 not in Devices:
            Domoticz.Device(Name="Total Demand Current",         Unit=19, TypeName="Current (Single)", Used=0).Create()
        if 20 not in Devices:
            Domoticz.Device(Name="Maximum Total Demand Current", Unit=20, TypeName="Current (Single)", Used=0).Create()
        if 21 not in Devices:
            Domoticz.Device(Name="Total Energy (Active)",        Unit=21, Type=0xfa, Subtype=0x01, Used=0).Create()
	# 22 will not be used Total Energy (Reactive)

        return


    def onStop(self):
        Domoticz.Debugging(0)

    def onHeartbeat(self):
        Domoticz.Debug(" Interface : IP="+self.IPAddress +", Port="+str(self.IPPort)+" ID="+str(self.MBAddr))
        try:
            client = ModbusClient(host=self.IPAddress, port=self.IPPort, unit_id=self.MBAddr, auto_open=True, auto_close=True, timeout=2)
        except:
            Domoticz.Error("Error connecting to TCP/Interface on address : "+self.IPaddress+":"+str(self.IPPort))
            # Set value to 0 -> Error on all devices
            Devices[1].Update(1, "0")
            Devices[2].Update(1, "0")
            Devices[3].Update(1, "0")
            Devices[4].Update(1, "0")
            Devices[5].Update(1, "0")
            Devices[6].Update(1, "0")
            Devices[7].Update(1, "0")
            Devices[8].Update(1, "0")
            Devices[9].Update(1, "0")
            Devices[10].Update(1, "0")
            Devices[13].Update(1, "0")
            Devices[14].Update(1, "0")
            Devices[15].Update(1, "0")
            Devices[16].Update(1, "0")
            Devices[17].Update(1, "0")
            Devices[18].Update(1, "0")
            Devices[19].Update(1, "0")
            Devices[20].Update(1, "0")
            Devices[21].Update(1, "0")

	# XXX: Finish that.

        # TODO: catch errors
        # 3 counters
        total_e = "0"
        export_e = "0"
        import_e = "0"
        export_w = 0
        import_w = 0
        power = "0"

        # Total Energy
        data = client.read_holding_registers(0, 2)
        Domoticz.Debug("Data from register 0: "+str(data))
        # Unsigned 32 
        decoder = BinaryPayloadDecoder.fromRegisters(data, byteorder=Endian.Big, wordorder=Endian.Big)
        # Value
        value = decoder.decode_32bit_int()
        total_e = str(value)

        # Export Energy
        data = client.read_holding_registers(0x8, 2)
        Domoticz.Debug("Data from register 0x8: "+str(data))
        # Unsigned 32 
        decoder = BinaryPayloadDecoder.fromRegisters(data, byteorder=Endian.Big, wordorder=Endian.Big)
        # Value
        value = decoder.decode_32bit_int()
        export_e = str(value)

        # Import Energy
        data = client.read_holding_registers(0xA, 2)
        Domoticz.Debug("Data from register 0xA: "+str(data))
        # Unsigned 32 
        decoder = BinaryPayloadDecoder.fromRegisters(data, byteorder=Endian.Big, wordorder=Endian.Big)
        # Value
        value = decoder.decode_32bit_int()
        import_e = str(value)

        # Voltage
        data = client.read_holding_registers(0xC, 1)
        Domoticz.Debug("Data from register 0xC: "+str(data))
        # Unsigned 16
        decoder = BinaryPayloadDecoder.fromRegisters(data, byteorder=Endian.Big, wordorder=Endian.Big)
        # Value
        value = decoder.decode_16bit_int()
        # Scale factor / 10
        value = round (value / 10, 3)
        Domoticz.Debug("Value after conversion : "+str(value))
        Domoticz.Debug("-> Calculating average")
        self.voltage.update(value)
        value = self.voltage.get()
        Domoticz.Debug(" = {}".format(value))
        Devices[4].Update(1, str(value))

        # Current
        data = client.read_holding_registers(0xD, 1)
        Domoticz.Debug("Data from register 0xD: "+str(data))
        # Unsigned 16
        decoder = BinaryPayloadDecoder.fromRegisters(data, byteorder=Endian.Big, wordorder=Endian.Big)
        # Value
        value = decoder.decode_16bit_int()
        # Scale factor / 100
        value = round (value / 100, 3)
        Domoticz.Debug("Value after conversion : "+str(value))
        Domoticz.Debug("-> Calculating average")
        self.current.update(value)
        value = self.current.get()
        Domoticz.Debug(" = {}".format(value))
        Devices[5].Update(1, str(value))

        # Active Power
        data = client.read_holding_registers(0xE, 1)
        Domoticz.Debug("Data from register 0xE: "+str(data))
        # Unsigned 16
        decoder = BinaryPayloadDecoder.fromRegisters(data, byteorder=Endian.Big, wordorder=Endian.Big)
        # Value
        value = decoder.decode_16bit_int()
        Domoticz.Debug("Value after conversion : "+str(value))
        Domoticz.Debug("-> Calculating average")
        self.active_power.update(value)
        value = self.active_power.get()
        Domoticz.Debug(" = {}".format(value))
        Devices[6].Update(1, str(value))
        if value > 0.0:
            import_w = value
        if value < 0.0:
            export_w = value
        power = str(abs(value))

        # Reactive Power
        data = client.read_holding_registers(0xF, 1)
        Domoticz.Debug("Data from register 0xF: "+str(data))
        # Unsigned 16
        decoder = BinaryPayloadDecoder.fromRegisters(data, byteorder=Endian.Big, wordorder=Endian.Big)
        # Value
        value = decoder.decode_16bit_int()
        Domoticz.Debug("Value after conversion : "+str(value))
        Domoticz.Debug("-> Calculating average")
        self.reactive_power.update(value)
        value = self.reactive_power.get()
        Domoticz.Debug(" = {}".format(value))
        Devices[7].Update(1, str(value))

        # Power Factor
        data = client.read_holding_registers(0x10, 1)
        Domoticz.Debug("Data from register 0x10: "+str(data))
        # Unsigned 16
        decoder = BinaryPayloadDecoder.fromRegisters(data, byteorder=Endian.Big, wordorder=Endian.Big)
        # Value
        value = decoder.decode_16bit_int()
        # Scale factor / 1000
        value = round (value / 1000, 3)
        Domoticz.Debug("Value after conversion : "+str(value))
        Domoticz.Debug("-> Calculating average")
        self.power_factor.update(value)
        value = self.power_factor.get()
        Domoticz.Debug(" = {}".format(value))
        Devices[8].Update(1, str(value))

        # Frequency
        data = client.read_holding_registers(0x11, 1)
        Domoticz.Debug("Data from register 0x11: "+str(data))
        # Unsigned 16
        decoder = BinaryPayloadDecoder.fromRegisters(data, byteorder=Endian.Big, wordorder=Endian.Big)
        # Value
        value = decoder.decode_16bit_int()
        # Scale factor / 100
        value = round (value / 100, 3)
        Domoticz.Debug("Value after conversion : "+str(value))
        Domoticz.Debug("-> Calculating average")
        self.frequency.update(value)
        value = self.frequency.get()
        Domoticz.Debug(" = {}".format(value))
        Devices[9].Update(1, str(value))


        # Do insert data on counters 
        Devices[1].Update(1, sValue=total_e+"0;0;0;0;"+power+";0")
        Devices[2].Update(1, sValue=export_e+"0;0;0;0;"+str(abs(export_w))+";0")
        Devices[3].Update(1, sValue=import_e+"0;0;0;0;"+str(abs(import_w))+";0")
        Devices[10].Update(1, sValue=import_e+"0;0;"+export_e+"0;0;"+str(abs(import_w))+";"+str(abs(export_w)))


global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

    # Generic helper functions
def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug( "'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
    return
