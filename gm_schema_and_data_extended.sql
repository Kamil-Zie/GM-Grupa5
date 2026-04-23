PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS Inwentaryzacja;
DROP TABLE IF EXISTS ProduktyLokalizacje;
DROP TABLE IF EXISTS LokalizacjeMagazynowe;
DROP TABLE IF EXISTS Dostawcy;
DROP TABLE IF EXISTS Pracownicy;
DROP TABLE IF EXISTS StanZapasu;
DROP TABLE IF EXISTS OperacjeMagazynowe;
DROP TABLE IF EXISTS KontaKosztowe;
DROP TABLE IF EXISTS Magazyny;
DROP TABLE IF EXISTS Materialy;

CREATE TABLE Materialy (
    MaterialID INTEGER PRIMARY KEY AUTOINCREMENT,
    Nazwa TEXT NOT NULL,
    Indeks INTEGER NOT NULL UNIQUE,
    Kategoria TEXT,
    Cenajedn REAL NOT NULL CHECK (Cenajedn >= 0),
    Jednostka TEXT DEFAULT 'szt'
);

CREATE TABLE Magazyny (
    MagazynID INTEGER PRIMARY KEY AUTOINCREMENT,
    Kod TEXT NOT NULL UNIQUE,
    Opis TEXT,
    Lokalizacja TEXT
);

CREATE TABLE KontaKosztowe (
    KontoID INTEGER PRIMARY KEY AUTOINCREMENT,
    Kod TEXT NOT NULL UNIQUE,
    Opis TEXT,
    Typ TEXT NOT NULL CHECK (Typ IN ('Przychod', 'Koszt'))
);

CREATE TABLE Pracownicy (
    id_pracownika INTEGER PRIMARY KEY AUTOINCREMENT,
    imie TEXT NOT NULL,
    nazwisko TEXT NOT NULL,
    stanowisko TEXT,
    dzial TEXT,
    email TEXT UNIQUE,
    telefon TEXT,
    aktywny INTEGER NOT NULL DEFAULT 1 CHECK (aktywny IN (0,1))
);

CREATE TABLE Dostawcy (
    id_dostawcy INTEGER PRIMARY KEY AUTOINCREMENT,
    nazwa TEXT NOT NULL UNIQUE,
    nip TEXT UNIQUE,
    miasto TEXT,
    adres TEXT,
    telefon TEXT,
    email TEXT,
    osoba_kontaktowa TEXT
);

CREATE TABLE LokalizacjeMagazynowe (
    id_lokalizacji INTEGER PRIMARY KEY AUTOINCREMENT,
    MagazynID INTEGER NOT NULL,
    strefa TEXT NOT NULL,
    regal TEXT NOT NULL,
    polka TEXT NOT NULL,
    pozycja TEXT,
    opis TEXT,
    UNIQUE (MagazynID, strefa, regal, polka, pozycja),
    FOREIGN KEY (MagazynID) REFERENCES Magazyny(MagazynID)
);

CREATE TABLE ProduktyLokalizacje (
    id_produktu_lokalizacji INTEGER PRIMARY KEY AUTOINCREMENT,
    id_produktu INTEGER NOT NULL,
    id_lokalizacji INTEGER NOT NULL,
    ilosc INTEGER NOT NULL DEFAULT 0 CHECK (ilosc >= 0),
    data_aktualizacji DATE DEFAULT CURRENT_DATE,
    UNIQUE (id_produktu, id_lokalizacji),
    FOREIGN KEY (id_produktu) REFERENCES Materialy(MaterialID),
    FOREIGN KEY (id_lokalizacji) REFERENCES LokalizacjeMagazynowe(id_lokalizacji)
);

