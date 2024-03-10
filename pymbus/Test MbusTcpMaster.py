#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  Test MbusTcpMaster.py
#  
#  Copyright 2024  <pi@raspberrypi>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
#  

from MbusTcpMaster import MbusTcpMaster

def main(args):
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
	

if __name__ == '__main__':
	import sys
	sys.exit(main(sys.argv))
