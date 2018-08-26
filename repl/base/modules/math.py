
from .. import command
import sys

def commands():
    return [
            make_addition_command(),
            make_subtraction_command(),
            make_multiply_command(),
            make_divide_command(),
            make_less_than_command(),
            make_greater_than_command(),
            make_equal_command(),
            make_increment_command(),
            make_decrement_command()
            ]

def number(arg):
    if type(arg) in [int, float]:
        return arg

    try:
        return int(arg)
    except ValueError as e:
        return float(arg)

def make_addition_command():

    def add(lhs, rhs):
        try:
            print(str(number(lhs) + number(rhs)))
        except ValueError as e:
            sys.stderr.write("Can only add valid numbers\n")
            sys.stderr.write("{} + {}\n".format(lhs, rhs))
            return 2
        return 0

    return command.Command(
            add,
            "add",
            "add lhs rhs",
            "Add two numbers"
    )

def make_subtraction_command():

    def subtract(lhs, rhs):
        try:
            print(str(number(lhs) - number(rhs)))
        except ValueError as e:
            sys.stderr.write("Can only subtract valid numbers\n")
            return 2
        return 0

    return command.Command(
            subtract,
            "subtract",
            "subtract lhs rhs",
            "subtract rhs from lhs"
    )

def make_multiply_command():

    def multiply(lhs, rhs):
        try:
            print(str(number(lhs) * number(rhs)))
        except ValueError as e:
            sys.stderr.write("Can only multiply valid numbers\n")
            return 2
        return 0

    return command.Command(
            multiply,
            "multiply",
            "multiply lhs rhs",
            "multiply two numbers"
    )

def make_divide_command():

    def divide(lhs, rhs):
        try:
            print(str(number(lhs) / number(rhs)))
        except ValueError as e:
            sys.stderr.write("Can only divide valid numbers\n")
            return 2
        return 0

    return command.Command(
            divide,
            "divide",
            "divide lhs rhs",
            "divide two numbers"
    )

def make_less_than_command():
    def less_than(lhs, rhs):
        try:
            lhs = number(lhs)
            rhs = number(rhs)
        except ValueError as e:
            sys.stderr.write("Both operands must be numbers\n")
            return 2

        return 0 if lhs < rhs else 1

    return command.Command(
        less_than,
        "less-than",
        "less-than lhs rhs",
        command.helpfmt("""
            Compare two numbers, returning true if lhs is less than rhs
            """)
    )

def make_greater_than_command():
    def greater_than(lhs, rhs):
        try:
            lhs = number(lhs)
            rhs = number(rhs)
        except ValueError as e:
            sys.stderr.write()("Both operands must be numbers\n")
            return 2

        return 0 if lhs > rhs else 1

    return command.Command(
        greater_than,
        "greater-than",
        "greater-than lhs rhs",
        command.helpfmt("""
            Compare two numbers, returning true if lhs is greater than rhs
            """)
    )

def make_equal_command():
    def eq(lhs, rhs):
        return 0 if number(lhs) == number(rhs) else 1

    return command.Command(
            eq,
            "equal",
            "equal lhs rhs",
            command.helpfmt("""
                Compare two numbers for equality
                """)
            )

def make_increment_command():
    def inc(n, step = 1):
        try:
            n = number(n)
        except ValueError as e:
            sys.stderr.write("Can only increment valid numbers\n")
            return 2
        print(n + step)
        return 0

    return command.Command(
            inc,
            "increment",
            "increment number [step]",
            command.helpfmt("""
                Increment a number by 1 (default) or by a set step amount
                """)
            )

def make_decrement_command():
    def dec(n, step = 1):
        try:
            n = number(n)
        except ValueError as e:
            sys.stderr.write("Can only decrement valid numbers\n")
            return 2
        print(n - step)
        return 0

    return command.Command(
            dec,
            "decrement",
            "decrement number [step]",
            command.helpfmt("""
                Decrement a number by 1 (default) or by a set step amount
                """)
            )

