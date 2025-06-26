from eralchemy import render_er
import os,argparse

parser = argparse.ArgumentParser(description='Optional app description')
parser.add_argument('database_path', type=str, help='SQLite database file')
parser.add_argument('output_file',type=str,help='Output file')

args = parser.parse_args()

os.environ["PATH"] += os.pathsep + r"C:\Program Files\Graphviz\bin"

# Draw from database
database_path = os.path.abspath(args.database_path)
render_er(f"sqlite:///{database_path}", args.output_file)