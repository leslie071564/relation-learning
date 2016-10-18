# -*- coding: utf-8 -*-
import sys
import shelve
import re
import codecs
import os
#sys.stdin = codecs.getwriter('utf-8')(sys.stdin)
#sys.stderr = codecs.getwriter('utf-8')(sys.stderr)
#sys.stdout = codecs.getwriter('utf-8')(sys.stdout)
import itertools
import argparse
from itertools import product
from subprocess import check_output
from utils import *
sys.path.append("../nnAlignLearn")
from RetrieveOriginalData import *
from Original_sentences_analysis import * 
import ConfigParser
config = ConfigParser.RawConfigParser()
config.read('./data_location.ini')
ARG_FILE = config.get('Raw', 'ARG_FILE')
IDS_FILE = config.get('Raw', 'IDS')
GOLD_ALIGN = shelve.open(config.get('Raw', 'GOLD'), flag='r')
ORIG_TEXT_DIR = config.get('Original', 'ORIG_TEXT_DIR')

class Event(object):
    #attributes = ['pred1', 'pred2', 'charStr_raw', 'charStr', 'gold', 'impossible_align', 'cf-num', 'context_word', 'arg_count']
    attributes = ['pred1', 'pred2', 'charStr_raw', 'charStr', 'gold', 'impossible_align', 'arg_count', 'context_word']
    def __init__(self, num, event_dict=None, modify=[], neglect=[]):
        # event_dict: dictionary from which the event instance is build.
        # modify: attribute(s) to be updated.
        # neglect: atttribute(s) not to be set nor modified. 
        self.num = num
        self.neglect = neglect
        if event_dict == None:
            # build instance from scratch.
            self._set_all()
        else:
            # build instance from existing dictionary.
            self.pred1 = Predicate("", event_dict['pred1'])
            self.pred2 = Predicate("", event_dict['pred2'])
            for attr in self.attributes[2:]:
                if attr in neglect:
                    continue
                if attr in modify:
                    exec("self._set_%s()" % attr)
                else:
                    setattr(self, attr, event_dict[attr])

    def _set_all(self):
        pa1_str, pa2_str = self._retrieve_raw_event()
        self.charStr_raw = "%s => %s" % (pa1_str, pa2_str)
        # set predicates and arguments.
        self.pred1 = Predicate(pa1_str)
        self.pred2 = Predicate(pa2_str)
        verb_key = "%s-%s" % (self.pred1.verb_raw, self.pred2.verb_raw)
        self.pred1._set_arguments(verb_key)
        self.pred2._set_arguments(verb_key)

        self._set_charStr()
        self._set_gold()
        self._set_impossible_align()
        self._set_arg_count()
        self._set_context_word()

    def _retrieve_raw_event(self):
        # retrieve the line of current event pair.
        command = "head -n %s %s | tail -n 1" % (self.num, ARG_FILE)
        line = check_output(command, shell=True)
        pa1_str = re.sub(r"[{{}}]", "", line.split(" ")[1])
        pa2_str = re.sub(r"[{{}}]", "", line.split(" ")[3])
        return pa1_str, pa2_str

    def _set_charStr_raw(self):
        pa1_str, pa2_str = self._retrieve_raw_event()
        self.charStr_raw = "%s => %s" % (pa1_str, pa2_str)

    def _set_charStr(self):
        self.charStr = "%s --> %s" % (self.pred1.get_charStr(), self.pred2.get_charStr())

    def _set_gold(self):
        if self.num in GOLD_ALIGN.keys():
            self.gold = process_gold(GOLD_ALIGN[self.num])
        else:
            self.gold = None

    def _set_impossible_align(self):
        given_args1 = self.pred1.args
        given_args2 = self.pred2.args
        self.impossible_align = []
        for case1, case2 in product(given_args1.keys(), given_args2.keys()):
            if set(given_args1[case1]) & set(given_args2[case2]):
                continue
            self.impossible_align.append("%s-%s" % (case1, case2))

    def _set_arg_count(self, remove_redundant=False, print_sent=""):
        if print_sent:
            PRINT_TO_FILE = open(print_sent, 'w')
        vkeys1 = self.pred1.get_vstr_for_keys()
        vkeys2 = self.pred2.get_vstr_for_keys()
        cckey1 = self.pred1.get_ccstr_for_keys()
        cckey2 = self.pred2.get_ccstr_for_keys()
        # get all keys for origin sentences retrieval.
        all_keys = []
        for i in itertools.product(cckey1, vkeys1, cckey2, vkeys2):
            full_key = "%s%s-%s%s" % (i[0], i[1], i[2], i[3])
            all_keys.append(full_key)
        #sys.stderr.write("key strings:\n%s\n" % ("\n".join(all_keys)))
        sys.stderr.write("key strings:\n")
        # get original sentences. 
        self.arg_count = defaultdict(lambda: defaultdict(int))
        for key in all_keys:
            if get_original_sentence(key.decode('utf-8')) == None:
                sys.stderr.write("%s 0\n" % key)
                continue
            original_sentence_of_key = get_original_sentence(key)
            sys.stderr.write("%s %d\n" % (key, len(original_sentence_of_key)))
            for parsed_sent, sent in original_sentence_of_key:
                if print_sent:
                    PRINT_TO_FILE.write(sent+'\n')
                self._update_arg_count(parsed_sent)
        # check for repeated sentences.
        self.arg_count = dict(self.arg_count)
        if remove_redundant:
            self.orig_sentences = remove_redundant_sentence(self.orig_sentences)

    def _update_arg_count(self, parsed_sent):
        PAS = parsed_sent.split(" - ")
        # not working: PAS_components = map(str.split(" "), PAS)    
        PAS_components = map(lambda x: x.split(" "), PAS)
        for pred_index, pa_components in enumerate(PAS_components):
            for arg, case in zip(pa_components[0::2], pa_components[1::2]):
                if case not in KATA_ENG.keys():
                    continue
                arg = "+".join(map(lambda x: x.split('/')[0], arg.split('+')))
                self.arg_count["%s%s" % (KATA_ENG[case.decode('utf-8')], pred_index+1)][arg] += 1

    def print_orig_sentences(self, write_to_file):
        self._set_arg_count(print_sent=write_to_file)

    def _set_context_word(self):
        skip = [u"こと"] + sum(self.pred1.args.values(), []) + sum(self.pred2.args.values(), [])
        skip = map(remove_hira, skip)
        raw_context_word = get_context_words(self.num)
        self.context_word = {k : v for k, v in raw_context_word.items() if k not in skip}

    def export(self):
        event_dict = {}
        event_dict['pred1'] = self.pred1.export()
        event_dict['pred2'] = self.pred2.export()
        for attr in self.attributes[2:]:
            if attr in self.neglect:
                continue
            event_dict[attr] = getattr(self, attr)
        return event_dict

    
