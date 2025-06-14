import re
import time
import configparser
import subprocess

#Functions
def turnOnPlug(power_ip, plug_id):
	print(f"Turning on plug {plug_id} on power strip located at {power_ip}")
	cmd = ['tplink-smarthome-api', 'setPowerState', '--childId', plug_id, power_ip, '1']
	
	print(f"Running cmd - {cmd}")
	result = subprocess.check_output(cmd, text=True)

def turnOffPlug(power_ip, plug_id):
	print(f"Turning off plug {plug_id} on power strip located at {power_ip}")
	cmd = ['tplink-smarthome-api', 'setPowerState', '--childId', plug_id, power_ip, '0']	
	
	print(f"Running cmd - {cmd}")
	result = subprocess.check_output(cmd, text=True)

def scanNetworkForKP303(): #Return IP address of the first KP303 power strip
	print("Scanning network for KP303")
	cmd = ['tplink-smarthome-api', 'search']
	result = subprocess.check_output(cmd, text=True)
	target = "KP303(US) plug IOT.SMARTPLUGSWITCH "
	sub_result = get_after_substring(result, target)
	powerstrip_ip = re.findall( r'[0-9]+(?:\.[0-9]+){3}', sub_result)[0] #Assume first IP in list is the KP303	
	print(f"Found powerstrip - IP {powerstrip_ip}")
	return powerstrip_ip

def get_after_substring(text, target):
    parts = text.split(target, 1)
    if len(parts) > 1:
        return parts[1]
    else:
        raise ValueError(f"{target} not found")

def testConfigSettings(power_ip):
	print(f"Testing config settings {power_ip}")
	cmd = ['tplink-smarthome-api', 'getInfo', power_ip]
	result = subprocess.check_output(cmd, text=True)
	print(f"Successfully connected to TP Link KP303 powerstrip at {power_ip}")

#Classes
class KP303:
	def __init__(self):
		self.plug1 = ""
		self.plug2 = ""
		self.plug3 = ""
		config = configparser.ConfigParser()
		try:
			#Read values from config file first			
			print("Reading files from config.ini")
			config.read('config.ini')
			self.power_ip = config['KP303']['power_ip']
			print(f"Setting powerstrip IP {self.power_ip}")
			
			self.plug1 = config['KP303']['plug_1']
			print(f"Setting plug 1 id - {self.plug1}")
			
			self.plug2 = config['KP303']['plug_2']
			print(f"Setting plug 2 id - {self.plug2}")
			
			self.plug3 = config['KP303']['plug_3']
			print(f"Setting plug 3 id - {self.plug3}")
			
			print(f"Attempting to connect to powerstrip located at {self.power_ip}")
			try:
				testConfigSettings(self.power_ip)
				
			except Exception as e: #if config isn't valid clear it and search network
				print(f"Unable to connect to powerstrip using config settings - IP:{self.power_ip} Plug1: {self.plug1} Plug2: {self.plug2} Plug3 {self.plug3}")
				print("Clearing config.ini")
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
							print(f"Setting plug 1 id - {plugid}")
							self.plug1 = plugid
						elif not self.plug2:
							print(f"Setting plug 2 id - {plugid}")
							self.plug2 = plugid
						elif not self.plug3:
							print(f"Setting plug 3 id - {plugid}")
							self.plug3 = plugid
							
				#Write new values to config file
				with open("config.ini", "w") as file:
					file.write("[KP303]\n")
					file.write(f"power_ip = {self.power_ip}\n")
					file.write(f"plug_1 = {self.plug1}\n")
					file.write(f"plug_2 = {self.plug2}\n")
					file.write(f"plug_3 = {self.plug3}\n")
			
			except Exception as e: #Unable to find a TP LInk KP303 powerstip on the network
				print(f"Unable to find a TP Link KP303 powerstip on the network")
				
							
#Main

#Initialize KP303 object - loads config, and/or searches network for power strip
smartpowerstrip = KP303()
turnOffPlug(smartpowerstrip.power_ip, smartpowerstrip.plug3)
