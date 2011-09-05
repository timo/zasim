from zasim.elementarytools import minimize_rule_number
from zasim.cagen import VonNeumannNeighbourhood, elementary_digits_and_values
import numpy as np
from time import time, sleep
import os
import multiprocessing
import math
import Queue


neigh = VonNeumannNeighbourhood()
rule = np.zeros(2 ** 5, dtype=np.dtype("i"))
start_num = 2 ** 32
try:
    with open("smaller_results.txt", "r") as old_results:
        old_results.seek(-1000, os.SEEK_END)
        lastdata = old_results.read().replace("\n", "<")
        numbers = lastdata.split("<")
        numbers = map(int, numbers)
        start_num = max(numbers)
except IOError:
    pass


print "resuming from %d" % (start_num)

known_bits = multiprocessing.Array("B", int(math.ceil(start_num / 8.0) + 10), lock=False)
print "array len is", len(known_bits)
program_running = multiprocessing.Value('f', 1)
array_lock = multiprocessing.RLock()

def set_bits(bits):
    with array_lock:
        for bit in bits:
            known_bits[bit / 8] |= 1 >> (bit % 8)

def ask_bit(bit):
    with array_lock:
        return (known_bits[bit / 8] & (1 >> (bit % 8))) > 0

def deal_with_range(start, stop, skip, data_queue):
    cache_hits = 0
    starttime = time()

    for rule_nr in range(start, stop, skip):
        if ask_bit(rule_nr):
            cache_hits += 1
            continue
        for digit in range(len(rule)):
            if rule_nr & (2 ** digit) > 0:
                rule[digit] = 1
            else:
                rule[digit] = 0
        dav = elementary_digits_and_values(neigh, 2, rule)
        lower, (route, _), cache = minimize_rule_number(neigh, dav)
        if lower < rule_nr:
            nom = [lower] + cache.keys()
            set_bits(nom)
            data_queue.put(nom)

    print "range(%d, %d, %d) took %s - %d cache hits" % (start, stop, skip, time() - starttime, cache_hits)

def master():
    def write_out_results(queue):
        with open("find_results.txt", "a") as results:
            while program_running.value > 0:
                try:
                    data = queue.get(timeout=1)
                    results.write("<".join(map(str,data)))
                    results.write("\n")
                except Queue.Empty:
                    print "timed out. program_running.value = ", program_running.value

        print "done writing out results"

    queue = multiprocessing.Queue(100)
    write_proc = multiprocessing.Process(target=write_out_results, args=(queue,))
    write_proc.start()
    processes = []
    chunksize = 1000
    for bunch in range(start_num / chunksize):
        while len(processes) >= 3:
            for proc in processes:
                if not proc.is_alive():
                    processes.remove(proc)
                    proc.join()
            sleep(0.1)
        proc = multiprocessing.Process(target=deal_with_range,
            args = (start_num - bunch * chunksize,
                    start_num - bunch * chunksize - chunksize,
                    -1, queue))
        proc.start()
        processes.append(proc)
        assert write_proc.is_alive()
    for proc in processes:
        print "joining a process"
        proc.join()
    program_running.value = 0
    print "finished. setting program_running.value = ", program_running.value
    write_proc.join()

if __name__ == "__main__":
    master()
