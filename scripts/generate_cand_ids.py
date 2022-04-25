# generate_cand_ids based on https://github.com/facebookresearch/BLINK/issues/65 and https://github.com/facebookresearch/BLINK/issues/106#issuecomment-1014507351

import torch
from torch.utils.data import DataLoader, RandomSampler, SequentialSampler, TensorDataset
from blink.biencoder.biencoder import load_biencoder
from blink.biencoder.data_process import (
    process_mention_data,
    get_candidate_representation,
)
import json
import sys
import os
from tqdm import tqdm

import argparse

biencoder_config = "models/biencoder_wiki_large.json"
biencoder_model = "models/biencoder_wiki_large.bin"
saved_cand_ids_path = "preprocessing/saved_cand_ids_umls2012AB.pt"
#saved_cand_ids_path = 'models/saved_cand_ids_entity.pt'
# Load biencoder model and biencoder params just like in main_dense.py
with open(biencoder_config) as json_file:
    biencoder_params = json.load(json_file)
    biencoder_params["path_to_model"] = biencoder_model
biencoder = load_biencoder(biencoder_params)

# Read the first 10 or all entities from entity catalogue, e.g. entity.jsonl
entities = []
#count = 10
#with open('models/entity.jsonl') as f:
with open('preprocessing/UMLS2012AB.jsonl', encoding="utf-8-sig") as f:
    for i, line in tqdm(enumerate(f)):
        entity = json.loads(line)
        entities.append(entity)
        #if i == count-1:
        #    break

# Get token_ids corresponding to candidate title and description
tokenizer = biencoder.tokenizer
max_context_length, max_cand_length =  biencoder_params["max_context_length"], biencoder_params["max_cand_length"]
max_seq_length = max_cand_length
ids = []

# it can take around 6 hours to process all 5.9M Wikipedia entities.
for entity in tqdm(entities):
    candidate_desc = entity['text']
    candidate_title = entity['title']
    cand_tokens = get_candidate_representation(
        candidate_desc, 
        tokenizer, 
        max_seq_length, 
        candidate_title=candidate_title
    )

    token_ids = cand_tokens["ids"]
    ids.append(token_ids)

ids = torch.tensor(ids)
print(ids)
torch.save(ids, saved_cand_ids_path)