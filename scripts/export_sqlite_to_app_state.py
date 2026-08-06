import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Exporta o SQLite local para backup JSON do app.")
    parser.add_argument("--db", required=True, help="Caminho do banco SQLite")
    parser.add_argument("--out", required=True, help="Arquivo JSON de saida")
    args = parser.parse_args()

    db_path = Path(args.db)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        state = build_state(conn)

    out_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Backup do app criado: {out_path}")
    print(f"Funcionarios: {len(state['employees'])}")
    print(f"Linhas TXT: {len(state['rawText'].splitlines()) - 1}")


def build_state(conn):
    employees = {}
    for row in conn.execute(
        """
        SELECT id, name, department, weekday_hours, saturday_hours, sunday_hours, tolerance_minutes
        FROM employees
        ORDER BY id
        """
    ):
        employees[str(row["id"])] = {
            "id": str(row["id"]),
            "name": row["name"] or f"Funcionario {row['id']}",
            "department": row["department"] or "",
            "weekdayHours": row["weekday_hours"] or "08:00",
            "saturdayHours": row["saturday_hours"] or "04:00",
            "sundayHours": row["sunday_hours"] or "00:00",
            "tolerance": row["tolerance_minutes"] or 0,
            "active": True,
        }

    raw_lines = ["ID\tNome\tDepart.\tTempo\tNumero da maquina"]
    day_edits = {}

    for row in conn.execute(
        """
        SELECT te.*, e.name, e.department
        FROM time_entries te
        LEFT JOIN employees e ON e.id = te.employee_id
        WHERE te.work_date IS NOT NULL
        ORDER BY te.work_date, te.employee_id, te.id
        """
    ):
        employee_id = str(row["employee_id"] or "")
        if not employee_id:
            continue

        name = row["name"] or f"Funcionario {employee_id}"
        department = row["department"] or ""
        date_br = date_to_br(row["work_date"])
        punches = collect_punches(row)

        for punch in punches:
            raw_lines.append(f"{employee_id}\t{name}\t{department}\t {date_br}     {punch}:00\t1")

        row_key = f"{employee_id}|{row['work_date']}"
        edit = {}
        if row["expected_hours"]:
            edit["expectedText"] = normalize_hhmm(row["expected_hours"])
        if row["note"]:
            edit["note"] = row["note"]
        if edit:
            day_edits[row_key] = edit

    return {
        "savedAt": datetime.now().isoformat(timespec="seconds"),
        "activeView": "timesheet",
        "rawText": "\n".join(raw_lines),
        "settings": {
            "weekdayHours": "08:00",
            "saturdayHours": "04:00",
            "defaultTolerance": "15",
        },
        "filters": {
            "monthFilter": "",
            "employeeFilter": "",
        },
        "employees": employees,
        "dayEdits": day_edits,
    }


def collect_punches(row):
    values = [
        row["entrada1"],
        row["saida1"],
        row["entrada2"],
        row["saida2"],
        row["entrada3"],
        row["saida3"],
        row["entrada4"],
        row["saida4"],
    ]
    punches = [normalize_hhmm(value) for value in values if normalize_hhmm(value)]
    return sorted(set(punches))


def normalize_hhmm(value):
    if not value:
        return None
    text = str(value)
    parts = text.split(":")
    if len(parts) < 2:
        return None
    try:
        return f"{int(parts[0]):02d}:{int(parts[1]):02d}"
    except ValueError:
        return None


def date_to_br(value):
    year, month, day = str(value).split("-")
    return f"{day}/{month}/{year}"


if __name__ == "__main__":
    main()
