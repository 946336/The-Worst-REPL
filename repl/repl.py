
import os, sys
import json, re
import time, timeit
from io import StringIO
from contextlib import redirect_stdout
import itertools

import atexit

from .base import environment, command, syntax, common
from .base import sink
from .base.command import helpfmt

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
                # We'd have problems with function
                # lifetime and scope, so we can't really allow nested functions
                sys.stderr.write("Cannot create nested functions\n")
                self.__owner.discard_block()
            else:
                self.__contents.append(line)

            return self

        def make_bindings(self, args, argspec):
            bindings = {
                "FUNCTION": self.__name,
                "#": str(len(args)),
                "@": " ".join([syntax.quote(arg) for arg in args]),
                "0": self.__name,
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
                if line.strip().startswith("shift"):
                    args = args[1:]
                    arspec = argspec[1:]
                    bindings = self.make_bindings(args, argspec)
                    continue

                try:
                    res = self.__owner.eval(line, bindings)
                    if res: print(res.strip("\n"))
                except common.REPLReturn as e:
                    return e.value

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
                    res = self.__owner.eval(line)
                    if res: print(res.strip("\n"))
                return

        # Stupidly, it's not a syntax error to have an else clause in the middle
        # of a conditional chain, even though it's not particularly useful to do
        # so
        def append(self, line):
            line = line.strip()
            if line.startswith("endif"):
                self.__chain.append((self.__condition, self.__block))
                self.complete()
            elif line.startswith("elif"):
                if len(line.split(" ")) == 1:
                    sys.stderr.write("Conditional block must have predicate\n")
                    self.__owner.discard_block()
                    return self

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

            broken = False
            res = self.__owner.eval(self.__condition)
            if res: print(res.strip("\n"))
            while str(self.__owner.get("?")) == "0" and not broken:
                for line in self.__contents:
                    try:
                        res = self.__owner.eval(line)
                        if res: print(res.strip("\n"))
                    except common.REPLBreak as e:
                        broken = True
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

        self.__block_under_construction = []

        self.__execution_depth = 0
        self.__call_stack = []

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

        self.__keywords = {
            "function": self.__start_function,
            "while": self.__start_loop,
            "if": self.__start_conditional,
            "break": self.__break,
            "return": self.__return,
            "quit": self.__stop,
            # Help should always be available, but the command version can
            # be tweaked by the user
            "help": self.__get_command_help,
            "time": self.__time,
        }

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
                "debug": self.__enable_debugging,
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
        self.__add_builtin(self.make_echo_command())
        self.__add_builtin(self.make_echoe_command())
        self.__add_builtin(self.make_alias_command())
        self.__add_builtin(self.make_unalias_command())
        self.__add_builtin(self.make_help_command())
        self.__add_builtin(self.make_set_command())
        self.__add_builtin(self.make_setlocal_command())
        self.__add_builtin(self.make_unset_command())
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
        self.__add_builtin(self.make_undef_command())
        self.__add_builtin(self.make_debug_command())
        self.__add_builtin(self.make_true_command())
        self.__add_builtin(self.make_false_command())
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
            # ._.
            # JSON doesn't like empty files
            if not str(e).endswith("(char 0)"):
                sys.stderr.write("Error reading config variables from {}\n"
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
        self.__functions[str(command_.name)] = command_
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
        if self.__block_under_construction:
            self.__block_under_construction[-1].append(string)
            return ""

        string = string.lstrip()
        if len(string) == 0: return ""
        if string[0] == "#": return ""

        try:
            bits = syntax.split_whitespace(string)
        except common.REPLSyntaxError as e:
            sys.stderr.write("Syntax error: {}\n".format(e))
            self.__env.bind(self.__resultvar, "2")
            return ""

        __env = self.__env
        bindings = self.__env
        if with_bindings is not None:
            e = environment.Environment(name = bits[0],
                    upstream = self.__env, initial_bindings = with_bindings)
            bindings = e

        if str(bits[0]) in self.__keywords:
            self.__env = bindings
            result = None
            try:
                result = self.__keywords[str(bits[0])](bits[1:])
            finally:
                __env.bind(self.__resultvar, str(result or 0))
            return ""

        # We can't do indiscriminate expansion before invoking keyword
        # expressions, because loops would become horribly unwieldy
        bits = [syntax.expand(bit, bindings) for bit in bits]

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
            stdout = self.execute(command, arguments)
        finally:
            self.__env = __env

        if isinstance(sys.stdin, StringIO): sys.stdin.close()
        # if type(sys.stdin) == StringIO: sys.stdin.close()
        sys.stdin = self.__true_stdin
        return stdout

    def execute(self, command, arguments, output_redirect = None):
        self.__execution_depth += 1

        if self.__echo:
            quoted = [syntax.quote(argument) for argument in arguments if
                    argument]
            sys.stderr.write("{} {} {}\n".format("+" *
                self.__execution_depth, command, " ".join(quoted)))

        if command.strip() in self.__keywords:
            out = sink.Wiretap()
            if output_redirect:
                out.join(output_redirect)
            try:
                with redirect_stdout(out):
                    result = self.__keywords[command](arguments)
            finally:
                self.set(self.__resultvar, result)
            stdout =  out.getvalue()
            out.close()
            return stdout

        command = self.lookup_command(command)
        self.__call_stack.append(command.name)

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
            sys.stderr.write("(Error) {}\n".format(command.usage))
            if self.__debug: raise e
            self.__env.bind(self.__resultvar, str(255))
        finally:
            self.__execution_depth -= 1
            self.__call_stack.pop()

        stdout = out.getvalue()
        out.close()

        return stdout

    def do_pipelines(self, bits, with_bindings = None):
        if not any(["|" in bit for bit in bits]): return bits

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
                    e = environment.Environment(name = command,
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

        if not any(["`" in bit for bit in bits]): return bits

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
                            e = environment.Environment(name = accumulator[0],
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
            sys.stderr.write("source: maximum depth exceeded ({})\n".format(
                self.__max_source_depth))
            self.__source_depth -= 1
            return 1

        try:
            with open(filename, "r") as f:
                for line in f:
                    res = self.eval(line.rstrip())
                    if res: print(res.strip("\n"))
        except FileNotFoundError as e:
            if not quiet:
                sys.stderr.write("source: File not found ({})\n"
                        .format(filename))
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

    def set_local(self, name, value):
        self.__env.bind_here(name, str(value))
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
            sys.stderr.write("Factory does not produce Command. No " +
                    "changes made\n")
        return self

    def default_prompt(self, _):
        prompt = ""
        if len(self.__block_under_construction) > 0:
            prompt = "({}/{}) ... ".format(self.__name, "/".join(
                [blk.name for blk in self.__block_under_construction]
            ))
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
                    print(self.eval(input(self.prompt).strip("\n")), end = "")
                except TypeError as e:
                    sys.stderr.write("TypeError: " + str(e) + "\n")
                    if self.__debug: raise e
                except RecursionError as e:
                    sys.stderr.write("Maximum recursion depth exceeded\n")
                    if self.__debug: raise e
                except common.REPLBreak as e:
                    sys.stderr.write("Cannot break when not executing a loop\n")
                except common.REPLReturn as e:
                    sys.stderr.write("Cannot return from outside of function\n")
                except common.REPLError as e:
                    sys.stderr.write("{}\n".format(str(e)))
        except (KeyboardInterrupt, EOFError) as e: # Exit gracefully
            print()
            return self
        except Exception as e: # Really?
            sys.stderr.write("{}: {}\n.format"(str(type(e)), str(e)))
            if self.__debug: raise e
            else: return self.go()

        return self

# ========================================================================
# Optional things - explicitly enable some features
# ========================================================================

    def enable_module(self, module_name):
        try:
            self.__known_modules[module_name]()
        except KeyError as e:
            sys.stderr.write("No module {} known\n".format(module_name))
        else:
            if self.__echo: sys.stderr.write("Loaded module {}\n"
                    .format(module_name))
            self.__modules_loaded.append(module_name)

        return self

    def __enable_shell(self):
        try:
            from .base.modules import shell
        except ImportError as e:
            sys.stderr.write("Failed to import shell module. Please check " +
                    "your installation\n")
            return
        s = shell.make_shell_command()
        self.__add_builtin(s)
        self.__add_alias("!", s.name)

        for command in shell.commands():
            self.__add_builtin(command) # We'll clobber, but that's fine

    def __enable_readline(self):
        try:
            import readline
        except ImportError:
            sys.stderr.write("Could not import readline. Not enabling " +
                    "readline\n")
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
        try:
            from .base.modules import math
        except ImportError as e:
            sys.stderr.write("Failed to import math module. Please check " +
                    "your installation\n")
            return

        for command in math.commands():
            self.__add_builtin(command)

    def __enable_debugging(self):
        self.__add_builtin(self.make_debug_command())

# ========================================================================
# REPL keyword handlers
# ========================================================================

    def __start_function(self, rest):
        if len(rest) == 0:
            sys.stderr.write("Function must have a name\n")
            self.__env.bind("?", "2")
            return

        name, argspec = rest[0], rest[1:]

        if name in REPL.REPLFunction.forbidden_names:
            sys.stderr.write("{} is a reserved word\n".format(name))
            self.__env.bind("?", "3")
            return

        self.__block_under_construction.append(self.REPLFunction(self,
            str(name), [str(spec) for spec in argspec]))

    def __start_loop(self, rest):
        if len(rest) == 0:
            sys.stderr.write("Loop must have condition\n")
            self.__env.bind("?", "2")
            return

        self.__block_under_construction.append(self.Loop(self,
            syntax.ExpandableString(" ".join(
                [str(bit) for bit in rest]
            ))))

    def __start_conditional(self, rest):
        if len(rest) == 0:
            stys.stderr.write("Conditional block must have predicate\n")
            self.__env.bind("?", "3")
            return

        self.__block_under_construction.append(self.Conditional(self,
            syntax.ExpandableString(
                " ".join([str(bit) for bit in rest]
            ))))

    def __break(self, *ignored):
        raise common.REPLBreak()
        return 0

    def __return(self, value):
        if not value: raise common.REPLReturn(None)

        [value] = value
        value = syntax.expand(value, self.__env)

        self.__env.bind(self.__resultvar, str(value or 0))
        raise common.REPLReturn(str(value))

    def __stop(self):
        self.__done = True
        return 0

    def __get_command_help(self, name):
        if not name: return 1

        [name] = name
        name = syntax.expand(name, self.__env)

        command = self.lookup_command(str(name))

        if command is None:
            return 1

        # In case the help command was somehow removed
        if str(name) == "help":
            print(helpfmt("""
                Usage: help command
                Show help for a command
                """))
            return 0

        elif command.name == "Unknown":
            sys.stderr.write("No command {}\n".format(str(name)))
            return 1

        print(command.help)
        return 0

    def __time(self, bits):
        bits = [str(syntax.quote(syntax.expand(bit, self.__env))) for bit
                in bits]
        t0 = timeit.default_timer()
        res = self.eval(" ".join(bits))
        t1 = timeit.default_timer()

        if res: print(res.strip("\n"))
        print("Time elapsed: {:.4f}s".format(t1 - t0))

        return self.get(self.__resultvar)

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
                sys.stderr.write("{} is not an alias\n".format(name))
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
                sys.stderr.write("No command {}\n".format(name))
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
                sys.stderr.write("Invalid identifier name\n")
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
                sys.stderr.write("Invalid identifier name\n")
                return 2

            self.unset(name)
            return 0

        return command.Command(
                unset,
                "unset",
                "unset name",
                "Unset a variable"
        )

    def make_exit_command(self):

        return command.Command(
                self.__stop,
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
                    sys.stderr.write("Subcommand set expected name and value\n")
                    return 1

                name, value = args
                if not re.match("[a-zA-Z0-9_?][a-zA-Z0-9_]*", name):
                    sys.stderr.write("Invalid identifier name\n")
                    return 2

                self.__config_env.bind(name, value)

            elif subcommand == "unset":
                if len(args) != 1:
                    sys.stderr.write("Subcommand unset expected name\n")
                    return 1

                [name] = args
                if not re.match("[a-zA-Z0-9_?][a-zA-Z0-9_]*", name):
                    sys.stderr.write("Invalid identifier name\n")
                    return 2

                self.__config_env.unbind(name)

            elif subcommand == "list":
                if len(args) != 0:
                    sysstderr.write("Subcommand list takes no arguments\n")
                    return 1
                print("\n".join(self.__config_env.list()))
            else:
                sys.stderr.write("Unrecognized subcommand: {}\n"
                        .format(subcommand))
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
                sys.stderr.write("env expected at most one argument\n")
                return 1

            if which[0] == "all":
                print("\n".join(self.__env.list_tree()))
                return 0
            else:
                sys.stderr.write("Unrecognized subcommand: {}\n"
                        .format(which[0]))
                return 2

        return command.Command(
                env,
                "env",
                "env [all]",
                helpfmt("""
                Show all non-config variables.
                    If all is given, list everything, including but not
                    limited to config variables""")
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
                helpfmt("""
                    Slice out a substring. start and end may be :, indicating
                    the ends of the string.
                """)
        )

    def make_sleep_command(self):

        def sleep(seconds):
            try:
                time.sleep(int(seconds))
            except TypeError:
                sys.stderr.write("sleep expects an integer number of seconds\n")
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

                if builtins:    print(builtins)
                if basis:       print(basis)
                if functions:   print(functions)
                if aliases:     print(aliases)

                return 0
            else:
                sys.stderr.write("Valid categories are builtins, basis, "
                        + "functions, aliases, and all\n")
                return 2

        return command.Command(
                list,
                "list",
                "list {builtins, basis, functions, aliases, all}",
                helpfmt("""
                    List available commands in one or all categories
                    """)
        )

    def make_verbose_command(self):

        def verbose(toggle):
            if toggle == "on":
                self.__echo = True
            elif toggle == "off":
                self.__echo = False
            else:
                sys.stderr.write("Argument must be 'on' or 'off'\n")
                return 2
            return 0

        return command.Command(
                verbose,
                "verbose",
                "verbose {on, off}",
                helpfmt("""
                    Turn echoing of commands on or off
                    """)
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

    def make_undef_command(self):

        def undef(*names):
            for name in names:
                self.unregister(name)

            return 0

        return command.Command(
                undef,
                "undef",
                "undef NAMES",
                helpfmt("""
                    Remove functions created with the `function` keyword
                    """)
        )

    def make_debug_command(self):

        def debug(*args):

            if len(args) > 1:
                sys.stderr.write("At most one subcommand expected\n")
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
                sys.stderr.write("Subcommand must be one of: on, off, toggle\n")

            return 0

        return command.Command(
                debug,
                "debug",
                "debug [on, off, toggle]",
                helpfmt("""
                    Toggle or query debugging behavior. When on, most errors
                    stop the REPL and give a normal python stacktrace
                    """)
        )

    def make_true_command(self):

        def true(*args):
            return 0

        return command.Command(
                true,
                "true",
                "true",
                helpfmt("""
                    Do nothing, successfully
                    """)
        )

    def make_false_command(self):

        def false(*args):
            return 1

        return command.Command(
                false,
                "false",
                "false",
                helpfmt("""
                    Do nothing, unsuccessfully
                    """)
        )

    def make_not_command(self):

        def _not(*expr):
            self.eval(" ".join(expr))
            return 1 if str(self.get("?")) == "0" else 0

        return command.Command(
            _not,
            "not",
            "not [command]",
            helpfmt("""
                Invert the result of a command.
                """)
        )

    def make_echo_command(self):
        escape_sequences = [
            (r"\n", "\n"),
            (r"\t", "\t"),
            (r"\a", "\a"),
            (r"\b", "\b"),
            (r"\f", "\f"),
            (r"\r", "\r"),
            (r"\v", "\v"),
            (r"\e", ""),
        ]
        def _echo(*args):
            replaced = []
            for arg in args:
                for target, result in escape_sequences:
                    arg = arg.replace(target, result)
                replaced.append(arg)

            print(" ".join(list(replaced)))
            return 0

        return command.Command(_echo, "echo",
                *command.helpfmt("""
                    echo [ args ]
                    """, """
                    Write arguments to standard output
                    """)
        )


    def make_echoe_command(self):
        escape_sequences = [
                (r"\n", "\n"),
                (r"\t", "\t"),
                (r"\a", "\a"),
                (r"\b", "\b"),
                (r"\f", "\f"),
                (r"\r", "\r"),
                (r"\v", "\v"),
                (r"\e", ""),
                ]
        def _echoe(*args):
            replaced = []
            for arg in args:
                for target, result in escape_sequences:
                    arg = arg.replace(target, result)
                replaced.append(arg)

            sys.stderr.write(" ".join(list(replaced)) + "\n")
            return 0

        return command.Command(_echoe, "echoe",
                *command.helpfmt("""
                    echoe [ args ]
                    """, """
                    Write arguments to standard error
                    """)
        )

    def make_debug_command(self):
        def debug():
            cmd = None
            while True:
                sys.stderr.write("DEBUG >>> ")
                try:
                    cmd = input().strip()
                except EOFError as e:
                    sys.stderr.write("\n")
                    sys.stdin = self.__true_stdin
                    break

                # using `debug` as an exit keyword is necessary to prevent
                # nested debugging sessions
                if cmd in ["debug", "exit", "quit"]: break
                elif cmd in ["stack", "backtrace", "bt", "where"]:
                    sys.stderr.write("Showing stacktrace, most "
                            + "recent call last:\n")
                    sys.stderr.write("{}\n"
                            .format("\n".join(self.__call_stack[:-1])))
                    continue

                res = self.eval(cmd)
                if res: sys.stderr.write(res.strip("\n") + "\n")

            return 0

        return command.Command(
            debug,
            "debug",
            *command.helpfmt("""
            debug
            """, """
            Interrupt the REPL and allow the user to interactively enter
            commands, and then resume.
            End a debugging session with the same command
            """)
        )

    def make_setlocal_command(self):
        def setlocal(name, value):
            if not re.match("[a-zA-Z0-9_?][a-zA-Z0-9_]*", name):
                sys.stderr.write("Invalid identifier name\n")
                return 2
            self.set_local(name, value)
            return 0

        return command.Command(
                setlocal,
                "set-local",
                *command.helpfmt("""
                    set-local name value
                    """,
                    """
                    Set a variable in the current scope
                    """)
                )

