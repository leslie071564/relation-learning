# -*- coding: utf-8 -*-
import sys
import shelve
import re
import codecs
import os
import itertools
import operator
import argparse
from itertools import product
from subprocess import check_output
#from build_cf_db import *
from utils import *
from RetrieveOriginalData import *
from Original_sentences_analysis import * 
import ConfigParser
config = ConfigParser.RawConfigParser()
config.read('./data_location.ini')
ARG_FILE = config.get('Raw', 'ARG_FILE')
IDS_FILE = config.get('Raw', 'IDS')
GOLD_ALIGN = shelve.open(config.get('Raw', 'GOLD'), flag='r')
ORIG_TEXT_DIR = config.get('Original', 'ORIG_TEXT_DIR')
CF = config.get('CF', 'CF') 

class Event(object):
    attributes = ['pred1', 'pred2', 'charStr_raw', 'charStr', 'gold', 'impossible_align', 'arg_count', 'context_word', 'cf_ids']
    def __init__(self, num, event_dict=None, modify=[]):
        """
        Build event attribute from scratch of from existing database (when event dict is given).
        modify is the list of attribute(s) to be updated.
        """
        self.num = num
        if event_dict == None:
            # build instance from scratch.
            self._set_all()
        else:
            # build instance from existing dictionary.
            self.pred1 = Predicate("", event_dict['pred1'])
            self.pred2 = Predicate("", event_dict['pred2'])
            for attr in self.attributes[2:]:
                if attr in modify:
                    exec("self._set_%s()" % attr)
                else:
                    setattr(self, attr, event_dict[attr])

    def _set_all(self):
        """
        Set all the event attributes.
        """
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
        self._set_cf_ids()

    def _retrieve_raw_event(self):
        """
        Retrieve the line of current event pair.
        """
        command = "head -n %s %s | tail -n 1" % (self.num, ARG_FILE)
        line = check_output(command, shell=True)
        pa1_str = re.sub(r"[{{}}]", "", line.split(" ")[1])
        pa2_str = re.sub(r"[{{}}]", "", line.split(" ")[3])
        return pa1_str, pa2_str

    def _set_charStr_raw(self):
        """
        Set the raw characteristic string of event instance.
        ex: 1vA貼る/はる:1w604(切手/きって) => 2vA入れる/いれる:2n627(ポスト/ぽすと,応募/おうぼ+箱/はこ)
        """
        pa1_str, pa2_str = self._retrieve_raw_event()
        self.charStr_raw = "%s => %s" % (pa1_str, pa2_str)

    def _set_charStr(self):
        """
        Set the characteristic string of event instance.
        ex: 切手を貼る => ポストに入れる 
        """
        self.charStr = "%s => %s" % (self.pred1.get_charStr(), self.pred2.get_charStr())

    def _set_gold(self):
        """
        Set the gold ailgnment of event instance (if exist). 
        The gold attribute will be None if the event pair is not annotated.
        The gold alignment stored is processed to remove ', /, p, g2, ...
        """
        if self.num in GOLD_ALIGN.keys():
            self.gold = process_gold(GOLD_ALIGN[self.num])
            if self.gold == ['X']:
                self.gold = []
        else:
            self.gold = None
        print " ".join(self.gold)

    def _set_impossible_align(self):
        """
        If the two cases with different given cases exists, the alignemnts between such cases would be regarded as impossible aligns.
        ex: 切手を貼る => ポストに入れる
            impossible_align = ['w-n']
        """
        given_args1 = self.pred1.args
        given_args2 = self.pred2.args
        self.impossible_align = []
        for case1, case2 in product(given_args1.keys(), given_args2.keys()):
            if set(given_args1[case1]) & set(given_args2[case2]):
                continue
            self.impossible_align.append("%s-%s" % (case1, case2))

    def _set_arg_count(self, remove_redundant=False, print_sent=""):
        """
        Retrieve original sentences and update set the counts of arguments in each case in the original sentences.
        """
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
        sys.stderr.write("key strings:\n")
        # get original sentences. 
        self.arg_count = defaultdict(lambda: defaultdict(int))
        keep_args1 = []
        keep_args2 = []
        for key in all_keys:
            if get_original_sentence(key.decode('utf-8')) == None:
                sys.stderr.write("%s 0\n" % key)
                continue
            for np in sum(self.pred1.args.values(), []):
                if np not in keep_args1 and np in key.split('-')[0].split('|'):
                    keep_args1.append(np)
            for np in sum(self.pred2.args.values(), []):
                if np not in keep_args2 and np in key.split('-')[1].split('|'):
                    keep_args2.append(np)
            original_sentence_of_key = get_original_sentence(key)
            sys.stderr.write("%s %d\n" % (key, len(original_sentence_of_key)))
            for parsed_sent, sent in original_sentence_of_key:
                if print_sent:
                    PRINT_TO_FILE.write(sent+'\n')
                self._update_arg_count(parsed_sent)
        self.pred1.update_args(keep_args1)
        self.pred2.update_args(keep_args2)
        # check for repeated sentences.
        self.arg_count = dict(self.arg_count)
        if remove_redundant:
            self.orig_sentences = remove_redundant_sentence(self.orig_sentences)

    def _update_arg_count(self, parsed_sent):
        """
        update the argument counts in each case of predicates in orignal sentences.
        """
        PAS = parsed_sent.split(" - ")
        PAS_components = map(lambda x: x.split(" "), PAS)
        for pred_index, pa_components in enumerate(PAS_components):
            for arg, case in zip(pa_components[0::2], pa_components[1::2]):
                if case not in KATA_ENG.keys():
                    continue
                #arg = "+".join(map(lambda x: x.split('/')[0], arg.split('+')))
                self.arg_count["%s%s" % (KATA_ENG[case.decode('utf-8')], pred_index+1)][arg] += 1

    def print_orig_sentences(self, write_to_file):
        self._set_arg_count(print_sent=write_to_file)

    def _set_context_word(self):
        seperate_list = [self.pred1.verb_rep, self.pred2.verb_rep]
        seperate_list = map(lambda x: x.split('+')[0], seperate_list)[::-1]
        raw_context_word = get_context_words(self.num, seperate_list, debug=False)

        givens = sum(self.pred1.args.values(), []) + sum(self.pred2.args.values(), [])
        skip = [u"こと/こと", u"[数詞]"] + givens + seperate_list
        save_context = raw_context_word['f'] + raw_context_word['m']
        self.context_word = {k : v for k, v in save_context.items() if k not in skip}
        #print "<All context words>"
        #for place, print_place in [('f', 'front'), ('m', 'middle'), ('r', 'after')]:
            #print print_place, ":"
            #print " ".join(filter(lambda y: raw_context_word[place][y] > 3, [x[0] for x in raw_context_word[place].items()]))

    def _set_cf_ids(self):
        CF_DB = shelve.open(config.get('DB', 'CF_DB'), flag='r')
        self.cf_ids = {"1":[], "2":[]}
        for which in ["1", "2"]:
            score_dict = {}
            cfs = CF_DB["%s_%s" % (self.num, which)]
            for cf_id, cf_dict in cfs.iteritems():
                try:
                    this_cf = CaseFrame(cf_dict=cf_dict)
                except:
                    sys.stderr.write("cannot convert case-frame object.\n")
                    continue
                cf_id = "%s##%s" % (cf_id, this_cf.get_char_str())
                score_dict[cf_id] = this_cf.get_score(self.arg_count, which, context_word=self.context_word)
            score_dict = sorted(score_dict.items(), key=operator.itemgetter(1), reverse=True)
            flag = False
            for cf_id, cf_score in score_dict:
                if flag and cf_score == 0:
                    break
                if cf_score != 0:
                    flag = True
                self.cf_ids[which].append("%s##%.3f" % (cf_id, cf_score))
                sys.stderr.write("%s %.3f\n" % (cf_id, cf_score))
            # modify:
            if flag == False:
                #self.cf_ids[which] = map(lambda x: "%s##%s" % (x, 0), self.cf_ids[which][::-1])
                self.cf_ids[which] = self.cf_ids[which][::-1]

        CF_DB.close()


    def get_all_features_dict(self, max_cf_num=5):
        CF_DB = shelve.open(config.get('DB', 'CF_DB'), flag='r')
        cf1s = CF_DB["%s_1" % self.num]
        cf2s = CF_DB["%s_2" % self.num]
        CF_DB.close()
        all_features_dict = {}
        # general.
        all_features_dict['all'] = {}
        all_features_dict['all']['postPred'] = self.pred2.args.keys()
        all_features_dict['all']['impossibleAlign'] = self.impossible_align

        for i in range(min(max_cf_num, len(self.cf_ids['1']))):
            for j in range(min(max_cf_num, len(self.cf_ids['2']))):
                cf1_id = self.cf_ids['1'][i].split("##")[0]
                cf2_id = self.cf_ids['2'][j].split("##")[0]
                cont_dict = self.get_context_features(CaseFrame(cf_dict=cf1s[cf1_id]), CaseFrame(cf_dict=cf2s[cf2_id]))
                cfsim_dict = self.get_cfsim_features(CaseFrame(cf_dict=cf1s[cf1_id]), CaseFrame(cf_dict=cf2s[cf2_id]))
                all_features_dict["%s_%s" % (i, j)] = {'cfsim': cfsim_dict, 'context': cont_dict}
        return all_features_dict


    def get_cfsim_features(self, cf1, cf2):
        """
        return cfsim feature dictionary.
        """
        cfsim_feature_dict = defaultdict(int)
        for c1, c2 in product(CASE_ENG, CASE_ENG):
            align = "%s-%s" % (c1, c2)
            if c1 not in cf1.args.keys() or c2 not in cf2.args.keys():
                continue
            align_sim = round(cosine_similarity(cf1.args[c1], cf2.args[c2]), 3)
            if align_sim:
                cfsim_feature_dict[align] = align_sim 
                cfsim_feature_dict["%s-_" % c1] += align_sim
                cfsim_feature_dict["_-%s" % c2] += align_sim
        return dict(cfsim_feature_dict)


    def get_context_features(self, cf1, cf2):
        """
        return context feature dictionary.
        """
        context_feature_dict = defaultdict(int)
        for c1, c2 in product(CASE_ENG, CASE_ENG):
            align = "%s-%s" % (c1, c2)
            align_context_score = 0.0
            for w, count in self.context_word.items():
                ###
                if count < 3:
                    continue
                ###
                w = w.encode('utf-8')
                p1 = cf1.get_arg_probability(c1, w)
                p2 = cf2.get_arg_probability(c2, w)
                align_context_score += min(p1, p2) * count
            align_context_score = round(align_context_score, 3)
            if align_context_score:
                context_feature_dict[align] = align_context_score
                context_feature_dict["%s-_" % c1] += align_context_score
                context_feature_dict["_-%s" % c2] += align_context_score

        return dict(context_feature_dict)

    def export(self):
        event_dict = {}
        event_dict['pred1'] = self.pred1.export()
        event_dict['pred2'] = self.pred2.export()
        for attr in self.attributes[2:]:
            event_dict[attr] = getattr(self, attr)
        return event_dict
