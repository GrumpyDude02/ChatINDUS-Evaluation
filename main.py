from Evaluation import Dataset, Evaluator

if __name__ == "__main__":
    dataset = Dataset(
        dataset_name="my_dataset",
        dataset_dir="datasets",
        samples_file="dev.json",
        database_dir="databases"
    )


    evaluator = Evaluator(dataset, experiment_path="MyTools")
    results = evaluator.evaluate_nl2sql360(evaluation_name="eval_003")

    print(evaluator._filter_results(results,"complexity"))