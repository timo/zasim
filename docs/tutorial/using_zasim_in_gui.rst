.. _tutorial_zasim_in_gui:

Using zasim in GUI
==================

Zasim offers a bunch of gui components, as can be seen in its own built-in
gui, but that's not all you can do with it; Most of the functionality is
spread across the components, which are all reusable and mostly decoupled.

In this tutorial we will be developing a tool to play around with `Dual
Rule CA <zasim.cagen.dualrule>`. A dual-rule CA is a nondeterministic
cellular automaton which has two different rules (like an elementary
cellular automaton would) and a probability to decide which rule to apply
to each cell.

The GUI that will be developed has two entry boxes for the rules and a
slider for the probability. There is a display for displaying the cellular
automaton and a button to change the starting configuration.

Mocking up the GUI
------------------

Using PyQt4 or PySide, creating the panel at the top for the sliders and
input boxes is rather simple. Explaining it in detail is beyond the scope
of this documentation, though. This is the code:

