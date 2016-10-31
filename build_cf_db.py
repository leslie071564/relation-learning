# -*- coding: utf-8 -*-
import sys
from CDB_Reader import CDB_Reader
import shelve 
import xml.etree.ElementTree as ET
from utils import *
#from Event import *
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
import operator

class CaseFrame(object):
    def __init__(self, xml="", cf_dict={}):
        if xml is not "": 
            self._set_caseframe_by_xml(xml)
        elif cf_dict:
            # construct by existing cf database.
            self.frequencies = {}
            self.args = {}
            for case, content in cf_dict.items():
                if case.startswith("frequency"):
                    case = case.split("_")[-1]
                    self.frequencies[case] = int(content)
                else:
                    content = {arg.encode('utf-8'): int(count) for arg, count in content.iteritems()}
                    self.args[case] = content

        else:
            raise ValueError("cannnot constuct caseframe instance.")

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

    def _set_caseframe_by_xml(self, cf_xml):
        """
        given the xml of caseframe,
        set instance attributes. (args/frequencies)
        """
        self.frequencies = {}
        self.args = {}
        for argument in cf_xml:
            case = argument.attrib['case']
            if case not in SAVE_CASE:
                continue
            eng_case = KATA_ENG[case]
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

    def check_cf_validation(self, event_args):
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
        case_args = {remove_hira(a):count for a, count in self.args[case].iteritems()}
        case_frequency = float(self.frequencies[case])
        total_prob = 0.0
        for arg in arg_list:
            if arg not in case_args.keys():
                continue
            #print arg
            target_arg_count = case_args[arg]
            total_prob += target_arg_count / case_frequency
        return total_prob

###
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
        for cf_xml in entry:
            cf_id = cf_xml.attrib['id']
            this_cf = CaseFrame(xml=cf_xml)
            cf_dict = this_cf.args
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
        sys.stderr.write(num)
        num = num.strip()
        print num
        ev = EVENT_DB[num]
        for which in ["1", "2"]:
            score_dict = {}
            cfs = CF_DB["%s_%s" % (num, which)]
            for cf_id, cf_dict in cfs.items():
                pred, pred_num = cf_id.split(':')
                #pred_num = re.match('.*?([0-9]+)$', pred_num).group(1)
                try:
                    this_cf = CaseFrame(cf_dict=cf_dict)
                    sys.exit()
                except:
                    continue
                score_dict[cf_id] = this_cf.get_score(ev['arg_count'], which, context_word=ev['context_word'])
            score_dict = sorted(score_dict.items(), key=operator.itemgetter(1), reverse=True)
            for cf_id, cf_score in score_dict[:5]:
                if cf_score == 0:
                    break
                print cf_id, cf_score
