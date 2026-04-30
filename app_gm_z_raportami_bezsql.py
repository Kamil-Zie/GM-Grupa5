import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from pathlib import Path
import sqlite3
import csv

try:
    import pyodbc
except ImportError:
    pyodbc = None

try:
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    MATPLOTLIB_OK = True
except Exception:
    MATPLOTLIB_OK = False
    Figure = None
    FigureCanvasTkAgg = None

APP_DIR = Path(__file__).resolve().parent
DBFILE = APP_DIR / "gmsystem.db"
SQLFILE = APP_DIR / "gm_schema_and_data.sql"

# Zmień przed uruchomieniem:
# "sqlite", "sqlserver_1", "sqlserver_2"
ACTIVE_DB = "sqlite"

DB_CONFIG = {
    "sqlite": {
        "type": "sqlite",
        "database": DBFILE,
    },
    "sqlserver_1": {
        "type": "pyodbc",
        "driver": "ODBC Driver 17 for SQL Server",
        "server": r"localhost\SQLEXPRESS",
        "database": "GMSystem1",
        "trusted_connection": "yes",
        "uid": "",
        "pwd": "",
    },
    "sqlserver_2": {
        "type": "pyodbc",
        "driver": "ODBC Driver 17 for SQL Server",
        "server": r"localhost\SQLEXPRESS",
        "database": "GMSystem2",
        "trusted_connection": "yes",
        "uid": "",
        "pwd": "",
    },
}

def get_connection():
    cfg = DB_CONFIG[ACTIVE_DB]

    if cfg["type"] == "sqlite":
        conn = sqlite3.connect(cfg["database"])
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    if cfg["type"] == "pyodbc":
        if pyodbc is None:
            raise RuntimeError("Brak biblioteki pyodbc. Zainstaluj: pip install pyodbc")

        if str(cfg.get("trusted_connection", "yes")).lower() in ("yes", "true", "1"):
            conn_str = (
                f"DRIVER={{{cfg['driver']}}};"
                f"SERVER={cfg['server']};"
                f"DATABASE={cfg['database']};"
                "Trusted_Connection=yes;"
            )
        else:
            conn_str = (
                f"DRIVER={{{cfg['driver']}}};"
                f"SERVER={cfg['server']};"
                f"DATABASE={cfg['database']};"
                f"UID={cfg.get('uid', '')};"
                f"PWD={cfg.get('pwd', '')};"
            )

        return pyodbc.connect(conn_str)

    raise ValueError(f"Nieobsługiwany typ bazy: {cfg['type']}")

