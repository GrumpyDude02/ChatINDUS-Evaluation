from nl2sql360.core import Core
from nl2sql360.arguments import CoreArguments, EvaluationArguments,DatasetArguments
import sqlite3, os, pandas as pd
from datetime import datetime


#assumption : json file keys for truth queries {"prompt":<Natural Language>,"query"<the true SQL query>:,"db_id":<id of the database>}

"""
0|id|INTEGER|1||1
1|pred|VARCHAR|1||0
2|exec_acc|FLOAT|0||0
3|exact_acc|FLOAT|0||0
4|ves|FLOAT|0||0
5|rves|FLOAT|0||0
6|f1|FLOAT|0||0
"""

core_args = CoreArguments()
core = Core(core_args)


def clear_cache():    
    core.delete_evaluation_history(
        dataset_name="my_data",
        eval_name="test1"
    )
    
    core.delete_dataset_history(
        dataset_name="my_data",
        delete_relavant_evaluations=True
    )

def import_data(dataset_name,dataset_dir,database_dir,sample_files):
    dataset_args = DatasetArguments(
        dataset_name=dataset_name,
        dataset_dir=dataset_dir,
        samples_file=sample_files,
        database_dir=os.path.abspath(database_dir),
        question_key="prompt",
        sql_key="query",
        db_id_key="db_id",
        sql_complexity_key=None,
        database_domain_file=None
    )

    core.import_dataset(dataset_args)

def clear_cached(dataset_name,eval_name):
    core.delete_evaluation_history(
        dataset_name=dataset_name,
        eval_name=eval_name
    )
    core.delete_dataset_history(
        dataset_name=dataset_name,
        delete_relavant_evaluations=True
    )


def evaluate(dataset_name, preds, test_name = None):
    if test_name is None:
        test_name = f"{test_name}-{datetime.now().strftime('%d%m%Y-%H-%M-%S')}"
    evaluation_args = EvaluationArguments(
        eval_name=test_name,
        eval_dataset=dataset_name,
        eval_metrics=["ex", "em", "ves"],
        pred_sqls_file=preds,
        enable_spider_eval=True
    )
    core.evaluate(evaluation_args)
    calculate_avg(test_name,dataset_name)
    


def calculate_avg(eval_name, dataset_name):
    abs_path = os.path.abspath("nl2sql360/nl2sql360.sqlite")
    con = sqlite3.connect(abs_path)
    try:
        table_name = f"DATASET_{dataset_name}_EVALUATION_{eval_name}"
        query = f"SELECT * FROM {table_name};"
        data = pd.read_sql_query(query, con)

        # Sélectionner uniquement les colonnes numériques
        numeric_data = data.select_dtypes(include='number')
        print(data)
        # Calcul des moyennes par colonne
        column_means = numeric_data.mean()

        print("execution accuracy mean:")
        print(column_means["exec_acc"])

    except Exception as e:
        print("Error in the name of the dataset or of the evaluation:", e)
    finally:
        con.close()

dataset_args = DatasetArguments(
    dataset_name="my_data",
    dataset_dir="datasets",
    samples_file="dev.json",
    database_dir=os.path.abspath("databases"),
    question_key="prompt",
    sql_key="query",
    db_id_key="db_id",
    sql_complexity_key=None,
    database_domain_file=None
)


evaluate("my_data","output.sql","test1")
