#!/usr/bin/env python3
import os
import re
import json
import sqlite3
import argparse
import yaml
from pathlib import Path
from datetime import datetime

BASE_DIR      = Path(__file__).parent.parent
EXERCICES_DIR = BASE_DIR / "exercices"
LATEX_OUT_DIR = BASE_DIR / "latex" / "generated"
DB_PATH       = BASE_DIR / "vlm.db"
JSON_PATH     = BASE_DIR / "site" / "exercices.json"

LATEX_OUT_DIR.mkdir(parents=True, exist_ok=True)
(BASE_DIR / "site").mkdir(parents=True, exist_ok=True)

def parse_exercise_file(filepath: Path) -> dict:
    content = filepath.read_text(encoding="utf-8")
    yaml_match = re.search(r"^% ---\n(.*?)^% ---", content, re.MULTILINE | re.DOTALL)
    if not yaml_match:
        print(f"  ⚠️  Pas de métadonnées YAML dans {filepath.name}")
        return None
    raw_yaml = re.sub(r"^% ?", "", yaml_match.group(1), flags=re.MULTILINE)
    try:
        meta = yaml.safe_load(raw_yaml)
    except yaml.YAMLError as e:
        print(f"  ❌ Erreur YAML dans {filepath.name}: {e}")
        return None

    latex_body = content[yaml_match.end():].strip()
    ex_match  = re.search(r"\\begin\{exercice\}.*?\\end\{exercice\}", latex_body, re.DOTALL)
    sol_match = re.search(r"\\begin\{solution\}.*?\\end\{solution\}", latex_body, re.DOTALL)

    meta["latex_exercice"] = ex_match.group(0)  if ex_match  else ""
    meta["latex_solution"] = sol_match.group(0) if sol_match else ""
    meta["fichier"]        = str(filepath.relative_to(BASE_DIR))
    meta["modifie_le"]     = datetime.fromtimestamp(filepath.stat().st_mtime).isoformat()

    if isinstance(meta.get("tags"), str):
        meta["tags"] = [t.strip() for t in meta["tags"].split(",")]
    meta["tags"] = meta.get("tags") or []

    meta.setdefault("chapitre_id",   None)
    meta.setdefault("chapitre_nom",  None)
    meta.setdefault("annee_scolaire", "")
    meta.setdefault("difficulte",    1)
    meta.setdefault("auteur",        "")

    if meta["chapitre_id"] is not None:
        meta["chapitre_id"] = int(meta["chapitre_id"])

    return meta

