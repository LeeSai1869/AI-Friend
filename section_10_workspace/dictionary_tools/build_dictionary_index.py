import argparse
import json
import sqlite3

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True, help='Path to the source JSON file')
    parser.add_argument('--output', required=True, help='Path to the output SQLite file')
    
    args = parser.parse_args()
    
    # Read the source JSON
    with open(args.source, 'r') as f:
        data = json.load(f)
    
    # Create SQLite database and table
    conn = sqlite3.connect(args.output)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS records (
            word TEXT,
            part_of_speech TEXT,
            definition TEXT
        )
    ''')
    
    # Process the data and insert rows
    count = 0
    for word, records in data.items():
        for record in records:
            for meaning in record.get('meanings', []):
                part_of_speech = meaning.get('partOfSpeech', '')
                for definition_obj in meaning.get('definitions', []):
                    definition = definition_obj.get('definition', '')
                    cursor.execute(
                        'INSERT INTO records (word, part_of_speech, definition) VALUES (?, ?, ?)',
                        (word, part_of_speech, definition)
                    )
                    count += 1
    
    conn.commit()
    conn.close()
    
    print(count)

if __name__ == '__main__':
    main()
