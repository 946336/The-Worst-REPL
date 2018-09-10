#!/usr/bin/env python3

import sys

from repl import repl
from repl.base import common

if __name__ == "__main__":
    r = repl.REPL(
        "bad-math",
        modules_enabled = ["readline", "math", "text"],
    )

    r.go()

