from ..external.qt import (QDialog, QWidget,
        QHBoxLayout, QVBoxLayout, QGridLayout,
        QGroupBox, QLabel,
        QCheckBox, QLineEdit,
        QDialogButtonBox,
        app)

import argparse as ap


class ArgparseWindow(QDialog):
    """This dialog takes an argparser as initialiser and returns an args
    object just like argparse does."""

    action_widgets = {}
    """A dictionary mapping an argparse action object to a tuple of
    1. either None or a QCheckBox, that can toggle the switch
    2. a QLineEdit or QCheckbox, that can set the value of the switch
    """

    taken_dests = set()
    """What "dest" values are already taken."""

    arguments = []
    """What the commandline looked like the last time it was updated."""

    def __init__(self, argparser, arguments=None, **kwargs):
        super(ArgparseWindow, self).__init__(**kwargs)

        self.argp = argparser
        if arguments:
            self.arguments = arguments
        else:
            self.arguments = {}

        self.setup_ui()

    def _widget_with_checkbox(self, widget, label_text, help_text):
        cont = QWidget(parent=self)
        box = QCheckBox(label_text, parent=self)

        box.toggled.connect(widget.setEnabled)
        box.toggled.connect(self.update_cmdline)

        widget.setEnabled(False)

        outer = QVBoxLayout()

        layout = QHBoxLayout()
        layout.addWidget(box)
        layout.addWidget(widget)

        outer.addLayout(layout)
        label = QLabel(help_text)
        label.setWordWrap(True)
        outer.addWidget(label)

        cont.setLayout(outer)

        return cont, box

    def build_action_widget(self, action):
        if isinstance(action, (ap._StoreTrueAction, ap._StoreFalseAction)):
            w = QWidget(parent=self)
            cont, box = self._widget_with_checkbox(w, action.dest, action.help)
            if action.dest in self.arguments:
                if isinstance(action, ap._StoreTrueAction):
                    box.setChecked(self.arguments[action.dest])
                else:
                    box.setChecked(not self.arguments[action.dest])
            else:
                    box.setChecked(action.default)

        elif isinstance(action, ap._StoreAction):
            w = QLineEdit()
            if action.dest in self.arguments:
                w.setText(unicode(self.arguments[action.dest]))
            if action.default:
                w.setText(unicode(action.default))
            cont, box = self._widget_with_checkbox(w, action.dest, action.help)
            w.textChanged.connect(self.update_cmdline)

        elif isinstance(action, ap._HelpAction):
            return None

        else:
            print "error"
            print "could not build a widget for ", action
            return None


        self.action_widgets[action] = (box, w)
        self.taken_dests.update([action.dest])
        return cont

    def build_action_group(self, ag):
        w = QGroupBox(ag.title)

        widgets = []

        for action in ag._actions:
            if action in self.action_widgets or action.dest in self.taken_dests:
                continue
            widget = self.build_action_widget(action)
            if widget:
                widgets.append(widget)

        layout = QGridLayout()

        for row, (left, right) in enumerate(zip(widgets[::2], widgets[1::2])):
            layout.addWidget(left, row, 0)
            layout.addWidget(right, row, 1)

        if len(widgets) % 2 != 0:
            layout.addWidget(widgets[-1], row + 1, 0)

        w.setLayout(layout)

        if not widgets:
            w.deleteLater()
            return None
        return w

    def setup_ui(self):
        layout = QVBoxLayout()

        self.cmdline = QLineEdit()
        # XXX this could 'easily' be set to false with appropriate calls to
        #     self.argp.parse_args etc.
        self.cmdline.setReadOnly(True)
        layout.addWidget(self.cmdline)

        for group in self.argp._action_groups:
            group = self.build_action_group(group)
            if group:
                layout.addWidget(group)

        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttonbox.accepted.connect(self.try_accept)
        buttonbox.rejected.connect(self.reject)

        layout.addWidget(buttonbox)

        self.setLayout(layout)

    def update_cmdline(self):
        arguments = []
        for action, (box, widget) in self.action_widgets.iteritems():
            checked = box.isChecked()
            if isinstance(action, ap._StoreFalseAction):
                active = not checked
            else:
                active = checked

            if active:
                if isinstance(widget, QLineEdit):
                    arguments.extend([action.option_strings[-1], widget.text()])
                else:
                    arguments.extend([action.option_strings[-1]])

        self.arguments = arguments
        self.cmdline.setText(" ".join(
            [arg if " " not in arg else arg.replace(" ", '" "') for arg in self.arguments]))

    def try_accept(self):
        self.argp.parse_args(self.arguments)

if __name__ == "__main__":
    argp = ap.ArgumentParser(
        description="Run a 1d BinRule, a 2d Game of Life, or a 2d elementary "
                    "cellular automaton")
    argp.add_argument("--onedim", default=False, action="store_true",
            help="generate a one-dimensional cellular automaton")
    argp.add_argument("--twodim", default=True, action="store_false", dest="onedim",
            help="generate a two-dimensional cellular automaton")
    argp.add_argument("--life", default=False, action="store_true",
            help="generate a conway's game of life - implies --twodim")

    argp.add_argument("-x", "--width", default=200, dest="width", type=int,
            help="the width of the image surface")
    argp.add_argument("-y", "--height", default=200, dest="height", type=int,
            help="the height of the image surface")
    argp.add_argument("-z", "--scale", default=3, dest="scale", type=int,
            help="the size of each cell of the configuration")
    argp.add_argument("-r", "--rule", default=None, type=str,
            help="the elementary cellular automaton rule number to use")
    argp.add_argument("-R", "--alt-rule", default=None, type=str,
            help="the alternative rule to use. Supplying this will turn nondet into dual-rule mode")
    argp.add_argument("-c", "--dont-copy-borders", default=True, action="store_false", dest="copy_borders",
            help="copy borders or just read zeros?")
    argp.add_argument("--black", default=None, type=float,
            help="what percentage of the cells to make black at the beginning. (between 2 and 100 or 0.0 and 1.0)")

    argp.add_argument("--nondet", default=100, type=float,
            help="with what percentage should cells be executed? (either between 2 and 100 or 0.0 and 1.0)")
    argp.add_argument("--beta", default=100, type=float,
            help="with what probability should a cell succeed in exposing its "\
                 "state to its neighbours? (either between 2 and 100 or 0.0 and 1.0)")

    argp.add_argument("--no-histogram", default=True, action="store_false", dest="histogram",
            help="don't display a histogram")
    argp.add_argument("--no-activity", default=True, action="store_false", dest="activity",
            help="don't display the activity")
    argp.add_argument("--base", default=2, type=int,
            help="The base of the cells.")

    argp.add_argument("--sparse", default=False, action="store_true",
            help="should a sparse loop be created?")

    args = argp.parse_args()

    win = ArgparseWindow(argp, vars(args))
    win.show()

    app.exec_()
