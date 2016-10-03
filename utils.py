# -*- coding: utf-8 -*-
import re
from pyknp import Juman
import itertools
from itertools import product
juman = Juman(command="/home/huang/usr/bin/juman", rcfile="/home/huang/usr/etc/jumanrc")
CASE_ENG = ['g', 'w', 'n', 'd']
CASE_KATA = [u"ガ格", u"ヲ格", u"ニ格", u"デ格"]
CASE_HIRA = [u"が", u"を", u"に", u"で"]
ENG_HIRA = dict(zip(CASE_ENG, CASE_HIRA))
verb_pattern = r"[12]([vjn])([APCKML])(.+)$"
noun_pattern = r"([12])([gwnod])(\d*)(.+)$"

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

def remove_hira(rep_str, split_char=['+'], keep_plus=False):
    # ex: 応募/おうぼ+箱/はこ --> 応募箱
    readable_strs = re.split(r'[%s]+' % ("".join(split_char)), rep_str)
    readable_strs = map(lambda x: x.split('/')[0], readable_strs)
    if keep_plus:
        return '+'.join(readable_strs)
    else:
        return "".join(readable_strs)

def process_gold(raw_gold):
    if raw_gold == ['null']:
        return []
    raw_gold = map(lambda x: x.replace("\'",""), raw_gold)
    raw_gold = map(lambda x: x.replace("g2","g"), raw_gold)
    
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


