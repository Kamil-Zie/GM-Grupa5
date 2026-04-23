PRAGMA foreign_keys = ON;

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
    FOREIGN KEY (MaterialID) REFERENCES Materialy(MaterialID),
    FOREIGN KEY (MagazynID) REFERENCES Magazyny(MagazynID)
);

CREATE TABLE KontaKosztowe (
    KontoID INTEGER PRIMARY KEY AUTOINCREMENT,
    Kod TEXT NOT NULL UNIQUE,
    Opis TEXT,
    Typ TEXT NOT NULL CHECK (Typ IN ('Przychod', 'Koszt'))
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

CREATE INDEX idx_materialy_indeks ON Materialy(Indeks);
CREATE INDEX idx_magazyny_kod ON Magazyny(Kod);
CREATE INDEX idx_operacje_data ON OperacjeMagazynowe(DataOperacji);
CREATE INDEX idx_operacje_typ ON OperacjeMagazynowe(TypOperacji);
CREATE INDEX idx_operacje_material ON OperacjeMagazynowe(MaterialID);
CREATE INDEX idx_operacje_magazyn ON OperacjeMagazynowe(MagazynID);
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


INSERT INTO OperacjeMagazynowe (MaterialID, MagazynID, TypOperacji, Ilo, DataOperacji, Dostawca, ZlecPracownika, Uwagi) VALUES
-- PRZYJĘCIA - PAŹDZIERNIK 2025
(1, 2, 'Przyjcie', 17, '2025-10-15', 'Grene', NULL, 'Partia P/01'),      -- +17 (dla wydania 2+15)
(2, 1, 'Przyjcie', 13, '2025-10-17', 'STO-ART S.A.', NULL, 'Partia P/02'), -- +13 (dla wydań 1+1+11)
(3, 1, 'Przyjcie', 16, '2025-10-19', 'Hydro-Max', NULL, 'Partia P/03'),    -- +16 (dla wydań 3+3+10)
(4, 2, 'Przyjcie', 24, '2025-10-21', 'Moto-Części', NULL, 'Partia P/04'),  -- +24 (dla wydań 2+22)
(5, 1, 'Przyjcie', 12, '2025-10-23', 'Tech-Serwis', NULL, 'Partia P/05'),  -- +12 (dla wydań 2+10)
(6, 1, 'Przyjcie', 18, '2025-10-25', 'Grene', NULL, 'Partia P/06'),       -- +18 (dla wydań 4+14)
(7, 2, 'Przyjcie', 35, '2025-10-27', 'STO-ART S.A.', NULL, 'Partia P/07'), -- +35 (dla wydań 5+30)
(8, 1, 'Przyjcie', 10, '2025-10-29', 'Hydro-Max', NULL, 'Partia P/08'),    -- +10 (dla wydań 1+9)

-- PRZYJĘCIA - LISTOPAD 2025  
(9, 1, 'Przyjcie', 22, '2025-11-02', 'Moto-Części', NULL, 'Partia P/09'),  -- +22 (dla wydań 2+20)
(10, 2, 'Przyjcie', 60, '2025-11-04', 'Tech-Serwis', NULL, 'Partia P/10'), -- +60 (dla wydań 10+50)
(11, 1, 'Przyjcie', 72, '2025-11-06', 'Grene', NULL, 'Partia P/11'),      -- +72 (dla wydań 12+60)
(12, 1, 'Przyjcie', 90, '2025-11-08', 'STO-ART S.A.', NULL, 'Partia P/12'), -- +90 (dla wydań 15+75)
(13, 2, 'Przyjcie', 30, '2025-11-10', 'Hydro-Max', NULL, 'Partia P/13'),   -- +30 (rezerwa)
(14, 1, 'Przyjcie', 15, '2025-11-12', 'Moto-Części', NULL, 'Partia P/14'), -- +15 (rezerwa)
(15, 1, 'Przyjcie', 20, '2025-11-14', 'Tech-Serwis', NULL, 'Partia P/15'), -- +20 (rezerwa)

-- WYDAJANIA - LISTOPAD 2025 (wszystkie PO przyjęciach i w granicach ilości)
(1, 2, 'Wydanie', 2, '2025-11-07', NULL, 'PKNS680 Marantów / 5210', 'Rozchód R/01'),   -- z 17→15
(2, 1, 'Wydanie', 1, '2025-11-09', NULL, 'PKNS690 Marantów / 5220', 'Rozchód R/02'),   -- z 13→12
(3, 1, 'Wydanie', 3, '2025-11-11', NULL, 'UR-01 / 5230', 'Rozchód R/03'),              -- z 16→13
(4, 2, 'Wydanie', 2, '2025-11-13', NULL, 'SERW-02 / 5240', 'Rozchód R/04'),            -- z 24→22
(5, 1, 'Wydanie', 2, '2025-11-15', NULL, 'BHP-03 / 5250', 'Rozchód R/05'),             -- z 12→10
(6, 1, 'Wydanie', 4, '2025-11-17', NULL, 'PKNS680 Marantów / 5210', 'Rozchód R/06'),   -- z 18→14
(7, 2, 'Wydanie', 5, '2025-11-19', NULL, 'PKNS690 Marantów / 5220', 'Rozchód R/07'),   -- z 35→30

-- KOLEJNE WYDAJANIA (wszystkie w granicach)
(8, 1, 'Wydanie', 1, '2025-11-21', NULL, 'UR-01 / 5230', 'Rozchód R/08'),              -- z 10→9
(9, 1, 'Wydanie', 2, '2025-11-23', NULL, 'SERW-02 / 5240', 'Rozchód R/09'),            -- z 22→20
(10, 2, 'Wydanie', 10, '2025-11-25', NULL, 'BHP-03 / 5250', 'Rozchód R/10'),           -- z 60→50
(11, 1, 'Wydanie', 12, '2025-11-27', NULL, 'PKNS680 Marantów / 5210', 'Rozchód R/11'), -- z 72→60
(12, 1, 'Wydanie', 15, '2025-11-29', NULL, 'PKNS690 Marantów / 5220', 'Rozchód R/12'), -- z 90→75

-- GRUDZIEŃ 2025 - wydania z zapasów
(1, 2, 'Wydanie', 2, '2025-12-01', NULL, 'UR-01 / 5230', 'Rozchód R/13'),              -- z 15→13
(2, 1, 'Wydanie', 1, '2025-12-03', NULL, 'SERW-02 / 5240', 'Rozchód R/14'),            -- z 12→11
(3, 1, 'Wydanie', 3, '2025-12-05', NULL, 'BHP-03 / 5250', 'Rozchód R/15'),             -- z 13→10
(4, 2, 'Wydanie', 2, '2025-12-07', NULL, 'PKNS680 Marantów / 5210', 'Rozchód R/16'),   -- z 22→20
(5, 1, 'Wydanie', 2, '2025-12-09', NULL, 'PKNS690 Marantów / 5220', 'Rozchód R/17'),   -- z 10→8
(6, 1, 'Wydanie', 4, '2025-12-11', NULL, 'UR-01 / 5230', 'Rozchód R/18'),              -- z 14→10
(7, 2, 'Wydanie', 5, '2025-12-13', NULL, 'SERW-02 / 5240', 'Rozchód R/19'),            -- z 30→25
(8, 1, 'Wydanie', 1, '2025-12-15', NULL, 'BHP-03 / 5250', 'Rozchód R/20'),             -- z 9→8
(9, 1, 'Wydanie', 2, '2025-12-17', NULL, 'PKNS680 Marantów / 5210', 'Rozchód R/21'),   -- z 20→18
(10, 2, 'Wydanie', 10, '2025-12-19', NULL, 'PKNS690 Marantów / 5220', 'Rozchód R/22'), -- z 50→40
(11, 1, 'Wydanie', 12, '2025-12-21', NULL, 'UR-01 / 5230', 'Rozchód R/23'),            -- z 60→48
(12, 1, 'Wydanie', 15, '2025-12-23', NULL, 'SERW-02 / 5240', 'Rozchód R/24');          -- z 75→60


