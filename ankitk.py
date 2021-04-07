#!/usr/bin/env python

import sys, os, argparse
sys.setrecursionlimit(2000)

from tqdm import tqdm
from bs4 import BeautifulSoup, SoupStrainer
import sqlite3
import itertools
from datetime import datetime
from operator import itemgetter, attrgetter
from collections import namedtuple
from functools import partial
                    
AnkiNote = namedtuple('AnkiNote', 'word usage definition timestamp')

def dict_to_fn(dictionary):
    return lambda a: dictionary[a]

def html_to_tsv(dict_html, dict_tsv, expand_iform=False, sep='\t', 
                input_encoding=None, drop_html_tags=False):
    #Encodings: 'windows-1252', 'utf-8', None

    print('Converting HTML dictionary into TSV dictionary. This will take a while...')
    parse_only_entry = SoupStrainer('entry')
    with open(dict_html, 'r', encoding=input_encoding, errors='ignore') as f:
        soup = BeautifulSoup(f, 'xml', parse_only=parse_only_entry)

    with open(dict_tsv, 'w', encoding='utf-8') as f:
        for entry in tqdm(soup.find_all('entry')):
            orth = entry.find('orth')
            _definition = orth.next_siblings
            stem = orth['value']
            iforms = [i['value'] for i in orth.find_all('iform')]
            try:
                definition = ''.join(
                    (str(tag) if not drop_html_tags else tag.get_text()) for tag in _definition
                    if tag.name != 'a'  # anchors do not work in Anki, strip them
                ).strip()
                f.write(f'{stem}{sep}{definition}\n')
                if expand_iform:
                    for iform in iforms:
                        f.write(f'{iform}{sep}{definition}\n')
            except Exception as e:
                print('Exception reading %s: '%stem, e)

def get_vocab(vocab_db='vocab.db', since='1990-01-01'):
    '''
        Parses a kindle vocab.db file into a list of sqlite3 rows
        vocab_db: string with path to vocab.db file
        since: string with the date from which to get the words onwards
    '''
    since= datetime.strptime(since, '%Y-%m-%d')
    if isinstance(since, datetime):
        since = int(since.timestamp()) * 1000
    else:
        since = since * 1000

    db = sqlite3.connect(vocab_db)
    db.row_factory = sqlite3.Row
    cur = db.cursor()
    sql = '''
        select WORDS.stem, WORDS.word, LOOKUPS.usage, BOOK_INFO.title, LOOKUPS.timestamp
        from LOOKUPS left join WORDS
        on WORDS.id = LOOKUPS.word_key
        left join BOOK_INFO
        on BOOK_INFO.id = LOOKUPS.book_key
        where LOOKUPS.timestamp > ?
        order by WORDS.stem, LOOKUPS.timestamp
    '''
    rows = cur.execute(sql, (since,)).fetchall()
    return rows

def make_notes(vocab, dictionary, include_nodef=False, remove_hyperlinks=True,
               fuzzy_match_score=80):
    '''
        Make Anki notes
        vocab: Can either be the output from get_vocab() or a list of words
        dictionary: Can either be a dict(), a function, or a string path to a '.tsv' file.
        include_nodef: include words for which no definitions were found. False by default
        remove_hyperlinks: remove hyperlinks from ouput html
        fuzzy_match_score: score above which words not found in the index will be automatically matched and fixed
    '''
    print('Generating Anki notes. Any words not that were not found will appear hereafter:')
    #Load dictionary
    if isinstance(dictionary, str):
        with open(dictionary, 'r', encoding='utf-8') as f:
            dictionary = dict(line.split('\t') for line in f.readlines())
        dict_db= dict_to_fn(dictionary)
        keys= list(dictionary.keys())
    elif isinstance(dictionary, dict):
        dict_db= dict_to_fn(dictionary)
        keys= list(dictionary.keys())
    else:
        dict_db= dictionary
        keys= None
        
    #Vocab can either be a list of tuples (word, extra_info), or a list of sqlite3 rows
    if len(vocab) > 0 and isinstance(vocab[0], sqlite3.Row):
        iterable= itertools.groupby(vocab, itemgetter('stem'))
    else:
        iterable= [ ( word, ([{'usage':extra_info, 'title':'', 'timestamp':None, 'word':None}]
                         if extra_info is not None else []) )
                             for word, extra_info in vocab]

    stems_no_def = set()
    notes = []
    # vocab is a list of db rows order by (stem, timestamp)
    for i, (stem, entries) in enumerate(iterable):
        try:
            # Merge multiple usages into one.
            usage_all = ''
            usage_timestamp = None
            for entry in entries:
                word = entry['word']
                if word is None:
                    _usage = entry['usage'].strip()
                else:
                    _usage = entry['usage'].replace(word, f'<strong>{word}</strong>').strip()
                usage = f'{_usage}<small> <i>{entry["title"]}</i></small><br>'
                usage_all += usage
                usage_timestamp = entry['timestamp']

            # Look up definition in dictionary
            try:
                definition = dict_db(stem).strip()
                if remove_hyperlinks:
                    definition= definition.replace('<a', '<span').replace('</a', '</span')
            except KeyError:
                #Attempt to fuzzy find the word
                print(' - %s '%stem, end='')
                if fuzzy_match_score > 0:
                    from fuzzywuzzy import process, fuzz
                    key, score= process.extractOne(stem, keys, scorer=fuzz.UQRatio)
                else:
                    key, score= '-', -100
                if score > fuzzy_match_score:
                    print('> %s'%key)
                    definition = dict_db(key).strip()
                    if remove_hyperlinks:
                        definition= definition.replace('<a', '<span').replace('</a', '</span')
                else:
                    #Otherwise, error
                    if fuzzy_match_score > 0:
                        print('> ?? (Closest: %s, score: %d)'%(key, score))
                    else:
                        print('')
                        
                    #Include or ignore
                    if include_nodef or usage_all!='':
                        definition = ''
                    else:
                        stems_no_def.add((i, stem))
                        continue
                        
            note = AnkiNote(stem, usage_all, definition, usage_timestamp)
            notes.append(note)
        except Exception as e:
            print('Exception:', e)
        
    print('Out of all words: %d could be found in the dictionary (or contained extra info), and %d could not'%(
            len(notes), len(stems_no_def)))

    return notes, stems_no_def

