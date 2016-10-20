# -*- coding: utf-8 -*-
import sys
import shelve 
import xml.etree.ElementTree as ET
import xmltodict
from utils import CASE_ENG
from Event import *
# read from config file.
import ConfigParser
sys.path.append("/home/huang/work/CDB_handler")
#sys.path.insert(0, "/home/huang/pyknp/pyknp")
config = ConfigParser.RawConfigParser()
config.read('./data_location.ini')
CF = config.get('CF', 'CF') 
CF_DB = shelve.open(config.get('DB', 'CF_DB'))
EVENT_DB = shelve.open(config.get('DB', 'EVENT_DB'), flag='r')
IDS_FILE = config.get('Raw', 'IDS')

SAVE_CASE = [u'ガ格', u'ヲ格', u'ニ格', u'デ格']
KATA_ENG = dict(zip(SAVE_CASE, CASE_ENG))

cf_cdb = CDB_Reader(CF)

def process_pred(key, cf_db_key):
    xml = cf_cdb.get(key, exhaustive=True)
    if not xml:
        result = juman.analysis(key.split('/')[0].decode('utf-8'))
        # ex: 入れる/いれる --> 入れる/いれる?入れる/はいれる 
        ambiguous_key = result.mrph_list()[0].repnames()
        key = ambiguous_key
        xml = cf_cdb.get(key, exhaustive=True)
    for x in xml:
        doc = xmltodict.parse(x)
        if doc[u'caseframedata'][u'entry'][u'@predtype'] != u"動":
            continue
        CF_DB[cf_db_key] = {}
        for caseframe in doc[u'caseframedata'][u'entry'][u'caseframe']:
            if type(caseframe) in [unicode, str]:
                continue
            CF_DB[cf_db_key].update(process_caseframe(caseframe))

def process_caseframe(caseframe_raw_dict):
    cf_id = caseframe_raw_dict[u'@id']
    caseframe_dict = {}
    for argument in caseframe_raw_dict[u'argument']:
        if type(argument) in [unicode, str]:
            continue
        case = argument[u'@case']
        if case not in SAVE_CASE:
            continue
        case = KATA_ENG[case]
        case_frequency = argument['@frequency']
        caseframe_dict['case_freq_%s' % case] = case_frequency
        freq_dict = {}
        for component in argument[u'component']:
            if type(component) in [unicode, str]:
                continue
            freq_dict[component['#text']] = int(component['@frequency'])
        caseframe_dict[case] = freq_dict
    return {cf_id: caseframe_dict}


def process_event(num):
    ev = EVENT_DB[num]
    pred1 = ev['pred1']['verb_rep']
    process_pred(pred1, "%s_1" % num)
    pred2 = ev['pred2']['verb_rep']
    process_pred(pred2, "%s_2" % num)

if __name__ == "__main__":
    for num in open(IDS_FILE).readlines():
        num = num.strip()
        print num
        process_event(num)

