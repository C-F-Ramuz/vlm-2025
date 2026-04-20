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

    # Compatibilité avec les anciens champs encore dans le INSERT
    meta.setdefault("chapitre", None)
    meta.setdefault("chapitre_nom", None)
    meta.setdefault("section", None)
    meta.setdefault("niveau", None)
    meta.setdefault("annee", None)
    meta.setdefault("source", None)
    
    # Normaliser les nouveaux champs
    meta["chapitre_id"] = meta.get("chapitre_id", None)
    chapitres_extra = meta.get("chapitres_extra", [])
    if not isinstance(chapitres_extra, list):
        chapitres_extra = []
    meta["chapitres_extra"] = json.dumps(chapitres_extra)
    meta["annee_scolaire"] = str(meta.get("annee_scolaire", ""))

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
            source         TEXT,
            fichier        TEXT,
            modifie_le     TEXT,
            latex_exercice TEXT,
            latex_solution TEXT,
            chapitre_id    INTEGER,
            chapitres_extra TEXT DEFAULT '[]',
            annee_scolaire TEXT DEFAULT ''
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
             auteur, annee, source, fichier, modifie_le, latex_exercice, latex_solution,
             chapitre_id, chapitres_extra, annee_scolaire)
        VALUES
            (:id, :titre, :chapitre, :chapitre_nom, :section, :niveau, :difficulte,
             :auteur, :annee, :source, :fichier, :modifie_le, :latex_exercice, :latex_solution,
             :chapitre_id, :chapitres_extra, :annee_scolaire)
        ON CONFLICT(id) DO UPDATE SET
            titre           = excluded.titre,
            chapitre        = excluded.chapitre,
            chapitre_nom    = excluded.chapitre_nom,
            section         = excluded.section,
            niveau          = excluded.niveau,
            difficulte      = excluded.difficulte,
            auteur          = excluded.auteur,
            annee           = excluded.annee,
            source          = excluded.source,
            fichier         = excluded.fichier,
            modifie_le      = excluded.modifie_le,
            latex_exercice  = excluded.latex_exercice,
            latex_solution  = excluded.latex_solution,
            chapitre_id     = excluded.chapitre_id,
            chapitres_extra = excluded.chapitres_extra,
            annee_scolaire  = excluded.annee_scolaire
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
    rows = conn.execute("""
        SELECT DISTINCT e.chapitre_id, c.nom
        FROM exercices e
        JOIN chapitres c ON c.id = e.chapitre_id
        WHERE e.chapitre_id IS NOT NULL
        ORDER BY e.chapitre_id
    """).fetchall()
    
    compteur_global = 1

    for chapitre, nom in rows:
        exercices = conn.execute("""
            SELECT e.id, e.titre, e.section, e.latex_exercice, e.latex_solution
            FROM exercices e
            WHERE e.chapitre_id = ?
            ORDER BY e.id
        """, (chapitre,)).fetchall()

        nom_latex = nom.replace('&', r'\&')
        lines = [
            f"\\phantomsection",
            f"\\addcontentsline{{toc}}{{chapter}}{{{nom_latex}}}",
            ""
        ]
        
        for idx, (ex_id, titre, section, latex_ex, latex_sol) in enumerate(exercices, start=compteur_global):
            latex_ex_num = re.sub(
                r'\\begin\{exercice\}\{[^}]*\}',
                f'\\\\begin{{exercice}}{{{idx}}}',
                latex_ex
            )
            latex_sol_num = re.sub(
                r'\\begin\{solution\}\{[^}]*\}',
                f'\\\\begin{{solution}}{{{idx}}}',
                latex_sol or ""
            )
            lines.append(latex_ex_num)
            lines.append(latex_sol_num)
            lines.append("")
        compteur_global += len(exercices)
            
        nom_clean = nom.lower().replace(' ','-').replace('è','e').replace('é','e').replace('ê','e').replace('à','a').replace('ô','o').replace('î','i').replace('ù','u')
        out_file = LATEX_OUT_DIR / f"ch{chapitre:02d}-{nom_clean}.tex"
        out_file.write_text("\n".join(lines), encoding="utf-8")
        print(f"  📄 Chapitre généré : {out_file.name} ({len(exercices)} exercices)")

