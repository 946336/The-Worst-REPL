
import os, sys
import json, re
import time
from io import StringIO
from contextlib import redirect_stdout
import itertools
from textwrap import dedent

import atexit

from .base import environment, command, syntax, common
from .base import sink

# Modules
from .base.modules import shell, math

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

    class REPLFunction:
        # This requires further thought
        forbidden_names = []

        def __init__(self, owner, name, argspec = None):
            self.__name = name
            self.__owner = owner
            self.__argspec = argspec

            self.__contents = []

        @property
        def name(self):
            return self.__name

        @property
        def argspec(self):
            return self.__argspec

        def complete(self, line):
            self.__owner.finish_block()

            usagestring = \
                    ("{} args".format(self.__name)
                    if not self.__argspec
                    else "{} {}".format(self.__name,
                        " ".join(self.__argspec)))

            helpstring = \
                ("function {}\n\t".format(self.__name)
                + "\n\t".join(self.__contents) + "\nendfunction"
                if not self.__argspec else
                "function {} {}\n\t".format(self.__name,
                    " ".join(self.__argspec))
                + "\n\t".join(self.__contents) + "\nendfunction"
                )

            self.__owner.register_user_function(command.Command(
                self,
                self.__name,
                usagestring,
                helpstring
            ))

        def append(self, line):
            line = line.strip()

            if line == "endfunction":
                self.complete(line)
            elif line.startswith("function"):
                print("Cannot create nested functions")
                self.__owner.discard_block()
            else:
                self.__contents.append(line)

            return self

        def make_bindings(self, args, argspec):
            bindings = {
                "FUNCTION": self.__name,
                "#": str(len(args)),
            }

            for position, argument in enumerate(args):
                bindings[str(position + 1)] = argument

            if argspec:
                for name in argspec:
                    bindings[name] = argument

            return bindings

        def __call__(self, *args):
            if self.__argspec and len(args) != len(self.__argspec):
                raise common.REPLRuntimeError("Usage: {} {}"
                        .format(self.__name, " ".join(self.__argspec)))

            argspec = self.__argspec[:]

            bindings = self.make_bindings(args, argspec)

            for line in self.__contents:

                # Execution-time builtins
                if line == "shift":
                    args = args[1:]
                    arspec = argspec[1:]
                    bindings = self.make_bindings(args, argspec)
                    continue

                self.__owner.eval(line, bindings)

                if line.strip().startswith("return"):
                    return

    # Hidden semantic construct. These are not exposed to the end user
    class Block:
        def __init__(self, owner, name = None):
            self.__name = name
            self.__owner = owner
            self.__contents = []

        def append(self, line):
            line = line.strip()
            return self

        def __getitem__(self, index):
            return self.__contents[index]

    class Conditional:
        def __init__(self, owner, condition):
            self.__owner = owner
            self.__name = "Conditional"

            self.__condition = condition
            self.__block = []

            self.__chain = []
            self.__else_block = []

        @property
        def name(self):
            return self.__name

        def complete(self):
            self.__owner.complete_block()
            for pred, blk in self.__chain:
                self.__owner.eval(pred)
                if str(self.__owner.get("?")) != "0":
                    continue

                for line in blk:
                    if line.strip() == "break":
                        raise common.REPLBreak()
                    self.__owner.eval(line)

        def append(self, line):
            line = line.strip()
            if line.startswith("endif"):
                self.__chain.append((self.__condition, self.__block))
                self.complete()
            elif line.startswith("elif "):
                self.__chain.append((self.__condition, self.__block))
                self.__condition = line.split(" ", 1)[-1]
                self.__block = []
            elif line.startswith("else"):
                self.__chain.append((self.__condition, self.__block))
                self.__condition = "true" # Kill me
                self.__block = []
            else:
                self.__block.append(line)
            return self

    # How could we handle a break?
    # TODO Test the break statement
    class Loop:
        def __init__(self, owner, condition):
            self.__condition = condition
            self.__owner = owner
            self.__name = "Loop"
            self.__contents = []

        @property
        def name(self):
            return self.__name

        def complete(self):
            self.__owner.complete_block()

            self.__owner.eval(self.__condition)
            while str(self.__owner.get("?")) == "0":
                for line in self.__contents:
                    if line.strip() == "break":
                        break
                    try:
                        self.__owner.eval(line)
                    except common.REPLBreak as e:
                        break
                self.__owner.eval(self.__condition)

        def append(self, line):
            line = line.strip()

            if line.startswith("done"):
                self.complete()
            else:
                self.__contents.append(line)

    def __init__(self, application_name = "repl", prompt = lambda self: ">>> ",
            upstream_environment = None, dotfile_prefix = None,
            dotfile_root = None, history_length = 1000, echo = False,
            modules_enabled = [], debug = False, noinit = False,
            nodotfile = False, noenv = False):
        # noinit: No builtins
        # nodotfile: Don't use dotfile
        # noenv: No environment

        self.__name = application_name
        self.__echo = echo
        self.__make_unknown_command = make_unknown_command
        self.__debug = debug
        self.__history_length = history_length

        self.__dotfile_prefix = dotfile_prefix or self.__name
        self.__dotfile_root = (os.getcwd() if dotfile_root is None else
                dotfile_root)

        self.__done = False
        self.__true_stdin = sys.stdin
        self.__true_stdout = sys.stdout
        self.__block_under_construction = []

        # The default prompt changes when defining a function
        self.__prompt = self.default_prompt

        self.__escapechar = "\\"
        self.__resultvar = "?"

        if not noenv:
            self.__config_env = environment.Environment(self.name + "-env",
                    upstream = upstream_environment, default_value = "")

            self.__varfile = os.path.join(self.__dotfile_root,
                    self.configs_file_pattern.format(self.__dotfile_prefix))
            self.load_config_vars()

        self.__env = environment.Environment(self.name, upstream =
                self.__config_env if not noenv else None, default_value = "")
        self.__env.bind(self.__resultvar, "0")
        self.__env.bind("0", self.__name)

        # REPL builtins
        self.__builtins = {
                # name : command.Command
        }
        if not noinit:
            self.setup_builtins()

        # Basis commands, if you have a need for them
        self.__basis = {
                # name : command.Command
        }

        # Populated by self.register(command)
        self.__functions = {
                # name : command.Command
        }

        # Populated by the `alias` builtin
        self.__aliases = {
                # name : command.Command
        }

        self.__known_modules = {
                "shell": self.__enable_shell,
                "readline": self.__enable_readline,
                "math": self.__enable_math,
        }
        self.__modules_loaded = []

        # Load selected modules
        for module in modules_enabled:
            self.enable_module(module)

        # Source startup file
        if not nodotfile:
            self.__source_depth = 0
            self.__max_source_depth = 500
            self.source(os.path.join(self.__dotfile_root,
                self.startup_file_pattern.format(self.__dotfile_prefix)),
                    quiet = True)

        # Why must container type default arguments be like this
        enabled_features = []

    def __add_builtin(self, command):
        self.__builtins[command.name] = command
        return self

    def setup_builtins(self):
        self.__add_builtin(shell.echo)
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
        self.__add_builtin(self.make_modules_command())
        self.__add_builtin(self.make_function_command())
        self.__add_builtin(self.make_endfunction_command())
        self.__add_builtin(self.make_undef_command())
        self.__add_builtin(self.make_return_command())
        self.__add_builtin(self.make_debug_command())
        self.__add_builtin(self.make_true_command())
        self.__add_builtin(self.make_false_command())
        self.__add_builtin(self.make_if_command())
        self.__add_builtin(self.make_while_command())
        self.__add_builtin(self.make_break_command())
        self.__add_builtin(self.make_not_command())
        return self

    def __add_basis(self, command):
        self.__basis[command.name] = command
        return self

    def __add_alias(self, newname, oldname):
        c = self.lookup_command(oldname)
        if c.name != self.__make_unknown_command("").name:
            self.__aliases[newname] = c
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
        if not isinstance(command_, command.Command):
            raise TypeError("Can only register objects of type command.Command")
        self.__basis[command_.name] = command_
        return self

    def register_user_function(self, command_):
        if not isinstance(command_, command.Command):
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

    def eval(self, string, with_bindings = None):
        """
        Unless the command is backslashed, lookup order is:
            * aliases
            * functions
            * basis
            * builtins
        If the command is backslashed, then the lookup order is reversed

        Evaluate a string as a repl command
        The returned result is bound to the name ?, and the output is returned
        """
        # This should probably be a chain to allow nesting.
        if self.__block_under_construction:
            self.__block_under_construction[-1].append(string)
            return ""

        string = string.lstrip()
        if len(string) == 0: return ""
        if string[0] == "#": return ""

        try:
            bits = syntax.split_whitespace(string)
        except common.REPLSyntaxError as e:
            print("Syntax error: {}".format(e))
            self.__env.bind(self.__resultvar, "2")
            return ""

        __env = self.__env
        bindings = self.__env
        if with_bindings is not None:
            e = environment.Environment(name = "arguments",
                    upstream = self.__env, initial_bindings = with_bindings)
            bindings = e

        bits = [bit.expand(bindings) for bit in bits]

        bits = self.expand_subshells(bits, with_bindings)
        bits = self.do_pipelines(bits, with_bindings)

        if len(bits) == 0:
            return ""

        if len(bits) == 1:
            command = bits[0]
            arguments = []
        elif len(bits) > 1:
            command, arguments = bits[0], bits[1:]

        self.__env = bindings
        try:
            stdout = self.execute(command, arguments, self.__true_stdout)
        finally:
            self.__env = __env

        if type(sys.stdin) == StringIO: sys.stdin.close()
        sys.stdin = self.__true_stdin
        return stdout

    def execute(self, command, arguments, output_redirect = None):
        if self.__echo:
            quoted = [syntax.quote(argument) for argument in arguments if
                    argument]
            self.__true_stdout.write("+ {} {}\n".format(command,
                " ".join(quoted)))
            self.__true_stdout.flush()

        command = self.lookup_command(command)

        if command is None:
            return ""

        out = sink.Wiretap()
        if output_redirect:
            out.join(output_redirect)

        try:
            with redirect_stdout(out):
                result = command(*arguments)
                self.__env.bind(self.__resultvar, str(result or 0))
        except TypeError as e:
            print("(Error) {}".format(command.usage))
            if self.__debug: raise e
            self.__env.bind(self.__resultvar, str(255))

        stdout = out.getvalue()
        out.close()

        return stdout

    def do_pipelines(self, bits, with_bindings = None):
        piped = [list(group) for k, group
                in itertools.groupby(bits, lambda x: x == "|") if not k]

        if len(piped) > 1:
            bits = piped[-1] # Save the last one to execute normally
            piped = piped[:-1] # Pipeline all the rest

            stdin = self.__true_stdin
            out = None
            for command in piped:

                __env = self.__env
                bindings = self.__env
                if with_bindings is not None:
                    e = environment.Environment(name = "arguments",
                            upstream = self.__env,
                            initial_bindings = with_bindings)
                    bindings = e

                command = self.expand_subshells(command, with_bindings)

                out = StringIO()
                self.__env = bindings
                try:
                    self.execute(command[0], command[1:], out)
                finally:
                    self.__env = __env
                stdin = out

                sys.stdin = stdin
                sys.stdin.seek(0)

        return bits

    def expand_subshells(self, bits, with_bindings = None):
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
                        __env = self.__env
                        bindings = self.__env
                        if with_bindings is not None:
                            e = environment.Environment(name = "arguments",
                                    upstream = self.__env,
                                    initial_bindings = with_bindings)
                            bindings = e

                        accumulator = self.do_pipelines(accumulator,
                                with_bindings)

                        self.__env = bindings
                        try:
                            fresh_bits.append(self.execute(accumulator[0],
                                accumulator[1:]).rstrip("\n"))
                        finally:
                            self.__env = __env

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

        if not name: return None

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

        return self.__make_unknown_command(name)

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

    def loaded_modules(self):
        return self.__modules_loaded

    def set_unknown_command(self, command_factory):
        if isinstance(command_factory(""), command.Command):
            self.__make_unknown_command = command_factory
        else:
            print("Factory does not produce Command. No changes made")
        return self

    def default_prompt(self, _):
        prompt = ""
        if len(self.__block_under_construction) > 0:
            prompt = "({}/{}) ... ".format(self.__name, "/".join(
                [blk.name for blk in self.__block_under_construction]
            ))
            # prompt = "({}/{}) ... ".format(self.__name,
            #         self.__block_under_construction.name)
        else:
            if self.__name == "repl":
                prompt = ">>> "
            else:
                prompt = "({}) >>> ".format(self.__name)

        return prompt

    def finish_block(self):
        return self.__block_under_construction.pop()

    def discard_block(self):
        self.__block_under_construction.pop()
        return self

    complete_block = discard_block

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
                    if self.__debug: raise e
                except RecursionError as e:
                    print("Maximum recursion depth exceeded")
                    if self.__debug: raise e
        except (KeyboardInterrupt, EOFError) as e: # Exit gracefully
            print()
            return self
        except Exception as e: # Really?
            print(type(e), ": ", e)
            if self.__debug: raise e
            self.go()

        return self

