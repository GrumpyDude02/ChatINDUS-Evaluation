from nl2sql360.arguments import CoreArguments, EvaluationArguments
from nl2sql360.core import Core
import sqlite3, os, json,tempfile
from premsql.agents.baseline.workers import BaseLineText2SQLWorker
from premsql.evaluator import Text2SQLEvaluator
from premsql.executors import SQLiteExecutor
from premsql.generators import Text2SQLGeneratorHF

from . import Dataset
from . import utils


class Evaluator:
    def __init__(self, dataset: Dataset, experiment_path, executor=None, generator=None):
        self.dataset = dataset
        self.experiment_path = experiment_path
        self.core = Core(CoreArguments())

        abs_path = os.path.abspath("nl2sql360/nl2sql360.sqlite")
        sqlite3.connect(abs_path)

        utils.check_and_handle_dataset(self.core,self.dataset.dataset_name)
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

    def evaluate_premsql(self, responses: dict,filter_by: str ="db_id") -> dict:
        return self.premsql_evaluator.execute(
            metric_name="accuracy",
            model_responses=responses,
            filter_by=filter_by,
            meta_time_out=10,
        )

    def evaluate_nl2sql360(self, evaluation_name, responses, filter_by):
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
        con = sqlite3.connect("nl2sql360/nl2sql360.sqlite")
        cursor = con.cursor()
        cursor.execute()


    def run_full_evaluation(self, eval_name):
        print("\nGenerating SQL responses...\n")
        responses = self.generate_response()

        print("\nEvaluating with PremSQL...\n")
        premsql_results = self.evaluate_premsql(responses)

        print("\nEvaluating with NL2SQL360...\n")
        self.evaluate_nl2sql360(eval_name, responses)

        print("Computing average NL2SQL360 metrics...\n")
        column_means = utils.calculate_avg(eval_name, self.dataset.args.dataset_name)

        return {
            "premsql_results": premsql_results,
            "nl2sql360_averages": column_means
        }
    
