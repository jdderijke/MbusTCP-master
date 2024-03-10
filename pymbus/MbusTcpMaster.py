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



import socket
import threading
import time
from enum import Enum
from datetime import datetime, date

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
import logging
_logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(module)s:%(funcName)s - %(message)s')
handler.setFormatter(formatter)
_logger.addHandler(handler)
_logger.setLevel(logging.INFO)



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
	
class Decoder(object):
	def __init__(self):
		pass

	@staticmethod
	def decode_INT8(data_ba):
		return int.from_bytes(data_ba, byteorder='little', signed=False)
		
	@staticmethod
	def decode_INT16(data_ba):
		return int.from_bytes(data_ba, byteorder='little', signed=False)
	
	@staticmethod
	def decode_INT24(data_ba):
		return int.from_bytes(data_ba, byteorder='little', signed=False)
	
	@staticmethod
	def decode_INT32(data_ba):
		return int.from_bytes(data_ba, byteorder='little', signed=False)
	
	@staticmethod
	def decode_FLOAT32(data_ba):
		raise NotImplementedError('decode_FLOAT32')
	
	@staticmethod
	def decode_INT48(self, data_ba):
		raise NotImplementedError('decode_INT48')
	
	@staticmethod
	def decode_INT64(data_ba):
		raise NotImplementedError('decode_INT64')
	
	@staticmethod
	def decode_BCD(data_ba):
		result = ''
		for x in reversed(data_ba):
			result += str(int((x >> 4) & 0x0F)) + str(int(x) & 0x0F)
		return result
	
	@staticmethod
	def decode_type_F(data_ba):
	
		if ((data_ba[0] & 0x80) != 0):					# Time valid ?
			_logger.error('Invalid datetime')
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
	
	
	@staticmethod
	def decode_type_G(data_ba):
		# print(" ".join(format(x, "02x") for x in data_ba))
		if (data_ba[1] & 0x0F) > 12:						# Date valid ?
			_logger.error('Invalid date')
			return ''
		else:
			year = ((data_ba[0] & 0xE0) >> 5) | ((data_ba[1] & 0xF0) >> 1)
			month = data_ba[1] & 0x0F
			day = data_ba[0] & 0x1F
			return str(date(year=year+2000, month=month, day=day))
	  
	
	@staticmethod
	def decode_STRING(data_ba):
		return data_ba.decode('ascii')

	@staticmethod
	def decode_MBUSID(data_ba):
		'''
		Decodes the FIXED DATA HEADER in a VDS structure
		'''
		# gaat ervan uit dat data_ba een bytearray is......
		results = {}
		results['identification'] = Decoder.decode_BCD(data_ba[:4])
		
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
	

