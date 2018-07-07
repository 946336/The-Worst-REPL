
class ComposteBaseException(Exception): pass

class DecryptError(ComposteBaseException): pass
class EncryptError(ComposteBaseException): pass
class GenericError(ComposteBaseException): pass

