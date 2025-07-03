from eralchemy import render_er
import os,argparse

if __name__=="__main__":
    parser = argparse.ArgumentParser(description='Optional app description')
    parser.add_argument('database_path', type=str, help='SQLite database file')
    parser.add_argument('output_file',type=str,help='Output file')

    args = parser.parse_args()

    # Draw from database
    database_path = os.path.abspath(args.database_path)
    render_er(f"sqlite:///{database_path}", args.output_file)