### End: Event Class
    
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

    def update_args(self, keep_args):
        for case, arg_list in self.args.items():
            new_arg_list = filter(lambda x: x in keep_args, arg_list)
            self.args[case] = new_arg_list


    def export(self):
        predicate_dict = {}
        for attr in self.attributes:
            predicate_dict[attr] = getattr(self, attr)
        return predicate_dict
### End: Predicate Class
class CaseFrame(object):
    def __init__(self, xml="", cf_dict={}):
        """
        initialize by xml or case-frame dictionary.
        xml is prioritized.
        """
        if xml is not "": 
            self._set_caseframe_by_xml(xml)
        elif cf_dict:
            # construct by existing cf database.
            self.frequencies = {}
            self.args = {}
            for case, content in cf_dict["frequencies"].items():
                self.frequencies[case] = int(content)
            for case, content in cf_dict["args"].items():
                content = {arg.encode('utf-8'): int(count) for arg, count in content.iteritems()}
                self.args[case] = content
        else:
            raise ValueError("cannnot constuct caseframe instance.")

    def _set_caseframe_by_xml(self, cf_xml):
        """
        given the xml of caseframe,
        set instance attributes. (args/frequencies)
        """
        self.frequencies = {}
        self.args = {}
        for argument in cf_xml:
            case = argument.attrib['case']
            if case not in CASE_VERBOSE:
                continue
            eng_case = VER_ENG[case]
            # save total frequency of current case.
            case_frequency = argument.attrib['frequency']
            self.frequencies[eng_case] = case_frequency
            # save argument counts of current case.
            case_dict = {}
            for component in argument: 
                arg_frequency = component.attrib['frequency']
                arg = component.text
                case_dict[arg] = arg_frequency
                self.args[eng_case] = case_dict

    def get_char_str(self, postfix_pred=""):
        """
        get the characteristic string of the caseframe object, by taking the most frequent argument in each case.
        ex: /ほう が 切手/きって を 契約/けいやく+書/しょ に 貼る/はる 
        """
        char_str = ""
        for case, args_dict in self.args.iteritems():
            max_arg = max(args_dict.iteritems(), key=operator.itemgetter(1))[0]
            char_str += "%s %s " % (max_arg, ENG_HIRA[case])
        if postfix_pred:
            char_str += postfix_pred
        return char_str

    def check_cf_validation(self, event_args):
        """
        check if the current case-frame contains any of the given arguments.
        """
        flag = False
        for case, given_args in event_args.iteritems():
            if case not in self.args.keys():
                return False
            given_args = map(unicode, given_args)
            cf_args = self.args[case].keys()
            if set(cf_args) & set(given_args):
                flag = True
            else:
                ambiguous_given_args = filter(lambda x: '?' in x, given_args)
                ambiguous_cf_args = filter(lambda x: '?' in x, cf_args)
                if ambiguous_given_args is not []:
                    ambiguous_given_args = sum(map(lambda x: x.split('?'), ambiguous_given_args), [])
                    if set(ambiguous_given_args) & set(cf_args):
                        flag = True
                elif ambiguous_cf_args is not []:
                    ambiguous_cf_args = sum(map(lambda x: x.split('?'), ambiguous_cf_args), [])
                    if set(ambiguous_cf_args) & set(given_args):
                        flag = True
        return flag
            

    def get_score(self, event_args, which, context_word={}):
        # modify:
        context_word = {arg.encode('utf-8'): count for arg, count in context_word.iteritems()}
        check_cases = filter(lambda x: which in x, event_args.keys())

        total_similarity = 0
        for case in check_cases:
            if case[0] not in self.args.keys():
            #    return 0
                continue
            case_sim = cosine_similarity(event_args[case], self.args[case[0]], strip=True) 
            # ??
            if context_word:
                context_sim = cosine_similarity(context_word, self.args[case[0]], strip=True)
                case_sim += context_sim
            total_similarity += case_sim
        return total_similarity 

    def get_arg_probability(self, case, arg_list):
        """
        find the probability that a given argument appears in a given case of the predicate. 
        """
        if type(arg_list) == str:
            arg_list = [arg_list]
        if case not in self.args.keys():
            return 0
        case_args = {a:count for a, count in self.args[case].iteritems()}
        case_frequency = float(self.frequencies[case])
        total_prob = 0.0
        for arg in arg_list:
            if arg not in case_args.keys():
                continue
            #print arg
            target_arg_count = case_args[arg]
            total_prob += target_arg_count / case_frequency
        return total_prob
