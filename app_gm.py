import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from pathlib import Path
import sqlite3
import sys

APP_DIR = Path(__file__).resolve().parent
DBFILE = APP_DIR / "gmsystem.db"
SQLFILE = APP_DIR / "gm_schema_and_data_extended.sql"


def get_connection():
    conn = sqlite3.connect(DBFILE)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


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
        self.root.geometry("1000x700")

        self.materialy_dict = {}
        self.magazyny_dict = {}

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.create_przyjecia_tab()
        self.create_wydania_tab()
        self.create_kartoteka_tab()
        self.create_stan_zapasu_tab()
        self.create_inwentaryzacja_tab()
        self.load_combobox_data()

    def create_inwentaryzacja_tab(self):
        self.inwentaryzacja_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.inwentaryzacja_frame, text="Inwentaryzacja")

        form_frame = ttk.LabelFrame(self.inwentaryzacja_frame, text="Nowy wpis inwentaryzacyjny", padding=10)
        form_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(form_frame, text="Produkt i Lokalizacja").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.inv_prod_loc_combo = ttk.Combobox(form_frame, state="readonly", width=60)
        self.inv_prod_loc_combo.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(form_frame, text="Ilość rzeczywista").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.inv_ilosc_entry = ttk.Entry(form_frame, width=20)
        self.inv_ilosc_entry.grid(row=1, column=1, sticky="w", padx=5, pady=5)

        ttk.Label(form_frame, text="Pracownik").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.inv_pracownik_combo = ttk.Combobox(form_frame, state="readonly", width=40)
        self.inv_pracownik_combo.grid(row=2, column=1, sticky="w", padx=5, pady=5)

        ttk.Label(form_frame, text="Uwagi").grid(row=3, column=0, sticky="nw", padx=5, pady=5)
        self.inv_uwagi_entry = ttk.Entry(form_frame, width=60)
        self.inv_uwagi_entry.grid(row=3, column=1, padx=5, pady=5)

        ttk.Button(form_frame, text="Zapisz inwentaryzację", command=self.save_inwentaryzacja).grid(row=4, column=1, pady=10, sticky="e")

        table_frame = ttk.LabelFrame(self.inwentaryzacja_frame, text="Historia inwentaryzacji", padding=10)
        table_frame.pack(fill="both", expand=True, padx=10, pady=10)

        cols = ("Data", "Produkt", "Lokalizacja", "Systemowa", "Rzeczywista", "Różnica", "Pracownik", "Status")
        self.inv_tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        for col in cols:
            self.inv_tree.heading(col, text=col)
            self.inv_tree.column(col, width=100)
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
            cursor2.execute("SELECT id_produktu, id_lokalizacji FROM ProduktyLokalizacje WHERE id_produktu_lokalizacji=?", (row[0],))
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
            if not label: raise ValueError("Wybierz produkt i lokalizację.")
            
            ilosc_rzecz = int(self.inv_ilosc_entry.get())
            pracownik_name = self.inv_pracownik_combo.get()
            if not pracownik_name: raise ValueError("Wybierz pracownika.")
            
            data = self.inv_prod_loc_dict[label]
            pracownik_id = self.pracownicy_dict[pracownik_name]
            
            conn = get_connection()
            cursor = conn.cursor()
            sql = """
                INSERT INTO Inwentaryzacja (id_produktu, id_lokalizacji, id_pracownika, data_inwentaryzacji, ilosc_systemowa, ilosc_rzeczywista, status, uwagi)
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
            messagebox.showinfo("OK", "Zapisano wynik inwentaryzacji.")
            self.refresh_inwentaryzacja()
        except Exception as e:
            messagebox.showerror("Błąd", str(e))

    def refresh_inwentaryzacja(self):
        for item in self.inv_tree.get_children():
            self.inv_tree.delete(item)
        
        conn = get_connection()
        cursor = conn.cursor()
        sql = """
            SELECT i.data_inwentaryzacji, m.Nazwa, lm.strefa || ' ' || lm.regal, i.ilosc_systemowa, i.ilosc_rzeczywista, i.roznica, p.nazwisko, i.status
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

    def create_stan_zapasu_tab(self):
        self.stan_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.stan_frame, text="Aktualny stan zapasu")
        
        button_frame = ttk.Frame(self.stan_frame)
        button_frame.pack(fill="x", padx=10, pady=5)
        ttk.Button(button_frame, text="Odśwież stan", command=self.refresh_stan_zapasu).pack(side="left")

        cols = ("Materiał", "Magazyn", "Ilość", "Jednostka", "Cena jedn.", "Wartość zapasu", "Lokalizacja")
        self.stan_tree = ttk.Treeview(self.stan_frame, columns=cols, show="headings")
        
        column_widths = {
            "Materiał": 250,
            "Magazyn": 80,
            "Ilość": 70,
            "Jednostka": 80,
            "Cena jedn.": 100,
            "Wartość zapasu": 120,
            "Lokalizacja": 150
        }

        for col in cols:
            self.stan_tree.heading(col, text=col)
            self.stan_tree.column(col, width=column_widths.get(col, 100), anchor="center" if col != "Materiał" else "w")
        
        self.stan_tree.pack(fill="both", expand=True, padx=10, pady=10)
        self.refresh_stan_zapasu()

    def refresh_stan_zapasu(self):
        for item in self.stan_tree.get_children():
            self.stan_tree.delete(item)

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
            ORDER BY m.Nazwa, mag.Kod
        """
        cursor.execute(sql)

        for row in cursor.fetchall():
            formatted_row = list(row)
            formatted_row[4] = f"{row[4]:.2f}"
            formatted_row[5] = f"{row[5]:.2f}"
            self.stan_tree.insert("", "end", values=formatted_row)

        conn.close()

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
            self.przyjecia_tree.column(col, width=120)

        self.przyjecia_tree.pack(fill="both", expand=True)

        #self.load_combobox_data()
        self.refresh_przyjecia()

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

        ttk.Label(form_frame, text="Zlecenie/Pracownik").grid(row=4, column=0, sticky="w", padx=5, pady=5)
        self.wydania_zlecenie_entry = ttk.Entry(form_frame, width=50)
        self.wydania_zlecenie_entry.grid(row=4, column=1, padx=5, pady=5)

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

        cols = ("ID", "Materiał", "Ilość", "Data", "Magazyn", "Zlecenie/Pracownik", "Uwagi")
        self.wydania_tree = ttk.Treeview(table_frame, columns=cols, show="headings", yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.wydania_tree.yview)

        for col in cols:
            self.wydania_tree.heading(col, text=col)
            self.wydania_tree.column(col, width=120)

        self.wydania_tree.pack(fill="both", expand=True)

    def create_kartoteka_tab(self):
        self.kartoteka_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.kartoteka_frame, text="Kartoteka")
        
        # Sekcja 1: MATERIAŁY
        material_frame = ttk.LabelFrame(self.kartoteka_frame, text="Nowy materiał", padding=10)
        material_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(material_frame, text="Nazwa").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.kartoteka_material_nazwa = ttk.Entry(material_frame, width=40)
        self.kartoteka_material_nazwa.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(material_frame, text="Indeks").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.kartoteka_material_indeks = ttk.Entry(material_frame, width=20)
        self.kartoteka_material_indeks.grid(row=1, column=1, sticky="w", padx=5, pady=5)

        ttk.Label(material_frame, text="Kategoria").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.kartoteka_material_kategoria = ttk.Entry(material_frame, width=40)
        self.kartoteka_material_kategoria.grid(row=2, column=1, sticky="w", padx=5, pady=5)

        ttk.Label(material_frame, text="Cena jedn.").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        self.kartoteka_material_cena = ttk.Entry(material_frame, width=20)
        self.kartoteka_material_cena.grid(row=3, column=1, sticky="w", padx=5, pady=5)

        ttk.Label(material_frame, text="Jednostka").grid(row=4, column=0, sticky="w", padx=5, pady=5)
        self.kartoteka_material_jednostka = ttk.Entry(material_frame, width=20)
        self.kartoteka_material_jednostka.grid(row=4, column=1, sticky="w", padx=5, pady=5)

        ttk.Button(material_frame, text="Dodaj materiał", command=self.add_material).grid(row=5, column=0, columnspan=2, pady=10)

        # Tabela z istniejącymi materiałami
        table_frame = ttk.LabelFrame(self.kartoteka_frame, text="Lista materiałów", padding=10)
        table_frame.pack(fill="both", expand=True, padx=10, pady=10)

        cols = ("ID", "Nazwa", "Indeks", "Kategoria", "Cena jedn.", "Jednostka")
        self.kartoteka_tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        for col in cols:
            self.kartoteka_tree.heading(col, text=col)
            self.kartoteka_tree.column(col, width=120)
        self.kartoteka_tree.pack(fill="both", expand=True)

        self.refresh_kartoteka()

    def load_combobox_data(self):
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT MaterialID, Nazwa FROM Materialy ORDER BY Nazwa")
        materialy = cursor.fetchall()
        self.materialy_dict = {row[1]: row[0] for row in materialy}
        self.przyjecia_material_combo["values"] = list(self.materialy_dict.keys())
        self.wydania_material_combo["values"] = list(self.materialy_dict.keys())

        cursor.execute("SELECT MagazynID, Kod, Opis FROM Magazyny ORDER BY Kod")
        magazyny = cursor.fetchall()
        self.magazyny_dict = {f"{row[1]} - {row[2]}": row[0] for row in magazyny}
        self.przyjecia_magazyn_combo["values"] = list(self.magazyny_dict.keys())
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
            cursor.execute(sql, (material_id, magazyn_id, "Przyjcie", ilosc, data, dostawca, None, uwagi))
            conn.commit()
            conn.close()

            messagebox.showinfo("OK", "Dodano przyjęcie.")
            self.clear_przyjecie_form()
            self.refresh_przyjecia()
            self.refresh_stan_zapasu()
        except ValueError as e:
            messagebox.showerror("Błąd danych", str(e))
        except sqlite3.Error as e:
            messagebox.showerror("Błąd bazy", str(e))
        except Exception as e:
            messagebox.showerror("Błąd", str(e))

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
            zlecenie = self.wydania_zlecenie_entry.get().strip()
            uwagi = self.wydania_uwagi_text.get("1.0", "end-1c").strip()

            conn = get_connection()
            cursor = conn.cursor()
            
            # Sprawdzenie stanu
            cursor.execute("""
                SELECT (COALESCE(SUM(CASE WHEN TypOperacji='Przyjcie' THEN Ilo ELSE 0 END), 0) - 
                        COALESCE(SUM(CASE WHEN TypOperacji='Wydanie' THEN Ilo ELSE 0 END), 0)) as stan
                FROM OperacjeMagazynowe  
                WHERE MaterialID=? AND MagazynID=?
            """, (material_id, magazyn_id))
            
            dostepny_stan = cursor.fetchone()[0]
            if dostepny_stan is None or dostepny_stan < ilosc:
                messagebox.showerror("Błąd", f"Brak wystarczającej ilości! Dostępne: {dostepny_stan if dostepny_stan else 0}")
                conn.close()
                return

            sql = (
                "INSERT INTO OperacjeMagazynowe "
                "(MaterialID, MagazynID, TypOperacji, Ilo, DataOperacji, Dostawca, ZlecPracownika, Uwagi) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
            )
            cursor.execute(sql, (material_id, magazyn_id, "Wydanie", ilosc, data, None, zlecenie, uwagi))
            conn.commit()
            conn.close()

            messagebox.showinfo("OK", "Dodano wydanie.")
            self.clear_wydanie_form()
            self.refresh_wydania()
            self.refresh_stan_zapasu()
        except ValueError as e:
            messagebox.showerror("Błąd danych", str(e))
        except sqlite3.Error as e:
            messagebox.showerror("Błąd bazy", str(e))
        except Exception as e:
            messagebox.showerror("Błąd", str(e))

    def add_material(self):
        try:
            nazwa = self.kartoteka_material_nazwa.get().strip()
            indeks_str = self.kartoteka_material_indeks.get().strip()
            kategoria = self.kartoteka_material_kategoria.get().strip()
            cena_str = self.kartoteka_material_cena.get().strip()
            jednostka = self.kartoteka_material_jednostka.get().strip()

            if not nazwa or not indeks_str or not cena_str or not jednostka:
                messagebox.showerror("Błąd", "Wypełnij wszystkie wymagane pola.")
                return

            indeks = int(indeks_str)
            cena = float(cena_str)

            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO Materialy (Nazwa, Indeks, Kategoria, Cenajedn, Jednostka) VALUES(?,?,?,?,?)",
                (nazwa, indeks, kategoria, cena, jednostka)
            )
            conn.commit()
            conn.close()

            messagebox.showinfo("OK", "Dodano nowy materiał.")
            self.load_combobox_data()
            self.refresh_kartoteka()
            
            # Wyczyść pola po dodaniu
            self.kartoteka_material_nazwa.delete(0, tk.END)
            self.kartoteka_material_indeks.delete(0, tk.END)
            self.kartoteka_material_kategoria.delete(0, tk.END)
            self.kartoteka_material_cena.delete(0, tk.END)
            self.kartoteka_material_jednostka.delete(0, tk.END)

        except ValueError:
            messagebox.showerror("Błąd danych", "Indeks musi być liczbą całkowitą, a cena liczbą zmiennoprzecinkową.")
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

    def clear_wydanie_form(self):
        self.wydania_material_combo.set("")
        self.wydania_ilosc_entry.delete(0, tk.END)
        self.wydania_data_entry.delete(0, tk.END)
        self.wydania_data_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.wydania_magazyn_combo.set("")
        self.wydania_zlecenie_entry.delete(0, tk.END)
        self.wydania_uwagi_text.delete("1.0", tk.END)

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
            "WHERE o.TypOperacji = ? "
            "ORDER BY o.DataOperacji DESC, o.OperacjaID DESC"
        )
        cursor.execute(sql, ("Przyjcie",))

        for row in cursor.fetchall():
            self.przyjecia_tree.insert("", "end", values=row)

        conn.close()

    def refresh_wydania(self):
        for item in self.wydania_tree.get_children():
            self.wydania_tree.delete(item)

        conn = get_connection()
        cursor = conn.cursor()
        sql = (
            "SELECT o.OperacjaID, m.Nazwa, o.Ilo, o.DataOperacji, mag.Kod, o.ZlecPracownika, o.Uwagi "
            "FROM OperacjeMagazynowe o "
            "JOIN Materialy m ON o.MaterialID = m.MaterialID "
            "JOIN Magazyny mag ON o.MagazynID = mag.MagazynID "
            "WHERE o.TypOperacji = ? "
            "ORDER BY o.DataOperacji DESC, o.OperacjaID DESC"
        )
        cursor.execute(sql, ("Wydanie",))

        for row in cursor.fetchall():
            self.wydania_tree.insert("", "end", values=row)

        conn.close()

    def refresh_kartoteka(self):
        for item in self.kartoteka_tree.get_children():
            self.kartoteka_tree.delete(item)

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT MaterialID, Nazwa, Indeks, Kategoria, Cenajedn, Jednostka FROM Materialy ORDER BY Nazwa")
        for row in cursor.fetchall():
            self.kartoteka_tree.insert("", "end", values=row)
        conn.close()


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    root.deiconify()
    app = MagazynApp(root)
    root.mainloop()
