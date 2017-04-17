#coding:utf-8
from gensim import corpora, models, similarities
from collections import defaultdict
from multiprocessing.dummy import Pool
import json
import sys
import os
import crawler
import jieba
import numpy as np
import logging
import codecs
from nltk.corpus import stopwords
import argparse

cns = stopwords.words('chinese')

reload(sys)
sys.setdefaultencoding('utf-8')

dir = crawler.corpusName

def cal_frequency(ll):
    frequency = defaultdict(int)
    for wl in ll:
        for word in wl:
            frequency[word] += 1
    return frequency

def cos(vector1, vector2):
    vector1 = [i[1] for i in vector1]
    vector2 = [i[1] for i in vector2]
    dot_product = 0.0;
    normA = 0.0;
    normB = 0.0;
    for a, b in zip(vector1, vector2):
        dot_product += a * b
        normA += a ** 2
        normB += b ** 2
    if normA == 0.0 or normB == 0.0:
        print vector1, vector2
        return None
    else:
        return abs(dot_product) / ((normA * normB) ** 0.5)

def file_extension(path):
    return os.path.splitext(path)[1]


def pre_process():
    global dir
    # try:
    if not os.path.exists(dir + '/pre'):
        os.mkdir(dir + '/pre')
    list = os.listdir(dir)
    all_words = []
    corpus_dict = {}
    tag_dict = {}
    docs = {}
    i = 0
    # list: txts in corpus
    for ll in list:
        #
        if file_extension(ll) != '.txt':
            continue
        dd = dir + "/" + ll
        tag = ll.replace('.txt', '')
        print(tag)
        content = json.loads(open(dd).read())
        tag_doc = []
        for k in content:
            tag_doc += [content[k]]
        docs[tag] = tag_doc
        frequency = cal_frequency(tag_doc)
        tag_word_list = []
        for k in content:
            for word in content[k]:
                if frequency[word] > 2 and word not in cns and word not in tag_word_list:
                    tag_word_list += [word]
            tag_dict[i] = tag
            i += 1
        all_words += [tag_word_list]

    dictionary = corpora.Dictionary(all_words)
    all_corpus = []
    for tag in docs:
        tag_corpus = []
        for doc in docs[tag]:
            tag_corpus += doc
            all_corpus += [dictionary.doc2bow(doc)]
        corpus_dict[tag] = dictionary.doc2bow(tag_corpus)
        # save tag_corpus
        file = codecs.open(dir + '/tag_corpus/%s'% tag, 'w', "utf-8")
        file.write(json.dumps(tag_corpus, ensure_ascii=False))
        file.close()

    dictionary.save(dir + '/pre/all.dict')
    corpora.MmCorpus.serialize(dir + '/pre/all.mm', all_corpus)  # store to disk, for later use

    # save doc2tag dict
    file = codecs.open(dir + '/pre/tag.dict', 'w', "utf-8")
    file.write(json.dumps(tag_dict, ensure_ascii=False))
    file.close()

    return dictionary, all_corpus, corpus_dict


def train_lsi(all_corpus, dictionary):
    global dir
    tfidf = models.TfidfModel(all_corpus)
    corpus_tfidf = tfidf[all_corpus]
    lsi = models.LsiModel(corpus_tfidf, id2word=dictionary, num_topics=10)
    lsi.save(dir + '/pre/all.lsi')
    corpus_lsi = lsi[corpus_tfidf]
    return lsi, corpus_lsi

