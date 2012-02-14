An overview over zasim
======================

For normal usage, zasim is composed as depicted in this chart:

.. aafig::

    +----------------+----------------+
    | GUI frontend   | CLI frontend   |
    +----------------+----------------+      +---------+
    | "preselected combinations"      |      | IPython |
    +---------------------------------+------+---------+
    |                                                  | z
    | /----------------------------------------------\ | a
    | | Simulator Interface                          | | s
    | +------------------------+---------------------+ | i
    | | "cagen generated code" | "hand-written code" | | m
    | \------------------------+---------------------/ |
    |                                                  |
    | /----------------------------------------------\ |
    | | Painter Interface                            | |
    | +----------+--------------+--------------------+ |
    | | QT based | string based | ipython based      | |
    | \----------+--------------+--------------------/ |
    |                                                  |
    | /----------------------------------------------\ |
    | | Generating Configurations                    | |
    | +--------+------------+------------------------+ |
    | | random | from image | from string            | |
    | \--------+------------+------------------------/ |
    \--------------------------------------------------/

The GUI and CLI frontend offer a selection of simulators with a
selection of parameters that you can specify.

When using IPython, any other interactive shell or just custom python code,
you can access every simulator, write your own, hook them up to different
painters and generate configurations from different sources and plug in
your own custom code for any component.
