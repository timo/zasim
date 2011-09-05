from zasim.elementarytools import minimize_rule_number
from zasim.cagen import VonNeumannNeighbourhood, elementary_digits_and_values
import numpy as np
from time import time
import os
import multiprocessing
import math
import Queue


neigh = VonNeumannNeighbourhood()
rule = np.zeros(2 ** 5, dtype=np.dtype("i"))
start_num = 2 ** 32
try:
    with open("smaller_results.txt", "r") as old_results:
        old_results.seek(-200, os.SEEK_END)
        lastline = old_results.readlines()[-1].strip()
        numbers = lastline.split(" < ")
        numbers = map(int, numbers)
        start_num = max(numbers)
except IOError:
    pass


print "resuming from %d" % (start_num)

known_bits = multiprocessing.Array("c", math.ceil(start_num / 8.0))
program_running = multiprocessing.Value('d', 1)

def set_bit(bit):
    known_bits[bit / 8] |= 1 >> (bit % 8)

def ask_bit(bit):
    return (known_bits[bit / 8] & (1 >> (bit % 8))) > 0

def deal_with_range(start, stop, skip, data_queue):
    counter = 0
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
            for number in nom:
                set_bit(number)
            data_queue.put(nom)
            counter += len(nom)

    print "range(%d, %d, %d) took %s" % (start, stop, skip, time() - starttime)

def master():
    def write_out_results():
        with open("find_results.txt", "a") as results:
            while program_running.value != 0:
                try:
                    data = queue.get_nowait()
                    data.sort()
                    results.write("<".join(data))
                    results.write("\n")
                except Queue.Empty:
                    pass

    queue = multiprocessing.Queue(100)
    write_proc = multiprocessing.Process(target=write_out_results)
    write_proc.start()
    processes = []
    start_num = 2 ** 32
    for bunch in range(50):
        while len(processes) > 10:
            for proc in processes:
                if not proc.is_alive():
                    processes.remove(proc)
        proc = multiprocessing.Process(target=deal_with_range,
            args = (start_num - bunch * 100, start_num - bunch * 100 - 100, -1, queue))
        proc.start()
        processes.append(proc)