def output_anki_tsv(notes, output, sort=True):
    if sort and len(notes) > 0 and notes[0].timestamp is not None:
        notes.sort(key=attrgetter('timestamp'), reverse=True)

    with open(output, 'w', encoding='utf-8') as f:
        for note in notes:
            line = f'{note.word}\t{note.definition}<hr>{note.usage}\n'
            f.write(line)
            
    print('Exported as:', output)

if __name__ == '__main__':
    
    #Parser setup
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--vocabulary', type=str,  default=None, nargs='+',
                        help='Input vocabulary: either a Kindle database (e.g. vocab.db), a simple text file with '+\
                        'a different word in each line (e.g. vocab.txt), or a space-separated list of words (e.g. water melon).'+\
                        'If a .txt file is provided, additional information can be added for each word after a Tab.')
    
    parser.add_argument('-d','--dictionary', type=str, default=None,
                        help='Input dictionary: Can be a tab-separated dictionary (e.g. dictionary.tsv), or an HTML '+\
                        'dictionary ebook, which will be converted to .tsv first (e.g. wordnet3/book.html). Once converted for'+\
                        'the first time, please use the converted .tsv dictionary')
    
    parser.add_argument('-e','--encoding', type=str, default=None,
                        help='Dictionary/Vocabulary encoding: utf-8, windows-1252, etc. By default, python will try to guess it')

    parser.add_argument('-t','--tags', type=bool, default=True,
                        help='Keep HTML tags. Default True')
    
    parser.add_argument('-s', '--since', type=str, default='1990-01-01',
                        help='Since date: If input is a Kindle database, consider only entries from this date onwards. '+\
                        'Default 1990-01-01')
    
    parser.add_argument('-f', '--fuzzy_match_score', type=int, default=82,
                        help='Fuzzy match score: If a key is not found in the dictionary, it will be looked up using fuzzy'+\
                        ' string matching. The highest scoring match, with a score of at least FUZZY_MATCH_SCORE will be '+\
                        'looked up instead. Set to 0 or a negative value to disable fuzzy matching. Default 82')
    
    parser.add_argument('-o', '--output', type=str, default=None,
                        help='Output file: Name of the output file (e.g. anki_export.tsv, or anki_export.html)')

    args = parser.parse_args()
    
    #Run the program
    #Do we need to convert the dictionary?
    dictionary= args.dictionary.replace('.html', '.tsv')
    if args.dictionary.endswith('.html'):
        if os.path.exists(dictionary):
            print('Using existing dictionary: %s'%dictionary)
        else:
            html_to_tsv(args.dictionary, dictionary, input_encoding=args.encoding, drop_html_tags=not args.tags)
    
    #Do we need to read the vocabulary from a text file?
    if args.vocabulary[0].endswith('txt'):
        vocabulary= [ ( line.strip().split('\t', maxsplit=1) if '\t' in line else (line.strip(), None) )
                         for line in open(args.vocabulary[0], encoding=args.encoding)]
    elif args.vocabulary[0].endswith('db'):
        vocabulary= get_vocab(vocab_db=args.vocabulary[0], since=args.since)
    else:
        vocabulary= args.vocabulary
    print('Read %d words'%len(vocabulary))
        
    #Create output
    notes, _ = make_notes(vocabulary, dictionary, fuzzy_match_score=args.fuzzy_match_score)
    output_anki_tsv(notes, output=args.output)
    