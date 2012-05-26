from __future__ import absolute_import

from .testutil import assert_arrays_equal

from zasim import config
from zasim.features import HAVE_MULTIDIM, HAVE_DTYPE_AS_INDEX

from itertools import product

import sys
IS_PYPY = "pypy_version_info" in dir(sys)

import pytest

class TestConfig:
    def test_random_1d(self):
        a = config.RandomConfiguration()
        arr = a.generate((1000,))
        assert not any(arr >= 2)
        assert not any(arr < 0)
        assert any(arr == 0)
        assert any(arr == 1)
        assert len(arr) == 1000

        b = config.RandomConfiguration(base=3)
        brr = b.generate((1000,))
        assert not any(brr >= 3)
        assert not any(brr < 0)
        assert any(brr == 0)
        assert any(brr == 1)
        assert any(brr == 2)

        c = config.RandomConfiguration(3)
        crr = c.generate((None,))
        assert len(crr.shape) == 1

    def test_random_1d_probabilities(self):
        a = config.RandomConfiguration(2, 0)
        arr = a.generate((1000,))
        assert not any(arr == 0)
        assert all(arr == 1)

        b = config.RandomConfiguration(2, 1)
        brr = b.generate((1000,))
        assert not any(brr == 1)
        assert all(brr == 0)

        c = config.RandomConfiguration(3, 0)
        crr = c.generate((1000,))
        assert not any(crr == 0)
        assert any(crr == 1)
        assert any(crr == 2)

    def test_random_errors_1d(self):
        with pytest.raises(ValueError):
            a = config.RandomConfiguration(2, 1.0, 1.0)
        with pytest.raises(ValueError):
            b = config.RandomConfiguration(2, 0.1, 0.1, 0.8)
        with pytest.raises(TypeError):
            c = config.RandomConfiguration(2, [0.1, 0.9])
        with pytest.raises(ValueError):
            d = config.RandomConfiguration(2, 0.1, 0.8)

    @pytest.mark.skipif("not HAVE_MULTIDIM")
    def test_random_2d(self):
        a = config.RandomConfiguration()
        arr = a.generate((100,100))
        assert not (arr > 2).any()
        assert not (arr < 0).any()
        assert (arr == 0).any()
        assert (arr == 1).any()
        assert arr.size == 100 * 100

        b = config.RandomConfiguration(base=3)
        brr = b.generate((100,100))
        assert not (brr > 3).any()
        assert not (brr < 0).any()
        assert (brr == 0).any()
        assert (brr == 1).any()
        assert (brr == 2).any()

        c = config.RandomConfiguration(3)
        crr = c.generate((None, 100))
        assert len(crr.shape) == 2
        assert crr.shape[1] == 100

    @pytest.mark.skipif("not HAVE_MULTIDIM")
    def test_random_2d_probabilities(self):
        a = config.RandomConfiguration(2, 0)
        arr = a.generate((100,100))
        assert not (arr == 0).any()
        assert (arr == 1).all()

        b = config.RandomConfiguration(2, 1)
        brr = b.generate((100,100))
        assert not (brr == 1).any()
        assert (brr == 0).all()

        c = config.RandomConfiguration(3, 0)
        crr = c.generate((100,100))
        assert not (crr == 0).any()
        assert (crr == 1).any()
        assert (crr == 2).any()

    @pytest.mark.skipif("not HAVE_MULTIDIM")
    @pytest.mark.skipif("IS_PYPY")
    def test_export_import_conf_ascii(self):
        from zasim.cagen import ElementarySimulator
        from zasim.display.console import TwoDimConsolePainter
        from tempfile import NamedTemporaryFile
        s = ElementarySimulator(size=(20, 30), rule=111)
        d = TwoDimConsolePainter(s)
        s.step()

        with NamedTemporaryFile(prefix="zasim_test_") as tmpfile:
            d.export(tmpfile.name)
            nconf_imp = config.FileAsciiConfiguration(tmpfile.name)
            assert_arrays_equal(nconf_imp.generate(), s.get_config())

    @pytest.mark.skipif("IS_PYPY")
    def test_export_import_conf_png(self, scale):
        from zasim.cagen import GameOfLife
        from zasim.display.qt import TwoDimQImagePainter
        from tempfile import NamedTemporaryFile
        s = GameOfLife(size=(30, 40))
        disp = TwoDimQImagePainter(s, scale=scale, frame_duration=0)
        for i in range(20):
            s.step()


        with NamedTemporaryFile(prefix="zasim_test_", suffix=".png", delete=False) as tmpfile:
            disp.export(tmpfile.name)
            nconf_imp = config.ImageConfiguration(tmpfile.name, scale=scale)
            assert_arrays_equal(nconf_imp.generate(), s.get_config())

    def test_probability_distribution_1d(self):
        zero_fun = 1
        one_fun = lambda x, w: 0 if x <= w/2 else 5

        gen = config.DensityDistributedConfiguration({0:zero_fun, 1:one_fun})
        for i in range(10):
            conf = gen.generate((100,))
            assert not conf[0:49].any()
            assert conf[50:].any()
            assert not conf[50:].all()

    @pytest.mark.skipif("not HAVE_MULTIDIM")
    @pytest.mark.xfail("not HAVE_DTYPE_AS_INDEX")
    def test_probability_distribution_2d(self):
        zero_fun = 1
        one_fun = lambda x, y, w, h: 0 if x <= w/2 else 5
        two_fun = lambda x, y, w, h: 0 if y <= h/2 else 10

        gen = config.DensityDistributedConfiguration(
                {0:zero_fun, 1:one_fun, 2:two_fun})

        for i in range(5):
            conf = gen.generate((50,50))
            print conf
            assert not conf[0:24,0:24].any()
            try:
                assert not (conf[...,0:24] == 2).any()
                assert not (conf[0:24,...] == 1).any()
            except TypeError:
                for x, y in product(xrange(50), xrange(50)):
                    if x <= 25:
                        assert conf[x, y] != 1
                    if y <= 25:
                        assert conf[x, y] != 2

def pytest_generate_tests(metafunc):
    if "scale" in metafunc.funcargnames:
        for i in [1, 4, 10]:
            metafunc.addcall(funcargs=dict(scale=i))

