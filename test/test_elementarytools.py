from zasim import elementarytools
from zasim.cagen import SimpleNeighbourhood, VonNeumannNeighbourhood

import pytest

class TestCAGen:
    def test_permutations_indexmap(self):
        neigh = SimpleNeighbourhood("lr", [(-1,), (1,)])
        dav = [dict(l=0, r=0, result_value=1),
               dict(l=0, r=1, result_value=2),
               dict(l=1, r=0, result_value=3),
               dict(l=1, r=1, result_value=4)]
        imap = elementarytools.permutation_to_index_map(neigh, {"l":"r", "r":"l"})
        res = elementarytools.apply_index_map(dav, imap)
        expected = [dict(l=0, r=0, result_value=1),
            dict(l=0, r=1, result_value=3),
            dict(l=1, r=0, result_value=2),
            dict(l=1, r=1, result_value=4)]
        assert res == expected

    def test_flip_horizontal_results_only(self):
        neigh = SimpleNeighbourhood("lr", [(-1,0), (1,0)])
        results = [1, 2, 3, 4]
        res = elementarytools.flip_h(neigh, results)
        expected = [1, 3, 2, 4]
        assert res == expected
