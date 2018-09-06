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

Note that the backslash _is not_ used to escape special characters in REPL.
Instead, special characters must be quoted to suppress their normal behavior.

## Default Offerings

The rest of this page is devoted to explaining what a reasonably uncustomized
`REPL` instance provides to the end user.

#### Variables

You may set and unset variables.

    (test) >>> set name value
    (test) >>> unset name

If a variable `hello` is set, `$hello` will expand to its value.

    (test) >>> set hello there
    (test) >>> echo $hello
    there
    (test) >>> set there ", there "
    (test) >>> echo hello${there}user
    hello, there user

Variable names must match the following regex: `$[A-Za-z_0-9?#@-][A-Za-z0-9_-]*`

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
commands. The `help` command taps into that.

    (test) >>> help echo
    Usage: echo [ args ]
    Write arguments to standard output

REPL also provides a command to list all available commands.

    (test) >>> help list
    Usage: list {builtins, basis, functions, aliases, all}
    List available commands in one or all categories
    (test) >>> list all
    ...

There is currently no mechanism for providing customized help for subcommands.

#### Aliases

REPL allows you to create aliases for commands.

Currently, these aliases are significantly less powerful than those of `tcsh` or
even `bash`: You may only introduce a new name for an existing command.

    (test) >>> alias newname oldname

**Note**

The default name resolution order for commands is `aliases`, `functions`,
`basis`, and finally `builtins`. Prefixing the command name with a backslash
(`\`) reverses REPL's lookup order for that command, potentially allowing you
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

REPL uses dotfiles for startup configuration. Which dotfile is used by default
depends on the name given to the REPL, but the filename can be overridden. For
example, if the REPL is given the name "test", the file `.testrc` will be used
as the dotfile. Dotfiles are sourced before control is returned to the user.

Note that the `REPL` constructor takes an optional parameter `dotfile_root`,
which controls where `REPL` will look for its dotfiles.

Dotfiles are sourced at startup (unless this behavior is suppressed by the
application), and are useful for doing setup work.

## Builtins

REPL provides the following builtins by default:

    (test) >>> list builtins
    alias
    cat
    config
    echo
    echoe
    env
    exceptions
    exit
    false
    help
    list
    modules
    not
    set
    set-local
    sleep
    slice
    source
    true
    unalias
    undef
    unset
    verbose

Of particular note is `exit`, which doesn't force the REPL to exit, but rather
sets a boolean flag in the REPL object to indicate that the user has decided to
stop the REPL.

REPL's `cat` is not useful, and is strictly less powerful than POSIX `cat`.
REPL `cat` will _only_ copy standard input to standard output, and does not
take any arguments.

## Keywords

REPL recognizes a few keywords, which take precedence over any other command.
These can be disabled by passing `True` to the `REPL` constructor for the
keyword argument `nokeyword`.

    break
    function
    help
    if
    quit
    return
    shift
    time
    while

`function`, `if`, and `while` are described below.

* `break`: Stops the execution of a loop, jumping to the command immediately
  following the end of the loop body.
* `help`: This is a near exact clone of the `help` command that is provided by
  default.
* `quit`: The `done` command is an alias for this keyword. `quit` sets the
  `REPL.done` flag.
* `return` Causes the execution of a function to stop, and sets `$?` to its
  first argument
* `shift`: Shift all function arguments forward by one. Named parameters are
  unset from first to last.
* `time`: Time the execution of a command.

## Modules

The developer of a REPL application may choose to enable any number of modules
that are provided by REPL but not enabled by default. You can see a list of
enabled modules using the `modules` command.

[Module Documentation](repl-modules.md)

## Functions

REPL allows you to define your own functions by composing existing
functionality.

    (test) >>> function greet
    (test/greet) ... echo Hello, $1!
    (test/greet) ... endfunction
    (test) >>> greet Justin
    Hello, Justin!

You may not define nested functions.  Positional parameters are designated `$1`,
`$2`, etc. `$0` is the function's name, `$#` is the total number of
arguments the function was given, and `$@` is the space-separated concatenation
of all arguments.

You may return a specific value by using the `return` command, but you may not
return the value of an expression.

Inside a function, positional arguments are bound successively to `$1`, `$2`,
etc. The function name is additionally  bound to `$FUNCTION`. `$#` and `shift`
work much the same way as in bash.

To avoid the risk of changing variables in an enclosing scope, use `set-local`
to set variables within functions.

If a function is declared with parameters, as below, then the arguments are
available under the corresponding names, and REPL will not execute the
function unless exactly that many arguments are supplied. For these named
parameters, `shift` incrementally unsets parameters starting from the first.
Note that the numbered positionals will still be unset from the end.

    (test) >>> function quote str
    (test/quote) ... echo "'$str'"
    (test/quote) ... endfunction

There is currently no way to express a function signature with a variable
number of arguments if any are named.

## Conditional logic

REPL has a mechanism for conditional branching in the form of `if`/`elif`/`else`
statements.

    (test) >>> if true
    (test/Conditional) ... echo First branch taken
    (test/Conditional) ... elif false
    (test/Conditional) ... echo Second branch taken
    (test/Conditional) ... else
    (test/Conditional) ... echo Last branch taken
    (test/Conditional) ... endif
    First branch taken

Expressions following `if` and `elif` keywords are evaluated in order, and the
first to evaluate to success (`0`) causes its corresponding block to be
executed. The block corresponding to an `else` keyword will be executed if no
preceding test succeeds. If no test succeeds and there is no `else` block,
nothing happens.

## Loops

REPL provides a single type of loop in the form of the `while` loop.

    (test) >>> set i 0
    (test) >>> while less-than $i 5
    (test/Loop) ... echo i is $i
    (test/Loop) ... set i `add 1 $i`
    (test/Loop) ... done
    i is 0
    i is 1
    i is 2
    i is 3
    i is 4

The expression following the `while` keyword is the loop condition, and is
evaluated once at the beginning of each loop iteration.

**Note**

`less-than` and `add` are builtins from the `math` module, and are not available
by default.

## Debugging

**Note** This is part of the module `debug`, but is documented here because in
theory, it is important enough to warrant it.

REPL provides a very rudimentary debugging tool: `debug`. Issuing the `debug`
command interrupts execution and drops into an interactive session where, in
addition to all of the usual commands, additional debugging commands are
available. Execution resumes when the debugging session is ended.

At this time, the only debugging tool provided is the ability to see a
rudimentary stacktrace, using any of the `stack`, `backtrace`, `bt`, or `where`
commands in a debug session.

    (test) >>> function a
    (test/a) ... debug
    (test/a) ... endfunction
    (test) >>> function b
    (test/b) ... a
    (test/b) ... endfunction
    (test) >>> function c
    (test/c) ... b
    (test/c) ... endfunction
    (test) >>> c
    DEBUG >>> stack
    Traceback (Most recent call last):
    c:1
    b:1
    a:1

There is currently no way to customize the debugging prompt.

## Timing

REPL provides low-precision timing capabilities in the form of the `time`
command, which reports the CPU time taken to execute a command.

    (test) >>> time sleep 2
    Time elapsed: 2.0025s

## Stretch Goals:

* Canned support for communication over sockets, websockets, OS pipes, etc
* Configurable, rudimentary, read-only filesystem access
* Types: Array types
* User-provided help text and usage lines for functions
* Useful prompt variables
* Parameter expansion
* More canned modules/libraries
* Initialization-time/runtime loading of canned modules/libraries by name

