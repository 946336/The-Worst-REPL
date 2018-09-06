# REPL

The worst REPL you've ever seen.

REPL is a simple framework for building simple interactive applications.

REPL provides a simple way to bind textual commands to python functions. If
you need an interactive, shell-like interface, this might work for you.

This is not an out-of-the-box solution, and it is certainly not intended to
replace a full domain-specific language. In its current state, REPL is more of
an interactive console than anything else.

## Requirements

REPL is being developed and tested on Linux/Python 3.5.

## Example

We provide sample applications built with REPL, located in `example/`. Try
them out!

## What REPL _can_ do

* Provide a simple way or users to interact with your application.
* Allow users to invoke your functions without being required to read your
  source code or write their own.
* Give you flexibility in spot-checking and testing code, especially if you're
  testing a backend application with no proper user interface.

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

