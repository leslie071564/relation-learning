# -*- coding: utf-8 -*-
import sys
import shelve
import operator
import argparse
import ConfigParser
config = ConfigParser.RawConfigParser()
config.read('./data_location.ini')
IDS_FILE = config.get('Raw', 'IDS')
from Event import Event
from utils import CASE_ENG, ALL_ALIGN2
import random

def get_feature_type_list(setting_file):
    config.read(setting_file)
    feature_types = config.__dict__['_sections'].copy()['Feature extraction']
    feature_types = filter(lambda x: feature_types[x] == 'True', feature_types.keys())
    return feature_types

def get_config(setting_file):
    config.read(setting_file)
    global CfNum, NegSample
    CfNum = config.getint('Training', 'CfNum')
    NegSample = config.getint('Training', 'NegSample')

### Feature File Related:
def print_train_file(key, feature_types, negative):
    key = key.split('_')
    if len(key) == 4:
        num = key[0]
        cf_pair = "%s_%s" % (key[1], key[2])
        gold_num = key[3]
    else:
        sys.stderr.write("key not valid.\n")
        sys.exit()

    EVENT_DB = shelve.open(config.get('DB', 'EVENT_DB'), flag='r')
    ev = Event(num, EVENT_DB[num])
    EVENT_DB.close()
    if gold_num == 'all':
        gold_align = ev.gold
    else:
        gold_align = ev.gold_sets[int(gold_num)]
    feat_dict = ev.get_all_features_dict(max_cf_num=CfNum)
    
    print "@boi"
    print "# %s %s" % (num, " ".join(gold_align))
    # print +
    if gold_align == []:
        class_str = "null"
    else:
        class_str = "_".join(gold_align)
    class_str = "%s_%s_%s" % (num, cf_pair, class_str)
    print "+%s %s" % (class_str, get_all_features(feat_dict['all'], feat_dict[cf_pair], gold_align, feature_types))

    # print -
    for alignment in random.sample(ALL_ALIGN2, negative):
        if alignment == gold_align:
            continue
        if alignment == []:
            class_str = "null"
        else:
            class_str = "_".join(alignment)
        class_str = "%s_%s_%s" % (num, cf_pair, class_str)
        print "-%s %s" % (class_str, get_all_features(feat_dict['all'], feat_dict[cf_pair], alignment, feature_types))

    """
    # try
    for neg_cf_pair in feat_dict.keys():
        if neg_cf_pair in [cf_pair, 'all']:
            continue
        if gold_align == []:
            class_str = "null"
        else:
            class_str = "_".join(gold_align)
        class_str = "%s_%s_%s" % (num, cf_pair, class_str)
        print "-%s %s" % (class_str, get_all_features(feat_dict['all'], feat_dict[neg_cf_pair], gold_align, feature_types))
    """
    print "@eoi"

def print_test_file(num, feature_types, without_impossible, only_gold):
    EVENT_DB = shelve.open(config.get('DB', 'EVENT_DB'), flag='r')
    ev = Event(num, EVENT_DB[num])
    EVENT_DB.close()
    feat_dict = ev.get_all_features_dict(max_cf_num=CfNum)

    if only_gold:
        #all_align = [gold_align]
        all_align = ev.gold_sets
    else:
        all_align = ALL_ALIGN2
    
    print "@boi"
    #print "# %s" % num
    print "# %s %s" % (num, " ".join(ev.gold))
    impossible_align = feat_dict['all']['impossibleAlign']
    for cf_pair in feat_dict.keys():
        if cf_pair == 'all':
            continue
        for alignment in all_align:
            if without_impossible and (set(alignment) & set(impossible_align)):
                continue
            if alignment == []:
                class_str = "null"
            else:
                class_str = "_".join(alignment)
            ### ??
            if only_gold:
                gold_index = all_align.index(alignment)
                class_str = "-%s_%s_%s_%s" % (num, cf_pair, gold_index, class_str)
            else:
                class_str = "-%s_%s_%s" % (num, cf_pair, class_str)
            print class_str, get_all_features(feat_dict['all'], feat_dict[cf_pair], alignment, feature_types)
    print "@eoi"

