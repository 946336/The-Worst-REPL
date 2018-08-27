
from .base import common

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
                except common.REPLFunctionShift as e:
                    self.__owner.stack_top().obj.callable.shift()
                    continue
            self.__owner.eval(self.__condition)

    def append(self, line):
        line = line.strip()

        if line.startswith("done"):
            self.complete()
        else:
            self.__contents.append(line)
