import sqlite3
import json
import sys
import tkinter as tk
import urllib.request
import webbrowser
from datetime import date, datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).resolve().parent
else:
    APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "data" / "ponto_funcionarios.db"
APP_VERSION = "26.08.4"
UPDATE_MANIFEST_URL = "https://raw.githubusercontent.com/L-DE-S-M-MEDEIROS/ponto-funcionarios/main/version.json"


MONTHS = [
    ("1", "Janeiro"),
    ("2", "Fevereiro"),
    ("3", "Março"),
    ("4", "Abril"),
    ("5", "Maio"),
    ("6", "Junho"),
    ("7", "Julho"),
    ("8", "Agosto"),
    ("9", "Setembro"),
    ("10", "Outubro"),
    ("11", "Novembro"),
    ("12", "Dezembro"),
]


class PontoDesktop(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SISTEMA_CONTROLE_DE_PONTO - BOLSAS BABY")
        self.geometry("1160x720")
        self.minsize(1060, 650)
        self.configure(bg="#eeeeee")
        self.selected_entry_id = None

        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row
        self.ensure_schema()
        self.create_menu()
        self.show_home()

    def ensure_schema(self):
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS employees (
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
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS time_entries (
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
            )
            """
        )
        self.conn.commit()

    def create_menu(self):
        menu = tk.Menu(self, tearoff=False)

        cadastros = tk.Menu(menu, tearoff=False)
        cadastros.add_command(label="Funcionário-Leitor Nitgen", command=self.show_employees)
        cadastros.add_command(label="Funcionário-Outros Leitores", command=self.show_employees)
        cadastros.add_command(label="Departamento", command=self.show_departments)
        menu.add_cascade(label="CADASTROS", menu=cadastros)

        processos = tk.Menu(menu, tearoff=False)
        processos.add_command(label="Consulta Ponto - Edição", command=self.show_manual_point)
        processos.add_command(label="Banco de Horas", command=self.show_hour_bank)
        processos.add_command(label="Ponto Biométrico Nitgen", command=self.not_ready)
        processos.add_command(label="Ponto por Barras ou Senha", command=self.not_ready)
        processos.add_command(label="Impressão do Ponto", command=self.show_report)
        processos.add_command(label="Importar Ponto", command=self.import_attendance_file)
        processos.add_separator()
        processos.add_command(label="Retirada de Cesta", command=self.not_ready)
        processos.add_command(label="Relatório Retirada de Cesta", command=self.not_ready)
        processos.add_command(label="Relatório Cesta não Retirada", command=self.not_ready)
        processos.add_separator()
        processos.add_command(label="Lançar Cesta", command=self.not_ready)
        processos.add_command(label="Limpar Cesta", command=self.not_ready)
        processos.add_separator()
        processos.add_command(label="Pagamentos/Holerite", command=self.not_ready)
        menu.add_cascade(label="PROCESSOS", menu=processos)

        auxiliares = tk.Menu(menu, tearoff=False)
        auxiliares.add_command(label="Usuários", command=self.not_ready)
        auxiliares.add_command(label="Parâmetros", command=self.show_parameters)
        auxiliares.add_command(label="Manutenção", command=self.not_ready)
        auxiliares.add_command(label="Eventos do Sistema", command=self.not_ready)
        auxiliares.add_command(label="Buscar Atualizações", command=self.check_updates)
        auxiliares.add_command(label="Cópia Segurança", command=self.backup_info)
        auxiliares.add_separator()
        auxiliares.add_command(label="Ponto Automatico Criar Atalho em Desktop", command=self.not_ready)
        auxiliares.add_separator()
        auxiliares.add_command(label="Limpar Banco de Dados", command=self.not_ready)
        auxiliares.add_separator()
        auxiliares.add_command(label="Sobre", command=self.about)
        menu.add_cascade(label="AUXILIARES", menu=auxiliares)

        menu.add_command(label="SAIR", command=self.destroy)
        self.config(menu=menu)

    def clear(self):
        for child in self.winfo_children():
            if not isinstance(child, tk.Menu):
                child.destroy()

    def show_login(self):
        self.clear()
        background = tk.Frame(self, bg="#e7eaed")
        background.pack(fill="both", expand=True)

        frame = tk.Frame(background, bg="white", highlightbackground="#9aa3aa", highlightthickness=1)
        frame.place(relx=0.5, rely=0.48, anchor="center", width=680, height=390)

        header = tk.Frame(frame, bg="#0b7285", height=74)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="PONTO", bg="#0b7285", fg="white", font=("Arial Black", 25)).pack(side="left", padx=(26, 4))
        tk.Label(header, text="FUNCIONÁRIOS", bg="#0b7285", fg="#ff7a00", font=("Arial Black", 25)).pack(side="left")
        tk.Label(header, text=f"Versão {APP_VERSION}", bg="#0b7285", fg="#d9f5f8", font=("Arial", 10, "bold")).pack(side="right", padx=24)

        body = tk.Frame(frame, bg="white")
        body.pack(fill="both", expand=True)

        left = tk.Frame(body, bg="white")
        left.place(x=42, y=38, width=275, height=215)
        tk.Label(left, text="Sistema local de controle de ponto", bg="white", fg="#263238", font=("Arial", 14, "bold")).pack(anchor="w")
        tk.Label(left, text="Banco de horas, conferência e inclusão manual", bg="white", fg="#65737a", font=("Arial", 10)).pack(anchor="w", pady=(8, 20))

        key_canvas = tk.Canvas(left, width=88, height=70, bg="white", highlightthickness=0)
        key_canvas.pack(anchor="w", pady=(4, 0))
        key_canvas.create_oval(8, 15, 38, 45, outline="#d99a00", width=4)
        key_canvas.create_line(34, 38, 75, 62, fill="#d99a00", width=4)
        key_canvas.create_line(58, 52, 58, 66, fill="#d99a00", width=3)
        key_canvas.create_line(68, 57, 68, 70, fill="#d99a00", width=3)

        form = tk.Frame(body, bg="white")
        form.place(x=360, y=42, width=250, height=225)

        self.login_user = tk.StringVar()
        self.login_password = tk.StringVar()

        tk.Label(form, text="Usuário", bg="white", fg="#263238", font=("Arial", 9, "bold")).pack(anchor="w")
        user_combo = ttk.Combobox(form, values=["ADMIN"], width=24)
        user_combo.pack(fill="x", pady=(4, 12), ipady=2)
        user_combo.set("ADMIN")

        tk.Label(form, text="Senha", bg="white", fg="#263238", font=("Arial", 9, "bold")).pack(anchor="w")
        tk.Entry(form, textvariable=self.login_password, bg="#fffbc2", show="*", width=28).pack(fill="x", pady=(4, 12), ipady=4)

        tk.Label(form, text="Empresa", bg="white", fg="#263238", font=("Arial", 9, "bold")).pack(anchor="w")
        tk.Entry(form, textvariable=self.login_user, bg="#fffbc2", width=28).pack(fill="x", pady=(4, 18), ipady=4)

        tk.Button(form, text="Entrar", command=self.show_manual_point, width=16, height=2).pack(anchor="e")

        tk.Frame(frame, bg="#00a9d6", height=7).pack(side="bottom", fill="x")
        footer = tk.Frame(frame, bg="#2b2b2b", height=34)
        footer.pack(side="bottom", fill="x")
        footer.pack_propagate(False)
        tk.Label(footer, text="BOLSAS BABY  |  Controle de ponto local", bg="#2b2b2b", fg="white", font=("Arial", 9, "bold")).pack(side="right", padx=24)

    def show_home(self):
        self.clear()
        self.configure(bg="white")
        self.selected_entry_id = None
        root = tk.Frame(self, bg="white")
        root.pack(fill="both", expand=True)

        toolbar = tk.Frame(root, bg="white")
        toolbar.pack(anchor="nw", padx=2, pady=2)

        self.home_button(toolbar, "👥", "Funcionário", self.show_employees, 0, 0)
        self.home_button(toolbar, "📝", "Entrada / Saída(F3)", self.not_ready, 0, 1, width=20)
        self.home_button(toolbar, "🔎", "Consulta Entrada/Saída(F4)", self.show_manual_point, 0, 2, width=26)
        self.home_button(toolbar, "❌", "Sair(F5)", self.destroy, 0, 3, width=12)
        self.home_button(toolbar, "🟢", "Importar Ponto", self.import_attendance_file, 1, 0)
        self.home_button(toolbar, "⏱", "Banco de Horas", self.show_hour_bank, 1, 1, width=20)

        self.clock_var = tk.StringVar()
        clock_frame = tk.Frame(root, bg="white")
        clock_frame.place(x=865, y=88)
        tk.Button(clock_frame, text="?", width=2, command=self.about, fg="white", bg="#4b56c2", font=("Arial", 12, "bold")).pack(side="left", padx=(0, 8))
        tk.Label(clock_frame, textvariable=self.clock_var, bg="#fffaa3", fg="black", font=("Arial", 26, "bold"), bd=1, relief="solid", padx=8).pack(side="left")
        self.update_clock()

        self.bind("<F3>", lambda _event: self.not_ready())
        self.bind("<F4>", lambda _event: self.show_manual_point())
        self.bind("<F5>", lambda _event: self.destroy())

    def home_button(self, parent, icon, text, command, row, column, width=18):
        button = tk.Button(
            parent,
            text=f"{icon} {text}",
            command=command,
            width=width,
            height=2,
            anchor="w",
            bg="#f4f4f4",
            activebackground="#e8eef5",
            font=("Arial", 12, "bold"),
            relief="raised",
            bd=1,
            padx=12,
        )
        button.grid(row=row, column=column, sticky="w", padx=1, pady=1)
        return button

    def update_clock(self):
        if hasattr(self, "clock_var"):
            self.clock_var.set(datetime.now().strftime("%H:%M:%S"))
            self.after(1000, self.update_clock)

    def show_manual_point(self):
        self.clear()
        self.selected_entry_id = None

        root = tk.Frame(self, bg="#eeeeee")
        root.pack(fill="both", expand=True, padx=8, pady=8)

        title = tk.Label(root, text="Ponto Inclusão Manual", bg="#eeeeee", fg="#777777", font=("Arial", 26, "bold"))
        title.grid(row=0, column=0, columnspan=4, sticky="w")

        top_buttons = tk.Frame(root, bg="#eeeeee")
        top_buttons.grid(row=0, column=4, columnspan=5, sticky="ew", padx=4)
        tk.Button(top_buttons, text="Alinha os dias sem intervalo", command=self.not_ready).pack(side="left", padx=4)
        tk.Button(top_buttons, text="Insere horário de almoço", command=self.insert_lunch).pack(side="left", padx=4)
        tk.Button(top_buttons, text="Clique aqui para Zerar o saldo do Funcionário", command=self.zero_balance).pack(side="left", padx=4)

        form = tk.LabelFrame(root, text="Funcionário", bg="#eeeeee", fg="black", font=("Arial", 10, "bold"))
        form.grid(row=1, column=0, columnspan=7, sticky="ew", pady=4)
        form.columnconfigure(0, weight=1)

        self.employee_var = tk.StringVar()
        self.employee_combo = ttk.Combobox(form, textvariable=self.employee_var, values=self.employee_options(), state="readonly")
        self.employee_combo.grid(row=0, column=0, sticky="ew", padx=6, pady=6)
        self.employee_combo.bind("<<ComboboxSelected>>", lambda _event: self.load_entries())

        tk.Label(form, text="Ativo\nN", bg="#eeeeee", font=("Arial", 9, "bold")).grid(row=0, column=1, padx=4)

        self.store_var = tk.StringVar(value="TODOS")
        self.month_var = tk.StringVar(value=str(date.today().month))
        self.year_var = tk.StringVar(value=str(date.today().year))
        self.hours_month_var = tk.StringVar(value="0:00")

        self.combo_block(form, "Loja", self.store_var, ["TODOS"], 2)
        self.combo_block(form, "Mês", self.month_var, [label for _num, label in MONTHS], 3)
        self.entry_block(form, "Ano", self.year_var, 4, width=7, yellow=True)
        self.entry_block(form, "Horas Mês", self.hours_month_var, 5, width=10)

        self.field_vars = {
            "day": tk.StringVar(),
            "week": tk.StringVar(),
            "absence": tk.BooleanVar(),
            "holiday": tk.BooleanVar(),
            "expected": tk.StringVar(value="0:00"),
            "worked": tk.StringVar(),
            "credit": tk.StringVar(),
            "debit": tk.StringVar(),
            "night": tk.StringVar(),
            "entrada1": tk.StringVar(),
            "saida1": tk.StringVar(),
            "entrada2": tk.StringVar(),
            "saida2": tk.StringVar(),
            "entrada3": tk.StringVar(),
            "saida3": tk.StringVar(),
            "entrada4": tk.StringVar(),
            "saida4": tk.StringVar(),
            "note": tk.StringVar(),
        }

        edit = tk.LabelFrame(root, bg="#eeeeee")
        edit.grid(row=2, column=0, columnspan=7, sticky="ew")
        for col in range(12):
            edit.columnconfigure(col, weight=1)

        self.small_field(edit, "Dia", "day", 0, 0, 7)
        self.small_field(edit, "Semana", "week", 0, 1, 8)
        tk.Checkbutton(edit, text="Falta", variable=self.field_vars["absence"], bg="#eeeeee").grid(row=0, column=2, sticky="w")
        tk.Checkbutton(edit, text="Feriado", variable=self.field_vars["holiday"], bg="#eeeeee").grid(row=0, column=3, sticky="w")
        self.small_field(edit, "Horas Dia", "expected", 0, 5, 9, bg="#fff8b8")
        self.small_field(edit, "Horas Trabalhada", "worked", 0, 6, 14)
        self.small_field(edit, "Crédito", "credit", 0, 7, 8, bg="#b7ffb7")
        self.small_field(edit, "Débito", "debit", 0, 8, 8, bg="#ff3a3a")
        self.small_field(edit, "Adicional", "night", 0, 9, 8, bg="#bffafa")

        punches = [("Entrada", "entrada1"), ("Saída", "saida1"), ("Entrada", "entrada2"), ("Saída", "saida2"), ("Entrada", "entrada3"), ("Saída", "saida3"), ("Entrada", "entrada4"), ("Saída", "saida4")]
        for idx, (label, key) in enumerate(punches):
            self.small_field(edit, label, key, 2, idx, 10)

        tk.Label(edit, text="Obs", bg="#eeeeee", font=("Arial", 9, "bold")).grid(row=4, column=0, sticky="w")
        tk.Entry(edit, textvariable=self.field_vars["note"]).grid(row=5, column=0, columnspan=10, sticky="ew", padx=4, pady=2)

        side = tk.Frame(root, bg="#eeeeee")
        side.grid(row=1, column=7, rowspan=3, sticky="ns", padx=8)
        tk.Button(side, text="Conferência Individual", width=22, command=self.load_entries).pack(pady=4)
        tk.Button(side, text="Conferência Todos", width=22, command=self.load_entries).pack(pady=4)
        tk.Button(side, text="Conferência por Período", width=22, command=self.load_entries).pack(pady=(48, 4))
        tk.Button(side, text="Funcionários Presentes", width=22, command=self.not_ready).pack(pady=4)
        tk.Button(side, text="Funcionários Faltantes", width=22, command=self.not_ready).pack(pady=4)

        columns = ("day", "entrada1", "saida1", "entrada2", "saida2", "entrada3", "saida3", "entrada4", "saida4", "expected", "worked", "note", "credit", "debit", "night", "store")
        self.tree = ttk.Treeview(root, columns=columns, show="headings", height=12)
        headings = ["Dia", "Entra.1", "Saida1", "Entra.2", "Saida2", "Entra.3", "Saida3", "Entra.4", "Saida4", "Horas dia", "Hora Trabalhada", "Obs", "Credito", "Debito", "Adicional", "Loja"]
        widths = [44, 65, 65, 65, 65, 65, 65, 65, 65, 75, 105, 160, 70, 70, 75, 80]
        for col, heading, width in zip(columns, headings, widths):
            self.tree.heading(col, text=heading)
            self.tree.column(col, width=width, minwidth=width, stretch=False)
        self.tree.grid(row=4, column=0, columnspan=8, sticky="nsew", pady=6)
        self.tree.bind("<<TreeviewSelect>>", self.select_entry)
        root.rowconfigure(4, weight=1)
        root.columnconfigure(6, weight=1)

        bottom = tk.Frame(root, bg="#eeeeee")
        bottom.grid(row=5, column=0, columnspan=8, sticky="ew", pady=4)
        tk.Button(bottom, text="💾\nGravar(F1)", width=12, height=3, command=self.save_entry).pack(side="left")
        tk.Button(bottom, text="➕\nIncluir(F2)", width=12, height=3, command=self.clear_form).pack(side="left")
        tk.Button(bottom, text="❌\nCancelar(F3)", width=12, height=3, command=self.clear_form).pack(side="left")
        tk.Button(bottom, text="🗑\nExcluir", width=12, height=3, command=self.delete_entry).pack(side="left")
        tk.Button(bottom, text="❌\nSair(F5)", width=12, height=3, command=self.show_home).pack(side="right")

        self.bind("<F1>", lambda _event: self.save_entry())
        self.bind("<F2>", lambda _event: self.clear_form())
        self.bind("<F3>", lambda _event: self.clear_form())
        self.bind("<F5>", lambda _event: self.show_home())

        employees = self.employee_options()
        if employees:
            self.employee_combo.set(employees[0])
        self.load_entries()

    def combo_block(self, parent, label, variable, values, col):
        tk.Label(parent, text=label, bg="#eeeeee", font=("Arial", 10, "bold")).grid(row=0, column=col, sticky="sw")
        combo = ttk.Combobox(parent, textvariable=variable, values=values, state="readonly", width=12)
        combo.grid(row=1, column=col, sticky="ew", padx=4, pady=3)
        combo.bind("<<ComboboxSelected>>", lambda _event: self.load_entries())

    def entry_block(self, parent, label, variable, col, width=10, yellow=False):
        tk.Label(parent, text=label, bg="#eeeeee", font=("Arial", 10, "bold")).grid(row=0, column=col, sticky="sw")
        tk.Entry(parent, textvariable=variable, width=width, bg="#fff8b8" if yellow else "white").grid(row=1, column=col, sticky="ew", padx=4, pady=3)

    def small_field(self, parent, label, key, row, col, width, bg="white"):
        tk.Label(parent, text=label, bg="#eeeeee", font=("Arial", 9, "bold")).grid(row=row, column=col, sticky="w", padx=2)
        tk.Entry(parent, textvariable=self.field_vars[key], width=width, bg=bg).grid(row=row + 1, column=col, sticky="ew", padx=2, pady=2)

    def employee_options(self):
        rows = self.conn.execute("SELECT id, name FROM employees ORDER BY name").fetchall()
        return [f"{row['id']} - {row['name']}" for row in rows]

    def selected_employee_id(self):
        if not hasattr(self, "employee_var"):
            return None
        value = self.employee_var.get()
        if not value:
            return None
        return int(value.split(" - ", 1)[0])

    def selected_month(self):
        value = self.month_var.get()
        for number, label in MONTHS:
            if value == label or value == number:
                return int(number)
        return date.today().month

    def load_entries(self):
        if not hasattr(self, "tree"):
            return
        for item in self.tree.get_children():
            self.tree.delete(item)

        employee_id = self.selected_employee_id()
        if not employee_id:
            return

        rows = self.conn.execute(
            """
            SELECT *
            FROM time_entries
            WHERE employee_id = ? AND month = ? AND year = ?
            ORDER BY day, id
            """,
            (employee_id, self.selected_month(), int(self.year_var.get() or date.today().year)),
        ).fetchall()

        credit_total = 0
        debit_total = 0
        worked_total = 0
        for row in rows:
            credit_total += minutes(row["credit_hours"])
            debit_total += minutes(row["debit_hours"])
            worked_total += minutes(row["worked_hours"])
            self.tree.insert(
                "",
                "end",
                iid=str(row["id"]),
                values=(
                    row["day"],
                    hhmm(row["entrada1"]),
                    hhmm(row["saida1"]),
                    hhmm(row["entrada2"]),
                    hhmm(row["saida2"]),
                    hhmm(row["entrada3"]),
                    hhmm(row["saida3"]),
                    hhmm(row["entrada4"]),
                    hhmm(row["saida4"]),
                    hhmm(row["expected_hours"]),
                    hhmm(row["worked_hours"]),
                    row["note"] or "",
                    hhmm(row["credit_hours"]),
                    hhmm(row["debit_hours"]),
                    decimal_to_hhmm(row["extra_night_decimal"]),
                    "TODOS",
                ),
            )
        self.hours_month_var.set(format_minutes(worked_total))

    def select_entry(self, _event=None):
        selected = self.tree.selection()
        if not selected:
            return
        self.selected_entry_id = int(selected[0])
        row = self.conn.execute("SELECT * FROM time_entries WHERE id = ?", (self.selected_entry_id,)).fetchone()
        if not row:
            return
        mapping = {
            "day": row["day"],
            "expected": hhmm(row["expected_hours"]),
            "worked": hhmm(row["worked_hours"]),
            "credit": hhmm(row["credit_hours"]),
            "debit": hhmm(row["debit_hours"]),
            "night": decimal_to_hhmm(row["extra_night_decimal"]),
            "entrada1": hhmm(row["entrada1"]),
            "saida1": hhmm(row["saida1"]),
            "entrada2": hhmm(row["entrada2"]),
            "saida2": hhmm(row["saida2"]),
            "entrada3": hhmm(row["entrada3"]),
            "saida3": hhmm(row["saida3"]),
            "entrada4": hhmm(row["entrada4"]),
            "saida4": hhmm(row["saida4"]),
            "note": row["note"] or "",
        }
        for key, value in mapping.items():
            self.field_vars[key].set("" if value is None else value)
        self.field_vars["absence"].set((row["absence"] or "").upper() == "S")

    def clear_form(self):
        self.selected_entry_id = None
        for key, variable in self.field_vars.items():
            if isinstance(variable, tk.BooleanVar):
                variable.set(False)
            else:
                variable.set("")
        self.field_vars["expected"].set("0:00")

    def show_hour_bank(self):
        self.clear()
        self.configure(bg="#eeeeee")

        root = tk.Frame(self, bg="#eeeeee")
        root.pack(fill="both", expand=True, padx=10, pady=10)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(2, weight=1)

        header = tk.Frame(root, bg="#eeeeee")
        header.grid(row=0, column=0, sticky="ew")
        tk.Label(header, text="Banco de Horas", bg="#eeeeee", fg="#666666", font=("Arial", 26, "bold")).pack(side="left")

        filters = tk.LabelFrame(root, text="Filtros", bg="#eeeeee", font=("Arial", 10, "bold"))
        filters.grid(row=1, column=0, sticky="ew", pady=(8, 6))
        filters.columnconfigure(1, weight=1)

        self.bank_employee_var = tk.StringVar(value="TODOS")
        self.bank_year_var = tk.StringVar(value=str(date.today().year))
        employee_values = ["TODOS"] + self.employee_options()

        tk.Label(filters, text="Funcionário", bg="#eeeeee", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", padx=6)
        employee_combo = ttk.Combobox(filters, textvariable=self.bank_employee_var, values=employee_values, state="readonly")
        employee_combo.grid(row=1, column=0, columnspan=2, sticky="ew", padx=6, pady=4)
        employee_combo.bind("<<ComboboxSelected>>", lambda _event: self.load_hour_bank())

        tk.Label(filters, text="Ano", bg="#eeeeee", font=("Arial", 10, "bold")).grid(row=0, column=2, sticky="w", padx=6)
        year_entry = tk.Entry(filters, textvariable=self.bank_year_var, width=8, bg="#fff8b8")
        year_entry.grid(row=1, column=2, sticky="w", padx=6, pady=4)
        year_entry.bind("<Return>", lambda _event: self.load_hour_bank())

        tk.Button(filters, text="Atualizar", width=12, command=self.load_hour_bank).grid(row=1, column=3, padx=6, pady=4)
        tk.Button(filters, text="Voltar", width=12, command=self.show_home).grid(row=1, column=4, padx=6, pady=4)

        table_frame = tk.Frame(root, bg="#eeeeee")
        table_frame.grid(row=2, column=0, sticky="nsew")
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        month_keys = [label[:3].upper() for _number, label in MONTHS]
        columns = ("employee", "kind", *month_keys, "total")
        self.hour_bank_tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=18)
        headings = ["Funcionário", "Tipo", *month_keys, "Total Ano"]
        widths = [180, 115, *([76] * 12), 90]
        for col, heading, width in zip(columns, headings, widths):
            self.hour_bank_tree.heading(col, text=heading)
            self.hour_bank_tree.column(col, width=width, minwidth=width, stretch=col == "employee")
        self.hour_bank_tree.grid(row=0, column=0, sticky="nsew")

        y_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.hour_bank_tree.yview)
        y_scroll.grid(row=0, column=1, sticky="ns")
        self.hour_bank_tree.configure(yscrollcommand=y_scroll.set)

        self.hour_bank_tree.tag_configure("credit", background="#e8ffe8")
        self.hour_bank_tree.tag_configure("debit", background="#ffe8e8")
        self.hour_bank_tree.tag_configure("balance", background="#eef4ff", font=("Arial", 9, "bold"))

        self.bank_summary_var = tk.StringVar()
        tk.Label(root, textvariable=self.bank_summary_var, bg="#eeeeee", fg="#222222", font=("Arial", 11, "bold")).grid(row=3, column=0, sticky="w", pady=(8, 0))

        self.bind("<F5>", lambda _event: self.show_home())
        self.load_hour_bank()

    def load_hour_bank(self):
        if not hasattr(self, "hour_bank_tree"):
            return
        for item in self.hour_bank_tree.get_children():
            self.hour_bank_tree.delete(item)

        try:
            year = int(self.bank_year_var.get())
        except ValueError:
            messagebox.showwarning("Banco de Horas", "Informe um ano válido.")
            return

        employee_filter = self.bank_employee_var.get()
        params = [year]
        employee_clause = ""
        if employee_filter and employee_filter != "TODOS":
            employee_clause = "AND e.id = ?"
            params.append(int(employee_filter.split(" - ", 1)[0]))

        rows = self.conn.execute(
            f"""
            SELECT e.id, e.name, t.month,
                   SUM(COALESCE(t.credit_decimal, 0)) AS credit,
                   SUM(COALESCE(t.debit_decimal, 0)) AS debit
            FROM employees e
            LEFT JOIN time_entries t ON t.employee_id = e.id AND t.year = ?
            WHERE 1 = 1 {employee_clause}
            GROUP BY e.id, e.name, t.month
            ORDER BY e.name, t.month
            """,
            params,
        ).fetchall()

        employees = {}
        for row in rows:
            employee = employees.setdefault(row["id"], {"name": row["name"], "credit": [0] * 12, "debit": [0] * 12})
            month = row["month"]
            if month:
                employee["credit"][int(month) - 1] = round(float(row["credit"] or 0) * 60)
                employee["debit"][int(month) - 1] = round(float(row["debit"] or 0) * 60)

        annual_credit = 0
        annual_debit = 0
        for employee in employees.values():
            credits = employee["credit"]
            debits = employee["debit"]
            balance = [credit - debit for credit, debit in zip(credits, debits)]
            annual_credit += sum(credits)
            annual_debit += sum(debits)
            self.hour_bank_tree.insert("", "end", values=(employee["name"], "HORAS EXTRAS", *[format_minutes(value) for value in credits], format_minutes(sum(credits))), tags=("credit",))
            self.hour_bank_tree.insert("", "end", values=("", "HORAS FALTANTES", *[format_minutes(value) for value in debits], format_minutes(sum(debits))), tags=("debit",))
            self.hour_bank_tree.insert("", "end", values=("", "TOTAL MÊS", *[format_minutes(value) for value in balance], format_minutes(sum(balance))), tags=("balance",))

        final_balance = annual_credit - annual_debit
        self.bank_summary_var.set(
            f"Resumo {year}: extras {format_minutes(annual_credit)} | faltantes {format_minutes(annual_debit)} | saldo {format_minutes(final_balance)}"
        )

    def import_attendance_file(self):
        path = filedialog.askopenfilename(
            title="Importar Ponto",
            filetypes=[("Arquivos TXT", "*.txt"), ("Todos os arquivos", "*.*")],
        )
        if not path:
            return

        try:
            summary = self.import_attendance_path(Path(path))
        except Exception as exc:
            messagebox.showerror("Importar Ponto", f"Não foi possível importar o arquivo.\n\n{exc}")
            return

        messagebox.showinfo(
            "Importar Ponto",
            "Importação concluída.\n\n"
            f"Arquivo: {Path(path).name}\n"
            f"Batidas lidas: {summary['punches']}\n"
            f"Dias atualizados: {summary['days']}\n"
            f"Funcionários não encontrados: {summary['unknown']}",
        )

    def import_attendance_path(self, path):
        punches = parse_attendance_txt(path)
        employees = {
            str(row["clock_id"]).strip(): row
            for row in self.conn.execute("SELECT * FROM employees WHERE clock_id IS NOT NULL AND clock_id <> ''")
        }

        grouped = {}
        unknown = set()
        for punch in punches:
            employee = employees.get(punch["clock_id"])
            if not employee:
                unknown.add(f"{punch['clock_id']} - {punch['name']}")
                continue
            key = (employee["id"], punch["stamp"].date())
            grouped.setdefault(key, {"employee": employee, "punches": []})["punches"].append(punch["stamp"])

        updated_days = 0
        for (employee_id, work_day), data in grouped.items():
            employee = data["employee"]
            stamps = sorted(set(data["punches"]))
            times = [stamp.strftime("%H:%M") for stamp in stamps[:8]]
            while len(times) < 8:
                times.append(None)

            expected = self.expected_hours_for_date(employee, work_day)
            worked_minutes = calculate_worked(times)
            expected_minutes = minutes(expected)
            diff = worked_minutes - expected_minutes
            tolerance = int(employee["tolerance_minutes"] or 0)
            if abs(diff) <= tolerance:
                diff = 0
            credit_minutes = max(diff, 0)
            debit_minutes = max(-diff, 0)
            note = f"Importado de {path.name}"
            if len(stamps) > 8:
                note += f" | {len(stamps) - 8} batida(s) extra(s) ignorada(s)"

            existing = self.conn.execute(
                "SELECT id FROM time_entries WHERE employee_id = ? AND work_date = ? ORDER BY id LIMIT 1",
                (employee_id, work_day.isoformat()),
            ).fetchone()
            values = (
                employee_id,
                work_day.isoformat(),
                work_day.day,
                work_day.month,
                work_day.year,
                *times,
                expected,
                format_minutes(worked_minutes),
                format_minutes(credit_minutes),
                format_minutes(debit_minutes),
                credit_minutes / 60,
                debit_minutes / 60,
                0,
                "N",
                note,
                f"txt:{path.name}:{employee['clock_id']}:{work_day.isoformat()}",
            )

            if existing:
                self.conn.execute(
                    """
                    UPDATE time_entries
                    SET employee_id=?, work_date=?, day=?, month=?, year=?,
                        entrada1=?, saida1=?, entrada2=?, saida2=?,
                        entrada3=?, saida3=?, entrada4=?, saida4=?,
                        expected_hours=?, worked_hours=?, credit_hours=?, debit_hours=?,
                        credit_decimal=?, debit_decimal=?, extra_night_decimal=?,
                        absence=?, note=?, legacy_id=?
                    WHERE id=?
                    """,
                    (*values, existing["id"]),
                )
            else:
                self.conn.execute(
                    """
                    INSERT INTO time_entries (
                        employee_id, work_date, day, month, year,
                        entrada1, saida1, entrada2, saida2,
                        entrada3, saida3, entrada4, saida4,
                        expected_hours, worked_hours, credit_hours, debit_hours,
                        credit_decimal, debit_decimal, extra_night_decimal,
                        absence, note, legacy_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    values,
                )
            updated_days += 1

        self.conn.commit()
        if hasattr(self, "tree"):
            self.load_entries()
        return {"punches": len(punches), "days": updated_days, "unknown": len(unknown)}

    def expected_hours_for_date(self, employee, work_day):
        if work_day.weekday() == 5:
            return employee["saturday_hours"] or "04:00"
        if work_day.weekday() == 6:
            return employee["sunday_hours"] or "00:00"
        return employee["weekday_hours"] or "08:00"

    def save_entry(self):
        employee_id = self.selected_employee_id()
        if not employee_id:
            messagebox.showwarning("Atenção", "Selecione um funcionário.")
            return
        try:
            day = int(self.field_vars["day"].get())
            month = self.selected_month()
            year = int(self.year_var.get())
            work_date = f"{year:04d}-{month:02d}-{day:02d}"
        except ValueError:
            messagebox.showwarning("Atenção", "Informe dia, mês e ano válidos.")
            return

        punches = [
            self.field_vars["entrada1"].get(),
            self.field_vars["saida1"].get(),
            self.field_vars["entrada2"].get(),
            self.field_vars["saida2"].get(),
            self.field_vars["entrada3"].get(),
            self.field_vars["saida3"].get(),
            self.field_vars["entrada4"].get(),
            self.field_vars["saida4"].get(),
        ]
        worked = calculate_worked(punches)
        expected = normalize_time(self.field_vars["expected"].get()) or "00:00"
        balance = worked - minutes(expected)
        credit = max(0, balance)
        debit = max(0, -balance)

        values = (
            employee_id,
            work_date,
            day,
            month,
            year,
            normalize_time(self.field_vars["entrada1"].get()),
            normalize_time(self.field_vars["saida1"].get()),
            normalize_time(self.field_vars["entrada2"].get()),
            normalize_time(self.field_vars["saida2"].get()),
            normalize_time(self.field_vars["entrada3"].get()),
            normalize_time(self.field_vars["saida3"].get()),
            normalize_time(self.field_vars["entrada4"].get()),
            normalize_time(self.field_vars["saida4"].get()),
            expected,
            format_minutes(worked),
            format_minutes(credit),
            format_minutes(debit),
            round(credit / 60, 2),
            round(debit / 60, 2),
            "S" if self.field_vars["absence"].get() else None,
            self.field_vars["note"].get(),
        )

        if self.selected_entry_id:
            self.conn.execute(
                """
                UPDATE time_entries
                SET employee_id=?, work_date=?, day=?, month=?, year=?,
                    entrada1=?, saida1=?, entrada2=?, saida2=?, entrada3=?, saida3=?, entrada4=?, saida4=?,
                    expected_hours=?, worked_hours=?, credit_hours=?, debit_hours=?,
                    credit_decimal=?, debit_decimal=?, absence=?, note=?
                WHERE id=?
                """,
                values + (self.selected_entry_id,),
            )
        else:
            self.conn.execute(
                """
                INSERT INTO time_entries (
                    employee_id, work_date, day, month, year,
                    entrada1, saida1, entrada2, saida2, entrada3, saida3, entrada4, saida4,
                    expected_hours, worked_hours, credit_hours, debit_hours,
                    credit_decimal, debit_decimal, absence, note
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )
        self.conn.commit()
        self.clear_form()
        self.load_entries()

    def delete_entry(self):
        if not self.selected_entry_id:
            return
        if not messagebox.askyesno("Excluir", "Excluir este ponto?"):
            return
        self.conn.execute("DELETE FROM time_entries WHERE id = ?", (self.selected_entry_id,))
        self.conn.commit()
        self.clear_form()
        self.load_entries()

    def insert_lunch(self):
        self.field_vars["saida1"].set("12:00")
        self.field_vars["entrada2"].set("12:30")

    def zero_balance(self):
        self.field_vars["credit"].set("00:00")
        self.field_vars["debit"].set("00:00")

    def show_employees(self):
        self.clear()
        frame = tk.Frame(self, bg="#eeeeee")
        frame.pack(fill="both", expand=True, padx=12, pady=12)
        tk.Label(frame, text="Funcionários", bg="#eeeeee", fg="#777777", font=("Arial", 24, "bold")).pack(anchor="w")
        tree = ttk.Treeview(frame, columns=("id", "clock", "name", "department", "weekday", "sat", "tol"), show="headings")
        for col, title, width in [
            ("id", "Código", 70),
            ("clock", "Crachá", 80),
            ("name", "Nome", 220),
            ("department", "Departamento", 150),
            ("weekday", "Semana", 80),
            ("sat", "Sábado", 80),
            ("tol", "Tolerância", 80),
        ]:
            tree.heading(col, text=title)
            tree.column(col, width=width)
        tree.pack(fill="both", expand=True, pady=10)
        for row in self.conn.execute("SELECT * FROM employees ORDER BY name"):
            tree.insert("", "end", values=(row["id"], row["clock_id"], row["name"], row["department"], row["weekday_hours"], row["saturday_hours"], row["tolerance_minutes"]))
        tk.Button(frame, text="Voltar", command=self.show_home).pack(anchor="e")

    def show_departments(self):
        departments = [row[0] for row in self.conn.execute("SELECT DISTINCT department FROM employees WHERE department IS NOT NULL AND department <> '' ORDER BY department")]
        messagebox.showinfo("Departamento", "\n".join(departments) or "Nenhum departamento cadastrado.")

    def show_parameters(self):
        messagebox.showinfo("Parâmetros", f"Banco local:\n{DB_PATH}")

    def show_report(self):
        employee_id = self.selected_employee_id()
        if not employee_id:
            self.show_manual_point()
            return
        rows = self.conn.execute(
            """
            SELECT e.name, SUM(COALESCE(credit_decimal, 0)), SUM(COALESCE(debit_decimal, 0)), COUNT(*)
            FROM time_entries t
            JOIN employees e ON e.id = t.employee_id
            WHERE t.employee_id = ? AND t.month = ? AND t.year = ?
            GROUP BY e.name
            """,
            (employee_id, self.selected_month(), int(self.year_var.get() or date.today().year)),
        ).fetchone()
        if not rows:
            messagebox.showinfo("Relatório", "Sem dados para o filtro atual.")
            return
        messagebox.showinfo("Relatório", f"Funcionário: {rows[0]}\nDias: {rows[3]}\nCrédito: {rows[1]:.2f}\nDébito: {rows[2]:.2f}")

    def backup_info(self):
        messagebox.showinfo("Cópia Segurança", f"Faça cópia deste arquivo:\n{DB_PATH}")

    def check_updates(self):
        try:
            with urllib.request.urlopen(UPDATE_MANIFEST_URL, timeout=12) as response:
                manifest = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            messagebox.showerror(
                "Buscar Atualizações",
                f"Não foi possível consultar atualizações.\n\n{exc}",
            )
            return

        remote_version = str(manifest.get("version", "")).strip()
        installer_url = str(manifest.get("url", "")).strip()
        title = str(manifest.get("title", "Atualização disponível")).strip()
        description = str(manifest.get("description", "")).strip()

        if not remote_version:
            messagebox.showwarning("Buscar Atualizações", "O arquivo de atualização não informou a versão.")
            return

        if version_tuple(remote_version) <= version_tuple(APP_VERSION):
            open_page = messagebox.askyesno(
                "Buscar Atualizações",
                f"Seu sistema já está atualizado.\n\nVersão instalada: {APP_VERSION}\nÚltima versão: {remote_version}\n\nDeseja abrir a página da versão mesmo assim?",
            )
        else:
            text = f"{title}\n\nVersão instalada: {APP_VERSION}\nNova versão: {remote_version}"
            if description:
                text += f"\n\n{description}"
            text += "\n\nDeseja abrir o instalador no GitHub?"
            open_page = messagebox.askyesno("Buscar Atualizações", text)

        if open_page:
            webbrowser.open(installer_url or "https://github.com/L-DE-S-M-MEDEIROS/ponto-funcionarios/releases/latest")

    def about(self):
        messagebox.showinfo("Sobre", f"Sistema de ponto local\nVersão {APP_VERSION}")

    def not_ready(self):
        messagebox.showinfo("Em desenvolvimento", "Este módulo será implementado na próxima etapa.")


def hhmm(value):
    normalized = normalize_time(value)
    return normalized or ""


def version_tuple(value):
    parts = []
    for item in str(value).replace("-", ".").split("."):
        digits = "".join(ch for ch in item if ch.isdigit())
        parts.append(int(digits or 0))
    return tuple(parts)


def parse_attendance_txt(path):
    text = read_text_file(path)
    punches = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.upper().startswith("ID"):
            continue
        parts = [part.strip() for part in line.split("\t") if part.strip()]
        if len(parts) < 4:
            continue
        clock_id, name, department, raw_stamp = parts[:4]
        stamp = parse_brazilian_datetime(raw_stamp)
        if not stamp:
            continue
        punches.append(
            {
                "clock_id": clock_id,
                "name": name,
                "department": department,
                "stamp": stamp,
            }
        )
    return punches


def read_text_file(path):
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return Path(path).read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return Path(path).read_text(errors="replace")


def parse_brazilian_datetime(value):
    normalized = " ".join(str(value).strip().split())
    for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(normalized, fmt)
        except ValueError:
            continue
    return None


def normalize_time(value):
    if value is None:
        return None
    text = str(value).strip()
    if not text or text == "00:00:00":
        return None
    parts = text.split(":")
    if len(parts) < 2:
        return None
    try:
        hour = int(parts[0])
        minute = int(parts[1])
    except ValueError:
        return None
    if minute > 59:
        return None
    return f"{hour:02d}:{minute:02d}"


def minutes(value):
    text = normalize_time(value)
    if not text:
        return 0
    hour, minute = text.split(":")
    return int(hour) * 60 + int(minute)


def format_minutes(total):
    total = int(total or 0)
    hour, minute = divmod(abs(total), 60)
    prefix = "-" if total < 0 else ""
    return f"{prefix}{hour:02d}:{minute:02d}"


def calculate_worked(values):
    times = [minutes(value) for value in values if normalize_time(value)]
    total = 0
    for index in range(0, len(times) - 1, 2):
        total += max(0, times[index + 1] - times[index])
    return total


def decimal_to_hhmm(value):
    if value in (None, ""):
        return ""
    try:
        return format_minutes(round(float(value) * 60))
    except ValueError:
        return ""


if __name__ == "__main__":
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    app = PontoDesktop()
    app.mainloop()
