import os,json
from premsql.datasets import StandardDataset
from MyTools.custom_generator import MyText2SQLGeneratorHF
from premsql.agents.baseline.workers import BaseLineText2SQLWorker
from premsql.evaluator import Text2SQLEvaluator
from premsql.executors import SQLiteExecutor

database_path = "./databases"
dataset_path = "./datasets"
validation_dataset = StandardDataset(
    split="validation",    # it can be either train / validation / test depending on your dataset and the name of the json file
    dataset_path=dataset_path,
    database_folder_name=database_path, # The same name of the folder
    json_file_name="dev.json",
)

text2sql_generator = MyText2SQLGeneratorHF(
    model_or_name_or_path="premai-io/prem-1B-SQL",
    experiment_name="text2sql_worker",
    type="test"
)
with open("datasets/dev.json","r",encoding='utf-8') as f:
    data = json.load(f)

responses = []
db_id = None
worker = None

for e in data:
    if e["db_id"] != db_id:
        db_id = e["db_id"]
        uri = "sqlite:///{abs_path}".format(abs_path =os.path.abspath(f"databases/{db_id}/{db_id}.sqlite") ) 
        worker = BaseLineText2SQLWorker(db_connection_uri=uri,generator=text2sql_generator,executor=SQLiteExecutor())
    print(e['prompt'])
    generated_response = worker.run(question = e["prompt"],temperature=0.1)
    query = generated_response["sql_string"] if generated_response else ""
    responses.append({"db_path":database_path,"db_id":db_id,"prompt":e["prompt"],"SQL":query,"difficulty":e["difficulty"]}) 

evaluator = Text2SQLEvaluator(
    executor=text2sql_generator,
    experiment_path=text2sql_generator.experiment_path
)



results = evaluator.execute(
    metric_name="accuracy",
    model_responses=responses,
    filter_by="db_id",
    meta_time_out=10
)

