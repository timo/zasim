from zasim import ca
import numpy as np
from random import randrange
from testutil import assert_arrays_equal, INTERESTING_BINRULES

import pytest

class TestBinRule:
    @pytest.mark.skipif("not ca.HAVE_WEAVE")
    def test_compare_weave_pure(self, ruleNum, random=True):
        """compare the weave version of binRule with the pure python one"""
        if random:
            br = ca.binRule(ruleNum, randrange(10,30), 1, ca.binRule.INIT_RAND)
        else:
            content = np.array([1,1,1,1,1,0,1,0,1,1,0,0,0,1,1,0,1,0,0,0,1,0,0,0])
            br = ca.binRule(ruleNum, len(content), 1, ca.binRule.INIT_ZERO)
            br.setConf(content)
        br2 = ca.binRule(ruleNum, len(br.getConf()), 1, ca.binRule.INIT_ZERO)
        br2.setConf(br.getConf())
        assert_arrays_equal(br.getConf(), br2.getConf())
        for i in range(5):
            print "step", i
            br.updateAllCellsWeaveInline()
            br2.updateAllCellsPy()
            assert_arrays_equal(br.getConf(), br2.getConf())

    def test_init_sanitized(self):
        # since random is random, we have to do this several times
        # to ensure that this test can fail if the binRule constructor
        # misbehaves
        for i in range(20):
            br = ca.binRule(110, 10, 1, ca.binRule.INIT_RAND)
            conf = br.getConf().copy()

            # do the edges match up?
            assert conf[0] == conf[-2]
            assert conf[-1] == conf[1]

    def test_setconf_sanitized(self):
        br = ca.binRule(110, 10, 1, ca.binRule.INIT_RAND)
        conf = br.getConf().copy()

        # make the edges not match up any more
        conf[:2] = [1, 0]
        conf[-2:] = [0, 1]

        # set the config
        br.setConf(conf)

        # has the config been corrected?
        assert conf[0] == conf[-2]
        assert conf[-1] == conf[1]

# TODO test setconf and stuff, sanitizing of confs etc., running pure only for pypy, ...

def pytest_generate_tests(metafunc):
    if "ruleNum" in metafunc.funcargnames:
        for i in INTERESTING_BINRULES:
            metafunc.addcall(funcargs=dict(ruleNum=i))
