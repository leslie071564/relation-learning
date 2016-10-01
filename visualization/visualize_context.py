# -*- coding: utf-8 -*-
import sys
import shelve
import argparse
from math import log
from gensim.models import Word2Vec
model_file = "/share/data/word2vec/2016.09.14/w2v.midasi.256.100M.bin"
model = Word2Vec.load_word2vec_format(model_file, binary=True)
VOCAB = model.vocab.keys()
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import mpld3
from sklearn.manifold import TSNE
COUNT_DB = shelve.open("/zinnia/huang/EventKnowledge/data/NP_Statistics.db", flag='r')
#N = len(COUNT_DB.keys()) - 1
N = 819
TFIDF_THRESHOLD = 5
ENLARGE = 5

def check_arg_appearance(arg):
    for num in COUNT_DB.keys():
        if num == "total":
            continue
        if arg in COUNT_DB[num].keys():
            print "%s in ID-%s: %s" % (arg, num, COUNT_DB[num][arg])

def tf_idf(arg, event_id):
    tf = COUNT_DB[event_id][arg]
    total_app = COUNT_DB['total'][arg]
    idf = log(1 + float(N)/total_app)
    return tf*idf

### to be modified:
# sometime skipping predicates preocess is needed.
def get_skip(cmd_str):
    cmd_str = cmd_str.decode('utf-8')
    return cmd_str.split("_")

def plot(event_id, skip):
    vocabs = {}
    vecs = []
    #OOV = {}
    for arg in COUNT_DB[event_id]:
        if arg in skip:
            continue
        tfidf = tf_idf(arg, event_id)
        if tfidf < TFIDF_THRESHOLD:
            continue
        arg = "".join(arg.split('+'))
        if arg not in VOCAB: 
            sys.stderr.write("%s not in vocabulary.\n" % arg)
            #OOV[arg] = tfidf
            continue
        vocabs[arg] = tfidf
        vecs.append(model[arg])

    # tSNE.
    tsne = TSNE(n_components=2, random_state=0)
    Y = tsne.fit_transform(vecs)

    # plot.
    fig = plt.figure()
    ax = fig.add_subplot(111)
    SCATTER = ax.scatter(Y[:,0], Y[:,1], s=map(lambda x:x*ENLARGE,  vocabs.values()))
    tooltip = mpld3.plugins.PointLabelTooltip(SCATTER, labels=map(lambda x: "%s:%s" % (x[0], x[1]), vocabs.items()))
    mpld3.plugins.connect(fig, tooltip)
    html_page = "/home/huang/public_html/relation/%s.html" % (event_id)
    mpld3.save_html(fig, html_page)
    

if __name__ == "__main__":
    # parse cmd arguments.
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', "--event_id", action="store", dest="event_id")
    parser.add_argument('-s', "--skip_words", action="store", dest="skip_words")
    options = parser.parse_args() 

    skip = get_skip(options.skip_words)
    plot(options.event_id, skip)
