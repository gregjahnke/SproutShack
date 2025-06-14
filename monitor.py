import re
import time
import configparser
import subprocess
import smbus2
import bme280
import matplotlib.pyplot as plt

from datetime import datetime


#Functions
def turnOnPlug(power_ip, plug_id): #Turn on plug on powerstrip
	print(f"{datetime.now()} - Turning on plug {plug_id} on power strip located at {power_ip}")
	cmd = ['tplink-smarthome-api', 'setPowerState', '--childId', plug_id, power_ip, '1']
	
	print(f"{datetime.now()} - Running cmd - {cmd}")
	result = subprocess.check_output(cmd, text=True)

def turnOffPlug(power_ip, plug_id): #Turn off plug on powerstrip
	print(f"{datetime.now()} - Turning off plug {plug_id} on power strip located at {power_ip}")
	cmd = ['tplink-smarthome-api', 'setPowerState', '--childId', plug_id, power_ip, '0']	
	
	print(f"{datetime.now()} - Running cmd - {cmd}")
	result = subprocess.check_output(cmd, text=True)

def scanNetworkForKP303(): #Return IP address of the first KP303 power strip
	print(f"{datetime.now()} - Scanning network for KP303")
	cmd = ['tplink-smarthome-api', 'search']
	result = subprocess.check_output(cmd, text=True)
	target = "KP303(US) plug IOT.SMARTPLUGSWITCH "
	sub_result = get_after_substring(result, target)
	powerstrip_ip = re.findall( r'[0-9]+(?:\.[0-9]+){3}', sub_result)[0] #Assume first IP in list is the KP303	
	print(f"{datetime.now()} - Found powerstrip - IP {powerstrip_ip}")
	return powerstrip_ip

def get_after_substring(text, target):
    parts = text.split(target, 1)
    if len(parts) > 1:
        return parts[1]
    else:
        raise ValueError(f"{target} not found")

def testConfigSettings(power_ip):
	print(f"{datetime.now()} - Testing config settings {power_ip}")
	cmd = ['tplink-smarthome-api', 'getInfo', power_ip]
	result = subprocess.check_output(cmd, text=True)
	print(f"{datetime.now()} - Successfully connected to TP Link KP303 powerstrip at {power_ip}")

def hpa_to_inhg(pressure_hpa):
  pressure_inhg = pressure_hpa * 0.02953
  return pressure_inhg

#Classes
class KP303:
	def __init__(self):
		self.plug1 = ""
		self.plug2 = ""
		self.plug3 = ""
		config = configparser.ConfigParser()
		try:
			#Read values from config file first			
			print(f"{datetime.now()} - Reading files from config.ini")
			config.read('config.ini')
			self.power_ip = config['KP303']['power_ip']
			print(f"{datetime.now()} - Setting powerstrip IP {self.power_ip}")
			
			self.plug1 = config['KP303']['plug_1']
			print(f"{datetime.now()} - Setting plug 1 id - {self.plug1}")
			
			self.plug2 = config['KP303']['plug_2']
			print(f"{datetime.now()} - Setting plug 2 id - {self.plug2}")
			
			self.plug3 = config['KP303']['plug_3']
			print(f"{datetime.now()} - Setting plug 3 id - {self.plug3}")
			
			print(f"{datetime.now()} - Attempting to connect to powerstrip located at {self.power_ip}")
			try:
				testConfigSettings(self.power_ip)
				
			except Exception as e: #if config isn't valid clear it and search network
				print(f"{datetime.now()} - Unable to connect to powerstrip using config settings - IP:{self.power_ip} Plug1: {self.plug1} Plug2: {self.plug2} Plug3 {self.plug3}")
				print(f"{datetime.now()} - Clearing config.ini")
				with open("config.ini", "w") as file:
					file.truncate(0)
				raise Exception("Unable to connect to power strip based on config settings")				
			
		except Exception as e: #if there is any error reading config - search network and create
			
			try:
				#Search network for values
				self.power_ip = scanNetworkForKP303()
				
				cmd = ['tplink-smarthome-api', 'getInfo', self.power_ip]
				result = subprocess.check_output(cmd, text=True)

				#Manually parse the javascript object output looking for plug ids
				lines = result.splitlines()
				for line in lines:
					if "id" in line:
						plugid = get_after_substring(line, "id: ")
						plugid = plugid.replace("'","") #remove single quotes
						plugid = plugid.replace(",","") #remove comma
						plugid = plugid.replace("\x1b[32m","") #remove escape code start for green
						plugid = plugid.replace("\x1b[39m","") #remove escape code end for green
						if not self.plug1:
							print(f"{datetime.now()} - Setting plug 1 id - {plugid}")
							self.plug1 = plugid
						elif not self.plug2:
							print(f"{datetime.now()} - Setting plug 2 id - {plugid}")
							self.plug2 = plugid
						elif not self.plug3:
							print(f"{datetime.now()} - Setting plug 3 id - {plugid}")
							self.plug3 = plugid
							
				#Write new values to config file
				with open("config.ini", "w") as file:
					file.write("[KP303]\n")
					file.write(f"power_ip = {self.power_ip}\n")
					file.write(f"plug_1 = {self.plug1}\n")
					file.write(f"plug_2 = {self.plug2}\n")
					file.write(f"plug_3 = {self.plug3}\n")
			
			except Exception as e: #Unable to find a TP LInk KP303 powerstip on the network
				print(f"{datetime.now()} - Unable to find a TP Link KP303 powerstip on the network")				
							
#Main

#Initialize KP303 object - loads config, and/or searches network for power strip
smartpowerstrip = KP303()

# BME280 sensor address (default address)
address = 0x76

# Initialize I2C bus
bus = smbus2.SMBus(1)

# Load calibration parameters
calibration_params = bme280.load_calibration_params(bus, address)

# Read sensor data
print(f"{datetime.now()} - Reading sensor data from bme280 at bus {bus} and address {address}")
data = bme280.sample(bus, address, calibration_params)

# Extract temperature, pressure, and humidity
temperature_celsius = data.temperature
temperature_fahrenheit = (temperature_celsius * 9/5) + 32
humidity = data.humidity
pressure_hPa = data.pressure
pressure_inHg = pressure_hPa * 0.02953
print(f"{datetime.now()} - Temperature: {temperature_celsius}(ÂºC) {temperature_fahrenheit}(ÂºF) Humidity: {humidity}(%) Pressure {pressure_hPa}(hPa) {pressure_inHg}(inHg)")
