# REPL User Guide

[README](../README.md)

-----------------------------

This is a guide to REPL syntax and its builtin functions. If you are looking
to integrate REPL into another project, see [this page](using-repl-code.md).

If you are looking to help develop REPL itself, see [this
page](how-repl-works.md).

-----------------------------

Most of REPL boils down to the following:

    command [arguments...]
    # This is a comment

REPL provides the following shell-like behavior:

The backslash _is not_ used to escape special characters in REPL. Instead,
special characters must be quoted to suppress their normal behavior.

#### Variables

You may set and unset variables.

    (test) >>> set name value
    (test) >>> unset name

If a variable `hello` is set, `$hello` will expand to its value.

    (test) >>> set hello there
    (test) >>> echo $hello
    there
    (test) >>> set there ", there"
    (test) >>> echo hello${there}
    hello, there

Variable names must match the following regex: `[A-Za-z0-9_?][A-Z-a-z0-9_]*`

**Note:** Special variables

REPL has the following special variables:

`$?`: This is the return value of the last executed command.

`$0`: On startup, this is set to the name of the REPL instance.

#### Parameter Substitution

If a command is enclosed within backticks (\`), it is replaced by the output
it produces when run.

    (test) >>> echo `echo hello`
    hello

#### Persistent Configs Variables

REPL can make use of an external plaintext store for names and values. You may
interact with it with the `config` command and its subcommands, which do what
you think they do.

**Subcommands**

* set
* unset
* list

        (test) >>> config set name value
        (test) >>> config unset name
        (test) >>> config list

#### Sourcing

REPL can read a file and run its contents in the current session.

    (test) >>> source .replrc

#### Help

Among other things, REPL has a framework for attaching documentation to
commands.

    (test) >>> help echo
    Usage: echo [ args ]
    Write arguments to standard output

REPL also provides a command to list all available commands.

    (test) >>> help list
    Usage: list {builtins, basis, functions, aliases, all}
    List available commands in one or all categories
    (test) >>> list all
    ...

#### Aliases

REPL allows you to create aliases for commands.

Currently, these aliases are significantly less powerful than those of `tcsh` or
even `bash`: You may only introduce a new name for an existing command.

    (test) >>> alias newname oldname

**Note**

The default name resolution order for commands is `aliases`, `functions`,
`basis`, and finally `builtins`. Prefixing the command name with a backslash
(\\) reverses REPL's lookup order for that command, potentially allowing you
to access a command that has been shadowed.

    (test) >>> echo list
    list
    (test) >>> alias echo help
    (test) >>> echo list
    Usage: list {builtins, basis, functions, aliases, all}
    List available commands in one or all categories
    (test) >>> \echo list
    list

#### Pipes

REPL supports pipelining standard output with the pipe character (|)

    (test) >>> echo hello | cat | cat | cat
    hello

**Note**

An important implementation detail for pipes here is that pipelines are
executed serially rather than in parallel. In practice, this means that users
should avoid long pipelines that transfer large amounts of data, as that data
must all live in memory at once.

#### Quoting

REPL supports two types of quotes: single quotes (') and double quotes (").
Like in many shells, Variable expansion does not take place within single
quotes, but does take place inside of double quotes.

    (test) >>> echo "$hello"
    world
    (test) >>> echo '$hello'
    $hello

Both types of quotes also prevent parameter substitution and pipelining from
taking place.

    (test) >>> echo "echo `echo hello` | cat"
    echo `echo hello` | cat
    (test) >>> echo 'echo `echo hello` | cat'
    echo `echo hello` | cat

#### Configurable dotfile name for startup

REPL uses dotfiles for startup configuration. Which dotfile is used depends on
the name given to the REPL. For example, if the REPL is given the name "test",
the file `.replrc` will be used as the dotfile. Dotfiles are sourced before
control is returned to the user.

## Builtins

REPL provides the following builtins by default:

    (test) >>> list builtins
    help
    echo
    list
    config
    set
    unset
    cat
    env
    alias
    unalias
    slice
    exit
    quit
    source
    sleep
    verbose
    modules

Of note are `quit` and `exit`, which don't force the REPL to exit, but rather
set a boolean flag in the REPL object to indicate that the user has decided to
stop the REPL.

REPL's `cat` is not useful, and is strictly less powerful than POSIX `cat`.
REPL `cat` will _only_ copy standard input to standard output, and does not
take any arguments.

## Modules

The developer of a REPL application may choose to enable any number of modules
that are provided by REPL but not enabled by default. You can see a list of
enabled modules using the `modules` command.

[Module Documentation](repl-modules.md)

## Functions

REPL allows you to define your own functions by composing existing
functionality.

```
(test) >>> function greet
(test/greet) ... echo Hello, $1!
(test/greet) ... endfunction
(test) >>> greet Justin
Hello, Justin!
```

You may not define nested functions, and REPL does not have flow control.
Positional parameters are designated `$1`, `$2`, etc. `$0` is the function's
name, and `$#` is the total number of arguments the function was given.

You may return a specific value by using the `return` command.

Inside a function, positional arguments are bound successively to `$1`, `$2`,
etc. The function name is bouond bound to `$FUNCTION`. `$#` and `shift` work
much the same way as in bash.

Unless assigning to a variable that was set in an enclosing scope, variables
created inside of a function are function local.

## Stretch Goals:

* Canned support for communication over sockets, websockets, OS pipes, etc
* Configurable, rudimentary, read-only filesystem access
* Flow control: Conditional statements
* Flow control: Loops
* Flow control: User-defined functions
* Types: Array types
* User-provided help text and usage lines for functions
* Useful prompt variables
* Parameter expansion
* Canned modules/libraries
* Initialization-time/runtime loading of canned modules/libraries by name

