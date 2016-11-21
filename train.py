# -*- coding: utf-8 -*-
import sys
import os
import os.path
from optparse import OptionParser
from subprocess import call, check_output
from print_feature_file import print_train_file
import ConfigParser
config = ConfigParser.RawConfigParser()
# retrieve data locations. 
config.read('./data_location.ini')
config.read('./settings.ini')

def initialize(ids_file):
    # MODIFY.
    for num in open(ids_file, 'r').readlines():
        num = num.rstrip()
        print "%s_0_0" % (num)


if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("--initialize", action='store_true', default=False, dest='initialize')

    parser.add_option("--cv_dir", action='store', dest='cv_dir')
    parser.add_option("--cv_train_dir", action='store', dest='train_dir')
    parser.add_option("--cv_test_dir", action='store', dest='test_dir')

    parser.add_option("--train_ids", action='store', dest='train_ids')

    options, args = parser.parse_args()

    if options.initialize:
        initialize(options.train_ids)







