from .displaywidgets import DisplayWidget

from ..external.qt import (QDialog, QHBoxLayout, QVBoxLayout,
        QLabel, QPushButton, Qt,
        QFileSystemWatcher)

from ..config import ImageInitialConfiguration
from tempfile import NamedTemporaryFile

from subprocess import Popen

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
            self.conf_disp.export(self.tmpfile.name)
            self.importer = ImageInitialConfiguration(self.tmpfile.name)
            self.watcher = QFileSystemWatcher([self.tmpfile.name])
            self.watcher.fileChanged.connect(self.import_)

            self.process = Popen(["gimp", self.tmpfile.name])
            self.mode = "png"

            self.exec_()

    def import_(self):
        self._sim.set_config(self.importer.generate())