CREATE TABLE OperacjeMagazynowe (
    OperacjaID INTEGER PRIMARY KEY AUTOINCREMENT,
    MaterialID INTEGER NOT NULL,
    MagazynID INTEGER NOT NULL,
    TypOperacji TEXT NOT NULL CHECK (TypOperacji IN ('Przyjcie', 'Wydanie')),
    Ilo INTEGER NOT NULL CHECK (Ilo > 0),
    DataOperacji DATE NOT NULL,
    Dostawca TEXT,
    ZlecPracownika TEXT,
    Uwagi TEXT,
    id_pracownika INTEGER,
    id_dostawcy INTEGER,
    KontoID INTEGER,
    id_lokalizacji INTEGER,
    FOREIGN KEY (MaterialID) REFERENCES Materialy(MaterialID),
    FOREIGN KEY (MagazynID) REFERENCES Magazyny(MagazynID),
    FOREIGN KEY (id_pracownika) REFERENCES Pracownicy(id_pracownika),
    FOREIGN KEY (id_dostawcy) REFERENCES Dostawcy(id_dostawcy),
    FOREIGN KEY (KontoID) REFERENCES KontaKosztowe(KontoID),
    FOREIGN KEY (id_lokalizacji) REFERENCES LokalizacjeMagazynowe(id_lokalizacji),
    CHECK (
        (TypOperacji = 'Przyjcie' AND id_dostawcy IS NOT NULL)
        OR (TypOperacji = 'Wydanie')
    )
);

CREATE TABLE StanZapasu (
    ZapisID INTEGER PRIMARY KEY AUTOINCREMENT,
    MaterialID INTEGER NOT NULL,
    MagazynID INTEGER NOT NULL,
    PeriodMiesiac TEXT NOT NULL,
    IloscPoczatkowa INTEGER DEFAULT 0,
    Przyjecia INTEGER DEFAULT 0,
    Wydania INTEGER DEFAULT 0,
    IloscKoncowa INTEGER DEFAULT 0,
    WartoscZapasu REAL DEFAULT 0,
    FOREIGN KEY (MaterialID) REFERENCES Materialy(MaterialID),
    FOREIGN KEY (MagazynID) REFERENCES Magazyny(MagazynID)
);

CREATE TABLE Inwentaryzacja (
    id_inwentaryzacji INTEGER PRIMARY KEY AUTOINCREMENT,
    id_produktu INTEGER NOT NULL,
    id_lokalizacji INTEGER NOT NULL,
    id_pracownika INTEGER NOT NULL,
    data_inwentaryzacji DATE NOT NULL,
    ilosc_systemowa INTEGER NOT NULL,
    ilosc_rzeczywista INTEGER NOT NULL,
    roznica INTEGER GENERATED ALWAYS AS (ilosc_rzeczywista - ilosc_systemowa) VIRTUAL,
    status TEXT NOT NULL DEFAULT 'Zatwierdzona' CHECK (status IN ('Robocza', 'Zatwierdzona', 'Wyjasnienie')),
    uwagi TEXT,
    FOREIGN KEY (id_produktu) REFERENCES Materialy(MaterialID),
    FOREIGN KEY (id_lokalizacji) REFERENCES LokalizacjeMagazynowe(id_lokalizacji),
    FOREIGN KEY (id_pracownika) REFERENCES Pracownicy(id_pracownika)
);

CREATE INDEX idx_materialy_indeks ON Materialy(Indeks);
CREATE INDEX idx_magazyny_kod ON Magazyny(Kod);
CREATE INDEX idx_operacje_data ON OperacjeMagazynowe(DataOperacji);
CREATE INDEX idx_operacje_typ ON OperacjeMagazynowe(TypOperacji);
CREATE INDEX idx_operacje_material ON OperacjeMagazynowe(MaterialID);
CREATE INDEX idx_operacje_magazyn ON OperacjeMagazynowe(MagazynID);
CREATE INDEX idx_operacje_pracownik ON OperacjeMagazynowe(id_pracownika);
CREATE INDEX idx_operacje_dostawca ON OperacjeMagazynowe(id_dostawcy);
CREATE INDEX idx_operacje_lokalizacja ON OperacjeMagazynowe(id_lokalizacji);
CREATE INDEX idx_lokalizacje_magazyn ON LokalizacjeMagazynowe(MagazynID);
CREATE INDEX idx_produkty_lokalizacje_prod ON ProduktyLokalizacje(id_produktu);
CREATE INDEX idx_inwentaryzacja_data ON Inwentaryzacja(data_inwentaryzacji);
CREATE INDEX idx_stan_period ON StanZapasu(PeriodMiesiac);

