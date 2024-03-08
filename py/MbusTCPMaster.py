#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  New_Mbus_Interface.py
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
import os
import __main__
if __name__ == "__main__":
	 __main__.logfilename = os.path.basename(__file__).replace("py", "log")
	 __main__.backupcount = 1
from LogRoutines import Logger



import socket
import threading
import time
from Conversion_Routines import From_MBUSID
from enum import Enum
from datetime import datetime, date

field_names = {0x01:[], 0x02:[]}



class Medium_field(Enum):
	Other = 0x00
	Oil = 0x01
	Electricity = 0x02
	Gas = 0x03
	Heat = 0x04
	Steam = 0x05
	Hot_water = 0x06
	Water = 0x07
	Heat_cost_alloc = 0x08
	Compressed_air = 0x09
	Cooling_outlet = 0x0A
	Cooling_inlet = 0x0B
	Heat_inlet = 0x0C
	Heat_cooling_load_meter = 0x0D
	Bus = 0x0E
	Unknown_medium = 0x0F
	Cold_water = 0x16
	Dual_water = 0x17
	Pressure = 0x18
	AD_converter = 0x19

class Status_field(Enum):
	'''
	Decribes the lowest 2 bits in the status field of the VDS
	'''
	No_error = 0
	Application_busy = 1
	Any_application_error = 2
	Reserved = 3

class Function_field(Enum):
	'''
	Describes the function bits (6 and 5) in the first DIF
	'''
	Act = 0b00
	Min = 0b10
	Max = 0b01
	Err = 0b11
	
	
def decode_INT8(data_ba):
	return int.from_bytes(data_ba, byteorder='little', signed=False)
	
def decode_INT16(data_ba):
	return int.from_bytes(data_ba, byteorder='little', signed=False)

def decode_INT24(data_ba):
	return int.from_bytes(data_ba, byteorder='little', signed=False)

def decode_INT32(data_ba):
	return int.from_bytes(data_ba, byteorder='little', signed=False)

def decode_FLOAT32():
	raise NotImplementedError('decode_FLOAT32')

def decode_INT48():
	raise NotImplementedError('decode_INT48')

def decode_INT64():
	raise NotImplementedError('decode_INT64')

def decode_BCD(data_ba):
	result = ''
	for x in reversed(data_ba):
		result += str(int((x >> 4) & 0x0F)) + str(int(x) & 0x0F)
	return result

def decode_type_F(data_ba):

	if ((data_ba[0] & 0x80) != 0):					# Time valid ?
		Logger.error('Invalid datetime')
		return ''
	else:
		year = ((data_ba[2] & 0xE0) >> 5) | ((data_ba[3] & 0xF0) >> 1)
		month = data_ba[3] & 0x0F
		day = data_ba[2] & 0x1F
		hour = data_ba[1] & 0x1F
		minute = data_ba[0] & 0x3F
		# print (f'year={year+2000}, month={month}, day={day}, hour={hour}, minute={minute}')
		return str(datetime(year=year+2000, month=month, day=day, hour=hour, minute=minute))
		# (data[1] & 0x80) is 1 of 0 >> daylight saving time


def decode_type_G(data_ba):
	# print(" ".join(format(x, "02x") for x in data_ba))
	if (data_ba[1] & 0x0F) > 12:						# Date valid ?
		Logger.error('Invalid date')
		return ''
	else:
		year = ((data_ba[0] & 0xE0) >> 5) | ((data_ba[1] & 0xF0) >> 1)
		month = data_ba[1] & 0x0F
		day = data_ba[0] & 0x1F
		return str(date(year=year+2000, month=month, day=day))
  

def decode_STRING(data_ba):
	return data_ba.decode('ascii')

Data_field = {
				0b0000:{'length':0, 'decoder':None},
				0b0001:{'length':1, 'decoder':decode_INT8},
				0b0010:{'length':2, 'decoder':decode_INT16},
				0b0011:{'length':3, 'decoder':decode_INT24},
				0b0100:{'length':4, 'decoder':decode_INT32},
				0b0101:{'length':4, 'decoder':decode_FLOAT32},
				0b0110:{'length':6, 'decoder':decode_INT48},
				0b0111:{'length':8, 'decoder':decode_INT64},
				
				0b1000:{'length':0, 'decoder':None},
				0b1001:{'length':1, 'decoder':decode_BCD},
				0b1010:{'length':2, 'decoder':decode_BCD},
				0b1011:{'length':3, 'decoder':decode_BCD},
				0b1100:{'length':4, 'decoder':decode_BCD},
				0b1101:{'length':4, 'decoder':None},
				0b1110:{'length':6, 'decoder':decode_BCD},
				0b1111:{'length':8, 'decoder':None}
				}
	
