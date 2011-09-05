from zasim import elementarytools

class TestCAGen:
    def test_flip_values(self):
        dav = [dict(l=0, r=0, result_value=1),
               dict(l=0, r=1, result_value=2),
               dict(l=1, r=0, result_value=3),
               dict(l=1, r=1, result_value=4)]
        res = elementarytools.flip_values(dav, [("l", "r")])
        expected = [dict(l=0, r=0, result_value=1),
            dict(l=0, r=1, result_value=3),
            dict(l=1, r=0, result_value=2),
            dict(l=1, r=1, result_value=4)]
        assert res == expected
