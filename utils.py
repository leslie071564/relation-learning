# -*- coding: utf-8 -*-
import re
from pyknp import Juman
import itertools
from itertools import product
from math import sqrt
juman = Juman(command="/home/huang/usr/bin/juman", rcfile="/home/huang/usr/etc/jumanrc")

CASE_ENG = ['g', 'w', 'n', 'd']
CASE_KATA = [u"ガ", u"ヲ", u"ニ", u"デ"]
CASE_HIRA = [u"が", u"を", u"に", u"で"]
CASE_VERBOSE = [u'ガ格', u'ヲ格', u'ニ格', u'デ格']

ENG_HIRA = dict(zip(CASE_ENG, CASE_HIRA))
ENG_KATA = dict(zip(CASE_ENG, CASE_KATA))
KATA_ENG = dict(zip(CASE_KATA, CASE_ENG))
VER_ENG = dict(zip(CASE_VERBOSE, CASE_ENG))
ENG_VER = dict(zip(CASE_ENG, CASE_VERBOSE))

verb_pattern = r"[12]([vjn])([APCKML])(.+)$"
noun_pattern = r"([12])([gwnod])(\d*)(.+)$"
####
from itertools import product, combinations, permutations
AL = list(product(CASE_ENG, CASE_ENG)) 
AL = map(lambda x:"%s-%s" % (x[0], x[1]), AL)
ALL_ALIGN = list(combinations(AL, 1)) + list(combinations(AL, 2)) + list(combinations(AL, 3)) + list(combinations(AL, 4))
ALL_ALIGN = map(lambda x: list(x), ALL_ALIGN)
ALL_ALIGN.append([])
ALL_ALIGN2 = []
for i in [1,2,3,4]:
    for p1 in combinations(CASE_ENG, i):
        for p2 in permutations(CASE_ENG, i):
             align = ["%s-%s" % (p1[x], p2[x]) for x in range(i)]
             if align not in ALL_ALIGN2:
                 ALL_ALIGN2.append(align)
ALL_ALIGN2.append([])
####


def get_verb_form(vStr, voice):
    sahen = isSahen(vStr)
    if voice == 'P':
        if sahen:
            vStr += "+する/する"
        vStr += "+れる/れる"
    if voice == 'C':
        if sahen:
            vStr += "+する/する"
        vStr += "+せる/せる"
    # not inplement 'L' since there is none.
    return vStr

def isSahen(vStr):
    result = juman.analysis(vStr.decode('utf-8').split('/')[0])
    if len(result.mrph_list()) == 1 and result.mrph_list()[0].bunrui == u'サ変名詞':
        return True
    return False

def remove_hira(rep_str, split_char=['+'], keep_plus=True):
    # ex: 応募/おうぼ+箱/はこ --> 応募箱
    readable_strs = re.split(r'[%s]+' % ("".join(split_char)), rep_str)
    readable_strs = map(lambda x: x.split('/')[0], readable_strs)
    if keep_plus:
        return '+'.join(readable_strs)
    else:
        return "".join(readable_strs)

import sys
query_dict = {u"う":u"わ", u"く":u"か", u"す":u"さ",u"る":u"ら",u"む":u"ま", u"ぶ":u"ば"}
def get_verb_query(verb_rep):
    # ex: 出荷+する+れる --> 出荷される
    verb_pieces = verb_rep.split('+')
    if verb_pieces[-1] in [u"する", u"なる"]:
        if verb_pieces[-2][-1] == u"だ":
            verb_pieces[-2] = verb_pieces[-2][:-1] + u"に"
            return "".join(verb_pieces)
        elif verb_pieces[-2].endswith(u"い"):
            verb_pieces[-2] = verb_pieces[-2][:-1] + u"く"
            return "".join(verb_pieces)
        else:
            sys.stderr.write("cannot convert %s-%s\n" % (verb_rep, verb_pieces[-2][-1]))
            return None

    if verb_pieces[-1] in [u"せる", u"れる"]:
        if verb_pieces[-2] == u"する":
            verb_pieces[-2] = u"さ"
            return "".join(verb_pieces)

        verb_pieces[-2] = verb_pieces[-2][:-1] + query_dict[verb_pieces[-2][-1].decode('utf-8')]
        return "".join(verb_pieces)
    return "".join(verb_pieces)


def process_gold(raw_gold):
    if raw_gold == ['null']:
        return []
    raw_gold = map(lambda x: x.replace("\'",""), raw_gold)
    raw_gold = map(lambda x: x.replace("g2","g"), raw_gold)
    raw_gold = map(lambda x: x.replace("(",""), raw_gold)
    raw_gold = map(lambda x: x.replace(")",""), raw_gold)
    
    trim_gold = []
    for g in raw_gold:
        if '/' in g:
            c1, c2 = g.split('-')
            all_possibility = product(c1.split('/'), c2.split('/')) 
            all_possibility = map(lambda x:"%s-%s" % (x[0], x[1]), all_possibility)
            trim_gold += all_possibility
        else:
            trim_gold.append(g)
    trim_gold = list(set(trim_gold))
    trim_gold = filter(lambda x: 'p' not in x, trim_gold)
    return trim_gold


def vector_norm(v):
    """
    expect a dictionary as input
    """
    n2 = 0
    for key, value in v.iteritems():
        if key == 'all':
            continue
        n2 += value ** 2
    return sqrt(n2)

def cosine_similarity(v1, v2, get_score=False, strip=False):
    """
    calculate cosine similarity of two dictionary-vector.
    """
    norm_v1 = vector_norm(v1)
    norm_v2 = vector_norm(v2)
    denom = norm_v1 * norm_v2
    if denom == 0:
        return 0
    if strip:
        v1 = {"+".join(map(lambda x: x.split('/')[0], arg.split('+'))) : count for arg, count in v1.iteritems()}
        v2 = {"+".join(map(lambda x: x.split('/')[0], arg.split('+'))) : count for arg, count in v2.iteritems()}

    #calculate inner product
    inner = 0
    sharedArg = set(v1.keys()).intersection(set(v2.keys()))
    for w in sharedArg:
        inner += v1[w]*v2[w]

    if get_score == True:
        return (inner * (norm_v1 + norm_v2)) / denom
    else :
        return inner/denom

def get_amb_key(pred_repStr):
    """
    given the rename of a predicate,
    return the ambiguous predicate repname.
    (if the ambiguous predicate repname is the same as the repname given, return empty string.)
    """
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
