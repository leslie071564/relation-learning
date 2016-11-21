# -*- coding: utf-8 -*-
import sys
reload(sys)
sys.setdefaultencoding('utf-8')
import shelve
import os.path
import argparse
import jinja2
from Event import Event
from utils import remove_hira
from evaluation import *
import ConfigParser
config = ConfigParser.RawConfigParser()
config.read('./data_location.ini')
#EVENT_DB = shelve.open(config.get('DB', 'EVENT_DB'), flag='r')
IDS_FILE = config.get('Raw', 'IDS')
HTML_DIR = config.get('HTML', 'HTML_ROOT')
EV_PAGE = config.get('HTML', 'EV_PAGE_TEMPLATE')
CF_PAGE = config.get('HTML', 'CF_TEMPATE')
OVERVIEW_PAGE = config.get('HTML', 'OVERVIEW_TEMPLATE')

### cf files related.
def _print_cf_file(ID):
    tLoader = jinja2.FileSystemLoader(searchpath='/')
    env = jinja2.Environment(loader=tLoader)
    cf_template = env.get_template(CF_PAGE)
    #
    EVENT_DB = shelve.open(config.get('DB', 'EVENT_DB'), flag='r')
    ev = Event(ID, EVENT_DB[ID])
    EVENT_DB.close()

    for pred_num in ['1', '2']:
        template_vars = {}
        for rank, cf in enumerate(ev.cf_ids[pred_num]):
            cf_id, cf_str, cf_sim = cf.split("##")
            cf_str = "%s %s" % (cf_str, cf_id.split(':')[0])
            template_vars["cf%s_id" % rank] = cf_id
            template_vars["cf%s_str" % rank] = cf_str
            template_vars["cf%s_sim" % rank] = cf_sim
        output_file = "%s/cf_candidate/%s_%s.html" % (HTML_DIR, ID, pred_num)
        F = open(output_file, 'w')
        F.write(cf_template.render(template_vars))

def print_cf_file():
    for ID in open(IDS_FILE):
        ID = ID.rstrip()
        _print_cf_file(ID)
        sys.stder.write("%s done\n" % ID)

def get_colored_align(gold, output, correct):
    if gold == []:
        gold = ['null']

    correct_gold = [x[0] for x in correct]
    correct_output = [x[1] for x in correct]
    correct_output = filter(lambda x: type(x) == str, correct_output) + sum(filter(lambda x: type(x) == list, correct_output), [])
    if output == ['null'] and gold == ['null']:
        correct_gold.append('null')
        correct_output.append('null')
    # gold align:
    gold_str = []
    for align in gold:
        if align in correct_gold:
            gold_str.append(align)
        else:
            gold_str.append("<font color=\"green\">%s</font>" % (align))
    # output align:
    output_str = []
    for align in output:
        if align in correct_output:
            output_str.append(align)
        else:
            output_str.append("<font color=\"red\">%s</font>" % (align))
    return " ".join(gold_str), " ".join(output_str)


def print_overview(result_file, postfix, print_event_page=False):
    tLoader = jinja2.FileSystemLoader(searchpath='/')
    env = jinja2.Environment(loader=tLoader)
    overview_template = env.get_template(OVERVIEW_PAGE)

    template_vars = {}
    template_vars['postfix'] = postfix
    for line in open(result_file).readlines():
        if line.startswith("@") or line.startswith("Accuracy") or line.startswith("#"):
            continue
        line = line.rstrip().split("_")
        ID, cf1, cf2 = line[:3]
        output = line[3:]
        result_dict = process_id(ID, output, get_set=True)
        colored_gold, colored_output = get_colored_align(result_dict['gold'], output, result_dict['correct'])
        #
        EVENT_DB = shelve.open(config.get('DB', 'EVENT_DB'), flag='r')
        ev = Event(ID, EVENT_DB[ID])
        EVENT_DB.close()
        #
        template_vars['event_str_%s' % ID] = ev.charStr
        template_vars['gold_%s' % ID] = colored_gold
        template_vars['output_%s' % ID] = colored_output
        if print_event_page:
            print_ev(postfix, ID, cf1, cf2, colored_gold, colored_output)
            print "%s done." % ID
    # write template to file.
    output_file = "%s/overview/overview_%s.html" % (HTML_DIR, postfix)
    F = open(output_file, 'w')
    F.write(overview_template.render(template_vars))
    F.close()

def print_ev(postfix, ID, cf_num1, cf_num2, gold, output):
    tLoader = jinja2.FileSystemLoader(searchpath='/')
    env = jinja2.Environment(loader=tLoader)
    ev_template = env.get_template(EV_PAGE)
    #
    EVENT_DB = shelve.open(config.get('DB', 'EVENT_DB'), flag='r')
    ev = Event(ID, EVENT_DB[ID])
    EVENT_DB.close()
    #
    template_vars = {}
    template_vars['id_string'] = ev.charStr_raw 
    template_vars['gold'] = gold
    template_vars['output'] = output
    template_vars['ID'] = ID
    # case frame related.
    cf1 = ev.cf_ids['1'][int(cf_num1)]
    cf_id1, cf_str1, cfsim_1 = cf1.split("##") 
    cf2 = ev.cf_ids['2'][int(cf_num2)]
    cf_id2, cf_str2, cfsim_2 = cf2.split("##")
    # TEMP.
    cf_str1 = "%s %s" % (cf_str1, cf_id1.split(':')[0])
    cf_str2 = "%s %s" % (cf_str2, cf_id2.split(':')[0])
    # TEMP.
    template_vars["cf1_str"] = "%s:%s" % (cf_id1, cf_str1)
    template_vars["cf2_str"] = "%s:%s" % (cf_id2, cf_str2)
    template_vars["cf1_sim"] = cfsim_1
    template_vars["cf2_sim"] = cfsim_2
    # chart
    template_vars["verb_1"] = remove_hira(ev.pred1.verb_rep)
    template_vars["verb_2"] = remove_hira(ev.pred2.verb_rep)
    feat_dict = ev.get_all_features_dict()
    cf_feat_dict = feat_dict["%s_%s" % (cf_num1, cf_num2)]
    for feat_type in ['cfsim', 'context']:
        for k, v in cf_feat_dict[feat_type].items():
            if '_' in k:
                continue
            template_vars["%s_%s" % (k.replace('-',''), feat_type)] = v

    # write template to file.
    output_file = "%s/ids/%s/%s.html" % (HTML_DIR, postfix, ID)
    F = open(output_file, 'w')
    F.write(ev_template.render(template_vars))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', "--result_file", action="store", dest="result_file")
    parser.add_argument('-p', "--postfix", action="store", dest="postfix")
    parser.add_argument("--print_cf", action="store_true", default=False, dest="print_cf")
    parser.add_argument("--print_overview", action="store_true", default=False, dest="print_overview")
    parser.add_argument("--print_ev", action="store_true", default=False, dest="print_ev")
    options = parser.parse_args() 
    if options.print_overview:
        if not options.postfix:
            sys.stderr.write("postfix not specified.")
        elif not os.path.isfile(options.result_file):
            sys.stderr.write("result file not existed.")
        else:
            print_overview(options.result_file, options.postfix, options.print_ev)

    if options.print_cf:
        print_cf_file()

