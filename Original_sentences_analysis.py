# -*- coding: utf-8 -*-
import sys
import shelve
from collections import Counter
import codecs
sys.stdout = codecs.getwriter('utf-8')(sys.stdout)
from pyknp import KNP
knp = KNP()

import ConfigParser
config = ConfigParser.RawConfigParser()
config.read('./data_location.ini')
IDS_FILE = config.get('Raw', 'IDS')
ORIG_TEXT_DIR = config.get('Original', 'ORIG_TEXT_DIR')
ORIG_KNP_DIR = config.get('Original', 'ORIG_KNP_DIR')
ORIG_PROCESSED_DIR = config.get('Original', 'ORIG_PROCESSED_DIR')
skip_list = [u"．．．", u"こと", u"切手", u"ポスト"]

def print_knp_task():
    for num in open(IDS_FILE, 'r').readlines():
        num = num.rstrip()
        text_file = "%s/%s.txt" % (ORIG_TEXT_DIR, num)
        knp_file = "%s/%s.txt" % (ORIG_KNP_DIR, num)
        print "cat %s | juman | knp -tab > %s && echo %s" % (text_file, knp_file, num)

def process_knp_file(knp_file):
    event_NP_counts = Counter()
    sent_data = ""
    for line in iter(open(knp_file, 'r').readline, ""):
        sent_data += line
        if line.strip() == "EOS":
            try:
                result = knp.result(sent_data.decode('utf-8'))
                NP_list = get_NP_list(result)
                event_NP_counts.update(NP_list)
            except:
                sys.stderr.write("knp processing error.\n")
                pass
            #if NP_list != None:
            #    print " ".join(NP_list) 
            sent_data = ""
    return event_NP_counts


def get_NP_list(result):
    NP_list = []
    cmp_flag = False
    for mrph in reversed(result.mrph_list()):
        if mrph.hinsi != u"名詞" and not cmp_flag:
            continue
        if mrph.bunrui == u"数詞":
            arg = u"[数詞]"
        else:
            arg = mrph.genkei
        if cmp_flag:
            NP_list[-1] = "%s+%s" % (arg, NP_list[-1])
        else:
            NP_list.append(arg)
        # maintain flag.
        if u"複合←" in mrph.fstring:
            cmp_flag = True
        else:
            cmp_flag = False
    # option: take only head words.
    pruned_NP_list = []
    for np in NP_list:
        np_parts = np.split('+')
        head = np_parts[-1]
        if head == u"[数詞]":
            continue
        if len(head) > 1:
            pruned_NP_list.append(head)
        elif len(head) == 1 and len(np_parts) >= 2:
            pruned_NP_list.append("%s+%s" % (np_parts[-2], head))
    return pruned_NP_list

def print_processed_task():
    for num in open(IDS_FILE, 'r').readlines():
        num = num.rstrip()
        text_file = open("%s/%s.txt" % (ORIG_TEXT_DIR, num), 'r')
        processed_file = open("%s/%s.txt" % (ORIG_PROCESSED_DIR, num), 'w')
        for line in text_file.readlines():
            line = line.rstrip()
            NP_list = get_NP_list(line)
            out = " ".join(NP_list) + '\n'
            processed_file.write(out.encode('utf-8'))

def get_context_words(event_id):
    np_counter = process_knp_file("%s/%s.txt" % (ORIG_KNP_DIR, event_id))
    return dict(np_counter)
    

'''
def print_processed_task(self):
    for index, pred in enumerate([self.pred1, self.pred2]):
        given_cases = pred.args.keys()
        for case in CASE_ENG:
            if case in given_cases:
                continue
            base_filename = "%s_%s%s.txt" % (self.num, case, index+1)
            print u"grep 用言代表表記:%s %s/%s > %s/%s" % (pred.verb_rep, raw_dir, base_filename, processed_dir, base_filename)
'''

if __name__ == "__main__":
    np_counts = process_knp_file("%s/104401.txt" % (ORIG_KNP_DIR))
    #for np, counts in np_counts.items():
    #    print counts, np

