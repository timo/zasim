# coding: utf-8
"""This module compiles all classes from all submodules for easier and less
verbose importing.


"""
# {LICENSE_TEXT}

# TODO make it extra hard to change the loop variables using a neighbourhood.

# TODO separate the functions to make C code from the ones that do pure python
#      computation

# TODO figure out how the code should handle resizing of configurations and
#      other such things.

# TODO figure out if scipy.weave.accelerate_tools is any good.

from .accessors import *
from .bases import *
from .beta_async import *
from .border import *
from .computations import *
from .loops import *
from .neighbourhoods import *
from .nondeterministic import *
from .simulators import *
from .stats import *
from .stepfunc import *
from .target import *
from .compatibility import *
from .dualrule import *

def categories():
    """Returns a dictionary mapping categories to known classes."""
    all_classes = []
    categories = {}
    look_at = StepFuncVisitor.__subclasses__()

    while len(look_at) > 0:
        item = look_at.pop()
        if item.category not in categories:
            categories[item.category] = []
        categories[item.category].append(item)
        all_classes.append(item)
        look_at.extend([cls for cls in item.__subclasses__() if cls not in all_classes])

    return categories

