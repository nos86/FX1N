
import binascii

def intToHexString(value, length=2):
    return binascii.hexlify(int.to_bytes(value,length,'little')).decode().upper()

#FIXME: i'm not sure it is useful
def hexStringToInt(value, length=2):
    pass