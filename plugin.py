#!/usr/bin/env python
"""
SDM120c Energy Meter
Author: Xavier Beaudouin
Requirements: 
    1. modbus over TCP adapter like PW21
    2. pymodbus AND pymodbusTCP
"""
"""
<plugin key="SDM120c_ModbusTCP" name="SDM120c ModbusTCP" author="Xavier Beaudouin" version="0.0.1" externallink="https://github.com/xbeaudouin/domoticz-sdm120c-modbus-tcp">
    <params>
        <param field="Address" label="IP Address" width="150px" required="true" />
        <param field="Port" label="Port Number" width="100px" required="true" default="502" />
        <param field="Mode3" label="Modbus address" width="100px" required="true" default="1" />
        <param field="Mode5" label="Collect extended data" width="100px">
            <options>
                <option label="Enabled" value="Moredata"/>
                <option label="Disabled" value="Regular" default="true" />
            </options>
        </param>
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
sys.path.append('/usr/local/lib/python3.10/dist-packages')

import pymodbus

from pyModbusTCP.client import ModbusClient
from pymodbus.constants import Endian
from pymodbus.payload   import BinaryPayloadDecoder

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

    def strget(self):
        return str(sum(self.samples) / len(self.samples))

# Plugin itself
class BasePlugin:
    def __init__(self):
        # Voltage for last 5 minutes
        self.voltage=Average()
        # Current for last 5 minutes
        self.current=Average()
	    # Apparent Power for last 5 minutes
        self.apparent_power=Average()
        # Active power for last 5 minutes
        self.active_power=Average()
        # Reactive power for last 5 minutes
        self.reactive_power=Average()
        # Power factor for last 5 minutes
        self.power_factor=Average()
	    # Phase Angle for last 5 minutes
        self.phase_angle=Average()
        # Frequency for last 5 minutes
        self.frequency=Average()
        # Total demand power for last 5 minutes
        self.total_demand_power=Average()
        # Import demand power for last 5 minutes
        self.import_demand_power=Average()
        # Export demand power for last 5 minutes
        self.export_demand_power=Average()
        # Total Demand Current for last 5 minutes
        self.total_demand_current=Average()

        return

    def onStart(self):
        Domoticz.Log("SDM120c Energy Meter TCP loaded!")

        # Check dependancies
        try:
            if (float(Parameters["DomoticzVersion"][:6]) < float("2020.2")): Domoticz.Error("WARNING: Domoticz version is outdated or not supported. Please update!")
            if (float(sys.version[:1]) < 3): Domoticz.Error("WARNING: Python3 should be used !")
        except:
            Domoticz.Error("Warning ! Dependancies could not be checked !")

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
            Domoticz.Device(Name="Import Energy",                Unit=9,  Type=243, Subtype=29, Used=0).Create()
        if 10 not in Devices:
            Domoticz.Device(Name="Export Energy",                Unit=10, Type=243, Subtype=29, Used=0).Create()
	    # 11 will be not used Import Energy (Reactive) / kVArh
	    # 12 will be not used Export Energy (Reactive) / kVArh
        if Parameters["Mode5"] == "Moredata":
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
            if Parameters["Mode5"] == "Moredata":
                Devices[13].Update(1, "0")
                Devices[14].Update(1, "0")
                Devices[15].Update(1, "0")
                Devices[16].Update(1, "0")
                Devices[17].Update(1, "0")
                Devices[18].Update(1, "0")
                Devices[19].Update(1, "0")
                Devices[20].Update(1, "0")

            Devices[21].Update(1, "0")

        #Domoticz.Log("Voltage : "          + str(getmodbus(0x0000, client)) )
        self.voltage.update(getmodbus(0x0000, client))
        Devices[1].Update(1, self.voltage.strget())

        #Domoticz.Log("Current : "          + str(getmodbus(0x0006, client)) )
        self.current.update(getmodbus(0x0006, client))
        Devices[2].Update(1, self.current.strget())

        #Domoticz.Log("Power Active : "     + str(getmodbus(0x000c, client)) )
        self.active_power.update(getmodbus(0x000c, client))
        Devices[3].Update(1, self.active_power.strget())

        #Domoticz.Log("Power apparent: "   + str(getmodbus(0x0012, client)) )
        self.apparent_power.update(getmodbus(0x0012, client))
        Devices[4].Update(1, self.apparent_power.strget())

        #Domoticz.Log("Power reactive:  "   + str(getmodbus(0x0018, client)) )
        self.reactive_power.update(getmodbus(0x0018, client))
        Devices[5].Update(1, self.reactive_power.strget())

        #Domoticz.Log("Power Factor : "     + str(getmodbus(0x001e, client)) )
        self.power_factor.update(getmodbus(0x001e, client))
        Devices[6].Update(1, self.power_factor.strget())

        #Domoticz.Log("Phase Angle : "      + str(getmodbus(0x0024, client)) )
        self.phase_angle.update(getmodbus(0x0024, client))
        Devices[7].Update(1, self.phase_angle.strget())

        #Domoticz.Log("Frequency : "        + str(getmodbus(0x0046, client)) )
        self.frequency.update(getmodbus(0x0046, client))
        Devices[8].Update(1, self.frequency.strget())

        power = self.active_power.get()
        if power >= 0:
            import_power = power
        else:
            import_power = 0

        if power < 0:
            export_power = abs(power)
        else:
            export_power = 0

        #Domoticz.Log("Import NRJ act : "   + str(getmodbus(0x0048, client)) )
        import_e = str(getmodbus(0x0048, client)*1000)
        Devices[9].Update(1, sValue=str(import_power)+";"+import_e)
        
        #Domoticz.Log("Export NRJ act : "   + str(getmodbus(0x004a, client)) )
        export_e = str(getmodbus(0x004a, client)*1000)
        Devices[10].Update(1, sValue=str(export_power)+";"+export_e)

        if Parameters["Mode5"] == "Moredata":
            #Domoticz.Log("Total Demand Pwr : " + str(getmodbus(0x0054, client)) )
            self.total_demand_power.update(getmodbus(0x0054, client))
            Devices[13].Update(1, self.total_demand_power.strget())

            #Domoticz.Log("Max Demand Pwr : "   + str(getmodbus(0x0056, client)) )
            Devices[14].Update(1, str(getmodbus(0x0056, client)))

            #Domoticz.Log("Input Demand Pwr : " + str(getmodbus(0x0058, client)) )
            self.import_demand_power.update(getmodbus(0x0058, client))
            Devices[15].Update(1, self.import_demand_power.strget())

            #Domoticz.Log("Max Input Demand Pwr : " + str(getmodbus(0x005a, client)) )
            Devices[16].Update(1, str(getmodbus(0x005a, client)))

            #Domoticz.Log("Export Demand Pwr : " + str(getmodbus(0x005c, client)) )
            self.import_demand_power.update(getmodbus(0x0058, client))
            Devices[17].Update(1, self.import_demand_power.strget())

            #Domoticz.Log("Max Export Demand Pwr : " + str(getmodbus(0x005e, client)) )
            Devices[18].Update(1, str(getmodbus(0x005e, client)))

            #Domoticz.Log("Total Demand Cur: " + str(getmodbus(0x0102, client)) )
            self.total_demand_current.update(getmodbus(0x0102, client))
            Devices[19].Update(1, self.total_demand_current.strget())

            #Domoticz.Log("Max Total Demand Cur: " + str(getmodbus(0x0108, client)) )
            Devices[20].Update(1, str(getmodbus(0x0108, client)))


        #Domoticz.Log("Total Energy Act: " + str(getmodbus(0x0156, client)) )
        Devices[21].Update(1, sValue=import_e+";0;"+export_e+";0;"+str(import_power)+";"+str(export_power))
        

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


# get Modbus float 32 bits values
def getmodbus(register, client):
    value = 0
    try:
        data = client.read_input_registers(register, 2)
        Domoticz.Debug("Data from register "+str(register)+": "+str(data))
        decoder = BinaryPayloadDecoder.fromRegisters(data, byteorder=Endian.Big, wordorder=Endian.Big)
        value = round(decoder.decode_32bit_float(), 3)
    except:
        Domoticz.Error("Error getting data from "+str(register) + ", try 1")
        try:
            data = client.read_input_registers(register, 2)
            Domoticz.Debug("Data from register "+str(register)+": "+str(data))
            decoder = BinaryPayloadDecoder.fromRegisters(data, byteorder=Endian.Big, wordorder=Endian.Big)
            value = round(decoder.decode_32bit_float(), 3)
        except:
            Domoticz.Error("Error getting data from "+str(register) + ", try 2")

    return value



