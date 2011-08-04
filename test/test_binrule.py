import CA
import numpy as np
from random import randrange
from testutil import assert_arrays_equal

class TestBinRule:
    def test_compare_weave_pure(self, ruleNum, random=True):
        """compare the weave version of binRule with the pure python one"""
        if random:
            br = CA.binRule(110, randrange(10,30), 1, CA.binRule.INIT_RAND)
        else:
            content = np.array([1,1,1,1,1,0,1,0,1,1,0,0,0,1,1,0,1,0,0,0,1,0,0,0])
            br = CA.binRule(110, len(content), 1, CA.binRule.INIT_ZERO)
            br.setConf(content)
        br2 = CA.binRule(110, len(br.getConf()), 1, CA.binRule.INIT_ZERO)
        br2.setConf(br.getConf())
        assert_arrays_equal(br.getConf(), br2.getConf())
        for i in range(5):
            print "step", i
            br.updateAllCellsWeaveInline()
            br2.updateAllCellsPy()
            assert_arrays_equal(br.getConf(), br2.getConf())

def pytest_generate_tests(metafunc):
    if "ruleNum" in metafunc.funcargnames:
        for i in range(128):
            metafunc.addcall(funcargs=dict(ruleNum=i))