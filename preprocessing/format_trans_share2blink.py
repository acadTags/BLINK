# transfer the format of share to blink
# to do: further preprocessing: tokenisation if needed

import os
import math
import json
#for tokenisation
from nltk.tokenize import RegexpTokenizer

#https://stackoverflow.com/a/5389547/5319143
def grouped(iterable, n=2):
    "s -> (s0,s1,s2,...sn-1), (sn,sn+1,sn+2,...s2n-1), (s2n,s2n+1,s2n+2,...s3n-1), ..."
    return zip(*[iter(iterable)]*n)

def pairwise(iterable):
    "s -> (s0, s1), (s2, s3), (s4, s5), ..."
    a = iter(iterable)
    return zip(a, a)

#output str content to a file
#input: filename and the content (str)
def output_to_file(file_name,str):
    with open(file_name, 'w', encoding="utf-8-sig") as f_output:
        f_output.write(str)

def preprocess(text):
    #set the tokenizer: retain only alphanumeric and dots
    tokenizer = RegexpTokenizer(r'\w+.') # original
    return ' '.join([t for t in tokenizer.tokenize(text)])

# create testing data
'''
Input format:
00176-102920-ECHO_REPORT.txt||Disease_Disorder||C0031039||120||140
document in the .txt file
there is a folder of documents： ‘ALLREPORTS test’

Output format: Each line is of form
{"context_left": "CRICKET -", "mention": "LEICESTERSHIRE", "context_right": "TAKE", "query_id": "947testa CRICKET:0", "label_id": "1622318", "Wikipedia_ID": "1622318", "Wikipedia_URL": "http://en.wikipedia.org/wiki/Leicestershire_County_Cricket_Club", "Wikipedia_title": "Leicestershire County Cricket Club"}
'''

context_length = 256 # the overall length of context (left + right)

do_preprocessing = False

input_data_folder_path = '../data/shareclef-ehealth-2013-natural-language-processing-and-information-retrieval-for-clinical-care-1.0'
train_doc_folder_name = 'ALLREPORTS'
test_doc_folder_name = 'ALLREPORTS test'
train_mentions_folder_name = 'CLEFPIPEDELIMITED NoDuplicates 3:7:2013'
test_mentions_folder_name = 'Gold_SN2012' # Gold_SN2011 (what's the difference?)

# create data.json
for data_split_mark in ['train','test']:
    list_data_json_str = [] # gather all the jsons (each for a mention and its entity) from the document 
    if data_split_mark == 'train':
        input_data_doc_folder_path = input_data_folder_path + '/' + train_doc_folder_name
        input_data_mentions_folder_path = input_data_folder_path + '/' + train_mentions_folder_name
    else:
        input_data_doc_folder_path = input_data_folder_path + '/' + test_doc_folder_name
        input_data_mentions_folder_path = input_data_folder_path + '/' + test_mentions_folder_name

    for filename in os.listdir(input_data_doc_folder_path):
        if filename.endswith(".txt"): 
            #print(os.path.join(input_data_doc_folder_path, filename))
            print(filename)
            #open doc
            with open(os.path.join(input_data_doc_folder_path,filename),encoding='utf-8') as f_content:
                doc = f_content.read()
                #print(doc)
            #open mentions of the doc
            filename = filename[:len(filename)-len('.txt')] + '.pipe.txt' if data_split_mark == 'train' else filename #change filename ending to .pipe.txt for training data            
            mentions_file_path = os.path.join(input_data_mentions_folder_path,filename)
            #print(mentions_file_path)
            if os.path.exists(mentions_file_path):
                #print('exist')
                with open(mentions_file_path,encoding='utf-8') as f_content:
                    mention_records = f_content.readlines()
            else:  
                mention_records = ''        
            #print(doc)
            #print(mentions)    

            #loop over mention_records to form the output json format - as each doc has many mentions
            for mention_record in mention_records:
                #print(len(mention.split('||')))
                mention_eles = mention_record.split('||')
                concept = mention_eles[2]
                mention = ''
                # aggregating the discontinous entities, and get the context between the mentions
                context_between = ''
                for mention_pos_start,mention_pos_end in grouped(mention_eles[3:],2):
                    mention_pos_end_prev = mention_pos_end
                    mention = mention + doc[int(mention_pos_start):int(mention_pos_end)]
                    context_between = context_between + doc[int(mention_pos_end_prev):int(mention_pos_start)]                
                #print(mention + ' ' + concept)   
                # get the left and right contexts (each as half of context_length tokens)
                doc_ctx_left = doc[:int(mention_pos_start)]
                doc_ctx_left_tokens = doc_ctx_left.split(' ')
                ctx_len_half = math.floor(context_length/2) #math.floor((context_length-1)/2)
                context_left = ' '.join(doc_ctx_left_tokens[-ctx_len_half:])
                ctx_btwn_len = len(context_between.split(' '))
                doc_ctx_right = doc[int(mention_pos_end):]
                context_right = context_between + ' '.join(doc_ctx_right.split(' ')[0:ctx_len_half - ctx_btwn_len])            
                
                #if concept == 'CUI-less':
                #    print('\t', 'ctx_left:',len(context_left.split()), context_left)
                #    print('\t', 'mention and concept:',mention, concept)#
                #    print('\t', 'ctx_right:',len(context_left.split()), context_right)

                #preprocessing if chosen to
                if do_preprocessing:
                    context_left = preprocess(context_left)
                    context_right = preprocess(context_right)

                #form the dictionary for this data row
                dict_data_row = {}
                dict_data_row['context_left'] = context_left
                dict_data_row['mention'] = mention
                dict_data_row['context_right'] = context_right
                dict_data_row['label_id'] = concept
                
                data_json_str = json.dumps(dict_data_row)
                list_data_json_str.append(data_json_str)

    output_to_file('share_clef_2013_%s%s.json' % (data_split_mark, '_preprocessed' if do_preprocessing else ''),'\n'.join(list_data_json_str))

    # get a randomly sampled subset for quick training/testing
    import random
    random.Random(1234).shuffle(list_data_json_str)
    n_data_selected = 100
    output_to_file('share_clef_2013_%s%s_sampled.json' % (data_split_mark, '_preprocessed' if do_preprocessing else ''),'\n'.join(list_data_json_str[:100]))