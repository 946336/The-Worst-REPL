
from .. import command
from textwrap import dedent
import sys

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
            print("Can only add valid numbers")
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
            print("Can only subtract valid numbers")
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
            print("Can only multiply valid numbers")
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
            print("Can only divide valid numbers")
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
            print("Both operands must be numbers")
            return 2

        return 0 if lhs < rhs else 1

    return command.Command(
        less_than,
        "less-than",
        "less-than lhs rhs",
        dedent("""
            Compare two numbers, returning true if lhs is less than rhs
            """).strip("\n")
    )

def make_greater_than_command():
    def greater_than(lhs, rhs):
        try:
            lhs = number(lhs)
            rhs = number(rhs)
        except ValueError as e:
            print("Both operands must be numbers")
            return 2

        return 0 if lhs > rhs else 1

    return command.Command(
        greater_than,
        "greater-than",
        "greater-than lhs rhs",
        dedent("""
            Compare two numbers, returning true if lhs is greater than rhs
            """).strip("\n")
    )

