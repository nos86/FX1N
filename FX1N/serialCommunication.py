import serial
import logging
import re

import exceptions

class serialCommunication:
    STX = b"\x02" #Start of text
    ETX = b'\x03' #End of text
    EOT = b'\x04' #End of transmission
    ENQ = b'\x05' #Enquiry
    ACK = b'\x06' #Acknowledge
    LF = b'\x0A'  #Line Feed
    CL = b'\x0C'  #Clear
    CR = b'\x0D'  #Carrier Return
    NAK = b'\x15' #Not Acknowledge

    def __init__(self, port, baudrate=9600, bytesize = serial.SEVENBITS, parity = serial.PARITY_EVEN, stopbits = serial.STOPBITS_ONE, timeout=5):
        self.com = serial.Serial(
            port = port
            , baudrate = baudrate
            , bytesize = bytesize
            , parity = parity
            , stopbits = stopbits
            , timeout=timeout
            )
        self.logger = logging.getLogger(self.__class__.__name__)
        self.regex = {'output': re.compile("^(?P<type>Y|M)(?P<pin>[0-9]+)$")}
        self.input = None
        self.output = None

    def readAddress_D(self, address, size=2):
        msg = '0'+"{:04X}".format(address*2+0x1000)+"{:02X}".format(size)
        response = self.com_writedata(payload=msg, response_size=size*2+4)
        return self.extractResponse(response)

    def readInputOutputStatus(self):
        data = self.com_writedata("E00024010",flushBefore=True, response_size=36)
        self.input = self.extractResponse(data)
        data = self.com_writedata("E00018010",flushBefore=True, response_size=36)
        self.output = self.extractResponse(data)
    
    def readAddress_M(self, address):
        pass
    
    def updateStatus(self, address):
        pass
    
    def calculateChecksum(self, payload):
        _sum = 3
        for ch in payload:
            _sum = _sum + ord(ch)
        return "{:02X}".format(_sum & 0xff)

    def handshake(self):
        self.com.write(self.ENQ)
        return self.checkACK()

    def extractResponse(self, response, checkChecksum=True):
        if response[0] != self.STX[0] or response[-3] != self.ETX[0]:
            raise exceptions.ResponseMalformed()
        message = response[1:-3].decode()
        if checkChecksum:
            if response[-2:] != self.calculateChecksum(message).encode():
                raise exceptions.WrongChecksum("Expected: {} | Received: {}".format(self.calculateChecksum(message), response[-2:]))
        return message

    def checkACK(self, response=None):
        if response is None:
            response = self.com.read(1)
        return response == self.ACK

    def com_writedata(self, payload, response_size=0, flushBefore = True, rawCommand = False):
        if flushBefore:
            self.com.flushOutput()
            self.com.flushInput()
        if rawCommand == False:
            payload = self.STX + payload.encode() +self.ETX + self.calculateChecksum(payload).encode()
        elif isinstance(payload, str):
            payload = payload.encode()
        self.com.write(payload)
        self.logger.debug("TX => {}".format(payload))
        if response_size > 0:
            response = self.com.read(response_size)
            self.logger.debug("RX => {}".format(response))
            return response
        else:
            return b''

    def setOutput(self, pin, state):
        if isinstance(pin, str):
            match = self.regex['output'].match(pin.upper())
            if match is None:
                raise exceptions.NotSupportedCommand()
            payload = ('7' if state>0 else '8') +"{:02X}".format(int(match.groupdict()['pin']))+'0'+ ('1' if match.groupdict()['type'] == 'M' else '5') 
            return self.checkACK(self.com_writedata(payload, 1))
        else:
            raise exceptions.NotSupportedCommand()
