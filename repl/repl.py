
import os, sys
import json, re
import time
from io import StringIO
from contextlib import redirect_stdout
import itertools
from textwrap import dedent

# Oof
import readline
import atexit

from .base import environment, command, syntax, common

DEBUG = True

def make_unknown_command(name):

    def unknown_command(*args):
        print("Unknown command: {}".format(name))
        return 1

    return command.Command(
            unknown_command,
            "Unknown",
            None,
            "Unknown command: {}".format(name),
    )

class REPL:
    startup_file_pattern = ".{}rc"
    history_file_pattern = ".{}_history"
    configs_file_pattern = ".{}_vars"

    def __init__(self, application_name = "repl", prompt = lambda self: ">>> ",
            upstream_environment = None, dotfile_prefix = None,
            dotfile_root = None, history_length = 1000, echo = False):
        self.__name = application_name
        self.__echo = echo

        self.__dotfile_prefix = dotfile_prefix or self.__name
        self.__dotfile_root = (os.getcwd() if dotfile_root is None else
                dotfile_root)

        self.__prompt = (prompt
                if application_name == "repl"
                else lambda _: "({}) >>> ".format(self.__name))

        self.__done = False
        self.__true_stdin = sys.stdin
        self.__true_stdout = sys.stdout

        self.__escapechar = "\\"
        self.__resultvar = "?"

        self.__config_env = environment.Environment(self.name + "-env",
                upstream = upstream_environment, default_value = "")

        self.__varfile = os.path.join(self.__dotfile_root,
                self.configs_file_pattern.format(self.__dotfile_prefix))
        self.load_config_vars()

        self.__env = environment.Environment(self.name, upstream =
                self.__config_env, default_value = "")
        self.__env.bind(self.__resultvar, "0")
        self.__env.bind("0", self.__name)

        # REPL builtins
        self.__builtins = {
                # name : command.Command
        }
        self.setup_builtins()

        # Basis commands, if you have a need for them
        self.__basis = {
                # name : command.Command
        }
        self.setup_basis()

        # Populated by self.register(command)
        self.__functions = {
                # name : command.Command
        }

        # Populated by the `alias` builtin
        self.__aliases = {
                # name : command.Command
        }

        # Readline and history setup
        self.__histfile = os.path.join(self.__dotfile_root,
            self.history_file_pattern.format(self.__dotfile_prefix))
        atexit.register(readline.write_history_file, self.__histfile)

        try:
            readline.read_history_file(self.__histfile)
            readline.set_history_length(history_length)
        except FileNotFoundError as e:
            pass

        readline.parse_and_bind("tab: complete")
        readline.set_completer(self.completion)

        # Source startup file
        self.__source_depth = 0
        self.__max_source_depth = 500
        self.source(os.path.join(self.__dotfile_root,
            self.startup_file_pattern.format(self.__dotfile_prefix)),
                quiet = True)

    def __add_builtin(self, command):
        self.__builtins[command.name] = command
        return self

    def setup_builtins(self):
        self.__add_builtin(command.echo)
        self.__add_builtin(self.make_alias_command())
        self.__add_builtin(self.make_unalias_command())
        self.__add_builtin(self.make_help_command())
        self.__add_builtin(self.make_set_command())
        self.__add_builtin(self.make_unset_command())
        self.__add_builtin(self.make_quit_command())
        self.__add_builtin(self.make_exit_command())
        self.__add_builtin(self.make_source_command())
        self.__add_builtin(self.make_cat_command())
        self.__add_builtin(self.make_config_command())
        self.__add_builtin(self.make_env_command())
        self.__add_builtin(self.make_slice_command())
        self.__add_builtin(self.make_sleep_command())
        self.__add_builtin(self.make_list_command())
        self.__add_builtin(self.make_verbose_command())
        return self

    def __add_basis(self, command):
        self.__basis[command.name] = command
        return self

    # No basis by default. Provide your own if you so desire
    def setup_basis(self):
        pass
        return self

    def load_config_vars(self):
        try:
            with open(self.__varfile, "r") as f:
                self.__config_env.load_from(f)
        except FileNotFoundError as e:
            pass
        except json.decoder.JSONDecodeError as e:
            if not str(e).endswith("(char 0)"): # ._.
                print("Error reading config variables from {}"
                        .format(self.__varfile))

        atexit.register(self.write_config)
        return self

    def write_config(self):
        with open(self.__varfile, "w") as f:
            self.__config_env.write_to(f)
        return self

    def completion(self, text, state):

        # Ouch
        possibilities = ( []
                + list(self.__aliases.keys())
                + list(self.__functions.keys())
                + list(self.__basis.keys())
                + list(self.__builtins.keys())
        )

        if len(text) > 0 and text[0] == "\\":
            possibilities.reverse()
            text = text[1:]

        possibilities = [candidate for candidate in possibilities
                if candidate.startswith(text.strip("\n"))]

        return possibilities[state]

    def register(self, command_):
        if isinstance(command_, command.Command):
            raise TypeError("Can only register objects of type command.Command")
        self.__functions[command_.name] = command_
        return self

    def unregister(self, name):
        try:
            del self.__functions[name]
        except KeyError as e:
            pass
        return self

    def set_prompt(self, prompt_callable):
        self.__prompt = prompt_callable
        return self

    # Oh boy
    # We have to figure out output redirection in this context, because this
    # is the context in which output redirection happens
    def eval(self, string):
        """
        Unless the command is escaped, lookup order is:
            * aliases
            * functions
            * basis
            * builtins
        If the command is escaped, then the lookup order is reversed

        Evaluate a string as a repl command
        The returned result is bound to the name ?, and the output is returned
        """
        string = string.lstrip()
        if len(string) == 0: return ""
        if string[0] == "#": return ""

        try:
            bits = syntax.split_whitespace(string)
        except common.REPLSyntaxError as e:
            print("Syntax error: {}".format(e))
            self.__env.bind(self.__resultvar, "2")
            return ""

        bits = [bit.expand(self.__env) for bit in bits]

        bits = self.do_pipelines(bits)
        bits = self.expand_subshells(bits)

        if len(bits) == 0:
            return ""

        if len(bits) == 1:
            command = bits[0]
            arguments = []
        elif len(bits) > 1:
            command, arguments = bits[0], bits[1:]

        stdout = self.execute(command, arguments)

        print(stdout, end="")

        if type(sys.stdin) == StringIO: sys.stdin.close()
        sys.stdin = self.__true_stdin
        return stdout

    def execute(self, command, arguments):
        if self.__echo:
            quoted = [syntax.quote(argument) for argument in arguments if
                    argument]
            print("+ {} {}".format(command, " ".join(quoted)))

        command = self.lookup_command(command)

        if command is None:
            return ""

        out = StringIO()
        # TODO
        # We can probably change how this all works. Instead of capturing
        # stdout and holding it hostage, we might be able to just skim a copy
        # instead, and only suppress it when a pipeline happens. This'll
        # require some rejiggering of eval, execute, and do_pipelines, but it
        # should net us a lot of usability, and potentially make cat less
        # pointless.

        try:
            with redirect_stdout(out):
                result = command(*arguments)
                self.__env.bind(self.__resultvar, str(result or 0))
        except TypeError as e:
            print("(Error) {}".format(command.usage))
            self.__env.bind(self.__resultvar, str(255))

        stdout = out.getvalue()
        out.close()

        return stdout

    def do_pipelines(self, bits):
        piped = [list(group) for k, group
                in itertools.groupby(bits, lambda x: x == "|") if not k]

        if len(piped) > 1:
            bits = piped[-1] # Save the last one to execute normally
            piped = piped[:-1] # Pipeline all the rest

            stdin = self.__true_stdin
            out = None
            for command in piped:

                out = StringIO()
                with redirect_stdout(out):
                    output = self.execute(command[0], command[1:])
                    print(output, end = "")

                stdin = out

                sys.stdin = stdin
                sys.stdin.seek(0)

        return piped[-1]

    def expand_subshells(self, bits):
        # Handling subshell expansion
        if len([tick for tick in bits if tick == "`"]) % 2 != 0:
            raise common.REPLSyntaxError("Error: Unmatched `")

        fresh_bits = []

        subshell = False
        accumulator = []
        for bit in bits:
            if bit == "`":
                if subshell: # Closing a subshell command
                    if len(accumulator) > 0:
                        fresh_bits.append(self.execute(accumulator[0],
                            accumulator[1:]).rstrip("\n"))
                    accumulator = []
                else: # Starting a subshell command
                    pass
                # Flip state
                subshell = not subshell
            else:
                if subshell: # Add to subshell command
                    accumulator.append(bit)
                else: # Just part of the normal command
                    fresh_bits.append(bit)

        return fresh_bits

    def lookup_command(self, name):

        envs = [self.__aliases,
                self.__functions,
                self.__basis,
                self.__builtins]

        if name[0] == self.__escapechar:
            envs.reverse()
            name = name[1:]

        for env in envs:
            value = env.get(name, None)
            if value is not None:
                return value

        return make_unknown_command(name)

    def source(self, filename, quiet = False):
        self.__source_depth += 1
        if self.__source_depth > self.__max_source_depth:
            sys.stderr.write("source: maximum depth exceeded ({})".format(
                self.__max_source_depth))
            return 1

        try:
            with open(filename, "r") as f:
                for line in f:
                    self.eval(line.rstrip())
        except FileNotFoundError as e:
            if not quiet:
                print("source: File not found ({})".format(filename))
            self.__source_depth -= 1
            return 1
        self.__source_depth -= 1
        return 0

    @property
    def echo(self):
        return self.__echo

    def set_echo(self, echo):
        self.__echo = bool(echo)
        return self

    @property
    def done(self):
        return self.__done

    @property
    def name(self):
        return self.__name

    @property
    def prompt(self):
        try:
            return self.__prompt(self)
        except TypeError:
            return "({}/Prompt error) >>> ".format(self.__name)

    def set(self, name, value):
        self.__env.bind(name, str(value))
        return self

    def get(self, name):
        return self.__env.get(name)

    def unset(self, name):
        self.__env.unbind(name)
        return self

    # If you find yourself wanting to edit this function, don't bother. That
    # means you're probably trying to ping-pong control between this module
    # and your own code, and you should probably do that manually. Just paste
    # this somewhere and hack on it there.
    def go(self):
        """
        Convenience method provided in case you just want to let the REPL run
        and do its thing without passing control back and forth
        """
        try:
            while not self.done:
                try:
                    self.eval(input(self.prompt).strip("\n"))
                except common.REPLError as e:
                    print(e)
                except TypeError as e:
                    print("TypeError: " + str(e))
        except (KeyboardInterrupt, EOFError) as e: # Exit gracefully
            print()
            return self
        except Exception as e: # Really?
            print(type(e), ": ", e)
            self.go()

        return self

