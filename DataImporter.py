import csv
import glob
import os
import re
import mysql.connector

# Database connection settings — change as needed
DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = "2943"  # make sure to change this to your MySQL password
DB_NAME = "hockey_schema"

# Pattern to find CSV files in the data/ directory
CSV_PATTERN = os.path.join("data", "*.csv")


def none_if_blank(value):
    if value is None:
        return None
    s = str(value).strip()
    return s if s != "" else None


def sanitize_identifier(name):
    name = re.sub(r"[^0-9a-zA-Z_]", "_", name)
    # cannot start with digit in some DBs — prefix if necessary
    if re.match(r"^[0-9]", name):
        name = "c_" + name
    return name.lower()


def create_table_if_not_exists(cursor, table_name, columns):
    cols_sql = ", ".join(f"`{col}` TEXT" for col in columns)
    sql = f"CREATE TABLE IF NOT EXISTS `{table_name}` ({cols_sql})"
    cursor.execute(sql)


def insert_rows(cursor, table_name, columns, rows):
    cols_sql = ", ".join(f"`{col}`" for col in columns)
    placeholders = ", ".join(["%s"] * len(columns))
    sql = f"INSERT INTO `{table_name}` ({cols_sql}) VALUES ({placeholders})"
    cursor.executemany(sql, rows)


def import_csv_to_table(cursor, filepath):
    base = os.path.basename(filepath)
    if "dictionary" in base.lower():
        print(f"Skipping dictionary file: {base}")
        return 0

    table_base = os.path.splitext(base)[0]
    table_name = "import_" + sanitize_identifier(table_base)

    with open(filepath, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        try:
            headers = next(reader)
        except StopIteration:
            print(f"Empty file: {base}")
            return 0

        # sanitize header names to valid SQL identifiers
        cols = [sanitize_identifier(h) if h and h.strip() != "" else f"col_{i+1}" for i, h in enumerate(headers)]

        create_table_if_not_exists(cursor, table_name, cols)

        rows = []
        count = 0
        for r in reader:
            # normalize row length
            if len(r) < len(cols):
                r += [None] * (len(cols) - len(r))
            elif len(r) > len(cols):
                r = r[:len(cols)]
            # convert blank strings to None
            r = [none_if_blank(x) for x in r]
            rows.append(r)
            count += 1

            # batch insert to keep memory reasonable
            if len(rows) >= 500:
                insert_rows(cursor, table_name, cols, rows)
                rows = []

        if rows:
            insert_rows(cursor, table_name, cols, rows)

    print(f"Imported {count} rows into {table_name} from {base}")
    return count


def main():
    connection = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        autocommit=False,
    )
    cursor = connection.cursor()

    total_files = 0
    total_rows = 0
    for filepath in sorted(glob.glob(CSV_PATTERN)):
        total_files += 1
        try:
            rows = import_csv_to_table(cursor, filepath)
            total_rows += rows
            connection.commit()
        except Exception as e:
            connection.rollback()
            print(f"Error importing {filepath}: {e}")

    cursor.close()
    connection.close()

    print("Files processed:", total_files)
    print("Total rows imported:", total_rows)


if __name__ == '__main__':
    main()