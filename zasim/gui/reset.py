from ..external.qt import *
from .elementary import CellDisplayWidget, EditableCellDisplayWidget
from ..display.qt import make_palette_qc

from ..config import BaseRandomConfiguration, PatternConfiguration

class_to_resetter = {}
def reg_resetter(base_class):
    def register_func(cls):
        class_to_resetter[base_class] = cls
        return cls
    return register_func

class BaseResetter(QWidget):
    def __init__(self, mainwin, **kwargs):
        super(BaseResetter, self).__init__(**kwargs)

        self._mw = mainwin
        self._sim = self._mw.simulator
        if "colors_qc" not in self._sim.palette_info:
            self._sim.palette_info["colors_qc"] = make_palette_qc(self._sim.palette_info["colors32"])
        self.sim_palette = self._sim.palette_info["colors_qc"]

        self.values = self._sim.t.possible_values

        try:
            if self._sim._target._reset_generator is not None:
                self.take_over_settings(self._sim._target._reset_generator)
        except:
            pass

        self.setup_ui()
        self.set_values()

    def setup_ui(self):
        """This method sets up the widgets that the user can manipulate to
        generate different kinds of configurations."""

    def set_values(self):
        """This method changes the widgets to represent the internal state
        of the Resetter."""

    def take_over_settings(self, configuration=None):
        """Either take over the settings of another configurator or reset
        the settings to the last used configurator."""

    def generate_generator(self):
        """Generate a matching configuration generator from the settings."""

@reg_resetter(BaseRandomConfiguration)
class BaseRandomConfigurationResetter(BaseResetter):
    perc_widgets = {}

    friendly_name = "Random Configuration"

    setting_values = False

    def take_over_settings(self, configuration=None):
        if configuration:
            self.original_configuration = configuration
        else:
            configuration = self.original_configuration

        self.values = configuration.values
        self.percs = list(configuration.percentages)

    def setup_ui(self):
        whole_layout = QVBoxLayout()
        for index, value in enumerate(self.values):
            side_by_side = QHBoxLayout()
            palette_repr = CellDisplayWidget(value=value, palette=self.sim_palette, parent=self)
            side_by_side.addWidget(palette_repr)

            perc_widget = QDoubleSpinBox(self)
            perc_widget.setMaximum(1)
            perc_widget.setMinimum(0)
            perc_widget.setValue(self.percs[value])
            perc_widget.setSingleStep(0.01)
            perc_widget.setDecimals(4)
            def value_changed_with_index(new_value, index=index):
                self.perc_changed(new_value, index)
            perc_widget.valueChanged.connect(value_changed_with_index)
            self.perc_widgets[index] = perc_widget
            side_by_side.addWidget(perc_widget)

            whole_layout.addLayout(side_by_side)

        self.setLayout(whole_layout)

    def set_values(self):
        self.setting_values = True
        try:
            for value in self.values:
                perc_widget = self.perc_widgets[value]
                perc_widget.setValue(self.percs[value])
        finally:
            self.setting_values = False

    def perc_changed(self, new_value, index):
        if self.setting_values:
            return
        old_value = self.percs[index]
        change = new_value - old_value

        self.percs[index] = new_value

        others = len(self.percs) - 1

        for i in self.perc_widgets.keys():
            if i == index:
                continue
            self.percs[i] -= change / float(others)

        last_not_changed = -1 if index == len(self.percs) - 1 else -2
        almost_all = sum(self.percs) - self.percs[last_not_changed]
        self.percs[last_not_changed] = 1.0 - almost_all

        self.set_values()

