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
    def __init__(self, *types):
        self.__slots = WeakValueDictionary()

    def __call__(self, *args, **kargs):
        for key in self.__slots:
            func, _ = key
            func(self.__slots[key], *args, **kargs)

    def connect(self, slot):
        key = (slot.im_func, id(slot.im_self))
        self.__slots[key] = slot.im_self

    def disconnect(self, slot):
        key = (slot.im_func, id(slot.im_self))
        if key in self.__slots:
            self.__slots.pop(key)

    def clear(self):
        self.__slots.clear()
