import pandas as pd
import sqlglot
from my_parse import *

def jaccard_similarity(set1, set2):
    if not set1 and not set2:
        return 1.0  # deux ensembles vides sont considérés identiques
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union if union != 0 else 0

# dictionnaire des extracteurs de caractéristiques
features = {
    "tables": extract_tables,
    "columns": extract_select_columns,
    "where_predicates": where_predicates,
    "agg_func": extract_aggregates
}

# Chargement des fichiers (attention : il faut des fichiers différents si possible)
gold = pd.read_csv("datasets/adventure_works_prompts.csv")
pred = pd.read_csv("datasets/adventure_works_prompts.csv")

# Initialisation de la structure de résultat
results = []

for gold_q, pred_q in zip(gold["sql"], pred["sql"]):
    parsed_gold = sqlglot.parse_one(gold_q)
    parsed_pred = sqlglot.parse_one(pred_q)
    
    row_result = {}
    for feature, feature_func in features.items():
        gold_feat = set(feature_func(parsed_gold))
        pred_feat = set(feature_func(parsed_pred))
        row_result[feature] = jaccard_similarity(gold_feat, pred_feat)
    
    results.append(row_result)

# Conversion en DataFrame
results_df = pd.DataFrame(results)
print(results_df)