class Predicate(object):
    attributes = ['verb_stem', 'verb_rep', 'args', 'negation', 'voice']
    def __init__(self, pa_str, pred_dict=None):
        if pred_dict == None:
            self.verb_raw = pa_str.split(":")[0]
            self.args_raw = pa_str.split(":")[1:]
            self._set_predicate(self.verb_raw)
        else:
            for attr in self.attributes:
                exec("self.%s = pred_dict[\'%s\']" % (attr, attr))

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
    
    def get_charStr(self):
        charStr = ""
        for case in self.args.keys():
            arg0 = self.args[case][0]
            charStr += remove_hira(arg0) + ENG_HIRA[case].encode('utf-8')
        charStr += remove_hira(self.verb_rep, keep_plus=True)
        return charStr

    def export(self):
        predicate_dict = {}
        for attr in self.attributes:
            predicate_dict[attr] = getattr(self, attr)
        return predicate_dict


def build_event_db(db_loc, ids_file):
    event_db = shelve.open(db_loc)
    for num in open(ids_file, 'r').readlines():
        sys.stderr.write("# %s\n" % (num))
        num = num.rstrip()
        ev = Event(int(num))
        event_db[num] = ev.export()
    
# now possible: (Event)charStr/charStr_raw/gold
### TODO: (Predicate) negation/voice/verb_raw 
def update(update_list, event_db="/zinnia/huang/EventKnowledge/data/event.db"):
    EVENT_DB = shelve.open(event_db)
    for num in open(IDS_FILE, 'r').readlines():
        num = num.rstrip()
        sys.stderr.write("now updating ...%s\n" % num)
        ev = Event(num, EVENT_DB[num], modify=update_list)
        EVENT_DB[num] = ev.export()
        sys.stderr.write("done\n")
# REMOVE or REWRITE
def print_tasks():
    event_db = "/zinnia/huang/EventKnowledge/data/event.db"
    EVENT_DB = shelve.open(event_db)
    for num in open(IDS_FILE, 'r').readlines():
        num = num.rstrip()
        ev = Event(num, EVENT_DB[num])
        #ev.print_task()
        ev.print_processed_task()

def print_ev_orig_sentences(orig_dir=ORIG_TEXT_DIR, ids=IDS_FILE):
    nums = []
    if type(ids) is list:
        nums = ids
    elif type(ids) is str:
        if not os.path.isfile(ids):
            sys.stderr.write("ids-file not exist!\n")
            return None
        nums = map(str.rstrip, open(ids, 'r').readlines())
    else:
        sys.stderr.write("not valid ids-file/list!\n")
        return None

    for num in nums:
        orig_file = "%s/%s.txt" % (orig_dir, num)
        ev = Event(num)
        ev.print_orig_sentences(orig_file)


### testing:
if __name__ == "__main__":
    #print_ev_orig_sentences()
    #sys.exit()
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', "--store_db", action="store", dest="store_db")
    parser.add_argument('-n', "--num", action="store", dest="num")
    parser.add_argument('-u', "--update", action="store", dest="update")
    options = parser.parse_args() 

    if options.store_db != None:
        build_event_db(options.store_db, IDS_FILE)
    elif options.update != None:
        update(options.update.split('/'))
    elif options.num != None:
        # debug mode.
        ev = Event(options.num)
    else:
        sys.stderr.write("no option specified.\n")
        
