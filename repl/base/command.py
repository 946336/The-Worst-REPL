
from textwrap import dedent
import inspect
import subprocess

from . import syntax

class Command:
    # Any more, and we risk getting into a situation where people stop writing
    # python and start writing repl code, so this is as good as we're going to
    # get
    def __init__(self, callable, name = "", usage = "", helptext = ""):
        self.__callable = callable

        # This is nasty with lambda functions
        self.__name = name if name else callable.__name__

        # If no helptext, use docstring from function
        self.__helptext = helptext if helptext else inspect.getdoc(callable)

        self.__usage = usage if usage else inspect.signature(callable)

    def __call__(self, *args):
        return self.__callable(*args)

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

def make_shell_command():

    def shell(*args):
        if len(args) == 0: return 0

        try:
            output = subprocess.check_output(
                    " ".join([syntax.quote(arg) for arg in args]),
                    shell = True, universal_newlines = True)
        except ValueError as e:
            print("Invalid arguments: {}".format(str(e)))
        except OSError as e:
            print("Error: {}".format(str(e)))
            return 2
        except subprocess.CalledProcessError as e:
            print(str(e.stdout), end = "")
            return e.returncode

        print(str(output), end = "")
        return 0

    return Command(
            shell,
            "shell",
            "shell command [arguments]",
            dedent("""
                Execute a program on the underlying system
                """).strip("\n")
    )

