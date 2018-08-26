
import inspect, textwrap

class Command:
    def __init__(self, callable, name = "", usage = "", helptext = ""):
        self.__callable = callable

        # This is nasty with lambda functions
        self.__name = name if name else callable.__name__

        # If no helptext, use function metadata
        self.__usage = usage if usage else inspect.signature(callable)
        self.__helptext = helptext if helptext else inspect.getdoc(callable)

    def __call__(self, *args):
        return self.__callable(*args)

    def copy(self):
        return Command(
            callable = self.__callable,
            name = self.__name,
            usage = self.__usage,
            helptext = self.__helptext
        )

    @property
    def callable(self):
        return self.__callable

    @property
    def name(self):
        return self.__name

    @property
    def usage(self):
        return "Usage: " + self.__usage

    @usage.setter
    def set_usage(self, usage):
        self.__usage = usage

    @property
    def help(self):
        return self.usage + ("\n" + self.__helptext if self.__helptext else "")

    @help.setter
    def set_help(self, helptext):
        self.__helptext = helptext

def helpfmt(*text):
    formatted = []
    for item in text:
        formatted.append(textwrap.dedent(item).strip("\n"))
    return formatted if len(formatted) != 1 else formatted[0]

