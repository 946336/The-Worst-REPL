
from . import command

def make_addition_command():

    def add(lhs, rhs):
        try:
            print(str(int(lhs) + int(rhs)))
            return 0
        except ValueError as e:
            pass

        try:
            print(str(int(lhs) + int(rhs)))
            return 0
        except ValueError as e:
            pass

        try:
            print(str(int(lhs) + int(rhs)))
            return 0
        except ValueError as e:
            pass

        try:
            print(str(int(lhs) + int(rhs)))
            return 0
        except ValueError as e:
            pass

        print("Can only add valid numbers")
        return 2

    return command.Command(
            add,
            "add",
            "add lhs rhs",
            "Add two numbers"
    )

