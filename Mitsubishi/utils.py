
import binascii

def intToHexString(value, length=2):
    return binascii.hexlify(int.to_bytes(value,length,'little')).decode().upper()

def hexStringToInt(value):
    return int.from_bytes(binascii.unhexlify(value), 'little')