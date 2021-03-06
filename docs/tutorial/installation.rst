Installing zasim and its dependencies
=====================================

Prerequisites
-------------

The only dependency beyond Python 2.6 or Python 2.7 [1]_ that you cannot use
zasim without is `NumPy`_, which it uses extensively for its array class.

Beyond that, to run stepfuncs compiled to C code, you need `SciPy`_ for its
weave module. This also adds the requirement of a C++ compiler, such as the
one from `GCC`_.

For the graphical user interface, you need `PySide`_, nokias Qt bindings
for Python. PyQt is, in theory, api-compatible, but the code is currently
only tested with PySide and is not guaranteed to work with PyQt.

There is a tutorial based on the `IPython notebook`_ and there is additional
support for the `IPython qtconsole`_.

If you have the `GNU indent`_ tool installed, generated C code will be a lot
more pretty to look at and thus quite a bit easier to debug, if you run
into trouble with self-made code.

.. [1] Almost the same subset of zasim you get if you have neither SciPy
       nor PySide is also usable with pypy 1.8 or newer.

.. _NumPy: http://numpy.org
.. _SciPy: http://scipy.org
.. _GCC: http://gcc.gnu.org
.. _PySide: http://pyside.org
.. _GNU indent: http://indent.isidore-it.eu/beautify.html
.. _IPython notebook: http://ipython.org/ipython-doc/stable/interactive/htmlnotebook.html
.. _IPython qtconsole: http://ipython.org/ipython-doc/stable/interactive/qtconsole.html


Installing zasim
----------------

From a git checkout
^^^^^^^^^^^^^^^^^^^

After checking out the git repository, you can just run - as root or in a
virtualenv -

    $ python setup.py develop

which will create a link to zasim in your global site-packages repository.

Whenever names of packages or modules change in the git repository, you
should re-run the above command, else you may get error messages about
failing imports.

Running without an installation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can also run zasim without installing it, just from the extracted
source tree. In order for this to work, just cd into the directory you
extracted zasim to. This folder should contain the setup.py and a zasim
folder.

