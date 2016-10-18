# -*- coding: utf-8 -*-
import sys
from Event import *
import ConfigParser
config = ConfigParser.RawConfigParser()
config.read('./data_location.ini')
EVENT_DB = shelve.open(config.get('DB', 'EVENT_DB'), flag='r')

def _print_retrieve_task(pred):
    # take a predicate object as input.
    verb = pred.verb_rep
    query = "%s＊" % get_verb_query(remove_hira(verb, keep_plus=True).decode('utf-8'))
    given_cases = pred.args.keys()
    for case in given_cases:
        query = "%s%s→%s" % (remove_hira(pred.args[case][0]), ENG_HIRA[case], query)
    queries = {}
    for case in CASE_ENG:
        if case in given_cases:
            continue
        queries[case] = "%s%s→%s" % (u"〜物", ENG_HIRA[case], query)
    return queries

def print_retrieve_task(num):
    # TODO: modify hard coding path.
    base_string = "/home/arseny/work/launch/cline.sh %s --num 1000 --format knp > /zinnia/huang/EventKnowledge/data/original_sentences/%s && echo %s"
    ev = Event(num, event_dict=EVENT_DB[num])

    for case, query in _print_retrieve_task(ev.pred1).items():
        file_name = "%s_%s1.txt" % (num, case)
        print base_string % (query, file_name, "finished: %s" % file_name) 
    for case, query in _print_retrieve_task(ev.pred2).items():
        file_name = "%s_%s2.txt" % (num, case)
        print base_string % (query, file_name, "finished: %s" % file_name) 


if __name__ == "__main__":
    print_retrieve_task("104401")

