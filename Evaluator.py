from nl2sql360.arguments import CoreArguments, EvaluationArguments, DatasetArguments
from nl2sql360.core import Core
from premsql.datasets import StandardDataset
import sqlite3, os, json, pandas as pd,tempfile
from premsql.agents.baseline.workers import BaseLineText2SQLWorker
from premsql.evaluator import Text2SQLEvaluator
from premsql.executors import SQLiteExecutor
from premsql.generators import Text2SQLGeneratorHF



class Dataset:
    def __init__(self, dataset_name, dataset_dir, samples_file, database_dir):
        self.dataset_name = dataset_name
        self.dataset_dir = os.path.abspath(dataset_dir)
        self.samples_file = samples_file
        self.database_dir = os.path.abspath(database_dir)

        self._validate_paths()

        self.args = self._build_dataset_args()
        self._premsql_dataset = None

    def _validate_paths(self):
        if not os.path.exists(self.dataset_dir):
            raise FileNotFoundError(f"Dataset directory not found: {self.dataset_dir}")
        if not os.path.exists(os.path.join(self.dataset_dir, self.samples_file)):
            raise FileNotFoundError(f"Samples file not found: {self.samples_file}")
        if not os.path.exists(self.database_dir):
            raise FileNotFoundError(f"Database directory not found: {self.database_dir}")

    def _build_dataset_args(self):
        return DatasetArguments(
            dataset_name=self.dataset_name,
            dataset_dir=self.dataset_dir,
            database_dir=self.database_dir,
            samples_file=self.samples_file,
            sql_key="query",
            question_key="prompt",
            db_id_key="db_id",
            sql_complexity_key="difficulty",
        )

    @property
    def premsql_dataset(self):
        if self._premsql_dataset is None:
            self._premsql_dataset = StandardDataset(
                split="validation",
                database_folder_name=self.database_dir,
                json_file_name=self.samples_file,
                dataset_path=self.dataset_dir,
            )
        return self._premsql_dataset


class Evaluator:
    def __init__(self, dataset: Dataset, experiment_path, executor=None, generator=None):
        self.dataset = dataset
        self.experiment_path = experiment_path
        self.core = Core(CoreArguments())

        abs_path = os.path.abspath("nl2sql360/nl2sql360.sqlite")
        sqlite3.connect(abs_path)

        Evaluator.check_and_handle_dataset(self.core,self.dataset.dataset_name)
        self.core.import_dataset(self.dataset.args)

        self.executor = executor or SQLiteExecutor()
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
            db_id = entry["db_id"]

            if db_id != current_db_id:
                worker, db_path = self._build_worker(db_id)
                current_db_id = db_id

            generated_response = worker.run(question=entry["prompt"], temperature=0.1)
            generated_query = (
                generated_response.sql_string if generated_response else ""
            )

            responses.append(
                {
                    "db_path": db_path,
                    "db_id": db_id,
                    "prompt": entry["prompt"],
                    "SQL": entry["query"],
                    "generated": generated_query,
                    "difficulty": entry.get("difficulty"),
                }
            )

        return responses

    def evaluate_premsql(self, responses: dict) -> dict:
        return self.premsql_evaluator.execute(
            metric_name="accuracy",
            model_responses=responses,
            filter_by="db_id",
            meta_time_out=10,
        )

    def evaluate_nl2sql360(self, evaluation_name, responses):
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

    @staticmethod
    def calculate_avg(eval_name, dataset_name):
        abs_path = os.path.abspath("nl2sql360/nl2sql360.sqlite")
        con = sqlite3.connect(abs_path)
        dataset_table_name = f"DATASET_{dataset_name}"
        cursor = con.cursor()
        
        try:
            db_ids = cursor.execute(f"SELECT DISTINCT db_id FROM {dataset_table_name}").fetchall()
            cursor.close()
            
            table_name = f"DATASET_{dataset_name}_EVALUATION_{eval_name}"
            all_means = {}

            for (db_id,) in db_ids:  # unpack tuple
                query = f"""
                    SELECT T1.* 
                    FROM {table_name} AS T1
                    INNER JOIN {dataset_table_name} AS T2 
                    ON T1.id = T2.id 
                    WHERE T2.db_id = ?;
                """
                data = pd.read_sql_query(query, con, params=(db_id,))

                numeric_data = data.select_dtypes(include="number")
                column_means = numeric_data.mean()
                all_means[db_id] = column_means

                print(f"\n=== AVERAGE METRICS FOR DB: {db_id} ===")
                for col, val in column_means.items():
                    print(f"{col}: {val:.4f}")

            return all_means

        except Exception as e:
            print("Error in the name of the dataset or evaluation:", e)
            return {}
        finally:
            con.close()

    def check_and_handle_dataset(core : Core, dataset_name: str, db_path="nl2sql360/nl2sql360.sqlite"):
        table_name = f"DATASET_{dataset_name}"
        abs_path = os.path.abspath(db_path)
        con = sqlite3.connect(abs_path)
        cur = con.cursor()

        try:
            # Check if table exists
            cur.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name=?;
            """, (table_name,))
            exists = cur.fetchone()

            if exists:
                print("An existing dataset with the same name was found.")
                core.delete_dataset_history(
                    dataset_name=dataset_name,
                    delete_relavant_evaluations=True
                )

        finally:
            con.close()


    def run_full_evaluation(self, eval_name):
        print("\nGenerating SQL responses...\n")
        responses = self.generate_response()

        print("\nEvaluating with PremSQL...\n")
        premsql_results = self.evaluate_premsql(responses)

        print("\nEvaluating with NL2SQL360...\n")
        self.evaluate_nl2sql360(eval_name, responses)

        print("Computing average NL2SQL360 metrics...\n")
        column_means = self.calculate_avg(eval_name, self.dataset.args.dataset_name)

        return {
            "premsql_results": premsql_results,
            "nl2sql360_averages": column_means
        }