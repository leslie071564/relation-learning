# -*- coding: utf-8 -*-
import sys
import shelve
from itertools import product
import argparse
import ConfigParser
config = ConfigParser.RawConfigParser()
config.read('./data_location.ini')
gold_db = shelve.open(config.get('Raw', 'GOLD'), flag='r')

def process_gold(raw_gold):
    if raw_gold == ['null']:
        return [], {}
    if raw_gold == ['X']:
        return [], {}
    gold_single = []
    gold_multiple = {}
    # remove quasi-alignments and g2.
    raw_gold = map(lambda x: x.replace("\'", ""), raw_gold)
    raw_gold = map(lambda x: x.replace("g2", "g"), raw_gold)
    # expand multi-alignments
    for g in raw_gold:
        if '/' not in g:
            if 'p' in g:
                continue
            if g == 'd-d':
                continue
            gold_single.append(g)
            continue
        # multi:
        c1s, c2s = g.split('-')
        all_possibility = product(c1s.split('/'), c2s.split('/')) 
        all_possibility = map(lambda x: "%s-%s" % (x[0], x[1]), all_possibility)
        all_possibility = filter(lambda x: 'p' not in x, all_possibility)
        all_possibility = filter(lambda x: 'd-d' != x, all_possibility)
        if all_possibility:
            gold_multiple[g] = all_possibility
    return gold_single, gold_multiple

def process_id(ID, output, debug=False):
    if output == ['null']:
        output = []
    gold_raw = gold_db[ID]
    gold_single, gold_multiple = process_gold(gold_raw)
    correct = set(gold_single) & set(output)
    for key, all_possibility in gold_multiple.items():
        correct_multiple = set(all_possibility) & set(output)
        if correct_multiple == set():
            continue
        correct.add(key)
    # debug 
    if debug:
        print "#", ID
        print "gold raw", " ".join(gold_raw)
        print "gold single", " ".join(gold_single), len(gold_single)
        print "gold multiple", " ".join(gold_multiple), len(gold_multiple)
        print "output", " ".join(output), len(output)
        print "correct", " ".join(correct), len(correct)
    # debug 
    return {'gold' : len(gold_single) + len(gold_multiple), 'output': len(output), 'correct' : len(correct)}

def process_file(result_file, debug=False):
    CORRECT = 0
    GOLD = 0
    OUTPUT = 0
    for line in open(result_file).readlines():
        if line.startswith("@") or line.startswith("Accuracy") or line.startswith("#"):
            continue
        # get output.
        line = line.rstrip().split("_")
        ID, cf1, cf2 = line[:3]
        output = line[3:]
        id_counts = process_id(ID, output)

        GOLD += id_counts['gold']
        OUTPUT += id_counts['output']
        CORRECT += id_counts['correct']
    #return {'gold': GOLD, 'output': OUTPUT, 'correct': CORRECT}
    return GOLD, OUTPUT, CORRECT


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', "--result_file", action="store", dest="result_file")
    parser.add_argument('-d', "--debug", action="store_true", default=False, dest="debug")
    options = parser.parse_args() 

    GOLD, OUTPUT, CORRECT = process_file(options.result_file, options.debug)

    # print result.
    if CORRECT == 0:
        print "precision:0 (0/%d)" % (OUTPUT)
        print "recall:0 (0/%d)" % (GOLD)
        print "AER:1"
    else:
        print "precision: %.4f (%d/%d)" % (float(CORRECT)/OUTPUT, CORRECT, OUTPUT)
        print "recall: %.4f (%d/%d)" % (float(CORRECT)/GOLD, CORRECT, GOLD)
        print "AER: %.4f" % (1 - 2*float(CORRECT)/(GOLD+OUTPUT))