INSERT INTO Materialy (Nazwa, Indeks, Kategoria, Cenajedn, Jednostka) VALUES
('Akumulator samochodowy 12V 180Ah', 71, 'części zamienne', 200.74, 'szt'),
('Wtyczka EURO 24V', 61, 'części zamienne', 18.22, 'szt'),
('Cewka zapłonowa', 64, 'części zamienne', 363.00, 'szt'),
('Cylinder hydrauliczny', 72, 'hydraulika', 550.00, 'szt'),
('Filtr oleju', 73, 'eksploatacyjne', 45.90, 'szt'),
('Pasek klinowy', 74, 'części zamienne', 39.50, 'szt'),
('Łożysko kulkowe 6204', 75, 'łożyska', 28.40, 'szt'),
('Olej silnikowy 10W40 5L', 76, 'smary', 120.00, 'opak'),
('Płyn hamulcowy DOT4', 77, 'chemia', 32.00, 'but'),
('Śruba M12x50', 78, 'elementy złączne', 1.20, 'szt'),
('Nakrętka M12', 79, 'elementy złączne', 0.80, 'szt'),
('Podkładka M12', 80, 'elementy złączne', 0.25, 'szt'),
('Rękawice robocze', 81, 'BHP', 12.50, 'para'),
('Kask ochronny', 82, 'BHP', 55.00, 'szt'),
('Smar litowy 400g', 83, 'smary', 19.90, 'szt');

INSERT INTO Magazyny (Kod, Opis, Lokalizacja) VALUES
('01', 'Magazyn główny', 'Wrocław'),
('02', 'Magazyn techniczny', 'Kraków');

INSERT INTO KontaKosztowe (Kod, Opis, Typ) VALUES
('5210', 'Produkcja', 'Koszt'),
('5220', 'Utrzymanie ruchu', 'Koszt'),
('5230', 'Serwis', 'Koszt'),
('5240', 'Logistyka', 'Koszt'),
('5250', 'BHP', 'Koszt');

INSERT INTO Pracownicy (imie, nazwisko, stanowisko, dzial, email, telefon) VALUES
('Jan', 'Kowalski', 'Magazynier', 'Magazyn', 'jan.kowalski@firma.pl', '600100100'),
('Anna', 'Nowak', 'Brygadzista', 'Produkcja', 'anna.nowak@firma.pl', '600100101'),
('Piotr', 'Wiśniewski', 'Specjalista UR', 'Utrzymanie ruchu', 'piotr.wisniewski@firma.pl', '600100102'),
('Maria', 'Zielińska', 'Koordynator logistyki', 'Logistyka', 'maria.zielinska@firma.pl', '600100103'),
('Tomasz', 'Lewandowski', 'Inspektor BHP', 'BHP', 'tomasz.lewandowski@firma.pl', '600100104');

INSERT INTO Dostawcy (nazwa, nip, miasto, adres, telefon, email, osoba_kontaktowa) VALUES
('Grene', '8970000001', 'Poznań', 'ul. Magazynowa 1', '611000001', 'kontakt@grene.pl', 'Adam Gajda'),
('STO-ART S.A.', '8970000002', 'Warszawa', 'ul. Przemysłowa 12', '611000002', 'biuro@stoart.pl', 'Ewa Brzoza'),
('Hydro-Max', '8970000003', 'Katowice', 'ul. Hutnicza 8', '611000003', 'sprzedaz@hydromax.pl', 'Paweł Kurek'),
('Moto-Części', '8970000004', 'Łódź', 'ul. Mechaników 5', '611000004', 'handel@moto-czesci.pl', 'Monika Lis'),
('Tech-Serwis', '8970000005', 'Gdańsk', 'ul. Portowa 19', '611000005', 'zamowienia@techserwis.pl', 'Karol Wójcik');

