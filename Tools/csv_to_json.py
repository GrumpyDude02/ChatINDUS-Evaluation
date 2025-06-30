import pandas as pd, json, argparse




def csv_to_json(file_path, output_file):
    dict_list = []
    data = pd.read_csv(file_path)
    for _,row in data.iterrows():
        d = {}
        for key, val in row.items():
            d[f"{key}"]=val
        dict_list.append(d)
    
    with open(output_file,"w",encoding="utf-8") as f:
        json.dump(dict_list,f,indent=4,ensure_ascii=False)


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('file_path')
    parser.add_argument('output_file')
    args = parser.parse_args()
    csv_to_json(args.file_path,args.output_file)