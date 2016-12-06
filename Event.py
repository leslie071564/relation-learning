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
from utils import *
from evaluation import process_gold
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
    attributes = ['pred1', 'pred2',\
                 'charStr_raw', 'charStr', 'gold', 'gold_sets', 'impossible_align',\
                 'conflict_counts', 'context_word', 'related_words', 'support_counts']
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
            if 'pred1' in modify or 'pred2' in modify:
                self._set_preds()
            else:
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
        self._set_preds(pa1_str, pa2_str, refine=False)

        self._set_charStr()
        self._set_gold()
        self._set_gold_sets()
        self._set_impossible_align()
        self._process_all_sentences(set_event_args=True, set_conflict_counts=True)
        self._set_context_word()
        self._set_cf_ids()
        self._set_support_counts()
        self._set_penalty_cfs()
        self._set_related_words()

    def _set_preds(self, pa1_str=None, pa2_str=None, refine=True):
        """
        Set Predicates.
        """
        if not pa1_str or not pa2_str:
            pa1_str, pa2_str = self._retrieve_raw_event()

        self.pred1 = Predicate(pa1_str)
        self.pred2 = Predicate(pa2_str)
        verb_key = "%s-%s" % (self.pred1.verb_raw, self.pred2.verb_raw)
        self.pred1._set_given_arguments(verb_key)
        self.pred2._set_given_arguments(verb_key)
        # update given arguments by deleteing given arguments without supporting sentences.
        if refine:
            self._process_all_sentences(set_event_args=True)
            self.pred1._set_core_cases()
            self.pred2._set_core_cases()

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
            gold_single, gold_multiple = process_gold(GOLD_ALIGN[self.num])
            gold_all = gold_single.values() + sum(gold_multiple.values(), [])
            self.gold = list(set(gold_all))
        else:
            self.gold = None

    def _set_gold_sets(self):
        """
        Get possible gold aligns for training.
        ex: "g/n-g/n" --> ['g-g', 'g-n', 'n-g', 'n-n']
        """
        if self.num not in GOLD_ALIGN.keys():
            self.gold_sets = None
            return None
        
        self.gold_sets = []
        gold_single_raw, gold_multiple_raw = process_gold(GOLD_ALIGN[self.num])
        # process quasi alignment.
        gold_single = filter(lambda x: "\'" not in x[0], gold_single_raw.items())
        gold_quasi = filter(lambda x: "\'" in x[0], gold_single_raw.items())
        gold_single = [x[1] for x in gold_single]
        gold_quasi = [x[1] for x in gold_quasi]
        gold_multiple = gold_multiple_raw.values()
        gold_multiple += map(lambda x: [x, 'dummy'], gold_quasi)


        gold_possibility = list(product(*gold_multiple))
        gold_possibility = map(lambda x: list(set(list(x) + gold_single)), gold_possibility)

        for g in gold_possibility:
            g = filter(lambda x: x != 'dummy', g)
            if g not in self.gold_sets:
                self.gold_sets.append(g)

    def _set_impossible_align(self):
        """
        If the two cases with different given cases exists, the alignemnts between such cases would be regarded as impossible aligns.
        ex: 切手を貼る => ポストに入れる
            impossible_align = ['w-n']
        """
        given_args1 = self.pred1.given_args
        given_args2 = self.pred2.given_args
        self.impossible_align = []
        for case1, case2 in product(given_args1.keys(), given_args2.keys()):
            if set(given_args1[case1]) & set(given_args2[case2]):
                continue
            self.impossible_align.append("%s-%s" % (case1, case2))

    def print_orig_sentences(self, write_to_file):
        """
        Print all supporting sentences to file.
        """
        self._process_all_sentences(print_sent=write_to_file)

    def _set_conflict_counts(self):
        """
        Set conflicit counts for each alignment.
        (counts that the two cases are filled with different arguments.)
        """
        self._process_all_sentences(set_conflict_counts=True)

    def _set_predicate_event_args(self):
        """
        Set the counts of arguments in each case in the original sentences.
        """
        self._process_all_sentences(set_event_args=True)

    def _process_all_sentences(self, print_sent=False, set_event_args=False, set_conflict_counts=False):
        """
        Retrieve original sentences and 
        (1) print all sentences. => print_sent
        (2) set the counts of arguments in each case in the original sentences. => set_event_args
        (3) set the conflict counts of each align pair in the original sentences. => set_conflict_counts
        """
        if print_sent:
            PRINT_TO_FILE = open(print_sent, 'w')
            
        # get all keys for origin sentences retrieval.
        vkeys1 = self.pred1.get_vstr_for_keys()
        vkeys2 = self.pred2.get_vstr_for_keys()
        cckey1 = self.pred1.get_ccstr_for_keys()
        cckey2 = self.pred2.get_ccstr_for_keys()
        all_keys = []
        for i in itertools.product(cckey1, vkeys1, cckey2, vkeys2):
            full_key = "%s%s-%s%s" % (i[0], i[1], i[2], i[3])
            all_keys.append(full_key)
        sys.stderr.write("key strings:\n")
        # get original sentences. 
        if set_event_args:
            self.pred1.event_args = defaultdict(lambda: defaultdict(int))
            self.pred2.event_args = defaultdict(lambda: defaultdict(int))
        if set_conflict_counts:
            self.conflict_counts = defaultdict(int)
        keep_args1 = []
        keep_args2 = []
        for key in all_keys:
            if get_original_sentence(key) == None:
                sys.stderr.write("%s 0\n" % key)
                continue
            # find the given arg.s with supporting sentences.
            for np in sum(self.pred1.given_args.values(), []):
                if np not in keep_args1 and np in key.split('-')[0].split('|'):
                    keep_args1.append(np)
            for np in sum(self.pred2.given_args.values(), []):
                if np not in keep_args2 and np in key.split('-')[1].split('|'):
                    keep_args2.append(np)
            original_sentence_of_key = get_original_sentence(key)
            sys.stderr.write("%s %d\n" % (key, len(original_sentence_of_key)))
            # process parsed sentence.
            for parsed_sent, sent in original_sentence_of_key:
                if print_sent:
                    PRINT_TO_FILE.write(sent+'\n')
                if set_event_args:
                    self._update_event_args(parsed_sent)
                if set_conflict_counts:
                    self._update_conflict_counts(parsed_sent)
        # remove given arguments that has no original sentences.
        self.pred1.update_given_args(keep_args1)
        self.pred2.update_given_args(keep_args2)

        if set_event_args:
            self.pred1.event_args = dict(self.pred1.event_args)
            self.pred2.event_args = dict(self.pred2.event_args)
            self.pred1._set_core_cases()
            self.pred2._set_core_cases()
        if set_conflict_counts:
            self.conflict_counts = dict(self.conflict_counts)

    def _update_event_args(self, parsed_sent):
        """
        update the argument counts in each case of predicates in orignal sentences.
        """
        PAS = parsed_sent.split(" - ")
        PAS_components = map(lambda x: x.split(" "), PAS)
        for pred_index, pa_components in enumerate(PAS_components):
            for arg, case in zip(pa_components[0::2], pa_components[1::2]):
                if case not in KATA_ENG.keys():
                    continue
                eng_case = KATA_ENG[case.decode('utf-8')]
                arg = arg.replace("[t]", "")
                if pred_index == 0:
                    self.pred1.event_args[eng_case][arg] += 1
                elif pred_index == 1:
                    self.pred2.event_args[eng_case][arg] += 1

    def _update_conflict_counts(self, parsed_sent):
        """
        update the conflict counts in each alignment pair in original sentences.
        """
        PAS = parsed_sent.split(" - ")
        PA1, PA2 = map(lambda x: x.split(" "), PAS)
        PA1 = dict(zip(PA1[1::2], PA1[0::2]))
        PA2 = dict(zip(PA2[1::2], PA2[0::2]))
        
        for c1, c2 in product(PA1.keys(), PA2.keys()):
            if c1 not in KATA_ENG.keys() or c2 not in KATA_ENG.keys():
                continue
            c1_eng = KATA_ENG[c1.decode('utf-8')]
            c2_eng = KATA_ENG[c2.decode('utf-8')]
            self.conflict_counts["%s-%s_total" % (c1_eng, c2_eng)] += 1
            if PA1[c1] != PA2[c2]:
                self.conflict_counts["%s-%s" % (c1_eng, c2_eng)] += 1
        self.conflict_counts["total"] += 1
        for c2 in PA2.keys():
            if c2 not in KATA_ENG.keys():
                continue
            c2_eng = KATA_ENG[c2.decode('utf-8')]
            self.conflict_counts["%s_total" % c2_eng] += 1

    def _set_context_word(self):
        """
        Retrieve context words, skipping given arguments and frequent words.
        """
        predicate_skip = [self.pred1.verb_rep, self.pred2.verb_rep]
        predicate_skip = map(lambda x: x.split('+')[0], predicate_skip)[::-1]
        given_args = sum(self.pred1.given_args.values(), []) + sum(self.pred2.given_args.values(), [])
        stop_words = [u"こと/こと", u"[数詞]", u"時/とき", u"場合/ばあい", u"様/よう", u"上/うえ", u"中/なか", u"後/あと", u"為/ため", u"方/ほう", u"下/した", u"ところ/ところ", u"頃/ころ", u"たび/たび"]
        stop_words = map(lambda x: x.encode('utf-8'), stop_words)
        skip_words = stop_words + given_args + predicate_skip

        raw_context_word = get_context_words(self.num, predicate_skip, debug=False)
        save_context = raw_context_word['f'] + raw_context_word['m']
        self.context_word = {k : v for k, v in save_context.items() if k not in skip_words}

    def _set_related_words(self):
        """
        List of related words.
        """
        given_args = sum(self.pred1.given_args.values(), []) + sum(self.pred2.given_args.values(), [])
        event_args = sum(self.pred1.get_event_args_list().values(), []) + sum(self.pred2.get_event_args_list().values(), [])
        context_words = self.context_word.keys()
        selected_context_words = filter(lambda x: self.context_word[x] > 2, context_words)
        #self.related_words = given_args + event_args + context_words
        self.related_words = given_args

    def _set_support_counts(self, max_cf_num=5):
        """
        Retrieve the counts of each related words in each case.
        The related words here contain:
        (1) given args.
        (2) event args.
        (3) context words.
        """
        CF_DB = shelve.open(config.get('DB', 'CF_DB'), flag='r')
        all_cfs = [CF_DB["%s_1" % self.num], CF_DB["%s_2" % self.num]]
        CF_DB.close()
        # words for checking counts.
        given_args = sum(self.pred1.given_args.values(), []) + sum(self.pred2.given_args.values(), [])
        event_args = sum(self.pred1.get_event_args_list().values(), []) + sum(self.pred2.get_event_args_list().values(), [])
        context_words = self.context_word.keys()
        word_list = list(set(event_args + context_words))
        #word_list = list(set(event_args))
        self.support_counts = {}
        
        for word in word_list:
            """
            if word not in event_args:
                freq = self.context_word[word]
                if freq <=2:
                    continue
            """
            word_dict = Counter()
            for which, pred in enumerate([self.pred1, self.pred2]):
                for i in range(min(max_cf_num, len(pred.cfs))):
                    cf_id, _, cf_sim = pred.cfs[i].split("##")
                    cf_dict = all_cfs[which][cf_id]
                    counts = self._get_word_support_count(word, cf_dict, which + 1)
                    #counts = self._get_word_support_count(word, cf_dict, which + 1, weight=float(cf_sim))
                    word_dict.update(counts)
            self.support_counts[word] = dict(word_dict)
        # TODO
        # check for core cases.


    def _get_word_support_count(self, word, cf_dict, which, weight=1.0):
        if weight == 0:
            weight = 1
        word = word.decode('utf-8')
        # TEMP
        word = word.replace("[t]", "")
        counts = {}
        for case, case_dict in cf_dict['args'].iteritems():
            if word not in case_dict.keys():
                continue
            counts[case + str(which)] = int(case_dict[word]) * weight
        return counts

    def _old_set_support_counts(self):
        """
        Retrieve the counts of each related words in each case.
        The related words here contain:
        (1) given args.
        (2) event args.
        (3) context words.
        """
        # words for checking counts.
        given_args = sum(self.pred1.given_args.values(), []) + sum(self.pred2.given_args.values(), [])
        event_args = sum(self.pred1.get_event_args_list().values(), []) + sum(self.pred2.get_event_args_list().values(), [])
        context_words = self.context_word.keys()
        word_list = list(set(given_args + event_args + context_words))
        # counts database.
        event_to_count_keymap = "/windroot/huang/EventCounts_20161030/Event-count/event_count.cdb.keymap"
        ev_count_cdb = CDB_Reader(event_to_count_keymap)
        self.support_counts = {}
        for word in word_list:
            # filter out low-frequency context word.
            if word not in given_args and word not in event_args:
                freq = self.context_word[word]
                if freq <=2:
                    continue

            word_dict = {}
            for case in CASE_KATA:
                eng_case = KATA_ENG[case]
                for which, pred in enumerate([self.pred1, self.pred2]):
                    keys = ["%s-%s-%s" % (word, case, pred.verb_rep)]
                    if pred.verb_amb:
                        keys += map(lambda x: "%s-%s-%s" % (word, case, x), pred.verb_amb)
                    ev_counts = 0
                    for k in keys:
                        count = ev_count_cdb.get(k)
                        if count:
                            ev_counts += int(count)
                    if ev_counts != 0:
                        word_dict["%s%s" % (eng_case, which + 1)] = ev_counts
            if word_dict != {}:
                self.support_counts[word] = word_dict

    def _set_cf_ids(self):
        CF_DB = shelve.open(config.get('DB', 'CF_DB'), flag='r')
        #self.pred1._set_cfs(CF_DB["%s_1" % self.num])
        #self.pred2._set_cfs(CF_DB["%s_2" % self.num])
        self.pred1._set_cfs(CF_DB["%s_1" % self.num], context_words=self.context_word)
        self.pred2._set_cfs(CF_DB["%s_2" % self.num], context_words=self.context_word)
        CF_DB.close()

    def _set_penalty_cfs(self, threshold=10, max_cf_num=10):
        self.pred1.penalty_cfs = []
        self.pred2.penalty_cfs = []
        """
        self.penalty_cfs = {}
        CF_DB = shelve.open(config.get('DB', 'CF_DB'), flag='r')
        cf1s = CF_DB["%s_1" % self.num]
        cf2s = CF_DB["%s_2" % self.num]
        CF_DB.close()
        sup_dict = self.get_support_features()
        self.penalty_cfs = defaultdict(list)
        # pred1.
        if 'w-_' in sup_dict.keys() and sup_dict['w-_'] > threshold:
            for i in range(min(max_cf_num, len(self.pred1.cfs))):
                cf_id = self.pred1.cfs[i].split("##")[0]
                cf_dict = cf1s[cf_id]
                if 'w' not in cf_dict["args"].keys():
                    self.penalty_cfs['1'].append(cf_id)
        # pred2
        if '_-w' in sup_dict.keys() and sup_dict['_-w'] > threshold:
            for i in range(min(max_cf_num, len(self.pred2.cfs))):
                cf_id = self.pred2.cfs[i].split("##")[0]
                cf_dict = cf2s[cf_id]
                if 'w' not in cf_dict["args"].keys():
                    self.penalty_cfs['2'].append(cf_id)
        """

    def get_all_features_dict(self, max_cf_num=5):
        CF_DB = shelve.open(config.get('DB', 'CF_DB'), flag='r')
        cf1s = CF_DB["%s_1" % self.num]
        cf2s = CF_DB["%s_2" % self.num]
        CF_DB.close()
        all_features_dict = {}
        # general.
        all_features_dict['all'] = {}
        all_features_dict['all']['postPred'] = self.pred2.given_args.keys()
        all_features_dict['all']['impossibleAlign'] = self.impossible_align
        all_features_dict['all']['verbType'] = self.get_verbType_features()
        all_features_dict['all']['support'] = self.get_support_features()
        all_features_dict['all']['conflict'] = self.get_conflict_features()

        for i in range(min(max_cf_num, len(self.pred1.cfs))):
            for j in range(min(max_cf_num, len(self.pred2.cfs))):
                cf1_id = self.pred1.cfs[i].split("##")[0]
                cf2_id = self.pred2.cfs[j].split("##")[0]
                #cont_dict = self.get_context_features(CaseFrame(cf_dict=cf1s[cf1_id]), CaseFrame(cf_dict=cf2s[cf2_id]))
                cont_dict = self.get_cfsim_features(CaseFrame(cf_dict=cf1s[cf1_id]), CaseFrame(cf_dict=cf2s[cf2_id]), restrict=True)
                cfsim_dict = self.get_cfsim_features(CaseFrame(cf_dict=cf1s[cf1_id]), CaseFrame(cf_dict=cf2s[cf2_id]))
                is_penalty_cf = {'1' : bool(cf1_id in self.pred1.penalty_cfs), '2' : bool(cf2_id in self.pred2.penalty_cfs)}
                all_features_dict["%s_%s" % (i, j)] = {'cfsim': cfsim_dict, 'context': cont_dict, 'penalty_cfs' : is_penalty_cf}
        return all_features_dict

    def get_support_features(self):
        escape = map(lambda x: "%s1" % x, self.pred1.given_args.keys()) + map(lambda x: "%s2" % x, self.pred2.given_args.keys())
        given_args = sum(self.pred1.given_args.values(), []) + sum(self.pred2.given_args.values(), [])
        event_args = sum(self.pred1.get_event_args_list().values(), []) + sum(self.pred2.get_event_args_list().values(), [])

        support_features = defaultdict(int)
        for word, word_dict in self.support_counts.items():
            support_align = {'1' : None, '2' : None}
            for case in sorted(word_dict, key=word_dict.get, reverse=True):
                if case in escape and word not in given_args:
                    continue
                case, which = list(case)
                if support_align[which]:
                    continue
                else:
                    support_align[which] = (case, word_dict[case+which])
            #
            if None not in support_align.values():
                support_score = min(support_align['1'][1], support_align['2'][1])
                support_align = "%s-%s" % (support_align['1'][0], support_align['2'][0])
                if support_align in self.impossible_align:
                    continue
                support_features[support_align] += support_score
                #sys.stderr.write("%s %s %s\n" % (word, support_align, support_score))
                #
                c1, c2 = support_align.split('-')
                support_features["%s-_" % c1] += support_score
                support_features["_-%s" % c2] += support_score
        # get max count.
        max_count = -1
        for align, score in support_features.items():
            if '_' in align:
                continue
            if score > max_count:
                max_count = score
        if max_count != -1:
            support_features["_max_"] = max_count

        return dict(support_features)

    def get_conflict_features(self):
        conflict_features = {}
        if self.conflict_counts == {}:
            return conflict_features
        #total = float(self.conflict_counts["total"])
        for c1, c2 in product(CASE_ENG, CASE_ENG):
            align = "%s-%s" % (c1, c2)
            if align not in self.conflict_counts.keys():
                continue
            #total = float(self.conflict_counts["%s_total" % align])
            total = float(self.conflict_counts["%s_total" % c2])
            conflict_features[align] = round(self.conflict_counts[align] / total, 3)
        return conflict_features

    def get_verbType_features(self):
        target_align = []
        for i, pred in enumerate([self.pred1, self.pred2]):
            i = i + 1
            if pred.voice == 'P':
                target_align.append("g%s" % i)
            if pred.voice == 'C':
                target_align.append("w%s" % i)
        return target_align


    def get_cfsim_features(self, cf1, cf2, restrict=False):
        """
        return cfsim feature dictionary.
        """
        cfsim_feature_dict = defaultdict(int)
        max_sim = -1
        for c1, c2 in product(CASE_ENG, CASE_ENG):
            align = "%s-%s" % (c1, c2)
            if c1 not in cf1.args.keys() or c2 not in cf2.args.keys():
                continue
            ###TRY
            if restrict:
                align_sim = round(cosine_similarity(cf1.args[c1], cf2.args[c2], restrict_set=self.related_words), 3)
            else:
                align_sim = round(cosine_similarity(cf1.args[c1], cf2.args[c2]), 3)
            ###TRY
            if align_sim:
                #print align
                cfsim_feature_dict[align] = align_sim 
                cfsim_feature_dict["%s-_" % c1] += align_sim
                cfsim_feature_dict["_-%s" % c2] += align_sim
                if align_sim > max_sim:
                    max_sim = align_sim
        if max_sim != -1:
            cfsim_feature_dict['_max_'] = max_sim
        return dict(cfsim_feature_dict)


    def get_context_features(self, cf1, cf2):
        """
        return context feature dictionary.
        """
        context_feature_dict = defaultdict(int)
        max_score = -1
        for c1, c2 in product(CASE_ENG, CASE_ENG):
            align = "%s-%s" % (c1, c2)
            P1 = 0.0
            P2 = 0.0
            tmp = []
            for word, count in self.context_word.items():
                if count < 3:
                    continue
                word = word.encode('utf-8')
                p1 = cf1.get_arg_probability(c1, word)
                p2 = cf2.get_arg_probability(c2, word)
                if p1 and p2:
                    tmp.append(word)
                    P1 += p1 * count 
                    P2 += p2 * count 
            align_context_score = round(min(P1, P2), 3)
            if align_context_score:
                context_feature_dict[align] = align_context_score
                context_feature_dict["%s-_" % c1] += align_context_score
                context_feature_dict["_-%s" % c2] += align_context_score
                if align_context_score > max_score:
                    max_score = align_context_score
        if max_score != -1:
            context_feature_dict["_max_"] = max_score
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
    attributes = ['verb_stem', 'verb_rep', 'verb_amb', 'negation', 'voice',\
                  'given_args', 'event_args', 'core_cases', 'cfs', 'penalty_cfs']
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
        verb_amb = get_amb_key(self.verb_rep)
        if self.verb_rep != verb_amb:
            self.verb_amb = verb_amb
        else:
            self.verb_amb = None
        #MODIFY
        if len(self.verb_amb.split('?')) == 2:
            self.verb_amb = [self.verb_amb, '?'.join(self.verb_amb.split('?')[::-1])]
        else:
            self.verb_amb = [self.verb_amb]

    def _set_given_arguments(self, verb_key):
        self.given_args = {}
        regex = re.compile(noun_pattern)
        for arg_str in self.args_raw:
            place, case, class_num, noun_str = regex.search(arg_str).groups()
            if class_num == "":     #like 2g酷/こくa
                self.given_args[case] = noun_str.split(",")
            else :
                class_id = "%s%s%s" % (place, case, class_num)
                self.given_args[case] = replace_word(verb_key, class_id)
                if self.given_args[case] == []:
                    noun_str = re.sub(r"[\(\)]", "", noun_str)
                    noun_str = re.sub(r"\.", "", noun_str)
                    self.given_args[case] = noun_str.split(",")

    def _set_core_cases(self):
        self.core_cases = []
        for case, arg_dict in self.event_args.iteritems():
            case_filled_counts = sum(arg_dict.values())
            if case_filled_counts >= 3:
                self.core_cases.append(case)

    def _set_cfs(self, all_cfs, context_words={}):
        self.cfs = []
        score_dict = {}
        for cf_id, cf_dict in all_cfs.iteritems():
            try:
                this_cf = CaseFrame(cf_dict=cf_dict)
            except:
                sys.stderr.write("cannot convert case-frame object.\n")
                continue
            cf_sim = this_cf.get_score(self.given_args, self.event_args, context_words=context_words, core_cases=self.core_cases)
            cf_id = "%s##%s##%.3f" % (cf_id, this_cf.get_char_str(), cf_sim)
            score_dict[cf_id] = cf_sim
        # sort by sim score.
        score_dict = sorted(score_dict.items(), key=operator.itemgetter(1), reverse=True)
        max_sim = score_dict[0][-1]
        flag = False
        for cf_id, cf_score in score_dict:
            #if flag and cf_score == 0:
            if flag and cf_score < 0.1 * max_sim:
                break
            if cf_score != 0:
                flag = True
            # append current cf-id to cfs of predicate.
            self.cfs.append(cf_id)
            sys.stderr.write("%s\n" % cf_id)
            
        # When all case frame has zero similarity:
        if flag == False:
            self.cfs = self.cfs[::-1]


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
            if case not in self.given_args.keys():
                continue
            temp = []
            for noun in self.given_args[case]:
                temp.extend(map(lambda x: "%s|%s|%s" % (noun, ENG_KATA_K[case], x), ccstr_for_keys))
            ccstr_for_keys = temp
        return ccstr_for_keys
    
    def get_charStr(self):
        charStr = ""
        for case in self.given_args.keys():
            arg0 = self.given_args[case][0]
            charStr += remove_hira(arg0) + ENG_HIRA[case].encode('utf-8')
        charStr += remove_hira(self.verb_rep, keep_plus=True)
        return charStr

    def update_given_args(self, keep_args):
        for case, arg_list in self.given_args.iteritems():
            new_arg_list = filter(lambda x: x in keep_args, arg_list)
            self.given_args[case] = new_arg_list
    
    def get_event_args_list(self):
        return dict([(case, self.event_args[case].keys()) for case in self.event_args.keys()])

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
            

    def get_score(self, given_args, event_args, context_words={}, core_cases={}):
        G = 1
        E = 0.5
        C = 0.5
        context_words = {arg: count for arg, count in context_words.iteritems()}

        total_similarity = 0
        """
        #check_cases = event_args.keys()
        check_cases = core_cases
        for case in check_cases:
            if case not in self.args.keys():
                return 0
        """
        for case in self.args.keys():
            if case in given_args.keys():
                case_sim_G = cosine_similarity(event_args[case], self.args[case], strip=True)
                total_similarity += case_sim_G * G
            elif case in event_args.keys():
                case_sim_E = cosine_similarity(event_args[case], self.args[case], strip=True) 
                total_similarity += case_sim_E * E
                if context_words:
                    context_sim_C = cosine_similarity(context_words, self.args[case], strip=True)
                    total_similarity += context_sim_C * C
        return total_similarity 

    def get_arg_probability(self, case, arg_list):
        """
        find the probability that a given argument appears in a given case of the predicate. 
        """
        if type(arg_list) == str:
            arg_list = [arg_list]
        #arg_list = map(disambiguous, arg_list)
        #arg_list = map(remove_hira, arg_list)
        if case not in self.args.keys():
            return 0
        #case_args = {disambiguous(a):count for a, count in self.args[case].iteritems()}
        #case_args = {remove_hira(a):count for a, count in self.args[case].iteritems()}
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
        #ev = Event(options.num)
        #ev_dict = ev.export()
        #sys.exit()

        # debug mode.
        EVENT_DB = shelve.open(config.get('DB', 'EVENT_DB'), flag='r')
        ev = Event(num, EVENT_DB[num])
        EVENT_DB.close()
        print ev.get_all_features_dict()
        ev._set_related_words()
        print ev.get_all_features_dict()
        sys.exit()
    else:
        sys.stderr.write("no option specified.\n")
        
