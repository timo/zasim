from __future__ import absolute_import

from zasim import cagen
from zasim.features import *
from zasim.display.console import *

from .testutil import *

import pytest
import tempfile

import sys
IS_PYPY = "pypy_version_info" in dir(sys)

class TestDisplay:
    @pytest.mark.skipif("not HAVE_MULTIDIM")
    @pytest.mark.xfail("IS_PYPY")
    def test_pretty_print_config_2d(self, capsys):
        gconf = GLIDER[0]
        simo = cagen.GameOfLife(config=gconf)
        display = TwoDimConsolePainter(simo)

        out, err = capsys.readouterr()
        assert out == """\
  #  
# #  
 ##  
     
     
"""

        with tempfile.NamedTemporaryFile(delete=False) as tmpfile:
            name = tmpfile.name
            display.export(tmpfile.name)

        assert open(name).read() == """\
  #  
# #  
 ##  
     
     
"""

    @pytest.mark.xfail("IS_PYPY")
    def test_pretty_print_config_1d(self, capsys):
        conf = np.array([1,0,1,1,0])
        br = cagen.BinRule(config=conf, rule=204)
        display = OneDimConsolePainter(br, 1)

        out, err = capsys.readouterr()
        assert out == """# ## \n"""

        with tempfile.NamedTemporaryFile(delete=False) as tmpfile:
            name = tmpfile.name
            display.export(tmpfile.name)

        assert open(name).read() == "# ## \n"

