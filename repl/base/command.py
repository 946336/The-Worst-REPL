
import inspect, textwrap

class Command:
    def __init__(self, callable_, name = "", usage = "", helptext = ""):
        if not callable(callable_):
            raise TypeError("Command requires callable object")

        self.__callable = callable_

        # This is nasty with lambda functions
        self.__name = name if name else callable.__name__

        # If no helptext, use function metadata
        self.__usage = usage if usage else inspect.signature(callable)
        self.__helptext = helptext if helptext else inspect.getdoc(callable)

    def __call__(self, *args):
        return self.__callable(*args)

    def copy(self):
        return Command(
            callable_ = self.__callable,
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

# UNTESTED
class WrapperCommand(Command):
    def __init__(self, function, name = "", usage = "", helptext = ""):
        def default_wrapper(*args):
            try:
                result = function(*args)
            except Exception:
                return 1
            else:
                print(result)
                return 0
        super().__init__(default_wrapper, name, usage, helptext)

def helpfmt(*text):
    formatted = []
    for item in text:
        formatted.append(textwrap.dedent(item).strip("\n"))
    return formatted if len(formatted) != 1 else formatted[0]

