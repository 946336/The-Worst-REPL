#!/usr/bin/env python3

from repl import repl

repl.REPL("test", modules_enabled = ["shell", "readline", "math", "debug",
    "text"],
        debug = True).go()

