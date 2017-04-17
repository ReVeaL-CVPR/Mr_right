# Mr_right
A mobile app recommendation assistant



**This part is to add tags of page content**



```
├──	readme.md   
├──	corpus_3_PagesPerItem_de/		#
│	├──	pre							# Model & some global files
│	├──	tag_corpus					# Corpus of each tags, comerge several docs
├──	database/
│	├──	...							# API returns
├──	res/							# Result
│	├──	compare						# Compare if using stopwords
│	├──	...							# Test results for each lable
├──	source/												
│	├──	chinese						# Chinese stopwords
├──	crawler.py						# Crawler corpus for an entry					
├──	tagger.py						# Topic model train, pred & test
├──	tidy.py							# Utility for txt filtering
├──	tag_vectors						# Dumped list of tag vectors
├──	sb								# A test corpus about movie "fast8"
```