def get_all_features(general_dict, feature_dict, alignment, feature_types):
    feature_strs = []
    ##
    if 'binary' in feature_types:
        feature_strs.append(_get_binary_feature(alignment))
    if 'multialign' in feature_types:
        feature_strs.append(_get_multialign_feature(alignment))
    if 'cfsim' in feature_types:
        feature_strs.append(_get_cfsim_feature(alignment, feature_dict['cfsim']))
    if 'cfrival' in feature_types:
        feature_strs.append(_get_rival_feature(alignment, feature_dict['cfsim'], 'cf'))
    if 'context' in feature_types:
        feature_strs.append(_get_context_feature(alignment, feature_dict['context']))
    if 'contextrival' in feature_types:
        feature_strs.append(_get_rival_feature(alignment, feature_dict['context'], 'con'))
    if 'postpred' in feature_types:
        feature_strs.append(_get_postpred_feature(alignment, general_dict['postPred']))
    if 'verbtype' in feature_types:
        feature_strs.append(_get_verbtype_feature(alignment, general_dict['verbType']))
    if 'support' in feature_types:
        #feature_strs.append(_get_support_feature(alignment, general_dict['support']))
        feature_strs.append(_get_rival_feature(alignment, general_dict['support'], 'sup', threshold=10))
    if 'conflict' in feature_types:
        feature_strs.append(_get_conflict_feature(alignment, general_dict['conflict']))
    ##
    feature_strs = filter(None, feature_strs)
    return  " ".join(feature_strs)

def _get_binary_feature(align):
    postfix = "_aligned"
    binary_feats = []
    if align == []:
        #return "%s%s" % ("null", postfix)
        return ""
    for a in align:
        binary_feats.append("%s%s" % (a, postfix))
    return " ".join(binary_feats)

def _get_multialign_feature(align):
    postfix = "_multi"
    multi_feats = []
    c1s = map(lambda x: x.split('-')[0], align)
    for c1 in set([x for x in c1s if c1s.count(x) > 1]):
        multi_feats.append("%s1%s" % (c1, postfix))

    c2s = map(lambda x: x.split('-')[-1], align)
    for c2 in set([x for x in c2s if c2s.count(x) > 1]):
        multi_feats.append("%s2%s" % (c2, postfix))
    return " ".join(multi_feats)

def _get_conflict_feature(align, conf_dict):
    postfix = "_conf"
    conf_feats = []
    for a in align:
        if a not in conf_dict.keys():
            continue
        conf_feats.append("%s%s:%.3f" % (a, postfix, conf_dict[a]))

def _get_support_feature(align, support_dict):
    postfix = "_sup"
    sup_feats = []
    for a in align:
        if a not in support_dict.keys():
            continue
        score = support_dict[a]
        if score < 10:
            continue
        if score > 100:
            score = 100
        sup_feats.append("%s%s:%s" % (a, postfix, score))
    return " ".join(sup_feats)


def _get_verbtype_feature(align, target_list):
    postfix = "_vtype"
    verbtype_feats = []
    c1s = map(lambda x: x.split('-')[0], align)
    c2s = map(lambda x: x.split('-')[-1], align)
    seperated_align = {'1' : c1s, '2' : c2s}
    for case in target_list:
        case, which = list(case)
        if case in seperated_align[which]:
            verbtype_feats.append("%s%s%s" % (case, which, postfix))
    return " ".join(verbtype_feats)

def _get_cfsim_feature(align, cf_dict):
    postfix = "_cfsim"
    cfsim_feats = []
    ''' no minus.
    for a in align:
        if a not in cf_dict.keys():
            continue
        cfsim_feats.append("%s%s:%.3f" % (a, postfix, cf_dict[a]))
    '''
    for a in cf_dict.keys():
        if '_' in a:
            continue
        if a in align:
            cfsim_feats.append("%s%s:%.3f" % (a, postfix, cf_dict[a]))
        else:
            cfsim_feats.append("%s%s:-%.3f" % (a, postfix, cf_dict[a]))

    return " ".join(cfsim_feats)
    
def _get_context_feature(align, con_dict):
    postfix = "_con"
    con_feats = []
    ''' no minus.
    for a in align:
        if a not in con_dict:
            continue
        con_feats.append("%s%s:%.3f" % (a, postfix, con_dict[a]))
    '''
    for a in con_dict.keys():
        if '_' in a:
            continue
        if a in align:
            con_feats.append("%s%s:%.3f" % (a, postfix, con_dict[a]))
        else:
            con_feats.append("%s%s:-%.3f" % (a, postfix, con_dict[a]))

    return " ".join(con_feats)

