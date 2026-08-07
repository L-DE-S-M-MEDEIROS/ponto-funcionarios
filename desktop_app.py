import sqlite3
import json
import os
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
CONFIG_PATH = APP_DIR / "config.json"
APP_VERSION = "26.08.13"
UPDATE_MANIFEST_URL = "https://raw.githubusercontent.com/L-DE-S-M-MEDEIROS/ponto-funcionarios/main/version.json"

DEFAULT_CONFIG = {
    "database": {
        "mode": "local",
        "host": "localhost",
        "port": 5432,
        "dbname": "ponto_funcionarios",
        "user": "ponto_app",
        "password": "",
    }
}


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


class AppConnection:
    def __init__(self, kind, config):
        self.kind = kind
        if kind == "postgres":
            try:
                import psycopg
                from psycopg.rows import dict_row
            except ImportError as exc:
                raise RuntimeError("Driver PostgreSQL não encontrado. Reinstale o sistema pela versão com suporte PostgreSQL.") from exc
            self.raw = psycopg.connect(
                host=config.get("host") or "localhost",
                port=int(config.get("port") or 5432),
                dbname=config.get("dbname") or "ponto_funcionarios",
                user=config.get("user") or "ponto_app",
                password=config.get("password") or "",
                row_factory=dict_row,
            )
        else:
            DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            self.raw = sqlite3.connect(config.get("path") or DB_PATH)
            self.raw.row_factory = sqlite3.Row

    def execute(self, sql, params=None):
        params = params or ()
        if self.kind == "postgres":
            sql = sql.replace("?", "%s")
        return self.raw.execute(sql, params)

    def executemany(self, sql, params):
        if self.kind == "postgres":
            sql = sql.replace("?", "%s")
        return self.raw.executemany(sql, params)

    def commit(self):
        self.raw.commit()

    def rollback(self):
        self.raw.rollback()

    def close(self):
        self.raw.close()


