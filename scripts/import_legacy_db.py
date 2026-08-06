import argparse
import re
import sqlite3
from pathlib import Path


CREATE_RE = re.compile(r"CREATE TABLE\s+`?(\w+)`?\s*\((.*?)\)\s*TYPE=", re.S | re.I)
INSERT_RE = re.compile(r"^INSERT INTO\s+`?(\w+)`?\s+VALUES\s*\((.*)\);$", re.M | re.I)


def main():
    parser = argparse.ArgumentParser(description="Importa backup MySQL antigo para SQLite local.")
    parser.add_argument("--sql", required=True, help="Caminho do arquivo .sql antigo")
    parser.add_argument("--db", required=True, help="Caminho do banco SQLite de saida")
    args = parser.parse_args()

    sql_path = Path(args.sql)
    db_path = Path(args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    text = read_text(sql_path)
    schemas = parse_schemas(text)

    if db_path.exists():
        db_path.unlink()

    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        create_raw_tables(conn, schemas)
        counts = import_rows(conn, text, schemas)
        create_normalized_tables(conn)
        normalize_employees(conn, schemas)
        normalize_time_entries(conn, schemas)
        create_import_metadata(conn, sql_path, counts)

    print(f"Banco criado: {db_path}")
    print(f"Tabelas importadas: {len(counts)}")
    for table, count in sorted(counts.items()):
        if count:
            print(f"- {table}: {count} registros")


def read_text(path):
    for encoding in ("utf-8", "latin-1", "cp1252"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(errors="replace")


def parse_schemas(text):
    schemas = {}
    for match in CREATE_RE.finditer(text):
        table = match.group(1)
        body = match.group(2)
        columns = []
        for raw_line in body.splitlines():
            line = raw_line.strip().rstrip(",")
            if not line or line.upper().startswith(("PRIMARY ", "KEY ", "UNIQUE ", "INDEX ")):
                continue
            column_match = re.match(r"`?([A-Za-z_][\w]*)`?\s+", line)
            if column_match:
                columns.append(column_match.group(1))
        if columns:
            schemas[table] = columns
    return schemas


def create_raw_tables(conn, schemas):
    for table, columns in schemas.items():
        raw_table = raw_name(table)
        column_sql = ", ".join(f"{quote(column)} TEXT" for column in columns)
        conn.execute(f"CREATE TABLE {quote(raw_table)} ({column_sql})")


def import_rows(conn, text, schemas):
    counts = {table: 0 for table in schemas}
    cursors = {}

    for match in INSERT_RE.finditer(text):
        table = match.group(1)
        if table not in schemas:
            continue

        values = parse_values(match.group(2))
        columns = schemas[table]
        if len(values) < len(columns):
            values.extend([None] * (len(columns) - len(values)))
        elif len(values) > len(columns):
            values = values[: len(columns)]

        raw_table = raw_name(table)
        placeholders = ", ".join("?" for _ in columns)
        sql = cursors.get(table)
        if sql is None:
            sql = f"INSERT INTO {quote(raw_table)} VALUES ({placeholders})"
            cursors[table] = sql
        conn.execute(sql, values)
        counts[table] += 1

    return counts


def parse_values(raw):
    values = []
    current = []
    in_string = False
    escaped = False

    for char in raw:
        if in_string:
            if escaped:
                current.append(char)
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == "'":
                in_string = False
            else:
                current.append(char)
            continue

        if char == "'":
            in_string = True
        elif char == ",":
            values.append(convert_token("".join(current).strip()))
            current = []
        else:
            current.append(char)

    values.append(convert_token("".join(current).strip()))
    return values


def convert_token(token):
    if token.upper() == "NULL" or token == "":
        return None
    return token


def create_normalized_tables(conn):
    conn.executescript(
        """
        CREATE TABLE employees (
          id INTEGER PRIMARY KEY,
          clock_id TEXT,
          name TEXT,
          department TEXT,
          active TEXT,
          cpf TEXT,
          pis TEXT,
          role TEXT,
          weekday_hours TEXT,
          saturday_hours TEXT,
          sunday_hours TEXT,
          tolerance_minutes INTEGER
        );

        CREATE TABLE time_entries (
          id INTEGER PRIMARY KEY,
          employee_id INTEGER,
          work_date TEXT,
          day INTEGER,
          month INTEGER,
          year INTEGER,
          entrada1 TEXT,
          saida1 TEXT,
          entrada2 TEXT,
          saida2 TEXT,
          entrada3 TEXT,
          saida3 TEXT,
          entrada4 TEXT,
          saida4 TEXT,
          expected_hours TEXT,
          worked_hours TEXT,
          credit_hours TEXT,
          debit_hours TEXT,
          credit_decimal REAL,
          debit_decimal REAL,
          extra_night_decimal REAL,
          absence TEXT,
          note TEXT,
          legacy_id TEXT
        );

        CREATE INDEX idx_time_entries_employee_date ON time_entries(employee_id, work_date);
        CREATE INDEX idx_time_entries_month ON time_entries(year, month);
        """
    )


def normalize_employees(conn, schemas):
    if "vendedor" not in schemas:
        return

    columns = schemas["vendedor"]
    index = {column.lower(): i for i, column in enumerate(columns)}
    rows = conn.execute(f"SELECT * FROM {quote(raw_name('vendedor'))}").fetchall()

    for row in rows:
        employee_id = to_int(get(row, index, "codigo"))
        name = get(row, index, "nome")
        if not employee_id or not name or name.lower().startswith("tempo"):
            continue

        conn.execute(
            """
            INSERT OR REPLACE INTO employees (
              id, clock_id, name, department, active, cpf, pis, role,
              weekday_hours, saturday_hours, sunday_hours, tolerance_minutes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                employee_id,
                get(row, index, "cracha"),
                clean_name(name),
                get(row, index, "departamento"),
                get(row, index, "ativo"),
                get(row, index, "cpf"),
                get(row, index, "pis"),
                get(row, index, "cargo") or get(row, index, "funcao"),
                decimal_hours_to_hhmm(get(row, index, "segunda")) or decimal_hours_to_hhmm(get(row, index, "horasdia")),
                decimal_hours_to_hhmm(get(row, index, "sabado")),
                decimal_hours_to_hhmm(get(row, index, "domingo")) or "00:00",
                to_int(get(row, index, "tolerancia")),
            ),
        )


def normalize_time_entries(conn, schemas):
    if "vendedor1" not in schemas:
        return

    columns = schemas["vendedor1"]
    index = {column.lower(): i for i, column in enumerate(columns)}
    rows = conn.execute(f"SELECT * FROM {quote(raw_name('vendedor1'))}").fetchall()

    for row in rows:
        conn.execute(
            """
            INSERT OR REPLACE INTO time_entries (
              id, employee_id, work_date, day, month, year,
              entrada1, saida1, entrada2, saida2, entrada3, saida3, entrada4, saida4,
              expected_hours, worked_hours, credit_hours, debit_hours,
              credit_decimal, debit_decimal, extra_night_decimal, absence, note, legacy_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                to_int(get(row, index, "codigo")),
                to_int(get(row, index, "funcionario")),
                get(row, index, "data"),
                to_int(get(row, index, "dia")),
                to_int(get(row, index, "mes")),
                to_int(get(row, index, "ano")),
                time_value(get(row, index, "entrada1")),
                time_value(get(row, index, "saida1")),
                time_value(get(row, index, "entrada2")),
                time_value(get(row, index, "saida2")),
                time_value(get(row, index, "entrada3")),
                time_value(get(row, index, "saida3")),
                time_value(get(row, index, "entrada4")),
                time_value(get(row, index, "saida4")),
                decimal_hours_to_hhmm(get(row, index, "horasdia")),
                time_value(get(row, index, "horasdiad")),
                time_value(get(row, index, "creditod")) or decimal_hours_to_hhmm(get(row, index, "credito")),
                time_value(get(row, index, "debitod")) or decimal_hours_to_hhmm(get(row, index, "debito")),
                to_float(get(row, index, "credito")),
                to_float(get(row, index, "debito")),
                to_float(get(row, index, "adicionaln")),
                get(row, index, "falta"),
                get(row, index, "obs"),
                get(row, index, "codigo"),
            ),
        )


def create_import_metadata(conn, sql_path, counts):
    conn.execute(
        """
        CREATE TABLE import_metadata (
          key TEXT PRIMARY KEY,
          value TEXT
        )
        """
    )
    metadata = {
        "source_sql": str(sql_path),
        "source_size": str(sql_path.stat().st_size),
        "raw_tables": str(len(counts)),
        "raw_rows": str(sum(counts.values())),
    }
    conn.executemany("INSERT INTO import_metadata VALUES (?, ?)", metadata.items())


def get(row, index, column):
    position = index.get(column.lower())
    if position is None or position >= len(row):
        return None
    return row[position]


def to_int(value):
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def to_float(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def clean_name(value):
    return str(value).strip().title()


def time_value(value):
    if not value or value == "00:00:00":
        return None
    match = re.match(r"^(\d{1,3}):(\d{2})(?::\d{2})?$", str(value))
    if not match:
        return None
    return f"{int(match.group(1)):02d}:{match.group(2)}"


def decimal_hours_to_hhmm(value):
    number = to_float(value)
    if number is None:
        return None
    minutes = round(number * 60)
    hours, mins = divmod(abs(minutes), 60)
    prefix = "-" if minutes < 0 else ""
    return f"{prefix}{hours:02d}:{mins:02d}"


def quote(identifier):
    return '"' + identifier.replace('"', '""') + '"'


def raw_name(table):
    return f"legacy_{table}"


if __name__ == "__main__":
    main()