def _get_rival_feature(align, feat_dict, postfix, threshold=0.005):
    postfix = "_%srival" % (postfix)
    rival_feats = []
    for a in align:
        c1, c2 = a.split('-') 
        if a not in feat_dict.keys():
            continue
        align_score = feat_dict[a]
        if align_score <= threshold:
            continue
        align_score = float(align_score)
        ratio1 = align_score / feat_dict["%s-_" % c1]
        ratio2 = align_score / feat_dict["_-%s" % c2]
        # MODIFY
        if align_score > threshold:
            rival_feats.append("%s%s:%.3f" % (a, postfix, ratio1 * ratio2))
    return " ".join(rival_feats)
    """
    for a in feat_dict.keys():
        if '_' in a:
            continue
        align_score = feat_dict[a]
        if align_score <= threshold:
            continue
        align_score = float(align_score)
        #
        c1, c2 = a.split('-') 
        ratio1 = align_score / feat_dict["%s-_" % c1]
        ratio2 = align_score / feat_dict["_-%s" % c2]
        if a in align:
            rival_feats.append("%s%s:%.3f" % (a, postfix, ratio1 * ratio2))
        else:
            rival_feats.append("%s%s:-%.3f" % (a, postfix, ratio1 * ratio2))
    return " ".join(rival_feats)
    """


def _get_postpred_feature(align, post_list):
    postfix = "_post"
    post_feats = []
    c2s = map(lambda x: x.split('-')[-1], align)
    for c2 in set(c2s) & set(post_list):
        post_feats.append("%s%s" % (c2, postfix))
    return " ".join(post_feats)


def print_test_task(output_dir, setting_file, ids_file, without_impossible, only_gold):
    for num in open(ids_file, 'r').readlines():
        num = num.rstrip()
        cmd =  "python print_feature_file.py --print_test_feature --num %s --setting_file %s" % (num, setting_file)
        if without_impossible:
            cmd += " --without_impossible_align" 
        if only_gold:
            cmd += " --only_gold_align"
        output_file = "%s/%s.txt" % (output_dir, num)
        print "%s > %s && echo -n -" % (cmd, output_file)

def print_train_task(output_dir, setting_file, ids_cf_file):
    for line in open(ids_cf_file, 'r').readlines():
        line = line.rstrip()
        if line in ["@boi", "@eoi"]:
            continue
        key = line.split('_')
        if len(key) < 4:
            sys.stderr.write("not valid key.\n")
            continue
        key = '_'.join(key[:4])
        cmd =  "python print_feature_file.py --print_train_feature --num %s --setting_file %s" % (key, setting_file)
        num = key.split('_')[0]
        output_file = "%s/%s.txt" % (output_dir, num)
        print "%s > %s && echo -n -" % (cmd, output_file)
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--print_test_task", action='store_true', default=False, dest='print_test_task')
    parser.add_argument("--print_train_task", action='store_true', default=False, dest='print_train_task')
    parser.add_argument("--print_train_feature", action='store_true', default=False, dest='print_train_feature')
    parser.add_argument("--print_test_feature", action='store_true', default=False, dest='print_test_feature')

    parser.add_argument('-o', "--output_dir", action='store', dest='output_dir')
    parser.add_argument('-s', "--setting_file", action='store', default='./setting.ini', dest='setting_file')
    parser.add_argument('-i', "--ids_file", action='store', dest='ids_file')
    parser.add_argument('-w', "--without_impossible_align", action='store_true', default=False, dest="without_impossible_align")
    parser.add_argument('-g', "--only_gold_align", action='store_true', default=False, dest="only_gold_align")

    parser.add_argument('-n', "--num", action='store', dest='num')
    options = parser.parse_args() 

    if options.print_test_task:
        if not options.output_dir:
            sys.stderr.write("please specify output directory.\n")
            sys.exit()
        print_test_task(options.output_dir, options.setting_file, options.ids_file, options.without_impossible_align, options.only_gold_align)

    elif options.print_train_task:
        if not options.output_dir:
            sys.stderr.write("please specify output directory.\n")
            sys.exit()
        print_train_task(options.output_dir, options.setting_file, options.ids_file)

    elif options.print_test_feature:
        get_config(options.setting_file)
        feature_types = get_feature_type_list(options.setting_file)
        print_test_file(options.num, feature_types, options.without_impossible_align, options.only_gold_align)

    elif options.print_train_feature:
        get_config(options.setting_file)
        feature_types = get_feature_type_list(options.setting_file)
        print_train_file(options.num, feature_types, negative=NegSample)
    else:
        sys.stderr.write("specify task.\n")
        sys.exit()

