
from textwrap import dedent
import inspect

class Command:
    # Any more, and we risk getting into a situation where people stop writing
    # python and start writing repl code, so this is as good as we're going to
    # get
    def __init__(self, callable, name = "", usage = "", helptext = ""):
        self.__callable = callable

        # This is nasty with lambda functions
        self.__name = name if name else callable.__name__

        # If no helptext, use docstring from function?
        self.__helptext = helptext if helptext else inspect.getdoc(callable)

        self.__usage = usage if usage else inspect.signature(callable)

    def __call__(self, *args):
        return self.__callable(*args)

    @property
    def name(self):
        return self.__name

    @property
    def usage(self):
        return self.__usage

    @property
    def help(self):
        return self.usage + ("\n" + self.__helptext if self.__helptext else "")

# ===============================================================
# Default, repl-independent commands
# ===============================================================

def _echo(*args):
    print(" ".join(list(args)))
    return 0

echo = Command(_echo, "echo",
        dedent("""
            echo [ args ]
            """).strip(),
        dedent("""
        Write arguments to standard output
        """).strip())