def test_lsi(test_dir, tag_vectors):
    test_tags = os.listdir(test_dir)
    lsi = models.LsiModel.load(dir + '/pre/all.lsi', mmap='r')
    dic = corpora.Dictionary.load(dir + '/pre/all.dict', mmap='r')
    # corpus = corpora.MmCorpus(dir + '/pre/all.mm', )
    for test_tag in test_tags:
        if test_tag == ".DS_Store":
            continue
        test_tag_dir = os.path.join(test_dir, test_tag)
        test_files = os.listdir(test_tag_dir)

        label = test_tag.split("-")[0:2]
        tp, fp, fn, n = 0, 0, 0, 0

        file = open("res/result_%s" % test_tag, "w")

        for test_file in test_files:
            test_path = os.path.join(test_tag_dir, test_file)
            f = open(test_path, "r").read()
            fwords = []
            fwords += [i for i in jieba.cut(f, cut_all=True) if i != '']
            sorted_cos = pred_lsi(lsi, dic, tag_vectors, fwords)
            if not sorted_cos:
                print test_path
                continue
            file.write("file %s:\n" % test_file)
            pred = sorted_cos[0][0].split("_")[0:2]
            n += 1
            tp += int(pred == label)

            file.write("%s\n\n" % str(sorted_cos))

        score = tp * 1.0 / n
        file.write("score: %f, tp = %d, n = %d\n" % (score, tp, n))
        print "score: %f, tp = %d, n = %d\n" % (score, tp, n), label
        file.close()

def pred_lsi(lsi, dic, tag_vectors, fwords):
    fwords_filter = [i for i in fwords if i != '']
    if len(fwords_filter) == 0:
        return None
    bow = dic.doc2bow(fwords_filter)
    # print query_lsi
    test_vector = lsi[bow]
    res_cos = []
    for tag in tag_vectors:
        res_cos.append((tag, cos(tag_vectors[ tag ], test_vector)))
    sorted_cos = sorted(res_cos, key=lambda item: -item[1])
    return sorted_cos

def tag_vector():
    lsi = models.LsiModel.load(dir + '/pre/all.lsi', mmap='r')
    dic = corpora.Dictionary.load(dir + '/pre/all.dict', mmap='r')
    corpus = corpora.MmCorpus(dir + '/pre/all.mm', )
    # index = similarities.MatrixSimilarity(lsi[corpus])

    tag_vectors = {}
    tags = os.listdir(dir + '/tag_corpus')
    for tag in tags:
        tag_corpus = json.loads(open(dir + '/tag_corpus/%s'% tag).read())
        tag_bow = dic.doc2bow(tag_corpus)
        tag_vector = lsi[tag_bow]
        tag_vectors[ tag ] = tag_vector
    f = codecs.open("tag_vectors", "w", "utf-8")
    f.write(json.dumps(tag_vectors, ensure_ascii=False))
    f.close()

    return  tag_vectors

def wrapper_pool(item_string):
    items = item_string.split(' ')
    pool = Pool(processes=16)
    result = pool.map( wrapper, items )
    print result
    result = {item[0]: item[1] for item in result}
    return json.dumps(result, ensure_ascii=False)

def wrapper(item):
    # _tag_vectors = tag_vector()
    tag_vectors = json.loads(open("tag_vectors").read())
    # test_lsi("tag_test", tag_vectors)

    lsi = models.LsiModel.load(dir + '/pre/all.lsi', mmap='r')
    dic = corpora.Dictionary.load(dir + '/pre/all.dict', mmap='r')

    entry, entry_doc = crawler.fetch_html_doc(item)
    sorted_cos = pred_lsi(lsi, dic, tag_vectors, entry_doc)
    print sorted_cos, "\nreturn the first rank...", item
    result = [x for x in sorted_cos if x[1] > 0.8]
    if not len(result):
        result.append( sorted_cos[0] )
    result_ = result[ 0: min(len(result), 3)]

    return item, result_

if __name__ == '__main__':
    # construct the argument parse and parse the arguments
    # ap = argparse.ArgumentParser()
    # ap.add_argument("-i", "--item", required=True, help="entry words")
    # args = vars(ap.parse_args())

    # item = args["速度与激情8 小红袍 火锅店"]

    # dictionary, all_corpus, corpus_dict = pre_process()
    # lsi, corpus_lsi = train_lsi(all_corpus, dictionary)
    # lsi.print_topics(num_topics=10)
    items = "速度与激情8 小红袍 火锅店"
    result =wrapper_pool(items)

    # print result

     # print entry
    f = codecs.open("sb", "w", "utf-8")
    f.write(result)
    # print entry_doc
    # for tag, lsi in zip(corpus_dict, corpus_lsi):
    #     print(tag, list(lsi))

