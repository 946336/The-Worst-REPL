# REPL Documentation

[Index](index.md)

[README](../README.md)

-----------------------------

## Writing Python functions for REPL

Functions written for use with REPL should behave somewhat like functions in a
POSIX shell, though some restrictions are simply convention and not currently
enforced by REPL.

With a few exceptions, your python code can do whatever you want it to. REPL
does require at least the following in order to work correctly:

* Your function SHOULD return the integer 0 upon success, and any other
  integer value upon failure
* Your function MAY produce output on standard output
* Your function MUST take only string parameters
* Your function MAY take default parameters
* Your function MAY have named parameters
* Your function MUST NOT take aggregate keyword arguments (`**kwargs`)

Because REPL captures the entirety of the output of your functions before
continuing, nothing your function sends to standard output will be displayed
until it terminates.

## Preparing your functions for REPL

REPL does not take bare functions. Instead, it uses a thin wrapper class
called `Command`.

```python
class Command:
    def __init__(self, callable, name = "", usage = "", helptext = ""):
        ...
```

* `callable` is the function that you want REPL to invoke.
* `name` is the name of the function and the name used to invoke the function.
* `usage` is a short usage string, used by the internal help system.
* `helptext` is a more detailed description of the function, used by the
  internal help system.

Usually, a `Command` will be registered to a REPL using `REPL.register()`.
This will register the new command as a user-level function. Currently, if you
wish to add your own builtins or basis to REPL, you must clone or fork this
project and modify that copy instead.

Keep in mind that `callable` can itself be a thin wrapper serving as an
adaptor between the function signature required by REPL and the original
function signature.

## Interacting with REPL programmatically

It is almost certain that your program will at some point want to interact
with the REPL that the end user is using. REPL allows you to query the
following:

* The name of the REPL: `REPL.name`
* The result of invoking the prompt callback: `REPL.prompt`
* Whether or not the REPL has been instructed to stop: `REPL.done`
* The state of variables in the REPL environment: `REPL.get()`
* Whether or not REPL will echo executed commands: `REPL.echo`
* The names of enabled modules

REPL also allows you to make the following types of changes after
initialization:

* You may replace the prompt callback: `REPL.set_prompt()`
* You may register additional commands: `REPL.register()`
* You may set the values of environment variables: `REPL.set()`
* You may register a new command: `REPL.register()`
* You may remove a function: `REPL.unregister()`
* You may source scripts: `REPL.source()`
* You may toggle whether or not REPL will echo the commands it executes:
  `REPL.set_echo()`
* You may change the default command that is executed when REPL does not
  recognize a command name: `REPL.set_unknown_command()`

While not prohibited, it is possible to leverage `REPL.eval()` and other
related functions to indirectly execute arbitrary REPL without informing the
user. This is not recommended, and a responsible developer will find another
way to accomplish the same task.

## REPL.set\_unknown\_command()

This function takes one parameter: a _command factory_. The command factory is
invoked with a single parameter: the name of the command that the user issued,
and is expected to return a command.

The command produced is invoked with a variable number of arguments, dependent
on user input.

## Modules

REPL comes with a few different modules containing various commands that may
be useful but that are likely to be unwanted in many situations. You may
explicitly enable these modules at initialization time using the
`modules_enabled` parameter to `REPL.__init__()`. `modules_enabled` should be
a list of strings, each of which should be the name of a module.

End users may see what modules are enabled with the `modules` command.

Current modules are:

* shell

## Advanced Usage

In a more advanced application, the main loop provided as `REPL.go()` and
reproduced below may not be sufficient or appropriate. In such cases, it may
be more convenient for you to write your own loop than to attempt to embed
application-specific logic into the limited callback space REPL provides.

```python
# class REPL:
    def go(self):
        try:
            while not self.done:
                try:
                    self.eval(input(self.prompt).strip("\n"))
                except common.REPLError as e:
                    print(e)
                except TypeError as e: # Bad command invocation
                    print(e)
        except (KeyboardInterrupt, EOFError) as e: # Exit gracefully
            print()
            return
        except Exception as e: # Attempt to keep running
            print(e)
            self.go
```

In particular, if any task needs to be carried out between successive command
invocations, that is a strong case to forgo the provided main loop and to roll
your own.

**Note**

If you _really_ want to hook into _every single_ command invocation, including
each part of a pipeline or command substitution, you need to hook
`REPL.execute()` instead.