INSERT INTO LokalizacjeMagazynowe (MagazynID, strefa, regal, polka, pozycja, opis) VALUES
(1, 'A', 'R1', 'P1', '01', 'Strefa części elektrycznych'),
(1, 'A', 'R1', 'P2', '02', 'Strefa drobnych elementów'),
(1, 'B', 'R2', 'P1', '01', 'Strefa BHP'),
(2, 'C', 'R3', 'P1', '01', 'Hydraulika i cięższe komponenty'),
(2, 'C', 'R3', 'P2', '02', 'Chemia i smary');

INSERT INTO ProduktyLokalizacje (id_produktu, id_lokalizacji, ilosc, data_aktualizacji) VALUES
(1, 1, 26, '2003-12-31'),
(2, 1, 22, '2003-12-31'),
(3, 1, 14, '2003-12-31'),
(4, 4, 36, '2003-12-31'),
(5, 2, 12, '2003-12-31'),
(6, 2, 20, '2003-12-31'),
(7, 4, 55, '2003-12-31'),
(8, 5, 11, '2003-12-31'),
(9, 5, 32, '2003-12-31'),
(10, 2, 40, '2003-12-31'),
(11, 2, 48, '2003-12-31'),
(12, 2, 65, '2003-12-31'),
(13, 3, 25, '2003-12-31'),
(14, 3, 12, '2003-12-31'),
(15, 5, 16, '2003-12-31');

