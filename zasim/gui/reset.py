"""This module offers a way for the user to reset a Simulator with
different kinds of generated or specified configurations.

The `ResetDocklet` gets embedded in the `ZasimMainWindow` automatically. The
user then gets to choose from any of the available resetters, all derived from
the `BaseResetter` class and registered with the `reg_resetter` class
decorator.

Each `Resetter` implements the following methods:

* `~BaseResetter.setup_ui`, to create the user interface for changing settings
  for this resetter.
* `~BaseResetter.set_values`, to update the GUI whenever the internal state has
  changed.
* `~BaseResetter.take_over_settings`, to read in settings from an existing
  `Configuration`
* `~BaseResetter.generate_generator`, which returns a Generator to match the
  settings from the user interface.

.. seealso::

    :ref:`zasim.config <zasim_config_module>`
"""


from ..external.qt import *
from .elementary import CellDisplayWidget, EditableCellDisplayWidget
from ..display.qt import make_palette_qc

from ..config import *

import re

class BaseResetter(QWidget):
    friendly_name = ""
    """Set this for the GUI."""

    handles_classes = ()
    """This defines, what kinds of Configuration classes we can handle."""

    def __init__(self, mainwin, **kwargs):
        super(BaseResetter, self).__init__(**kwargs)

        self._mw = mainwin
        self._sim = self._mw.simulator
        if "colors_qc" not in self._sim.palette_info:
            self._sim.palette_info["colors_qc"] = make_palette_qc(self._sim.palette_info["colors32"])
        self.sim_palette = self._sim.palette_info["colors_qc"]
        # XXX this needs to go somewhere else, I think.
        self._sim.limit_palette()

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

class BaseRandomConfigurationResetter(BaseResetter):
    perc_widgets = {}

    friendly_name = "Random Configuration"

    handles_classes = (BaseRandomConfiguration)

    setting_values = False

    def take_over_settings(self, configuration=None):
        if configuration and isinstance(configuration, BaseRandomConfiguration):
            self.original_configuration = configuration
        else:
            try:
                configuration = self.original_configuration
            except:
                configuration = RandomConfigurationFromPalette(self.values)
                self.original_configuration = configuration

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

        self.percs = [max(0, v) for v in self.percs]

        while sum(self.percs) != 1:
            last_not_changed = -1 if index == len(self.percs) - 1 else -2
            almost_all = sum(self.percs) - self.percs[last_not_changed]
            self.percs[last_not_changed] = 1.0 - almost_all
            self.percs = [max(0, v) for v in self.percs]

        self.set_values()

    def generate_generator(self):
        return RandomConfigurationFromPalette(self.values, *self.percs)

