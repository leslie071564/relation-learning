# -*- coding: utf-8 -*-
import sys
import numpy as np
from gensim.models import Word2Vec
from sklearn.manifold import TSNE
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import mpld3
model_file = "/share/data/word2vec/2016.09.14/w2v.midasi.256.100M.bin"
model = Word2Vec.load_word2vec_format(model_file, binary=True)
V = model.vocab.keys()
plot_file = "/data/huang/pair1_10.txt"

def get_offset(w1, w2):
    w1 = w1.decode("utf-8")
    w2 = w2.decode("utf-8")
    if (w1 not in V) or (w2 not in V):
        return None
    return model[w1] - model[w2]


if __name__ == "__main__":
    vocabs = []
    vecs = []
    for line in open(plot_file, "r").readlines():
        w1, w2 = line.rstrip().split() 
        if w1 == w2:
            continue
        offset = get_offset(w1, w2)
        if offset == None:
            continue
        word_pair = "%s-%s" % (w1, w2)
        if word_pair in vocabs:
            continue
        vocabs.append(word_pair)
        vecs.append(offset)
    print len(vocabs)
    
    # fit t-SNE
    tsne = TSNE(n_components=2, random_state=0)
    Y = tsne.fit_transform(vecs)

    # plot
    fig = plt.figure()
    ax = fig.add_subplot(111)
    SCATTER = ax.scatter(Y[:,0], Y[:,1], s=1)
    tooltip = mpld3.plugins.PointLabelTooltip(SCATTER, labels=vocabs)
    mpld3.plugins.connect(fig, tooltip)
    mpld3.save_html(fig, "/home/huang/public_html/relation/test.html")
    
