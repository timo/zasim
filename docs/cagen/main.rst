:mod:`zasim.cagen.main` - Running cagen as a program
====================================================

.. seealso::

    The tutorial section has a :ref:`chapter on invoking zasim from the
    commandline <tutorial_invocation>`.

Running this module from the commandline
----------------------------------------

Either invoke the module like this

.. command-output:: python -m zasim.cagen.main --help
  :shell:

or use the launcher script, that was installed on your system with the zasim
package:

.. command-output:: zasim_cli --help
  :shell:
  :ellipsis: 5

One example usage:

.. command-output:: zasim_cli -x 80 -r 126 --print-rule -s 30 --pure

API Documentation
-----------------

.. automodule:: zasim.cagen.main
