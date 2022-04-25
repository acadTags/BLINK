# get all UMLS 2012 AB entities as subset of SNOMEDCT and in the disease semantic group (according to Ji, 2020, AMIA)
'''
output format: each line is 
{"text": " Autism is a developmental disorder characterized by difficulties with social interaction and communication, and by restricted and repetitive behavior. Parents usually notice signs during the first three years of their child's life. These signs often develop gradually, though some children with autism reach their developmental milestones at a normal pace before worsening. Autism is associated with a combination of genetic and environmental factors. Risk factors during pregnancy include certain infections, such as rubella, toxins including valproic acid, alcohol, cocaine, pesticides and air pollution, fetal growth restriction, and autoimmune diseases. Controversies surround other proposed environmental causes; for example, the vaccine hypothesis, which has been disproven. Autism affects information processing in the brain by altering connections and organization of nerve cells and their synapses. How this occurs is not well understood. In the DSM-5, autism and less severe forms of the condition, including Asperger syndrome and pervasive developmental disorder not otherwise specified (PDD-NOS), have been combined into the diagnosis of autism spectrum disorder (ASD). Early behavioral interventions or speech therapy can help children with autism gain self-care, social, and communication skills. Although there is no known cure, there have been cases of children who recovered. Not many children with autism live independently after reaching adulthood, though some are successful. An autistic culture has developed, with some individuals seeking a cure and others believing autism should be accepted as a difference and not treated as a disorder. Globally, autism is estimated to affect 24.8 million people . In the 2000s, the number of people affected was estimated at", "idx": "https://en.wikipedia.org/wiki?curid=25", "title": "Autism", "entity": "Autism"}
'''

from tqdm import tqdm
import json

#output str content to a file
#input: filename and the content (str)
def output_to_file(file_name,str):
    with open(file_name, 'w', encoding="utf-8-sig") as f_output:
        f_output.write(str)

UMLS_file_path1 = '../ontologies/MRCONSO.RRF.aa'
UMLS_file_path2 = '../ontologies/MRCONSO.RRF.ab'
#about MRCONSO, see https://www.ncbi.nlm.nih.gov/books/NBK9685/table/ch03.T.concept_names_and_sources_file_mr/
STY_file_path = '../ontologies/MRSTY.RRF'
DEF_file_path = '../ontologies/MRDEF.RRF'

disease_sem_gp_filter_list = ['Congenital Abnormality',
                              'Acquired Abnormality',
                              'Injury or Poisoning',
                              'Pathologic Function',
                              'Disease or Syndrome',
                              'Mental or Behavioral Dysfunction',
                              'Cell or Molecular Dysfunction',
                              'Experimental Model of Disease',
                              'Anatomical Abnormality',
                              'Neoplastic Process',
                              'Sign or Symptom']

dict_CUI_by_STY = {}
dict_CUI_SNOMEDCT = {}
dict_CUI_DEF = {}
dict_CUI_default_name = {}

with open(STY_file_path,encoding='utf-8') as f_content:
    doc_STY = f_content.readlines()

with open(DEF_file_path,encoding='utf-8') as f_content:
    doc_DEF = f_content.readlines()

# get dict of CUI filtered by STY
for line in tqdm(doc_STY):
    for STY in disease_sem_gp_filter_list:
        if '|%s|' % STY in line:
            CUI = line[:line.find('|')]
            dict_CUI_by_STY[CUI] = 1
            break

# get dict of CUI to DEF
for line in tqdm(doc_DEF):
    def_eles = line.split('|')
    CUI = def_eles[0]
    DEF = def_eles[5]
    #print(CUI,DEF)
    dict_CUI_DEF[CUI] = DEF

entity_json_str = ''
n_all_sel_UMLS_w_def = 0
n_all_sel_UMLS = 0å
for UMLS_file_path in [UMLS_file_path1,UMLS_file_path2]:
    with open(UMLS_file_path,encoding='utf-8') as f_content:
        doc = f_content.readlines()

    for line in tqdm(doc):
        data_eles = line.split('|')
        if len(data_eles) > 11:
            source = data_eles[11]
        else:
            source = ''    

        CUI = data_eles[0]
        lang = data_eles[1]
        if (not CUI in dict_CUI_default_name) and (lang == 'ENG'):
            default_name = data_eles[14]
            dict_CUI_default_name[CUI] = default_name
        if source == 'SNOMEDCT':
            if CUI in dict_CUI_by_STY:
                #using the the first one in English as the default name 
                ##only record the first one in the MRRCONSO for the same concept
                if CUI in dict_CUI_SNOMEDCT:
                    continue
                dict_CUI_SNOMEDCT[CUI] = 1
                n_all_sel_UMLS += 1
                title = data_eles[14]      
                #get definition of CUI and the statistics 
                if CUI in dict_CUI_DEF:
                    n_all_sel_UMLS_w_def += 1
                    CUI_def = dict_CUI_DEF[CUI]
                else:
                    CUI_def = ''    
                default_name = dict_CUI_default_name[CUI]
                #print(CUI_def,CUI,title)
                dict_entity_row = {}
                dict_entity_row['text'] = CUI_def
                dict_entity_row['idx'] = CUI
                dict_entity_row['title'] = default_name
                #dict_entity_row['title'] = title
                dict_entity_row['entity'] = default_name
                if entity_json_str == '':
                    entity_json_str = json.dumps(dict_entity_row)
                else:    
                    entity_json_str = entity_json_str + '\n' + json.dumps(dict_entity_row)

#add NIL entity
dict_entity_row = {}
dict_entity_row['text'] = ''
dict_entity_row['idx'] = 'CUI-less'
dict_entity_row['title'] = 'NIL'
dict_entity_row['entity'] = 'NIL'
entity_json_str = entity_json_str + '\n' + json.dumps(dict_entity_row)

output_to_file('UMLS2012AB.jsonl',entity_json_str)
print(len(dict_CUI_SNOMEDCT))  # 88151 = 88150 + 1 (the NIL entity)
print('percentage of sel UMLS with def:',float(n_all_sel_UMLS_w_def)/n_all_sel_UMLS,n_all_sel_UMLS_w_def,n_all_sel_UMLS)
#percentage of sel UMLS with def: 0.07888825865002837 6954 88150