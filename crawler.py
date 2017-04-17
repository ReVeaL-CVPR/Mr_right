#coding:utf-8

import requests
import codecs
import os
import sys
import requests
import json
import lxml
from bs4 import BeautifulSoup
from multiprocessing.dummy import Pool
import socket
import re
import jieba

reload(sys)
sys.setdefaultencoding('utf-8')


socket.setdefaulttimeout(5)
sess = requests.session()
KeyMaps = {"product":["title", "description", "price", "salesVolume", "score", "freight","promotionalInfo", "tags"],\
"restaurant":["title", "description", "price", "score", "salesVolume", "freight", "tel", "address", "openTime", "longitude", "latitude"],\
"video":["title", "description", "uploader", "uploadTime", "videoTime", "playCount", "commentCount", "comments", "tags"],\
"movie":["title", "description","score", "director", "star", "language", "countries", "movieType", "evaluateCount", "comments", "releaseTime", "movieTime", "tags"],\
"music":["title", "singer", "lyricist", "composer", "lyric", "musicTime", "album", "tags", "releaseTime", "commentCount", "comments"],\
"news":["title", "writer", "description", "press", "publishedDate"],\
"question":["questionTime", "answerWriter", "answerContent", "answerTime"],\
"travel":["title", "city", "address", "description", "trafficInfo"]\
}

CorpusSize = 3
# the number of pages extracted from baidu search
EntrySize = 30
# the number of pages extracted from database

api = "http://60.205.139.71:8080/MobileSearch/api/dataset!get.action?"

database_dir = "database"
corpusName = "corpus_" + str(CorpusSize) + "_PagesPerItem_de"


def init_list():
    if not os.path.exists(database_dir):
        os.mkdir(database_dir)
    for typeName in KeyMaps:
        fieldNameList = KeyMaps[typeName]
        for fieldName in fieldNameList:
            tagLocalpath = database_dir + "/" + typeName + "_" + fieldName + ".txt"
            if not os.path.exists(tagLocalpath):
                # file = codecs.open(tagLocalpath, 'w', "utf-8")
                # file.write(json.dumps({}, ensure_ascii=False))
                # file.close()
                _url = api + "typeName=" + typeName + "&fieldName=" + fieldName + "&size=" + str(EntrySize)
                req = requests.get(_url, timeout=5)
                req.encoding = 'utf-8'
                print(_url)
                req = req.json()
                if req['count'] > 0:
                    res = [item for item in req['results'] if item != '']
                    print(_url, res)
                    res = list(set(res))
                    file = codecs.open(tagLocalpath, 'w', "utf-8")
                    file.write(json.dumps(res, ensure_ascii=False))
                    file.close()


def getWordsUrl(item):
    url = 'http://www.baidu.com/s?wd=' + item + '&rn=' + str(CorpusSize)
    r = sess.get(url)
    xpath = u"///h3/a/@href"
    html_map = lxml.etree.HTML(r.text)
    links = html_map.xpath(xpath)
    return links

def fetch_html_doc(entry):
    res = []
    try:
        links = getWordsUrl(entry)
        for link in links:
            req = requests.get(link, timeout=1)
            soup = BeautifulSoup(req.content, "lxml")
            for script in soup.findAll('script'):
                script.extract()
            for style in soup.findAll('style'):
                style.extract()
            reg = re.compile("<[^>]*>")
            content = entry + ' ' + reg.sub('', soup.prettify())
            list = re.split('\r|\n| ', content)
            for item in list:
                if item != '':
                    res += [i for i in jieba.cut(item, cut_all=True) if i != '']
    except Exception as e:
        print(e)
    return entry, res

def crawl_from_web():
    if not os.path.exists(corpusName):
        os.mkdir(corpusName)
    pool = Pool(processes=16)
    list = os.listdir(database_dir)
    cnt = 1
    for ll in list:
        if ll == '.DS_Store':
            continue
        dir = database_dir + "/" + ll
        out = corpusName + '/' + ll
        if os.path.exists(out):
            continue
        content = json.loads(open(dir).read())
        docs = pool.map(fetch_html_doc, content)
        docs = {item[0]: item[1] for item in docs if item[1] != ''}
        print(cnt, len(docs))
        cnt += 1
        file = codecs.open(out, 'w', "utf-8")
        file.write(json.dumps(docs, ensure_ascii=False))
        file.close()


if __name__ == '__main__':
    # init_list()
    crawl_from_web()