### End: CaseFrame Class

### Event-db Related:
def build_event_db(db_loc, ids_file):
    """
    Build the EVENT_DB database.
    """
    event_db = shelve.open(db_loc)
    for num in open(ids_file, 'r').readlines():
        sys.stderr.write("# %s\n" % (num))
        num = num.rstrip()
        ev = Event(int(num))
        event_db[num] = ev.export()

    
def update(update_list, event_db="/zinnia/huang/EventKnowledge/data/event.db"):
    """
    update one or several atttribute to the event db.
    """
    # now possible: (Event)charStr/charStr_raw/gold
    ### TODO: (Predicate) negation/voice/verb_raw 
    EVENT_DB = shelve.open(event_db)
    for num in open(IDS_FILE, 'r').readlines():
        num = num.rstrip()
        sys.stderr.write("now updating ...%s\n" % num)
        ev = Event(num, EVENT_DB[num], modify=update_list)
        EVENT_DB[num] = ev.export()
        sys.stderr.write("done\n")

### Cf-db Related:
import xml.etree.ElementTree as ET
#sys.path.insert(0, "../nnAlignLearn")
from CDB_Reader import CDB_Reader
def build_cf_db(db_loc, ids_file):
    """
    Build the CF_DB database.
    """
    for num in open(ids_file, 'r').readlines():
        num = num.rstrip()
        _build_cf_db(num)

