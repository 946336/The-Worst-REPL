
class REPLError(Exception):  pass

class REPLBreak(REPLError):  pass

class REPLReturn(REPLError):
    def __init__(self, value):
        self.value = value

class REPLSyntaxError(REPLError): pass
class REPLRuntimeError(REPLError): pass

