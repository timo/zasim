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

.. [1] The same subset of zasim you get if you have neither SciPy nor
       PySide is also usable with pypy 1.6 or newer.

.. _ NumPy: http://numpy.org
.. _ SciPy: http://scipy.org
.. _ GCC: http://gcc.gnu.org
.. _ PySide: http:/pyside.org


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