class PatternResetter(BaseResetter):
    """This resetter allows the user to define patterns, that will be used
    to create a configuration."""

    friendly_name = "Pattern Editor"

    handles_classes = (PatternConfiguration)

    # XXX breaks down if the palette doesn't have 0 or 1.
    patterns = [(0,), (1,)]
    layout = (1,)

    class SubPatternEditor(QWidget): # {{{
        delete_me = Signal([int])
        add_more = Signal([int])
        pattern_changed = Signal([int])
        def __init__(self, base, position, pattern=None, palette=None, **kwargs):
            super(PatternResetter.SubPatternEditor, self).__init__(**kwargs)
            self.base = base
            self.pattern = list(pattern) or [0]
            self.sim_palette = palette
            self.position = position
            self.setup_ui()

        def setup_ui(self):
            layout = QHBoxLayout()
            position_label = QLabel(str(self.position) if self.position != 0 else "bg")
            position_label.setMinimumWidth(26)
            layout.addWidget(position_label)
            self.pos_lbl = position_label
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

            layout.addStretch()
            add_right = QPushButton("+")
            add_right.setMaximumSize(20,20)
            add_right.clicked.connect(self.add_right)
            layout.addWidget(add_right)

            layout.addSpacing(16)
            delete_me = QPushButton("del")
            delete_me.clicked.connect(self.on_delete_me)
            self.btn_delete_me = delete_me
            add_new = QPushButton("more")
            add_new.clicked.connect(self.on_add_more)
            layout.addWidget(delete_me)
            layout.addWidget(add_new)

            self.setLayout(layout)
            self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Preferred)

        def make_pattern_editors(self):
            editors = []
            for idx, value in enumerate(self.pattern):
                editors.append(self.create_edit_widget(value, idx))

            return editors

        def create_edit_widget(self, value, idx):
            editor = EditableCellDisplayWidget(value, idx, base=self.base, size=12, palette=self.sim_palette)
            editor.value_changed.connect(self.change_pattern)
            return editor

        def change_pattern(self, idx, new):
            self.pattern[idx] = new
            self.pattern_changed.emit(self.position)

        def set_is_only(self, is_only):
            if is_only:
                self.btn_delete_me.hide()
            else:
                self.btn_delete_me.show()

        def add_left(self):
            self.pattern.insert(0, self.pattern[0])
            self.editors.insert(0, self.create_edit_widget(self.pattern[0], 0))
            self.editor_layout.insertWidget(0, self.editors[0])
            for idx, editor in enumerate(self.editors[1:]):
                editor.set_position(idx + 2)
            self.pattern_changed.emit(self.position)

        def add_right(self):
            self.pattern.append(self.pattern[-1])
            self.editors.append(self.create_edit_widget(self.pattern[-1], len(self.pattern)-1))
            self.editor_layout.addWidget(self.editors[-1])
            self.pattern_changed.emit(self.position)

        def set_position(self, position):
            self.position = position
            self.pos_lbl.setText(str(self.position) if self.position != 0 else "bg")

        def on_add_more(self): self.add_more.emit(self.position)
        def on_delete_me(self): self.delete_me.emit(self.position)
        # }}}

    def take_over_settings(self, configuration=None):
        if configuration and isinstance(configuration, PaternConfiguration):
            self.original_configuration = configuration
        else:
            try:
                configuration = self.original_configuration
            except:
                configuration = PatternConfiguration([(0,), (1,)], [1,])

        self.patterns = list(configuration.patterns)
        self.layout = list(configuration.layout)

        # TODO this doesn't change the GUI yet.

    def setup_ui(self):
        layout = QVBoxLayout()

        editors = QVBoxLayout()

        for idx, pattern in enumerate(self.patterns):
            editors.addWidget(self.make_pattern_editor(idx, pattern))

        self.editors = editors
        layout.addLayout(editors)

        self.layout_edit = QLineEdit()
        self.layout_edit.setText(" ".join(map(str,self.layout)))
        self.layout_edit.textChanged.connect(self.layout_changed)
        layout.addWidget(self.layout_edit)

        self.setLayout(layout)

    def make_pattern_editor(self, position, pattern):
        editor = self.SubPatternEditor(len(self.values), position, pattern, self.sim_palette)
        editor.add_more.connect(self.insert_new_pattern)
        editor.delete_me.connect(self.remove_pattern)
        editor.pattern_changed.connect(self.pattern_changed)
        return editor

    def pattern_changed(self, position):
        self.patterns[position] = self.editors.itemAt(position).widget().pattern

    def insert_new_pattern(self, position):
        self.patterns.insert(position, [0])
        self.editors.insertWidget(position, self.make_pattern_editor(position, self.patterns[position]))

        # move layout items down a bit to make space.
        for idx in range(0, self.editors.count()):
            item = self.editors.itemAt(idx)
            item.widget().set_position(idx)

    def remove_pattern(self, position):
        del self.patterns[position]

        new_last_row = self.editors.count() - 1
        item = self.editors.takeAt(position)
        item.widget().deleteLater()

        for idx in range(0, new_last_row):
            item = self.editors.itemAt(idx)
            item.widget().set_position(idx)

    def layout_changed(self, text):
        numbers = re.findall(r"\d+", text)
        self.layout = map(int, numbers)

    def generate_generator(self):
        return PatternConfiguration(self.patterns, self.layout)

