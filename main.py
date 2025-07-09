from Evaluator import Dataset, Evaluation
import json
from MyTools.custom_generator import MyText2SQLGeneratorHF

if __name__ == "__main__":
    dataset = Dataset(
        dataset_name="my_dataset2",
        dataset_dir="datasets",
        samples_file="generated.json",
        database_dir="databases",
    )

    evalation = Evaluation(dataset, "path/to/experiment/folder","test_008",generator=MyText2SQLGeneratorHF(""))
    result = evalation.run_full_evaluation()
    print(evalation._filter_results(result["NL2SQL360"]))