"""This module implements a window that allows editing configurations
in external programs. Instantiate one ExternalEditWindow per session (or keep
it) and call `external_png` or `external_txt` to display the Dialog.

The file will be created as a temporary file, changes to it will automatically
cause a reload of the config to the simulator and any display updates. An
"import" button is also provided in case the filesystem watcher fails."""

from .displaywidgets import DisplayWidget

from ..external.qt import (QDialog, QHBoxLayout, QVBoxLayout,
        QInputDialog, QLabel, Qt,
        QDialogButtonBox,
        QFileSystemWatcher)

from ..config import ImageConfiguration, FileAsciiConfiguration
from tempfile import NamedTemporaryFile

from ..display.console import TwoDimConsolePainter

from subprocess import Popen
from os import environ

import shlex

class ExternalEditWindow(QDialog):
    def __init__(self, simulator, parent=None):
        super(ExternalEditWindow, self).__init__(parent=parent)
        self._sim = simulator

        self.setup_ui()
        self.setModal(True)
        self.tmpfile = None
        self.process = None
        self.watcher = None

    def setup_ui(self):
        self.lay = QVBoxLayout(self)

        self.fname_disp = QLabel(parent=self)
        self.fname_disp.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.lay.addWidget(self.fname_disp)

        self.btn_box_u = QDialogButtonBox(parent=self)
        self.btn_box_u.addButton(QDialogButtonBox.Reset).setToolTip("Change the configuration back to what it was before.")
        self.btn_box_u.addButton("Update", QDialogButtonBox.AcceptRole).setToolTip("Read the file and load the configuration.")
        self.btn_box_u.clicked.connect(self.button_clicked)

        self.lay.addWidget(self.btn_box_u)

        self.lay.addStretch()

        disp_lay = QHBoxLayout()
        self.conf_disp = DisplayWidget(self._sim)
        self.conf_disp.set_scale(1)
        disp_lay.addStretch()
        disp_lay.addWidget(self.conf_disp)
        disp_lay.addStretch()
        self.lay.addLayout(disp_lay)

        self.lay.addStretch()

        self.btn_box_l = QDialogButtonBox(parent=self)
        self.btn_box_l.addButton(QDialogButtonBox.Ok).setToolTip("Close this window and keep all changes.")
        self.btn_box_l.addButton(QDialogButtonBox.Cancel).setToolTip("Reset all changes and close this window.")
        self.btn_box_l.clicked.connect(self.button_clicked)
        self.lay.addWidget(self.btn_box_l)

    def button_clicked(self, button):
        for bbox in [self.btn_box_l, self.btn_box_u]:
            if bbox.buttonRole(button) != QDialogButtonBox.InvalidRole:
                role = bbox.buttonRole(button)
                box = bbox
                break

        if role == QDialogButtonBox.ResetRole:
            self.reset()
        elif role == QDialogButtonBox.RejectRole:
            self.reset()
            self.reject()
        elif role == QDialogButtonBox.AcceptRole:
            if box == self.btn_box_u:
                self.import_()
            else:
                self.accept()

    def __external_edit(self, prefix, suffix, importer_class, program):
        assert self.tmpfile is None
        assert self.process is None

        self.original_config = self._sim.get_config()

        with NamedTemporaryFile(prefix=prefix, suffix=suffix) as self.tmpfile:
            self.fname_disp.setText(self.tmpfile.name)
            self.exporter.export(self.tmpfile.name)
            self.importer = importer_class(self.tmpfile.name)
            self.watcher = QFileSystemWatcher([self.tmpfile.name])
            self.watcher.fileChanged.connect(self.import_)

            self.process = Popen(program + [self.tmpfile.name])

            result = self.exec_()

        if result is QDialog.Rejected:
            self.reset()

        self.tmpfile = None
        self.process = None
        self.watcher.fileChanged.disconnect(self.import_)
        del self.watcher
        self.watcher = None

    def reset(self):
        self._sim.set_config(self.original_config)

    def external_png(self, prefix="zasim", suffix=".png"):
        self.exporter = self.conf_disp
        self.__external_edit(prefix, suffix, ImageConfiguration, ["gimp"])

    def external_txt(self, prefix="zasim", suffix=".txt"):
        editor = None
        envvars = ["ZASIM_EDITOR", "EDITOR"]
        for envvar in envvars:
            if envvar in environ:
                editor = environ[envvar]
                break

        if editor is None:
            editor = QInputDialog.getText(self, "Please specify the editor commandline", "Zasim looks at the environment variables %s to figure out what editor to use. Please consider setting it. Until then, specify the editor to use:" % (", ".join(envvars)), "gvim")
            if editor is None:
                return False

        editor = shlex.split(editor)

        self.exporter = TwoDimConsolePainter(self._sim)
        self.__external_edit(prefix, suffix, FileAsciiConfiguration, editor)

    def import_(self):
        self._sim.set_config(self.importer.generate())

