
class REPLError(Exception):  pass
class REPLControl(Exception): pass

class REPLBreak(REPLControl):  pass

class REPLReturn(REPLControl):
    def __init__(self, value):
        self.value = value

class REPLFunctionShift(REPLControl): pass

class REPLSyntaxError(REPLError): pass
class REPLRuntimeError(REPLError): pass

