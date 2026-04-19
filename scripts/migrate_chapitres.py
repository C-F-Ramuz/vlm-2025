#!/usr/bin/env python3
"""
migrate_chapitres.py — Crée les tables domaines et chapitres dans vlm.db
et met à jour la table exercices.

30 chapitres répartis en 5 domaines PER (MSN 31–35).
Pas de distinction VP/VG au niveau des chapitres (sera géré via les tags).

Usage:
    python scripts/migrate_chapitres.py
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "vlm.db"

# ─────────────────────────────────────────────────────────────────────
# DOMAINES — dans l'ordre PER
# ─────────────────────────────────────────────────────────────────────
DOMAINES = [
    {"id": 1, "code": "MSN31", "nom": "Nombres & Opérations",       "couleur": "#185FA5", "ordre": 1},
    {"id": 2, "code": "MSN32", "nom": "Géométrie",                   "couleur": "#534AB7", "ordre": 2},
    {"id": 3, "code": "MSN33", "nom": "Algèbre & Fonctions",         "couleur": "#0F6E56", "ordre": 3},
    {"id": 4, "code": "MSN34", "nom": "Grandeurs & Mesures",         "couleur": "#854F0B", "ordre": 4},
    {"id": 5, "code": "MSN35", "nom": "Statistiques & Probabilités", "couleur": "#993556", "ordre": 5},
]

# ─────────────────────────────────────────────────────────────────────
# CHAPITRES — dans l'ordre PER
# annees : indication orientative uniquement
# ─────────────────────────────────────────────────────────────────────
CHAPITRES = [
    # ── MSN 31 : Nombres & Opérations ─────────────────────────────────
    {"id":  1, "domaine_id": 1, "ordre": 1, "nom": "Nombres entiers & divisibilité",
     "detail": "ppmc · pgdc · facteurs premiers", "annees": "9H"},
    {"id":  2, "domaine_id": 1, "ordre": 2, "nom": "Entiers relatifs",
     "detail": "", "annees": "9H"},
    {"id":  3, "domaine_id": 1, "ordre": 3, "nom": "Fractions & pourcentages",
     "detail": "", "annees": "9–10H"},
    {"id":  4, "domaine_id": 1, "ordre": 4, "nom": "Priorité des opérations",
     "detail": "", "annees": "9H"},
    {"id":  5, "domaine_id": 1, "ordre": 5, "nom": "Puissances & racines",
     "detail": "", "annees": "10–11H"},
    {"id":  6, "domaine_id": 1, "ordre": 6, "nom": "Écriture scientifique",
     "detail": "", "annees": "10H"},
    {"id":  7, "domaine_id": 1, "ordre": 7, "nom": "Problèmes – 4 opérations",
     "detail": "", "annees": "9–10H"},

    # ── MSN 32 : Géométrie ─────────────────────────────────────────────
    {"id":  8, "domaine_id": 2, "ordre": 1, "nom": "Définitions géométriques",
     "detail": "vocabulaire & notations", "annees": "9H"},
    {"id":  9, "domaine_id": 2, "ordre": 2, "nom": "Constructions",
     "detail": "outils · techniques", "annees": "9–10H"},
    {"id": 10, "domaine_id": 2, "ordre": 3, "nom": "Isométries",
     "detail": "translation · rotation · réflexion", "annees": "9–10H"},
    {"id": 11, "domaine_id": 2, "ordre": 4, "nom": "Calculs d'angles",
     "detail": "", "annees": "9–10H"},
    {"id": 12, "domaine_id": 2, "ordre": 5, "nom": "Théorème de Pythagore",
     "detail": "", "annees": "10H"},
    {"id": 13, "domaine_id": 2, "ordre": 6, "nom": "Triangles semblables & Thalès",
     "detail": "", "annees": "11H"},
    {"id": 14, "domaine_id": 2, "ordre": 7, "nom": "Théorèmes métriques",
     "detail": "", "annees": "11H"},
    {"id": 15, "domaine_id": 2, "ordre": 8, "nom": "Trigonométrie",
     "detail": "", "annees": "11H"},

    # ── MSN 33 : Algèbre & Fonctions ───────────────────────────────────
    {"id": 16, "domaine_id": 3, "ordre": 1, "nom": "Fonctions & proportionnalité",
     "detail": "", "annees": "9–10H"},
    {"id": 17, "domaine_id": 3, "ordre": 2, "nom": "Droites",
     "detail": "équation · représentation graphique", "annees": "10H"},
    {"id": 18, "domaine_id": 3, "ordre": 3, "nom": "Calcul littéral",
     "detail": "", "annees": "10H"},
    {"id": 19, "domaine_id": 3, "ordre": 4, "nom": "Produits remarquables",
     "detail": "", "annees": "11H"},
    {"id": 20, "domaine_id": 3, "ordre": 5, "nom": "Factorisation",
     "detail": "", "annees": "11H"},
    {"id": 21, "domaine_id": 3, "ordre": 6, "nom": "Équations du 1er degré",
     "detail": "problèmes inclus", "annees": "10–11H"},
    {"id": 22, "domaine_id": 3, "ordre": 7, "nom": "Systèmes d'équations",
     "detail": "", "annees": "11H"},
    {"id": 23, "domaine_id": 3, "ordre": 8, "nom": "Équations du 2ème degré",
     "detail": "paraboles incluses", "annees": "11H"},

    # ── MSN 34 : Grandeurs & Mesures ───────────────────────────────────
    {"id": 24, "domaine_id": 4, "ordre": 1, "nom": "Unités & conversions",
     "detail": "", "annees": "9–10H"},
    {"id": 25, "domaine_id": 4, "ordre": 2, "nom": "Aires & périmètres",
     "detail": "", "annees": "9–10H"},
    {"id": 26, "domaine_id": 4, "ordre": 3, "nom": "Volumes",
     "detail": "", "annees": "10–11H"},
    {"id": 27, "domaine_id": 4, "ordre": 4, "nom": "Développements (patrons)",
     "detail": "", "annees": "10H"},
    {"id": 28, "domaine_id": 4, "ordre": 5, "nom": "Vitesse & masse volumique",
     "detail": "", "annees": "10H"},

    # ── MSN 35 : Statistiques & Probabilités ───────────────────────────
    {"id": 29, "domaine_id": 5, "ordre": 1, "nom": "Statistiques descriptives",
     "detail": "tableaux · diagrammes · moyenne · médiane · étendue", "annees": "9–11H"},
    {"id": 30, "domaine_id": 5, "ordre": 2, "nom": "Probabilités",
     "detail": "expériences aléatoires · fréquences · calcul", "annees": "10–11H"},
]


def migrate(conn: sqlite3.Connection):
    cur = conn.cursor()

    # ── 1. Table domaines ──────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS domaines (
            id      INTEGER PRIMARY KEY,
            code    TEXT NOT NULL UNIQUE,
            nom     TEXT NOT NULL,
            couleur TEXT NOT NULL DEFAULT '#333',
            ordre   INTEGER NOT NULL DEFAULT 0
        )
    """)

    # ── 2. Table chapitres ─────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS chapitres (
            id          INTEGER PRIMARY KEY,
            domaine_id  INTEGER NOT NULL REFERENCES domaines(id),
            ordre       INTEGER NOT NULL DEFAULT 0,
            nom         TEXT NOT NULL,
            detail      TEXT DEFAULT '',
            annees      TEXT DEFAULT ''
        )
    """)

    # ── 3. Mise à jour de la table exercices ───────────────────────────
    cols = {r[1] for r in cur.execute("PRAGMA table_info(exercices)").fetchall()}
    alterations = {
        "chapitre_id":    "INTEGER REFERENCES chapitres(id)",
        "annee_scolaire": "TEXT DEFAULT ''",
    }
    for col, definition in alterations.items():
        if col not in cols:
            cur.execute(f"ALTER TABLE exercices ADD COLUMN {col} {definition}")
            print(f"  + Colonne ajoutée : exercices.{col}")

    # ── 4. Seed domaines ───────────────────────────────────────────────
    cur.executemany(
        "INSERT OR IGNORE INTO domaines(id, code, nom, couleur, ordre) "
        "VALUES(:id, :code, :nom, :couleur, :ordre)",
        DOMAINES
    )

    # ── 5. Seed chapitres ──────────────────────────────────────────────
    cur.executemany(
        "INSERT OR IGNORE INTO chapitres(id, domaine_id, ordre, nom, detail, annees) "
        "VALUES(:id, :domaine_id, :ordre, :nom, :detail, :annees)",
        CHAPITRES
    )

    # ── 6. Migration des anciens exercices (si 'chapitre' existait) ────
    if "chapitre" in cols:
        cur.execute("""
            UPDATE exercices
            SET chapitre_id = chapitre
            WHERE chapitre_id IS NULL
              AND typeof(chapitre) = 'integer'
              AND chapitre BETWEEN 1 AND 30
        """)
        n = cur.rowcount
        if n:
            print(f"  → {n} exercice(s) migré(s) vers chapitre_id")

    conn.commit()

    # ── Résumé ─────────────────────────────────────────────────────────
    nb_dom  = cur.execute("SELECT COUNT(*) FROM domaines").fetchone()[0]
    nb_chap = cur.execute("SELECT COUNT(*) FROM chapitres").fetchone()[0]
    print(f"\n✅ Migration terminée : {nb_dom} domaines · {nb_chap} chapitres")

    # Affichage de l'arborescence pour vérification
    print()
    for d in cur.execute("SELECT id, code, nom FROM domaines ORDER BY ordre").fetchall():
        print(f"  {d[1]}  {d[2]}")
        for c in cur.execute(
            "SELECT ordre, nom, annees FROM chapitres WHERE domaine_id = ? ORDER BY ordre", (d[0],)
        ).fetchall():
            print(f"    {c[0]:02d}. {c[1]:<42} {c[2]}")


if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    migrate(conn)
    conn.close()
