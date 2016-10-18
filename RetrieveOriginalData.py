# -*- coding: utf-8 -*-
import sys
sys.path.append("../nnAlignLearn")
import codecs
sys.stdout = codecs.getwriter('utf-8')(sys.stdout)
import re
import os
import cdb
import itertools
from Event import Event
from pyknp import KNP
knp = KNP()
from CDB_Reader import *
from collections import defaultdict
from subprocess import check_output
from optparse import OptionParser
# read from config file.
import ConfigParser
config = ConfigParser.RawConfigParser()
config.read('./data_location.ini')
KEYMAP = config.get('Original', 'KEY2SID')
SID2PA_KEYMAP = config.get('Original', 'SID2PA')
ORIG_DIR = config.get('Original', 'ORIG_DIR')
WORD_REPLACE = config.get('Original', 'WORD_REPLACE')

WR_POSTFIX = ["", ".1", ".2", ".3"]
VOICE = ['A','P','C','K','M','L']
VOICE_SUFFIX = [[""],[u"[受動]",u"[受動│可能]"], [u"[使役]"], [u"[可能]"], [u"[もらう]"], [u"[判]"]]
VOICE2SUFFIX = dict(zip(VOICE, VOICE_SUFFIX))
NEG = ['v', 'j', 'n']
NEG_SUFFIX = ["", u"[準否定]", u"[否定]"]
NEG2SUFFIX = dict(zip(NEG, NEG_SUFFIX))
CASE_ENG_K = ['d', 'n', 'w', 'g', 'o']
CASE_KATA_K = [u"デ", u"ニ", u"ヲ", u"ガ", u"ノ"]
ENG_KATA_K = dict(zip(CASE_ENG_K, CASE_KATA_K))
KATA_ENG_K = dict(zip(CASE_KATA_K, CASE_ENG_K))
HINSI = set([u"名詞", u"動詞", u"形容詞", u"助詞", u"指示詞"])

def get_mrph_set(sent):
    try:
        result = knp.parse(sent.decode('utf-8'))
    except:
        return None
    return set([(x.midasi, x.hinsi) for x in result.mrph_list()])

def check_redundant_sentence(mrph_sets, new_sent):
    new_sent_mrph = get_mrph_set(new_sent)
    if new_sent_mrph == None:
        sys.stderr.write("knp parsing error: %s\n" % (new_sent))
        return None
    for old_sent_mrph in mrph_sets:
        diff = old_sent_mrph ^ new_sent_mrph
        diff = [x[1] for x in diff] 
        if len(set(diff) & HINSI) == 0:
            sys.stderr.write("redundant sentence: %s\n" % (new_sent))
            return None
    return new_sent_mrph

def remove_redundant_sentence(orig_sentences):
    mrph_sets = []
    trimmed_sentences = []
    for sent in orig_sentences:
        new_mrph = check_redundant_sentence(mrph_sets, sent) 
        if new_mrph != None:
            trimmed_sentences.append(sent)
            mrph_sets.append(new_mrph)
    return trimmed_sentences

def get_pa_from_sid(sid):
    SID2PAdb = CDB_Reader(SID2PA_KEYMAP)
    PAstr = SID2PAdb.get("%s:" % sid)
    if PAstr == None:
        return PAstr
    else :
        PAstr_payload = PAstr.split(" | ")[0]
        return PAstr_payload

def get_orig_sentence(sid):
    sid = sid.split('%')[0]
    sub_dir = sid.split('-')[0]
    sub_dir2 = sid.split('-')[1][:4]
    sub_dir3 = sid.split('-')[1][:6]
    file_loc = "%s/%s/%s/%s.cdb" % (ORIG_DIR, sub_dir, sub_dir2, sub_dir3)
    #sys.stderr.write(file_loc+ '\n')
    F = cdb.init(file_loc)
    sent = F.get(sid)
    #sys.stderr.write(sent + '\n')
    return sent

def get_original_sentence(key):
    KEY2SID = CDB_Reader(KEYMAP)
    value = KEY2SID.get(key)
    if value != None:
        value = value.split(",")
    else :
        #sys.stderr.write("No SID corresponding to %s.\n" % (key))
        return None

    all_pa_str = []
    #orig_sentences = []
    for instance in value:
        sid, relation = instance.split(":")
        relation = relation.split(";")[0]
        sent = get_orig_sentence(sid)
        pa_str = get_pa_from_sid(sid)
        if sent != None and pa_str != None:
            #orig_sentences.append(sent)
            all_pa_str.append((pa_str, sent))
    return all_pa_str

def replace_word(key, class_num):
    all_noun = []
    for p in WR_POSTFIX:
        WR = "%s%s" % (WORD_REPLACE, p)
        F = cdb.init(WR)
        noun = F.get(key)
        if noun != None:
            all_noun.extend(noun.rstrip().split('|'))
    rtn = []
    for noun in all_noun:
        now_class, nounList = noun.split('-')
        nounList = nounList.split(':')
        if now_class == class_num:
            nounList = map(lambda x: x.split('#')[0], nounList)
            rtn.extend(nounList)
    return rtn

