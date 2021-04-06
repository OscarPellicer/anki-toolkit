# Anki Toolkit
A simple Python script to generate a deck of Anki cards from a Kindle vocabulary database or a list of words.

# Installation
First, Python is required. If not sure, just download [Miniconda](https://docs.conda.io/en/latest/miniconda.html) and install it.
Then, open a terminal and install the required libraries, clone this repository, and the [KindleUnpack](https://github.com/kevinhendricks/KindleUnpack) repository:
```bash
conda install python==3.7 git
pip install html5lib lxml tqdm fuzzywuzzy[speedup] beautifulsoup4
git clone https://github.com/OscarPellicer/anki-toolkit.git
git clone https://github.com/kevinhendricks/KindleUnpack.git
```

We will navigate to the directory where anki-toolkit was created:
```bash
#We assume that it was git-cloned into the user path (~)
cd anki-toolkit
```

# Preparing a dictionary
Anki Toolkit uses ebook dictionaries to provide the definition / translations for the words. 
For example, we can translate english words into spanish using the openly available **WordNet 3 Infused ES** dictionary.
If you want to use a DRM-protected dictionary (e.g. a dictionary you bought from Amazon), you will need to de-DRM it first. Please look at [Using protected dictionaries](#using-protected-dictionaries)

First, we need to download the dictionary, by going to the [website](http://eb.lv) and downloading **WordNet3 Infused ES**. 

Then, we transform the downloaded `wn3infes.mobi` dictionary to `.html` using [KindleUnpack](https://github.com/kevinhendricks/KindleUnpack):
```bash
#Replace the path to KindleUnpack if it was cloned elsewhere
#Also, replace the dictionary path to wherever it was downloaded
python ../KindleUnpack/lib/kindleunpack.py wn3infes.mobi wordnet3es
```

# Usage
## Basic usage
Once we have a dictionary available, we can directly use it to create Anki cards.

```bash
python ankitk.py -v some translateable words -d wordnet3es/mobi7/book.html -o test.html
```

The first time that an HTML dictionary is used, it will be automatically converted to .tsv for further processing. This might take a while, but must only be done once.

Also, notice that the word `translateable` was misspelled, yet, the correct spelling `translatable` was found. By default, if no exact match is found for a word, fuzzy matching is performed. This can be tweaked or disabled by setting the parameter `--fuzzy_match_score`. By default it has a value of 82: the score of the fuzzy-matched word must be at least 82. Setting it to 0 or a negative value disables it. For instance: `python ankitk.py -v some translateable words -d wordnet3es/book.html -o test.html -f 0` will disregard the misspelled word

Once it has finished, the resulting `test.html` file can be opened with an internet browser for quick visualization, or imported from Anki, by clicking `File > Import`. In the import options, make sure that your desired destination Deck is selected, that `fields are separated by Tab`, and that `Allow HTML in fields` is checked. Then click import, and that's it!

## Reading Kindle vocabulary
To process a Kindle vocabulary database (`vocab.db`) the procedure is the same. First, the file `vocab.db` must be located within the storage of your Kindle device. A typcial path is `D:\system\vocabulary\vocab.db`, where `D:` is the letter assigned to the Kindle device by your computer.

Then, the syntax is identical:

```bash
python ankitk.py -v vocab.db -d wordnet3es/book.html -o test.html -s 2018-20-04
```

Notice that an optional parameter was used `-s 2018-20-04` to only include the words added since a given date. If omitted, all words in `vocab.db` are read.

## Other options
- Besides the previous use cases, the input vocabulary can also be new-line-separated list of words in a file. E.g. `-v words.txt`.
- The encoding for the dictionary and the vocabulary can be manually specified, in case Python does not figure it out by itself. E.g. `-e utf-8`, or `-e windows-1252`.
- If you want your dictionary to only contain plain text (no HTML tags): `-t False`.

# Using protected dictionaries
When using an Amazon-bought dictionary, it must be first de-DRMd, otherwise it is encrypted cannot be used:

1. Download the Calibre de-DRM plugin: https://github.com/apprenticeharper/DeDRM_tools/releases
1. Note the highest Calibre version supported by the plugin, and download and install that Calibre version: https://calibre-ebook.com/download
1. Follow the instructions here to install and use the plugin to obtain a de-DRMd version of your dictionary: https://github.com/apprenticeharper/DeDRM_tools/blob/master/DeDRM_plugin_ReadMe.txt

# Credits
- Most code was based on: https://github.com/wzyboy/kindle_vocab_anki