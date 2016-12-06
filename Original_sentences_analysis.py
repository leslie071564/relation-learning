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

def process_knp_file(knp_file, seperate=[], debug=False):
    #event_NP_counts = Counter()
    event_NP_counts = {'r': Counter(), 'm': Counter(), 'f': Counter()}
    sent_data = ""
    for line in iter(open(knp_file, 'r').readline, ""):
        sent_data += line
        if line.strip() == "EOS":
            try:
                result = knp.result(sent_data.decode('utf-8'))
                NP_list = get_NP_list(result, seperate[:])
                if debug:
                    print "Sentence: %s" % get_orig_sent(result)
                for place in ['r', 'm', 'f']:
                    event_NP_counts[place].update(NP_list[place])
                    if debug:
                        print "<%s> %s" % (place, " ".join(filter(lambda x: x not in seperate, NP_list[place])))
                if debug:
                    print ""
            except:
                sys.stderr.write("knp processing error.\n")
                pass
            #if NP_list != None:
            #    print " ".join(NP_list) 
            sent_data = ""

    return event_NP_counts

def get_orig_sent(result):
    return "".join([x.midasi for x in result.mrph_list()])
    #return " ".join([x.repname for x in result.mrph_list()])

def get_noun(comp_str):
    if '+' not in comp_str:
        return comp_str
    comp_str = comp_str.split('+')[-2:]
    if len(comp_str[-1].split('/')[0]) == 1:
        return "+".join(comp_str)
    return comp_str[-1]

def get_NP_list(result, seperate):
    #NP_list = []
    NP_list = {'r':[], 'm':[], 'f':[]}
    now_place = 'r'
    noun_postfix = ""
    compound_postfix = ""
    for mrph in reversed(result.mrph_list()):
        mrph_rep = mrph.repname
        if now_place != 'f' and mrph_rep == seperate[0]:
            seperate.pop(0)
            if seperate == []:
                now_place = 'f'
            else:
                now_place = 'm'
            
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
                #NP_list.append("%s+%s" % (mrph_rep, compound_postfix))
                NP_list[now_place].append("%s+%s" % (mrph_rep, compound_postfix))
                compound_postfix = ""
            continue
        if noun_postfix:
            if mrph.hinsi == u"名詞":
                #NP_list.append("%s+%s" % (mrph_rep, noun_postfix))
                NP_list[now_place].append("%s+%s" % (mrph_rep, noun_postfix))
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
            #NP_list.append(mrph_rep)
            NP_list[now_place].append(mrph_rep)
            continue

    for place in ['r', 'm', 'f']:
        noun_list = map(get_noun, NP_list[place])
        noun_list = map(lambda x: x.encode('utf-8'), noun_list)
        NP_list[place] = noun_list
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

def get_context_words(event_id, seperate_list, debug=False):
    np_counter = process_knp_file("%s/%s.txt" % (ORIG_KNP_DIR, event_id), seperate_list, debug=debug)
    return dict(np_counter)
    

if __name__ == "__main__":
    pass
