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
            #result = knp.result(sent_data.decode('utf-8'))
            #NP_list = get_NP_list(result)
            #sys.exit()
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

def get_noun(comp_str):
    if '+' not in comp_str:
        return comp_str
    comp_str = comp_str.split('+')[-2:]
    if len(comp_str[-1].split('/')[0]) == 1:
        return "+".join(comp_str)
    return comp_str[-1]

def get_NP_list(result):
    NP_list = []
    noun_postfix = ""
    compound_postfix = ""
    for mrph in reversed(result.mrph_list()):
        mrph_rep = mrph.repname
        if not mrph_rep:
            noun_postfix = ""
            compound_postfix = ""
            continue
        if mrph.bunrui in [u"数詞", u"人名"]:
            mrph_rep = "[%s]" % (mrph.bunrui)

        # compound noun or noun phrase.
        if compound_postfix:
            if u"複合←" in mrph.fstring:
                compound_postfix = "%s+%s" % (mrph_rep, compound_postfix)
            else:
                comp_noun = "%s+%s" % (mrph_rep, compound_postfix)
                NP_list.append("%s+%s" % (mrph_rep, compound_postfix))
                compound_postfix = ""
            continue
        if noun_postfix:
            if mrph.hinsi == u"名詞":
                NP_list.append("%s+%s" % (mrph_rep, noun_postfix))
            noun_postfix = ""
            continue
        # normal noun.
        if mrph.hinsi == u"名詞" and u"複合←" in mrph.fstring:
            compound_postfix = mrph_rep
            continue
        elif mrph.hinsi == u"接尾辞":
            noun_postfix = mrph_rep
            continue
        elif mrph.hinsi == u"名詞":
            NP_list.append(mrph_rep)
            continue

    NP_list = map(get_noun, NP_list)
    return NP_list

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
    

if __name__ == "__main__":
    np_counts = process_knp_file("%s/104401.txt" % (ORIG_KNP_DIR))
    for np, counts in np_counts.items():
        if counts < 5:
            continue
        print counts, np

