
class NotSupportedCommand(Exception):
    pass

class NotSupportedRegister(ValueError):
    pass

class ResponseMalformed(Exception):
    pass

class WrongChecksum(Exception):
    pass

class PLCNotAvailable(Exception):
    pass