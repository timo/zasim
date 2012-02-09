from ..external.qt import *
from .. import cagen
CLASS_OBJECT_ROLE = Qt.UserRole + 1

import inspect

def get_class_for_implementation(meth):
    """Taken from stackoverflow user Alex Martelli."""
    for cls in inspect.getmro(meth.im_class):
        if meth.__name__ in cls.__dict__: return cls
    return None

class StepFuncCompositionDialog(QWidget):
    """With this dialog, the user can, by selecting classes from a categorized
    tree of classes derived from StepFuncVisitor, assemble a step
    function.

    In a later version, the user will also be able to set arguments, such as
    the probability for nondeterministic visitors."""

    single_categories = ["loop", "accessor", "neighbourhood"]
    """The categories that can hold only a single class.

    These correspond closely to the keyword arguments of
    :meth:`StepFunc.__init__` with the same name."""

    def __init__(self, **kwargs):
        super(StepFuncCompositionDialog, self).__init__(**kwargs)

        self.setAttribute(Qt.WA_DeleteOnClose)

        self.parts = {}
        self.extraparts = []

        self.setup_ui()
        self.part_tree.currentItemChanged.connect(self.update_docs)
        self.part_tree.itemActivated.connect(self.dbl_click_item)

        self.cancel_button.clicked.connect(self.close)
        self.create_button.clicked.connect(self.create)

    def update_docs(self, new, old):
        """Display the docstring of the class and its __init__ at the bottom of
        the window when a new class has been selected, or display a general
        help text when the user clicks on something else."""

        obj = new.data(0, CLASS_OBJECT_ROLE)
        if obj is None:
            data = """<h2>Create a stepfunction from parts</h2>

Doubleclick on classes from the list on the left to set them at the right, or
click on the buttons on the right to remove classes again.

Doubleclick on items in the right list of extra classes to remove them.

This pane at the bottom will display documentation."""

        else:
            data = """<h2>%s</h2>
%s""" % (obj.__name__, obj.__doc__)
            try:
                if get_class_for_implementation(obj.__init__) == obj:
                    data += """<h2>Constructor</h2>
    %s""" % (obj.__init__.__doc__)
            except AttributeError:
                pass
        self.doc_display.setText(data)

    def setup_ui(self):
        categories = cagen.categories()

        outermost_layout = QVBoxLayout(self)

        outer_layout = QSplitter(Qt.Vertical, self)
        outermost_layout.addWidget(outer_layout)

        # upper part: list and slots
        upper_widget = QWidget(self)
        upper_pane = QHBoxLayout(upper_widget)
        upper_widget.setLayout(upper_pane)
        outer_layout.addWidget(upper_widget)

        # left pane: list of all available parts
        left_pane = QVBoxLayout()
        self.part_tree = QTreeWidget(upper_widget)
        self.part_tree.setHeaderHidden(True)
        self.part_tree.setObjectName("parts")
        left_pane.addWidget(self.part_tree)

        for (category, classes) in categories.iteritems():
            cat_item = QTreeWidgetItem([category])

            for cls in classes:
                cls_item = QTreeWidgetItem([cls.__name__])
                cls_item.setData(0, CLASS_OBJECT_ROLE, cls)
                cat_item.addChild(cls_item)

            self.part_tree.addTopLevelItem(cat_item)
            self.part_tree.expandItem(cat_item)

        # right pane: selected parts
        right_pane = QGridLayout()
        self.category_buttons = {}
        for num, category in enumerate(self.single_categories):
            label = QLabel(category, self)
            slot = QPushButton(self)
            slot.setObjectName("slot_%s" % category)
            right_pane.addWidget(label, num, 0)
            right_pane.addWidget(slot, num, 1)
            self.category_buttons[category] = slot
        num += 1
        label = QLabel("additionals", self)
        self.additional_list = QListWidget(self)
        self.additional_list.setObjectName("additional_list")
        right_pane.addWidget(label, num, 0, 1, 2)
        right_pane.addWidget(self.additional_list, num + 1, 0, 1, 2)

        # lower part: documentation
        self.doc_display = QTextEdit(self)
        self.doc_display.setReadOnly(True)
        self.doc_display.setObjectName("doc_display")

        outer_layout.addWidget(self.doc_display)

        upper_pane.addLayout(left_pane)
        upper_pane.addLayout(right_pane)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_button = QPushButton("Cancel", self)
        self.cancel_button.setObjectName("cancel")
        self.create_button = QPushButton("Create", self)
        self.create_button.setObjectName("create")

        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.create_button)

        outermost_layout.addLayout(button_layout)
        self.setLayout(outermost_layout)

    def dbl_click_item(self, item, column):
        """When the user activates a class in the list, insert it into the
        correct slot at the right."""

        cls = item.data(0, CLASS_OBJECT_ROLE)
        if cls is None:
            return
        if cls.category in self.single_categories:
            button = self.category_buttons[cls.category]
            button.setText(cls.__name__)
            self.parts[cls.category] = cls
        else:
            self.additional_list.addItem(cls.__name__)
            self.extraparts.append(cls)

    def create(self):
        extra_code = "[%s]" % (", ".join(
            ["%s()" % (cls.__name__) for cls in self.extraparts]))
        generated_code = """
w, h = 200, 200
scale = 3

t = cagen.Target(size=(w, h))
l = %(loop)s()
acc = %(acc)s()
neigh = %(neigh)s()
extra_code = %(extra)s
sim = cagen.StepFunc(loop=l, accessor=acc, neighbourhood=neigh,
                extra_code=[extra_code], target=t)

sim.gen_code()

sim_obj = ElementaryCagenSimulator(sim, t)

display_obj = ZasimDisplay(sim_obj)
display_obj.set_scale(scale)
display_objects.append(display_obj)

display_obj.control.start()""" % dict(
            loop=self.parts["loop"].__name__, acc=self.parts["accessor"].__name__,
            neigh=self.parts["neighbourhood"].__name__, extra=extra_code)

        EditWindow(generated_code).exec_()

class EditWindow(QDialog):
    def __init__(self, code, title="Editing code"):
        super(EditWindow, self).__init__()
        self.setWindowTitle(title)
        self.setup_ui()
        self.edit_widget.setText(code)

        self.run_button.clicked.connect(self.run_code)
        self.cancel_button.clicked.connect(self.rejected)

    def setup_ui(self):
        l = QVBoxLayout(self)
        self.edit_widget = QTextEdit(self)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.run_button = QPushButton("Execute")
        self.cancel_button = QPushButton("Cancel")

        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.run_button)

        l.addWidget(self.edit_widget)
        l.addLayout(button_layout)

        self.setLayout(l)

    def run_code(self):
        exec self.edit_widget.toPlainText() in globals(), locals()
        self.accepted.emit()
        self.close()
