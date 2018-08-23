# REPL Modules

[Index](index.md)

[README](../readme.md)

-------------------------

REPL provides a number of modules. When enabled, modules add additional
builtin functions and may introduce new aliases.

## shell

The `shell` module provides one command `shell` and one alias `!` to `shell`.

**shell**

`shell` passes its arguments to an underlying operating system shell.

## math

The `math` module provides several mathematical functions and relational
predicates.

    add            lhs   rhs
    subtract       lhs   rhs
    multiply       lhs   rhs
    divide         lhs   rhs
    less-than      lhs   rhs
    greater-than   lhs   rhs
    equal          lhs   rhs
    increment      number
    decrement      number

## debug

The `debug` module provides debugging tools. See [here](index.md#Debugging).

## readline

This module attempts to enbable readline, for a better interactive experience.

## text

This module provides text-centric utilities, including a few regex based ones.

    regex-match     pattern [strings...]
    regex-capture   pattern [strings...]
    regex-replace   pattern replacement [strings...]

The above are regex based commands that fairly directly forward their arguments
to their python equivalents.

    length string

`length` prints the length of a string

    devnull

Like `cat`, `devnull` accepts input. However, `devnull` silently discards the
input it receives.