class ImageResetter(BaseResetter):
    friendly_name = "From Image"

    handles_classes = (ImageConfiguration)

    def __init__(self, *args, **kwargs):
        super(ImageResetter, self).__init__(*args, **kwargs)
        self.sim_palette = self._sim.palette_info["colors32"]

    def take_over_settings(self, configuration=None):
        if configuration and isinstance(configuration, ImageConfiguration):
            self.original_configuration = configuration
        else:
            try:
                configuration = self.original_configuration
            except:
                configuration = None

        if configuration is not None:
            self.filename = configuration.filename
        else:
            self.filename = None

        self.path_edit.setText(self.filename)
        try:
            self.preview.setPixmap(QPixmap(self.filename))
        except:
            self.preview.setText("no preview")

    def setup_ui(self):
        v_layout = QVBoxLayout()
        h_layout = QHBoxLayout()

        self.path_edit = QLineEdit()
        self.path_edit.textChanged.connect(self.try_load)
        self.browse_btn = QPushButton("...")
        self.browse_btn.clicked.connect(self.browse)

        h_layout.addWidget(self.path_edit)
        h_layout.addWidget(self.browse_btn)
        v_layout.addLayout(h_layout)

        h_layout_2 = QHBoxLayout()
        h_layout_2.addWidget(QLabel("Scale factor"))
        self.scale_edit = QSpinBox()
        self.scale_edit.setMinimum(1)
        h_layout_2.addWidget(self.scale_edit)
        self.fuzz_check = QCheckBox("fuzzy matching")
        h_layout_2.addWidget(self.fuzz_check)

        v_layout.addLayout(h_layout_2)

        self.preview = QLabel("no preview")
        v_layout.addWidget(self.preview)

        self.setLayout(v_layout)

    def generate_generator(self):
        return ImageConfiguration(self.filename,
                                  scale=self.scale_edit.value(),
                                  palette=self.sim_palette,
                                  fuzz=self.fuzz_check.isChecked())

    def browse(self):
        filename, typ = QFileDialog.getOpenFileName(self, "Select an image file")

        if filename:
            self.filename = filename
            self.preview.setPixmap(QPixmap(self.filename))
            self.path_edit.setText(filename)

    def try_load(self, path):
        image = QPixmap(path)
        if image.isNull():
            self.preview.setText("no preview")
        else:
            self.preview.setPixmap(QPixmap(path))
            self.filename = path

class FallbackResetter(BaseResetter):
    friendly_name = "Reset using original"

    handles_classes = (BaseConfiguration)

    def take_over_settings(self, configuration=None):
        if configuration:
            self.original_configuration = configuration

    def setup_ui(self):
        layout = QHBoxLayout()

        label = QLabel("A %s was used to generate this configuration.<br/>"
        "The GUI doesn't know how to configure this, but it does know how to"
        "just use the same generator again. Use the generate button below to"
        "do that." % type(self.original_configuration).__name__)
        label.setWordWrap(True)
        label.setTextFormat(Qt.RichText)
        layout.addWidget(label)
        layout.addStretch()

        self.setLayout(layout)

    def generate_generator(self):
        return self.original_configuration

class ResetWidget(QWidget):
    """This widget lets the user choose from a wide variety of
    config generators using classes derived from BaseResetter and registered
    with the reg_resetter class decorator."""

    resetters = {}

    current_resetter = None

    def __init__(self, mainwin, **kwargs):
        super(ResetWidget, self).__init__(**kwargs)

        self._mw = mainwin

        self.setup_ui()
        self.switch_resetter(0)

    def setup_ui(self):
        whole_layout = QVBoxLayout()

        resetter_selecter = QComboBox(self)
        needs_fallback = True
        for cls in BaseResetter.__subclasses__():
            resetter_selecter.addItem(cls.friendly_name, cls)
            if isinstance(self._mw.simulator._target._reset_generator, cls.handles_classes):
                needs_fallback = False
        if needs_fallback:
            resetter_selecter.addItem(FallbackResetter.friendly_name, FallbackResetter)
        resetter_selecter.currentIndexChanged.connect(self.switch_resetter)

        whole_layout.addWidget(resetter_selecter)
        self.resetter_selecter = resetter_selecter

        self.resetters_layout = QVBoxLayout()
        whole_layout.addLayout(self.resetters_layout)

        dismiss_button = QPushButton("undo changes")
        dismiss_button.clicked.connect(self.dismiss_changes)
        whole_layout.addWidget(dismiss_button)
        whole_layout.addSpacing(10)

        reset_button = QPushButton("Generate new")
        reset_button.clicked.connect(self.generate)
        whole_layout.addWidget(reset_button)

        whole_layout.addStretch()

        self.whole_layout = whole_layout
        self.setLayout(self.whole_layout)

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

    def generate(self):
        generator = self.current_resetter.generate_generator()
        self._mw.simulator.reset(generator)

class ResetDocklet(QDockWidget):
    """This dockwidget lets the user choose from a wide variety of
    config generators, by embedding a ResetWidget into a DockWidget.

    The ZasimMainWindow embeds this by default."""

    def __init__(self, mainwin, **kwargs):
        super(ResetDocklet, self).__init__(**kwargs)
        self.setAllowedAreas(Qt.RightDockWidgetArea)
        self.setFloating(False)

        self._mw = mainwin

        self.setup_ui()

    def setup_ui(self):
        self.reset_widget = ResetWidget(self._mw, parent=self)

        self.setWidget(self.reset_widget)