class MagazynApp:
    def __init__(self, root):
        self.root = root
        self.root.title("System GM - Gospodarka Magazynowa")
        self.root.geometry("1180x780")

        self.materialy_dict = {}
        self.magazyny_dict = {}
        self.current_chart_canvas = None
        self.current_figure = None
        self.chart_mode = "bar"

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.create_przyjecia_tab()
        self.create_wydania_tab()
        self.create_raporty_tab()

        self.load_combobox_data()
        self.load_combobox_data_for_wydania()
        self.refresh_przyjecia()
        self.refresh_wydania()

    def create_przyjecia_tab(self):
        self.przyjecia_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.przyjecia_frame, text="Przyjęcia")

        form_frame = ttk.LabelFrame(self.przyjecia_frame, text="Dodaj nowe przyjęcie", padding=10)
        form_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(form_frame, text="Materiał").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.przyjecia_material_combo = ttk.Combobox(form_frame, state="readonly", width=40)
        self.przyjecia_material_combo.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(form_frame, text="Ilość").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.przyjecia_ilosc_entry = ttk.Entry(form_frame, width=20)
        self.przyjecia_ilosc_entry.grid(row=1, column=1, sticky="w", padx=5, pady=5)

        ttk.Label(form_frame, text="Data operacji").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.przyjecia_data_entry = ttk.Entry(form_frame, width=20)
        self.przyjecia_data_entry.grid(row=2, column=1, sticky="w", padx=5, pady=5)
        self.przyjecia_data_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))

        ttk.Label(form_frame, text="Magazyn").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        self.przyjecia_magazyn_combo = ttk.Combobox(form_frame, state="readonly", width=30)
        self.przyjecia_magazyn_combo.grid(row=3, column=1, sticky="w", padx=5, pady=5)

        ttk.Label(form_frame, text="Dostawca").grid(row=4, column=0, sticky="w", padx=5, pady=5)
        self.przyjecia_dostawca_entry = ttk.Entry(form_frame, width=50)
        self.przyjecia_dostawca_entry.grid(row=4, column=1, padx=5, pady=5)

        ttk.Label(form_frame, text="Uwagi").grid(row=5, column=0, sticky="nw", padx=5, pady=5)
        self.przyjecia_uwagi_text = tk.Text(form_frame, height=3, width=50)
        self.przyjecia_uwagi_text.grid(row=5, column=1, padx=5, pady=5)

        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=6, column=0, columnspan=3, pady=10)
        ttk.Button(button_frame, text="Dodaj przyjęcie", command=self.add_przyjecie).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Odśwież", command=self.refresh_przyjecia).pack(side="left", padx=5)

        table_frame = ttk.LabelFrame(self.przyjecia_frame, text="Historia przyjęć", padding=10)
        table_frame.pack(fill="both", expand=True, padx=10, pady=10)
        scrollbar = ttk.Scrollbar(table_frame)
        scrollbar.pack(side="right", fill="y")

        cols = ("ID", "Materiał", "Ilość", "Data", "Magazyn", "Dostawca", "Uwagi")
        self.przyjecia_tree = ttk.Treeview(table_frame, columns=cols, show="headings", yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.przyjecia_tree.yview)
        for col in cols:
            self.przyjecia_tree.heading(col, text=col)
            self.przyjecia_tree.column(col, width=140)
        self.przyjecia_tree.pack(fill="both", expand=True)

    def create_wydania_tab(self):
        self.wydania_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.wydania_frame, text="Wydania")

        form_frame = ttk.LabelFrame(self.wydania_frame, text="Dodaj nowe wydanie", padding=10)
        form_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(form_frame, text="Materiał").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.wydania_material_combo = ttk.Combobox(form_frame, state="readonly", width=40)
        self.wydania_material_combo.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(form_frame, text="Ilość").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.wydania_ilosc_entry = ttk.Entry(form_frame, width=20)
        self.wydania_ilosc_entry.grid(row=1, column=1, sticky="w", padx=5, pady=5)

        ttk.Label(form_frame, text="Data operacji").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.wydania_data_entry = ttk.Entry(form_frame, width=20)
        self.wydania_data_entry.grid(row=2, column=1, sticky="w", padx=5, pady=5)
        self.wydania_data_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))

        ttk.Label(form_frame, text="Magazyn").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        self.wydania_magazyn_combo = ttk.Combobox(form_frame, state="readonly", width=30)
        self.wydania_magazyn_combo.grid(row=3, column=1, sticky="w", padx=5, pady=5)

        ttk.Label(form_frame, text="Zlec. pracownika").grid(row=4, column=0, sticky="w", padx=5, pady=5)
        self.wydania_pracownik_entry = ttk.Entry(form_frame, width=50)
        self.wydania_pracownik_entry.grid(row=4, column=1, padx=5, pady=5)

        ttk.Label(form_frame, text="Uwagi").grid(row=5, column=0, sticky="nw", padx=5, pady=5)
        self.wydania_uwagi_text = tk.Text(form_frame, height=3, width=50)
        self.wydania_uwagi_text.grid(row=5, column=1, padx=5, pady=5)

        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=6, column=0, columnspan=3, pady=10)
        ttk.Button(button_frame, text="Dodaj wydanie", command=self.add_wydanie).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Odśwież", command=self.refresh_wydania).pack(side="left", padx=5)

        table_frame = ttk.LabelFrame(self.wydania_frame, text="Historia wydań", padding=10)
        table_frame.pack(fill="both", expand=True, padx=10, pady=10)
        scrollbar = ttk.Scrollbar(table_frame)
        scrollbar.pack(side="right", fill="y")

        cols = ("ID", "Materiał", "Ilość", "Data", "Magazyn", "Pracownik", "Uwagi")
        self.wydania_tree = ttk.Treeview(table_frame, columns=cols, show="headings", yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.wydania_tree.yview)
        for col in cols:
            self.wydania_tree.heading(col, text=col)
            self.wydania_tree.column(col, width=140)
        self.wydania_tree.pack(fill="both", expand=True)

        self.load_combobox_data_for_wydania()
        self.refresh_wydania()

    def create_raporty_tab(self):
        self.raporty_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.raporty_frame, text="Raporty")

        ctrl_frame = ttk.LabelFrame(self.raporty_frame, text="Opcje raportu", padding=10)
        ctrl_frame.pack(fill="x", padx=10, pady=10)

        ttk.Button(ctrl_frame, text="1. Stan zapasu", command=self.raport_stan_zapasu).pack(side="left", padx=5)
        ttk.Button(ctrl_frame, text="2. Analiza miesięczna", command=self.raport_miesieczny).pack(side="left", padx=5)
        ttk.Button(ctrl_frame, text="3. Ruchy magazynowe", command=self.raport_ruchy).pack(side="left", padx=5)
        ttk.Button(ctrl_frame, text="4. Ranking produktów", command=self.raport_ranking).pack(side="left", padx=5)
        ttk.Button(ctrl_frame, text="5. Trend miesięczny", command=self.raport_trendy_miesieczne).pack(side="left", padx=5)
        ttk.Button(ctrl_frame, text="6. Obroty materiału", command=self.raport_obroty_materialu).pack(side="left", padx=5)
        ttk.Button(ctrl_frame, text="Tryb słupkowy", command=self.configure_bar_chart).pack(side="left", padx=5)
        ttk.Button(ctrl_frame, text="Tryb liniowy", command=self.configure_line_chart).pack(side="left", padx=5)
        ttk.Button(ctrl_frame, text="Eksportuj CSV", command=self.export_csv).pack(side="left", padx=5)

        ttk.Label(ctrl_frame, text="Materiał (dla pkt 6):").pack(side="left", padx=(10, 2))
        self.raport_material_combo = ttk.Combobox(ctrl_frame, state="readonly", width=30)
        self.raport_material_combo.pack(side="left", padx=5)

        self.chart_frame = ttk.LabelFrame(self.raporty_frame, text="Wykres", padding=10)
        self.chart_frame.pack(fill="both", expand=False, padx=10, pady=(0, 10))

        chart_controls = ttk.Frame(self.chart_frame)
        chart_controls.pack(fill="x", pady=(0, 8))

        ttk.Label(chart_controls, text="Metryka").grid(row=0, column=0, padx=4, pady=4, sticky="w")
        self.chart_metric_combo = ttk.Combobox(chart_controls, state="readonly", width=18, values=["Ilość", "Wartość", "Liczba operacji"])
        self.chart_metric_combo.grid(row=0, column=1, padx=4, pady=4)
        self.chart_metric_combo.set("Ilość")

        ttk.Label(chart_controls, text="Grupowanie").grid(row=0, column=2, padx=4, pady=4, sticky="w")
        self.chart_group_combo = ttk.Combobox(chart_controls, state="readonly", width=18, values=["Materiał", "Magazyn", "Miesiąc"])
        self.chart_group_combo.grid(row=0, column=3, padx=4, pady=4)
        self.chart_group_combo.set("Materiał")

        ttk.Label(chart_controls, text="Typ operacji").grid(row=0, column=4, padx=4, pady=4, sticky="w")
        self.chart_type_combo = ttk.Combobox(chart_controls, state="readonly", width=14, values=["Wszystkie", "Przyjcie", "Wydanie"])
        self.chart_type_combo.grid(row=0, column=5, padx=4, pady=4)
        self.chart_type_combo.set("Wszystkie")

        ttk.Label(chart_controls, text="Limit").grid(row=0, column=6, padx=4, pady=4, sticky="w")
        self.chart_limit_entry = ttk.Entry(chart_controls, width=6)
        self.chart_limit_entry.grid(row=0, column=7, padx=4, pady=4)
        self.chart_limit_entry.insert(0, "10")

        ttk.Button(chart_controls, text="Rysuj wykres", command=self.draw_embedded_chart).grid(row=0, column=8, padx=6, pady=4)
        ttk.Button(chart_controls, text="Wyczyść wykres", command=self.clear_chart).grid(row=0, column=9, padx=6, pady=4)

        self.chart_message = ttk.Label(self.chart_frame, text="Wybierz parametry i kliknij 'Rysuj wykres'.")
        self.chart_message.pack(anchor="w", pady=(0, 6))

        self.chart_canvas_holder = ttk.Frame(self.chart_frame, height=320)
        self.chart_canvas_holder.pack(fill="both", expand=True)
        self.chart_canvas_holder.pack_propagate(False)

        table_frame = ttk.LabelFrame(self.raporty_frame, text="Wyniki raportu", padding=10)
        table_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.raport_y_scroll = ttk.Scrollbar(table_frame)
        self.raport_y_scroll.pack(side="right", fill="y")
        self.raport_x_scroll = ttk.Scrollbar(table_frame, orient="horizontal")
        self.raport_x_scroll.pack(side="bottom", fill="x")

        cols = ("Lp.", "Materiał", "Magazyn", "Ilość", "Wartość", "Wyszczególnienie")
        self.raporty_tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=16, yscrollcommand=self.raport_y_scroll.set, xscrollcommand=self.raport_x_scroll.set)
        self.raport_y_scroll.config(command=self.raporty_tree.yview)
        self.raport_x_scroll.config(command=self.raporty_tree.xview)

        widths = {"Lp.": 50, "Materiał": 240, "Magazyn": 90, "Ilość": 140, "Wartość": 140, "Wyszczególnienie": 280}
        for col in cols:
            self.raporty_tree.heading(col, text=col)
            self.raporty_tree.column(col, width=widths[col], anchor="w")
        self.raporty_tree.pack(fill="both", expand=True)

    def load_combobox_data(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT MaterialID, Nazwa FROM Materialy ORDER BY Nazwa")
        materialy = cursor.fetchall()
        self.materialy_dict = {row[1]: row[0] for row in materialy}
        self.przyjecia_material_combo["values"] = list(self.materialy_dict.keys())
        self.raport_material_combo["values"] = list(self.materialy_dict.keys())

        cursor.execute("SELECT MagazynID, Kod, Opis FROM Magazyny ORDER BY Kod")
        magazyny = cursor.fetchall()
        self.magazyny_dict = {f"{row[1]} - {row[2]}": row[0] for row in magazyny}
        self.przyjecia_magazyn_combo["values"] = list(self.magazyny_dict.keys())
        conn.close()

    def load_combobox_data_for_wydania(self):
        self.wydania_material_combo["values"] = list(self.materialy_dict.keys())
        self.wydania_magazyn_combo["values"] = list(self.magazyny_dict.keys())

    def add_przyjecie(self):
        try:
            material_name = self.przyjecia_material_combo.get()
            magazyn_name = self.przyjecia_magazyn_combo.get()
            if not material_name:
                messagebox.showerror("Błąd", "Wybierz materiał.")
                return
            if not magazyn_name:
                messagebox.showerror("Błąd", "Wybierz magazyn.")
                return
            ilosc = int(self.przyjecia_ilosc_entry.get())
            if ilosc <= 0:
                raise ValueError("Ilość musi być większa od zera.")
            data = self.przyjecia_data_entry.get().strip()
            datetime.strptime(data, "%Y-%m-%d")
            material_id = self.materialy_dict[material_name]
            magazyn_id = self.magazyny_dict[magazyn_name]
            dostawca = self.przyjecia_dostawca_entry.get().strip()
            uwagi = self.przyjecia_uwagi_text.get("1.0", "end-1c").strip()
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO OperacjeMagazynowe (MaterialID, MagazynID, TypOperacji, Ilo, DataOperacji, Dostawca, ZlecPracownika, Uwagi) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (material_id, magazyn_id, "Przyjcie", ilosc, data, dostawca or None, None, uwagi or None),
            )
            conn.commit()
            conn.close()
            self.clear_przyjecie_form()
            self.refresh_przyjecia()
            messagebox.showinfo("OK", "Dodano przyjęcie.")
        except Exception as e:
            messagebox.showerror("Błąd", str(e))

    def get_available_stock(self, material_id, magazyn_id):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                COALESCE(SUM(CASE WHEN TypOperacji='Przyjcie' THEN Ilo ELSE 0 END), 0) -
                COALESCE(SUM(CASE WHEN TypOperacji='Wydanie' THEN Ilo ELSE 0 END), 0)
            FROM OperacjeMagazynowe
            WHERE MaterialID = ? AND MagazynID = ?
            """,
            (material_id, magazyn_id),
        )
        row = cur.fetchone()
        conn.close()
        return int(row[0] or 0)

    def add_wydanie(self):
        try:
            material_name = self.wydania_material_combo.get()
            magazyn_name = self.wydania_magazyn_combo.get()
            if not material_name:
                messagebox.showerror("Błąd", "Wybierz materiał.")
                return
            if not magazyn_name:
                messagebox.showerror("Błąd", "Wybierz magazyn.")
                return
            ilosc = int(self.wydania_ilosc_entry.get())
            if ilosc <= 0:
                raise ValueError("Ilość musi być większa od zera.")
            data = self.wydania_data_entry.get().strip()
            datetime.strptime(data, "%Y-%m-%d")
            material_id = self.materialy_dict[material_name]
            magazyn_id = self.magazyny_dict[magazyn_name]
            pracownik = self.wydania_pracownik_entry.get().strip()
            uwagi = self.wydania_uwagi_text.get("1.0", "end-1c").strip()

            dostepna_ilosc = self.get_available_stock(material_id, magazyn_id)
            if ilosc > dostepna_ilosc:
                raise ValueError(
                    f"Brak wystarczającego stanu magazynowego. Dostępna ilość: {dostepna_ilosc}, próba wydania: {ilosc}."
                )

            conn = get_connection()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO OperacjeMagazynowe (MaterialID, MagazynID, TypOperacji, Ilo, DataOperacji, Dostawca, ZlecPracownika, Uwagi) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (material_id, magazyn_id, "Wydanie", ilosc, data, None, pracownik or None, uwagi or None),
            )
            conn.commit()
            conn.close()
            self.clear_wydanie_form()
            self.refresh_wydania()
            messagebox.showinfo("OK", "Dodano wydanie.")
        except Exception as e:
            messagebox.showerror("Błąd", str(e))

    def clear_przyjecie_form(self):
        self.przyjecia_material_combo.set("")
        self.przyjecia_ilosc_entry.delete(0, tk.END)
        self.przyjecia_data_entry.delete(0, tk.END)
        self.przyjecia_data_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.przyjecia_magazyn_combo.set("")
        self.przyjecia_dostawca_entry.delete(0, tk.END)
        self.przyjecia_uwagi_text.delete("1.0", tk.END)

    def clear_wydanie_form(self):
        self.wydania_material_combo.set("")
        self.wydania_ilosc_entry.delete(0, tk.END)
        self.wydania_data_entry.delete(0, tk.END)
        self.wydania_data_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.wydania_magazyn_combo.set("")
        self.wydania_pracownik_entry.delete(0, tk.END)
        self.wydania_uwagi_text.delete("1.0", tk.END)

    def refresh_przyjecia(self):
        for item in self.przyjecia_tree.get_children():
            self.przyjecia_tree.delete(item)
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT o.OperacjaID, m.Nazwa, o.Ilo, o.DataOperacji, mag.Kod, o.Dostawca, o.Uwagi FROM OperacjeMagazynowe o JOIN Materialy m ON o.MaterialID=m.MaterialID JOIN Magazyny mag ON o.MagazynID=mag.MagazynID WHERE o.TypOperacji=? ORDER BY o.DataOperacji DESC, o.OperacjaID DESC",
            ("Przyjcie",),
        )
        for row in cur.fetchall():
            self.przyjecia_tree.insert("", "end", values=row)
        conn.close()

    def refresh_wydania(self):
        for item in self.wydania_tree.get_children():
            self.wydania_tree.delete(item)
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT o.OperacjaID, m.Nazwa, o.Ilo, o.DataOperacji, mag.Kod, o.ZlecPracownika, o.Uwagi FROM OperacjeMagazynowe o JOIN Materialy m ON o.MaterialID=m.MaterialID JOIN Magazyny mag ON o.MagazynID=mag.MagazynID WHERE o.TypOperacji=? ORDER BY o.DataOperacji DESC, o.OperacjaID DESC",
            ("Wydanie",),
        )
        for row in cur.fetchall():
            self.wydania_tree.insert("", "end", values=row)
        conn.close()

    def clear_report_table(self):
        for item in self.raporty_tree.get_children():
            self.raporty_tree.delete(item)

    def raport_stan_zapasu(self):
        self.clear_report_table()
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
                    SELECT m.Nazwa, mag.Kod,

                   SUM(CASE WHEN o.TypOperacji='Przyjcie' THEN o.Ilo ELSE -o.Ilo END) AS IloscAktualna,

                   SUM(CASE WHEN o.TypOperacji='Przyjcie' THEN o.Ilo * m.Cenajedn ELSE -o.Ilo * m.Cenajedn END) AS WartoscAktualna,

                   m.Cenajedn

            FROM OperacjeMagazynowe o

            JOIN Materialy m ON o.MaterialID = m.MaterialID

            JOIN Magazyny mag ON o.MagazynID = mag.MagazynID

            GROUP BY m.MaterialID, mag.MagazynID, m.Nazwa, mag.Kod, m.Cenajedn

            HAVING SUM(CASE WHEN o.TypOperacji='Przyjcie' THEN o.Ilo ELSE -o.Ilo END) > 0

            ORDER BY mag.Kod, m.Nazwa;
        """)
        total = 0.0
        for lp, row in enumerate(cur.fetchall(), 1):
            nazwa, magazyn, ilosc, wartosc, cena = row
            wartosc = float(wartosc or 0)
            total += wartosc
            self.raporty_tree.insert("", "end", values=(lp, nazwa, magazyn, f"{ilosc} szt.", f"{wartosc:.2f} PLN", f"Cena jedn. {cena:.2f} PLN"))
        self.raporty_tree.insert("", "end", values=("", "RAZEM", "", "", f"{total:.2f} PLN", ""))
        conn.close()

    def raport_miesieczny(self):
        self.clear_report_table()
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
                    SELECT strftime('%Y-%m', o.DataOperacji) AS Miesiac, m.Nazwa, mag.Kod,
                    SUM(CASE WHEN o.TypOperacji='Przyjcie' THEN o.Ilo ELSE 0 END) AS Przyjecia,
                    SUM(CASE WHEN o.TypOperacji='Wydanie' THEN o.Ilo ELSE 0 END) AS Wydania,
                    SUM(CASE WHEN o.TypOperacji='Przyjcie' THEN o.Ilo ELSE 0 END) - SUM(CASE WHEN o.TypOperacji='Wydanie' THEN o.Ilo ELSE 0 END) AS Saldo
                FROM OperacjeMagazynowe o
                JOIN Materialy m ON o.MaterialID = m.MaterialID
                JOIN Magazyny mag ON o.MagazynID = mag.MagazynID
                WHERE o.DataOperacji IS NOT NULL
                GROUP BY Miesiac, m.Nazwa, mag.Kod
                ORDER BY Miesiac DESC, mag.Kod ASC, m.Nazwa ASC;
              
        """)
        for lp, row in enumerate(cur.fetchall(), 1):
            miesiac, nazwa, magazyn, przyjecia, wydania, saldo = row
            self.raporty_tree.insert("", "end", values=(lp, nazwa, magazyn, f"P:{przyjecia} / W:{wydania}", f"Saldo: {saldo}", miesiac))
        conn.close()

    def raport_ruchy(self):
        self.clear_report_table()
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT o.DataOperacji, m.Nazwa, mag.Kod, o.TypOperacji, o.Ilo, m.Cenajedn,
            (o.Ilo * m.Cenajedn) AS wartosc,
                COALESCE(o.Dostawca, o.ZlecPracownika, '-') AS Szczegoly
                FROM OperacjeMagazynowe o
                JOIN Materialy m ON o.MaterialID = m.MaterialID
                JOIN Magazyny mag ON o.MagazynID = mag.MagazynID
                WHERE o.DataOperacji IS NOT NULL; 
        """)
        for lp, row in enumerate(cur.fetchall(), 1):
            data, nazwa, magazyn, typ, ilosc, cena, wartosc, szczegoly = row
            self.raporty_tree.insert("", "end", values=(lp, nazwa, magazyn, f"{typ}: {ilosc} szt.", f"{float(wartosc or 0):.2f} PLN", f"{data}; {szczegoly}"))
        conn.close()

    def raport_ranking(self):
        self.clear_report_table()
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
                    SELECT m.Nazwa,
                    COUNT(o.OperacjaID) AS liczba_op,
                    SUM(o.Ilo) AS laczna_ilosc,
                    SUM(o.Ilo * m.Cenajedn) AS laczna_wartosc
                FROM OperacjeMagazynowe o
                JOIN Materialy m ON o.MaterialID = m.MaterialID
                WHERE o.TypOperacji = 'Wydanie'
                GROUP BY m.Nazwa
                ORDER BY laczna_ilosc DESC, m.Nazwa ASC;
        """)
        for lp, row in enumerate(cur.fetchall(), 1):
            nazwa, liczba_op, laczna_ilosc, laczna_wartosc = row
            self.raporty_tree.insert("", "end", values=(lp, nazwa, "-", f"{laczna_ilosc} szt.", f"{float(laczna_wartosc or 0):.2f} PLN", f"Liczba operacji: {liczba_op}"))
        conn.close()

    def raport_trendy_miesieczne(self):
        self.clear_report_table()
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT strftime('%Y-%m', DataOperacji) AS Miesiac,
                   SUM(CASE WHEN TypOperacji = 'Przyjcie' THEN Ilo ELSE 0 END) AS Przyjecia,
                   SUM(CASE WHEN TypOperacji = 'Wydanie' THEN Ilo ELSE 0 END) AS Wydania
            FROM OperacjeMagazynowe
            WHERE DataOperacji IS NOT NULL
            GROUP BY Miesiac
            ORDER BY Miesiac ASC;
        """)
        results = cur.fetchall()
        months, p_values, w_values = [], [], []
        
        for lp, row in enumerate(results, 1):
            miesiac, przyjecia, wydania = row
            months.append(miesiac)
            p_values.append(float(przyjecia or 0))
            w_values.append(float(wydania or 0))
            self.raporty_tree.insert("", "end", values=(lp, "TREND ZBIORCZY", "-", f"P:{przyjecia} / W:{wydania}", "-", miesiac))
        conn.close()

        if results:
            self.draw_two_line_chart("Trend miesięczny (Przyjęcia vs Wydania)", months, p_values, w_values)

    def raport_obroty_materialu(self):
        material_name = self.raport_material_combo.get()
        if not material_name:
            messagebox.showwarning("Uwaga", "Wybierz materiał do raportu obrotów.")
            return
        
        material_id = self.materialy_dict[material_name]
        self.clear_report_table()
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT strftime('%Y-%m', DataOperacji) AS Miesiac,
                   SUM(CASE WHEN TypOperacji = 'Przyjcie' THEN Ilo ELSE 0 END) AS Przyjecia,
                   SUM(CASE WHEN TypOperacji = 'Wydanie' THEN Ilo ELSE 0 END) AS Wydania
            FROM OperacjeMagazynowe
            WHERE MaterialID = ? AND DataOperacji IS NOT NULL
            GROUP BY Miesiac
            ORDER BY Miesiac ASC;
        """, (material_id,))
        
        results = cur.fetchall()
        months, p_values, w_values = [], [], []
        for lp, row in enumerate(results, 1):
            miesiac, przyjecia, wydania = row
            months.append(miesiac)
            p_values.append(float(przyjecia or 0))
            w_values.append(float(wydania or 0))
            obrot = (przyjecia or 0) + (wydania or 0)
            self.raporty_tree.insert("", "end", values=(lp, material_name, "-", f"P:{przyjecia} / W:{wydania}", f"Obrót: {obrot}", miesiac))
        conn.close()

        if results:
            self.draw_two_line_chart(f"Obroty materiału: {material_name}", months, p_values, w_values)

    def draw_two_line_chart(self, title, x_labels, y1_values, y2_values):
        if not MATPLOTLIB_OK:
            messagebox.showerror("Brak biblioteki", "Matplotlib nie jest dostępny.")
            return

        self.clear_chart()
        fig = Figure(figsize=(8.8, 3.6), dpi=100)
        ax = fig.add_subplot(111)

        # Wykresy liniowe z punktami (marker='o')
        ax.plot(x_labels, y1_values, marker="o", linestyle="-", linewidth=2, color="#2a6fdb", label="Przyjęcia")
        ax.plot(x_labels, y2_values, marker="s", linestyle="--", linewidth=2, color="#e67e22", label="Wydania")

        ax.set_title(title)
        ax.set_xlabel("Miesiąc")
        ax.set_ylabel("Ilość")
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        for label in ax.get_xticklabels():
            label.set_rotation(35)
            label.set_horizontalalignment("right")

        fig.tight_layout()
        self.current_figure = fig
        self.current_chart_canvas = FigureCanvasTkAgg(fig, master=self.chart_canvas_holder)
        self.current_chart_canvas.draw_idle()
        self.current_chart_canvas.get_tk_widget().pack(fill="both", expand=True)
        self.chart_message.config(text=f"Wyświetlono wykres porównawczy: {title}")
        self.root.update_idletasks()

    def export_csv(self):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                        SELECT m.Nazwa AS Material, mag.Kod AS Magazyn,
                        SUM(CASE WHEN o.TypOperacji='Przyjcie' THEN o.Ilo ELSE -o.Ilo END) AS Ilosc,
                        SUM(CASE WHEN o.TypOperacji='Przyjcie' THEN o.Ilo * m.Cenajedn ELSE -o.Ilo * m.Cenajedn END) AS Wartosc
                        FROM OperacjeMagazynowe o
                        JOIN Materialy m ON o.MaterialID = m.MaterialID
                        JOIN Magazyny mag ON o.MagazynID = mag.MagazynID
                        GROUP BY m.Nazwa, mag.Kod
                        ORDER BY mag.Kod, m.Nazwa;
            """)
            filename = APP_DIR / f"raport_zapasu_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            with open(filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Materiał", "Magazyn", "Ilość", "Wartość PLN"])
                writer.writerows(cur.fetchall())
            conn.close()
            messagebox.showinfo("Sukces", f"Raport wyeksportowany do:\n{filename}")
        except Exception as e:
            messagebox.showerror("Błąd", str(e))

    def configure_bar_chart(self):
        self.chart_mode = "bar"
        self.chart_message.config(text="Wybrano tryb słupkowy. Kliknij 'Rysuj wykres'.")

    def configure_line_chart(self):
        self.chart_mode = "line"
        self.chart_message.config(text="Wybrano tryb liniowy. Kliknij 'Rysuj wykres'.")

    def clear_chart(self):
        if self.current_chart_canvas is not None:
            try:
                self.current_chart_canvas.get_tk_widget().pack_forget()
                self.current_chart_canvas.get_tk_widget().destroy()
            except Exception:
                pass
            self.current_chart_canvas = None
        if self.current_figure is not None:
            try:
                self.current_figure.clear()
            except Exception:
                pass
            self.current_figure = None
        for child in self.chart_canvas_holder.winfo_children():
            child.destroy()
        self.chart_message.config(text="Wykres wyczyszczony.")
        self.root.update_idletasks()

    def draw_embedded_chart(self):
        if not MATPLOTLIB_OK:
            messagebox.showerror("Brak biblioteki", "Matplotlib nie jest dostępny. Zainstaluj pakiet matplotlib.")
            return

        metric_label = self.chart_metric_combo.get()
        group_label = self.chart_group_combo.get()
        type_label = self.chart_type_combo.get()
        try:
            limit = max(1, int(self.chart_limit_entry.get().strip()))
        except Exception:
            limit = 10

        metric_map = {"Ilość": "Ilo", "Wartość": "wartosc", "Liczba operacji": "liczba"}
        metric = metric_map.get(metric_label, "Ilo")

        if group_label == "Miesiąc":
            xexpr = "strftime('%Y-%m', o.DataOperacji)"
            xlabel = "Miesiąc"
            order_expr = "x ASC"
        elif group_label == "Magazyn":
            xexpr = "mag.Kod"
            xlabel = "Magazyn"
            order_expr = "y DESC, x ASC"
        else:
            xexpr = "m.Nazwa"
            xlabel = "Materiał"
            order_expr = "y DESC, x ASC"

        if metric == "Ilo":
            agg = "SUM(o.Ilo)"
            ylabel = "Ilość"
        elif metric == "wartosc":
            agg = "SUM(o.Ilo * m.Cenajedn)"
            ylabel = "Wartość"
        else:
            agg = "COUNT(o.OperacjaID)"
            ylabel = "Liczba operacji"

        where_clause = ""
        params = []
        if type_label in ("Przyjcie", "Wydanie"):
            where_clause = "WHERE o.TypOperacji = ?"
            params.append(type_label)

        query = f"""
            SELECT {xexpr} AS x, {agg} AS y
            FROM OperacjeMagazynowe o
            JOIN Materialy m ON m.MaterialID = o.MaterialID
            JOIN Magazyny mag ON mag.MagazynID = o.MagazynID
            {where_clause}
            GROUP BY x
            ORDER BY {order_expr}
            LIMIT ?
        """
        params.append(limit)

        conn = get_connection()
        cur = conn.cursor()
        cur.execute(query, params)
        rows = cur.fetchall()
        conn.close()

        if not rows:
            messagebox.showwarning("Brak danych", "Brak danych do wygenerowania wykresu.")
            return

        self.clear_chart()

        x_values = [r[0] for r in rows]
        y_values = [float(r[1] or 0) for r in rows]

        fig = Figure(figsize=(8.8, 3.6), dpi=100)
        ax = fig.add_subplot(111)

        if self.chart_mode == "bar":
            ax.bar(x_values, y_values, color="#2a6fdb")
            ax.set_title(f"Wykres słupkowy: {metric_label} wg {group_label}")
        else:
            ax.plot(x_values, y_values, marker="o", linewidth=2.0, color="#0f766e")
            ax.set_title(f"Wykres liniowy: {metric_label} wg {group_label}")

        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.grid(axis="y", alpha=0.25)
        for label in ax.get_xticklabels():
            label.set_rotation(35)
            label.set_horizontalalignment("right")

        fig.tight_layout()
        self.current_figure = fig
        self.current_chart_canvas = FigureCanvasTkAgg(fig, master=self.chart_canvas_holder)
        self.current_chart_canvas.draw_idle()
        widget = self.current_chart_canvas.get_tk_widget()
        widget.pack(fill="both", expand=True)
        widget.update_idletasks()
        self.chart_message.config(text=f"Wyświetlono wykres {self.chart_mode} dla: {metric_label} / {group_label}.")
        self.root.update_idletasks()


