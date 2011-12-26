"""This module offers a store for multiple previous configurations and for
comparing, analysing and accessing prior configurations."""

import numpy as np

class HistoryStore(object):
    """Attach this class to a simulator and it will store the last `store_amount`
    configs. Use `to_array` to create an array with one more dimension than each
    configuration from the stored configurations."""

    def __init__(self, sim, store_amount=-1):
        super(HistoryStore, self).__init__()

        self._sim = sim

        self._sim.updated.connect(self.after_step)
        self._sim.changed.connect(self.change_conf)

        self.store_amount = store_amount

        self._store = []

    def after_step(self, change=False):
        if change:
            # remove the newest entry
            self._store.pop()
        self._store.append(self._sim.get_config().copy())

        if len(self._store) > self.store_amount and not self.store_amount == -1:
            self._store.pop(0)

    def change_conf(self):
        self.after_step(True)

    def to_array(self):
        """Put the latest configurations into an array that has one dimension
        more than each configuration."""

        result = np.empty((len(self._store),) + self._store[-1].shape,
                          dtype=self._store[-1].dtype)

        for idx, conf in enumerate(self._store):
            result[idx] = conf

        return result