Data_field = {
				0b0000:{'length':0, 'decoder':None},
				0b0001:{'length':1, 'decoder':Decoder.decode_INT8},
				0b0010:{'length':2, 'decoder':Decoder.decode_INT16},
				0b0011:{'length':3, 'decoder':Decoder.decode_INT24},
				0b0100:{'length':4, 'decoder':Decoder.decode_INT32},
				0b0101:{'length':4, 'decoder':Decoder.decode_FLOAT32},
				0b0110:{'length':6, 'decoder':Decoder.decode_INT48},
				0b0111:{'length':8, 'decoder':Decoder.decode_INT64},
				
				0b1000:{'length':0, 'decoder':None},
				0b1001:{'length':1, 'decoder':Decoder.decode_BCD},
				0b1010:{'length':2, 'decoder':Decoder.decode_BCD},
				0b1011:{'length':3, 'decoder':Decoder.decode_BCD},
				0b1100:{'length':4, 'decoder':Decoder.decode_BCD},
				0b1101:{'length':4, 'decoder':None},
				0b1110:{'length':6, 'decoder':Decoder.decode_BCD},
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
				'0110110n':{'descr':'Time_point', 'scaling':1, 'unit':lambda x:['date','datetime'][x & 0x01], 'decoder':lambda x:[Decoder.decode_type_G, Decoder.decode_type_F][x & 0x01]},
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
	Connecting = 1
	Connected=2
	DisConnecting = 3
	DisConnected=4
	
class MbusState(Enum):
	Idle=0
	Sending=1
	Receiving=2
	Retrying=3
	

class ConnectionType(Enum):
	TCP = 1
	UDP = 2
	SERIAL = 3
	
	
tcp_buffersize = 1024

class MbusSpecific(object):
	def __init__(self, **kwargs):
		
		pass
		
	def _make_req_ud2(self, slave_address=0x01):
		return bytearray([0x10, 0x5B, slave_address, self._calc_crc([0x5B, slave_address]), 0x16])
		
	def _make_req_ud1(self, slave_address=0x01):
		return bytearray([0x10, 0x5A, slave_address, self._calc_crc([0x5A, slave_address]), 0x16])

	def scan_slaves_primary(self, **kwargs):
		""" 
		usage: slaves = test.scan_slaves_primary([scan_timeout, stop_at])
		
		kwargs:
		scan_timeout: How long to wait for response from an address (float:1.0)
		stop_at: Quit looking for more slaves after this number of detected slaves (int:250)
		
		returns:
		A dictionary with Fixed Data Headers (FDH's) part of the response of the detected slaves, keyed on their primary addresses.
		An FDH contains: Ident. Nr. Manufr. Version Medium AccessNo. Status Signature
		"""
		try:
			if not self.is_connected(): raise Exception('Not connected')
			self.TCPclientSock.settimeout(kwargs.get('scan_timeout', 1.0))
				
			scan_results = dict()
			for addr in range(0,251,1):
				try:
					results = self._ud2_rsupd(addr, header_only=True)
					scan_results[addr]=results
					_logger.info(f'Found device on address {format(addr, "02x")}, ID:{results["identification"]}, manuf:{results["manufacturer"]}, version:{results["version"]}, medium:{results["medium"]}')
					if len(scan_results) >= kwargs.get('stop_at', 250): return scan_results
				except socket.timeout as err:
					_logger.debug(f'No slave detected on address {format(addr, "02x")}, err:{err}')
			return scan_results
			self.TCPclientSock.settimeout(self.timeout)
		except Exception as err:
			_logger.exception(err)
			
		
	def get_all_fields(self, slave_address, **kwargs):
		'''
		usage: result = test.get_all_fields(slave_address, [extensive_mode, scale_results])
		args:
		slave_address: slave address to send request to (int:1)
		
		kwargs:
		extensive_mode: generate extra field information in the 'fields' part of the result (bool:False)
		scale_results: Return scaled values (bool:True)
		
		returns:
		All fields/registers from 1 specific slave address. (only VARIABLE DATA STRUCTURE is supported at this moment)
		returns a dictionary with the FDH information of this slave and a 'fields' key 
		The 'fields' key contains a list of dictionaries (1 per decoded field/register) with: Description, Value, Unit
		'''
		try:
			if not self.is_connected(): raise Exception('Not connected')
			return self._ud2_rsupd(slave_address, **kwargs)
			
		except Exception as err:
			_logger.exception(err)
			

	def _ud2_rsupd(self, slave_address, **kwargs):
		self.send(self._make_req_ud2(slave_address))
		answer = self.recv()
		
		# Control codes for Data Transfer from Slave to Master after Request: [0x08, 0x18, 0x28, 0x38]
		if answer['c'] in [0x08, 0x18, 0x28, 0x38]:				# Normal RSP_UD Data Transfer from Slave to Master after Request
			if answer['ci'] in [0x72, 0x76]:					# Variable Data Structure
				results = self._parseVDS(answer['data'], **kwargs)
				return results
			if answer['ci'] in [0x70]:							# RSP_UD Application error response
				raise NotImplementedError('RSP_UD Application error response')




	def _parseVDS(self, data_ba, **kwargs):
		'''
		Parse a variable data structure from the bytearray
		'''
		try:
			results=dict()
			if kwargs.get('extensive_mode', False): results['response'] = data_ba
			
			# eerste 12 bytes zijn ALTIJD de FIXED DATA HEADER (FDH) 
			results.update(Decoder.decode_MBUSID(data_ba[:12]))
			# decode all fields untill no more fields are found
			if kwargs.get('header_only', False): return results
			
			index = 12
			
			results['fields']=[]
			
			while index < len(data_ba):
				# result, skip  = self.__field_VDS_decoder(msgbytes[index:])
				# if result: results.update(result)
				# index += skip
				'''
				Decode the next field from the data_ba byte array
				'''
				DR_start = index
				dif_info, index = self._VDSdif_decoder(data_ba, index)
				function, var_length, _, _, storage_nr, tariff = dif_info
				
				vif_info, index = self._VDSvif_decoder(data_ba, dif_info, index)
				descr, scaling, unit, nr_bytes, decoder = vif_info
				
				data_start = index
				
				value = decoder(data_ba[index:index + nr_bytes])
				_logger.debug(f'decoded databytes on index {index} for {function}_{descr}_{storage_nr}, decoder: {decoder}, result: {value}')
				index += nr_bytes
				
				field = dict(	descr=f'{function}_{descr} {storage_nr}:{tariff}', 
								value=value*scaling if kwargs.get('scale_results', True) else value, 
								unit=unit)
				if kwargs.get('extensive_mode', False): field.update(dict(	
															function=function,
															storage=storage_nr,
															tariff=tariff,
															orig_value=value
															scaling=scaling, 
															DR_startindex=DR_start, 
															DR=data_ba[VDS_start:index], 
															decoder=decoder)
													)
				results['fields'].append(field)
					
				_logger.debug(f'VDS was {" ".join(format(x, "02x") for x in data_ba[VDS_start:index])}')
				_logger.debug('')
				_logger.debug('')
				# print ()
			return results
		except Exception as err:
			_logger.error(err)

	def _VDSdif_decoder(self, data_ba, index=0):
		tariff = 0
		
		dif_start = index
		dif = int(data_ba[index])										# get the first DIF
		index += 1
		
		dif_extension = (dif > 0x7F)
		storage_nr = (dif >> 6) & 0x01									# store the LSB of the storage_nr
		
		function = Function_field((dif >> 4) & 0x03).name
		
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
			
		_logger.debug(f'DIF={" ".join(format(x, "02x") for x in data_ba[dif_start:index])}, function={function}, storage_nr={storage_nr}, tariff={tariff}, var_length={var_length}, nr_bytes={nr_bytes}, decoder={decoder}')
	
		return (function, var_length, nr_bytes, decoder, storage_nr, tariff), index
		
	def _VDSvif_decoder(self, data_ba, dif_info, index=0):
		
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
			
			descr, scaling, unit, nwdecoder = self._get_value_information(vif_field_secondary, vif, max_shift=4)
			if nwdecoder: decoder = nwdecoder			# If needed.. overrule the DIF defined decoder
			
		else:
	
			descr, scaling, unit, nwdecoder = self._get_value_information(vif_field, vif, max_shift=3)
			# There could be more additional VIFE's, to extend the description of change the scaling or replace the unit
			while (vif > 0x7F):
				vif = int(data_ba[index])							# get the next VIFE
				index += 1
				xtra_descr, nw_scaling, nw_unit, nwdecoder = self._get_value_information(vif_field_secondary, vif, max_shift=4)
				if xtra_descr: 	descr += ', ' + xtra_descr
				if nw_scaling: 	scaling = nw_scaling * scaling
				if nw_unit: 	unit = nw_unit
				
			if nwdecoder: decoder = nwdecoder			# If needed.. overrule the DIF defined decoder
				
				
		_logger.debug(f'VIF={" ".join(format(x, "02x") for x in data_ba[vif_start:index])}, descr = {descr}, scaling = {scaling}, unit = {unit}')
			
		return (descr, scaling, unit, nr_bytes, decoder), index
		
	def _get_value_information(self, table, vif, max_shift=3):
		'''
		Retrieved the data definition from a dictionary (table) based on a lookup key (vif) in bitwise string representation
		First the full bitwise string of the lookup key (vif) is used as key, if no match is found then the lookup string is replaced 
		from the right bit with the letter n and again a match is searched....etc until lookup has been shifted right by max_shift bits OR 
		a match was found
		So a vif of '01011100' would be used a key to search for, if no match '0101110n' is used, if still no match '010111nn' is used etc.
		The found key contains a descr(iption), a scaling and a unit entry. with optionally a decoder entry, these entries are returned
		'''
		shift = 0
		keystr = format(vif, "08b")
		keystr = '0' + keystr[1:]									# Always reset the MSB of the vif in the searchkey
		data_def = None
		while not data_def and shift <= max_shift:
			for teller in range(shift): keystr = keystr[:len(keystr)-shift] + 'n' * shift
			data_def = table.get(keystr, None) 
			
			if not data_def:
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
			_logger.debug(f'decoder_overrule = {decoder_overrule}')
		else:
			raise NotImplementedError(f'VIF not found, VIF = {format(vif, "02x")}')
			
		return (descr, scaling, unit, decoder_overrule)



			

class BaseMbusMaster(MbusSpecific):
	"""
	Inteface for an Mbus synchronous client. Defined here are all the
	methods for performing the related request methods.  Derived classes
	simply need to implement the transport methods
	"""
	def __init__(self, **kwargs):
		""" Initialize a client instance
		"""
		# Optional args with their defaults
		self._debug = kwargs.pop('_debug', False)
		self.conn_type = kwargs.pop('conn_type', None)
		self.timeout = kwargs.pop('timeout', 20)
		self.maxretries = kwargs.pop('maxretries', 3)
		
		# pass on the rest of the kwargs to the base classes
		super().__init__(**kwargs)

		# other properties and defaults
		self.conn_state = ConnState.DisConnected
		self.bus_state = MbusState.Idle
		self.buffersize = 4096


		

	def connect(self):
		""" Connect to the mbus remote host, 
		returns: True if connection succeeded, False otherwise
		"""
		raise NotImplementedException("Method not implemented by derived class")

	def close(self):
		""" Closes the underlying socket/serial connection
		"""
		raise NotImplementedException("close() not implemented by {}".format(self.__str__()))

	def is_connected(self):
		"""
		Check whether the underlying socket/serial is open or not.
		:returns: True if socket/serial is open, False otherwise
		"""
		raise NotImplementedException("is_socket_open() not implemented by {}".format(self.__str__()))

	def send(self, request):
		""" Sends data to the subclass _send routine
		:param request: The encoded request to send
		:return: The number of bytes written
		"""
		try:
			self.mbus_state = MbusState.Sending
			for attempt in range(self.maxretries):
				try:
					sndbytes = self._send(request)
					return sndbytes
				except Exception as err:
					_logger.error(err)
					self.mbus_state = MbusState.Retrying
			return 0
		except:
			pass
		finally:
			self.mbus_state = MbusState.Idle

	def _send(self, request):
		""" Sends data on the underlying socket

		:param request: The encoded request to send
		:return: The number of bytes written
		"""
		raise NotImplementedException("Method not implemented by derived class")

	def recv(self, size=tcp_buffersize):
		""" Reads data from the underlying subclass _recv routine
		:param size: The buffer size or number of bytes to read
		:return: The bytes read
		"""
		data = None
		# TODO: Dont know how to implement the maxretries mechanism on the receiver side......
		self.mbus_state = MbusState.Receiving
		data = self._recv(size)
		self.mbus_state = MbusState.Idle
		
		# check if valid start of telegram (data[0] in [0x10, 0xE5, 0x68])
		if data[0] == 0x68:
			l, c, a, ci = int(data[1]), data[4], data[5], data[6]
			# check CRC
			crc = self._calc_crc(data[4:-2])
			if crc != data[-2]:
				raise Exception('Checksum error')
			if l != len(data[4:-2]):
				raise Exception('length field error')
			return {'l':l, 'c':c, 'ci':ci, 'a':a, 'data':data[7:-2]}
		else:
			raise Exception(f'Invalid start of telegram byte {format(data[0], "2x")}')

	def _recv(self, size):
		""" Reads data from the underlying descriptor

		:param size: The number of bytes to read
		:return: The bytes read
		"""
		raise NotImplementedException("Method not implemented by derived class")

	def _calc_crc(self, data_ba):
		""" Calculates the CRC byte by adding all bytes and apply modulo 256 on the result
		
		:return: CRC as integer
		"""
		tmpsum = 0x0000         # force an Unsigned INT16 into tmpsum
		for i in range(len(data_ba)):
			tmpsum = tmpsum + data_ba[i]
		# % is the modulo operator, it results in the remainder after dividing the left through the right variable, i.e. 7 % 2 = 1
		tmpsum =tmpsum % 256 
		return tmpsum


	# # ----------------------------------------------------------------------- #
	# # The magic methods
	# # ----------------------------------------------------------------------- #
	# def __enter__(self):
		# """ Implement the client with enter block

		# :returns: The current instance of the client
		# """
		# if not self.connect():
			# raise ConnectionException("Failed to connect[%s]" % (self.__str__()))
		# return self

	# def __exit__(self, klass, value, traceback):
		# """ Implement the client with exit block """
		# self.close()

	# def idle_time(self):
		# """
		# Bus Idle Time to initiate next transaction
		# :return: time stamp
		# """
		# if self.last_frame_end is None or self.silent_interval is None:
			# return 0
		# return self.last_frame_end + self.silent_interval

	# def debug_enabled(self):
		# """
		# Returns a boolean indicating if debug is enabled.
		# """
		# return self._debug

	# def set_debug(self, debug):
		# """
		# Sets the current debug flag.
		# """
		# self._debug = debug

	# def trace(self, writeable):
		# if writeable:
			# self.set_debug(True)
		# self._debugfd = writeable

	# def _dump(self, data, direction):
		# fd = self._debugfd if self._debugfd else sys.stdout
		# try:
			# fd.write(hexlify_packets(data))
		# except Exception as e:
			# _logger.debug(hexlify_packets(data))
			# _logger.exception(e)


	# def __str__(self):
		# """ Builds a string representation of the connection

		# :returns: The string representation
		# """
		# return "Null Transport"

class MbusTcpMaster(BaseMbusMaster):
	def __repr__(self):
		if self.conn_type == ConnectionType.TCP:
			return f"{self.name}({self.host}:{self.port}), {self.conn_type}: timeout={self.timeout}, retries={self.maxretries}"
		else:
			return f"<{self.__class__.__module__}.{self.__class__.__name__} object at {hex(id(self))}>"

	def __init__(self, host, port, **kwargs):
		# Mandatory args
		self.host = host
		self.port = port
		
		# Optional args with their defaults
		self.name = kwargs.pop('name', '')
		self.auto_connect = kwargs.pop('auto_connect', True)
		
		# pass on the rest of the kwargs to the base classes
		super().__init__(**kwargs)

		# Add non arg properties and their defaults
		self.TCPclientSock = None
		
		# Overrule already defined property values
		self.conn_type = ConnectionType.TCP
		
		if self.auto_connect: self.connect()
		
	def connect(self):
		if not self.conn_type == ConnectionType.TCP:
			raise NotImplementedError(f'Connection type {self.conn_type} not implemented in {self}')
			
		self.conn_state = ConnState.Connecting
		self.TCPclientSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.TCPclientSock.settimeout(self.timeout)
		
		for tries in range(self.maxretries):
			try:
				self.TCPclientSock.connect((self.host, self.port))
				self.conn_state = ConnState.Connected
				self.mbus_state = MbusState.Idle
				_logger.info(f'{self}')
				break
			except Exception as err:
				_logger.error (f'{self.name}-- Problem connecting {self.conn_type}-{self.host}:{self.port} attempt {tries+1}, {err}')
				time.sleep(0.5)
		if not self.is_connected(): 
			_logger.error('disconnecting')
			self.close()
			return False
		else:
			_logger.info('Connected')
			return True
						
	def close(self):
		if self.is_connected(): 
			_logger.debug('I am connected.... now disconnecting')
			self.TCPclientSock.close()
			
		self.TCPclientSock = None
		self.conn_state = ConnState.DisConnected
		self.bus_state = MbusState.Idle
				
						
	def is_connected(self):
		if not hasattr(self, 'TCPclientSock'): 
			return False
		if self.TCPclientSock is None: 
			return False
		else:
			try:
				self.TCPclientSock.send(bytearray([]))
				return True
			except Exception as err:
				# print (err)
				return False
			
	def _recv(self, size):
		data = self.TCPclientSock.recv(size)
		return data
		
	def _send(self, sndmsg):
		""" Sends data on the underlying socket

		:param sndmsg: The encoded request to send
		:return: The number of bytes send
		"""
		sndbytes = self.TCPclientSock.send(sndmsg)
		return sndbytes

		
	
		






def main(args):
	raise Exception ('Not an executable script...')

if __name__ == '__main__':
	import sys
	sys.exit(main(sys.argv))
