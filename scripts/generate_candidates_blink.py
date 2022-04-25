# The command to run this script
# To generate original wikipedia entity encodings
# First, run generate_cand_ids to get saved_cand_ids_entity.pt
# PYTHONPATH=. python scripts/generate_candidates_blink.py --path_to_model_config="models/biencoder_wiki_large.json" --path_to_model="models/biencoder_wiki_large.bin" --entity_dict_path="models/entity.jsonl" --saved_cand_ids="models/saved_cand_ids_entity.pt" --encoding_save_file_dir="models/test_ent_enc" --compare_saved_embeds="models/all_entities_large.t7"

# To generate UMLS2012AB and SNOMEDCT overlapped entity encodings with the original biencoder model
# First, run generate_cand_ids to get saved_cand_ids_umls2012AB.pt
# PYTHONPATH=. python scripts/generate_candidates_blink.py --path_to_model_config="models/biencoder_wiki_large.json" --path_to_model="models/biencoder_wiki_large.bin" --entity_dict_path="preprocessing/UMLS2012AB.jsonl" --saved_cand_ids="preprocessing/saved_cand_ids_umls2012AB.pt" --encoding_save_file_dir="models/UMLS2012AB_ent_enc"

# Copyright (c) Facebook, Inc. and its affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
#
import torch
from torch.utils.data import DataLoader, RandomSampler, SequentialSampler, TensorDataset
from blink.biencoder.biencoder import load_biencoder
import elq.candidate_ranking.utils as utils
import json
import sys
import os
from tqdm import tqdm

import argparse


def encode_candidate(
    reranker,
    candidate_pool,
    encode_batch_size,
    silent,
    logger,
):
    reranker.model.eval()
    device = reranker.device
    #for cand_pool in candidate_pool:
    #logger.info("Encoding candidate pool %s" % src)
    sampler = SequentialSampler(candidate_pool)
    data_loader = DataLoader(
        candidate_pool, sampler=sampler, batch_size=encode_batch_size
    )
    if silent:
        iter_ = data_loader
    else:
        iter_ = tqdm(data_loader)

    cand_encode_list = None
    for step, batch in enumerate(iter_):
        cands = batch
        cands = cands.to(device)
        cand_encode = reranker.encode_candidate(cands)
        if cand_encode_list is None:
            cand_encode_list = cand_encode
        else:
            cand_encode_list = torch.cat((cand_encode_list, cand_encode))

    return cand_encode_list


def load_candidate_pool(
    tokenizer,
    params,
    logger,
    cand_pool_path,
):
    candidate_pool = None
    # try to load candidate pool from file
    try:
        logger.info("Loading pre-generated candidate pool from: ")
        logger.info(cand_pool_path)
        candidate_pool = torch.load(cand_pool_path)
    except:
        logger.info("Loading failed.")
    assert candidate_pool is not None

    return candidate_pool


parser = argparse.ArgumentParser()
parser.add_argument('--path_to_model_config', type=str, required=True, help='filepath to saved model config')
parser.add_argument('--path_to_model', type=str, required=True, help='filepath to saved model')
parser.add_argument('--entity_dict_path', type=str, required=True, help='filepath to entities to encode (.jsonl file)')
parser.add_argument('--saved_cand_ids', type=str, help='filepath to entities pre-parsed into IDs')
parser.add_argument('--encoding_save_file_dir', type=str, help='directory of file to save generated encodings', default=None)
parser.add_argument('--test', action='store_true', default=False, help='whether to just test encoding subsample of entities')

parser.add_argument('--compare_saved_embeds', type=str, help='compare against these saved embeddings')

parser.add_argument('--batch_size', type=int, default=512, help='batch size for encoding candidate vectors (default 512)')

# processing every 100
parser.add_argument('--chunk_every_k', type=int, default=100, help='every k data items (or chunks) to be preprocessed, this replaces the original --chunk_start and --chunk_end below')

#parser.add_argument('--chunk_start', type=int, default=0, help='example idx to start encoding at (for parallelizing encoding process)')
#parser.add_argument('--chunk_end', type=int, default=-1, help='example idx to stop encoding at (for parallelizing encoding process)')


args = parser.parse_args()

try:
    with open(args.path_to_model_config) as json_file:
        biencoder_params = json.load(json_file)
except json.decoder.JSONDecodeError:
    with open(args.path_to_model_config) as json_file:
        for line in json_file:
            line = line.replace("'", "\"")
            line = line.replace("True", "true")
            line = line.replace("False", "false")
            line = line.replace("None", "null")
            biencoder_params = json.loads(line)
            break
# model to use
biencoder_params["path_to_model"] = args.path_to_model
# entities to use
biencoder_params["entity_dict_path"] = args.entity_dict_path
biencoder_params["degug"] = False
biencoder_params["data_parallel"] = True
biencoder_params["no_cuda"] = False
biencoder_params["max_context_length"] = 32
biencoder_params["encode_batch_size"] = args.batch_size

saved_cand_ids = getattr(args, 'saved_cand_ids', None)
encoding_save_file_dir = args.encoding_save_file_dir
if encoding_save_file_dir is not None and not os.path.exists(encoding_save_file_dir):
    os.makedirs(encoding_save_file_dir, exist_ok=True)

logger = utils.get_logger(biencoder_params.get("model_output_path", None))
biencoder = load_biencoder(biencoder_params)
baseline_candidate_encoding = None
if getattr(args, 'compare_saved_embeds', None) is not None:
    baseline_candidate_encoding = torch.load(getattr(args, 'compare_saved_embeds'))

candidate_pool = load_candidate_pool(
    biencoder.tokenizer,
    biencoder_params,
    logger,
    getattr(args, 'saved_cand_ids', None),
)
number_of_cands = len(candidate_pool)
print('number of candidates in candidate_pool:',number_of_cands)
if args.test:
    candidate_pool = candidate_pool[:10]

cand_encoding_all = None
for chunk_start,chunk_end in tqdm(zip(range(0,number_of_cands,args.chunk_every_k),range(args.chunk_every_k,number_of_cands+args.chunk_every_k,args.chunk_every_k))):
    candidate_encoding = encode_candidate(
        biencoder,
        candidate_pool[chunk_start:chunk_end],
        biencoder_params["encode_batch_size"],
        biencoder_params["silent"],
        logger,
    )

    # concatenate the chunks together
    if cand_encoding_all is None:
        cand_encoding_all = candidate_encoding
    else:   
        cand_encoding_all = torch.cat((cand_encoding_all, candidate_encoding))

    print(cand_encoding_all.shape)    

# save the encoding
save_file = None
if getattr(args, 'encoding_save_file_dir', None) is not None:
    save_file = os.path.join(
        args.encoding_save_file_dir,
        "ent_encodings.t7",
    )
print("Saving in: {}".format(save_file))
if save_file is not None:
    f = open(save_file, "w").close()  # mark as existing
    print("Saving in: {}".format(save_file))
    torch.save(cand_encoding_all, save_file)

# check whether same as the baseline encoding
print(cand_encoding_all[0,:10])
if baseline_candidate_encoding is not None:
    print(baseline_candidate_encoding[0,:10])