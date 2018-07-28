
class REPLError(Exception): pass
class REPLBreak(Exception): pass

class REPLSyntaxError(REPLError): pass
class REPLRuntimeError(REPLError): pass

