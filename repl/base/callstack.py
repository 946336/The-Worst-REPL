
class CallStackEntry:
    def __init__(self, name, line_number):
        self.name = name
        self.line_number = line_number

    def __repr__(self):
        return "{}:{}".format(self.line_number, self.name)

 class CallStack:
     def __init__(self):
         self.__stack = []

    def __repr__(self):
        stk =  "\n".join([str(entry) for entry in self.__stack])
        return "Traceback (Most recent call last):\n" + stk + "\n"

    def append(self, entry):
        self.__stack.append(entry)

    def pop(self):
        last = self.__stack[-1]
        self.__stack.pop()
        return last