# ========================================================================
# Optional things - explicitly enable some features
# ========================================================================

    def enable_module(self, module_name):
        try:
            self.__known_modules[module_name]()
        except KeyError as e:
            print("No module {} known".format(module_name))
        else:
            if self.__echo: print("Loaded module {}".format(module_name))
            self.__modules_loaded.append(module_name)

        return self

    def __enable_shell(self):
        s = shell.make_shell_command()
        self.__add_builtin(s)
        self.__add_alias("!", s.name)

    def __enable_readline(self):
        try:
            import readline
        except ImportError:
            print("Could not import readline. Not enabling readline")
            return

        # Readline and history setup
        self.__histfile = os.path.join(self.__dotfile_root,
            self.history_file_pattern.format(self.__dotfile_prefix))
        atexit.register(readline.write_history_file, self.__histfile)

        try:
            readline.read_history_file(self.__histfile)
            readline.set_history_length(self.__history_length)
        except FileNotFoundError as e:
            pass

        readline.parse_and_bind("tab: complete")
        readline.set_completer(self.completion)

    def __enable_math(self):
        self.__add_builtin(math.make_addition_command())
        self.__add_builtin(math.make_subtraction_command())
        self.__add_builtin(math.make_multiply_command())
        self.__add_builtin(math.make_divide_command())
        self.__add_builtin(math.make_less_than_command())
        self.__add_builtin(math.make_greater_than_command())

