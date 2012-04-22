"""This module offers a store for multiple previous configurations and for
comparing, analysing and accessing prior configurations."""

import numpy as np

class HistoryStore(object):
    """Attach this class to a simulator and it will store the last `store_amount`
    configs. Use `to_array` to create an array with one more dimension than each
    configuration from the stored configurations.

    When a simulator emits `snapshot_restored`, the history will be cleared."""

    def __init__(self, sim, store_amount=-1):
        super(HistoryStore, self).__init__()

        self._sim = sim

        self._sim.updated.connect(self.after_step)
        self._sim.changed.connect(self.change_conf)
        self._sim.snapshot_restored.connect(self.clear_history)

        self.store_amount = store_amount

        self._store = []

    def _prepare_conf(self, conf):
        """Re-implement this method to preprocess the configuration before storing it.
        This may include things like cutting out a slice of it."""
        return conf.copy()

    def after_step(self, change=False):
        if change:
            # remove the newest entry
            self._store.pop()
        self._store.append(self._prepare_conf(self._sim.get_config()))

        if len(self._store) > self.store_amount and not self.store_amount == -1:
            self._store.pop(0)

    def change_conf(self):
        self.after_step(True)

    def clear_history(self):
        self._store = []

        # XXX is this always correct?
        self.after_step()

    def to_array(self):
        """Put the latest configurations into an array that has one dimension
        more than each configuration."""

        result = np.empty((len(self._store),) + self._store[-1].shape,
                          dtype=self._store[-1].dtype)

        for idx, conf in enumerate(self._store):
            result[idx] = conf

        return result