def _build_cf_db(num, debug=False):
    """
    write all the valid cfs to cf-db.
    """
    CF_DB = shelve.open(config.get('DB', 'CF_DB'))
    EVENT_DB = shelve.open(config.get('DB', 'EVENT_DB'), flag='r')
    ev = Event(num, EVENT_DB[num])

    key1 = "%s_1" % num
    pred1 = ev.pred1.verb_rep
    args1 = ev.pred1.args
    print "predicate: %s" % pred1 
    if debug:
        get_predicate_dict(pred1, args1)
    else:
        CF_DB[key1] = get_predicate_dict(pred1, args1)

    key2 = "%s_2" % num
    pred2 = ev.pred2.verb_rep
    args2 = ev.pred2.args
    print "predicate: %s" % pred2 
    if debug:
        get_predicate_dict(pred2, args2)
    else:
        CF_DB[key2] = get_predicate_dict(pred2, args2)
    sys.stderr.write("%s done.\n" % num)

def get_predicate_dict(pred_repStr, given_args, only_verb=True, all_cf=False):
    """
    given the rep-str of a predicate,
    return the dictionary of the predicate(caseframe-id: caseframe-dictionary) 
    """
    cf_cdb = CDB_Reader(CF, repeated_keys=True)
    amb_key = get_amb_key(pred_repStr)
    xml = cf_cdb.get(pred_repStr, exhaustive=True)
    xml_amb = cf_cdb.get(amb_key, exhaustive=True)
    
    if not xml:
        xml = xml_amb
    elif xml_amb:
        xml += xml_amb

    pred_dict = {}
    flag = False

    for x in xml:
        caseframedata = ET.fromstring(x)
        entry = caseframedata[0]
        predtype = entry.attrib['predtype']
        if only_verb and predtype != u"動":
            continue
        flag = True
        for cf_xml in entry:
            cf_id = cf_xml.attrib['id']
            this_cf = CaseFrame(xml=cf_xml)
            freq_dict = this_cf.frequencies
            cf_dict = {}
            cf_dict['args'] = this_cf.args
            cf_dict['frequencies'] = this_cf.frequencies 
            if all_cf:
                print cf_id
                pred_dict[cf_id] = cf_dict
            elif not given_args or this_cf.check_cf_validation(given_args):
                print cf_id
                pred_dict[cf_id] = cf_dict
    if flag:
        if not pred_dict:
            return get_predicate_dict(pred_repStr, given_args, only_verb=False, all_cf=True)
        return pred_dict
    else:
        return get_predicate_dict(pred_repStr, given_args, only_verb=False)


### Original Sentence Related:
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
    parser = argparse.ArgumentParser()
    parser.add_argument('-e', "--event_db", action="store", dest="event_db")
    parser.add_argument('-u', "--update", action="store", dest="update")
    parser.add_argument('-c', "--cf_db", action="store", dest="cf_db")
    #parser.add_argument('-d', "--store_db", action="store", dest="store_db")
    parser.add_argument('-n', "--num", action="store", dest="num")
    options = parser.parse_args() 

    if options.event_db != None:
        build_event_db(options.event_db, IDS_FILE)

    elif options.update != None:
        update(options.update.split('/'))

    elif options.cf_db != None:
        build_cf_db(options.cf_db, IDS_FILE)

    elif options.num != None:
        # debug mode.
        num = options.num
        ev = Event(options.num)
        sys.exit()

        EVENT_DB = shelve.open(config.get('DB', 'EVENT_DB'), flag='r')
        ev = Event(num, EVENT_DB[num])
        EVENT_DB.close()
        print ev.gold
        sys.exit()
        print ev.get_all_features_dict()
    else:
        sys.stderr.write("no option specified.\n")
        
