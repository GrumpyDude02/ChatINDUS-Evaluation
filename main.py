from Evaluator import Dataset, Evaluation
import json

if __name__ == "__main__":
    dataset = Dataset(
        dataset_name="my_dataset2",
        dataset_dir="datasets",
        samples_file="generated.json",
        database_dir="databases",
    )
    with open("generated.json", "r+", encoding="utf-8") as f:
        responses = json.load(f)

    evalation = Evaluation(dataset, "path/to/experiment/folder","test_008")
    result = evalation.run_full_evaluation(responses)
    print(evalation._filter_results(result["NL2SQL360"]))