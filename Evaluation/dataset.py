import os
from nl2sql360.arguments import DatasetArguments
from premsql.datasets import StandardDataset

class Dataset:
    DEFAULT_KEYS = {
        "sql_key":"query",
        "question_key":"question",
        "prompt":"prompt",
        "db_id_key":"db_id",
        "sql_complexity_key":"difficulty"
    }
    def __init__(self, dataset_name, dataset_dir, samples_file, database_dir,keys: dict=DEFAULT_KEYS):
        self.keys = keys
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
            sql_key=self.keys["sql_key"],
            question_key=self.keys["question_key"],
            db_id_key=self.keys["db_id_key"],
            sql_complexity_key=self.keys["sql_complexity_key"],
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

