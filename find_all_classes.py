from zasim.elementarytools import minimize_rule_number
from zasim.cagen import elementary_digits_and_values
from zasim import cagen
import numpy as np
from time import time, sleep
import os
import multiprocessing
import Queue

filepath = "find_results.txt"

neigh = cagen.VonNeumannNeighbourhood()
rule = np.zeros(2 ** len(neigh.offsets), dtype=np.dtype("i"))
maximum_number = 2 ** (2 ** len(neigh.offsets))
try:
    with open(filepath, "r") as old_results:
        old_results.seek(-1000, os.SEEK_END)
        lastdata = old_results.read().replace("\n", "<")
        numbers = lastdata.split("<")
        numbers = map(int, numbers)
        start_num = max(numbers)
except IOError:
    start_num = maximum_number


print "resuming from %d" % (start_num)

known_bits = multiprocessing.Array("B", int(maximum_number / 8 + 10), lock=False)
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

def find_old_bits():
    try:
        print "going to fill up the known_bits array from old data."
        starttime = time()
        with open(filepath, "r") as old_results:
            count = 0
            for line in old_results:
                numbers = line.strip().split("<")
                numbers = map(int, numbers)
                numbers = [num for num in numbers if num < start_num]
                set_bits(numbers)
                count += 1
        print "done! yay. took me %s seconds for %d lines" % (time() - starttime, count)
    except IOError:
        print "could not fill up the known_bits array."

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
            nom = cache.keys()
            set_bits(nom)
            data_queue.put(nom)

    print "range(%d, %d, %d) took %s - %d cache hits" % (start, stop, skip, time() - starttime, cache_hits)

def master():
    find_old_bits()
    def write_out_results(queue):
        with open(filepath, "a") as results:
            while program_running.value > 0:
                try:
                    data = queue.get(timeout=1)
                    data.sort()
                    results.write("<".join(map(str,data)))
                    results.write("\n")
                except Queue.Empty:
                    print "timed out. program_running.value = ", program_running.value

        print "done writing out results"

    queue = multiprocessing.Queue(100)
    write_proc = multiprocessing.Process(target=write_out_results, args=(queue,))
    write_proc.start()
    processes = []
    num_done = 0
    last_done_time = time()
    try:
        process_limit = multiprocessing.cpu_count()
    except NotImplementedError:
        process_limit = 2
    process_limit += 1

    chunksize = min(1000, start_num / (process_limit * 2))

    for bunch in range(start_num / chunksize):
        while len(processes) >= process_limit:
            for proc in processes:
                if not proc.is_alive():
                    processes.remove(proc)
                    proc.join()
                    num_done += chunksize
                    if num_done % (chunksize * (process_limit + 3)) == 0:
                        time_taken = time() - last_done_time
                        print "%d nums took %s time" % (chunksize, time_taken / (process_limit + 3))
                        last_done_time = time()

            sleep(0.1)
        proc = multiprocessing.Process(target=deal_with_range,
            args = (max(1, start_num - bunch * chunksize),
                    max(0, start_num - bunch * chunksize - chunksize),
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