from . import protocol
from . import exceptions
import re
import logging
import math

class FX1N(protocol.Protocol):
    register_offset = {
        'D': {'offset': 0x4000, 'size': 2},
        'C': {'offset': 0x0A00, 'size': 2},
        'T': {'offset': 0x1000, 'size': 2},
        'M': {'offset': 0x0000, 'size': 1},
        'X': {'offset': 0x1200, 'size': 1},
        'Y': {'offset': 0x0C00, 'size': 1},
        'TC':{'offset': 0x1000, 'size': 1}, #Timer Contacts
        'TE':{'offset': 0x2800, 'size': 1}, #Timer Enabled
    }