# -*- coding: utf8 -*-
from __future__ import absolute_import

from zasim import cagen
from zasim.features import *
from zasim.simulator import CagenSimulator

from .testutil import *

import pytest

class TestDualRule:
    @pytest.mark.xfail("not HAVE_DTYPE_AS_INDEX")
    def test_run_nondeterministic_pure(self):
        # implement nazim fatès density classifier
        compu = cagen.DualRuleCellularAutomaton(184, 232, 0.1)
        sf = cagen.automatic_stepfunc(computation=compu, histogram=True, needs_random_generator=True)
        sf.gen_code()
        simu = CagenSimulator(sf)

        for i in range(20):
            simu.step_pure_py()

    @pytest.mark.skipif("not HAVE_WEAVE")
    def test_run_nondeterministic_weave(self):
        # implement nazim fatès density classifier
        compu = cagen.DualRuleCellularAutomaton(184, 232, 0.1)
        sf = cagen.automatic_stepfunc(computation=compu, histogram=True, needs_random_generator=True)
        simu = CagenSimulator(sf)

        for i in range(50):
            simu.step_inline()

    @pytest.mark.xfail("not HAVE_DTYPE_AS_INDEX")
    def test_compare_nondeterministic_pure(self):
        compu = cagen.DualRuleCellularAutomaton(184, 232, 0)
        sf = cagen.automatic_stepfunc(size=(100,), computation=compu, histogram=True, needs_random_generator=True)
        sf.gen_code()
        simu = CagenSimulator(sf)

        br = cagen.BinRule(rule=232, config=simu.get_config())

        for i in range(20):
            simu.step_pure_py()
            br.step_pure_py()

            assert_arrays_equal(simu.get_config(), br.get_config())

    @pytest.mark.skipif("not HAVE_WEAVE")
    def test_compare_nondeterministic_weave(self):
        compu = cagen.DualRuleCellularAutomaton(184, 232, 1)
        sf = cagen.automatic_stepfunc(size=(100,), computation=compu, needs_random_generator=True, histogram=True)
        sf.gen_code()
        simu = CagenSimulator(sf)

        br = cagen.BinRule(rule=184, config=simu.get_config())

        for i in range(50):
            simu.step_inline()
            br.step_inline()

            assert_arrays_equal(simu.get_config(), br.get_config())

    @pytest.mark.xfail("not HAVE_DTYPE_AS_INDEX")
    def test_compare_evil_random_pure(self):
        rule_a = 30
        rule_b = 184
        rando = ZerosThenOnesRandom(1001)
        compu = cagen.DualRuleCellularAutomaton(rule_a, rule_b, 0.5)
        sf = cagen.automatic_stepfunc(size=(100,), computation=compu,
                                      needs_random_generator=True,
                                      random_generator=rando, histogram=True)
        sf.gen_code()
        simu = CagenSimulator(sf)

        br = cagen.BinRule(rule=rule_a, config=simu.get_config())

        for i in range(10):
            simu.step_pure_py()
            br.step_pure_py()

            assert_arrays_equal(simu.get_config(), br.get_config())

        br2 = cagen.BinRule(rule=rule_b, config=simu.get_config())

        for i in range(19):
            simu.step_pure_py()
            br2.step_pure_py()

            assert_arrays_equal(simu.get_config(), br2.get_config())

    @pytest.mark.xfail("not HAVE_DTYPE_AS_INDEX")
    def test_dualrail_prettyprint(self):
        compu = cagen.DualRuleCellularAutomaton(184, 232, 0.2)
        sf = cagen.automatic_stepfunc(size=(100,), computation=compu, histogram=True, needs_random_generator=True)
        pretty_result = compu.pretty_print()
        print pretty_result
        assert pretty_result == '''000  100  010  110  001  101  011  111  
                                        
 0    0    0    1   1/0   1   0/1   1   
probability: 0.2 / 0.8'''