def init_db(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS exercices (
            id             TEXT PRIMARY KEY,
            titre          TEXT,
            chapitre_id    INTEGER,
            chapitre_nom   TEXT,
            annee_scolaire TEXT DEFAULT '',
            difficulte     INTEGER,
            auteur         TEXT,
            fichier        TEXT,
            modifie_le     TEXT,
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
    conn.execute("""
        INSERT INTO exercices
            (id, titre, chapitre_id, chapitre_nom, annee_scolaire,
             difficulte, auteur, fichier, modifie_le, latex_exercice, latex_solution)
        VALUES
            (:id, :titre, :chapitre_id, :chapitre_nom, :annee_scolaire,
             :difficulte, :auteur, :fichier, :modifie_le, :latex_exercice, :latex_solution)
        ON CONFLICT(id) DO UPDATE SET
            titre          = excluded.titre,
            chapitre_id    = excluded.chapitre_id,
            chapitre_nom   = excluded.chapitre_nom,
            annee_scolaire = excluded.annee_scolaire,
            difficulte     = excluded.difficulte,
            auteur         = excluded.auteur,
            fichier        = excluded.fichier,
            modifie_le     = excluded.modifie_le,
            latex_exercice = excluded.latex_exercice,
            latex_solution = excluded.latex_solution
    """, meta)

    conn.execute("DELETE FROM tags WHERE exercice_id = ?", (meta["id"],))
    conn.executemany(
        "INSERT INTO tags (exercice_id, tag) VALUES (?, ?)",
        [(meta["id"], tag) for tag in meta.get("tags", [])]
    )
    conn.execute("DELETE FROM objectifs WHERE exercice_id = ?", (meta["id"],))
    conn.executemany(
        "INSERT INTO objectifs (exercice_id, objectif) VALUES (?, ?)",
        [(meta["id"], obj) for obj in (meta.get("objectifs") or [])]
    )
    conn.commit()

def nettoyer_nom(nom):
    return (nom.lower()
        .replace(' ', '-').replace('&', '')
        .replace('è','e').replace('é','e').replace('ê','e')
        .replace('à','a').replace('â','a').replace('ô','o')
        .replace('î','i').replace('ù','u').replace('--','-'))

def generate_latex_chapters(conn: sqlite3.Connection):
    rows = conn.execute("""
        SELECT DISTINCT chapitre_id, chapitre_nom
        FROM exercices
        WHERE chapitre_id IS NOT NULL
        ORDER BY chapitre_id
    """).fetchall()

    compteur_global = 1

    for chapitre_id, chapitre_nom in rows:
        exercices = conn.execute("""
            SELECT id, titre, latex_exercice, latex_solution
            FROM exercices
            WHERE chapitre_id = ?
            ORDER BY difficulte, id
        """, (chapitre_id,)).fetchall()

        nom_latex = (chapitre_nom or "").replace('&', r'\&')
        lines = [
            f"\\cleardoublepage",
            f"\\phantomsection",
            f"\\addcontentsline{{toc}}{{chapter}}{{{nom_latex}}}",
            ""
        ]

        for idx, (ex_id, titre, latex_ex, latex_sol) in enumerate(exercices, start=compteur_global):
            latex_ex_num = re.sub(
                r'\\begin\{exercice\}\{[^}]*\}',
                f'\\\\begin{{exercice}}{{{idx}}}',
                latex_ex or ""
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

        nom_clean = nettoyer_nom(chapitre_nom or f"ch{chapitre_id}")
        out_file = LATEX_OUT_DIR / f"ch{chapitre_id:02d}-{nom_clean}.tex"
        out_file.write_text("\n".join(lines), encoding="utf-8")
        print(f"  📄 Chapitre généré : {out_file.name} ({len(exercices)} exercices)")

    # Générer main.tex automatiquement
    inputs = "\n".join([
        f"\\input{{latex/generated/ch{cid:02d}-{nettoyer_nom(nom or '')}}}"
        for cid, nom in rows
    ])
    main_template = BASE_DIR / "latex" / "templates" / "main_template.tex"
    main_out      = BASE_DIR / "latex" / "templates" / "main.tex"
    template = main_template.read_text(encoding="utf-8")
    template = template.replace("%%CHAPITRES%%", inputs)
    main_out.write_text(template, encoding="utf-8")
    print(f"  📄 main.tex généré avec {len(rows)} chapitres")

def generate_individual_pdfs(conn: sqlite3.Connection):
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
        (INDIV_DIR / f"{ex_id}.tex").write_text(tex, encoding="utf-8")
    print(f"  📄 {len(exercices)} fichiers .tex individuels générés")

def export_json(conn: sqlite3.Connection):
    exercices = conn.execute("""
        SELECT id, titre, chapitre_id, chapitre_nom,
               annee_scolaire, difficulte, auteur, modifie_le, latex_exercice
        FROM exercices
        ORDER BY chapitre_id, difficulte, id
    """).fetchall()

    cols = ["id", "titre", "chapitre_id", "chapitre_nom",
            "annee_scolaire", "difficulte", "auteur", "modifie_le", "latex_exercice"]
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

        ids_fichiers = set()
        for f in tex_files:
            meta = parse_exercise_file(f)
            if meta:
                ids_fichiers.add(meta["id"])

        ids_db = set(row[0] for row in conn.execute("SELECT id FROM exercices").fetchall())
        for ex_id in ids_db - ids_fichiers:
            conn.execute("DELETE FROM tags WHERE exercice_id = ?", (ex_id,))
            conn.execute("DELETE FROM objectifs WHERE exercice_id = ?", (ex_id,))
            conn.execute("DELETE FROM exercices WHERE id = ?", (ex_id,))
            print(f"  🗑️  Supprimé : {ex_id}")
        conn.commit()

        for f in tex_files:
            meta = parse_exercise_file(f)
            if meta:
                upsert_exercise(conn, meta)
                print(f"  ✅ {meta['id']} — {meta['titre']}")

        if not args.db_only:
            print("\n📝 Génération des chapitres LaTeX…")
            generate_latex_chapters(conn)
            print("\n📄 Génération des PDF individuels…")
            generate_individual_pdfs(conn)

    print("\n📦 Export JSON…")
    export_json(conn)

    conn.close()
    print("\n✨ Build terminé !")

if __name__ == "__main__":
    main()