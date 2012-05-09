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
            nb = reads(f.read(), 'json')

            yield IPyNbItem(self.fspath.basename, self, nb)

class IPyNbItem(pytest.Item):
    def __init__(self, name, parent, notebook):
        super(IPyNbItem, self).__init__(name, parent)
        self.nb = notebook

    def runtest(self):
        km = BlockingKernelManager()
        try:
            km.start_kernel(stderr=open(os.devnull, 'w'))
            km.start_channels()
            shell = km.shell_channel
            # simple ping:
            shell.execute("pass")
            shell.get_msg()

            cells = 0
            for ws in self.nb.worksheets:
                for cell in ws.cells:
                    if cell.cell_type != 'code':
                        continue
                    shell.execute(cell.input, allow_stdin=False)
                    # wait for finish, maximum 20s
                    reply = shell.get_msg(timeout=20)['content']
                    if reply['status'] == 'error':
                        raise IPyNbException(cells, cell.input, '\n'.join(reply['traceback']))
                    cells += 1
                    sys.stdout.write('.')

        finally:
            km.shutdown_kernel()
            del km

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
        return self.fspath, 0, "notebook: %s" % self.nb.metadata.name

class IPyNbException(Exception):
    """ custom exception for error reporting. """
