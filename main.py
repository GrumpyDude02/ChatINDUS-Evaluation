from Evaluation import Dataset, Evaluator

if __name__ == "__main__":
    dataset = Dataset(
        dataset_name="my_dataset",
        dataset_dir="datasets",
        samples_file="dev.json",
        database_dir="databases"
    )

    evaluator = Evaluator(dataset, experiment_path="MyTools")
    results = evaluator.run_full_evaluation(eval_name="eval_001")

    print(results)