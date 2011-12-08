Debugging StepFuncs with cagen
==============================

Writing StepFuncVisitors can be especially complicated, as you only write parts
of the whole function that are thrown together with completely different pieces
of code.

Fortunately, zasim offers a few methods to make developing both C code and
python code for stepfunctions easier.


Debugging C code
----------------

The environment variable `ZASIM_WEAVE_DEBUG` controls debugging behaviour for
weave code. Setting it to anything ("yes, please", for example), will cause
`weave.inline` to compile the extension with -O0 and be more verbose about
its compilation process.

Setting it to "gdb" will emit a SIGTRAP at the beginnnig of every step, so that
you can attach a gdb or other kind of debugger to the python process and step
through the lines in your generated stepfunc.


Debugging python code
---------------------

The environment variable `ZASIM_PY_DEBUG` controls debugging behaviour for python
code. Setting it to anything will cause `StepFunc.gen_code` to write out the path
to the python file as well as its source code.

Setting it to either "pudb" or "pdb" will cause a pdb/pudb to start at the
beginning of each step, letting you step through the code line by line and inspect
the variables.

