# MbusTcpMaster
This project aims to develop a generic Mbus master for reading data from Mbus devices.

## Standards
IEC 870-5, EN1434-3

## Connection
For now only the Tcp connection is implemented

## Supported Telegrams
For now only the REQ_UD2 → RSP_UD Request/Respond Procedure with Variable Data Structure is implemented.

## Methods
**MbusTcpMaster.__init__:**   
<code>
<ins>usage:</ins> result = MbusTcpMaster(host, port, [name, auto_connect])  

<ins>args:</ins>  
host: IP address of TCP/Mbus bridge  
port: Port 

<ins>kwargs:</ins>  
name: Name for this instance (str:'')  
auto_connect: Connect after initialization (bool:True)  

<ins>returns:</ins>  Initialized connection    
</code>



**scan_slaves_primary:**  
<code>
<ins>usage:</ins> slaves = test.scan_slaves_primary([scan_timeout, stop_at])  
 
<ins>kwargs:</ins>  
scan_timeout: How long to wait for response from an address (float:1.0)	 
stop_at: Quit looking for more slaves after this number of detected slaves (int:250)  

<ins>returns:</ins>   
A dictionary with Fixed Data Headers (FDH's) part of the response of the detected slaves, keyed on their primary addresses.  
An FDH contains: IdentificationNo. Manufr. Version Medium AccessNo. Status Signature  
</code>

**get_all_fields:**  
<code>
<ins>usage:</ins> result = test.get_all_fields(slave_address, [extensive_mode, scale_results])  

<ins>args:</ins>  
slave_address: slave address to send request to (int:1)  

<ins>kwargs:</ins>  
extensive_mode: generate extra field information in the 'fields' part of the result (bool:False)  
scale_results: Return scaled values (bool:True)  

<ins>returns:</ins>  
All fields/registers from 1 specific slave address. (only VARIABLE DATA STRUCTURE is supported at this moment)  
returns a dictionary with the FDH information of this slave and a 'fields' key  

In extensive_mode the full Variable Data STructure (VDS) is added in the reponse field as a bytearray  

In default mode the 'fields' key contains a list of dictionaries (1 per decoded field/register) with: Description, Value, Unit 
Descr consists of: function_descr storage_nr:tariff in order to distinguish between the different variations of the same description  
Example: Act_Energy 0:0  

In extensive_mode The following extra information is added per field:  
function: Min, Max, Actual or Error type of value  
storage:  
tariff:   
orig_value: Value before scaling  
scaling: Scaling factor 
DR_startindex: Startindex of this  Data Record in the Variable Data Structure part of the response 
DR: The actual, undecoded, Data Record (Data Record Header + Data) as a bytearray  
decoder: The used decoder   

Using extensive_mode one could decide to decode and scale the data outside of the MbusTcpMaster.
</code>

## How to use
Using the MbusTcpMaster the 'look' and 'feel' should be similar to using the ModbusTcpClient from the pymodbus package

Example:

```
from MbusTcpMaster import MbusTcpMaster

# Create an instance of the MbusTcpMaster (replace ip_address and port with the appropriate values)
test = MbusTcpMaster(host='192.168.178.204', port=10001)

# get all slaves on the bus (this may take a while to scan...)
slaves = test.scan_slaves_primary(stop_at=2)

if slaves:
	for slave_address in slaves:
		# get all the fields/registers from the slave
		results = test.get_all_fields(slave_address=slave_address, extensive_mode=True)
		
		for i,j in results.items():
			if i=='fields': continue
			print(f'{i}:{j}')
			
			
		for field in results['fields']:
			print(' '.join(f'{i}:{j}' for i,j in field.items()))
			
		print()

# close the connection
test.close()

```