# The VIF field contains all data specifications...
vif_field = {
				# Energy
				'00000nnn':{'descr':'Energy', 'scaling':lambda x: 10**((x & 0x07) - 3), 'unit':'Wh'},
				'00001nnn':{'descr':'Energy', 'scaling':lambda x: 10**(x & 0x07), 'unit':'J'},
				# Volumes and Mass
				'00010nnn':{'descr':'Volume', 'scaling':lambda x: 10**((x & 0x07) - 6), 'unit':'m3'},
				'00011nnn':{'descr':'Mass', 'scaling':lambda x: 10**((x & 0x07) - 3), 'unit':'kg'},
				# times
				'001000nn':{'descr':'On_time', 'scaling':1, 'unit':lambda x: ['seconds','minutes','hours','days'][x & 0x03]},
				'001001nn':{'descr':'Operating_time', 'scaling':1, 'unit':lambda x: ['seconds','minutes','hours','days'][x & 0x03]},
				# powers
				'00101nnn':{'descr':'Power', 'scaling':lambda x: 10**((x & 0x07) - 3), 'unit':'W'},
				'00110nnn':{'descr':'Power', 'scaling':lambda x: 10**(x & 0x07), 'unit':'J/h'},
				# flows
				'00111nnn':{'descr':'Volume_flow', 'scaling':lambda x: 10**((x & 0x07) - 6), 'unit':'m3/h'},
				'01000nnn':{'descr':'Volume_flow', 'scaling':lambda x: 10**((x & 0x07) - 7), 'unit':'m3/min'},
				'01001nnn':{'descr':'Volume_flow', 'scaling':lambda x: 10**((x & 0x07) - 9), 'unit':'m3/s'},
				'01010nnn':{'descr':'Mass_flow', 'scaling':lambda x: 10**((x & 0x07) - 3), 'unit':'kg/h'},
				# temperatures
				'010110nn':{'descr':'Flow_temperature', 'scaling':lambda x:10**((x & 0x03) - 3), 'unit':'C'},
				'010111nn':{'descr':'Return_temperature', 'scaling':lambda x:10**((x & 0x03) - 3), 'unit':'C'},
				'011000nn':{'descr':'Temperature_diff', 'scaling':lambda x:10**((x & 0x03) - 3), 'unit':'C'},
				'011001nn':{'descr':'External_temperature', 'scaling':lambda x:10**((x & 0x03) - 3), 'unit':'C'},
				# pressure
				'011010nn':{'descr':'Pressure', 'scaling':lambda x:10**((x & 0x03) - 3), 'unit':'bar'},
				# others
				'0110110n':{'descr':'Time_point', 'scaling':1, 'unit':lambda x:['date','datetime'][x & 0x01], 'decoder':lambda x:[decode_type_G, decode_type_F][x & 0x01]},
				'01101110':{'descr':'Units_for_HCA.', 'scaling':1, 'unit':''},
				'01101111':{'descr':'Reserved.', 'scaling':1, 'unit':''},
				'011100nn':{'descr':'Averaging_duration.', 'scaling':1, 'unit':lambda x: ['seconds','minutes','hours','days'][x & 0x03]},
				'011101nn':{'descr':'Actuality_duration.', 'scaling':1, 'unit':lambda x: ['seconds','minutes','hours','days'][x & 0x03]},
				'01111000':{'descr':'Fabrication_no.', 'scaling':1, 'unit':''},
				'01111001':{'descr':'Enhanced', 'scaling':1, 'unit':''},
				'01111010':{'descr':'Bus_address', 'scaling':1, 'unit':''}
			}
	
