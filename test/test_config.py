from __future__ import absolute_import

from zasim import config

import pytest

class TestConfig:
    def test_random_1d(self):
        a = config.RandomInitialConfiguration()
        arr = a.generate((1000,))
        assert not any(arr > 2)
        assert not any(arr < 0)
        assert any(arr == 0)
        assert any(arr == 1)
        assert len(arr) == 10

        b = config.RandomInitialConfiguration(base=3)
        brr = b.generate((1000,))
        assert not any(brr > 3)
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
