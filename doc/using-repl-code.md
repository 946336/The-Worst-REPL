# REPL Documentation

[Index](index.md)

[README](../README.md)

-----------------------------

## Writing Python functions for REPL

Functions written for use with REPL should behave somewhat like functions in a
POSIX shell, though some restrictions are simply convention and not currently
enforced by REPL.

With a few exceptions, your python code can do whatever you want it to, with the
following caveats:

* All arguments are given as strings.
* Like in a POSIX shelll, return values are intended to indicate success or
  failure, with a return value of `0` indicating success and any other value
  indicating failure.

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
This will register the new command as part of the basis of your application. If
you prefer to register the command as a user-level function, use
`REPL.register_user_function()` instead. The only functional difference is that
the user can overwrite user-level commands.

Keep in mind that `callable` can itself be a thin wrapper serving as an
adaptor between the function signature required by REPL and the original
function signature.

If any of `name`, `usage`, of `helptext` are falsy values, `Command` attempts
to extract useful information from `callable` and uses that instead of leaving
them completely blank.

## Interacting with REPL programmatically

It is almost certain that your program will at some point want to interact
with the REPL that the end user is using. REPL allows you to query at least the
following:

* The name of the REPL: `REPL.name`
* The result of invoking the prompt callback: `REPL.prompt`
* Whether or not the REPL has been instructed to stop: `REPL.done`
* The state of variables in the REPL environment: `REPL.get()`
* Whether or not REPL will echo executed commands: `REPL.echo`
* The names of enabled modules `REPL.loaded_modules`

REPL also allows you to make at least the following changes after
initialization:

* You may replace the prompt callback: `REPL.set_prompt()`
* You may register additional commands to the basis: `REPL.register()`
* You may set the values of environment variables: `REPL.set()`
* You may unset the values of environment variables: `REPL.unset()`
* You may register a new command: `REPL.register_user_function()`
* You may remove a function: `REPL.unregister()`
* You may source scripts: `REPL.source()`
* You may toggle whether or not REPL will echo the commands it executes:
  `REPL.set_echo()`
* You may change the default command that is executed when REPL does not
  recognize a command name: `REPL.set_unknown_command()`
* You may add hooks to `REPL.eval()` and `REPL.execute()`:
  `REPL.set_eval_hook()`, `REPL.set_exec_hook()`
* You may set the source from which REPL will take input:
  `REPL.set_input_source()`
* You may set the sink that REPL will write its standard output to:
  `REPL.set_output_sink()`
* You may set the sink that REPL will write its standard error to:
  `REPL.set_error_sink()`

While not prohibited, it is possible to leverage `REPL.eval()` and other
related functions to indirectly execute arbitrary REPL without informing the
user. This is not recommended, and the responsible developer will find another
way to accomplish the same task when possible.

Care should be taken when invoking methods not listed here, as they may have
undesirable side effects if not used correctly.

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

For more details about the default modules, see the [module
documentation](repl-modules.md)

Current modules are:

* debug
* math
* readline
* shell
* text

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
                self.toStdout(self.eval(input(self.prompt).strip("\n")), end = "")
            except TypeError as e:
                self.toStderr("TypeError: " + str(e) + "")
                if self.__debug: raise e
            except RecursionError as e:
                self.toStderr("Maximum recursion depth exceeded")
                if self.__debug: raise e
            except common.REPLBreak as e:
                self.toStderr("Cannot break when not executing a loop")
            except common.REPLReturn as e:
                self.toStderr("Cannot return from outside of function")
            except common.REPLFunctionShift as e:
                self.toStderr("Cannot shift from outside of function")
            except common.REPLError as e:
                self.toStderr("{}".format(str(e)))
    except (KeyboardInterrupt, EOFError) as e:
        self.toStdout()
        return self
    except Exception as e:
        if self.__debug: raise e
        else:
            self.toStderr("{}: {}.format"(str(type(e)), str(e)))
            return self.go()

    return self
```

In particular, if any task needs to be carried out between successive command
invocations that can't be done in one of the provided hooks described below,
that is a strong case to forgo the provided main loop and to roll your own.

## Hooks

REPL provides two hooks: one for `eval` and one for `exec`.

The `eval` hook is invoked once when REPL successfully evaluates a line of
input. It receives the following arguments: the string that was evaluated, the
output it produced, and the result returned.

    self.__eval_hook(string, stdout, self.get("?"))

If you _really_ want to hook into _every single_ command invocation, including
each part of a pipeline or command substitution, you need to hook
`REPL.execute()` instead. The `exec` hook is invoked once when REPL successfully
executes a command. It receives the following arguments: the name of the command
executed, a list of the arguments to that command, the output it produced, and
the result returned.

    self.__exec_hook(command.name, arguments, stdout, self.get("?"))