vif_field_secondary = {
				# Currency units
				'000000nn':{'descr':'Credit in local currency', 'scaling':lambda x:10**((x & 0x03) - 3), 'unit':'Eur'},
				'000001nn':{'descr':'Debit in local currency', 'scaling':lambda x:10**((x & 0x03) - 3), 'unit':'Eur'},
				# Enhanced Identification
				'00001000':{'descr':'Transmission count', 'scaling':1, 'unit':'#'},
				'00001001':{'descr':'Medium', 'scaling':1, 'unit':''},
				'00001010':{'descr':'Manufacturer', 'scaling':1, 'unit':''},
				'00001011':{'descr':'Parameter set identification', 'scaling':1, 'unit':''},
				'00001100':{'descr':'Model version', 'scaling':1, 'unit':''},
				'00001101':{'descr':'Hardware version #', 'scaling':1, 'unit':''},
				'00001110':{'descr':'Firmware version #', 'scaling':1, 'unit':''},
				'00001111':{'descr':'Software version #', 'scaling':1, 'unit':''},
				# TC294 implementation
				'00010000':{'descr':'Customer location', 'scaling':1, 'unit':''},
				'00010001':{'descr':'Customer', 'scaling':1, 'unit':''},
				'00010010':{'descr':'Access code user', 'scaling':1, 'unit':''},
				'00010011':{'descr':'Access code operator', 'scaling':1, 'unit':''},
				'00010100':{'descr':'Access code system operator', 'scaling':1, 'unit':''},
				'00010101':{'descr':'Access code developer', 'scaling':1, 'unit':''},
				'00010110':{'descr':'Password', 'scaling':1, 'unit':''},
				'00010111':{'descr':'Error flags', 'scaling':1, 'unit':'binary'},
				'00011000':{'descr':'Error mask', 'scaling':1, 'unit':'binary'},
				'00011001':{'descr':'Reserved', 'scaling':1, 'unit':''},
				# device info
				'00011010':{'descr':'Digital output', 'scaling':1, 'unit':'binary'},
				'00011011':{'descr':'Digital input', 'scaling':1, 'unit':'binary'},
				'00011100':{'descr':'Baudrate', 'scaling':1, 'unit':'Baud'},
				'00011101':{'descr':'Response delay time', 'scaling':1, 'unit':'bittimes'},
				
				'00011110':{'descr':'Retry', 'scaling':1, 'unit':''},
				'00011111':{'descr':'Reserved', 'scaling':1, 'unit':''},
				
				# Enhanced storage management
				'00100000':{'descr':'First storage #', 'scaling':1, 'unit':''},
				'00100001':{'descr':'Last storage #', 'scaling':1, 'unit':''},
				'00100010':{'descr':'Size of storage block', 'scaling':1, 'unit':''},
				'00100011':{'descr':'Reserved', 'scaling':1, 'unit':''},
				'001001nn':{'descr':'Storage interval', 'scaling':1, 'unit':lambda x:['s','min','hr','days'][x & 0x03]},
				'00101000':{'descr':'Storage interval months', 'scaling':1, 'unit':'months'},
				'00101001':{'descr':'Storage interval years', 'scaling':1, 'unit':'years'},
				'00101010':{'descr':'Reserved', 'scaling':1, 'unit':''},
				'00101011':{'descr':'Reserved', 'scaling':1, 'unit':''},
				'001011nn':{'descr':'Duration since last readout', 'scaling':1, 'unit':lambda x:['s','min','hr','days'][x & 0x03]},
				
				# Enhanced tariff management
				'00110000':{'descr':'Startdate of tariff', 'scaling':1, 'unit':'datetime'},
				'001100nn':{'descr':'Duration of tariff', 'scaling':1, 'unit':lambda x:['s','min','hr','days'][x & 0x03]},
				'001101nn':{'descr':'Tariff period', 'scaling':1, 'unit':lambda x:['s','min','hr','days'][x & 0x03]},
				'00111000':{'descr':'Tariff period months', 'scaling':1, 'unit':'months'},
				'00111001':{'descr':'Tariff period years', 'scaling':1, 'unit':'years'},
				'00111010':{'descr':'No dimension', 'scaling':1, 'unit':''},
				'00111011':{'descr':'Reserved', 'scaling':1, 'unit':''},
				'001111nn':{'descr':'Reserved', 'scaling':1, 'unit':''},
				# Electrical units
				'0100nnnn':{'descr':'', 'scaling':lambda x:10**((x&0x0F) - 9), 'unit':'V'},
				'0101nnnn':{'descr':'', 'scaling':lambda x:10**((x&0x0F) - 12), 'unit':'A'},

				'01100000':{'descr':'Reset counter', 'scaling':1, 'unit':''},
				'01100001':{'descr':'Cumulation counter', 'scaling':1, 'unit':''},
				'01100010':{'descr':'Control signal', 'scaling':1, 'unit':''},
				'01100011':{'descr':'Day of week', 'scaling':1, 'unit':''},
				'01100100':{'descr':'Week number', 'scaling':1, 'unit':''},
				'01100101':{'descr':'Timepoint of daychange', 'scaling':1, 'unit':''},
				'01100110':{'descr':'State of parameter activation', 'scaling':1, 'unit':''},
				'01100111':{'descr':'Special supplier info', 'scaling':1, 'unit':''},

				'011010nn':{'descr':'Duration since last cumulation', 'scaling':1, 'unit':lambda x:['hr','days','months','years'][x & 0x03]},
				'011011nn':{'descr':'Operating time battery', 'scaling':1, 'unit':lambda x:['hr','days','months','years'][x & 0x03]},
				'01110000':{'descr':'Datetime battery change', 'scaling':1, 'unit':'datetime'},
				'0111000n':{'descr':'Reserved', 'scaling':1, 'unit':''}

						}


