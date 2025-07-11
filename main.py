from Evaluator import Evaluation, Dataset,exceptions
import json
from nl2sql360.core import Core
from nl2sql360.arguments import CoreArguments
from MyTools.custom_generator import MyText2SQLGeneratorHF

if __name__ == "__main__":
    core = Core(CoreArguments())
    dataset = Dataset(
            core = core,
            dataset_name="my_dataset2",
            dataset_dir="datasets",
            samples_file="dev.json",
            database_dir="databases",
        )
    dataset.setup_dataset()

    evaluation = Evaluation(
    dataset=dataset,
    experiment_path="path/to/experiment/folder",
    evaluation_name="test_008",
    core=core
)