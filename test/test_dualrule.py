# -*- coding: utf8 -*-
from __future__ import absolute_import

from zasim import cagen
from zasim.features import *
from zasim.simulator import CagenSimulator

from .testutil import *

import pytest

class TestDualRule:
    def test_run_nondeterministic_pure(self):
        # implement nazim fatès density classifier
        compu = cagen.DualRuleCellularAutomaton(184, 232, 0.1)
        sf = cagen.automatic_stepfunc(computation=compu, histogram=True)
        sf.gen_code()
        simu = CagenSimulator(sf, sf.target)

        for i in range(20):
            simu.step_pure_py()

    @pytest.mark.skipif("not HAVE_WEAVE")
    def test_run_nondeterministic_weave(self):
        # implement nazim fatès density classifier
        compu = cagen.DualRuleCellularAutomaton(184, 232, 0.1)
        sf = cagen.automatic_stepfunc(computation=compu, histogram=True)
        simu = CagenSimulator(sf, sf.target)

        for i in range(50):
            simu.step_inline()

    def test_compare_nondeterministic_pure(self):
        compu = cagen.DualRuleCellularAutomaton(184, 232, 0)
        sf = cagen.automatic_stepfunc(size=(100,), computation=compu, histogram=True)
        sf.gen_code()
        simu = CagenSimulator(sf, sf.target)

        br = cagen.BinRule(rule=184, config=simu.get_config())

        for i in range(20):
            simu.step_pure_py()
            br.step_pure_py()

            assert_ndim_arrays_equal(simu.get_config(), br.get_config())

    @pytest.mark.skipif("not HAVE_WEAVE")
    def test_compare_nondeterministic_weave(self):
        compu = cagen.DualRuleCellularAutomaton(184, 232, 1)
        sf = cagen.automatic_stepfunc(size=(100,), computation=compu, histogram=True)
        sf.gen_code()
        simu = CagenSimulator(sf, sf.target)

        br = cagen.BinRule(rule=232, config=simu.get_config())

        for i in range(50):
            simu.step_inline()
            br.step_inline()

            assert_ndim_arrays_equal(simu.get_config(), br.get_config())