# ========================================================================
# REPL commands
# ========================================================================

    def make_alias_command(self):
        # This seems unsafe, because you can probably get into some pretty bad
        # circular situations
        def alias(new_name, name):
            self.__aliases[new_name] = self.lookup_command(name)
            return 0

        return command.Command(
                alias,
                "alias",
                "alias newname name",
                "Introduce new-name as an alias for name",
        )

    def make_unalias_command(self):

        def unalias(name):
            try:
                del self.__aliases[name]
            except KeyError:
                print("{} is not an alias".format(name))
                return 1
            return 0

        return command.Command(
                unalias,
                "unalias",
                "unalias name",
                "Remove an alias"
        )

    def make_help_command(self):

        def help(name):
            command = self.lookup_command(name)

            if command.name == "Unknown":
                print("No command {}".format(name))
                return 1

            print(command.help)
            return 0

        return command.Command(
                help,
                "help",
                "help command",
                "Show help for a command",
        )

    def make_set_command(self):

        def set(name, value):
            if not re.match("[a-zA-Z0-9_?][a-zA-Z0-9_]*", name):
                print("Invalid identifier name")
                return 2

            self.set(name, value)
            return 0

        return command.Command(
                set,
                "set",
                "set name value",
                "Set a value for name",
        )

    def make_unset_command(self):

        def unset(name):
            if not re.match("[a-zA-Z0-9_?][a-zA-Z0-9_]*", name):
                print("Invalid identifier name")
                return 2

            self.unset(name)
            return 0

        return command.Command(
                unset,
                "unset",
                "unset name",
                "Unset a variable"
        )

    def make_quit_command(self):

        def quit():
            self.__done = True
            return 0

        return command.Command(
                quit,
                "quit",
                "quit",
                "Stop the repl",
        )

    def make_exit_command(self):

        def exit():
            self.__done = True
            return 0

        return command.Command(
                exit,
                "exit",
                "exit",
                "Stop the repl",
        )

    def make_source_command(self):

        def source(filename):
            return self.source(filename)

        return command.Command(
                source,
                "source",
                "source filename",
                "Read and run the contents of a file"
        )

    def make_cat_command(self):

        def cat():
            try:
                while True:
                    print(input())
            except EOFError:
                return 0

        return command.Command(
                cat,
                "cat",
                "cat",
                "Copy standard input to standard output"
        )

    def make_config_command(self):

        def config(subcommand, *args):
            if subcommand == "set":
                if len(args) != 2:
                    print("Subcommand set expected name and value")
                    return 1

                name, value = args
                if not re.match("[a-zA-Z0-9_?][a-zA-Z0-9_]*", name):
                    print("Invalid identifier name")
                    return 2

                self.__config_env.bind(name, value)

            elif subcommand == "unset":
                if len(args) != 1:
                    print("Subcommand unset expected name")
                    return 1

                [name] = args
                if not re.match("[a-zA-Z0-9_?][a-zA-Z0-9_]*", name):
                    print("Invalid identifier name")
                    return 2

                self.__config_env.unbind(name)

            elif subcommand == "list":
                if len(args) != 0:
                    print("Subcommand list takes no arguments")
                    return 1
                print("\n".join(self.__config_env.list()))
            else:
                print("Unrecognized subcommand: {}".format(subcommand))
                return 2

            return 0

        return command.Command(
            config,
            "config",
            "config {set, unset, list} [args...]",
            "Set or unset persistent config variables"
        )

    def make_env_command(self):

        def env(*which):

            if len(which) == 0:
                print("\n".join(self.__env.list()))
                return 0

            if len(which) > 1:
                print("env expected at most one argument")
                return 1

            if which[0] == "all":
                print("\n".join(self.__env.list_tree()))
                return 0
            else:
                print("Unrecognized subcommand: {}".format(which[0]))
                return 2

        return command.Command(
                env,
                "env",
                "env [all]",
                dedent("""
                Show all non-config variables.
                    If all is given, list everything, including but not
                    limited to config variables""".lstrip("\n"))
        )

    def make_slice_command(self):

        def slice(string, start, end):
            string = str(string)
            start = None if start == ":" else int(start)
            end = None if stop == ":" else int(stop)

            if start is None and end is None:
                return string
            elif start is None and end is not None:
                return string[:end]
            elif end is None and start is not None:
                return string[start:]
            else:
                return string[start:end]

        return command.Command(
                slice,
                "slice",
                "slice string start-index end-index",
                dedent("""
                    Slice out a substring. start and end may be :, indicating
                    the ends of the string.
                """).strip("\n")
        )

    def make_sleep_command(self):

        def sleep(seconds):
            try:
                time.sleep(int(seconds))
            except TypeError:
                print("sleep expects an integer number of seconds")
                return 2

            return 0

        return command.Command(
                sleep,
                "sleep",
                "sleep seconds",
                "Wait a number of seconds"
        )

    def make_list_command(self):

        def list(category):
            if category == "builtins":
                print("\n".join(self.__builtins.keys()))
                return 0
            elif category == "basis":
                print("\n".join(self.__basis.keys()))
                return 0
            elif category == "functions":
                print("\n".join(self.__functions.keys()))
                return 0
            elif category == "aliases":
                print("\n".join(self.__aliases.keys()))
                return 0
            elif category == "all":
                builtins = ("\n".join(self.__builtins.keys()))
                basis = ("\n".join(self.__basis.keys()))
                functions = ("\n".join(self.__functions.keys()))
                aliases = ("\n".join(self.__aliases.keys()))

                if builtins: print(builtins)
                if basis: print(basis)
                if functions: print(functions)
                if aliases: print(aliases)

                return 0
            else:
                print("Valid categories are builtins, basis, functions, "
                        + "aliases, and all")
                return 2

        return command.Command(
                list,
                "list",
                "list {builtins, basis, functions, aliases, all}",
                dedent("""
                    List available commands in one or all categories
                    """).strip("\n")
        )

    def make_verbose_command(self):

        def verbose(toggle):
            if toggle == "on":
                self.__echo = True
            elif toggle == "off":
                self.__echo = False
            else:
                print("Argument must be 'on' or 'off'")
                return 2
            return 0

        return command.Command(
                verbose,
                "verbose",
                "verbose {on, off}",
                dedent("""
                    Turn echoing of commands on or off
                    """).strip("\n")
        )