# ========================================================================
# REPL commands
# ========================================================================

    def make_alias_command(self):
        # This seems unsafe, because you can probably get into some pretty bad
        # circular situations
        def alias(new_name, name):
            self.__add_alias(new_name, name)
            return 0

        return command.Command(
                alias,
                "alias",
                "alias newname name",
                "Introduce newname as an alias for name",
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

    def make_modules_command(self):

        def modules():

            if self.__modules_loaded:
                print("\n".join(self.__modules_loaded))

            return 0

        return command.Command(
                modules,
                "modules",
                "modules",
                "List all loaded modules",
        )

    def make_function_command(self):

        def function(name, *argspec):
            if name in REPL.REPLFunction.forbidden_names:
                print("{} is a reserved name".format(name))
                return 2

            self.__block_under_construction.append(self.REPLFunction(self, name,
                argspec))

            return 0

        return command.Command(
                function,
                "function",
                "function name",
                "Begin defining a function with that name"
        )

    # Proxy for REPLFunction functionality
    def make_endfunction_command(self):

        def endfunction():
            if len(self.__block_under_construction) == 0:
                print("No function to end")
                return 1
            elif type(self.__block_under_construction[-1]) != REPLFunction:
                print("Enclosing scope is not a function")
                return 1
            return 0

        return command.Command(
                endfunction,
                "endfunction",
                "endfunction",
                "End the source code for a function"
        )

    # TODO - fold into commands that are exclusive to REPLFunctions
    def make_return_command(self):

        def _return(value):
            return value

        return command.Command(
                _return,
                "return",
                "return VAL",
                "End a function and return a value"
        )

    def make_undef_command(self):

        def undef(*names):
            for name in names:
                try:
                    del self.__functions[name]
                except KeyError as e:
                    print("No function {} to remove".format(name))

            return 0

        return command.Command(
                undef,
                "undef",
                "undef NAMES",
                dedent("""
                    Remove functions created with the `function` command
                    """).strip("\n")
        )

    def make_debug_command(self):

        def debug(*args):

            if len(args) > 1:
                print("At most one subcommand expected")
                return 2

            if len(args) == 0:
                print(str(self.__debug))
                return 0

            state = args[0]

            if state.lower() == "on":
                self.__debug = True
            elif state.lower() == "off":
                self.__debug = False
            elif state.lower() == "toggle":
                self.__debug = not self.__debug
            else:
                print("Subcommand must be one of: on, off, toggle")

            return 0

        return command.Command(
                debug,
                "debug",
                "debug [on, off, toggle]",
                dedent("""
                    Toggle or query debugging behavior. When on, most errors
                    stop the REPL and give a normal python stacktrace
                    """).strip("\n")
        )

    def make_true_command(self):

        def true(*args):
            return 0

        return command.Command(
                true,
                "true",
                "true",
                dedent("""
                    Do nothing, successfully
                    """).strip("\n")
        )

    def make_false_command(self):

        def false(*args):
            return 1

        return command.Command(
                false,
                "false",
                "false",
                dedent("""
                    Do nothing, unsuccessfully
                    """).strip("\n")
        )

    def make_if_command(self):
        def _if(*predicate):
            if len(predicate) < 1:
                print("Conditional statement must have a predicate")
                return 2

            self.__block_under_construction.append(self.Conditional(self,
                " ".join(predicate)))

            return 0

        return command.Command(
            _if,
            "if",
            "if condition ....",
            dedent("""
                Start a conditional block.
                if predicate
                ...
                elif predicate2
                ...
                else
                ...
                endif
                """).strip("\n")
        )

    def make_while_command(self):
        def _while(*predicate):
            if len(predicate) < 1:
                print("Loop must have test")
                return 2

            self.__block_under_construction.append(self.Loop(self,
                " ".join(predicate)
                ))

            return 0

        return command.Command(
            _while,
            "while",
            "while predicate",
            dedent("""
                Start a loop with the following structure:
                while predicate
                ...
                done
            """).strip("\n")
        )

    def make_break_command(self):
        def _break(*args):
            print("Only meaningful in a loop")
            return 0

        return command.Command(
                _break,
                "break",
                "break",
                "Break out of a loop"
        )

    def make_not_command(self):

        def _not(*expr):
            self.eval(" ".join(expr))
            return 1 if str(self.get("?")) == "0" else 0

        return command.Command(
            _not,
            "not",
            "not [command]",
            dedent("""
                Invert the result of a command.
                """).strip("\n")
        )

