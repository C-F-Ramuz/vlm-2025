#!/usr/bin/env python3
"""
vlm_build.py — Script principal du projet VLM Math
---------------------------------------------------
Fonctions :
  1. Parser les fichiers .tex et extraire les métadonnées YAML
  2. Construire/mettre à jour la base SQLite
  3. Générer les fichiers .tex de chapitre (pour la compilation)
  4. Exporter un JSON pour le site web

Usage :
  python vlm_build.py              # Build complet
  python vlm_build.py --db-only    # Seulement la base de données
  python vlm_build.py --json-only  # Seulement l'export JSON
"""

import os
import re
import json
import sqlite3
import argparse
import yaml
from pathlib import Path
from datetime import datetime

# ── Configuration ────────────────────────────────────────────────
BASE_DIR      = Path(__file__).parent.parent
EXERCICES_DIR = BASE_DIR / "exercices"
LATEX_OUT_DIR = BASE_DIR / "latex" / "generated"
DB_PATH       = BASE_DIR / "vlm.db"
JSON_PATH     = BASE_DIR / "site" / "exercices.json"

LATEX_OUT_DIR.mkdir(parents=True, exist_ok=True)
(BASE_DIR / "site").mkdir(parents=True, exist_ok=True)

# ── 1. Parser un fichier .tex ─────────────────────────────────────
def parse_exercise_file(filepath: Path) -> dict | None:
    """
    Extrait les métadonnées YAML (dans les commentaires % --- ... ---)
    et le contenu LaTeX brut du fichier.
    """
    content = filepath.read_text(encoding="utf-8")

    # Extraire le bloc YAML entre % --- et % ---
    yaml_match = re.search(r"^% ---\n(.*?)^% ---", content, re.MULTILINE | re.DOTALL)
    if not yaml_match:
        print(f"  ⚠️  Pas de métadonnées YAML dans {filepath.name}")
        return None

    # Nettoyer les % en début de ligne YAML
    raw_yaml = re.sub(r"^% ?", "", yaml_match.group(1), flags=re.MULTILINE)

    try:
        meta = yaml.safe_load(raw_yaml)
    except yaml.YAMLError as e:
        print(f"  ❌ Erreur YAML dans {filepath.name}: {e}")
        return None

    # Extraire le corps LaTeX (après le bloc YAML)
    latex_body = content[yaml_match.end():].strip()

    # Séparer exercice et solution
    ex_match  = re.search(r"\\begin\{exercice\}.*?\\end\{exercice\}", latex_body, re.DOTALL)
    sol_match = re.search(r"\\begin\{solution\}.*?\\end\{solution\}", latex_body, re.DOTALL)

    meta["latex_exercice"] = ex_match.group(0)  if ex_match  else ""
    meta["latex_solution"] = sol_match.group(0) if sol_match else ""
    meta["fichier"]        = str(filepath.relative_to(BASE_DIR))
    meta["modifie_le"]     = datetime.fromtimestamp(filepath.stat().st_mtime).isoformat()

    # Normaliser les tags (toujours une liste)
    if isinstance(meta.get("tags"), str):
        meta["tags"] = [t.strip() for t in meta["tags"].split(",")]
    meta["tags"] = meta.get("tags") or []

    return meta

