# How REPL Works

[Index](index.md)

[README](../readme.md)

-----------------------

From 10,000 Feet
================

REPL does exactly what it says on the box. Doing anything involves three steps:
reading input, evaluating it, and printing the results for the world to see.
Predictably, almost all of the actual work falls under the umbrella of
"evaluation."

Reading Input
=============

REPL takes its input from a single source, usually the keyboard. While it is
possible to change that, commands that rely on detecting end of input, like the
builtin `cat` will behave erratically if you do so.

There's not a lot of customization to be done here, and there's not likely to be
a whole lot of tweaking around this part of REPL. However, if you wish to play
around, the following are good places to start looking:

* `REPL.set_input_source()`
* `REPL.set_output_sink()`
* `REPL.set_error_sink()`
* `REPL.input()`
* `REPL.toStdoutEager()`
* `REPL.toStdoutLazy()`
* `REPL.toStdout()`
* `REPL.toStderr()`
* `REPL.go()`

Evaluating Input
================

Evaluation is roughly split into two stages: tokenizing and executing. In REPL,
execution involves some things that may not fall under the typical definition of
the word, but that certainly don't fall under tokenizing.

----------------------------------------

For tokenizing, start with `syntax.split_whitespace()`, which is quite possibly
the single most poorly named function in the entire REPL project. For reference,
I, the author, don't really remember how it works aside from the fact that a
nonessential feature straight-up _doesn't_ work: You can't use the backslash to
escape characters that have special meaning to REPL, but you were supposed to be
able to.

* `syntax.split_whitespace()`

----------------------------------------

For evaluation, your starting points are the following:

* `REPL.eval()`
* `REPL.execute()`

`REPL.eval()` evaluates starting from a single string holding a line of input
and handles, for the most part, tokenizing its input into a single command and
its arguments. `REPL.eval()` then defers to `REPL.execute()`, which finally
executes the command.

`REPL.execute()` does a lookup to determine what `Command` was requested, and
invokes it with the arguments it was handed. `REPL.execute()` also handles
capturing output and setting the result variable `$?`.

Unfortunately, that was it for the easy parts and the parts that made any sense
at all. From here on, it gets nasty fast. I cannot possibly document everything
correctly, but I can give you some pointers.

You must be wary of pipelines and subshell expansions whenever you make a change
to the evaluation process, as these both do evaluation behind the scenes.

* `REPL.do_pipelines()`
* `REPL.expand_subshells()`

You also have to be wary of any and all language features like REPL's keywords
and block constructs, which cause deferred evaluation of input. Most, if not
all, of these features must separately invoke one of `REPL.eval()` and
`REPL.execute()`, as well as take care of the associated busywork involved in
settings up for and cleaning up after these functions.

* `Function`
* `Loop`
* `Conditional`
* REPL keywords (`keywords`)

