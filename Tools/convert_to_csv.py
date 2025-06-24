import csv

def txt_to_csv(txt_path, csv_path):
    with open(txt_path, 'r', encoding='utf-8') as infile:
        lines = [line.rstrip('\n') for line in infile if line.strip() != '']  # skip empty lines

    entries = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('-'):
            prompt = line[1:].strip()
            sql = ''
            i += 1
            # Collect all following lines until next prompt or end of file
            while i < len(lines) and not lines[i].lstrip().startswith('-'):
                sql += lines[i].strip() + ' '
                i += 1
            entries.append((prompt, sql.strip()))
        else:
            i += 1  # just in case, skip if line doesn't start with '-'

    # Save to CSV
    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['prompt', 'sql'])
        writer.writerows(entries)

    print(f"✅ {len(entries)} prompts converted to {csv_path}")

if __name__=="__main__":
    txt_to_csv('./datasets/adventureworks_prompts.txt', 'output.csv')