class ConnState(Enum):
	Connecting=1
	Connected=2
	DisConnecting=3
	DisConnected=4

class ConnectionType(Enum):
	TCP = 1
	UDP = 2
	SERIAL = 3


class MbusInterface(object):
	def __repr__(self):
		if self.conn_type == ConnectionType.TCP:
			return f"{self.name}({self.host}:{self.port}), {self.conn_type}: timeout={self.timeout}, retries={self.maxretries}"
		else:
			return f"<{self.__class__.__module__}.{self.__class__.__name__} object at {hex(id(self))}>"

	def __init__(self, host, port, **kwargs):
		# Non optional
		self.host = host
		self.port = port
		# Optional
		self.name = 'test'
		self.timeout = 20
		self.maxretries = 3
		self.conn_type = ConnectionType.TCP
		self.extensive_mode = False
		self.scale_results = True
		self.auto_connect = True

		self.connstate = ConnState.DisConnected
		
		for k,v in kwargs.items(): setattr(self, k, v)
		if self.auto_connect: self.connect()
		
	def connect(self):
		if self.conn_type in [ConnectionType.TCP]:
			self.connstate = ConnState.Connecting
			self.TCPclientSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self.TCPclientSock.settimeout(self.timeout)
			
			for tries in range(self.maxretries):
				try:
					self.TCPclientSock.connect((self.host, self.port))
					self.connstate = ConnState.Connected
					Logger.info(f'{self}')
					break
				except Exception as err:
					Logger.error (f'{self.name}-- Problem connecting {self.conn_type}-{self.host}:{self.port} attempt {tries+1}, {err}')
					time.sleep(0.5)
			if not self.connected(): 
				print('disconnecting')
				self.disconnect()
				
						
	def disconnect(self):
		if self.conn_type in [ConnectionType.TCP]:
			if self.connected():
				self.TCPclientSock.close()
			self.TCPclientSock = None
			self.connstate = ConnState.DisConnected
				
						
	def connected(self):
		if not hasattr(self, 'TCPclientSock'): 
			return False
		if self.TCPclientSock is None: 
			return False
		else:
			try:
				self.TCPclientSock.send(bytearray([]))
				return True
			except Exception as err:
				print (err)
				return False
			
		
	def __req_ud2(self, slave_address=0x01):
		return bytearray([0x10, 0x5B, slave_address, self.__calc_crc([0x5B, slave_address]), 0x16])
		
	def __req_ud1(self, slave_address=0x01):
		return bytearray([0x10, 0x5A, slave_address, self.__calc_crc([0x5A, slave_address]), 0x16])
		
		
	def get_RSPUD(self, slave_address):
		# print (self.__req_ud2(slave_address))
		# print (" ".join(format(x, "02x") for x in self.__req_ud2(slave_address)))
		# input ('any')
			
		self.__send(self.__req_ud2(slave_address))
		answer = self.__recv()
		
		# print (" ".join(format(x, "02x") for x in answer['data']))
		# input ('any')
		
		# Control codes for Data Transfer from Slave to Master after Request: [0x08, 0x18, 0x28, 0x38]
		if answer['c'] in [0x08, 0x18, 0x28, 0x38]:				# Normal RSP_UD Data Transfer from Slave to Master after Request
			if answer['ci'] in [0x72, 0x76]:					# Variable Data Structure
				results = self.__parseVDS(answer['data'])
				return results
			if answer['ci'] in [0x70]:							# RSP_UD Application error response
				raise NotImplementedError('RSP_UD Application error response')
				
	def __recv(self):
		TCP_BUFFER_SIZE = 1024
		if not self.connected(): raise Exception('Not connected')
		
		if self.conn_type == ConnectionType.TCP: 
			self.TCPclientSock.setblocking(True)
			data = self.TCPclientSock.recv(TCP_BUFFER_SIZE)
		else:
			raise NotImplementedError(self.conn_type)
		
		
		if data[0] in [0x10, 0xE5, 0x68]:
			if data[0] == 0x68:
				l = int(data[1])
				c = data[4]
				a = data[5]
				ci = data[6]
				
				# check CRC
				crc = self.__calc_crc(data[4:-2])
				if crc != data[-2]:
					raise Exception('Checksum error')
				if l != len(data[4:-2]):
					raise Exception('length field error')
				return {'l':l, 'c':c, 'ci':ci, 'a':a, 'data':data[7:-2]}
				
	
	def __parseVDS(self, data_ba):
		'''
		Parse a variable data structure from the bytearray
		'''
		results=dict()
		# eerste 12 bytes zijn ALTIJD de FIXED DATA HEADER (FDH) 
		results.update(self.__MBUSID_VDS_decoder(data_ba[:12]))
		# decode all fields untill no more fields are found
		index = 12
		results['fields']=[]
		
		while index < len(data_ba):
			# result, skip  = self.__field_VDS_decoder(msgbytes[index:])
			# if result: results.update(result)
			# index += skip
			'''
			Decode the next field from the data_ba byte array
			'''
			VDS_start = index
			dif_info, index = self.__VDSdif_decoder(data_ba, index)
			function, var_length, _, _, storage_nr, tariff = dif_info
			
			vif_info, index = self.__VDSvif_decoder(data_ba, dif_info, index)
			descr, scaling, unit, nr_bytes, decoder = vif_info
			
			data_start = index
			value = decoder(data_ba[index:index + nr_bytes])
			
			Logger.debug(f'decoded databytes on index {index} for {function}_{descr}_{storage_nr}, decoder: {decoder}, result: {value}')
			index += nr_bytes
			
			field = dict(	descr=f'{function}_{descr} {storage_nr}:{tariff}', 
							value=value*scaling if self.scale_results else value, 
							unit=unit)
			if self.extensive_mode: field.update(dict(	scaling=scaling, 
														data_start=data_start, 
														vds=data_ba[VDS_start:index], 
														decoder=decoder)
												)
			results['fields'].append(field)
				
			Logger.debug(f'VDS was {" ".join(format(x, "02x") for x in data_ba[VDS_start:index])}')
			Logger.debug('')
			Logger.debug('')
			# print ()
		return results
		
			
		
	def __send(self, sndmsg):
		if not self.connected(): raise Exception('Not connected')
		if self.conn_type == ConnectionType.TCP:
			self.TCPclientSock.send(sndmsg)
		else:
			Logger.error(f'Not implemented error {self.conn_type}')
			raise NotImplementedError(self.conn_type)

		
	def __VDSdif_decoder(self, data_ba, index=0):
		tariff = 0
		
		dif_start = index
		dif = int(data_ba[index])	# get the first DIF
		index += 1
		
		dif_extension = (dif > 0x7F)
		storage_nr = (dif >> 6) & 0x01									# store the LSB of the storage_nr
		
		# print(f'dif = {format(dif, "8b")}, function bits are {format((dif >> 4) & 0x03, "2b")}')
		function = Function_field((dif >> 4) & 0x03).name
		# print(function)
		
		if (dif & 0x0F) == 0b1101:
			# In this case the length is given by the first databyte after the DRH (header), so the first real databyte (LVAR)
			nr_bytes = None
			decoder = None
			var_length = True
		else:
			nr_bytes = Data_field[dif & 0x0F]['length']
			decoder = Data_field[dif & 0x0F]['decoder']
			var_length = False
			
		# So far storage nummer is 0 or 1 and tariff is 0 (default), via extended DIF fields more storage numbers and tariffs can be specified 
		shift_store = 1
		shift_tariff = 0 
		while dif_extension:
			dife = int(data_ba[index])										# get the next extended DIF (dife)
			index += 1
			dif_extension = (dife > 0x7F)
			
			# get the new storage number by left shifting DIFE and adding bit 6 from DIF as LSB
			storage_nr = ((dife & 0x0F) << shift_store) | storage_nr
			tariff = ((dife >> 4) & 0x03) << shift_tariff | tariff
			shift_store += 4
			shift_tariff += 2
			
		Logger.debug(f'DIF={" ".join(format(x, "02x") for x in data_ba[dif_start:index])}, function={function}, storage_nr={storage_nr}, tariff={tariff}, var_length={var_length}, nr_bytes={nr_bytes}, decoder={decoder}')
	
		return (function, var_length, nr_bytes, decoder, storage_nr, tariff), index
		
	def __VDSvif_decoder(self, data_ba, dif_info, index=0):
		
		function, var_length, nr_bytes, decoder, storage_nr, tariff = dif_info
		result = {}
		
		vif_start = index
		vif = int(data_ba[index])	# get the first VIF
		index += 1
		
		if vif in [0x7E, 0xFE]:
			raise NotImplementedError('vif in [0x7E, 0xFE]')
		elif vif in [0x7F, 0xFF]:
			raise NotImplementedError('vif in [0x7F, 0xFF]')
		elif vif in [0x7C, 0xFC]:
			# ASCII string, length is given in the first byte of the data (als0 DIF-var_length should be True)
			if not var_length: raise ProtocolError(f'ASCII field, but var_length in DIF not True')
			# no need to look for further VIFE's'
			descr = ''
			scaling = 1
			unit = ''
			lvar = int(data_ba[index])
			index += 1
			value_startindex = index
			
			if 0x00 <= lvar <= 0xBF:
				decoder = decode_STRING
				nr_bytes = int(lvar)
			elif 0xC0 <= lvar <= 0xCF:
				nr_bytes = int(lvar - 0xC0)
				decoder = decode_BCD
			elif 0xD0 <= lvar <= 0xDF:
				nr_bytes = int(lvar - 0xD0)
				decoder = lambda x: '-' + decode_BCD(x)
			elif 0xE0 <= lvar <= 0xEF:
				nr_bytes = int(lvar - 0xE0)
				decoder = lambda x: int.from_bytes(x)
			else:
				raise NotImplementedError(f'LVAR = {format(lvar, "02x")}')
				
			
		elif vif in [0xFD, 0xFB]:
			# he true VIF is given by the next byte and the coding is taken from the table for secondary VIF (chapter 8.4.4). 
			# This extends the available VIF´s by another 256 codes. No need to look for further VIFE's beyond this
			vif = int(data_ba[index])
			index += 1
			
			descr, scaling, unit, nwdecoder = self.__get_value_information(vif_field_secondary, vif, max_shift=4)
			if nwdecoder: decoder = nwdecoder			# If needed.. overrule the DIF defined decoder
			
		else:
	
			descr, scaling, unit, nwdecoder = self.__get_value_information(vif_field, vif, max_shift=3)
			# There could be more additional VIFE's, to extend the description of change the scaling or replace the unit
			while (vif > 0x7F):
				vif = int(data_ba[index])							# get the next VIFE
				index += 1
				xtra_descr, nw_scaling, nw_unit, nwdecoder = self.__get_value_information(vif_field_secondary, vif, max_shift=4)
				if xtra_descr: 	descr += ', ' + xtra_descr
				if nw_scaling: 	scaling = nw_scaling * scaling
				if nw_unit: 	unit = nw_unit
				
			if nwdecoder: decoder = nwdecoder			# If needed.. overrule the DIF defined decoder
				
				
		Logger.debug(f'VIF={" ".join(format(x, "02x") for x in data_ba[vif_start:index])}, descr = {descr}, scaling = {scaling}, unit = {unit}')
			
		return (descr, scaling, unit, nr_bytes, decoder), index
		
	def __get_value_information(self, table, vif, max_shift=3):
		'''
		Retrieved the data definition from a table (dictionary) based on a lookup key
		First the full lookup is used as kay, if no match is found then the lookup is shifted bitwise right 1 bit and
		again a match is searched.... etc until lookup has been shifted right by max_shift bits OR a match was found
		'''
		shift = 0
		keystr = format(vif, "08b")
		keystr = '0' + keystr[1:]									# Always reset the MSB of the vif in the searchkey
		data_def = None
		while not data_def and shift <= max_shift:
			for teller in range(shift): keystr = keystr[:len(keystr)-shift] + 'n' * shift
			# print (f'searchkeystr = {keystr}')
			# input('any key')
			data_def = table.get(keystr, None) 
			
			if not data_def:
				# print('Not Found!!') 
				shift +=1
				
		if data_def:
			descr = data_def['descr'](vif) if callable(data_def['descr']) else data_def['descr']
			scaling = data_def['scaling'](vif) if callable(data_def['scaling']) else data_def['scaling']
			unit = data_def['unit'](vif) if callable(data_def['unit']) else data_def['unit']
			if data_def.get('decoder', None):
				# The VIF can overrule the DIF defined decoder with a new one
				decoder_overrule = data_def['decoder'](vif) if callable(data_def['decoder']) else data_def['decoder']
			else:
				decoder_overrule = None
			Logger.debug(f'decoder_overrule = {decoder_overrule}')
		else:
			raise NotImplementedError(f'VIF not found, VIF = {format(vif, "02x")}')
			
		return (descr, scaling, unit, decoder_overrule)
	
		
	def __MBUSID_VDS_decoder(self, data_ba):
		'''
		Decodes the FIXED DATA HEADER in a VDS structure
		'''
		# gaat ervan uit dat data_ba een bytearray is......
		results = {}
		results['identification'] = decode_BCD(data_ba[:4])
		
		manuf = int.from_bytes(data_ba[4:6],'little')
		letter1 = chr(((manuf >> 10) & 0x001F) + 64)
		letter2 = chr(((manuf >> 5) & 0x001F) + 64)
		letter3 = chr((manuf & 0x001F) + 64)
		manuf_str = letter1 + letter2 + letter3
		results['manufacturer'] = manuf_str
	
		results['version'] = int(data_ba[6])
		
		try:
			results['medium'] = Medium_field(data_ba[7]).name
		except ValueError:
			results['medium'] = 'reserved or unknown'
			
		results['access_number'] = int(data_ba[8])
	
		results['status'] = Status_field(data_ba[9] & 0x03).name
		results['signature_hex'] = ' '.join(format(x, '02x') for x in data_ba[10:12])
		
		return results

	def __calc_crc(self, data_ba):
		tmpsum = 0x0000         # force an Unsigned INT16 into tmpsum
		for i in range(len(data_ba)):
			tmpsum = tmpsum + data_ba[i]
		# % is the modulo operator, it results in the remainder after dividing the left through the right variable, i.e. 7 % 2 = 1
		tmpsum =tmpsum % 256 
		return tmpsum





def main(args):
	test = MbusInterface(host='192.168.178.204', port=10001, extensive_mode=False, scale_results=True, name='Vermogensmeters Twentseweg')
	results = test.get_RSPUD(slave_address=0x01)
	
	
	print('fixed header:------------------------------')
	for key in results:
		if key=='fields': continue
		print(key, results[key])
	print('fields:------------------------------------')
	for field in results['fields']:
		if test.extensive_mode:
			print(' '.join(f'{i}:{j}' for i,j in field.items()))
		else:
			print(' '.join(f'{j}' for i,j in field.items()))

	print()
	print()
	
	results = test.get_RSPUD(slave_address=0x02)
	print('fixed header:------------------------------')
	for key in results:
		if key=='fields': continue
		print(key, results[key])
	print('fields:------------------------------------')
	for field in results['fields']:
		if test.extensive_mode:
			print(' '.join(f'{i}:{j}' for i,j in field.items()))
		else:
			print(' '.join(f'{j}' for i,j in field.items()))
		
	return 0

if __name__ == '__main__':
	import sys
	sys.exit(main(sys.argv))
