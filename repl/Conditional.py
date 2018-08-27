
from .base import common

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
                try:
                    res = self.__owner.eval(line)
                except common.REPLFunctionShift as e:
                    self.__owner.stack_top().obj.callable.shift()
                    continue
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