class PontoDesktop(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SISTEMA_CONTROLE_DE_PONTO - BOLSAS BABY")
        self.geometry("1160x720")
        self.minsize(1060, 650)
        self.configure(bg="#eeeeee")
        self.selected_entry_id = None

        self.app_config = load_app_config()
        self.conn = self.open_database()
        self.ensure_schema()
        self.create_menu()
        self.show_home()

    def open_database(self):
        db_config = self.app_config.get("database", {})
        if db_config.get("mode") == "postgres":
            try:
                return AppConnection("postgres", db_config)
            except Exception as exc:
                messagebox.showerror(
                    "Banco da Empresa",
                    f"Não foi possível conectar ao PostgreSQL.\n\n{exc}\n\nO sistema será aberto no banco local.",
                )
                self.app_config["database"]["mode"] = "local"
        return AppConnection("local", {"path": DB_PATH})

    def reconnect_database(self):
        try:
            self.conn.close()
        except Exception:
            pass
        self.conn = self.open_database()
        self.ensure_schema()

    def ensure_schema(self):
        if getattr(self.conn, "kind", "local") == "postgres":
            self.conn.execute(
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
            self.conn.execute(
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
            self.conn.commit()
            return

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
        cadastros.add_command(label="Funcionários", command=self.show_employees)
        cadastros.add_command(label="Departamentos", command=self.show_departments)
        menu.add_cascade(label="Cadastros", menu=cadastros)

        ponto = tk.Menu(menu, tearoff=False)
        ponto.add_command(label="Consultar / editar ponto", command=self.show_manual_point)
        ponto.add_command(label="Importar batidas do relógio", command=self.import_attendance_file)
        ponto.add_command(label="Banco de horas", command=self.show_hour_bank)
        ponto.add_separator()
        ponto.add_command(label="Inserir horário de almoço", command=self.insert_lunch)
        menu.add_cascade(label="Ponto", menu=ponto)

        relatorios = tk.Menu(menu, tearoff=False)
        relatorios.add_command(label="Espelho individual em PDF", command=self.show_manual_point)
        relatorios.add_command(label="Espelho de todos em PDF", command=self.show_manual_point)
        relatorios.add_command(label="Ponto + banco de horas em PDF", command=self.show_manual_point)
        relatorios.add_command(label="Banco de horas em PDF", command=self.show_hour_bank)
        menu.add_cascade(label="Relatórios", menu=relatorios)

        sistema = tk.Menu(menu, tearoff=False)
        sistema.add_command(label="Banco de dados e conexão", command=self.show_parameters)
        sistema.add_command(label="Buscar atualizações", command=self.check_updates)
        sistema.add_command(label="Cópia de segurança", command=self.backup_info)
        sistema.add_separator()
        sistema.add_command(label="Sobre", command=self.about)
        menu.add_cascade(label="Sistema", menu=sistema)

        menu.add_command(label="Sair", command=self.destroy)
        self.config(menu=menu)

    def create_menu_old(self):
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
        self.configure(bg="#f3f6f8")
        self.selected_entry_id = None

        root = tk.Frame(self, bg="#f3f6f8")
        root.pack(fill="both", expand=True)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(2, weight=1)

        header = tk.Frame(root, bg="#0b7285", height=86)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        header.columnconfigure(0, weight=1)
        tk.Label(header, text="Ponto Funcionários", bg="#0b7285", fg="white", font=("Arial", 24, "bold")).grid(row=0, column=0, sticky="w", padx=22, pady=(13, 0))
        tk.Label(header, text=f"BOLSAS BABY  |  Versão {APP_VERSION}  |  {self.database_label()}", bg="#0b7285", fg="#d9f5f8", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="w", padx=22)

        self.clock_var = tk.StringVar()
        clock_box = tk.Frame(header, bg="#0b7285")
        clock_box.grid(row=0, column=1, rowspan=2, sticky="e", padx=22)
        tk.Button(clock_box, text="?", width=3, command=self.about, fg="white", bg="#4154b3", activebackground="#34439a", font=("Arial", 11, "bold"), relief="flat").pack(side="left", padx=(0, 10))
        tk.Label(clock_box, textvariable=self.clock_var, bg="#fffaa3", fg="#111111", font=("Arial", 24, "bold"), bd=1, relief="solid", padx=10).pack(side="left")
        self.update_clock()

        content = tk.Frame(root, bg="#f3f6f8")
        content.grid(row=1, column=0, sticky="nsew", padx=18, pady=18)
        content.columnconfigure((0, 1, 2), weight=1)

        self.home_section(content, "Lançamentos", 0, [
            ("Consultar / editar ponto", "Editar batidas, faltas, débitos e créditos", self.show_manual_point, "#0b7285"),
            ("Importar batidas", "Ler arquivo TXT do relógio de ponto", self.import_attendance_file, "#157347"),
            ("Funcionários", "Consultar cadastros e códigos do relógio", self.show_employees, "#475569"),
        ])
        self.home_section(content, "Relatórios", 1, [
            ("Espelho individual", "Gerar PDF do funcionário selecionado", self.show_manual_point, "#7c3aed"),
            ("Todos os espelhos", "PDF único, um funcionário por página", self.show_manual_point, "#7c3aed"),
            ("Banco de horas", "Resumo anual e PDF de saldos", self.show_hour_bank, "#b45309"),
        ])
        self.home_section(content, "Sistema", 2, [
            ("Banco de dados", "Local ou PostgreSQL da empresa", self.show_parameters, "#334155"),
            ("Buscar atualizações", "Verificar nova versão no GitHub", self.check_updates, "#0369a1"),
            ("Sair", "Fechar o sistema", self.destroy, "#b42318"),
        ])

        self.bind("<F3>", lambda _event: self.not_ready())
        self.bind("<F4>", lambda _event: self.show_manual_point())
        self.bind("<F5>", lambda _event: self.destroy())

    def show_home_old(self):
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

    def home_section(self, parent, title, column, actions):
        section = tk.Frame(parent, bg="white", highlightbackground="#d6dde3", highlightthickness=1)
        section.grid(row=0, column=column, sticky="nsew", padx=8)
        section.columnconfigure(0, weight=1)

        tk.Label(section, text=title, bg="white", fg="#1f2933", font=("Arial", 15, "bold")).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))
        for index, (label, detail, command, color) in enumerate(actions, start=1):
            button = tk.Button(
                section,
                text=f"{label}\n{detail}",
                command=command,
                anchor="w",
                justify="left",
                bg="#f8fafc",
                fg="#111827",
                activebackground="#eef4f8",
                relief="flat",
                bd=0,
                padx=12,
                pady=8,
                font=("Arial", 10, "bold"),
            )
            button.grid(row=index, column=0, sticky="ew", padx=12, pady=5)
            marker = tk.Frame(section, bg=color, width=5, height=48)
            marker.grid(row=index, column=0, sticky="w", padx=(12, 0), pady=5)

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

        root = tk.Frame(self, bg="#f3f6f8")
        root.pack(fill="both", expand=True, padx=8, pady=8)

        title = tk.Label(root, text="Lançamento e Conferência de Ponto", bg="#f3f6f8", fg="#1f2933", font=("Arial", 22, "bold"))
        title.grid(row=0, column=0, columnspan=4, sticky="w")

        top_buttons = tk.Frame(root, bg="#f3f6f8")
        top_buttons.grid(row=0, column=4, columnspan=5, sticky="ew", padx=4)
        tk.Button(top_buttons, text="Alinhar dias", command=self.not_ready, width=14).pack(side="left", padx=4)
        tk.Button(top_buttons, text="Inserir almoço", command=self.insert_lunch, width=14).pack(side="left", padx=4)
        tk.Button(top_buttons, text="Zerar saldo", command=self.zero_balance, width=14).pack(side="left", padx=4)

        form = tk.LabelFrame(root, text="Filtros do ponto", bg="#f3f6f8", fg="#1f2933", font=("Arial", 10, "bold"))
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

        side = tk.LabelFrame(root, text="Relatórios e consultas", bg="#f3f6f8", fg="#1f2933", font=("Arial", 10, "bold"))
        side.grid(row=1, column=7, rowspan=3, sticky="ns", padx=8)
        tk.Button(side, text="Espelho individual", width=24, command=self.show_individual_conference).pack(pady=(8, 4), padx=8)
        tk.Button(side, text="PDF ponto de todos", width=24, command=self.export_all_point_pdf).pack(pady=4, padx=8)
        tk.Button(side, text="PDF ponto + banco horas", width=24, command=self.export_mass_reports_pdf).pack(pady=4, padx=8)
        tk.Button(side, text="Conferir período", width=24, command=self.load_entries).pack(pady=(24, 4), padx=8)
        tk.Button(side, text="Funcionários presentes", width=24, command=self.not_ready).pack(pady=4, padx=8)
        tk.Button(side, text="Funcionários faltantes", width=24, command=self.not_ready).pack(pady=4, padx=8)

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
        if not self.widget_exists("tree"):
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

    def collect_individual_conference(self, employee_id, month, year):
        employee = self.conn.execute("SELECT * FROM employees WHERE id = ?", (employee_id,)).fetchone()
        if not employee:
            return None

        rows = self.conn.execute(
            """
            SELECT *
            FROM time_entries
            WHERE employee_id = ? AND month = ? AND year = ?
            ORDER BY day, id
            """,
            (employee_id, month, year),
        ).fetchall()
        if not rows:
            return {"employee": employee, "month": month, "year": year, "rows": []}

        credit_total = 0
        debit_total = 0
        worked_total = 0
        expected_total = 0
        night_total = 0
        absence_total = 0
        balance = 0
        entries = []

        for row in rows:
            credit = entry_minutes(row, "credit_decimal", "credit_hours")
            debit = entry_minutes(row, "debit_decimal", "debit_hours")
            worked = minutes(row["worked_hours"])
            expected = minutes(row["expected_hours"])
            night = entry_minutes(row, "extra_night_decimal", None)
            balance += credit - debit
            absence = (row["absence"] or "").upper() == "S"
            note = row["note"] or ("Falta" if absence else "")

            credit_total += credit
            debit_total += debit
            worked_total += worked
            expected_total += expected
            night_total += night
            absence_total += 1 if absence else 0

            entries.append(
                {
                    "date": entry_date_label(row, month, year),
                    "weekday": weekday_label(row["work_date"], row["day"], month, year),
                    "entrada1": hhmm(row["entrada1"]),
                    "saida1": hhmm(row["saida1"]),
                    "entrada2": hhmm(row["entrada2"]),
                    "saida2": hhmm(row["saida2"]),
                    "entrada3": hhmm(row["entrada3"]),
                    "saida3": hhmm(row["saida3"]),
                    "entrada4": hhmm(row["entrada4"]),
                    "saida4": hhmm(row["saida4"]),
                    "expected": format_minutes(expected),
                    "worked": format_minutes(worked),
                    "note": note,
                    "credit": format_minutes(credit) if credit else "",
                    "debit": format_minutes(debit) if debit else "",
                    "night": format_minutes(night) if night else "",
                    "balance": format_minutes(balance),
                }
            )

        return {
            "employee": employee,
            "month": month,
            "year": year,
            "month_label": month_name(month),
            "rows": entries,
            "totals": {
                "days": len(rows),
                "worked": worked_total,
                "expected": expected_total,
                "credit": credit_total,
                "debit": debit_total,
                "balance": credit_total - debit_total,
                "night": night_total,
                "absences": absence_total,
            },
        }

    def current_individual_conference(self, title="Conferência Individual"):
        employee_id = self.selected_employee_id()
        if not employee_id:
            messagebox.showwarning(title, "Selecione um funcionário.")
            return None
        try:
            year = int(self.year_var.get() or date.today().year)
        except ValueError:
            messagebox.showwarning(title, "Informe um ano válido.")
            return None

        data = self.collect_individual_conference(employee_id, self.selected_month(), year)
        if not data or not data["rows"]:
            messagebox.showinfo(title, "Sem dados para o funcionário e mês selecionados.")
            return None
        return data

    def show_individual_conference(self):
        data = self.current_individual_conference()
        if not data:
            return

        window = tk.Toplevel(self)
        window.title("Conferência Individual")
        window.geometry("1120x680")
        window.configure(bg="#f3f6f8")
        window.transient(self)
        window.columnconfigure(0, weight=1)
        window.rowconfigure(2, weight=1)

        header = tk.Frame(window, bg="#0b7285", height=72)
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        header.grid_propagate(False)
        header.columnconfigure(0, weight=1)
        tk.Label(header, text="RELATÓRIO ESPELHO DE PONTO", bg="#0b7285", fg="white", font=("Arial", 18, "bold")).grid(row=0, column=0, sticky="w", padx=18, pady=(10, 0))
        tk.Label(header, text=f"{data['employee']['name']}  |  {data['month_label']} / {data['year']}  |  {data['employee']['department'] or 'Sem departamento'}", bg="#0b7285", fg="#d9f5f8", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="w", padx=18)
        tk.Label(header, text=f"Versão {APP_VERSION}", bg="#0b7285", fg="#d9f5f8", font=("Arial", 10, "bold")).grid(row=0, column=1, rowspan=2, sticky="e", padx=18)

        info = tk.Frame(window, bg="#f3f6f8")
        info.grid(row=1, column=0, columnspan=2, sticky="ew", padx=14, pady=12)
        info.columnconfigure(0, weight=1)
        employee_text = f"Funcionário: {data['employee']['name']}    ID relógio: {data['employee']['clock_id'] or '-'}    PIS: {data['employee']['pis'] or '-'}    CPF: {data['employee']['cpf'] or '-'}"
        tk.Label(info, text=employee_text, bg="#f3f6f8", fg="#1f2933", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w")

        summary = tk.Frame(info, bg="#f3f6f8")
        summary.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        summary_items = [
            ("Dias", str(data["totals"]["days"])),
            ("Previstas", format_minutes(data["totals"]["expected"])),
            ("Trabalhadas", format_minutes(data["totals"]["worked"])),
            ("Crédito", format_minutes(data["totals"]["credit"])),
            ("Débito", format_minutes(data["totals"]["debit"])),
            ("Saldo", format_minutes(data["totals"]["balance"])),
            ("Adicional", format_minutes(data["totals"]["night"])),
            ("Faltas", str(data["totals"]["absences"])),
        ]
        for index, (label, value) in enumerate(summary_items):
            card = tk.Frame(summary, bg="white", highlightbackground="#d6dde3", highlightthickness=1)
            card.grid(row=0, column=index, sticky="ew", padx=(0, 8))
            summary.columnconfigure(index, weight=1)
            color = "#0b7285"
            if label == "Débito" or (label == "Saldo" and data["totals"]["balance"] < 0):
                color = "#b42318"
            elif label == "Crédito":
                color = "#157347"
            tk.Label(card, text=label.upper(), bg="white", fg="#52616b", font=("Arial", 8, "bold")).pack(anchor="w", padx=10, pady=(7, 0))
            tk.Label(card, text=value, bg="white", fg=color, font=("Arial", 14, "bold")).pack(anchor="w", padx=10, pady=(0, 8))

        style = ttk.Style(window)
        style.configure("Conference.Treeview", rowheight=24, font=("Arial", 9))
        style.configure("Conference.Treeview.Heading", font=("Arial", 9, "bold"))
        columns = ("date", "weekday", "entrada1", "saida1", "entrada2", "saida2", "entrada3", "saida3", "entrada4", "saida4", "worked", "note", "debit", "credit", "night", "balance")
        tree = ttk.Treeview(window, columns=columns, show="headings", height=18, style="Conference.Treeview")
        headings = ["Data", "Dia", "Entrada", "Saída", "Entrada", "Saída", "Entrada", "Saída", "Entrada", "Saída", "Trab.", "Ocorrências", "Débito", "Crédito", "Adic.", "Saldo"]
        widths = [74, 54, 66, 66, 66, 66, 66, 66, 66, 66, 70, 180, 70, 70, 66, 72]
        for col, heading, width in zip(columns, headings, widths):
            tree.heading(col, text=heading)
            tree.column(col, width=width, minwidth=width, stretch=col == "note")
        tree.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=10, pady=6)
        tree.tag_configure("debit", foreground="#b42318")
        tree.tag_configure("credit", foreground="#157347")

        for row in data["rows"]:
            tags = []
            if row["debit"]:
                tags.append("debit")
            elif row["credit"]:
                tags.append("credit")
            tree.insert(
                "",
                "end",
                values=(
                    row["date"],
                    row["weekday"],
                    row["entrada1"],
                    row["saida1"],
                    row["entrada2"],
                    row["saida2"],
                    row["entrada3"],
                    row["saida3"],
                    row["entrada4"],
                    row["saida4"],
                    row["worked"],
                    row["note"],
                    row["debit"],
                    row["credit"],
                    row["night"],
                    row["balance"],
                ),
                tags=tags,
            )

        bottom = tk.Frame(window, bg="#f3f6f8")
        bottom.grid(row=3, column=0, columnspan=2, sticky="ew", padx=10, pady=8)
        tk.Label(bottom, text="Conferência pronta para impressão no formato espelho de ponto.", bg="#f3f6f8", fg="#555555").pack(side="left")
        tk.Button(bottom, text="Gerar PDF", width=14, command=lambda: self.export_individual_pdf(data)).pack(side="right", padx=(6, 0))
        tk.Button(bottom, text="Fechar", width=12, command=window.destroy).pack(side="right")

    def export_individual_pdf(self, data=None, open_after=True):
        if data is None:
            data = self.current_individual_conference("Impressão do Ponto")
            if not data:
                return None
        try:
            pdf_path = self.generate_individual_conference_pdf(data)
        except Exception as exc:
            messagebox.showerror("Impressão do Ponto", f"Não foi possível gerar o PDF.\n\n{exc}")
            return None

        if open_after:
            try:
                os.startfile(pdf_path)
            except OSError:
                pass
            messagebox.showinfo("Impressão do Ponto", f"PDF gerado para impressão:\n{pdf_path}")
        return pdf_path

    def export_all_point_pdf(self, open_after=True):
        try:
            month = self.selected_month() if hasattr(self, "month_var") else date.today().month
            year = int(self.year_var.get() if hasattr(self, "year_var") else date.today().year)
        except ValueError:
            messagebox.showwarning("Conferência Todos", "Informe um ano válido.")
            return None

        try:
            pdf_path, count = self.generate_all_point_pdf(month, year)
        except Exception as exc:
            messagebox.showerror("Conferência Todos", f"Não foi possível gerar o PDF em massa.\n\n{exc}")
            return None
        if count == 0:
            messagebox.showinfo("Conferência Todos", "Nenhum funcionário com ponto no mês selecionado.")
            return None
        if open_after:
            try:
                os.startfile(pdf_path)
            except OSError:
                pass
            messagebox.showinfo("Conferência Todos", f"PDF gerado com {count} funcionário(s):\n{pdf_path}")
        return pdf_path

    def export_mass_reports_pdf(self):
        try:
            month = self.selected_month() if hasattr(self, "month_var") else date.today().month
            year = int(self.year_var.get() if hasattr(self, "year_var") else date.today().year)
        except ValueError:
            messagebox.showwarning("Impressão em Massa", "Informe um ano válido.")
            return

        try:
            point_path, count = self.generate_all_point_pdf(month, year)
            bank_path = self.generate_hour_bank_pdf(self.collect_hour_bank(year, "TODOS"))
        except Exception as exc:
            messagebox.showerror("Impressão em Massa", f"Não foi possível gerar os PDFs.\n\n{exc}")
            return
        if count == 0:
            messagebox.showinfo("Impressão em Massa", "Nenhum funcionário com ponto no mês selecionado.")
            return
        try:
            os.startfile(point_path.parent)
        except OSError:
            pass
        messagebox.showinfo(
            "Impressão em Massa",
            f"PDFs gerados:\n\nPonto ({count} funcionário(s)):\n{point_path}\n\nBanco de Horas:\n{bank_path}",
        )

    def generate_all_point_pdf(self, month, year):
        from pypdf import PdfReader, PdfWriter

        employees = self.conn.execute("SELECT id, name FROM employees ORDER BY name").fetchall()
        report_dir = APP_DIR / "relatorios" / str(year) / f"{month:02d}"
        report_dir.mkdir(parents=True, exist_ok=True)
        output_path = report_dir / f"PONTO_TODOS_{year}_{month:02d}.pdf"
        writer = PdfWriter()
        count = 0

        for employee in employees:
            data = self.collect_individual_conference(employee["id"], month, year)
            if not data or not data["rows"]:
                continue
            employee_pdf = self.generate_individual_conference_pdf(data)
            reader = PdfReader(str(employee_pdf))
            for page in reader.pages:
                writer.add_page(page)
            count += 1

        if count:
            with output_path.open("wb") as file:
                writer.write(file)
        return output_path, count

    def generate_individual_conference_pdf(self, data):
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        report_dir = APP_DIR / "relatorios" / str(data["year"]) / f"{data['month']:02d}"
        report_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{safe_filename(data['employee']['name'])}_PONTO_{data['year']}_{data['month']:02d}.pdf"
        pdf_path = report_dir / filename

        doc = SimpleDocTemplate(str(pdf_path), pagesize=landscape(A4), leftMargin=8 * mm, rightMargin=8 * mm, topMargin=6 * mm, bottomMargin=6 * mm, title="Relatório Espelho de Ponto")
        styles = getSampleStyleSheet()
        story = []
        story.append(
            Table(
                [[Paragraph("<b>RELATÓRIO ESPELHO DE PONTO</b><br/>BOLSAS BABY", styles["Normal"]), Paragraph(f"<b>Competência:</b> {data['month_label']} / {data['year']}<br/><b>Gerado:</b> {datetime.now():%d/%m/%Y %H:%M}", styles["Normal"])]],
                colWidths=[194 * mm, 75 * mm],
                style=[
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#0b7285")),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
                    ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#0b7285")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ],
            )
        )
        story.append(Spacer(1, 3 * mm))

        employee = data["employee"]
        employee_rows = [
            ["Funcionário", employee["name"], "ID Relógio", employee["clock_id"] or "-", "Departamento", employee["department"] or "-"],
            ["CPF", employee["cpf"] or "-", "PIS", employee["pis"] or "-", "Função", employee["role"] or "-"],
        ]
        story.append(
            Table(
                employee_rows,
                colWidths=[24 * mm, 77 * mm, 24 * mm, 35 * mm, 28 * mm, 81 * mm],
                style=[
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#b9c4cc")),
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef3f6")),
                    ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#eef3f6")),
                    ("BACKGROUND", (4, 0), (4, -1), colors.HexColor("#eef3f6")),
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                    ("FONTNAME", (4, 0), (4, -1), "Helvetica-Bold"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ],
            )
        )
        story.append(Spacer(1, 2 * mm))

        headers = ["Data", "Dia", "Entrada", "Saída", "Entrada", "Saída", "Entrada", "Saída", "Entrada", "Saída", "Trab.", "Ocorrências", "Débito", "Crédito", "Adic.", "Saldo"]
        table_data = [headers]
        for row in data["rows"]:
            table_data.append([row["date"], row["weekday"], row["entrada1"], row["saida1"], row["entrada2"], row["saida2"], row["entrada3"], row["saida3"], row["entrada4"], row["saida4"], row["worked"], row["note"], row["debit"], row["credit"], row["night"], row["balance"]])
        totals = data["totals"]
        table_data.append(["TOTAL", "", "", "", "", "", "", "", "", "", format_minutes(totals["worked"]), f"Faltas: {totals['absences']}", format_minutes(totals["debit"]), format_minutes(totals["credit"]), format_minutes(totals["night"]), format_minutes(totals["balance"])])
        table = Table(table_data, repeatRows=1, colWidths=[16 * mm, 12 * mm, 15 * mm, 15 * mm, 15 * mm, 15 * mm, 15 * mm, 15 * mm, 15 * mm, 15 * mm, 16 * mm, 46 * mm, 16 * mm, 16 * mm, 15 * mm, 16 * mm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eef2")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#17324d")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 5.8),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#b9c4cc")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 1),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                    ("ALIGN", (0, 0), (10, -1), "CENTER"),
                    ("ALIGN", (12, 0), (-1, -1), "CENTER"),
                    ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f7fafc")),
                    ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 3 * mm))

        totals_text = f"Total de Horas Trabalhadas: {format_minutes(totals['worked'])}    Total de Atrasos/Débitos: {format_minutes(totals['debit'])}    Total de Horas Extras/Créditos: {format_minutes(totals['credit'])}    Adicional Noturno: {format_minutes(totals['night'])}    Saldo: {format_minutes(totals['balance'])}"
        story.append(Paragraph(totals_text, styles["Normal"]))
        story.append(Spacer(1, 5 * mm))
        story.append(Paragraph("Ass: ______________________________________________", styles["Normal"]))
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph(f"Eu, {employee['name']}, reconheço a exatidão das informações acima.", styles["Normal"]))
        doc.build(story)
        return pdf_path

    def show_individual_conference_old(self):
        employee_id = self.selected_employee_id()
        if not employee_id:
            messagebox.showwarning("Conferência Individual", "Selecione um funcionário.")
            return
        try:
            year = int(self.year_var.get() or date.today().year)
        except ValueError:
            messagebox.showwarning("Conferência Individual", "Informe um ano válido.")
            return

        month = self.selected_month()
        employee = self.conn.execute("SELECT * FROM employees WHERE id = ?", (employee_id,)).fetchone()
        rows = self.conn.execute(
            """
            SELECT *
            FROM time_entries
            WHERE employee_id = ? AND month = ? AND year = ?
            ORDER BY day, id
            """,
            (employee_id, month, year),
        ).fetchall()

        if not rows:
            messagebox.showinfo("Conferência Individual", "Sem dados para o funcionário e mês selecionados.")
            return

        credit_total = round(sum(float(row["credit_decimal"] or 0) * 60 for row in rows))
        debit_total = round(sum(float(row["debit_decimal"] or 0) * 60 for row in rows))
        worked_total = sum(minutes(row["worked_hours"]) for row in rows)
        night_total = round(sum(float(row["extra_night_decimal"] or 0) * 60 for row in rows))
        balance_total = credit_total - debit_total
        absence_total = sum(1 for row in rows if (row["absence"] or "").upper() == "S")

        month_label = next((label for number, label in MONTHS if int(number) == month), str(month))
        window = tk.Toplevel(self)
        window.title("Conferência Individual")
        window.geometry("980x620")
        window.configure(bg="#eeeeee")
        window.transient(self)
        window.columnconfigure(0, weight=1)
        window.rowconfigure(2, weight=1)

        tk.Label(
            window,
            text=f"Conferência Individual - {employee['name']}",
            bg="#eeeeee",
            fg="#555555",
            font=("Arial", 18, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=10, pady=(10, 2))
        tk.Label(
            window,
            text=f"{month_label} / {year}    Departamento: {employee['department'] or ''}",
            bg="#eeeeee",
            fg="#222222",
            font=("Arial", 10, "bold"),
        ).grid(row=1, column=0, sticky="w", padx=10, pady=(0, 8))

        summary = tk.Frame(window, bg="#eeeeee")
        summary.grid(row=0, column=1, rowspan=2, sticky="e", padx=10, pady=10)
        summary_items = [
            ("Dias", str(len(rows))),
            ("Horas Trabalhadas", format_minutes(worked_total)),
            ("Crédito", format_minutes(credit_total)),
            ("Débito", format_minutes(debit_total)),
            ("Saldo", format_minutes(balance_total)),
            ("Adicional", format_minutes(night_total)),
            ("Faltas", str(absence_total)),
        ]
        for index, (label, value) in enumerate(summary_items):
            tk.Label(summary, text=label, bg="#eeeeee", fg="#555555", font=("Arial", 9, "bold")).grid(row=index, column=0, sticky="e", padx=(0, 6))
            tk.Label(summary, text=value, bg="#fff8b8", fg="#111111", width=12, relief="solid", bd=1, font=("Arial", 10, "bold")).grid(row=index, column=1, sticky="ew", pady=1)

        columns = ("day", "entrada1", "saida1", "entrada2", "saida2", "entrada3", "saida3", "entrada4", "saida4", "worked", "credit", "debit", "night", "note")
        tree = ttk.Treeview(window, columns=columns, show="headings", height=18)
        headings = ["Dia", "Entra.1", "Saída1", "Entra.2", "Saída2", "Entra.3", "Saída3", "Entra.4", "Saída4", "Trabalhada", "Crédito", "Débito", "Adicional", "Obs"]
        widths = [45, 65, 65, 65, 65, 65, 65, 65, 65, 85, 70, 70, 75, 180]
        for col, heading, width in zip(columns, headings, widths):
            tree.heading(col, text=heading)
            tree.column(col, width=width, minwidth=width, stretch=col == "note")
        tree.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=10, pady=6)

        for row in rows:
            tree.insert(
                "",
                "end",
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
                    hhmm(row["worked_hours"]),
                    hhmm(row["credit_hours"]),
                    hhmm(row["debit_hours"]),
                    decimal_to_hhmm(row["extra_night_decimal"]),
                    row["note"] or "",
                ),
            )

        bottom = tk.Frame(window, bg="#eeeeee")
        bottom.grid(row=3, column=0, columnspan=2, sticky="ew", padx=10, pady=8)
        tk.Label(
            bottom,
            text="Base original: soma de credito, debito, horasdiad e adicionaln da tabela vendedor1.",
            bg="#eeeeee",
            fg="#555555",
        ).pack(side="left")
        tk.Button(bottom, text="Fechar", width=12, command=window.destroy).pack(side="right")

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
        tk.Button(filters, text="Gerar PDF", width=12, command=self.export_hour_bank_pdf).grid(row=1, column=4, padx=6, pady=4)
        tk.Button(filters, text="Voltar", width=12, command=self.show_home).grid(row=1, column=5, padx=6, pady=4)

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
        if not self.widget_exists("hour_bank_tree"):
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

    def collect_hour_bank(self, year, employee_filter="TODOS"):
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

        employee_list = list(employees.values())
        annual_credit = sum(sum(employee["credit"]) for employee in employee_list)
        annual_debit = sum(sum(employee["debit"]) for employee in employee_list)
        return {
            "year": year,
            "employee_filter": employee_filter,
            "employees": employee_list,
            "annual_credit": annual_credit,
            "annual_debit": annual_debit,
            "annual_balance": annual_credit - annual_debit,
        }

    def export_hour_bank_pdf(self, data=None, open_after=True):
        if data is None:
            try:
                year = int(self.bank_year_var.get() if hasattr(self, "bank_year_var") else date.today().year)
            except ValueError:
                messagebox.showwarning("Banco de Horas", "Informe um ano válido.")
                return None
            employee_filter = self.bank_employee_var.get() if hasattr(self, "bank_employee_var") else "TODOS"
            data = self.collect_hour_bank(year, employee_filter)
        try:
            pdf_path = self.generate_hour_bank_pdf(data)
        except Exception as exc:
            messagebox.showerror("Banco de Horas", f"Não foi possível gerar o PDF.\n\n{exc}")
            return None
        if open_after:
            try:
                os.startfile(pdf_path)
            except OSError:
                pass
            messagebox.showinfo("Banco de Horas", f"PDF gerado para impressão:\n{pdf_path}")
        return pdf_path

    def generate_hour_bank_pdf(self, data):
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        report_dir = APP_DIR / "relatorios" / str(data["year"]) / "banco_de_horas"
        report_dir.mkdir(parents=True, exist_ok=True)
        filter_name = "TODOS" if data["employee_filter"] == "TODOS" else safe_filename(data["employee_filter"].split(" - ", 1)[-1])
        pdf_path = report_dir / f"BANCO_DE_HORAS_{data['year']}_{filter_name}.pdf"

        doc = SimpleDocTemplate(str(pdf_path), pagesize=landscape(A4), leftMargin=8 * mm, rightMargin=8 * mm, topMargin=7 * mm, bottomMargin=7 * mm, title="Banco de Horas")
        styles = getSampleStyleSheet()
        story = []
        story.append(
            Table(
                [[Paragraph("<b>BANCO DE HORAS</b><br/>BOLSAS BABY", styles["Normal"]), Paragraph(f"<b>Ano:</b> {data['year']}<br/><b>Gerado:</b> {datetime.now():%d/%m/%Y %H:%M}", styles["Normal"])]],
                colWidths=[194 * mm, 75 * mm],
                style=[
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#0b7285")),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ],
            )
        )
        story.append(Spacer(1, 4 * mm))

        headers = ["Funcionário", "Tipo", *[label[:3].upper() for _number, label in MONTHS], "Total Ano"]
        table_data = [headers]
        for employee in data["employees"]:
            credits = employee["credit"]
            debits = employee["debit"]
            balance = [credit - debit for credit, debit in zip(credits, debits)]
            table_data.append([employee["name"], "HORAS EXTRAS", *[format_minutes(value) for value in credits], format_minutes(sum(credits))])
            table_data.append(["", "HORAS FALTANTES", *[format_minutes(value) for value in debits], format_minutes(sum(debits))])
            table_data.append(["", "TOTAL MÊS", *[format_minutes(value) for value in balance], format_minutes(sum(balance))])
        table_data.append(["TOTAL GERAL", "SALDO", *["" for _ in MONTHS], format_minutes(data["annual_balance"])])

        table = Table(table_data, repeatRows=1, colWidths=[44 * mm, 28 * mm, *([13 * mm] * 12), 24 * mm])
        styles_list = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eef2")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#17324d")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 6.6),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#b9c4cc")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (2, 0), (-1, -1), "CENTER"),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f7fafc")),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ]
        for row_index in range(1, len(table_data) - 1):
            kind = table_data[row_index][1]
            if kind == "HORAS EXTRAS":
                styles_list.append(("BACKGROUND", (0, row_index), (-1, row_index), colors.HexColor("#ecfdf3")))
            elif kind == "HORAS FALTANTES":
                styles_list.append(("BACKGROUND", (0, row_index), (-1, row_index), colors.HexColor("#fff1f0")))
            elif kind == "TOTAL MÊS":
                styles_list.append(("BACKGROUND", (0, row_index), (-1, row_index), colors.HexColor("#eef4ff")))
                styles_list.append(("FONTNAME", (0, row_index), (-1, row_index), "Helvetica-Bold"))
        table.setStyle(TableStyle(styles_list))
        story.append(table)
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph(f"Resumo {data['year']}: extras {format_minutes(data['annual_credit'])} | faltantes {format_minutes(data['annual_debit'])} | saldo {format_minutes(data['annual_balance'])}", styles["Normal"]))
        doc.build(story)
        return pdf_path

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
        if self.widget_exists("tree"):
            self.load_entries()
        return {"punches": len(punches), "days": updated_days, "unknown": len(unknown)}

    def widget_exists(self, name):
        widget = getattr(self, name, None)
        if widget is None:
            return False
        try:
            return bool(widget.winfo_exists())
        except tk.TclError:
            return False

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
        departments = [row["department"] for row in self.conn.execute("SELECT DISTINCT department FROM employees WHERE department IS NOT NULL AND department <> '' ORDER BY department")]
        messagebox.showinfo("Departamento", "\n".join(departments) or "Nenhum departamento cadastrado.")

    def show_parameters(self):
        window = tk.Toplevel(self)
        window.title("Parâmetros")
        window.geometry("560x420")
        window.configure(bg="#eeeeee")
        window.transient(self)
        window.columnconfigure(0, weight=1)

        db_config = self.app_config.get("database", {})
        mode_var = tk.StringVar(value=db_config.get("mode", "local"))
        host_var = tk.StringVar(value=db_config.get("host", "localhost"))
        port_var = tk.StringVar(value=str(db_config.get("port", 5432)))
        dbname_var = tk.StringVar(value=db_config.get("dbname", "ponto_funcionarios"))
        user_var = tk.StringVar(value=db_config.get("user", "ponto_app"))
        password_var = tk.StringVar(value=db_config.get("password", ""))

        tk.Label(window, text="Banco de Dados", bg="#eeeeee", fg="#555555", font=("Arial", 22, "bold")).grid(row=0, column=0, sticky="w", padx=14, pady=(14, 6))

        mode_frame = tk.LabelFrame(window, text="Modo de uso", bg="#eeeeee", font=("Arial", 10, "bold"))
        mode_frame.grid(row=1, column=0, sticky="ew", padx=14, pady=6)
        tk.Radiobutton(mode_frame, text=f"Banco local SQLite ({DB_PATH})", variable=mode_var, value="local", bg="#eeeeee").pack(anchor="w", padx=8, pady=3)
        tk.Radiobutton(mode_frame, text="Banco da empresa PostgreSQL", variable=mode_var, value="postgres", bg="#eeeeee").pack(anchor="w", padx=8, pady=3)

        form = tk.LabelFrame(window, text="PostgreSQL", bg="#eeeeee", font=("Arial", 10, "bold"))
        form.grid(row=2, column=0, sticky="ew", padx=14, pady=6)
        form.columnconfigure(1, weight=1)
        fields = [
            ("IP / nome do PC", host_var, False),
            ("Porta", port_var, False),
            ("Banco", dbname_var, False),
            ("Usuário", user_var, False),
            ("Senha", password_var, True),
        ]
        for index, (label, variable, secret) in enumerate(fields):
            tk.Label(form, text=label, bg="#eeeeee", font=("Arial", 9, "bold")).grid(row=index, column=0, sticky="w", padx=8, pady=3)
            tk.Entry(form, textvariable=variable, show="*" if secret else "", width=34).grid(row=index, column=1, sticky="ew", padx=8, pady=3)

        status_var = tk.StringVar(value=f"Conexão atual: {self.database_label()}")
        tk.Label(window, textvariable=status_var, bg="#eeeeee", fg="#333333", font=("Arial", 10, "bold")).grid(row=3, column=0, sticky="w", padx=14, pady=(8, 0))

        buttons = tk.Frame(window, bg="#eeeeee")
        buttons.grid(row=4, column=0, sticky="ew", padx=14, pady=14)

        def build_config():
            try:
                return postgres_config_from_values(mode_var.get(), host_var.get(), port_var.get(), dbname_var.get(), user_var.get(), password_var.get())
            except ValueError:
                messagebox.showwarning("Parâmetros", "Informe uma porta válida.")
                return None

        def test_connection():
            config = build_config()
            if not config:
                return
            try:
                conn = AppConnection(config["database"]["mode"], config["database"] if config["database"]["mode"] == "postgres" else {"path": DB_PATH})
                conn.execute("SELECT 1").fetchone()
                conn.close()
                messagebox.showinfo("Parâmetros", "Conexão testada com sucesso.")
            except Exception as exc:
                messagebox.showerror("Parâmetros", f"Falha ao conectar.\n\n{exc}")

        def save_config():
            config = build_config()
            if not config:
                return
            self.app_config = config
            save_app_config(self.app_config)
            self.reconnect_database()
            status_var.set(f"Conexão atual: {self.database_label()}")
            messagebox.showinfo("Parâmetros", "Configuração salva. O sistema já está usando o banco selecionado.")

        def migrate_current_sqlite():
            config = build_config()
            if not config or config["database"]["mode"] != "postgres":
                messagebox.showwarning("Migrar", "Selecione PostgreSQL para migrar.")
                return
            if not DB_PATH.exists():
                messagebox.showwarning("Migrar", f"Banco SQLite não encontrado:\n{DB_PATH}")
                return
            if not messagebox.askyesno("Migrar", "Migrar os funcionários e pontos do SQLite local para o PostgreSQL?\n\nA migração atualiza registros com o mesmo código."):
                return
            try:
                result = migrate_sqlite_to_postgres(DB_PATH, config["database"])
                messagebox.showinfo("Migrar", f"Migração concluída.\n\nFuncionários: {result['employees']}\nPontos: {result['entries']}")
            except Exception as exc:
                messagebox.showerror("Migrar", f"Não foi possível migrar.\n\n{exc}")

        tk.Button(buttons, text="Testar conexão", width=16, command=test_connection).pack(side="left", padx=(0, 6))
        tk.Button(buttons, text="Migrar SQLite atual", width=18, command=migrate_current_sqlite).pack(side="left", padx=6)
        tk.Button(buttons, text="Salvar e usar", width=14, command=save_config).pack(side="right")
        tk.Button(buttons, text="Fechar", width=10, command=window.destroy).pack(side="right", padx=6)

    def database_label(self):
        if getattr(self.conn, "kind", "local") == "postgres":
            db_config = self.app_config.get("database", {})
            return f"PostgreSQL {db_config.get('host')}:{db_config.get('port')}/{db_config.get('dbname')}"
        return f"SQLite local {DB_PATH}"

    def show_parameters_old(self):
        messagebox.showinfo("Parâmetros", f"Banco local:\n{DB_PATH}")

    def show_report(self):
        if not hasattr(self, "employee_var"):
            self.show_manual_point()
            return
        self.export_individual_pdf()
        return
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
                manifest = json.loads(response.read().decode("utf-8-sig").lstrip("\ufeff"))
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


