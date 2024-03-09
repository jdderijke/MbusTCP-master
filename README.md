# MbusTcpMaster
This project aims to develop a generic Mbus master for reading data from Mbus devices.

## Standards
IEC 870-5, EN1434-3

## Connection
For now only the Tcp connection is implemented

## Supported Telegrams
For now only the REQ_UD2 → RSP_UD Request/Respond Procedure with Variable Data Structure is implemented.

## Methods
**MbusTcpMaster:**
		result = MbusTcpMaster(host, port, [name, auto_connect])
args:
		host:			IP address of TCP/Mbus bridge
		port:			Port
kwargs:
		name:			(str:'')		Name for this instance
		auto_connect:	(bool:True)		Connect after initialization ()
returns:		
		Initialized connection
		
**scan_slaves_primary:**
		slaves = test.scan_slaves_primary([scan_timeout, stop_at])
kwargs:
		scan_timeout:	(float:1.0)		How long to wait for response from an address
		stop_at:		(int:250)		Quit looking for more slaves after this number of detected slaves
returns:
		A dictionary with Fixed Data Headers (FDH's) part of the response of the detected slaves, keyed on their primary addresses.
		An FDH contains: Ident. Nr. Manufr. Version Medium AccessNo. Status Signature
		
**get_all_fields:**
		result = test.get_all_fields(slave_address, [extensive_mode, scale_results])
args:
		slave_address:	(int:1)			slave address to send request to
kwargs:
		extensive_mode:	(bool:False)	generate extra field information in the 'fields' part of the result
		scale_results:	(bool:True)		Return scaled values
returns:
		All fields/registers from 1 specific slave address. (only VARIABLE DATA STRUCTURE is supported at this moment)
		returns a dictionary with the FDH information of this slave and a 'fields' key 
		The 'fields' key contains a list of dictionaries (1 per decoded field/register) with: Description, Value, Unit
		

## How to use
Using the MbusTcpMaster the 'look' and 'feel' should be similar to using the ModbusTcpClient from the pymodbus package

Example:

```
from MbusTcpMaster import MbusTcpMaster


# Create an instance of the MbusTcpMaster (replace ip_address and port with the appropriate values)
test = MbusTcpMaster(host='ip_address', port=port)

# get all slaves on the bus (this may take a while to scan... so we limit the maximum to 2)
slaves = test.scan_slaves_primary(stop_at=2)

if slaves:
	for slave_address in slaves:
		# get all the fields/registers from the slave
		results = test.get_all_fields(slave_address=slave_address)
		
		for field in results['fields']:
			print(' '.join(f'{j}' for i,j in field.items()))
			
		print()

# close the connection
test.close()

```