INSERT INTO OperacjeMagazynowe (MaterialID, MagazynID, TypOperacji, Ilo, DataOperacji, Dostawca, ZlecPracownika, Uwagi, id_pracownika, id_dostawcy, KontoID, id_lokalizacji) VALUES
(1, 2, 'Przyjcie', 15, '2003-10-15', 'Grene', NULL, 'Partia P01', 1, 1, NULL, 4),
(2, 1, 'Przyjcie', 12, '2003-10-17', 'STO-ART S.A.', NULL, 'Partia P02', 1, 2, NULL, 1),
(3, 1, 'Przyjcie', 10, '2003-10-19', 'Hydro-Max', NULL, 'Partia P03', 1, 3, NULL, 1),
(4, 2, 'Przyjcie', 20, '2003-10-21', 'Moto-Części', NULL, 'Partia P04', 4, 4, NULL, 4),
(5, 1, 'Przyjcie', 8, '2003-10-23', 'Tech-Serwis', NULL, 'Partia P05', 4, 5, NULL, 2),
(6, 1, 'Przyjcie', 14, '2003-10-25', 'Grene', NULL, 'Partia P06', 1, 1, NULL, 2),
(7, 2, 'Przyjcie', 30, '2003-10-27', 'STO-ART S.A.', NULL, 'Partia P07', 1, 2, NULL, 4),
(8, 1, 'Przyjcie', 6, '2003-10-29', 'Hydro-Max', NULL, 'Partia P08', 4, 3, NULL, 5),
(9, 1, 'Przyjcie', 18, '2003-10-31', 'Moto-Części', NULL, 'Partia P09', 1, 4, NULL, 5),
(10, 2, 'Przyjcie', 50, '2003-11-02', 'Tech-Serwis', NULL, 'Partia P10', 4, 5, NULL, 2),
(11, 1, 'Przyjcie', 60, '2003-11-04', 'Grene', NULL, 'Partia P11', 1, 1, NULL, 2),
(12, 1, 'Przyjcie', 80, '2003-11-06', 'STO-ART S.A.', NULL, 'Partia P12', 1, 2, NULL, 2),
(13, 2, 'Przyjcie', 25, '2003-11-08', 'Hydro-Max', NULL, 'Partia P13', 4, 3, NULL, 3),
(14, 1, 'Przyjcie', 12, '2003-11-10', 'Moto-Części', NULL, 'Partia P14', 1, 4, NULL, 3),
(15, 1, 'Przyjcie', 16, '2003-11-12', 'Tech-Serwis', NULL, 'Partia P15', 4, 5, NULL, 5),
(1, 2, 'Przyjcie', 15, '2003-11-14', 'Grene', NULL, 'Partia P16', 1, 1, NULL, 4),
(2, 1, 'Przyjcie', 12, '2003-11-16', 'STO-ART S.A.', NULL, 'Partia P17', 1, 2, NULL, 1),
(3, 1, 'Przyjcie', 10, '2003-11-18', 'Hydro-Max', NULL, 'Partia P18', 4, 3, NULL, 1),
(4, 2, 'Przyjcie', 20, '2003-11-20', 'Moto-Części', NULL, 'Partia P19', 4, 4, NULL, 4),
(5, 1, 'Przyjcie', 8, '2003-11-22', 'Tech-Serwis', NULL, 'Partia P20', 1, 5, NULL, 2),
(6, 1, 'Przyjcie', 14, '2003-11-24', 'Grene', NULL, 'Partia P21', 1, 1, NULL, 2),
(7, 2, 'Przyjcie', 30, '2003-11-26', 'STO-ART S.A.', NULL, 'Partia P22', 4, 2, NULL, 4),
(8, 1, 'Przyjcie', 6, '2003-11-28', 'Hydro-Max', NULL, 'Partia P23', 1, 3, NULL, 5),
(9, 1, 'Przyjcie', 18, '2003-11-30', 'Moto-Części', NULL, 'Partia P24', 4, 4, NULL, 5),
(10, 2, 'Przyjcie', 50, '2003-12-02', 'Tech-Serwis', NULL, 'Partia P25', 1, 5, NULL, 2),
(1, 2, 'Wydanie', 2, '2003-11-07', NULL, 'PKNS680 Marantów 5210', 'Rozchód R01', 2, NULL, 1, 4),
(2, 1, 'Wydanie', 1, '2003-11-09', NULL, 'PKNS690 Marantów 5220', 'Rozchód R02', 2, NULL, 2, 1),
(3, 1, 'Wydanie', 3, '2003-11-11', NULL, 'UR-01 5230', 'Rozchód R03', 3, NULL, 3, 1),
(4, 1, 'Wydanie', 2, '2003-11-13', NULL, 'SERW-02 5240', 'Rozchód R04', 4, NULL, 4, 4),
(5, 2, 'Wydanie', 2, '2003-11-15', NULL, 'BHP-03 5250', 'Rozchód R05', 5, NULL, 5, 2),
(6, 1, 'Wydanie', 4, '2003-11-17', NULL, 'PKNS680 Marantów 5210', 'Rozchód R06', 2, NULL, 1, 2),
(7, 1, 'Wydanie', 5, '2003-11-19', NULL, 'PKNS690 Marantów 5220', 'Rozchód R07', 2, NULL, 2, 4),
(8, 1, 'Wydanie', 1, '2003-11-21', NULL, 'UR-01 5230', 'Rozchód R08', 3, NULL, 3, 5),
(9, 2, 'Wydanie', 2, '2003-11-23', NULL, 'SERW-02 5240', 'Rozchód R09', 4, NULL, 4, 5),
(10, 1, 'Wydanie', 10, '2003-11-25', NULL, 'BHP-03 5250', 'Rozchód R10', 5, NULL, 5, 2),
(11, 1, 'Wydanie', 12, '2003-11-27', NULL, 'PKNS680 Marantów 5210', 'Rozchód R11', 2, NULL, 1, 2),
(12, 1, 'Wydanie', 15, '2003-11-29', NULL, 'PKNS690 Marantów 5220', 'Rozchód R12', 2, NULL, 2, 2),
(1, 2, 'Wydanie', 2, '2003-12-01', NULL, 'UR-01 5230', 'Rozchód R13', 3, NULL, 3, 4),
(2, 1, 'Wydanie', 1, '2003-12-03', NULL, 'SERW-02 5240', 'Rozchód R14', 4, NULL, 4, 1),
(3, 1, 'Wydanie', 3, '2003-12-05', NULL, 'BHP-03 5250', 'Rozchód R15', 5, NULL, 5, 1),
(4, 1, 'Wydanie', 2, '2003-12-07', NULL, 'PKNS680 Marantów 5210', 'Rozchód R16', 2, NULL, 1, 4),
(5, 2, 'Wydanie', 2, '2003-12-09', NULL, 'PKNS690 Marantów 5220', 'Rozchód R17', 2, NULL, 2, 2),
(6, 1, 'Wydanie', 4, '2003-12-11', NULL, 'UR-01 5230', 'Rozchód R18', 3, NULL, 3, 2),
(7, 1, 'Wydanie', 5, '2003-12-13', NULL, 'SERW-02 5240', 'Rozchód R19', 4, NULL, 4, 4),
(8, 1, 'Wydanie', 1, '2003-12-15', NULL, 'BHP-03 5250', 'Rozchód R20', 5, NULL, 5, 5),
(9, 2, 'Wydanie', 2, '2003-12-17', NULL, 'PKNS680 Marantów 5210', 'Rozchód R21', 2, NULL, 1, 5),
(10, 1, 'Wydanie', 10, '2003-12-19', NULL, 'PKNS690 Marantów 5220', 'Rozchód R22', 2, NULL, 2, 2),
(11, 1, 'Wydanie', 12, '2003-12-21', NULL, 'UR-01 5230', 'Rozchód R23', 3, NULL, 3, 2),
(12, 1, 'Wydanie', 15, '2003-12-23', NULL, 'SERW-02 5240', 'Rozchód R24', 4, NULL, 4, 2);

