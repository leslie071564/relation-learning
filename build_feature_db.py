# -*- coding: utf-8 -*-
import sys
from Event import *
import ConfigParser
config = ConfigParser.RawConfigParser()
config.read('./data_location.ini')
EVENT_DB = shelve.open(config.get('DB', 'EVENT_DB'), flag='r')
FEAT_DB = shelve.open(config.get('DB', 'FEAT_DB'))

if __name__ == "__main__":
    """test
    num = "104401"
    ev = Event(num, EVENT_DB[num])
    print ev.get_all_features_dict()
    sys.exit()
    """
    for num in open(IDS_FILE, 'r').readlines():
        num = num.rstrip()
        print num
        ev = Event(num, EVENT_DB[num])
        FEAT_DB[num] = ev.get_all_features_dict()
