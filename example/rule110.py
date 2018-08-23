#!/usr/bin/env python3

from repl import repl

if __name__ == "__main__":
    repl.REPL(
        application_name = "Rule 110",
        modules_enabled = ["readline", "math", "text"],
        dotfile_prefix = "rule110"
    ).go()

