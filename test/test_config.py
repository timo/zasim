from __future__ import absolute_import

from .testutil import assert_arrays_equal

from zasim import config
from zasim.features import HAVE_MULTIDIM

import pytest

class TestConfig:
    def test_random_1d(self):
        a = config.RandomInitialConfiguration()
        arr = a.generate((1000,))
        assert not any(arr >= 2)
        assert not any(arr < 0)
        assert any(arr == 0)
        assert any(arr == 1)
        assert len(arr) == 1000

        b = config.RandomInitialConfiguration(base=3)
        brr = b.generate((1000,))
        assert not any(brr >= 3)
        assert not any(brr < 0)
        assert any(brr == 0)
        assert any(brr == 1)
        assert any(brr == 2)

    def test_random_1d_probabilities(self):
        a = config.RandomInitialConfiguration(2, 0)
        arr = a.generate((1000,))
        assert not any(arr == 0)
        assert all(arr == 1)

        b = config.RandomInitialConfiguration(2, 1)
        brr = b.generate((1000,))
        assert not any(brr == 1)
        assert all(brr == 0)

        c = config.RandomInitialConfiguration(3, 0)
        crr = c.generate((1000,))
        assert not any(crr == 0)
        assert any(crr == 1)
        assert any(crr == 2)

    def test_random_errors_1d(self):
        with pytest.raises(ValueError):
            a = config.RandomInitialConfiguration(2, 1.0, 1.0)
        with pytest.raises(ValueError):
            b = config.RandomInitialConfiguration(2, 0.1, 0.1, 0.8)
        with pytest.raises(TypeError):
            c = config.RandomInitialConfiguration(2, [0.1, 0.9])
        with pytest.raises(ValueError):
            d = config.RandomInitialConfiguration(2, 0.1, 0.8)

    @pytest.mark.skipif("not HAVE_MULTIDIM")
    def test_random_2d(self):
        a = config.RandomInitialConfiguration()
        arr = a.generate((100,100))
        assert not (arr > 2).any()
        assert not (arr < 0).any()
        assert (arr == 0).any()
        assert (arr == 1).any()
        assert arr.size == 100 * 100

        b = config.RandomInitialConfiguration(base=3)
        brr = b.generate((100,100))
        assert not (brr > 3).any()
        assert not (brr < 0).any()
        assert (brr == 0).any()
        assert (brr == 1).any()
        assert (brr == 2).any()

    @pytest.mark.skipif("not HAVE_MULTIDIM")
    def test_random_2d_probabilities(self):
        a = config.RandomInitialConfiguration(2, 0)
        arr = a.generate((100,100))
        assert not (arr == 0).any()
        assert (arr == 1).all()

        b = config.RandomInitialConfiguration(2, 1)
        brr = b.generate((100,100))
        assert not (brr == 1).any()
        assert (brr == 0).all()

        c = config.RandomInitialConfiguration(3, 0)
        crr = c.generate((100,100))
        assert not (crr == 0).any()
        assert (crr == 1).any()
        assert (crr == 2).any()

    @pytest.mark.skipif("not HAVE_MULTIDIM")
    def test_export_import_conf_ascii(self):
        from zasim.cagen import ElementarySimulator
        from zasim.display.console import TwoDimConsolePainter
        from tempfile import NamedTemporaryFile
        s = ElementarySimulator(size=(30, 50), rule=111)
        d = TwoDimConsolePainter(s)
        s.step()

        with NamedTemporaryFile(prefix="zasim_test_") as tmpfile:
            d.export(tmpfile.name)
            nconf_imp = config.AsciiInitialConfiguration(tmpfile.name)
            assert_arrays_equal(nconf_imp.generate(), s.get_config())

    @pytest.mark.skipif("not HAVE_MULTIDIM")
    def test_export_import_conf_png(self, scale):
        from zasim.cagen import ElementarySimulator
        from zasim.display.qt import TwoDimQImagePainter
        from tempfile import NamedTemporaryFile
        s = ElementarySimulator(size=(100, 100))
        disp = TwoDimQImagePainter(s, scale=scale)
        s.step()

        with NamedTemporaryFile(prefix="zasim_test_", suffix=".png", delete=False) as tmpfile:
            disp.export(tmpfile.name)
            nconf_imp = config.ImageInitialConfiguration(tmpfile.name, scale=scale)
            assert_arrays_equal(nconf_imp.generate(), s.get_config())

def pytest_generate_tests(metafunc):
    if "scale" in metafunc.funcargnames:
        for i in [1, 4, 10]:
            metafunc.addcall(funcargs=dict(scale=i))

