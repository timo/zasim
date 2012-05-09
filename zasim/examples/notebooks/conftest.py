import pytest
import os,sys,time

wrapped_stdin = sys.stdin
sys.stdin = sys.__stdin__
from IPython.zmq.blockingkernelmanager import BlockingKernelManager
sys.stdin = wrapped_stdin
from IPython.nbformat.current import reads

# combined from
# http://pytest.org/latest/example/nonpython.html#non-python-tests
# and
# https://gist.github.com/2621679 by minrk

def pytest_collect_file(path, parent):
    if path.ext == ".ipynb":
        return IPyNbFile(path, parent)

class IPyNbFile(pytest.File):
    def collect(self):
        with self.fspath.open() as f:
            self.nb = reads(f.read(), 'json')

            cell_num = 0

            for ws in self.nb.worksheets:
                for cell in ws.cells:
                    if cell.cell_type == "code":
                        yield IPyNbCell(self.name, self, cell_num, cell)
                        cell_num += 1

    def setup(self):
        self.km = BlockingKernelManager()
        self.km.start_kernel(stderr=open(os.devnull, 'w'))
        self.km.start_channels()
        self.shell = self.km.shell_channel

    def teardown(self):
        self.km.shutdown_kernel()
        del self.shell
        del self.km

class IPyNbCell(pytest.Item):
    def __init__(self, name, parent, cell_num, cell):
        super(IPyNbCell, self).__init__(name, parent)

        self.cell_num = cell_num
        self.cell = cell

    def runtest(self):
        shell = self.parent.shell
        shell.execute(self.cell.input, allow_stdin=False)
        # wait for finish, maximum 20s
        reply = shell.get_msg(timeout=20)['content']
        if reply['status'] == 'error':
            raise IPyNbException(self.cell.input, '\n'.join(reply['traceback']))

    def repr_failure(self, excinfo):
        """ called when self.runtest() raises an exception. """
        if isinstance(excinfo.value, IPyNbException):
            return "\n".join([
                "notebook worksheet execution failed",
                " cell %d\n\n"
                "   input: %r\n\n"
                "   raised: %r\n" % excinfo.value.args[1:3],
            ])

    def reportinfo(self):
        return self.fspath, 0, "cell %d" % self.cell_num

class IPyNbException(Exception):
    """ custom exception for error reporting. """

