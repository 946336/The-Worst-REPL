from .. import command, syntax

import subprocess

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

    return command.Command(
            shell,
            "shell",
            "shell command [arguments]",
            helpfmt("""
                Execute a program noninteractively on the underlying system
                """)
    )

