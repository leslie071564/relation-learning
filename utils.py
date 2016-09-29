# -*- coding: utf-8 -*-
CASE_ENG = ['g', 'w', 'n', 'd']
CASE_KATA = [u"ガ格", u"ヲ格", u"ニ格", u"デ格"]
CASE_HIRA = [u"が", u"を", u"に", u"で"]
verb_pattern = r"[12]([vjn])([APCKML])(.+)$"
noun_pattern = r"([12])([gwnod])(\d*)(.+)$"
from pyknp import Juman
juman = Juman(command="/home/huang/usr/bin/juman", rcfile="/home/huang/usr/etc/jumanrc")

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

