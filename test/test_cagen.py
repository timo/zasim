from __future__ import absolute_import

from zasim import cagen
from zasim.features import *

from .testutil import *

from random import randrange
from itertools import product

import numpy as np
import pytest

MIN_SIZE, MAX_SIZE = 5, 25

class TestCAGen:
    @pytest.mark.skipif("not HAVE_WEAVE")
    def test_gen_weave_only(self, tested_rule_num):
        confs = TESTED_BINRULE_WITHOUT_BORDERS[tested_rule_num]
        br = cagen.BinRule(rule=tested_rule_num, config=confs[0])
        pretty_print_binrule(br.rule)
        assert_arrays_equal(br.get_config(), confs[0])
        for conf in confs[1:]:
            br.step_inline()
            assert_arrays_equal(br.get_config(), conf)

    def test_gen_pure_only(self, tested_rule_num):
        confs = TESTED_BINRULE_WITHOUT_BORDERS[tested_rule_num]
        br = cagen.BinRule(rule=tested_rule_num, config=confs[0])
        pretty_print_binrule(br.rule)
        assert_arrays_equal(br.get_config(), confs[0])
        for conf in confs[1:]:
            br.step_pure_py()
            assert_arrays_equal(br.get_config(), conf)

    def test_run_nondeterministic_pure(self, rule_num):
        size = randrange(MIN_SIZE, MAX_SIZE)
        br = cagen.BinRule((size,), nondet=0.5, rule=rule_num)

        for i in range(10):
            br.step_pure_py()

    @pytest.mark.skipif("not HAVE_WEAVE")
    def test_run_nondeterministic_weave(self, rule_num):
        size = randrange(MIN_SIZE, MAX_SIZE)
        br = cagen.BinRule((size-2,), nondet=0.5, rule=rule_num)

        for i in range(10):
            br.step_inline()

    def test_immutability(self):
        br = cagen.BinRule(size=(10,))
        with pytest.raises(AssertionError):
            br._step_func.set_target(br)
        with pytest.raises(AttributeError):
            br._step_func.add_weave_code("headers", "int foo = 42")
        with pytest.raises(AttributeError):
            br._step_func.add_py_code("pre_compute", "print 'hello'")

    def test_pretty_print_rules_1d(self):
        br = cagen.BinRule(size=(10,),rule=110)

        res = br.pretty_print()
        res = "\n".join(a.strip() for a in res.split("\n"))

        assert res == """000  100  010  110  001  101  011  111

0    1    1    1    0    1    1    0"""

    @pytest.mark.skipif("not HAVE_MULTIDIM")
    def test_pretty_print_rules_2d(self):
        conf = np.zeros((10, 10), int)
        t = cagen.Target(config=conf)

        l = cagen.TwoDimCellLoop()
        acc = cagen.SimpleStateAccessor()
        neigh = cagen.VonNeumannNeighbourhood()
        compute = cagen.ElementaryCellularAutomatonBase(1515361445)
        copier = cagen.SimpleBorderCopier()

        sf = cagen.StepFunc(loop=l, accessor=acc, neighbourhood=neigh,
                           extra_code=[copier, compute], target=t)

        res = compute.pretty_print()
        res = "\n".join(a.strip() for a in res.split("\n"))
        assert res == """0    0    1    1    0    0    1    1    0    0    1    1    0    0    1    1    0    0    1    1    0    0    1    1    0    0    1    1    0    0    1    1
000  100  000  100  010  110  010  110  000  100  000  100  010  110  010  110  001  101  001  101  011  111  011  111  001  101  001  101  011  111  011  111
0    0    0    0    0    0    0    0    1    1    1    1    1    1    1    1    0    0    0    0    0    0    0    0    1    1    1    1    1    1    1    1

1    0    1    0    0    1    0    1    0    0    1    0    1    0    0    1    0    1    0    0    1    0    1    0    0    1    0    1    1    0    1    0"""

    @pytest.mark.skipif("not HAVE_MULTIDIM")
    @pytest.mark.skipif("not HAVE_WEAVE")
    def test_weave_game_of_life(self):
        sim = cagen.GameOfLife(config=GLIDER[0])

        for glider_conf in GLIDER[1:]:
            sim.step_inline()
            assert_arrays_equal(glider_conf, sim.get_config())

    @pytest.mark.skipif("not HAVE_MULTIDIM")
    def test_pure_game_of_life(self):
        sim = cagen.GameOfLife(config=GLIDER[0])

        for glider_conf in GLIDER[1:]:
            sim.step_pure_py()
            assert_arrays_equal(glider_conf, sim.get_config())

    def body_weave_nondeterministic_stepfunc_1d(self, inline=True, sparse=False):
        conf = np.ones(1000)
        # this rule would set all fields to 1 at every step.
        # since we use a nondeterministic step func, this will amount to about
        # half ones, half zeros
        br = cagen.BinRule(nondet=0.5, config=conf, rule=0,
                           sparse_loop=sparse, activity=sparse, needs_random_generator=sparse)
        if inline:
            br.step_inline()
        else:
            br.step_pure_py()
        assert not br.get_config().all(), "oops, all fields have been executed in the"\
                                  " nondeterministic step function"
        assert br.get_config().any(), "oops, no fields have been executed in the"\
                              " nondeterministic step function"

        # and now a sanity check for rule 0
        br2 = cagen.BinRule(size=(1000,), rule=0,
                            sparse_loop=sparse, activity=sparse, needs_random_generator=sparse)
        assert not br2.get_config().all(), "why was the random config all ones?"
        assert br2.get_config().any(), "why was the random config all zeros?"
        if inline:
            br2.step_inline()
        else:
            br2.step_pure_py()
        assert not br2.get_config().any(), "huh, rule0 was supposed to set all"\
                             " fields to zero!"

    @pytest.mark.skipif("not HAVE_WEAVE")
    def test_weave_nondeterministic_stepfunc_id(self):
        self.body_weave_nondeterministic_stepfunc_1d()

    def test_pure_nondeterministic_stepfunc_id(self):
        self.body_weave_nondeterministic_stepfunc_1d(False)

    @pytest.mark.skipif("not HAVE_WEAVE")
    def test_weave_nondeterministic_sparse_stepfunc_id(self):
        self.body_weave_nondeterministic_stepfunc_1d(True, True)

    def test_pure_nondeterministic_sparse_stepfunc_id(self):
        self.body_weave_nondeterministic_stepfunc_1d(False, True)

    def body_nondeterministic_stepfunc_2d(self, inline=True):
        conf = np.ones((100, 100))

        def make_stepfunc(target, deterministic=False):
            computer = cagen.ElementaryCellularAutomatonBase(rule=0)
            sf = cagen.StepFunc(
                    loop=cagen.TwoDimCellLoop() if deterministic else
                          cagen.TwoDimNondeterministicCellLoop(),
                    accessor=cagen.SimpleStateAccessor(),
                    neighbourhood=cagen.VonNeumannNeighbourhood(),
                    extra_code=[cagen.SimpleBorderCopier(),
                        computer] +
                           ([] if deterministic else [cagen.RandomGenerator()]),
                    target=target)
            sf.gen_code()
            return sf

        t = cagen.Target(config=conf.copy())
        uno = make_stepfunc(t)
        if inline:
            uno.step_inline()
        else:
            uno.step_pure_py()
        assert not uno.get_config().all(), "oops, no cells have been executed :("
        assert uno.get_config().any(), "oops, all cells have been executed :("

        # this is just a sanity check to see if the stepfunc does what we think
        t = cagen.Target(config=conf.copy())
        dos = make_stepfunc(t, True)
        if inline:
            dos.step_inline()
        else:
            dos.step_pure_py()
        assert not dos.get_config().any(), "rule 0 was supposed to turn all"\
                                    "fields into 0. huh?"


    @pytest.mark.skipif("not HAVE_MULTIDIM")
    @pytest.mark.skipif("not HAVE_WEAVE")
    def test_weave_nondeterministic_stepfunc_2d(self):
        self.body_nondeterministic_stepfunc_2d()

    @pytest.mark.skipif("not HAVE_MULTIDIM")
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

        t = cagen.Target(config=conf)
        computer = cagen.ElementaryCellularAutomatonBase(0)

        stepfunc = cagen.StepFunc(
                loop=cagen.OneDimNondeterministicCellLoop(),
                accessor=cagen.SimpleStateAccessor(),
                neighbourhood=cagen.ElementaryFlatNeighbourhood(),
                extra_code=[cagen.SimpleBorderCopier(),
                    cagen.RandomGenerator(random_generator=rand),
                    computer], target=t)

        stepfunc.gen_code()
        stepfunc.step_pure_py()
        assert not stepfunc.get_config().any(), "the step func should have"\
                                            " turned all fields into zeros"
        stepfunc.step_pure_py()
        assert not stepfunc.get_config().any(), "there should be no ones in the"\
                                            " config at all."
        stepfunc.step_pure_py()
        assert not stepfunc.get_config().any(), "there should be no ones in the"\
                                            " config at all."

    @pytest.mark.skipif("not HAVE_MULTIDIM")
    def test_nondeterministic_leak_data_2d(self):
        rand = ZerosThenOnesRandom(101)
        conf = np.ones((10,10))

        t = cagen.Target(config=conf)
        computer = cagen.ElementaryCellularAutomatonBase(0)

        stepfunc = cagen.StepFunc(
                loop=cagen.TwoDimNondeterministicCellLoop(),
                accessor=cagen.SimpleStateAccessor(),
                neighbourhood=cagen.VonNeumannNeighbourhood(),
                extra_code=[cagen.SimpleBorderCopier(),
                    cagen.RandomGenerator(random_generator=rand),
                    computer], target=t)

        stepfunc.gen_code()
        stepfunc.step_pure_py()
        assert not stepfunc.get_config().any(), "the step func should have"\
                                            " turned all fields into zeros"
        stepfunc.step_pure_py()
        assert not stepfunc.get_config().any(), "there should be no ones in the"\
                                            " config at all."
        stepfunc.step_pure_py()
        assert not stepfunc.get_config().any(), "there should be no ones in the"\
                                            " config at all."

    def body_compare_twodim_slicing_border_copier_simple_border_copier(self, names, positions):
        conf = np.zeros((4, 4), int)
        for num, pos in enumerate(product(range(0, 4), range(0, 4))):
            conf[pos] = int(str(pos[0] + 1) + str(pos[1] + 1))
        t1 = cagen.Target(config=conf)
        t2 = cagen.Target(config=conf)

        names = list("abXde" + "fg" + "hcI" + "Jk" + "lmnop")
        positions = ((-2, -2), (-1, -2), (0, -2), (1, -2), (2, -2),
                     (-2, -1),                             (2, -1),
                     (-2,  0),           (0,  0),          (2,  0),
                     (-2,  1),                             (2,  1),
                     (-2,  2), (-1,  2), (0,  2), (1,  2), (2,  2))
        n1 = cagen.SimpleNeighbourhood(names, positions)
        n2 = cagen.SimpleNeighbourhood(names, positions)

        class MyComputation(cagen.Computation):
            def visit(self):
                super(MyComputation, self).visit()
                self.code.add_weave_code("compute",
                        "result = c * 10;")
                self.code.add_py_code("compute",
                        "result = c * 10")

        sf1 = cagen.StepFunc(
                loop=cagen.TwoDimCellLoop(),
                accessor=cagen.SimpleStateAccessor(),
                neighbourhood=n1,
                target=t1,
                extra_code=[cagen.TwoDimSlicingBorderCopier(), MyComputation()])
        sf2 = cagen.StepFunc(
                loop=cagen.TwoDimCellLoop(),
                accessor=cagen.SimpleStateAccessor(),
                neighbourhood=n2,
                target=t2,
                extra_code=[cagen.SimpleBorderCopier(), MyComputation()])

        sf1.gen_code()
        sf2.gen_code()

        simo1 = cagen.CagenSimulator(sf1)
        simo2 = cagen.CagenSimulator(sf2)

        print simo1.get_config().T
        print simo2.get_config().T
        assert_arrays_equal(simo1.get_config(), simo2.get_config())

        if HAVE_WEAVE:
            simo1.step_inline()
            simo2.step_inline()
        else:
            simo1.step_pure_py()
            simo2.step_pure_py()

        print simo1.get_config().T
        print simo2.get_config().T
        assert_arrays_equal(simo1.get_config(), simo2.get_config())

        if HAVE_WEAVE:
            simo1.step_pure_py()
            simo2.step_pure_py()

            print simo1.get_config().T
            print simo2.get_config().T
            assert_arrays_equal(simo1.get_config(), simo2.get_config())

    @pytest.mark.skipif("not HAVE_MULTIDIM")
    def test_compare_twodim_slicing_border_copier_simple_border_copier(self):
        names = list("abXde" + "fg" + "hcI" + "Jk" + "lmnop")
        positions = ((-2, -2), (-1, -2), (0, -2), (1, -2), (2, -2),
                     (-2, -1),                             (2, -1),
                     (-2,  0),           (0,  0),          (2,  0),
                     (-2,  1),                             (2,  1),
                     (-2,  2), (-1,  2), (0,  2), (1,  2), (2,  2))
        self.body_compare_twodim_slicing_border_copier_simple_border_copier(names, positions)

    @pytest.mark.skipif("not HAVE_MULTIDIM")
    def test_compare_slicing_simple_border_copier_asymmetric_neighbourhood(self):
        names = list("abXd" + "ef" + "gcI" + "Jklm")
        positions = ((-2, -2), (-1, -2), (0, -2), (1, -2),
                     (-2, -1),                    (1, -1),
                     (-2,  0),           (0,  0), (1,  0),
                     (-2,  1), (-1,  1), (0,  1), (1,  1))
        self.body_compare_twodim_slicing_border_copier_simple_border_copier(names, positions)
        names = list("abXd" + "ef" + "gcI" + "Jklm")
        positions = ((-1, -2), (0, -2), (1, -2), (2, -2),
                     (-1, -1),                   (2, -1),
                     (-1,  0), (0,  0),          (2,  0),
                     (-1,  1), (0,  1), (1,  1), (2,  1))
        self.body_compare_twodim_slicing_border_copier_simple_border_copier(names, positions)
        names = list("abXd" + "ecf" + "gI" + "Jklm")
        positions = ((-1, -1), (0, -1), (1, -1), (2, -1),
                     (-1,  0), (0,  0),          (2,  0),
                     (-1,  1),                   (2,  1),
                     (-1,  2), (0,  2), (1,  2), (2,  2))
        self.body_compare_twodim_slicing_border_copier_simple_border_copier(names, positions)
        names = list("abXd" + "ecf" + "gI" + "Jklm")
        positions = ((-2, -1), (-1, -1), (0, -1), (1, -1),
                     (-2,  0),           (0,  0), (1,  0),
                     (-2,  1),                    (1,  1),
                     (-2,  2), (-1,  2), (0,  2), (1,  2))
        self.body_compare_twodim_slicing_border_copier_simple_border_copier(names, positions)

    def body_histogram_1d(self, inline=False, deterministic=True):
        br = cagen.BinRule((100,), rule=105, histogram=True, nondet=1.0 if deterministic else 0.5)
        assert_arrays_equal(br.t.histogram, np.bincount(br.get_config()))
        for i in range(10):
            if inline:
                br.step_inline()
            else:
                br.step_pure_py()
            assert_arrays_equal(br.t.histogram, np.bincount(br.get_config()))

    @pytest.mark.skipif("not HAVE_BINCOUNT")
    def test_histogram_1d_pure(self):
        self.body_histogram_1d()

    @pytest.mark.skipif("not HAVE_WEAVE")
    def test_histogram_1d_weave(self):
        self.body_histogram_1d(inline=True)

    @pytest.mark.skipif("not HAVE_BINCOUNT")
    def test_histogram_1d_nondet_pure(self):
        self.body_histogram_1d(deterministic=False)

    @pytest.mark.skipif("not HAVE_WEAVE")
    def test_histogram_1d_nondet_weave(self):
        self.body_histogram_1d(inline=True, deterministic=False)


    def body_histogram_2d(self, inline=False, deterministic=True):
        t = cagen.Target((20, 20))

        compute = cagen.LifeCellularAutomatonBase()
        if deterministic:
            l = cagen.TwoDimCellLoop()
        else:
            l = cagen.TwoDimNondeterministicCellLoop(probab=0.4)

        acc = cagen.SimpleStateAccessor()
        neigh = cagen.MooreNeighbourhood()
        copier = cagen.SimpleBorderCopier()
        histogram = cagen.SimpleHistogram()
        extra_code = [copier, compute, histogram]

        if not deterministic:
            extra_code.append(cagen.RandomGenerator())

        sf = cagen.StepFunc(loop=l, accessor=acc, neighbourhood=neigh,
                        extra_code=extra_code, target=t)

        sf.gen_code()
        sim = cagen.CagenSimulator(sf)
        assert_arrays_equal(sim.t.histogram,
                            np.bincount(np.ravel(sim.get_config())))
        for i in range(10):
            if inline:
                sim.step_inline()
            else:
                sim.step_pure_py()
            assert_arrays_equal(sim.t.histogram,
                                np.bincount(np.ravel(sim.get_config())))

    @pytest.mark.skipif("not HAVE_BINCOUNT")
    @pytest.mark.skipif("not HAVE_MULTIDIM")
    def test_histogram_2d_pure(self):
        self.body_histogram_2d()

    @pytest.mark.skipif("not HAVE_WEAVE")
    @pytest.mark.skipif("not HAVE_MULTIDIM")
    def test_histogram_2d_weave(self):
        self.body_histogram_2d(inline=True)

    @pytest.mark.skipif("not HAVE_BINCOUNT")
    @pytest.mark.skipif("not HAVE_MULTIDIM")
    def test_histogram_2d_nondet_pure(self):
        self.body_histogram_2d(deterministic=False)

    @pytest.mark.skipif("not HAVE_WEAVE")
    @pytest.mark.skipif("not HAVE_MULTIDIM")
    def test_histogram_2d_nondet_weave(self):
        self.body_histogram_2d(inline=True, deterministic=False)

    def body_beta_asynchronism(self, inline=False):
        fail = True
        for i in range(50):
            try:
                conf = np.zeros((100,), np.dtype("i"))
            except TypeError:
                # pypy compat
                conf = np.zeros(100, np.dtype("i"))
            br = cagen.BinRule(config=conf, rule=255, beta=0.5)

            if inline:
                br.step_inline()
            else:
                br.step_pure_py()

            assert_arrays_equal(br.t.inner, np.ones(100))
            if abs(sum(br.get_config()) - 50) < 10:
                fail = False
                break
        assert not fail, "testing 50 times, never gotten close to half of "\
                   " the fields updating their outer state."

        try:
            conf = np.zeros((100,), np.dtype("i"))
        except TypeError:
            # pypy compat
            conf = np.zeros(100, np.dtype("i"))
        br = cagen.BinRule(config=conf, rule=255, beta=0.5)

        for i in range(20):
            if inline:
                br.step_inline()
            else:
                br.step_pure_py()

        assert_arrays_equal(br.t.inner, br.get_config())

    @pytest.mark.skipif("not HAVE_WEAVE")
    def test_beta_asynchronism_inline(self):
        self.body_beta_asynchronism(True)

    def test_beta_asynchronism_pure(self):
        self.body_beta_asynchronism(False)

    @pytest.mark.skipif("not HAVE_WEAVE")
    @pytest.mark.skipif("not HAVE_MULTIDIM")
    def test_cagen_main(self):
        from zasim.cagen import main

        main.main("--width 90 --pure --steps 10".split(" "))
        main.main("--width 90 --height 30 --pure --steps 10".split(" "))
        main.main("--steps 5 --rule 10".split(" "))
        main.main("--nondet 50 --steps 10 --rule 0x20".split(" "))
        main.main("--nondet 50 --height 20 --steps 10 --rule 0x20".split(" "))
        main.main("--beta 50 --steps 10 --print-rule".split(" "))
        main.main("--base 4 --nondet 20 --steps 10".split(" "))
        main.main("--base 3 --beta 30 --steps 10".split(" "))
        main.main("--beta 30 --pure --activity --steps 10".split(" "))
        main.main("--beta 30 --histogram --steps 10 --print-rule".split(" "))
        main.main("--nondet 50 --activity --steps 10".split(" "))
        main.main("--nondet 40 --histogram --pure --steps 10".split(" "))
        main.main("--beta 30 --life --steps 10 --width 30".split(" "))
        main.main("--nondet 50 --life --activity --steps 10".split(" "))
        main.main("--nondet 40 --histogram --pure --steps 10".split(" "))

def pytest_generate_tests(metafunc):
    if "rule_num" in metafunc.funcargnames:
        for i in INTERESTING_BINRULES:
            metafunc.addcall(funcargs=dict(rule_num=i))
    if "tested_rule_num" in metafunc.funcargnames:
        for i in TESTED_BINRULE.keys():
            metafunc.addcall(funcargs=dict(tested_rule_num=i))
