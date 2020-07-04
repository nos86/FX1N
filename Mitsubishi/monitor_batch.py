from . import utils
import logging
import math

class MonitorBatch:
    def __init__(self, serial, write_address: int = 0x1400, read_address: int = 0x1790):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.write_address = write_address
        self.read_address = read_address
        self.serial = serial
        self.data_monitor = []
        self.bit_monitor = []
        self.started = False
        self.logger.debug("Initialized at address: 0x{:04X}".format(read_address))
    
    def addRegisterToMonitor(self, register):
        if not self.started:
            _, size = self.serial.getRegisterAddress(register, returnSize=True)
            (self.bit_monitor if size == 1 else self.data_monitor).append(register)
        else:
            self.logger.error("Unable to add registers to monitor while it is active")

    def startMonitor(self):
        """ Protocol used for setup is:
            E10 <WRITE_ADDRESS> <LENGTH OF MESSAGE> <NUMBER OF WORDS> 81 <NUMBER OF BITS> 00 <LIST OF WORDS> <LIST OF BITS>
            <LENGTH OF MESSAGE> = (<NUMBER OF WORDS> + <NUMBER OF BITS>) * 2 + 4 
        """
        if not self.started:

            data_len = len(self.data_monitor)
            data = "".join([utils.intToHexString(self.serial.getRegisterAddress(addr)) for addr in self.data_monitor])

            bit_len =  len(self.bit_monitor)
            bit = "".join([utils.intToHexString(self.serial.getRegisterAddress(addr)) for addr in self.bit_monitor])
            
            request = "{:02X}81{:02X}00{}{}".format(data_len, bit_len, data, bit)
            if self.serial.writeToAddress(self.write_address, request)==self.serial.ACK:
                self.logger.info("Monitor installed correctly")
                self.started = True
            else:
                self.logger.info("Unable to install the monitor")
        else:
            self.logger.info("Monitor already installed")

    def stopMonitor(self):
        self.monitor_started = False

    def getValueFromMonitor(self, convertNumber=True):
        data_len = len(self.data_monitor)
        byte_len = int(math.ceil(len(self.bit_monitor)/8.0))
        response = self.serial.readFromAddress(self.read_address, data_len * 2 + byte_len)
        data = {}
        for idx, param in enumerate(self.data_monitor):
            offset = 4 * idx
            code = response[offset:offset+4]
            if convertNumber:
                data[param] = int(code[2:4] + code[0:2],16)
            else:
                data[param] = code[2:4] + code[0:2]
        for idx, param in enumerate(self.bit_monitor):
            offset = 4 * data_len + 2 * ( idx / 8 ) #Search for right byte
            code = int(response[offset:offset+2])
            data[param] = (code & (1 << ( idx % 8 ) )>0)
        return data
