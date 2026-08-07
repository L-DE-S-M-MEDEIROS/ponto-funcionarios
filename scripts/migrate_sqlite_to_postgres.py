import argparse
import sqlite3

import psycopg


EMPLOYEE_COLUMNS = [
    "id",
    "clock_id",
    "name",
    "department",
    "active",
    "cpf",
    "pis",
    "role",
    "weekday_hours",
    "saturday_hours",
    "sunday_hours",
    "tolerance_minutes",
]

ENTRY_COLUMNS = [
    "id",
    "employee_id",
    "work_date",
    "day",
    "month",
    "year",
    "entrada1",
    "saida1",
    "entrada2",
    "saida2",
    "entrada3",
    "saida3",
    "entrada4",
    "saida4",
    "expected_hours",
    "worked_hours",
    "credit_hours",
    "debit_hours",
    "credit_decimal",
    "debit_decimal",
    "extra_night_decimal",
    "absence",
    "note",
    "legacy_id",
]


def placeholders(count):
    return ", ".join(["%s"] * count)


def migrate(args):
    sqlite_conn = sqlite3.connect(args.sqlite)
    sqlite_conn.row_factory = sqlite3.Row
    pg_conn = psycopg.connect(
        host=args.host,
        port=args.port,
        dbname=args.dbname,
        user=args.user,
        password=args.password,
    )

    employee_rows = sqlite_conn.execute("SELECT * FROM employees ORDER BY id").fetchall()
    entry_rows = sqlite_conn.execute("SELECT * FROM time_entries ORDER BY id").fetchall()

    with pg_conn:
        with pg_conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS employees (
                  id SERIAL PRIMARY KEY,
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
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS time_entries (
                  id SERIAL PRIMARY KEY,
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
                )
                """
            )
            employee_sql = f"""
                INSERT INTO employees ({', '.join(EMPLOYEE_COLUMNS)})
                VALUES ({placeholders(len(EMPLOYEE_COLUMNS))})
                ON CONFLICT (id) DO UPDATE SET
                  clock_id=EXCLUDED.clock_id,
                  name=EXCLUDED.name,
                  department=EXCLUDED.department,
                  active=EXCLUDED.active,
                  cpf=EXCLUDED.cpf,
                  pis=EXCLUDED.pis,
                  role=EXCLUDED.role,
                  weekday_hours=EXCLUDED.weekday_hours,
                  saturday_hours=EXCLUDED.saturday_hours,
                  sunday_hours=EXCLUDED.sunday_hours,
                  tolerance_minutes=EXCLUDED.tolerance_minutes
            """
            entry_sql = f"""
                INSERT INTO time_entries ({', '.join(ENTRY_COLUMNS)})
                VALUES ({placeholders(len(ENTRY_COLUMNS))})
                ON CONFLICT (id) DO UPDATE SET
                  employee_id=EXCLUDED.employee_id,
                  work_date=EXCLUDED.work_date,
                  day=EXCLUDED.day,
                  month=EXCLUDED.month,
                  year=EXCLUDED.year,
                  entrada1=EXCLUDED.entrada1,
                  saida1=EXCLUDED.saida1,
                  entrada2=EXCLUDED.entrada2,
                  saida2=EXCLUDED.saida2,
                  entrada3=EXCLUDED.entrada3,
                  saida3=EXCLUDED.saida3,
                  entrada4=EXCLUDED.entrada4,
                  saida4=EXCLUDED.saida4,
                  expected_hours=EXCLUDED.expected_hours,
                  worked_hours=EXCLUDED.worked_hours,
                  credit_hours=EXCLUDED.credit_hours,
                  debit_hours=EXCLUDED.debit_hours,
                  credit_decimal=EXCLUDED.credit_decimal,
                  debit_decimal=EXCLUDED.debit_decimal,
                  extra_night_decimal=EXCLUDED.extra_night_decimal,
                  absence=EXCLUDED.absence,
                  note=EXCLUDED.note,
                  legacy_id=EXCLUDED.legacy_id
            """
            for row in employee_rows:
                cur.execute(employee_sql, tuple(row[column] for column in EMPLOYEE_COLUMNS))
            for row in entry_rows:
                cur.execute(entry_sql, tuple(row[column] for column in ENTRY_COLUMNS))
            cur.execute("SELECT setval(pg_get_serial_sequence('employees','id'), COALESCE((SELECT MAX(id) FROM employees), 1), true)")
            cur.execute("SELECT setval(pg_get_serial_sequence('time_entries','id'), COALESCE((SELECT MAX(id) FROM time_entries), 1), true)")

    sqlite_conn.close()
    pg_conn.close()
    print(f"Migracao concluida. Funcionarios: {len(employee_rows)} | Pontos: {len(entry_rows)}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sqlite", default="data/ponto_funcionarios.db")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=5432)
    parser.add_argument("--dbname", default="ponto_funcionarios")
    parser.add_argument("--user", default="ponto_app")
    parser.add_argument("--password", required=True)
    migrate(parser.parse_args())


if __name__ == "__main__":
    main()
