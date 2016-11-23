# -*- coding: utf-8 -*-
import sys
import glob
import os
import os.path
from optparse import OptionParser
from subprocess import call, check_output
from collections import defaultdict
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
        print "%s_0_0_all" % (num)

def get_model_dict(model_file):
    pass

def average_model(cv_dir):
    """
    find all the model files model_# under cv_dir, and average them.
    """
    model_dict = defaultdict(int)
    model_num = 0
    for md_file in glob.glob("%s/model?" % cv_dir):
        model_num += 1
        for line in open(md_file, 'r'):
            if line.startswith("@"):
                continue
            line = line.rstrip()
            para, feat = line.split()
            model_dict[feat] += float(para)
    # average:
    if model_num == 0:
        sys.stderr.write("No model file found.\n")
        return None
    averaged_model = {k: v/model_num for k, v in model_dict.iteritems()}
    # write to model file.
    #output_file = "%s/model_averaged" % cv_dir
    for feat, para in averaged_model.items():
        print "%s %s" % (feat, para)
    
if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("--initialize", action='store_true', default=False, dest='initialize')
    parser.add_option("--average_model", action='store_true', default=False, dest='average_model')

    parser.add_option("--cv_dir", action='store', dest='cv_dir')
    parser.add_option("--cv_train_dir", action='store', dest='train_dir')
    parser.add_option("--cv_test_dir", action='store', dest='test_dir')

    parser.add_option("--train_ids", action='store', dest='train_ids')
    options, args = parser.parse_args()

    if options.initialize:
        initialize(options.train_ids)

    if options.average_model:
        average_model(options.cv_dir)