@reg_resetter(PatternConfiguration)
class PatternResetter(BaseResetter):
    """This resetter allows the user to define patterns, that will be used
    to create a configuration."""

    friendly_name = "Pattern Editor"

    # XXX breaks down if the palette doesn't have 0 or 1.
    patterns = [(0,), (1,)]
    layout = (1,)

    class SubPatternEditor(QWidget):
        delete_me = Signal([int])
        add_more = Signal([int])
        pattern_changed = Signal()
        def __init__(self, base, position, pattern=None, palette=None, **kwargs):
            super(PatternResetter.SubPatternEditor, self).__init__(**kwargs)
            self.base = base
            self.pattern = pattern or [0]
            self.sim_palette = palette
            self.position = position
            self.setup_ui()

        def setup_ui(self):
            layout = QHBoxLayout()
            add_left = QPushButton("+")
            add_left.setMaximumSize(20,20)
            add_left.clicked.connect(self.add_left)
            layout.addWidget(add_left)

            self.editors = self.make_pattern_editors()
            self.editor_layout = QHBoxLayout()
            self.editor_layout.setSpacing(0)
            for editor in self.editors:
                self.editor_layout.addWidget(editor)

            layout.addLayout(self.editor_layout)

            add_right = QPushButton("+")
            add_right.setMaximumSize(20,20)
            add_right.clicked.connect(self.add_right)
            layout.addWidget(add_right)

            layout.addStretch()
            layout.addSpacing(16)
            delete_me = QPushButton("del")
            delete_me.clicked.connect(self.on_delete_me)
            self.btn_delete_me = delete_me
            add_new = QPushButton("more")
            add_new.clicked.connect(self.on_add_more)
            layout.addWidget(delete_me)
            layout.addWidget(add_new)

            self.setLayout(layout)

        def make_pattern_editors(self):
            editors = []
            for idx, value in enumerate(self.pattern):
                editors.append(
                        EditableCellDisplayWidget(value, idx, base=self.base, size=12, palette=self.sim_palette))

            return editors

        def change_pattern(self, idx, new):
            self.pattern[idx] = new
            self.pattern_changed.emit()

        def set_is_only(self, is_only):
            if is_only:
                self.btn_delete_me.hide()
            else:
                self.btn_delete_me.show()

        def add_left(self):
            self.editors.insert(0,
                    EditableCellDisplayWidget(self.pattern[0], 0, base=self.base, size=12, palette=self.sim_palette))
            self.editor_layout.insertWidget(0, self.editors[0])
            for idx, editor in enumerate(self.editors[1:]):
                editor.set_position(idx + 2)

        def add_right(self):
            self.editors.append(
                    EditableCellDisplayWidget(self.pattern[-1], len(self.pattern), base=self.base, size=12, palette=self.sim_palette))
            self.editor_layout.addWidget(self.editors[-1])

        def set_position(self, position):
            self.position = position

        def on_add_more(self): self.add_more.emit(self.position)
        def on_delete_me(self): self.delete_me.emit(self.position)

    def take_over_settings(self, configuration=None):
        if configuration:
            self.original_configuration = configuration
        else:
            configuration = self.original_configuration

        self.patterns = configuration.patterns
        self.layout = configuration.layout

    def rebuild_patterns_layout(self):
        patterns_layout = QFormLayout()
        for idx, pattern in enumerate(self.patterns):
            if 
            patterns_layout.addRow(str(idx) if idx != 0 else "bg/0", self.make_pattern_editor(idx, pattern))

        self.pat_layout = patterns_layout
        self.pat_lay_container.setLayout(self.pat_layout)

    def setup_ui(self):
        layout = QVBoxLayout()

        self.pat_lay_container = QWidget(self)
        layout.addWidget(self.pat_lay_container)
        self.rebuild_patterns_layout()

        self.layout_edit = QLineEdit()
        self.layout_edit.setText(", ".join(map(str,self.layout)))
        layout.addWidget(self.layout_edit)

        self.setLayout(layout)

    def make_pattern_editor(self, position, pattern):
        editor = self.SubPatternEditor(len(self.values), position, pattern, self.sim_palette)
        editor.add_more.connect(self.insert_new_pattern)
        editor.delete_me.connect(self.remove_pattern)
        return editor

    def insert_new_pattern(self, position):
        self.patterns.insert(position, self.patterns[position])
        self.rebuild_patterns_layout()

    def remove_pattern(self, position):
        del self.patterns[position]
        self.rebuild_patterns_layout()

class ResetDocklet(QDockWidget):
    """This dockwidget lets the user choose from a wide variety of
    config generators."""

    resetters = {}

    current_resetter = None

    def __init__(self, mainwin, **kwargs):
        super(ResetDocklet, self).__init__(**kwargs)
        self.setAllowedAreas(Qt.RightDockWidgetArea)
        self.setFloating(False)

        self._mw = mainwin

        self.setup_ui()
        self.switch_resetter(0)

    def setup_ui(self):
        centralwidget = QWidget()

        whole_layout = QVBoxLayout()

        resetter_selecter = QComboBox(self)
        for cls in class_to_resetter.values():
            resetter_selecter.addItem(cls.friendly_name, cls)
        resetter_selecter.currentIndexChanged.connect(self.switch_resetter)

        whole_layout.addWidget(resetter_selecter)
        self.resetter_selecter = resetter_selecter

        self.resetters_layout = QVBoxLayout()
        whole_layout.addLayout(self.resetters_layout)

        dismiss_button = QPushButton("reset changes")
        dismiss_button.clicked.connect(self.dismiss_changes)
        whole_layout.addWidget(dismiss_button)

        reset_button = QPushButton("Generate new")
        whole_layout.addWidget(reset_button)

        whole_layout.addStretch()

        self.whole_layout = whole_layout
        centralwidget.setLayout(self.whole_layout)

        self.setWidget(centralwidget)

    def switch_resetter(self, index):
        cls = self.resetter_selecter.itemData(index)
        if self.current_resetter:
            self.current_resetter.hide()
        if cls in self.resetters:
            w = self.resetters[cls]
            w.show()
        else:
            w = cls(self._mw, parent=self)
            self.resetters[cls] = w
            self.resetters_layout.addWidget(w)
            w.show()
            self.whole_layout.update()

        self.current_resetter = w

    def dismiss_changes(self):
        self.current_resetter.take_over_settings()
        self.current_resetter.set_values()

