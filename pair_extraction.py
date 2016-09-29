# -*- coding: utf-8 -*-
import sys
import codecs
from BeautifulSoup import BeautifulSoup as bs
dict_files = ["/data/huang/iwanami_utf_8/i%02d_utf8.txt" % x for x in range(1, 31)]

def process_entry(entry):
    related_words = []
    flag = True
    for sense in entry("sense"):
        for mor in sense("mor"):
            word = mor.getText()
            if word == u"。":
                return related_words
            '''
            # flag.
            if word == u"「":
                flag = False
            elif word == u"」":
                flag = True
            if not flag:
                continue
            '''
            # flag.
            # POS
            if mor.get("pos") != u"1":
                continue
            # word length.
            if len(word) == 1:
                continue
            related_words.append(word)
    return related_words


def process_file(file_path):
    soup = bs(codecs.open(file_path, "r", "utf-8"))
    for entry in soup("entry"):
        entry_pos = entry.get("pos")
        if entry_pos != u"名":
            continue
        entry_name = entry.get("knz")
        if entry_name == None:
            entry_name = entry.get("mds")
        if len(entry_name) == 1:
            continue
        related_words = process_entry(entry)
        for w in related_words:
            print "%s %s" % (entry_name.encode("utf-8"), w.encode("utf-8"))
    
if __name__ == "__main__":
    for n in range(10):
        process_file(dict_files[n])
    #soup = bs(codecs.open(dict_files[0], "r", "utf-8"))
    #x = soup("entry", attrs={"id": "1610"})