# ── 4. Export JSON pour le site web ──────────────────────────────
def export_json(conn: sqlite3.Connection):
    exercices = conn.execute("""
        SELECT e.id, e.titre, e.chapitre_id, e.chapitres_extra,
               e.annee_scolaire, e.difficulte, e.auteur, e.modifie_le,
               e.latex_exercice,
               c.nom  AS chapitre_nom,
               d.code AS domaine_code,
               d.nom  AS domaine_nom
        FROM exercices e
        LEFT JOIN chapitres c ON c.id = e.chapitre_id
        LEFT JOIN domaines  d ON d.id = c.domaine_id
        ORDER BY e.chapitre_id, e.id
    """).fetchall()

    cols = ["id", "titre", "chapitre_id", "chapitres_extra",
            "annee_scolaire", "difficulte", "auteur", "modifie_le",
            "latex_exercice", "chapitre_nom", "domaine_code", "domaine_nom"]
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
def generate_individual_pdfs(conn: sqlite3.Connection):
    """Génère un fichier .tex par exercice pour compilation individuelle."""
    INDIV_DIR = BASE_DIR / "latex" / "individual"
    INDIV_DIR.mkdir(parents=True, exist_ok=True)

    template_path = BASE_DIR / "latex" / "templates" / "exercice_seul.tex"
    template = template_path.read_text(encoding="utf-8")

    exercices = conn.execute(
        "SELECT id, latex_exercice, latex_solution FROM exercices"
    ).fetchall()

    for ex_id, latex_ex, latex_sol in exercices:
        contenu = (latex_ex or "") + "\n" + (latex_sol or "")
        tex = template.replace("%%CONTENU%%", contenu)
        out = INDIV_DIR / f"{ex_id}.tex"
        out.write_text(tex, encoding="utf-8")

    print(f"  📄 {len(exercices)} fichiers .tex individuels générés")
    
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
        
        # Supprimer les exercices dont le fichier .tex n'existe plus
        ids_fichiers = set()
        for f in sorted(EXERCICES_DIR.rglob("*.tex")):
            meta = parse_exercise_file(f)
            if meta:
                ids_fichiers.add(meta["id"])
        
        ids_db = set(row[0] for row in conn.execute("SELECT id FROM exercices").fetchall())
        ids_supprimes = ids_db - ids_fichiers
        for ex_id in ids_supprimes:
            conn.execute("DELETE FROM tags WHERE exercice_id = ?", (ex_id,))
            conn.execute("DELETE FROM objectifs WHERE exercice_id = ?", (ex_id,))
            conn.execute("DELETE FROM exercices WHERE id = ?", (ex_id,))
            print(f"  🗑️  Supprimé de la base : {ex_id}")
        conn.commit()
        
        for f in tex_files:
            meta = parse_exercise_file(f)
            if meta:
                upsert_exercise(conn, meta)
                print(f"  ✅ {meta['id']} — {meta['titre']}")

        if not args.db_only:
            print("\n📝 Génération des chapitres LaTeX…")
            generate_latex_chapters(conn)
            
# Générer main.tex automatiquement
    chapitres_list = conn.execute("""
        SELECT DISTINCT e.chapitre_id, c.nom
        FROM exercices e
        JOIN chapitres c ON c.id = e.chapitre_id
        WHERE e.chapitre_id IS NOT NULL
        ORDER BY e.chapitre_id
    """).fetchall()
    
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
    
    print("\n📄 Génération des PDF individuels…")
    generate_individual_pdfs(conn)

    print("\n📦 Export JSON…")
    export_json(conn)

    conn.close()
    print("\n✨ Build terminé !")

if __name__ == "__main__":
    main()
