
from . import formatter
from .base import command, syntax, common

import re

class REPLFunction:
    # This requires further thought
    forbidden_names = []

    forbidden_argspec_pattern = re.compile(
        "^[0-9]"
    )

    def __init__(self, owner, name, argspec = None):
        self.__name = name
        self.__owner = owner
        self.__variadic = argspec[-1] == "..." if argspec else False
        self.__argspec = argspec[:-1] if self.__variadic else argspec

        self.__contents = []

        self.args_ = None
        self.argspec_ = None

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
            ("function {}\n".format(self.__name)
            + formatter.format(self.__contents, depth = 1) + "\nendfunction"
            if not self.__argspec else
            "function {} {}\n".format(self.__name,
                " ".join(self.__argspec))
            + formatter.format(self.__contents, depth = 1) + "\nendfunction"
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

        for name, argument in zip(argspec, args):
            bindings[name] = argument

        return bindings

    def shift(self):
        self.args_ = self.args_[1:]

        to_unset = None
        if len(self.args_) < len(self.argspec_):
            to_unset = self.argspec_[0]
            self.argspec_ = self.argspec_[1:]

        bindings = self.make_bindings(self.args_, self.argspec_)

        # Unset last argument
        del self.bindings[str(len(self.args_))]
        if to_unset:
            del self.bindings[str(to_unset)]

        # Apply shift down
        for k, v in bindings.items():
            self.bindings[k] = v

    def calledIncorrectly(self, args):
        if not self.__argspec: return False
        if self.__variadic:
            return len(args) < len(self.__argspec)
        else:
            return len(args) != len(self.__argspec)

    def __call__(self, *args):
        if self.calledIncorrectly(args):
            raise common.REPLRuntimeError("Usage: {} {}"
                    .format(self.__name, " ".join(self.__argspec)))

        self.argspec_ = self.__argspec[:]
        self.args_ = args

        self.bindings = self.make_bindings(self.args_, self.argspec_)

        self.__owner.add_scope(self.bindings, self.__name)

        try:
            for line in self.__contents:
                try:
                    res = self.__owner.eval(line)
                    self.__owner.stack_top().line_number += 1
                    if res: print(res.strip("\n"))
                except common.REPLReturn as e:
                    return e.value
                except common.REPLFunctionShift as e:
                    self.shift()
                    continue
        finally:
            self.__owner.pop_scope()

