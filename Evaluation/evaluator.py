from nl2sql360.arguments import CoreArguments, EvaluationArguments
from nl2sql360.core import Core
import sqlite3, os, json,tempfile
from premsql.agents.baseline.workers import BaseLineText2SQLWorker
from premsql.evaluator import Text2SQLEvaluator
from premsql.executors import SQLiteExecutor
from premsql.generators import Text2SQLGeneratorHF
from . import Dataset
from . import utils
import pandas as pd

class ExistingEvaluationError(Exception):
    default_message = "An existing evaluation under the same name has been found"
    def __init__(self, message=None, *args):
        final_message = message or ExistingEvaluationError.default_message
        super().__init__(final_message, *args)


class Evaluation:

    def __init__(self, dataset: Dataset, experiment_path, evaluation_name, executor=None, generator=-1 ):
        self.dataset = dataset
        self.experiment_path = experiment_path
        self.core = Core(CoreArguments())
        existing_datasets = self.core.query_available_datasets()
        if dataset.dataset_name in existing_datasets["Dataset"]:
            existing_evaluations = self.core.query_available_evaluations(self.dataset.dataset_name)
            print("An existing dataset with the same name has been found")
            if evaluation_name in existing_evaluations:
                raise Exception("An existing evaluation under the same dataset has been found. Clear the dataset evaluation history and try again.")
        
        self.core.import_dataset(self.dataset.args)

        self.executor = executor or SQLiteExecutor()
        if generator!=-1:
            self.generator = generator or self._init_default_generator()
        self.premsql_evaluator = Text2SQLEvaluator(self.executor, experiment_path)

    def _init_default_generator(self):
        return Text2SQLGeneratorHF(
            model_or_name_or_path="premai-io/prem-1B-SQL",
            experiment_name="text2sql_worker",
            type="test",
        )

    def _load_data(self):
        samples_path = os.path.join(self.dataset.dataset_dir, self.dataset.samples_file)
        with open(samples_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _build_worker(self, db_id):
        database_full_path = os.path.join(
            self.dataset.database_dir, db_id, f"{db_id}.sqlite"
        )
        uri = f"sqlite:///{database_full_path}"
        worker = BaseLineText2SQLWorker(
            db_connection_uri=uri,
            generator=self.generator,
            executor=self.executor,
        )
        return worker, database_full_path

    def generate_response(self):
        data = self._load_data()
        responses = []

        current_db_id = None
        worker = None
        db_path = None

        for entry in data:

            db_id = entry[self.dataset.keys["db_id_key"]]

            if db_id != current_db_id:
                worker, db_path = self._build_worker(db_id)
                current_db_id = db_id
            try:
                generated_response = worker.run(question=entry["prompt"], temperature=0.1)
                generated_query = (
                    generated_response.sql_string if generated_response else ""
                )
            except Exception as e:
                generated_query = ""
                print(f"Excepetion Occured:{e}")
            responses.append(
                {
                    "db_path": db_path,
                    "db_id": db_id,
                    "question": entry[self.dataset.keys["question_key"]],
                    "SQL": entry[self.dataset.keys["sql_key"]],
                    "generated": generated_query,
                    "difficulty": entry.get(self.dataset.keys["sql_complexity_key"]),
                }
            )

        return responses

    def evaluate_premsql(self, responses: dict,filter_by: str ="db_id") -> dict:
        return self.premsql_evaluator.execute(
            metric_name="accuracy",
            model_responses=responses,
            filter_by=filter_by,
            meta_time_out=10,
        )

    def evaluate_nl2sql360(self, evaluation_name, responses=None):
        if responses is not None:
            with tempfile.NamedTemporaryFile("w+", encoding="utf-8", delete=False, suffix=".txt") as temp:
                for entry in responses:
                    temp.write(entry["generated"] + "\n")
                temp_path = temp.name

            eval_args = EvaluationArguments(
                eval_name=evaluation_name,
                eval_dataset=self.dataset.args.dataset_name,
                eval_metrics=["ex", "ves", "rves", "f1"],
                pred_sqls_file=temp_path,
            )
            self.core.evaluate(eval_args)
             
        try:
            con = sqlite3.connect("nl2sql360/nl2sql360.sqlite")
        except sqlite3.OperationalError as e:
            print("Connection failed: Unable to open the database file.")
            print("Please check if the file exists at 'nl2sql360/nl2sql360.sqlite' and that you have the necessary permissions.")
            print("Error details:", e)
        
        dataset_table_name = f"DATASET_{self.dataset.dataset_name}"
        eval_table = f"{dataset_table_name}_EVALUATION_{evaluation_name}"

        query = f"""WITH CombinedData AS (
                            SELECT T1.*, T2.*
                            FROM {dataset_table_name} AS T1
                            INNER JOIN {eval_table} AS T2
                            ON T1.id = T2.id
                        )
                        SELECT * 
                        FROM CombinedData;"""
        

        df = pd.read_sql_query(query, con)
        return df[["id","nlq","gold","pred","db_id","complexity","exec_acc","exact_acc","ves","rves","f1"]]

    def _filter_results(self,df: pd.DataFrame, key: str) -> pd.DataFrame:
        """
        Calculates the average of specified evaluation metrics, grouped by a given key column.

        Args:
            df (pd.DataFrame): The input DataFrame containing evaluation results.
            key (str): The name of the column to group by (e.g., 'difficulty').

        Returns:
            pd.DataFrame: A DataFrame where the index represents unique values of 'key'
                        and columns represent the average of each evaluation metric.
        """
        evaluation_metrics = ["exec_acc", "ves", "rves", "f1"]

        # Ensure the key column exists
        if key not in df.columns:
            raise ValueError(f"Key column '{key}' not found in the DataFrame.")
        
        # Ensure all evaluation metrics exist and are numeric
        for metric in evaluation_metrics:
            if metric not in df.columns:
                print(f"Warning: Evaluation metric '{metric}' not found in DataFrame. Skipping.")
            # Optional: Convert to numeric if not already, coercing errors to NaN
            # df[metric] = pd.to_numeric(df[metric], errors='coerce')

        # Filter to only include the relevant columns
        cols_to_average = [col for col in evaluation_metrics if col in df.columns]
        if not cols_to_average:
            raise ValueError("No valid evaluation metrics found in the DataFrame.")

        # Group by the key and calculate the mean for the specified metrics
        # .mean(numeric_only=True) can be added if you select the whole df,
        # but here we're explicitly selecting numeric columns.
        filtered_results = df.groupby(key)[cols_to_average].mean()

        return filtered_results


    def run_full_evaluation(self, eval_name, filter_by):
        """
        Performs a full evaluation by calculating average metrics based on a specified filter.

        Args:
            eval_name (str): A name for this evaluation run (e.g., 'model_v1_test_run').
                             Used for naming output files.
            filter_by (str): The column by which to group and calculate averages.
                             Possible values: "id", "nlq", "gold", "pred", "db_id", "complexity".
                             - "id": Unique identifier for each test case.
                                     (Averaging by 'id' would result in individual row values,
                                      as 'id' is unique, so this typically means no grouping).
                             - "nlq": Natural Language Query. Group by the input question.
                             - "gold": Gold Standard SQL Query. Group by the true correct SQL.
                             - "pred": Predicted SQL Query. Group by the model's generated SQL.
                             - "db_id": Database ID. Group by the database schema (e.g., 'sakila').
                             - "complexity": Difficulty/Complexity level (e.g., 'easy', 'medium', 'hard').
        
        Returns:
            pd.DataFrame: A DataFrame containing the calculated averages.
        """
        print("\nGenerating SQL responses...\n")
        responses = self.generate_response()

        #print("\nEvaluating with PremSQL...\n")
        # premsql_results = self.evaluate_premsql(responses)

        print("\nEvaluating with NL2SQL360...\n")
        result = self.evaluate_nl2sql360(eval_name, responses)

        print("Computing average NL2SQL360 metrics...\n")

        return self._filter_results(result,filter_by)
    
