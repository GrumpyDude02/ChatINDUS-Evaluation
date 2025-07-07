import sqlite3, os, pandas as pd
from nl2sql360.core import Core

def calculate_avg(eval_name, dataset_name):
        abs_path = os.path.abspath("nl2sql360/nl2sql360.sqlite")
        con = sqlite3.connect(abs_path)
        dataset_table_name = f"DATASET_{dataset_name}"
        cursor = con.cursor()
        
        try:
            db_ids = cursor.execute(f"SELECT DISTINCT db_id FROM {dataset_table_name}").fetchall()
            cursor.close()
            
            table_name = f"DATASET_{dataset_name}_EVALUATION_{eval_name}"
            all_means = {}

            for (db_id,) in db_ids:  # unpack tuple
                query = f"""
                    SELECT T1.* 
                    FROM {table_name} AS T1
                    INNER JOIN {dataset_table_name} AS T2 
                    ON T1.id = T2.id 
                    WHERE T2.db_id = ?;
                """
                data = pd.read_sql_query(query, con, params=(db_id,))

                numeric_data = data.select_dtypes(include="number")
                column_means = numeric_data.mean()
                all_means[db_id] = column_means

                print(f"\n=== AVERAGE METRICS FOR DB: {db_id} ===")
                for col, val in column_means.items():
                    print(f"{col}: {val:.4f}")

            return all_means

        except Exception as e:
            print("Error in the name of the dataset or evaluation:", e)
            return {}
        finally:
            con.close()

def check_and_handle_dataset(core : Core, dataset_name: str, db_path="nl2sql360/nl2sql360.sqlite"):
        table_name = f"DATASET_{dataset_name}"
        abs_path = os.path.abspath(db_path)
        con = sqlite3.connect(abs_path)
        cur = con.cursor()

        try:
            # Check if table exists
            cur.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name=?;
            """, (table_name,))
            exists = cur.fetchone()

            if exists:
                print("An existing dataset with the same name was found.")
                core.delete_dataset_history(
                    dataset_name=dataset_name,
                    delete_relavant_evaluations=True
                )

        finally:
            cur.close()
            con.close()
