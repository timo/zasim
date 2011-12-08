"""This module offers a function to fork a gdb in a terminal and attach it to the
running process, so that weave stepfuncs and other things may be debugged."""

from __future__ import print_function

import os
import subprocess as sp
import sys

def launch_debugger(debugger_binary="gdb", terminal_binary="x-terminal-emulator"):
    os.system("%s -e %s -p %d &" % (terminal_binary, debugger_binary, os.getpid()))

trap_code = "kill(%d, SIGTRAP);" % (os.getpid())

def indent_c_code(code):
    try:
        indent = sp.Popen(["indent", "-kr", "-", "-o", "-"], stdout=sp.PIPE, stdin=sp.PIPE)
        return indent.communicate(code)[0]
    except:
        print("indent failed", file=sys.stderr)
        return code
