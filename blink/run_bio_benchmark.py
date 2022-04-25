# Copyright (c) Facebook, Inc. and its affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
#
import argparse
import prettytable

import blink.main_dense as main_dense
import blink.candidate_ranking.utils as utils

DATASETS = [
    {
        "name": "Share-CLEF_eHealth2013-train-sampled",
        "filename": "preprocessing/share_clef_2013_train_sampled.json", 
    },
    {
        "name": "Share-CLEF_eHealth2013-test-preprocessed",
        "filename": "preprocessing/share_clef_2013_test_sampled.json", 
    },
    # {
    #     "name": "Share-CLEF_eHealth2013-train-preprocessed",
    #     "filename": "preprocessing/share_clef_2013_train_preprocessed.json", 
    # },
    # {
    #     "name": "Share-CLEF_eHealth2013-test-preprocessed",
    #     "filename": "preprocessing/share_clef_2013_test_preprocessed.json", 
    # },
    # {
    #     "name": "Share-CLEF_eHealth2013-train",
    #     "filename": "preprocessing/share_clef_2013_train.json", 
    # },
    # {
    #     "name": "Share-CLEF_eHealth2013-test",
    #     "filename": "preprocessing/share_clef_2013_test.json", 
    # },
]

#the key parameters here
PARAMETERS = {
    "faiss_index": None,
    "index_path": None,
    "test_entities": None,
    "test_mentions": None,
    "interactive": False,
    "biencoder_model": "models/biencoder_wiki_large.bin",
    "biencoder_config": "models/biencoder_wiki_large.json",
    "entity_catalogue": "preprocessing/UMLS2012AB_with_NIL.jsonl", # a four-element entity data structure: text (or definition), idx (or url), title (or name of the entity), entity (canonical name)
    #UMLS2012AB_with_NIL.jsonl (with NIL or CUI-less as an entity added) or UMLS2012AB.jsonl (original list of entities)
    # file2 to create    
    "entity_encoding": "models/UMLS2012AB_ent_enc/UMLS2012AB_ent_enc.t7", # a torch7 file # how to get this?
    # file3 to create
    "crossencoder_model": "models/crossencoder_wiki_large.bin",
    "crossencoder_config": "models/crossencoder_wiki_large.json",
    "output_path": "output",
    "fast": False,
    "top_k": 100,
}
args = argparse.Namespace(**PARAMETERS)

logger = utils.get_logger(args.output_path)

models = main_dense.load_models(args, logger) # load biencoder, crossencoder, and candidate entities

table = prettytable.PrettyTable(
    [
        "DATASET",
        "biencoder accuracy",
        "recall at 100",
        "biencoder accuracy for NIL",
        "recall at 100 for NIL",
        "crossencoder normalized accuracy",
        "overall unormalized accuracy",
        "support",
    ]
)

for dataset in DATASETS:
    logger.info(dataset["name"])
    PARAMETERS["test_mentions"] = dataset["filename"]
    #set the parameter test_mentions as the filename of the dataset

    args = argparse.Namespace(**PARAMETERS)
    
    (
        biencoder_accuracy,
        recall_at,
        biencoder_NIL_accuracy,
        recall_NIL_at,
        crossencoder_normalized_accuracy,
        overall_unormalized_accuracy,
        num_datapoints,
        predictions,
        scores,
    ) = main_dense.run(args, logger, *models) # here it starts inferencing

    table.add_row(
        [
            dataset["name"],
            round(biencoder_accuracy, 4),
            round(recall_at, 4),
            round(biencoder_NIL_accuracy, 4),
            round(recall_NIL_at, 4),
            round(crossencoder_normalized_accuracy, 4),
            round(overall_unormalized_accuracy, 4),
            num_datapoints,
        ]
    )
    # to look at these later
    #print('predictions:',predictions)
    #print('scores:',scores)
logger.info("\n{}".format(table))