def load_app_config():
    config = json.loads(json.dumps(DEFAULT_CONFIG))
    if CONFIG_PATH.exists():
        try:
            saved = json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))
            config["database"].update(saved.get("database", {}))
        except Exception:
            pass
    return config


def save_app_config(config):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")


def postgres_config_from_values(mode, host, port, dbname, user, password):
    return {
        "database": {
            "mode": mode,
            "host": host.strip() or "localhost",
            "port": int(port or 5432),
            "dbname": dbname.strip() or "ponto_funcionarios",
            "user": user.strip() or "ponto_app",
            "password": password,
        }
    }


def migrate_sqlite_to_postgres(sqlite_path, pg_config):
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    pg_conn = AppConnection("postgres", pg_config)
    try:
        if getattr(pg_conn, "raw", None):
            pg_conn.raw.autocommit = False

        pg_conn.execute(
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
        pg_conn.execute(
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

        employee_rows = sqlite_conn.execute("SELECT * FROM employees ORDER BY id").fetchall()
        entry_rows = sqlite_conn.execute("SELECT * FROM time_entries ORDER BY id").fetchall()

        employee_columns = [
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
        entry_columns = [
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

        employee_insert = f"""
            INSERT INTO employees ({', '.join(employee_columns)})
            VALUES ({', '.join(['?'] * len(employee_columns))})
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
        entry_insert = f"""
            INSERT INTO time_entries ({', '.join(entry_columns)})
            VALUES ({', '.join(['?'] * len(entry_columns))})
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
            pg_conn.execute(employee_insert, tuple(row[column] for column in employee_columns))
        for row in entry_rows:
            pg_conn.execute(entry_insert, tuple(row[column] for column in entry_columns))

        pg_conn.execute("SELECT setval(pg_get_serial_sequence('employees','id'), COALESCE((SELECT MAX(id) FROM employees), 1), true)")
        pg_conn.execute("SELECT setval(pg_get_serial_sequence('time_entries','id'), COALESCE((SELECT MAX(id) FROM time_entries), 1), true)")
        pg_conn.commit()
        return {"employees": len(employee_rows), "entries": len(entry_rows)}
    except Exception:
        pg_conn.rollback()
        raise
    finally:
        sqlite_conn.close()
        pg_conn.close()


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


def entry_minutes(row, decimal_key, time_key):
    if decimal_key:
        try:
            value = row[decimal_key]
            if value not in (None, ""):
                return round(float(value) * 60)
        except (KeyError, TypeError, ValueError):
            pass
    if time_key:
        try:
            return minutes(row[time_key])
        except (KeyError, TypeError):
            return 0
    return 0


def month_name(month):
    return next((label for number, label in MONTHS if int(number) == int(month)), str(month))


def entry_date_label(row, month, year):
    work_date = row["work_date"]
    if work_date:
        try:
            current = datetime.strptime(work_date, "%Y-%m-%d")
            if current.day == int(row["day"]) and current.month == int(month) and current.year == int(year):
                return current.strftime("%d/%m/%Y")
        except ValueError:
            pass
    return f"{int(row['day']):02d}/{int(month):02d}/{int(year)}"


def weekday_label(work_date, day, month, year):
    labels = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    try:
        if work_date:
            current = datetime.strptime(work_date, "%Y-%m-%d").date()
            if current.day != int(day) or current.month != int(month) or current.year != int(year):
                current = date(int(year), int(month), int(day))
        else:
            current = date(int(year), int(month), int(day))
        return labels[current.weekday()]
    except (TypeError, ValueError):
        return ""


def safe_filename(value):
    allowed = []
    for char in str(value).strip():
        if char.isalnum() or char in (" ", "-", "_"):
            allowed.append(char)
        else:
            allowed.append("_")
    name = "".join(allowed).strip().replace(" ", "_")
    while "__" in name:
        name = name.replace("__", "_")
    return name or "FUNCIONARIO"


if __name__ == "__main__":
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    app = PontoDesktop()
    app.mainloop()
