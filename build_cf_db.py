# -*- coding: utf-8 -*-
import sys
import shelve 
import xml.etree.ElementTree as ET
from utils import CASE_ENG
from Event import *
# read from config file.
import ConfigParser
sys.path.append("/home/huang/work/CDB_handler")
config = ConfigParser.RawConfigParser()
config.read('./data_location.ini')
CF = config.get('CF', 'CF') 
CF_DB = shelve.open(config.get('DB', 'CF_DB'))
EVENT_DB = shelve.open(config.get('DB', 'EVENT_DB'), flag='r')
IDS_FILE = config.get('Raw', 'IDS')

SAVE_CASE = [u'ガ格', u'ヲ格', u'ニ格', u'デ格']
KATA_ENG = dict(zip(SAVE_CASE, CASE_ENG))
ENG_KATA = dict(zip(CASE_ENG, SAVE_CASE))

cf_cdb = CDB_Reader(CF)

def get_amb_key(pred_repStr):
    postfix = ""
    if pred_repStr.split('+') > 1:
        postfix = "+".join(pred_repStr.split('+')[1:])
    result = juman.analysis(pred_repStr.split('/')[0].decode('utf-8'))
    amb_key = result.mrph_list()[0].repnames()
    if postfix:
        amb_key = "%s+%s" % (amb_key, postfix)
    if amb_key == pred_repStr:
        return ""
    return amb_key

def print_xml(pred_repStr):
    amb_key = get_amb_key(pred_repStr)
    xml = cf_cdb.get(pred_repStr, exhaustive=True)
    xml_amb = cf_cdb.get(amb_key, exhaustive=True)
    if not xml:
        xml = xml_amb
    elif xml_amb:
        xml += xml_amb
    for x in xml:
        caseframedata = ET.fromstring(x)
        entry = caseframedata[0]
        predtype = entry.attrib['predtype']
        if predtype != u"動":
            continue
        print x


def get_predicate_dict(pred_repStr, given_args, only_verb=True, all_cf=False):
    """
    given the rep-str of a predicate,
    return the dictionary of the predicate(caseframe-id: caseframe-dictionary) 
    """
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
        for cf in entry:
            cf_id = cf.attrib['id']
            cf_dict = get_caseframe_dict(cf)
            if all_cf:
                print cf_id
                pred_dict[cf_id] = cf_dict
            elif not given_args or check_cf_validation(cf_dict, given_args):
                print cf_id
                pred_dict[cf_id] = cf_dict
    if flag:
        if not pred_dict:
            return get_predicate_dict(pred_repStr, given_args, only_verb=False, all_cf=True)
        return pred_dict
    else:
        return get_predicate_dict(pred_repStr, given_args, only_verb=False)


def get_caseframe_dict(cf_xml):
    """
    given the xml of caseframe,
    return the caseframe_dict.
    """
    cf_dict = {}
    for argument in cf_xml:
        case = argument.attrib['case']
        if case not in SAVE_CASE:
            continue
        eng_case = KATA_ENG[case]
        case_frequency = argument.attrib['frequency']
        cf_dict['frequency_%s' % eng_case] = case_frequency
        case_dict = {}
        for component in argument: 
            arg_frequency = component.attrib['frequency']
            arg = component.text
            case_dict[arg] = arg_frequency
        cf_dict[eng_case] = case_dict 
    return cf_dict

def check_cf_validation(cf, args):
    """
    given a caseframe dictionary and given arguments for some cases,
    return True if the caseframe contains at least one of thee give arguments, otherwise returns False.
    """
    for case, given_args in args.items():
        # 満腹/まんぷくa+感/かん --> 満腹/まんぷく+感/かん
        #alphabets = re.compile(r'[a-z]+')
        #given_args = map(lambda x: alphabets.sub('', x), given_args)
        if case not in cf.keys():
            return False
        given_args = map(unicode, given_args)
        if set(cf[case].keys()) & set(given_args):
            print " ".join(list(set(cf[case].keys()) & set(given_args)))
            return True
        else:
            ambiguous_given_args = filter(lambda x: '?' in x, given_args)
            ambiguous_cf_args = filter(lambda x: '?' in x, cf[case].keys())
            if ambiguous_given_args:
                ambiguous_given_args = sum(map(lambda x: x.split('?'), ambiguous_given_args), [])
                if set(ambiguous_given_args) & set(cf[case].keys()):
                    return True
            elif ambiguous_cf_args:
                ambiguous_cf_args = sum(map(lambda x: x.split('?'), ambiguous_cf_args), [])
                if set(ambiguous_cf_args) & set(given_args):
                    return True
    return False

def write_cf_db(num, debug=False):
    """
    write all the valid cfs to cf-db.
    """
    ev = EVENT_DB[num]

    key1 = "%s_1" % num
    pred1 = ev['pred1']['verb_rep']
    args1 = ev['pred1']['args']
    print "predicate: %s" % pred1 
    if debug:
        get_predicate_dict(pred1, args1)
    else:
        CF_DB[key1] = get_predicate_dict(pred1, args1)

    key2 = "%s_2" % num
    pred2 = ev['pred2']['verb_rep']
    args2 = ev['pred2']['args']
    print "predicate: %s" % pred2 
    if debug:
        get_predicate_dict(pred2, args2)
    else:
        CF_DB[key2] = get_predicate_dict(pred2, args2)
    sys.stderr.write("%s done.\n" % num)

if __name__ == "__main__":
    for num in open(IDS_FILE, 'r').readlines():
        num = num.strip()
        print num
        write_cf_db(num)
        #write_cf_db(num, debug=True)

