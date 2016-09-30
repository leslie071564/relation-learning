# -*- coding: utf-8 -*-
import sys
import shelve
import re
import codecs
import itertools
import argparse
from itertools import product
#sys.stdin = codecs.getwriter('utf-8')(sys.stdin)
#sys.stderr = codecs.getwriter('utf-8')(sys.stderr)
#sys.stdout = codecs.getwriter('utf-8')(sys.stdout)
from subprocess import check_output
from utils import *
sys.path.append("../nnAlignLearn")
from RetrieveOriginalData import *
import ConfigParser
config = ConfigParser.RawConfigParser()
config.read('./data_location.ini')
ARG_FILE = config.get('Raw', 'ARG_FILE')
IDS_FILE = config.get('Raw', 'IDS')
GOLD_ALIGN = shelve.open(config.get('Raw', 'GOLD'), flag='r')

class Event(object):
    def __init__(self, num):
        self.num = num
        self._set_basic()
        self._set_original()

    def _set_basic(self):
        # retrieve the line of current event pair.
        command = "head -n %s %s | tail -n 1" % (self.num, ARG_FILE)
        line = check_output(command, shell=True)
        pa1_str = re.sub(r"[{{}}]", "", line.split(" ")[1])
        pa2_str = re.sub(r"[{{}}]", "", line.split(" ")[3])
        self.charStr_raw = "%s => %s" % (pa1_str, pa2_str)
        # set predicates and arguments.
        self.pred1 = Predicate(pa1_str)
        self.pred2 = Predicate(pa2_str)
        verb_key = "%s-%s" % (self.pred1.verb_raw, self.pred2.verb_raw)
        self.pred1._set_arguments(verb_key)
        self.pred2._set_arguments(verb_key)

    def _set_original(self):
        vkeys1 = self.pred1.get_vstr_for_keys()
        vkeys2 = self.pred2.get_vstr_for_keys()
        cckey1 = self.pred1.get_ccstr_for_keys()
        cckey2 = self.pred2.get_ccstr_for_keys()
        # get all keys for origin sentences retrieval.
        all_keys = []
        for i in itertools.product(cckey1, vkeys1, cckey2, vkeys2):
            full_key = "%s%s-%s%s" % (i[0], i[1], i[2], i[3])
            all_keys.append(full_key)
        sys.stderr.write("key strings:\n%s\n" % ("\n".join(all_keys)))
        # get original sentences. 
        self.orig_sentences = []
        mrph_sets = []
        for key in all_keys:
            if get_original_sentence(key.decode('utf-8')) == None:
                continue
            for val, sent in get_original_sentence(key):
                # check for repeated sentences.
                new_mrph = check_redundant_sentence(mrph_sets, sent)
                if new_mrph !=None:
                    self.orig_sentences.append(sent)
                    mrph_sets.append(new_mrph)


    def export(self):
        event_dict = {}
        event_dict['pred1'] = self.pred1.export()
        event_dict['pred2'] = self.pred2.export()
        event_dict['charStr_raw'] = self.charStr_raw
        event_dict['orig_sentences'] = self.orig_sentences
        return event_dict


class Predicate(object):
    def __init__(self, pa_str):
        self.verb_raw = pa_str.split(":")[0]
        self.args_raw = pa_str.split(":")[1:]
        self._set_predicate(self.verb_raw)

    def _set_predicate(self, verb_str):
        regex = re.compile(verb_pattern)
        self.negation, self.voice, self.verb_stem = regex.search(verb_str).groups()
        self.verb_rep = get_verb_form(self.verb_stem, self.voice)
    def _set_arguments(self, verb_key):
        self.args = {}
        regex = re.compile(noun_pattern)
        for arg_str in self.args_raw:
            place, case, class_num, noun_str = regex.search(arg_str).groups()
            if class_num == "":     #like 2g酷/こくa
                self.args[case] = noun_str.split(",")
            else :
                class_id = "%s%s%s" % (place, case, class_num)
                self.args[case] = replace_word(verb_key, class_id)
                if self.args[case] == []:
                    noun_str = re.sub(r"[\(\)]", "", noun_str)
                    noun_str = re.sub(r"\.", "", noun_str)
                    self.args[case] = noun_str.split(",")
    def get_vstr_for_keys(self, changeVoice=False): 
        v_basic = []
        for p in self.verb_rep.split('+'):
            if p in [u"れる/れる", u"せる/せる"]:
                if u"する/する" in v_basic:
                    v_basic.remove(u"する/する")
                continue
            v_basic.append(p)
        v_basic = '+'.join(v_basic)

        neg_suffix = NEG2SUFFIX[self.negation]
        vstr_for_key = v_basic + neg_suffix
        if changeVoice:
            voice_suffix = VOICE2SUFFIX[changeVoice]
        else :
            voice_suffix = VOICE2SUFFIX[self.voice]
        vstr_for_keys = map(lambda x: "%s%s" % (vstr_for_key, x), voice_suffix)
        return vstr_for_keys 

    def get_ccstr_for_keys(self):
        ccstr_for_keys = [""]
        for case in CASE_ENG_K:
            if case not in self.args.keys():
                continue
            temp = []
            for noun in self.args[case]:
                temp.extend(map(lambda x: "%s|%s|%s" % (noun, ENG_KATA_K[case], x), ccstr_for_keys))
            ccstr_for_keys = temp
        return ccstr_for_keys

    def export(self):
        predicate_dict = {}
        predicate_dict['verb_rep'] = self.verb_rep
        predicate_dict['verb_stem'] = self.verb_stem
        predicate_dict['args'] = self.args
        return predicate_dict


def build_event_db(db_loc, ids_file):
    event_db = shelve.open(db_loc)
    for num in open(ids_file, 'r').readlines():
        sys.stderr.write("# %s\n" % (num))
        num = num.rstrip()
        ev = Event(int(num))
        event_db[num] = ev.export()
    

### testing:
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', "--store_db", action="store", dest="store_db")
    parser.add_argument('-n', "--num", action="store", dest="num")
    options = parser.parse_args() 
    if options.store_db != None:
        build_event_db(options.store_db, IDS_FILE)
    elif options.num != None:
        # debug mode.
        ev = Event(options.num)
    else:
        sys.stderr.write("no option specified.\n")

        
