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
			results = test.get_all_fields(slave_address=slave_address)
			
			for field in results['fields']:
				print(' '.join(f'{j}' for i,j in field.items()))
				
			print()
	
	# close the connection
	test.close()
	
	
	
	
	
	# test = MbusTcpMaster(host='192.168.178.204', port=10001, extensive_mode=False, scale_results=True, name='Vermogensmeters Twentseweg')
	
	# slaves = test.scan_slaves_primary()
	# print(slaves)
	# input('any')
	
	# results = test.ud2_rsupd(slave_address=0x01)
	
	
	# print('fixed header:------------------------------')
	# for key in results:
		# if key=='fields': continue
		# print(key, results[key])
	# print('fields:------------------------------------')
	# for field in results['fields']:
		# if test.extensive_mode:
			# print(' '.join(f'{i}:{j}' for i,j in field.items()))
		# else:
			# print(' '.join(f'{j}' for i,j in field.items()))

	# print()
	# print()
	
	# results = test.ud2_rsupd(slave_address=0x02)
	# print('fixed header:------------------------------')
	# for key in results:
		# if key=='fields': continue
		# print(key, results[key])
	# print('fields:------------------------------------')
	# for field in results['fields']:
		# if test.extensive_mode:
			# print(' '.join(f'{i}:{j}' for i,j in field.items()))
		# else:
			# print(' '.join(f'{j}' for i,j in field.items()))
		
	# return 0

if __name__ == '__main__':
	import sys
	sys.exit(main(sys.argv))
