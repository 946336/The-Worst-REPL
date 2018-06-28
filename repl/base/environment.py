
"""
Environments

* Bind names to values, allowing lookup and modification by trampling
* Chain off of one another, allowing lookups and assignments to other
environments
* Variable shadowing is _not_ the behavior
"""

import sys

class Environment:
    def __init__(self, name = "(?)", upstream = None, default_value = ""):
        self.__name = name
        self.__bindings = {}

        # Default value to give when something isn't found
        self.__default = default_value

        if type(upstream) not in [type(None), Environment]:
            raise RuntimeError("Upstream environment must be None or an environment")
        self.__upstream = upstream

    # Bindings search up as far as possible for something to trample, but
    # otherwise stay at this height
    def bind(self, name, value):
        if self.update_upstream(name, value) is None:
            self.__bindings[name] = value

    # Return name of environment where binding was updated, or None if no
    # matching binding was found
    def update_upstream(self, name, value):
        up = None
        if self.__upstream is not None:
            up = self.__upstream.update_upstream(name, value)

            if up is None and self.__bindings.get(name, None) is not None:
                self.__bindings[name] = value
                return self.__name

        return up

    def bind_no_trample(self, name, value):
        if name in self.__bindings.keys():
            raise KeyError("Key {} already present in environment {}"
                    .format(name, self.__name))
        self.bind(name, value)

    def unbind(self, name):
        try:
            del self.__bindings[name]
        except KeyError as e:
            # Unbinding something we don't have is fine
            pass

    # Don't catch the exception when unbinding something we don't have
    def unbind_strict(self, name):
        del self.__bindings[name]

    # Downstream environments have priority
    def get(self, name):
        mine = self.__bindings.get(name, None)

        if mine is None:
            if self.__upstream is None:
                return self.__default
            else:
                return self.__upstream.get(name)
        else:
            return mine

    def __getitem__(self, name):
        return self.get(name)

    def load_from(self, file_like):
        line_nr = 0
        for line in file_like:
            line_nr += 1
            if line.strip() == "": continue
            if line.strip()[0] == "#": continue
            if line.strip()[0] == "=":
                print("Warning:{}:{}: Expected name before '='\n{}"
                        .format(self.__varfile, line_nr, line))
                continue

            pieces = [bits.strip() for bits in line.split("=") if
                    bits.strip() != ""]

            if len(pieces) < 2:
                pieces.append("")

            value = pieces[-1]
            for name in pieces[:-1]:
                self.__bindings[name] = value

    def write_to(self, file_like):
        for k, v in self.__bindings.items():
            file_like.write("{} = {}\n".format(str(k), str(v)))

    def list(self):
        return [ "{} -> {}".format(k, v) for k, v in self.__bindings.items() ]

    def list_tree(self):
        finger = self.__upstream

        accum = ["==========\n{}\n==========".format(self.__name),
                "\n".join(self.list())]

        while finger is not None:
            accum.append("==========\n{}\n==========".format(finger.__name))
            accum.append("\n".join(finger.list()))
            finger = finger.__upstream

        return accum

