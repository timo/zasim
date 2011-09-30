"""This module implements a window that allows editing configurations
in external programs. Currently, only editing the configs as images with
The GIMP is supported."""

from .displaywidgets import DisplayWidget

from ..external.qt import (QDialog, QHBoxLayout, QVBoxLayout,
        QInputDialog, QLabel, QPushButton, Qt,
        QFileSystemWatcher)

from ..config import ImageInitialConfiguration, AsciiInitialConfiguration
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

        self.fname_lay = QHBoxLayout()

        self.fname_disp = QLabel(parent=self)
        self.fname_disp.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.fname_lay.addWidget(self.fname_disp)

        self.import_btn = QPushButton("Import", parent=self)
        self.import_btn.clicked.connect(self.import_)
        self.fname_lay.addWidget(self.import_btn)
        self.lay.addLayout(self.fname_lay)

        self.conf_disp = DisplayWidget(self._sim)
        self.conf_disp.set_scale(1)

        self.lay.addWidget(self.conf_disp)

    def external_png(self, prefix="zasim", suffix=".png"):
        assert self.tmpfile is None
        assert self.process is None
        with NamedTemporaryFile(prefix=prefix, suffix=suffix) as self.tmpfile:
            self.fname_disp.setText(self.tmpfile.name)
            self.exporter = self.conf_disp
            self.exporter.export(self.tmpfile.name)
            self.importer = ImageInitialConfiguration(self.tmpfile.name)
            self.watcher = QFileSystemWatcher([self.tmpfile.name])
            self.watcher.fileChanged.connect(self.import_)

            self.process = Popen(["gimp", self.tmpfile.name])
            self.mode = "png"

            self.exec_()

    def external_txt(self, prefix="zasim", suffix=".txt"):
        assert self.tmpfile is None
        assert self.process is None
        with NamedTemporaryFile(prefix=prefix, suffix=suffix) as self.tmpfile:
            self.fname_disp.setText(self.tmpfile.name)
            self.exporter = TwoDimConsolePainter(self._sim)
            self.exporter.export(self.tmpfile.name)
            self.importer = AsciiInitialConfiguration(self.tmpfile.name)
            self.watcher = QFileSystemWatcher([self.tmpfile.name])
            self.watcher.fileChanged.connect(self.import_)

            editor = None
            envvars = ["ZASIM_EDITOR", "EDITOR"]
            for envvar in envvars:
                if envvar in environ:
                    editor = environ[envvar]
                    break

            if editor is None:
                editor = QInputDialog.getText(self, "Please specify the editor commandline", "Zasim looks at the environment variables %s to figure out what editor to use. Please consider setting it. Until then, specify the editor to use:", "gvim")
                if editor is None:
                    return False

            editor = shlex.split(editor)

            self.process = Popen(editor + [self.tmpfile.name])
            self.mode = "png"

            self.exec_()

    def import_(self):
        self._sim.set_config(self.importer.generate())

