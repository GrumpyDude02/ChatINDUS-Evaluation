import pandas as pd
import sqlglot
from Tools.my_parse import *

features = {
    "tables": extract_tables,
    "columns": extract_select_columns,
    "where_predicates": where_predicates,
    "agg_func": extract_aggregates,
    "functions": extract_functions,
}

data = pd.read_csv("./generated_sql_queries.csv")

results = data.copy()

for i in range(len(data)):
    try:
        parsed_gold = sqlglot.parse_one(data.loc[i, "gold"])
        parsed_pred = sqlglot.parse_one(data.loc[i, "pred"])

        for feature, feature_func in features.items():
            gold_feat = set(feature_func(parsed_gold))
            pred_feat = set(feature_func(parsed_pred))
            results.loc[i, feature] = jaccard_similarity(gold_feat, pred_feat)
    except Exception:
        for feature in features:
            results.loc[i, feature] = -1

results.to_excel("output_with_features.xlsx", index=False)