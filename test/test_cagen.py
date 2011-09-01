from __future__ import absolute_import
from zasim import ca, cagen
from random import randrange
from .testutil import *
from itertools import repeat, chain, product

import pytest

MIN_SIZE, MAX_SIZE = 5, 25

class EvilRandom(object):
    def __init__(self, iterator):
        self.iterator = iter(iterator)

    def random(self):
        return self.iterator.next()

class ZerosThenOnesRandom(EvilRandom):
    def __init__(self, zeros):
        super(ZerosThenOnesRandom, self).__init__(
            chain(repeat(0.0, zeros), repeat(1.0)))

class TestCAGen:
    @pytest.mark.skipif("not ca.HAVE_WEAVE")
    def test_compare_weaves(self, rule_num):
        size = randrange(MIN_SIZE, MAX_SIZE)
        br = ca.binRule(rule_num, size, 1, ca.binRule.INIT_RAND)
        br2 = cagen.BinRule((size-2,), rule=rule_num, config=br.getConf().copy()[1:-1])

        for i in range(10):
            br.updateAllCellsWeaveInline()
            br2.step_inline()
            compare_arrays(br.getConf(), br2.cconf)

        assert_arrays_equal(br.getConf(), br2.cconf)

    @pytest.mark.skipif("not ca.HAVE_WEAVE")
    def test_gen_weave_only(self, tested_rule_num):
        confs = TESTED_BINRULE[tested_rule_num]
        br = cagen.BinRule(rule=tested_rule_num, config=confs[0][1:-1])
        pretty_print_binrule(br.rule)
        assert_arrays_equal(br.cconf, confs[0])
        for conf in confs[1:]:
            br.step_inline()
            assert_arrays_equal(br.cconf, conf)

    def test_gen_pure_only(self, tested_rule_num):
        confs = TESTED_BINRULE[tested_rule_num]
        br = cagen.BinRule(rule=tested_rule_num, config=confs[0][1:-1])
        pretty_print_binrule(br.rule)
        assert_arrays_equal(br.cconf, confs[0])
        for conf in confs[1:]:
            br.step_pure_py()
            assert_arrays_equal(br.cconf, conf)

    def test_compare_pures(self, rule_num):
        size = randrange(MIN_SIZE, MAX_SIZE)
        br = ca.binRule(rule_num, size, 1, ca.binRule.INIT_RAND)
        br2 = cagen.BinRule((size-2,), rule=rule_num, config=br.getConf().copy()[1:-1])

        # are the rules the same?
        assert_arrays_equal(br.ruleIdx, br2.rule)

        assert_arrays_equal(br.getConf(), br2.cconf)

        for i in range(10):
            br.updateAllCellsPy()
            br2.step_pure_py()
            compare_arrays(br.getConf(), br2.cconf)

        assert_arrays_equal(br.getConf(), br2.cconf)

    def test_run_nondeterministic_pure(self, rule_num):
        size = randrange(MIN_SIZE, MAX_SIZE)
        br = cagen.BinRule((size-2,), deterministic=False, rule=rule_num)

        for i in range(10):
            br.step_pure_py()

    @pytest.mark.skipif("not ca.HAVE_WEAVE")
    def test_run_nondeterministic_weave(self, rule_num):
        size = randrange(MIN_SIZE, MAX_SIZE)
        br = cagen.BinRule((size-2,), deterministic=False, rule=rule_num)

        for i in range(10):
            br.step_inline()

    def test_immutability(self):
        br = cagen.BinRule(size=(10,))
        with pytest.raises(AssertionError):
            br.stepfunc.set_target(br)
        with pytest.raises(AttributeError):
            br.stepfunc.add_code("headers", "int foo = 42")
        with pytest.raises(AttributeError):
            br.stepfunc.add_py_hook("pre_compute", "print 'hello'")

    def test_pretty_print_rules_1d(self):
        br = cagen.BinRule(size=(10,),rule=110)

        res = br.pretty_print()
        res = "\n".join(a.strip() for a in res.split("\n"))

        assert res == """000  100  010  110  001  101  011  111

0    1    1    1    0    1    1    0"""

    @pytest.mark.skipif("not cagen.HAVE_MULTIDIM")
    def test_pretty_print_rules_2d(self):
        conf = np.zeros((10, 10), int)
        t = cagen.TestTarget(config=conf)

        l = cagen.LinearCellLoop()
        acc = cagen.TwoDimStateAccessor()
        neigh = cagen.VonNeumannNeighbourhood()
        compute = cagen.ElementaryCellularAutomatonBase(1515361445)
        copier = cagen.SimpleBorderCopier()

        sf = cagen.WeaveStepFunc(loop=l, accessor=acc, neighbourhood=neigh,
                           extra_code=[copier, compute], target=t)

        res = compute.pretty_print()
        res = "\n".join(a.strip() for a in res.split("\n"))
        assert res == """0    0    1    1    0    0    1    1    0    0    1    1    0    0    1    1    0    0    1    1    0    0    1    1    0    0    1    1    0    0    1    1
000  100  000  100  010  110  010  110  000  100  000  100  010  110  010  110  001  101  001  101  011  111  011  111  001  101  001  101  011  111  011  111
0    0    0    0    0    0    0    0    1    1    1    1    1    1    1    1    0    0    0    0    0    0    0    0    1    1    1    1    1    1    1    1

1    0    1    0    0    1    0    1    0    0    1    0    1    0    0    1    0    1    0    0    1    0    1    0    0    1    0    1    1    0    1    0"""

    @pytest.mark.skipif("not cagen.HAVE_MULTIDIM")
    @pytest.mark.skipif("not ca.HAVE_WEAVE")
    def test_weave_game_of_life(self):
        t = cagen.TestTarget(config=GLIDER[0])

        l = cagen.TwoDimCellLoop()
        acc = cagen.TwoDimStateAccessor()
        neigh = cagen.MooreNeighbourhood()
        compute = cagen.LifeCellularAutomatonBase()
        copier = cagen.TwoDimZeroReader()
        sf = cagen.WeaveStepFunc(loop=l, accessor=acc, neighbourhood=neigh,
                    extra_code=[copier, compute], target=t)

        sf.gen_code()

        for glider_conf in GLIDER[1:]:
            sf.step_inline()
            assert_arrays_equal(glider_conf, t.cconf[1:-1, 1:-1])

    @pytest.mark.skipif("not cagen.HAVE_MULTIDIM")
    def test_pure_game_of_life(self):
        t = cagen.TestTarget(config=GLIDER[0])

        l = cagen.TwoDimCellLoop()
        acc = cagen.TwoDimStateAccessor()
        neigh = cagen.MooreNeighbourhood()
        compute = cagen.LifeCellularAutomatonBase()
        copier = cagen.TwoDimZeroReader()
        sf = cagen.WeaveStepFunc(loop=l, accessor=acc, neighbourhood=neigh,
                    extra_code=[copier, compute], target=t)

        sf.gen_code()

        for glider_conf in GLIDER[1:]:
            sf.step_pure_py()
            assert_arrays_equal(glider_conf, t.cconf[1:-1,1:-1])

    @pytest.mark.skipif("not cagen.HAVE_MULTIDIM")
    def test_pretty_print_config_2d(self, capsys):
        gconf = GLIDER[0]
        conf = np.zeros((gconf.shape[0] + 2, gconf.shape[1] + 2))
        conf[1:-1,1:-1] = gconf

        # manually create the border.
        conf[3,6] = 1
        conf[6,2] = 1

        pp = cagen.build_array_pretty_printer(conf.shape, ((1, 1), (1, 1)))
        pp(conf)
        out, err = capsys.readouterr()
        assert out == """\
,,,,,,,
, #   ,
,  #  ,
,###  %
,     ,
,     ,
,,%,,,,
"""

    def test_pretty_print_config_1d(self, capsys):
        # test pretty-printing with left-border 2 and right-border 1
        # without any extra at the side
        conf = np.array([1,1, 0,1,0,1,1, 1])
        pp = cagen.build_array_pretty_printer(conf.shape, ((2, 1),))
        pp(conf)
        out, err = capsys.readouterr()
        assert out == """%% # ##,\n"""

        # test pretty-printing with left-border and right-border 3
        conf = np.array([1,1,0, 1,0,1,1,0,  1,0,1])
        pp = cagen.build_array_pretty_printer(conf.shape, ((3, 3),), ((0, 0),))
        pp(conf)
        out, err = capsys.readouterr()
        assert out == """%%,# ## %,%\n"""

    def test_pretty_print_config_1d_extra(self, capsys):
        conf = np.array([1,1,1, 0,0,0,1,1,1, 0,0,0])

        # add one extra cell from beyond the border
        pp = cagen.build_array_pretty_printer(conf.shape, ((3, 3),), ((1, 1),))
        pp(conf)
        out, err = capsys.readouterr()
        assert out == ",%%%   ###,,,%\n"

        # two extra cells on the left, none on the right
        pp = cagen.build_array_pretty_printer(conf.shape, ((3, 3),), ((2, 0),))
        pp(conf)
        out, err = capsys.readouterr()
        assert out == ",,%%%   ###,,,\n"

        # six extra fields. this is the maximum possible
        pp = cagen.build_array_pretty_printer(conf.shape, ((3, 3),), ((6, 6),))
        pp(conf)
        out,err = capsys.readouterr()
        assert out == "%%%,,,%%%   ###,,,%%%,,,\n"

        with pytest.raises(AssertionError):
            pp = cagen.build_array_pretty_printer(conf.shape, ((3, 3),), ((7, 6),))

    def body_weave_nondeterministic_stepfunc_1d(self, inline=True):
        conf = np.ones(1000)
        # this rule would set all fields to 1 at every step.
        # since we use a nondeterministic step func, this will amount to about
        # half ones, half zeros
        br = cagen.BinRule(deterministic=False, config=conf, rule=0)
        if inline:
            br.step_inline()
        else:
            br.step_pure_py()
        assert not br.cconf.all(), "oops, all fields have been executed in the"\
                                  " nondeterministic step function"
        assert br.cconf.any(), "oops, no fields have been executed in the"\
                              " nondeterministic step function"

        # and now a sanity check for rule 0
        br2 = cagen.BinRule(size=(1000,), rule=0)
        assert not br2.cconf.all(), "why was the random config all ones?"
        assert br2.cconf.any(), "why was the random config all zeros?"
        if inline:
            br2.step_inline()
        else:
            br2.step_pure_py()
        assert not br2.cconf.any(), "huh, rule0 was supposed to set all"\
                             " fields to zero!"

    @pytest.mark.skipif("not ca.HAVE_WEAVE")
    def test_weave_nondeterministic_stepfunc_id(self):
        self.body_weave_nondeterministic_stepfunc_1d()

    def test_pure_nondeterministic_stepfunc_id(self):
        self.body_weave_nondeterministic_stepfunc_1d(False)

    def body_nondeterministic_stepfunc_2d(self, inline=True):
        conf = np.ones((100, 100))

        def make_stepfunc(target, deterministic=False):
            computer = cagen.ElementaryCellularAutomatonBase(rule=0)
            sf = cagen.WeaveStepFunc(
                    loop=cagen.TwoDimCellLoop() if deterministic else
                          cagen.TwoDimNondeterministicCellLoop(),
                    accessor=cagen.TwoDimStateAccessor(),
                    neighbourhood=cagen.VonNeumannNeighbourhood(),
                    extra_code=[cagen.SimpleBorderCopier(),
                        computer], target=target)
            sf.gen_code()
            return sf

        t = cagen.TestTarget(config=conf.copy())
        uno = make_stepfunc(t)
        if inline:
            uno.step_inline()
        else:
            uno.step_pure_py()
        assert not uno.getConf().all(), "oops, no cells have been executed :("
        assert uno.getConf().any(), "oops, all cells have been executed :("

        # this is just a sanity check to see if the stepfunc does what we think
        t = cagen.TestTarget(config=conf.copy())
        dos = make_stepfunc(t, True)
        if inline:
            dos.step_inline()
        else:
            dos.step_pure_py()
        assert not dos.getConf().any(), "rule 0 was supposed to turn all"\
                                    "fields into 0. huh?"


    @pytest.mark.skipif("not cagen.HAVE_MULTIDIM")
    @pytest.mark.skipif("not ca.HAVE_WEAVE")
    def test_weave_nondeterministic_stepfunc_2d(self):
        self.body_nondeterministic_stepfunc_2d()

    @pytest.mark.skipif("not cagen.HAVE_MULTIDIM")
    def test_pure_nondeterministic_stepfunc_2d(self):
        self.body_nondeterministic_stepfunc_2d(False)

    def test_nondeterministic_leak_data_1d(self):
        class EvilRandom(object):
            def __init__(self, zeros):
                self.zeros = zeros

            def random(self):
                self.zeros -= 1
                if self.zeros >= 0:
                    return 0.0
                else:
                    return 1.0

        rand = ZerosThenOnesRandom(101)
        conf = np.ones(100)

        t = cagen.TestTarget(config=conf)
        computer = cagen.ElementaryCellularAutomatonBase(0)

        stepfunc = cagen.WeaveStepFunc(
                loop=cagen.LinearNondeterministicCellLoop(random_generator=rand),
                accessor=cagen.LinearStateAccessor(),
                neighbourhood=cagen.ElementaryFlatNeighbourhood(),
                extra_code=[cagen.SimpleBorderCopier(),
                    computer], target=t)

        stepfunc.gen_code()
        stepfunc.step_pure_py()
        assert not stepfunc.getConf().any(), "the step func should have"\
                                            " turned all fields into zeros"
        stepfunc.step_pure_py()
        assert not stepfunc.getConf().any(), "there should be no ones in the"\
                                            " config at all."
        stepfunc.step_pure_py()
        assert not stepfunc.getConf().any(), "there should be no ones in the"\
                                            " config at all."

    @pytest.mark.skipif("not cagen.HAVE_MULTIDIM")
    def test_nondeterministic_leak_data_2d(self):
        rand = ZerosThenOnesRandom(101)
        conf = np.ones((10,10))

        t = cagen.TestTarget(config=conf)
        computer = cagen.ElementaryCellularAutomatonBase(0)

        stepfunc = cagen.WeaveStepFunc(
                loop=cagen.TwoDimNondeterministicCellLoop(random_generator=rand),
                accessor=cagen.TwoDimStateAccessor(),
                neighbourhood=cagen.VonNeumannNeighbourhood(),
                extra_code=[cagen.SimpleBorderCopier(),
                    computer], target=t)

        stepfunc.gen_code()
        stepfunc.step_pure_py()
        assert not stepfunc.getConf().any(), "the step func should have"\
                                            " turned all fields into zeros"
        stepfunc.step_pure_py()
        assert not stepfunc.getConf().any(), "there should be no ones in the"\
                                            " config at all."
        stepfunc.step_pure_py()
        assert not stepfunc.getConf().any(), "there should be no ones in the"\
                                            " config at all."

    @pytest.mark.skipif("not cagen.HAVE_MULTIDIM")
    def test_compare_twodim_slicing_border_copier_simple_border_copier(self):
        conf = np.zeros((5, 5), int)
        for num, pos in enumerate(product(range(0, 5), range(0, 5))):
            conf[pos] = 10 + num
        t1 = cagen.TestTarget(config=conf)
        t2 = cagen.TestTarget(config=conf)

        names = list("abcde" + "fg" + "hci" + "jk" + "lmnop")
        positions = ((-2, -2), (-1, -2), (0, -2), (1, -2), (2, -2),
                    (-2, -1),                             (2, -1),
                    (-2,  0),           (0,  0),          (2,  0),
                    (-2, -1),                             (2, -1),
                    (-2, -2), (-1, -2), (0, -2), (1, -2), (2,  2))
        n1 = cagen.SimpleNeighbourhood(names, positions)
        n2 = cagen.SimpleNeighbourhood(names, positions)

        sf1 = cagen.WeaveStepFunc(
                loop=cagen.TwoDimCellLoop(),
                accessor=cagen.TwoDimStateAccessor(),
                neighbourhood=n1,
                extra_code=[cagen.TwoDimSlicingBorderCopier()], target=t1)
        sf2 = cagen.WeaveStepFunc(
                loop=cagen.TwoDimCellLoop(),
                accessor=cagen.TwoDimStateAccessor(),
                neighbourhood=n2,
                extra_code=[cagen.SimpleBorderCopier()], target=t2)

        sf1.gen_code()
        sf2.gen_code()

        print t1.cconf
        print t2.cconf
        assert_arrays_equal(t1.cconf, t2.cconf)

def pytest_generate_tests(metafunc):
    if "rule_num" in metafunc.funcargnames:
        for i in INTERESTING_BINRULES:
            metafunc.addcall(funcargs=dict(rule_num=i))
    if "tested_rule_num" in metafunc.funcargnames:
        for i in TESTED_BINRULE.keys():
            metafunc.addcall(funcargs=dict(tested_rule_num=i))