INSERT INTO StanZapasu (MaterialID, MagazynID, PeriodMiesiac, IloscPoczatkowa, Przyjecia, Wydania, IloscKoncowa, WartoscZapasu) VALUES
(1, 2, '2003-12', 15, 15, 4, 26, 5219.24),
(2, 1, '2003-12', 12, 12, 2, 22, 400.84),
(3, 1, '2003-12', 10, 10, 6, 14, 5082.00),
(4, 2, '2003-12', 20, 20, 4, 36, 19800.00),
(5, 1, '2003-12', 8, 8, 4, 12, 550.80),
(6, 1, '2003-12', 14, 14, 8, 20, 790.00),
(7, 2, '2003-12', 30, 30, 5, 55, 1562.00),
(8, 1, '2003-12', 6, 6, 1, 11, 1320.00),
(9, 1, '2003-12', 18, 18, 4, 32, 1024.00),
(10, 2, '2003-12', 50, 50, 10, 40, 48.00),
(11, 1, '2003-12', 60, 60, 12, 48, 38.40),
(12, 1, '2003-12', 80, 80, 15, 65, 16.25),
(13, 2, '2003-12', 25, 0, 0, 25, 312.50),
(14, 1, '2003-12', 12, 0, 0, 12, 660.00),
(15, 1, '2003-12', 16, 0, 0, 16, 318.40);

INSERT INTO Inwentaryzacja (id_produktu, id_lokalizacji, id_pracownika, data_inwentaryzacji, ilosc_systemowa, ilosc_rzeczywista, status, uwagi) VALUES
(1, 4, 1, '2003-12-28', 26, 26, 'Zatwierdzona', 'Stan zgodny'),
(5, 2, 1, '2003-12-28', 12, 11, 'Wyjasnienie', 'Brak jednej sztuki po wydaniu awaryjnym'),
(13, 3, 5, '2003-12-29', 25, 25, 'Zatwierdzona', 'Stan zgodny'),
(8, 5, 4, '2003-12-29', 11, 12, 'Wyjasnienie', 'Nadwyżka po korekcie dostawy');
