# REPL

The worst REPL you've ever seen.

REPL binds textual commands to python functions and is, at its core, meant to
serve as a scripting language. If you need such an interactive, shell-like
interface, this might work for you.

## Requirements

REPL is being developed and tested on Linux/Python 3.5.

## Examples

We provide sample programs built with REPL, located in `example/`.

#### wrap

Wrap a noninteractive CLI program (such as git) in an interactive session.

#### rule110.py

An implementation of [Rule 110](https://en.wikipedia.org/wiki/Rule_110),
demonstrating that REPL is Turing complete when its builtins and modules are
enabled.

#### webpage-links

An absolutely terrible way to browse the web. Point it at a URL, and it can
extract links from the HTML. You can then point it at those URLs and repeat.

#### bad-math

Recursive and iterative functions for calculating Fibonacci numbers and
factorials. These are functions written and defined in REPL, not in the
underlying Python.

## What REPL _can_ do

* Provide a simple way or users to interact with your prorgram.
* Allow users to invoke your functions without being required to read your
  source code or write their own.
* Give you flexibility in spot-checking and testing code, especially if you're
  testing a backend program with no proper user interface.
* Disable unneeded feature families.

## What REPL _cannot_ do

* Replace a true embedded scripting language like Lua.
* Replace a true shell like bash/fish/zsh/etc.
* Replace an actual user interface.

## Features:

For more details, see the [documentation](doc/index.md).

* Shell-like syntax that will be mostly familiar to users who have experience
  in POSIX shells
* Built-in supoport for a persistent plaintext variable store
* Primitive tab completion for top-level commands using GNU readline
* Built-in help system
* Customizable prompt
* Primitive debugging facilities

## Using REPL

If you are looking to use REPL for your own project, you will want to read
[this](doc/using-repl-code.md).

## Dependencies

REPL has no hard dependencies outside of the Python standard library, but has
the following _optional_ dependencies:

* readline: Required by the `readline` module

## License

REPL is released under the MIT license.

