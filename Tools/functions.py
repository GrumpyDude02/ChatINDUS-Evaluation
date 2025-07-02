import sqlite3,json

def get_schema_sql_only(database_path):
    con = sqlite3.connect(database_path)
    cursor = con.cursor()
    
    # Récupère tous les objets créés dans la base
    cursor.execute("SELECT type, name, sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY type, name;")
    entries = cursor.fetchall()
    con.close()

    return "\n\n".join(
        f"-- {row[0]}: {row[1]}\n{row[2]};"
        for row in entries
    )

def save_valid_results(database_path:str,result_list:dict,file_path:str):
    con = sqlite3.connect(database_path)
    cursor = con.cursor()

    valid_results = []
    for pair in result_list:
        query = pair["query"].strip()
        
        if not query.lower().startswith(("select", "with")):
            continue
        
        try:
            cursor.execute(query)
            valid_results.append(pair)
        except Exception as e:
            print(f"Query failed:\n{query}\nError: {e}\n")

    # Sauvegarde des requêtes valides
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(valid_results, f, ensure_ascii=False, indent=2)

    con.close()
    print(f"Saved {len(valid_results)} valid queries to file")