from __future__ import absolute_import

from zasim import cagen
from zasim.features import *
from zasim.display.console import *

from .testutil import *

import pytest

class TestCAGen:
    @pytest.mark.skipif("not HAVE_MULTIDIM")
    def test_pretty_print_config_2d(self, capsys):
        gconf = GLIDER[0]
        simo = cagen.GameOfLife(config=gconf)
        display = TwoDimConsolePainter(simo)
        simo.step()

        out, err = capsys.readouterr()
        assert out == """\
     
# #  
 ##  
 #   
     
"""

    def test_pretty_print_config_1d(self, capsys):
        conf = np.array([1,0,1,1,0])
        br = cagen.BinRule(config=conf, rule=204)
        display = LinearConsolePainter(br, 1)
        br.step()

        out, err = capsys.readouterr()
        assert out == """# ## \n"""

