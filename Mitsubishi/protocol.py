import serial
import logging
import re

from . import exceptions
from .monitor_batch import MonitorBatch

class Protocol(serial.Serial):
    STX = b"\x02" #Start of text
    ETX = b'\x03' #End of text
    EOT = b'\x04' #End of transmission
    ENQ = b'\x05' #Enquiry
    ACK = b'\x06' #Acknowledge
    LF  = b'\x0A' #Line Feed
    CL  = b'\x0C' #Clear
    CR  = b'\x0D' #Carrier Return
    NAK = b'\x15' #Not Acknowledge

    register_regex = re.compile('^(?P<type>[A-Z]+)(?P<register>[0-9]+)$')
    register_offset = {} #To be inplemented in child classes

    monitor_batch_config = [
       {'write_address': 0x1400, 'read_address': 0x1790},
       {'write_address': 0x1440, 'read_address': 0x17D0} 
    ]

    def __init__(self, 
                port, 
                baudrate = 9600, 
                bytesize = serial.SEVENBITS, 
                parity = serial.PARITY_EVEN, 
                stopbits = serial.STOPBITS_ONE, 
                timeout = 5, 
                logging_level = logging.INFO):
        super().__init__(port, baudrate, bytesize, parity, stopbits, timeout)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging_level)
        self.monitor_batch = [MonitorBatch(self, **monitor) for monitor in self.monitor_batch_config]
        if not self.handshake():
            raise exceptions.PLCNotAvailable()

    def handshake(self):
        return self.write(self.ENQ, rawCommand=True) == self.ACK

    def write(self, payload, rawCommand = False, flushBefore = True, ignoreChecksum=False):
        if flushBefore:
            self.flushOutput()
            self.flushInput()
        if rawCommand == False:
            payload = self.STX + payload.encode() + self.ETX + self.calculateChecksum(payload).encode()
        elif isinstance(payload, str):
            payload = payload.encode()
        self.logger.debug("< [{}] {} bytes".format(''.join([chr(i) if i > 15 else '.' for i in payload]), len(payload)))
        super().write(payload)
        response = self.read(ignoreChecksum=ignoreChecksum)
        return response

    def _read(self, n=1):
        data = super().read(n)
        data = b''.join([(b & 0x7F).to_bytes(1, 'little') for b in data])
        return data

    def read(self, ignoreChecksum=False):
        #Look for starting character
        data =  self._read(1)
        if data == self.ACK:
            self.logger.debug("> ACK")
            return self.ACK
        elif (data == self.STX):  #message
            char = self._read(1)
            while char != self.ETX and char is not None:
                data += char
                char = self._read(1)
            if char == self.ETX:
                data += char + self._read(2)
                self.logger.debug("> [{}] {} bytes".format(''.join([chr(i) if i > 15 else '.' for i in data]), len(data)))
                message = data[1:-3].decode()
                if data[-2:] != self.calculateChecksum(message).encode():
                    if ignoreChecksum:
                        self.logger.error("Checksum wrong for message {} - Expected {} | Received: {}".format(''.join([chr(i) if i > 15 else '.' for i in data]), self.calculateChecksum(message), data[-2:]))
                    else:
                        raise exceptions.WrongChecksum("Expected: {} | Received: {}".format(self.calculateChecksum(message), data[-2:]))
                return message
            else:
                self.logger.debug("> [{}] {} bytes - Timeout of communication".format(''.join([chr(i) if i > 15 else '.' for i in data]), len(data)))
                raise exceptions.ResponseMalformed()
        elif data == b'':
            self.logger.error("No answer from PLC")
            return None
        else:
            self.logger.error("Received unknown character: 0x{:02X}".format(data[0]))
            return data

    def calculateChecksum(self, payload):
        _sum = 3
        for ch in payload:
            _sum = _sum + ord(ch)
        return "{:02X}".format(_sum & 0xff)

    def getRegisterAddress(self, register, returnSize=False):
        match = self.register_regex.match(register)
        if not match:
            raise ValueError(register)
        data = match.groupdict()
        if data['type'] in self.register_offset.keys():
            address = self.register_offset[data['type']]['offset'] + self.register_offset[data['type']]['size'] * int(data['register'])
            return (address, self.register_offset[data['type']]['size']) if returnSize else address
        else:
            raise exceptions.NotSupportedRegister(register)

    def readFromAddress(self, address, size):
        #<stx> E00 YYYY NN <etx> CC   ==> YYYY = Address (4bytes) NN = number of bytes (2bytes) CC = sum
        request = f'E00{address:04X}{size:02X}'
        return self.write(payload = request)

    def writeToAddress(self, address: int, value: list ):
        #<stx> E10 YYYY NN XXXXXXX<etx> CC   ==> YYYY = Address (4bytes) NN = number of bytes (2bytes) X = data to write CC = sum
        if isinstance(value, int):
            value = [value]
        elif not isinstance(value, list) and not isinstance(value, str):
            raise ValueError("Only integer or list of integer are allowed")
        size = len(value) * 2
        if not isinstance(value, str):
            value = b''.join([int.to_bytes(val, length=2, byteorder='little') for val in value])
            value = binascii.hexlify(value).decode()
        request = f'E10{address:04X}{size:02X}{value}'
        return self.write(payload = request)

    def setBitToAddress(self, address):
        return self.changeBitToAddress(address, 1)

    def clearBitToAddress(self, address):
        return self.changeBitToAddress(address, 0)

    def changeBitToAddress(self, address, state):
        #<stx> E7 addrs <etx>  --> FOR SET
        #<stx> E8 addrs <etx>  --> FOR CLEAR
        payload = "E{}{}".format('7' if state>0 else '8',  self.intToHexString(address)) 
        return self.write(payload)==self.ACK

    def readFromRegister(self, register):
        return self.readFromAddress(*self.getRegisterAddress(register, returnSize=True))

    def writeToRegister(self, register, value):
        return self.writeToAddress(*self.getRegisterAddress(register, False), value)