def main():
    root = tk.Tk()
    app = MagazynApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

'''
Zadanie 1. Napisz zapytanie SQL aby wyświetlać raporty dla funkcji: raport_stan_zapasu, raport_miesieczny, raport_ruchy, raport_ranking i export_csv.


Zadanie 2. Napisz zapytanie SQL wyświetlające materiały o niskim stanie magazynowym. 
Stan oblicz jako suma przyjęć minus suma wydań dla każdego materiału w każdym magazynie. 
Wyświetl nazwę materiału, magazyn, sumę przyjęć, sumę wydań i stan końcowy. 
Pokaż tylko te pozycje, dla których stan jest niższy niż 20. Wynik posortuj rosnąco według stanu.

Zadanie 3. Napisz zapytanie SQL tworzące ranking materiałów o największym ruchu magazynowym. 
Przez ruch rozumiej sumę wszystkich ilości z operacji przyjęć i wydań. Wyświetl nazwę materiału, 
liczbę operacji, sumę przyjęć, sumę wydań oraz łączny ruch. Wynik posortuj malejąco według łącznego ruchu.
W wersji rozszerzonej dodaj pozycję rankingową.

Zadania dla grup projektowych

Zadanie 4: przygotuj raport trendów miesięcznych dla operacji przyjęć i wydań. 
Oblicz dla każdego miesiąca łączną ilość przyjęć i wydań, a następnie przedstaw wynik w tabeli oraz na wykresie liniowym lub słupkowym.

Zadanie 5: przygotuj raport obrotów magazynowych według materiału. 
Dla dowolnego ateriału oblicz sumę przyjęć, sumę wydań i łączny obrót miesiąc po miesiącu, a wynik pokaż w formie wykresu słupkowego.



'''
