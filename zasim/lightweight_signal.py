"""
File:    lightweight_signal.py
Author:  Thiago Marcos P. Santos
Created: August 28, 2008

Purpose: A signal/slot implementation

This code was taken from http://code.activestate.com/recipes/576477/
It's supposed to serve as a drop-in replacement for PyQt/PySide Signals.

Modifications have been made to it to make them behave more like Signals from
Qt4.
"""

from weakref import WeakValueDictionary


class Signal(object):
    """A lightweight Signal class when Qt is not installed."""
    def __init__(self, *types):
        """Create the Signal object. The type signatures are ignored."""
        self.__slots = WeakValueDictionary()

    def emit(self, *args, **kwargs):
        """Emit the signal, call all slots that are connected."""
        for key in self.__slots:
            func, _ = key
            func(self.__slots[key], *args, **kwargs)

    def connect(self, slot):
        """Connect this signal to a slot."""
        key = (slot.im_func, id(slot.im_self))
        self.__slots[key] = slot.im_self

    def disconnect(self, slot):
        """Disconnect this signal from a slot."""
        key = (slot.im_func, id(slot.im_self))
        if key in self.__slots:
            self.__slots.pop(key)