# ── 2. Base de données SQLite ─────────────────────────────────────
def init_db(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS exercices (
            id            TEXT PRIMARY KEY,
            titre         TEXT,
            chapitre      INTEGER,
            chapitre_nom  TEXT,
            section       TEXT,
            niveau        TEXT,
            difficulte    INTEGER,
            auteur        TEXT,
            annee         INTEGER,
            source        TEXT,
            fichier       TEXT,
            modifie_le    TEXT,
            latex_exercice TEXT,
            latex_solution TEXT
        );

        CREATE TABLE IF NOT EXISTS tags (
            exercice_id TEXT,
            tag         TEXT,
            FOREIGN KEY (exercice_id) REFERENCES exercices(id)
        );

        CREATE TABLE IF NOT EXISTS objectifs (
            exercice_id TEXT,
            objectif    TEXT,
            FOREIGN KEY (exercice_id) REFERENCES exercices(id)
        );
    """)
    conn.commit()

def upsert_exercise(conn: sqlite3.Connection, meta: dict):
    """Insère ou met à jour un exercice dans la base."""
    conn.execute("""
        INSERT INTO exercices
            (id, titre, chapitre, chapitre_nom, section, niveau, difficulte,
             auteur, annee, source, fichier, modifie_le, latex_exercice, latex_solution)
        VALUES
            (:id, :titre, :chapitre, :chapitre_nom, :section, :niveau, :difficulte,
             :auteur, :annee, :source, :fichier, :modifie_le, :latex_exercice, :latex_solution)
        ON CONFLICT(id) DO UPDATE SET
            titre          = excluded.titre,
            chapitre       = excluded.chapitre,
            chapitre_nom   = excluded.chapitre_nom,
            section        = excluded.section,
            niveau         = excluded.niveau,
            difficulte     = excluded.difficulte,
            auteur         = excluded.auteur,
            annee          = excluded.annee,
            source         = excluded.source,
            fichier        = excluded.fichier,
            modifie_le     = excluded.modifie_le,
            latex_exercice = excluded.latex_exercice,
            latex_solution = excluded.latex_solution
    """, meta)

    # Tags : supprimer puis réinsérer
    conn.execute("DELETE FROM tags WHERE exercice_id = ?", (meta["id"],))
    conn.executemany(
        "INSERT INTO tags (exercice_id, tag) VALUES (?, ?)",
        [(meta["id"], tag) for tag in meta.get("tags", [])]
    )

    # Objectifs
    conn.execute("DELETE FROM objectifs WHERE exercice_id = ?", (meta["id"],))
    conn.executemany(
        "INSERT INTO objectifs (exercice_id, objectif) VALUES (?, ?)",
        [(meta["id"], obj) for obj in (meta.get("objectifs") or [])]
    )

    conn.commit()

# ── 3. Génération des fichiers .tex de chapitre ───────────────────
def generate_latex_chapters(conn: sqlite3.Connection):
    """
    Génère un fichier .tex par chapitre contenant tous les exercices
    (et leurs solutions, car le template main.tex gère la visibilité).
    """
    rows = conn.execute(
        "SELECT DISTINCT chapitre, chapitre_nom FROM exercices ORDER BY chapitre"
    ).fetchall()

    for chapitre, nom in rows:
        exercices = conn.execute("""
            SELECT e.id, e.titre, e.section, e.latex_exercice, e.latex_solution
            FROM exercices e
            WHERE e.chapitre = ?
            ORDER BY e.id
        """, (chapitre,)).fetchall()

        lines = [
            f"\\chapter{{{nom}}}",
            ""
        ]
        current_section = None
        for ex_id, titre, section, latex_ex, latex_sol in exercices:
            if section != current_section:
                lines.append(f"\\section{{{section}}}")
                current_section = section
            lines.append(latex_ex)
            lines.append(latex_sol)   # invisible côté élève grâce à \ifdefined\AVECSOLUTIONS
            lines.append("")

        nom_clean = nom.lower().replace(' ','-').replace('è','e').replace('é','e').replace('ê','e').replace('à','a').replace('ô','o').replace('î','i').replace('ù','u')
        out_file = LATEX_OUT_DIR / f"ch{chapitre:02d}-{nom_clean}.tex"
        out_file.write_text("\n".join(lines), encoding="utf-8")
        print(f"  📄 Chapitre généré : {out_file.name} ({len(exercices)} exercices)")

# ── 4. Export JSON pour le site web ──────────────────────────────
def export_json(conn: sqlite3.Connection):
    exercices = conn.execute("""
        SELECT id, titre, chapitre, chapitre_nom, section,
               niveau, difficulte, auteur, annee, modifie_le
        FROM exercices
        ORDER BY chapitre, id
    """).fetchall()

    cols = ["id","titre","chapitre","chapitre_nom","section",
            "niveau","difficulte","auteur","annee","modifie_le"]
    result = []
    for row in exercices:
        ex = dict(zip(cols, row))
        ex["tags"] = [r[0] for r in conn.execute(
            "SELECT tag FROM tags WHERE exercice_id = ? ORDER BY tag", (ex["id"],)
        ).fetchall()]
        ex["objectifs"] = [r[0] for r in conn.execute(
            "SELECT objectif FROM objectifs WHERE exercice_id = ?", (ex["id"],)
        ).fetchall()]
        result.append(ex)

    JSON_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  📦 JSON exporté : {JSON_PATH} ({len(result)} exercices)")

# ── Main ──────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="VLM Build Tool")
    parser.add_argument("--db-only",   action="store_true")
    parser.add_argument("--json-only", action="store_true")
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    if not args.json_only:
        print("\n🔍 Parsing des exercices…")
        tex_files = sorted(EXERCICES_DIR.rglob("*.tex"))
        for f in tex_files:
            meta = parse_exercise_file(f)
            if meta:
                upsert_exercise(conn, meta)
                print(f"  ✅ {meta['id']} — {meta['titre']}")

        if not args.db_only:
            print("\n📝 Génération des chapitres LaTeX…")
            generate_latex_chapters(conn)
            
# Générer main.tex automatiquement
    chapitres_list = conn.execute(
        "SELECT DISTINCT chapitre, chapitre_nom FROM exercices ORDER BY chapitre"
    ).fetchall()
    
    inputs = "\n".join([
        f"\\input{{latex/generated/ch{chapitre:02d}-{nom.lower().replace(' ','-').replace('è','e').replace('é','e').replace('ê','e').replace('à','a').replace('ô','o').replace('î','i').replace('ù','u')}}}"
        for chapitre, nom in chapitres_list
    ])
    
    main_template = BASE_DIR / "latex" / "templates" / "main_template.tex"
    main_out = BASE_DIR / "latex" / "templates" / "main.tex"
    
    template = main_template.read_text(encoding="utf-8")
    template = template.replace("%%CHAPITRES%%", inputs)
    main_out.write_text(template, encoding="utf-8")
    print(f"  📄 main.tex généré avec {len(chapitres_list)} chapitres")

    print("\n📦 Export JSON…")
    export_json(conn)

    conn.close()
    print("\n✨ Build terminé !")

if __name__ == "__main__":
    main()
