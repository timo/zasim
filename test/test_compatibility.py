from __future__ import absolute_import

from zasim import cagen
import pytest

class TestCompatibility:
    def test_onedim_loop_twodim_conf(self):
        with pytest.raises(cagen.CompatibilityException):
            sf = cagen.WeaveStepFunc(
                    loop=cagen.LinearCellLoop(),
                    accessor=cagen.SimpleStateAccessor(),
                    neighbourhood=cagen.VonNeumannNeighbourhood(),
                    extra_code=[],
                    size=(100, 100))

    def test_twodim_loop_onedim_conf(self):
        with pytest.raises(cagen.CompatibilityException):
            sf = cagen.WeaveStepFunc(
                    loop=cagen.TwoDimCellLoop(),
                    accessor = cagen.SimpleStateAccessor(),
                    neighbourhood=cagen.VonNeumannNeighbourhood(),
                    extra_code=[],
                    size=(100,))

    def test_onedim_conf_twodim_neighbourhood(self):
        with pytest.raises(cagen.CompatibilityException):
            sf = cagen.WeaveStepFunc(
                    loop=cagen.LinearCellLoop(),
                    accessor = cagen.SimpleStateAccessor(),
                    neighbourhood=cagen.VonNeumannNeighbourhood(),
                    extra_code=[],
                    size=(100,))

    def test_incomplete_beta_async(self):
        with pytest.raises(cagen.CompatibilityException):
            sf = cagen.WeaveStepFunc(
                    loop=cagen.LinearCellLoop(),
                    accessor = cagen.BetaAsynchronousAccessor(),
                    neighbourhood=cagen.VonNeumannNeighbourhood(),
                    extra_code=[],
                    size=(100,))

        with pytest.raises(cagen.CompatibilityException):
            sf = cagen.WeaveStepFunc(
                    loop=cagen.LinearCellLoop(),
                    accessor = cagen.SimpleStateAccessor(),
                    neighbourhood=cagen.VonNeumannNeighbourhood(Base=cagen.BetaAsynchronousNeighbourhood),
                    extra_code=[],
                    size=(100,))
