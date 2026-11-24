import argparse
import json
import sqlite3

BATCH_SIZE = 5000


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True, help='Path to the source JSON file')
    parser.add_argument('--output', required=True, help='Path to the output SQLite file')
    args = parser.parse_args()

    with open(args.source, 'r', encoding='utf-8') as f:
        data = json.load(f)

    conn = sqlite3.connect(args.output)
    cursor = conn.cursor()
    cursor.execute('DROP TABLE IF EXISTS records')
    cursor.execute(
        'CREATE TABLE records (word TEXT, part_of_speech TEXT, definition TEXT)'
    )

    sql = 'INSERT INTO records (word, part_of_speech, definition) VALUES (?, ?, ?)'
    batch = []
    count = 0
    for word, records in data.items():
        for record in records:
            for meaning in record.get('meanings', []):
                part_of_speech = meaning.get('partOfSpeech', '')
                for definition_obj in meaning.get('definitions', []):
                    batch.append((word, part_of_speech, definition_obj.get('definition', '')))
                    if len(batch) >= BATCH_SIZE:
                        cursor.executemany(sql, batch)
                        count += len(batch)
                        batch = []
    if batch:
        cursor.executemany(sql, batch)
        count += len(batch)

    conn.commit()
    conn.close()
    print(count)


if __name__ == '__main__':
    main()
