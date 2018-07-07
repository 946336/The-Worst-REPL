
from .common import common

import logging

class IsNone(common.REPLError): pass

class Loggable:
    """
    Base class to provide logging facilities
    """
    def __init__(self, logger):
        if logger == None:
            raise IsNone("Logger must not be None")
        self.__logger = logger

    def info    (self, message): self.__logger.info    (message)
    def debug   (self, message): self.__logger.debug   (message)
    def warn    (self, message): self.__logger.warn    (message)
    def error   (self, message): self.__logger.error   (message)
    def critical(self, message): self.__logger.critical(message)

class devnull(Loggable):
    """
    Sometimes you don't care what they have to say
    """
    def __init__(self, logger = None): pass

    def info    (self, message): pass
    def debug   (self, message): pass
    def warn    (self, message): pass
    def error   (self, message): pass
    def critical(self, message): pass

DevNull = devnull()

class AdHoc:
    """
    Ad-Hoc logger for Loggable. Provide your own sink that supports write().
    Usually an open file or sys.stderr.
    Does not do formatting, etc
    """
    def __init__(self, sink, loglevel = logging.DEBUG, name = None, **kwargs):
        """
        Use kwargs to provide prefixes for custom loglevels. The following are
        provided by default:
            INFO
            DEBUG
            WARNING
            ERROR
            CRITICAL
        Prefixes default to the names of the loglevels
        The logger name is provided alongside all messages
        """
        self.__sink = sink
        self.__level = loglevel
        self.__name = "{}/".format(name) if name else ""

        self.__prefixes = {
                "info": "[{}INFO]: ".format(self.__name),
                "debug": "[{}DEBUG]: ".format(self.__name),
                "warning": "[{}WARNING]: ".format(self.__name),
                "error": "[{}ERROR]: ".format(self.__name),
                "critical": "[{}CRITICAL]: ".format(self.__name),
        }
        self.__prefixes.update(kwargs)

    def __log(self, message, level):
        message = str(message)
        if self.__level <= level:
            self.__sink.write(message + "\n")

    def info(self, message):
        self.__log(self.__prefixes["info"] + str(message), logging.INFO)

    def debug(self, message):
        self.__log(self.__prefixes["debug"] + str(message), logging.DEBUG)

    def warn(self, message):
        self.__log(self.__prefixes["warn"] + str(message), logging.WARNING)

    def error(self, message):
        self.__log(self.__prefixes["error"] + str(message), logging.ERROR)

    def critical(self, message):
        self.__log(self.__prefixes["critical"] + str(message), logging.CRITICAL)

import sys
StdErr = AdHoc(sys.stderr, name = "stderr")

# Combine loggers
class Combined:
    """
    Combine loggers to duplicate logging statements to multiple sinks
    """
    def __init__(self, loggers):
        self.__loggers = []

        try:
            for logger in loggers:
                self.__loggers.append(logger)
        except TypeError as e:
            self.__loggers.append(loggers)

    def add(self, logger):
        self.__logger.append(logger)

    def remove(self, logger):
        try:
            self.__loggers.remove(logger)
        except ValueError: pass

    def info(self, message):
        for logger in self.__loggers:
            logger.info(message)

    def debug(self, message):
        for logger in self.__loggers:
            logger.debug(message)

    def warn(self, message):
        for logger in self.__loggers:
            logger.warn(message)

    def error(self, message):
        for logger in self.__loggers:
            logger.error(message)

    def critical(self, message):
        for logger in self.__loggers:
            logger.critical(message)

