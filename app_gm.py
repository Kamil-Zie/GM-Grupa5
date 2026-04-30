import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from pathlib import Path
import sqlite3
import csv
import sys

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
SQLFILE = APP_DIR / "gm_schema_and_data_extended.sql"

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


def database_has_required_tables():
    if not DBFILE.exists():
        return False
    try:
        conn = sqlite3.connect(DBFILE)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Materialy'")
        ok = cur.fetchone() is not None
        conn.close()
        return ok
    except sqlite3.Error:
        return False


class MagazynApp:
    def __init__(self, root):
        self.root = root
        self.root.title("System GM - Gospodarka Magazynowa")
        self.root.geometry("1200x780")

        self.materialy_dict = {}
        self.magazyny_dict = {}
        self.current_chart_canvas = None
        self.current_figure = None
        self.chart_mode = "bar"

        self.create_header()

        self.main_container = ttk.Frame(self.root)
        self.main_container.pack(fill="both", expand=True, padx=20, pady=10)

        self.sidebar_frame = ttk.Frame(self.main_container, width=200)
        self.sidebar_frame.pack(side="right", fill="y", padx=(20, 0))

        self.notebook = ttk.Notebook(self.main_container)
        self.notebook.pack(side="left", fill="both", expand=True)

        self.setup_theme()
        self.create_sidebar()

        self.create_przyjecia_tab()
        self.create_wydania_tab()
        self.create_kartoteka_tab()
        self.create_stan_zapasu_tab()
        self.create_inwentaryzacja_tab()
        self.create_raporty_tab()

        self.load_combobox_data()
        self.refresh_przyjecia()
        self.refresh_wydania()

    def create_header(self):
        self.header_frame = tk.Frame(self.root, height=60)
        self.header_frame.pack(fill="x", side="top")
        self.header_frame.pack_propagate(False)

        self.title_label = tk.Label(
            self.header_frame,
            text="Gospodarka Magazynowa GM",
            font=('Segoe UI', 16, 'bold')
        )
        self.title_label.pack(side="left", padx=20, pady=15)

    def create_header(self):
        self.header_frame = tk.Frame(self.root, height=60)
        self.header_frame.pack(fill="x", side="top")
        self.header_frame.pack_propagate(False)

        self.title_label = tk.Label(self.header_frame, text="Gospodarka Magazynowa GM", font=('Segoe UI', 16, 'bold'))
        self.title_label.pack(side="left", padx=20, pady=15)

    def setup_theme(self):
        self.style = ttk.Style(self.root)
        self.style.theme_use('clam')
        self.change_theme("Jasny")

    def create_sidebar(self):
        ttk.Label(self.sidebar_frame, text="Ustawienia", font=('Segoe UI', 12, 'bold')).pack(pady=(0, 15), anchor="w")
        ttk.Label(self.sidebar_frame, text="Motyw aplikacji:").pack(anchor="w", pady=(0, 5))

        self.theme_var = tk.StringVar(value="Jasny")
        themes = [("Jasny (Domyślny)", "Jasny"), ("Ciemny (Dark Mode)", "Ciemny"), ("Firmowy Niebieski", "Niebieski")]

        for text, mode in themes:
            ttk.Radiobutton(
                self.sidebar_frame,
                text=text,
                value=mode,
                variable=self.theme_var,
                command=lambda: self.change_theme(self.theme_var.get())
            ).pack(anchor="w", pady=5)

        ttk.Separator(self.sidebar_frame, orient="horizontal").pack(fill="x", pady=20)

        ttk.Label(self.sidebar_frame, text="Użytkownik:", font=('Segoe UI', 10, 'bold')).pack(anchor="w", pady=(0, 5))
        ttk.Label(self.sidebar_frame, text="Admin_Magazyn_01").pack(anchor="w")

        ttk.Separator(self.sidebar_frame, orient="horizontal").pack(fill="x", pady=20)

        ttk.Label(self.sidebar_frame, text="Baza danych:", font=('Segoe UI', 10, 'bold')).pack(anchor="w", pady=(0, 5))
        ttk.Label(self.sidebar_frame, text=ACTIVE_DB).pack(anchor="w")

    def change_theme(self, mode):
        if mode == "Jasny":
            colors = {
                "bg_main": "#f0f2f5", "bg_frame": "#ffffff", "fg_main": "#333333",
                "header_bg": "#1a1a1a", "header_fg": "#ffffff",
                "tab_bg": "#e4e6eb", "accent": "#0056b3", "accent_hover": "#004494",
                "tree_sel_bg": "#e6f2ff", "tree_sel_fg": "#000000", "border": "#d1d5db"
            }
        elif mode == "Ciemny":
            colors = {
                "bg_main": "#121212", "bg_frame": "#1e1e1e", "fg_main": "#e0e0e0",
                "header_bg": "#000000", "header_fg": "#ffffff",
                "tab_bg": "#2d2d2d", "accent": "#007acc", "accent_hover": "#005c99",
                "tree_sel_bg": "#004c99", "tree_sel_fg": "#ffffff", "border": "#333333"
            }
        elif mode == "Niebieski":
            colors = {
                "bg_main": "#e6f2ff", "bg_frame": "#ffffff", "fg_main": "#002b5e",
                "header_bg": "#003366", "header_fg": "#ffffff",
                "tab_bg": "#cce5ff", "accent": "#004080", "accent_hover": "#00264d",
                "tree_sel_bg": "#66b2ff", "tree_sel_fg": "#ffffff", "border": "#99ccff"
            }

        self.apply_colors(colors)

    def apply_colors(self, colors):
        default_font = ('Segoe UI', 10)
        heading_font = ('Segoe UI', 11, 'bold')

        self.root.configure(bg=colors["bg_main"])
        self.header_frame.configure(bg=colors["header_bg"])
        self.title_label.configure(bg=colors["header_bg"], fg=colors["header_fg"])

        self.style.configure(".", font=default_font, background=colors["bg_frame"], foreground=colors["fg_main"])
        self.style.configure("TFrame", background=colors["bg_main"])

        self.style.configure("TNotebook", background=colors["bg_main"], borderwidth=0)
        self.style.configure("TNotebook.Tab", background=colors["tab_bg"], foreground=colors["fg_main"],
                              padding=[20, 8], font=default_font, borderwidth=0)
        self.style.map("TNotebook.Tab",
                       background=[("selected", colors["bg_frame"])],
                       foreground=[("selected", colors["accent"])],
                       font=[("selected", heading_font)])

        self.style.configure("TButton", padding=8, relief="flat", background=colors["accent"],
                              foreground="white", font=heading_font)
        self.style.map("TButton", background=[("active", colors["accent_hover"])])

        self.style.configure("TLabelframe", background=colors["bg_frame"], borderwidth=1,
                              relief="solid", bordercolor=colors["border"])
        self.style.configure("TLabelframe.Label", font=heading_font, background=colors["bg_frame"],
                              foreground=colors["fg_main"], padding=[0, 10])

        self.style.configure("Treeview", background=colors["bg_frame"], fieldbackground=colors["bg_frame"],
                              foreground=colors["fg_main"], rowheight=30, borderwidth=0)
        self.style.configure("Treeview.Heading", font=heading_font, background=colors["tab_bg"],
                              foreground=colors["fg_main"], relief="flat", padding=[0, 5])
        self.style.map("Treeview",
                       background=[('selected', colors["tree_sel_bg"])],
                       foreground=[('selected', colors["tree_sel_fg"])])

        try:
            if hasattr(self, 'przyjecia_uwagi_text'):
                self.przyjecia_uwagi_text.configure(bg=colors["bg_frame"], fg=colors["fg_main"],
                                                    insertbackground=colors["fg_main"])
            if hasattr(self, 'wydania_uwagi_text'):
                self.wydania_uwagi_text.configure(bg=colors["bg_frame"], fg=colors["fg_main"],
                                                  insertbackground=colors["fg_main"])
        except Exception:
            pass


    def create_przyjecia_tab(self):
        self.przyjecia_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.przyjecia_frame, text="Przyjęcia")

        form_frame = ttk.LabelFrame(self.przyjecia_frame, text="Dodaj nowe przyjęcie", padding=20)
        form_frame.pack(fill="x", padx=15, pady=15)

        ttk.Label(form_frame, text="Materiał:").grid(row=0, column=0, sticky="w", padx=10, pady=8)
        self.przyjecia_material_combo = ttk.Combobox(form_frame, state="readonly", width=40)
        self.przyjecia_material_combo.grid(row=0, column=1, padx=10, pady=8, sticky="w")

        ttk.Label(form_frame, text="Ilość:").grid(row=1, column=0, sticky="w", padx=10, pady=8)
        self.przyjecia_ilosc_entry = ttk.Entry(form_frame, width=20)
        self.przyjecia_ilosc_entry.grid(row=1, column=1, sticky="w", padx=10, pady=8)

        ttk.Label(form_frame, text="Data operacji:").grid(row=2, column=0, sticky="w", padx=10, pady=8)
        self.przyjecia_data_entry = ttk.Entry(form_frame, width=20)
        self.przyjecia_data_entry.grid(row=2, column=1, sticky="w", padx=10, pady=8)
        self.przyjecia_data_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))

        ttk.Label(form_frame, text="Magazyn:").grid(row=3, column=0, sticky="w", padx=10, pady=8)
        self.przyjecia_magazyn_combo = ttk.Combobox(form_frame, state="readonly", width=30)
        self.przyjecia_magazyn_combo.grid(row=3, column=1, sticky="w", padx=10, pady=8)

        ttk.Label(form_frame, text="Dostawca:").grid(row=4, column=0, sticky="w", padx=10, pady=8)
        self.przyjecia_dostawca_entry = ttk.Entry(form_frame, width=50)
        self.przyjecia_dostawca_entry.grid(row=4, column=1, sticky="w", padx=10, pady=8)

        ttk.Label(form_frame, text="Uwagi:").grid(row=5, column=0, sticky="nw", padx=10, pady=8)
        self.przyjecia_uwagi_text = tk.Text(form_frame, height=3, width=48, font=('Segoe UI', 10), bd=1, relief="solid")
        self.przyjecia_uwagi_text.grid(row=5, column=1, padx=10, pady=8, sticky="w")

        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=6, column=0, columnspan=2, pady=15, sticky="e")
        ttk.Button(button_frame, text="Odśwież", command=self.refresh_przyjecia).pack(side="left", padx=10)
        ttk.Button(button_frame, text="Zarejestruj przyjęcie", command=self.add_przyjecie).pack(side="left")

        table_frame = ttk.LabelFrame(self.przyjecia_frame, text="Historia przyjęć", padding=15)
        table_frame.pack(fill="both", expand=True, padx=15, pady=5)

        scrollbar = ttk.Scrollbar(table_frame)
        scrollbar.pack(side="right", fill="y")

        cols = ("ID", "Materiał", "Ilość", "Data", "Magazyn", "Dostawca", "Uwagi")
        self.przyjecia_tree = ttk.Treeview(table_frame, columns=cols, show="headings", yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.przyjecia_tree.yview)

        for col in cols:
            self.przyjecia_tree.heading(col, text=col)
            self.przyjecia_tree.column(col, width=120, anchor="center" if col not in ("Materiał", "Uwagi") else "w")

        self.przyjecia_tree.pack(fill="both", expand=True)


    def create_wydania_tab(self):
        self.wydania_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.wydania_frame, text="Wydania")

        form_frame = ttk.LabelFrame(self.wydania_frame, text="Zarejestruj nowe wydanie", padding=20)
        form_frame.pack(fill="x", padx=15, pady=15)

        ttk.Label(form_frame, text="Materiał:").grid(row=0, column=0, sticky="w", padx=10, pady=8)
        self.wydania_material_combo = ttk.Combobox(form_frame, state="readonly", width=40)
        self.wydania_material_combo.grid(row=0, column=1, padx=10, pady=8, sticky="w")

        ttk.Label(form_frame, text="Ilość:").grid(row=1, column=0, sticky="w", padx=10, pady=8)
        self.wydania_ilosc_entry = ttk.Entry(form_frame, width=20)
        self.wydania_ilosc_entry.grid(row=1, column=1, sticky="w", padx=10, pady=8)

        ttk.Label(form_frame, text="Data operacji:").grid(row=2, column=0, sticky="w", padx=10, pady=8)
        self.wydania_data_entry = ttk.Entry(form_frame, width=20)
        self.wydania_data_entry.grid(row=2, column=1, sticky="w", padx=10, pady=8)
        self.wydania_data_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))

        ttk.Label(form_frame, text="Magazyn:").grid(row=3, column=0, sticky="w", padx=10, pady=8)
        self.wydania_magazyn_combo = ttk.Combobox(form_frame, state="readonly", width=30)
        self.wydania_magazyn_combo.grid(row=3, column=1, sticky="w", padx=10, pady=8)

        ttk.Label(form_frame, text="Odbiorca:").grid(row=4, column=0, sticky="w", padx=10, pady=8)
        self.wydania_odbiorca_entry = ttk.Entry(form_frame, width=50)
        self.wydania_odbiorca_entry.grid(row=4, column=1, sticky="w", padx=10, pady=8)

        ttk.Label(form_frame, text="Uwagi:").grid(row=5, column=0, sticky="nw", padx=10, pady=8)
        self.wydania_uwagi_text = tk.Text(form_frame, height=3, width=48, font=('Segoe UI', 10), bd=1, relief="solid")
        self.wydania_uwagi_text.grid(row=5, column=1, padx=10, pady=8, sticky="w")

        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=6, column=0, columnspan=2, pady=15, sticky="e")
        ttk.Button(button_frame, text="Odśwież", command=self.refresh_wydania).pack(side="left", padx=10)
        ttk.Button(button_frame, text="Zarejestruj wydanie", command=self.add_wydanie).pack(side="left")

        table_frame = ttk.LabelFrame(self.wydania_frame, text="Historia wydań", padding=15)
        table_frame.pack(fill="both", expand=True, padx=15, pady=5)

        scrollbar = ttk.Scrollbar(table_frame)
        scrollbar.pack(side="right", fill="y")

        cols = ("ID", "Materiał", "Ilość", "Data", "Magazyn", "Odbiorca", "Uwagi")
        self.wydania_tree = ttk.Treeview(table_frame, columns=cols, show="headings", yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.wydania_tree.yview)

        for col in cols:
            self.wydania_tree.heading(col, text=col)
            self.wydania_tree.column(col, width=120, anchor="center" if col not in ("Materiał", "Uwagi") else "w")

        self.wydania_tree.pack(fill="both", expand=True)



    def create_kartoteka_tab(self):
        self.kartoteka_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.kartoteka_frame, text="Kartoteka")

        paned_window = ttk.PanedWindow(self.kartoteka_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill="both", expand=True, padx=15, pady=15)

        material_frame = ttk.Frame(paned_window)
        paned_window.add(material_frame, weight=1)

        mat_form = ttk.LabelFrame(material_frame, text="Dodaj nowy materiał", padding=15)
        mat_form.pack(fill="x", pady=(0, 10), padx=(0, 5))

        ttk.Label(mat_form, text="Nazwa:").grid(row=0, column=0, sticky="w", pady=5)
        self.mat_nazwa_entry = ttk.Entry(mat_form, width=30)
        self.mat_nazwa_entry.grid(row=0, column=1, pady=5, padx=5)

        ttk.Label(mat_form, text="Jednostka:").grid(row=1, column=0, sticky="w", pady=5)
        self.mat_jednostka_entry = ttk.Entry(mat_form, width=15)
        self.mat_jednostka_entry.grid(row=1, column=1, sticky="w", pady=5, padx=5)

        ttk.Label(mat_form, text="Cena jedn. (PLN):").grid(row=2, column=0, sticky="w", pady=5)
        self.mat_cena_entry = ttk.Entry(mat_form, width=15)
        self.mat_cena_entry.grid(row=2, column=1, sticky="w", pady=5, padx=5)

        ttk.Button(mat_form, text="Zapisz materiał", command=self.add_material).grid(row=3, column=1, sticky="e", pady=10)

        mat_table_frame = ttk.LabelFrame(material_frame, text="Lista materiałów", padding=10)
        mat_table_frame.pack(fill="both", expand=True, padx=(0, 5))

        self.mat_tree = ttk.Treeview(mat_table_frame, columns=("ID", "Nazwa", "Jednostka", "Cena"), show="headings")
        self.mat_tree.heading("ID", text="ID")
        self.mat_tree.heading("Nazwa", text="Nazwa")
        self.mat_tree.heading("Jednostka", text="J.m.")
        self.mat_tree.heading("Cena", text="Cena")
        self.mat_tree.column("ID", width=40, anchor="center")
        self.mat_tree.column("Nazwa", width=150)
        self.mat_tree.column("Jednostka", width=50, anchor="center")
        self.mat_tree.column("Cena", width=70, anchor="e")
        self.mat_tree.pack(fill="both", expand=True)

        magazyn_frame = ttk.Frame(paned_window)
        paned_window.add(magazyn_frame, weight=1)

        mag_form = ttk.LabelFrame(magazyn_frame, text="Dodaj nowy magazyn", padding=15)
        mag_form.pack(fill="x", pady=(0, 10), padx=(5, 0))

        ttk.Label(mag_form, text="Kod magazynu:").grid(row=0, column=0, sticky="w", pady=5)
        self.mag_kod_entry = ttk.Entry(mag_form, width=15)
        self.mag_kod_entry.grid(row=0, column=1, sticky="w", pady=5, padx=5)

        ttk.Label(mag_form, text="Opis/Lokalizacja:").grid(row=1, column=0, sticky="w", pady=5)
        self.mag_opis_entry = ttk.Entry(mag_form, width=30)
        self.mag_opis_entry.grid(row=1, column=1, pady=5, padx=5)

        ttk.Button(mag_form, text="Zapisz magazyn", command=self.add_magazyn).grid(row=2, column=1, sticky="e", pady=10)

        mag_table_frame = ttk.LabelFrame(magazyn_frame, text="Lista magazynów", padding=10)
        mag_table_frame.pack(fill="both", expand=True, padx=(5, 0))

        self.mag_tree = ttk.Treeview(mag_table_frame, columns=("ID", "Kod", "Opis"), show="headings")
        self.mag_tree.heading("ID", text="ID")
        self.mag_tree.heading("Kod", text="Kod")
        self.mag_tree.heading("Opis", text="Opis")
        self.mag_tree.column("ID", width=40, anchor="center")
        self.mag_tree.column("Kod", width=80, anchor="center")
        self.mag_tree.column("Opis", width=180)
        self.mag_tree.pack(fill="both", expand=True)

        self.refresh_kartoteka()



    def create_stan_zapasu_tab(self):
        self.stan_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.stan_frame, text="Aktualny stan zapasu")

        filter_frame = ttk.LabelFrame(self.stan_frame, text="Filtrowanie", padding=15)
        filter_frame.pack(fill="x", padx=15, pady=10)

        controls_frame = ttk.Frame(filter_frame)
        controls_frame.pack(fill="x")

        ttk.Label(controls_frame, text="Magazyn:").pack(side="left", padx=(0, 5))
        self.stan_filter_magazyn = ttk.Combobox(controls_frame, state="readonly", width=15)
        self.stan_filter_magazyn.pack(side="left", padx=(0, 15))

        ttk.Label(controls_frame, text="Produkt:").pack(side="left", padx=(0, 5))
        self.stan_filter_produkt = ttk.Entry(controls_frame, width=25)
        self.stan_filter_produkt.pack(side="left", padx=(0, 15))

        ttk.Button(controls_frame, text="Filtruj", command=self.refresh_stan_zapasu).pack(side="left", padx=(0, 5))
        ttk.Button(controls_frame, text="Wyczyść", command=self.clear_stan_filters).pack(side="left", padx=(0, 5))

        table_frame = ttk.Frame(self.stan_frame)
        table_frame.pack(fill="both", expand=True, padx=15, pady=5)

        cols = ("Materiał", "Magazyn", "Ilość", "Jednostka", "Cena jedn.", "Wartość zapasu", "Lokalizacja")
        self.stan_tree = ttk.Treeview(table_frame, columns=cols, show="headings")

        column_widths = {
            "Materiał": 250, "Magazyn": 100, "Ilość": 80,
            "Jednostka": 80, "Cena jedn.": 100, "Wartość zapasu": 120, "Lokalizacja": 150
        }

        for col in cols:
            self.stan_tree.heading(col, text=col)
            self.stan_tree.column(col, width=column_widths.get(col, 100),
                                  anchor="center" if col != "Materiał" else "w")

        self.stan_tree.pack(fill="both", expand=True)

        self.update_stan_filter_combos()
        self.refresh_stan_zapasu()

    def update_stan_filter_combos(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT Kod FROM Magazyny ORDER BY Kod")
        magazyny = ["Wszystkie"] + [row[0] for row in cursor.fetchall()]
        self.stan_filter_magazyn["values"] = magazyny
        self.stan_filter_magazyn.set("Wszystkie")
        conn.close()

    def clear_stan_filters(self):
        self.stan_filter_magazyn.set("Wszystkie")
        self.stan_filter_produkt.delete(0, tk.END)
        self.refresh_stan_zapasu()

    def refresh_stan_zapasu(self):
        for item in self.stan_tree.get_children():
            self.stan_tree.delete(item)

        mag_filter = self.stan_filter_magazyn.get()
        prod_filter = self.stan_filter_produkt.get().strip()

        conn = get_connection()
        cursor = conn.cursor()
        sql = """
            SELECT
                m.Nazwa,
                mag.Kod,
                pl.ilosc,
                m.Jednostka,
                m.Cenajedn,
                (pl.ilosc * m.Cenajedn) AS Wartosc,
                COALESCE(lm.strefa || ' ' || lm.regal || '-' || lm.polka || '-' || lm.pozycja, 'Brak') AS Lokalizacja
            FROM ProduktyLokalizacje pl
            JOIN Materialy m ON pl.id_produktu = m.MaterialID
            JOIN LokalizacjeMagazynowe lm ON pl.id_lokalizacji = lm.id_lokalizacji
            JOIN Magazyny mag ON lm.MagazynID = mag.MagazynID
            WHERE 1=1
        """
        params = []
        if mag_filter != "Wszystkie":
            sql += " AND mag.Kod = ?"
            params.append(mag_filter)

        if prod_filter:
            sql += " AND m.Nazwa LIKE ?"
            params.append(f"%{prod_filter}%")

        sql += " ORDER BY m.Nazwa, mag.Kod"

        cursor.execute(sql, params)

        for row in cursor.fetchall():
            formatted_row = list(row)
            formatted_row[4] = f"{row[4]:.2f} zł"
            formatted_row[5] = f"{row[5]:.2f} zł"
            self.stan_tree.insert("", "end", values=formatted_row)

        conn.close()


    def create_inwentaryzacja_tab(self):
        self.inwentaryzacja_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.inwentaryzacja_frame, text="Inwentaryzacja")

        form_frame = ttk.LabelFrame(self.inwentaryzacja_frame, text="Nowy wpis inwentaryzacyjny", padding=20)
        form_frame.pack(fill="x", padx=15, pady=15)

        ttk.Label(form_frame, text="Produkt i Lokalizacja:").grid(row=0, column=0, sticky="w", padx=10, pady=8)
        self.inv_prod_loc_combo = ttk.Combobox(form_frame, state="readonly", width=60)
        self.inv_prod_loc_combo.grid(row=0, column=1, padx=10, pady=8)

        ttk.Label(form_frame, text="Ilość rzeczywista:").grid(row=1, column=0, sticky="w", padx=10, pady=8)
        self.inv_ilosc_entry = ttk.Entry(form_frame, width=20)
        self.inv_ilosc_entry.grid(row=1, column=1, sticky="w", padx=10, pady=8)

        ttk.Label(form_frame, text="Pracownik:").grid(row=2, column=0, sticky="w", padx=10, pady=8)
        self.inv_pracownik_combo = ttk.Combobox(form_frame, state="readonly", width=40)
        self.inv_pracownik_combo.grid(row=2, column=1, sticky="w", padx=10, pady=8)

        ttk.Label(form_frame, text="Uwagi:").grid(row=3, column=0, sticky="nw", padx=10, pady=8)
        self.inv_uwagi_entry = ttk.Entry(form_frame, width=60)
        self.inv_uwagi_entry.grid(row=3, column=1, padx=10, pady=8)

        ttk.Button(form_frame, text="Zapisz inwentaryzację", command=self.save_inwentaryzacja).grid(
            row=4, column=1, pady=15, sticky="e", padx=10)

        table_frame = ttk.LabelFrame(self.inwentaryzacja_frame, text="Historia inwentaryzacji", padding=15)
        table_frame.pack(fill="both", expand=True, padx=15, pady=5)

        cols = ("Data", "Produkt", "Lokalizacja", "Systemowa", "Rzeczywista", "Różnica", "Pracownik", "Status")
        self.inv_tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        for col in cols:
            self.inv_tree.heading(col, text=col)
            self.inv_tree.column(col, width=100, anchor="center")

        self.inv_tree.column("Produkt", width=200, anchor="w")
        self.inv_tree.pack(fill="both", expand=True)

        self.load_inventory_data()
        self.refresh_inwentaryzacja()

    def load_inventory_data(self):
        conn = get_connection()
        cursor = conn.cursor()

        sql = """
            SELECT pl.id_produktu_lokalizacji, m.Nazwa, mag.Kod, lm.strefa, lm.regal, lm.polka, pl.ilosc
            FROM ProduktyLokalizacje pl
            JOIN Materialy m ON pl.id_produktu = m.MaterialID
            JOIN LokalizacjeMagazynowe lm ON pl.id_lokalizacji = lm.id_lokalizacji
            JOIN Magazyny mag ON lm.MagazynID = mag.MagazynID
        """
        cursor.execute(sql)
        self.inv_prod_loc_dict = {}
        values = []
        for row in cursor.fetchall():
            label = f"{row[1]} (Mag: {row[2]}, Lok: {row[3]} {row[4]}-{row[5]}) [Stan: {row[6]}]"
            self.inv_prod_loc_dict[label] = {
                "id_pl": row[0],
                "system_qty": row[6],
                "material_id": None,
                "location_id": None
            }
            cursor2 = conn.cursor()
            cursor2.execute(
                "SELECT id_produktu, id_lokalizacji FROM ProduktyLokalizacje WHERE id_produktu_lokalizacji=?",
                (row[0],)
            )
            ids = cursor2.fetchone()
            self.inv_prod_loc_dict[label]["material_id"] = ids[0]
            self.inv_prod_loc_dict[label]["location_id"] = ids[1]
            values.append(label)

        self.inv_prod_loc_combo["values"] = values

        cursor.execute("SELECT id_pracownika, imie, nazwisko FROM Pracownicy")
        workers = cursor.fetchall()
        self.pracownicy_dict = {f"{r[1]} {r[2]}": r[0] for r in workers}
        self.inv_pracownik_combo["values"] = list(self.pracownicy_dict.keys())

        conn.close()

    def save_inwentaryzacja(self):
        try:
            label = self.inv_prod_loc_combo.get()
            if not label:
                raise ValueError("Wybierz produkt i lokalizację.")

            ilosc_rzecz = int(self.inv_ilosc_entry.get())
            pracownik_name = self.inv_pracownik_combo.get()
            if not pracownik_name:
                raise ValueError("Wybierz pracownika.")

            data = self.inv_prod_loc_dict[label]
            pracownik_id = self.pracownicy_dict[pracownik_name]

            conn = get_connection()
            cursor = conn.cursor()
            sql = """
                INSERT INTO Inwentaryzacja
                (id_produktu, id_lokalizacji, id_pracownika, data_inwentaryzacji,
                 ilosc_systemowa, ilosc_rzeczywista, status, uwagi)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(sql, (
                data["material_id"],
                data["location_id"],
                pracownik_id,
                datetime.now().strftime("%Y-%m-%d"),
                data["system_qty"],
                ilosc_rzecz,
                "Zatwierdzona",
                self.inv_uwagi_entry.get()
            ))

            conn.commit()
            conn.close()
            messagebox.showinfo("Sukces", "Pomyślnie zapisano wynik inwentaryzacji.")
            self.refresh_inwentaryzacja()
        except Exception as e:
            messagebox.showerror("Błąd", str(e))

    def refresh_inwentaryzacja(self):
        for item in self.inv_tree.get_children():
            self.inv_tree.delete(item)

        conn = get_connection()
        cursor = conn.cursor()
        sql = """
            SELECT i.data_inwentaryzacji, m.Nazwa, lm.strefa || ' ' || lm.regal,
                   i.ilosc_systemowa, i.ilosc_rzeczywista, i.roznica, p.nazwisko, i.status
            FROM Inwentaryzacja i
            JOIN Materialy m ON i.id_produktu = m.MaterialID
            JOIN LokalizacjeMagazynowe lm ON i.id_lokalizacji = lm.id_lokalizacji
            JOIN Pracownicy p ON i.id_pracownika = p.id_pracownika
            ORDER BY i.data_inwentaryzacji DESC
        """
        cursor.execute(sql)
        for row in cursor.fetchall():
            self.inv_tree.insert("", "end", values=row)
        conn.close()


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
        self.chart_metric_combo = ttk.Combobox(chart_controls, state="readonly", width=18,
                                               values=["Ilość", "Wartość", "Liczba operacji"])
        self.chart_metric_combo.grid(row=0, column=1, padx=4, pady=4)
        self.chart_metric_combo.set("Ilość")

        ttk.Label(chart_controls, text="Grupowanie").grid(row=0, column=2, padx=4, pady=4, sticky="w")
        self.chart_group_combo = ttk.Combobox(chart_controls, state="readonly", width=18,
                                              values=["Materiał", "Magazyn", "Miesiąc"])
        self.chart_group_combo.grid(row=0, column=3, padx=4, pady=4)
        self.chart_group_combo.set("Materiał")

        ttk.Label(chart_controls, text="Typ operacji").grid(row=0, column=4, padx=4, pady=4, sticky="w")
        self.chart_type_combo = ttk.Combobox(chart_controls, state="readonly", width=14,
                                             values=["Wszystkie", "Przyjcie", "Wydanie"])
        self.chart_type_combo.grid(row=0, column=5, padx=4, pady=4)
        self.chart_type_combo.set("Wszystkie")

        ttk.Label(chart_controls, text="Limit").grid(row=0, column=6, padx=4, pady=4, sticky="w")
        self.chart_limit_entry = ttk.Entry(chart_controls, width=6)
        self.chart_limit_entry.grid(row=0, column=7, padx=4, pady=4)
        self.chart_limit_entry.insert(0, "10")

        ttk.Button(chart_controls, text="Rysuj wykres", command=self.draw_embedded_chart).grid(
            row=0, column=8, padx=6, pady=4)
        ttk.Button(chart_controls, text="Wyczyść wykres", command=self.clear_chart).grid(
            row=0, column=9, padx=6, pady=4)

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
        self.raporty_tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=16,
                                         yscrollcommand=self.raport_y_scroll.set,
                                         xscrollcommand=self.raport_x_scroll.set)
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

        if hasattr(self, 'przyjecia_material_combo'):
            self.przyjecia_material_combo["values"] = list(self.materialy_dict.keys())
        if hasattr(self, 'wydania_material_combo'):
            self.wydania_material_combo["values"] = list(self.materialy_dict.keys())
        if hasattr(self, 'raport_material_combo'):
            self.raport_material_combo["values"] = list(self.materialy_dict.keys())

        cursor.execute("SELECT MagazynID, Kod, Opis FROM Magazyny ORDER BY Kod")
        magazyny = cursor.fetchall()
        self.magazyny_dict = {f"{row[1]} - {row[2]}": row[0] for row in magazyny}

        if hasattr(self, 'przyjecia_magazyn_combo'):
            self.przyjecia_magazyn_combo["values"] = list(self.magazyny_dict.keys())
        if hasattr(self, 'wydania_magazyn_combo'):
            self.wydania_magazyn_combo["values"] = list(self.magazyny_dict.keys())

        conn.close()


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
            cursor = conn.cursor()
            sql = (
                "INSERT INTO OperacjeMagazynowe "
                "(MaterialID, MagazynID, TypOperacji, Ilo, DataOperacji, Dostawca, ZlecPracownika, Uwagi) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
            )
            cursor.execute(sql, (material_id, magazyn_id, "Przyjęcie", ilosc, data, dostawca, None, uwagi))
            conn.commit()
            conn.close()

            messagebox.showinfo("Sukces", "Pomyślnie zarejestrowano przyjęcie.")
            self.clear_przyjecie_form()
            self.refresh_przyjecia()
            self.refresh_stan_zapasu()
        except ValueError as e:
            messagebox.showerror("Błąd danych", str(e))
        except sqlite3.Error as e:
            messagebox.showerror("Błąd bazy", str(e))
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

    def refresh_przyjecia(self):
        for item in self.przyjecia_tree.get_children():
            self.przyjecia_tree.delete(item)

        conn = get_connection()
        cursor = conn.cursor()
        sql = (
            "SELECT o.OperacjaID, m.Nazwa, o.Ilo, o.DataOperacji, mag.Kod, o.Dostawca, o.Uwagi "
            "FROM OperacjeMagazynowe o "
            "JOIN Materialy m ON o.MaterialID = m.MaterialID "
            "JOIN Magazyny mag ON o.MagazynID = mag.MagazynID "
            "WHERE o.TypOperacji IN ('Przyjcie', 'Przyjęcie') "
            "ORDER BY o.DataOperacji DESC, o.OperacjaID DESC"
        )
        cursor.execute(sql)
        for row in cursor.fetchall():
            self.przyjecia_tree.insert("", "end", values=row)
        conn.close()


    def get_available_stock(self, material_id, magazyn_id):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                COALESCE(SUM(CASE WHEN TypOperacji IN ('Przyjcie', 'Przyjęcie') THEN Ilo ELSE 0 END), 0) -
                COALESCE(SUM(CASE WHEN TypOperacji = 'Wydanie' THEN Ilo ELSE 0 END), 0)
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
                raise ValueError("Proszę wybrać materiał.")
            if not magazyn_name:
                raise ValueError("Proszę wybrać magazyn.")

            try:
                ilosc = int(self.wydania_ilosc_entry.get())
                if ilosc <= 0:
                    raise ValueError
            except ValueError:
                raise ValueError("Ilość musi być poprawną liczbą całkowitą większą od zera.")

            data = self.wydania_data_entry.get().strip()
            datetime.strptime(data, "%Y-%m-%d")

            material_id = self.materialy_dict[material_name]
            magazyn_id = self.magazyny_dict[magazyn_name]
            odbiorca = self.wydania_odbiorca_entry.get().strip()
            uwagi = self.wydania_uwagi_text.get("1.0", "end-1c").strip()

            dostepna_ilosc = self.get_available_stock(material_id, magazyn_id)
            if ilosc > dostepna_ilosc:
                raise ValueError(
                    f"Niewystarczający stan magazynowy. Dostępna ilość: {dostepna_ilosc}, próba wydania: {ilosc}."
                )

            conn = get_connection()
            cursor = conn.cursor()

            sql_insert = """
                INSERT INTO OperacjeMagazynowe
                (MaterialID, MagazynID, TypOperacji, Ilo, DataOperacji, Dostawca, ZlecPracownika, Uwagi)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(sql_insert, (material_id, magazyn_id, "Wydanie", ilosc, data, odbiorca, None, uwagi))

            sql_update_stan = """
                UPDATE ProduktyLokalizacje
                SET ilosc = ilosc - ?
                WHERE id_produktu = ? AND id_lokalizacji IN (
                    SELECT id_lokalizacji FROM LokalizacjeMagazynowe WHERE MagazynID = ?
                )
            """
            cursor.execute(sql_update_stan, (ilosc, material_id, magazyn_id))

            conn.commit()
            conn.close()

            messagebox.showinfo("Sukces", "Pomyślnie zarejestrowano wydanie.")
            self.clear_wydanie_form()
            self.refresh_wydania()
            self.refresh_stan_zapasu()
        except ValueError as e:
            messagebox.showerror("Błąd walidacji", str(e))
        except sqlite3.Error as e:
            messagebox.showerror("Błąd bazy danych", str(e))
        except Exception as e:
            messagebox.showerror("Błąd", str(e))

    def clear_wydanie_form(self):
        self.wydania_material_combo.set("")
        self.wydania_ilosc_entry.delete(0, tk.END)
        self.wydania_data_entry.delete(0, tk.END)
        self.wydania_data_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.wydania_magazyn_combo.set("")
        self.wydania_odbiorca_entry.delete(0, tk.END)
        self.wydania_uwagi_text.delete("1.0", tk.END)

    def refresh_wydania(self):
        for item in self.wydania_tree.get_children():
            self.wydania_tree.delete(item)

        conn = get_connection()
        cursor = conn.cursor()
        sql = """
            SELECT o.OperacjaID, m.Nazwa, o.Ilo, o.DataOperacji, mag.Kod, o.Dostawca, o.Uwagi
            FROM OperacjeMagazynowe o
            JOIN Materialy m ON o.MaterialID = m.MaterialID
            JOIN Magazyny mag ON o.MagazynID = mag.MagazynID
            WHERE o.TypOperacji = 'Wydanie'
            ORDER BY o.DataOperacji DESC, o.OperacjaID DESC
        """
        cursor.execute(sql)
        for row in cursor.fetchall():
            self.wydania_tree.insert("", "end", values=row)
        conn.close()
        self.load_combobox_data()


    def add_material(self):
        nazwa = self.mat_nazwa_entry.get().strip()
        jednostka = self.mat_jednostka_entry.get().strip()
        cena_str = self.mat_cena_entry.get().strip().replace(',', '.')

        if not nazwa or not jednostka or not cena_str:
            messagebox.showerror("Błąd", "Wszystkie pola muszą być wypełnione.")
            return

        try:
            cena = float(cena_str)
            if cena < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Błąd", "Cena musi być poprawną liczbą dodatnią.")
            return

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO Materialy (Nazwa, Jednostka, Cenajedn) VALUES (?, ?, ?)",
                (nazwa, jednostka, cena)
            )
            conn.commit()
            conn.close()

            messagebox.showinfo("Sukces", "Materiał został dodany do bazy.")
            self.mat_nazwa_entry.delete(0, tk.END)
            self.mat_jednostka_entry.delete(0, tk.END)
            self.mat_cena_entry.delete(0, tk.END)

            self.refresh_kartoteka()
            self.load_combobox_data()
        except sqlite3.Error as e:
            messagebox.showerror("Błąd bazy danych", str(e))

    def add_magazyn(self):
        kod = self.mag_kod_entry.get().strip()
        opis = self.mag_opis_entry.get().strip()

        if not kod or not opis:
            messagebox.showerror("Błąd", "Wszystkie pola muszą być wypełnione.")
            return

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO Magazyny (Kod, Opis) VALUES (?, ?)", (kod, opis))
            conn.commit()
            conn.close()

            messagebox.showinfo("Sukces", "Magazyn został dodany do bazy.")
            self.mag_kod_entry.delete(0, tk.END)
            self.mag_opis_entry.delete(0, tk.END)

            self.refresh_kartoteka()
            self.load_combobox_data()
        except sqlite3.Error as e:
            messagebox.showerror("Błąd bazy danych", str(e))

    def refresh_kartoteka(self):
        for item in self.mat_tree.get_children():
            self.mat_tree.delete(item)
        for item in self.mag_tree.get_children():
            self.mag_tree.delete(item)

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT MaterialID, Nazwa, Jednostka, Cenajedn FROM Materialy ORDER BY Nazwa")
        for row in cursor.fetchall():
            row_formatted = list(row)
            row_formatted[3] = f"{row_formatted[3]:.2f}"
            self.mat_tree.insert("", "end", values=row_formatted)

        cursor.execute("SELECT MagazynID, Kod, Opis FROM Magazyny ORDER BY Kod")
        for row in cursor.fetchall():
            self.mag_tree.insert("", "end", values=row)

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
                   SUM(CASE WHEN o.TypOperacji IN ('Przyjcie','Przyjęcie') THEN o.Ilo ELSE -o.Ilo END) AS IloscAktualna,
                   SUM(CASE WHEN o.TypOperacji IN ('Przyjcie','Przyjęcie') THEN o.Ilo * m.Cenajedn ELSE -o.Ilo * m.Cenajedn END) AS WartoscAktualna,
                   m.Cenajedn
            FROM OperacjeMagazynowe o
            JOIN Materialy m ON o.MaterialID = m.MaterialID
            JOIN Magazyny mag ON o.MagazynID = mag.MagazynID
            GROUP BY m.MaterialID, mag.MagazynID, m.Nazwa, mag.Kod, m.Cenajedn
            HAVING SUM(CASE WHEN o.TypOperacji IN ('Przyjcie','Przyjęcie') THEN o.Ilo ELSE -o.Ilo END) > 0
            ORDER BY mag.Kod, m.Nazwa;
        """)
        total = 0.0
        for lp, row in enumerate(cur.fetchall(), 1):
            nazwa, magazyn, ilosc, wartosc, cena = row
            wartosc = float(wartosc or 0)
            total += wartosc
            self.raporty_tree.insert("", "end", values=(
                lp, nazwa, magazyn, f"{ilosc} szt.", f"{wartosc:.2f} PLN", f"Cena jedn. {cena:.2f} PLN"
            ))
        self.raporty_tree.insert("", "end", values=("", "RAZEM", "", "", f"{total:.2f} PLN", ""))
        conn.close()

    def raport_miesieczny(self):
        self.clear_report_table()
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT strftime('%Y-%m', o.DataOperacji) AS Miesiac, m.Nazwa, mag.Kod,
                   SUM(CASE WHEN o.TypOperacji IN ('Przyjcie','Przyjęcie') THEN o.Ilo ELSE 0 END) AS Przyjecia,
                   SUM(CASE WHEN o.TypOperacji = 'Wydanie' THEN o.Ilo ELSE 0 END) AS Wydania,
                   SUM(CASE WHEN o.TypOperacji IN ('Przyjcie','Przyjęcie') THEN o.Ilo ELSE 0 END) -
                   SUM(CASE WHEN o.TypOperacji = 'Wydanie' THEN o.Ilo ELSE 0 END) AS Saldo
            FROM OperacjeMagazynowe o
            JOIN Materialy m ON o.MaterialID = m.MaterialID
            JOIN Magazyny mag ON o.MagazynID = mag.MagazynID
            WHERE o.DataOperacji IS NOT NULL
            GROUP BY Miesiac, m.Nazwa, mag.Kod
            ORDER BY Miesiac DESC, mag.Kod ASC, m.Nazwa ASC;
        """)
        for lp, row in enumerate(cur.fetchall(), 1):
            miesiac, nazwa, magazyn, przyjecia, wydania, saldo = row
            self.raporty_tree.insert("", "end", values=(
                lp, nazwa, magazyn, f"P:{przyjecia} / W:{wydania}", f"Saldo: {saldo}", miesiac
            ))
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
            self.raporty_tree.insert("", "end", values=(
                lp, nazwa, magazyn, f"{typ}: {ilosc} szt.", f"{float(wartosc or 0):.2f} PLN", f"{data}; {szczegoly}"
            ))
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
            self.raporty_tree.insert("", "end", values=(
                lp, nazwa, "-", f"{laczna_ilosc} szt.",
                f"{float(laczna_wartosc or 0):.2f} PLN", f"Liczba operacji: {liczba_op}"
            ))
        conn.close()

    def raport_trendy_miesieczne(self):
        self.clear_report_table()
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT strftime('%Y-%m', DataOperacji) AS Miesiac,
                   SUM(CASE WHEN TypOperacji IN ('Przyjcie','Przyjęcie') THEN Ilo ELSE 0 END) AS Przyjecia,
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
            self.raporty_tree.insert("", "end", values=(
                lp, "TREND ZBIORCZY", "-", f"P:{przyjecia} / W:{wydania}", "-", miesiac
            ))
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
                   SUM(CASE WHEN TypOperacji IN ('Przyjcie','Przyjęcie') THEN Ilo ELSE 0 END) AS Przyjecia,
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
            self.raporty_tree.insert("", "end", values=(
                lp, material_name, "-", f"P:{przyjecia} / W:{wydania}", f"Obrót: {obrot}", miesiac
            ))
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
                       SUM(CASE WHEN o.TypOperacji IN ('Przyjcie','Przyjęcie') THEN o.Ilo ELSE -o.Ilo END) AS Ilosc,
                       SUM(CASE WHEN o.TypOperacji IN ('Przyjcie','Przyjęcie') THEN o.Ilo * m.Cenajedn ELSE -o.Ilo * m.Cenajedn END) AS Wartosc
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

    def add_wydanie(self):
        try:
            material_name = self.wydania_material_combo.get()
            magazyn_name = self.wydania_magazyn_combo.get()

            if not material_name:
                raise ValueError("Proszę wybrać materiał.")
            if not magazyn_name:
                raise ValueError("Proszę wybrać magazyn.")

            try:
                ilosc = int(self.wydania_ilosc_entry.get())
                if ilosc <= 0:
                    raise ValueError
            except ValueError:
                raise ValueError("Ilość musi być poprawną liczbą całkowitą większą od zera.")

            data = self.wydania_data_entry.get().strip()
            datetime.strptime(data, "%Y-%m-%d")

            material_id = self.materialy_dict[material_name]
            magazyn_id = self.magazyny_dict[magazyn_name]
            odbiorca = self.wydania_odbiorca_entry.get().strip()
            uwagi = self.wydania_uwagi_text.get("1.0", "end-1c").strip()

            conn = get_connection()
            cursor = conn.cursor()

            sql_check = """
                SELECT 
                    COALESCE(SUM(CASE WHEN TypOperacji IN ('Przyjcie', 'Przyjęcie') THEN Ilo ELSE 0 END), 0) -
                    COALESCE(SUM(CASE WHEN TypOperacji = 'Wydanie' THEN Ilo ELSE 0 END), 0)
                FROM OperacjeMagazynowe
                WHERE MaterialID = ? AND MagazynID = ?
            """
            cursor.execute(sql_check, (material_id, magazyn_id))
            dostepna_ilosc = cursor.fetchone()[0]

            if dostepna_ilosc < ilosc:
                conn.close()
                raise ValueError(f"Niewystarczający stan magazynowy. Dostępna ilość: {dostepna_ilosc}")

            sql_insert = """
                INSERT INTO OperacjeMagazynowe 
                (MaterialID, MagazynID, TypOperacji, Ilo, DataOperacji, Dostawca, ZlecPracownika, Uwagi) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(sql_insert, (material_id, magazyn_id, "Wydanie", ilosc, data, odbiorca, None, uwagi))
            
            sql_update_stan = """
                UPDATE ProduktyLokalizacje 
                SET ilosc = ilosc - ? 
                WHERE id_produktu = ? AND id_lokalizacji IN (
                    SELECT id_lokalizacji FROM LokalizacjeMagazynowe WHERE MagazynID = ?
                )
            """
            cursor.execute(sql_update_stan, (ilosc, material_id, magazyn_id))

            conn.commit()
            conn.close()

            messagebox.showinfo("Sukces", "Pomyślnie zarejestrowano wydanie.")
            self.clear_wydanie_form()
            self.refresh_wydania()
            self.refresh_stan_zapasu()
        except ValueError as e:
            messagebox.showerror("Błąd walidacji", str(e))
        except sqlite3.Error as e:
            messagebox.showerror("Błąd bazy danych", str(e))
        except Exception as e:
            messagebox.showerror("Błąd", str(e))

    def clear_wydanie_form(self):
        self.wydania_material_combo.set("")
        self.wydania_ilosc_entry.delete(0, tk.END)
        self.wydania_data_entry.delete(0, tk.END)
        self.wydania_data_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.wydania_magazyn_combo.set("")
        self.wydania_odbiorca_entry.delete(0, tk.END)
        self.wydania_uwagi_text.delete("1.0", tk.END)

    def refresh_wydania(self):
        for item in self.wydania_tree.get_children():
            self.wydania_tree.delete(item)

        conn = get_connection()
        cursor = conn.cursor()
        sql = """
            SELECT o.OperacjaID, m.Nazwa, o.Ilo, o.DataOperacji, mag.Kod, o.Dostawca, o.Uwagi 
            FROM OperacjeMagazynowe o 
            JOIN Materialy m ON o.MaterialID = m.MaterialID 
            JOIN Magazyny mag ON o.MagazynID = mag.MagazynID 
            WHERE o.TypOperacji = 'Wydanie' 
            ORDER BY o.DataOperacji DESC, o.OperacjaID DESC
        """
        cursor.execute(sql)

        for row in cursor.fetchall():
            self.wydania_tree.insert("", "end", values=row)

        conn.close()
        self.load_combobox_data()

    def add_material(self):
        nazwa = self.mat_nazwa_entry.get().strip()
        jednostka = self.mat_jednostka_entry.get().strip()
        cena_str = self.mat_cena_entry.get().strip().replace(',', '.')

        if not nazwa or not jednostka or not cena_str:
            messagebox.showerror("Błąd", "Wszystkie pola muszą być wypełnione.")
            return

        try:
            cena = float(cena_str)
            if cena < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Błąd", "Cena musi być poprawną liczbą dodatnią.")
            return

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO Materialy (Nazwa, Jednostka, Cenajedn) VALUES (?, ?, ?)", (nazwa, jednostka, cena))
            conn.commit()
            conn.close()

            messagebox.showinfo("Sukces", "Materiał został dodany do bazy.")
            self.mat_nazwa_entry.delete(0, tk.END)
            self.mat_jednostka_entry.delete(0, tk.END)
            self.mat_cena_entry.delete(0, tk.END)
            
            self.refresh_kartoteka()
            self.load_combobox_data()
        except sqlite3.Error as e:
            messagebox.showerror("Błąd bazy danych", str(e))

    def add_magazyn(self):
        kod = self.mag_kod_entry.get().strip()
        opis = self.mag_opis_entry.get().strip()

        if not kod or not opis:
            messagebox.showerror("Błąd", "Wszystkie pola muszą być wypełnione.")
            return

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO Magazyny (Kod, Opis) VALUES (?, ?)", (kod, opis))
            conn.commit()
            conn.close()

            messagebox.showinfo("Sukces", "Magazyn został dodany do bazy.")
            self.mag_kod_entry.delete(0, tk.END)
            self.mag_opis_entry.delete(0, tk.END)
            
            self.refresh_kartoteka()
            self.load_combobox_data()
        except sqlite3.Error as e:
            messagebox.showerror("Błąd bazy danych", str(e))

    def refresh_kartoteka(self):
        for item in self.mat_tree.get_children():
            self.mat_tree.delete(item)
        for item in self.mag_tree.get_children():
            self.mag_tree.delete(item)

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT MaterialID, Nazwa, Jednostka, Cenajedn FROM Materialy ORDER BY Nazwa")
        for row in cursor.fetchall():
            row_formatted = list(row)
            row_formatted[3] = f"{row_formatted[3]:.2f}"
            self.mat_tree.insert("", "end", values=row_formatted)

        cursor.execute("SELECT MagazynID, Kod, Opis FROM Magazyny ORDER BY Kod")
        for row in cursor.fetchall():
            self.mag_tree.insert("", "end", values=row)

        conn.close()


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    root.deiconify()
    app = MagazynApp(root)
    root.mainloop()
