from __future__ import absolute_import

from zasim import cagen
from zasim.features import *
from zasim import config

from .testutil import *

import pytest

class TestSparseLoop:
    def body_compare_sparse_life(self, weave=False):
        conf = config.RandomInitialConfiguration().generate((25, 25))
        life_full   = cagen.GameOfLife(config=conf, histogram=True, activity=True)
        life_sparse = cagen.GameOfLife(config=conf, histogram=True, activity=True,
                                       sparse_loop=True)

        for i in range(20):
            if weave:
                life_full.step_inline()
                life_sparse.step_inline()
            else:
                life_full.step_pure_py()
                life_sparse.step_pure_py()

            print life_sparse.t.sparse_list[:life_sparse.t.activity[1]]

            assert_arrays_equal(life_full.get_config(), life_sparse.get_config())
            assert life_full.t.activity[1] == life_sparse.t.activity[1]
            assert life_full.t.activity[0] >= life_sparse.t.activity[0]

    @pytest.mark.skipif("not HAVE_MULTIDIM")
    @pytest.mark.skipif("not HAVE_WEAVE")
    def test_compare_sparse_life_weave(self):
        self.body_compare_sparse_life(True)

    @pytest.mark.skipif("not HAVE_MULTIDIM")
    def test_compare_sparse_life_pure(self):
        self.body_compare_sparse_life(False)

    def body_compare_sparse_elementary(self, rule_num, weave=False):
        conf = cagen.RandomInitialConfiguration().generate((100,))
        elem_full   = cagen.ElementarySimulator(config=conf, rule=rule_num, activity=True)
        elem_sparse = cagen.ElementarySimulator(config=conf, rule=rule_num, activity=True,
                                                sparse_loop=True)

        for i in range(20):
            if weave:
                elem_full.step_inline()
                elem_sparse.step_inline()
            else:
                elem_full.step_pure_py()
                elem_sparse.step_pure_py()

            print elem_sparse.t.sparse_list, elem_sparse.t.activity[1]

            assert_arrays_equal(elem_full.get_config(), elem_sparse.get_config())
            assert elem_full.t.activity[1] == elem_sparse.t.activity[1]
            assert elem_full.t.activity[0] >= elem_sparse.t.activity[0]

    @pytest.mark.skipif("not HAVE_WEAVE")
    def test_compare_sparse_elementary_weave(self, rule_num):
        self.body_compare_sparse_elementary(rule_num, True)

    def test_compare_sparse_elementary_pure(self, rule_num):
        self.body_compare_sparse_elementary(rule_num, False)

def pytest_generate_tests(metafunc):
    if "rule_num" in metafunc.funcargnames:
        for i in INTERESTING_BINRULES:
            metafunc.addcall(funcargs=dict(rule_num=i))
