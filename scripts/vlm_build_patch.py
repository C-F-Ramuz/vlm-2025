#!/usr/bin/env python3
"""
vlm_build_patch.py — Patch de vlm_build.py pour les nouveaux champs.
Lance : python3 scripts/vlm_build_patch.py
"""
from pathlib import Path

TARGET = Path(__file__).parent / "vlm_build.py"

PATCHES = [
    # ── 1. parse_exercise_file() : normaliser les nouveaux champs ──────
    (
        "parse_exercise_file",
        '    # Normaliser les tags (toujours une liste)\n'
        '    if isinstance(meta.get("tags"), str):\n'
        '        meta["tags"] = [t.strip() for t in meta["tags"].split(",")]\n'
        '    meta["tags"] = meta.get("tags") or []\n'
        '\n'
        '    return meta',
        '    # Normaliser les tags (toujours une liste)\n'
        '    if isinstance(meta.get("tags"), str):\n'
        '        meta["tags"] = [t.strip() for t in meta["tags"].split(",")]\n'
        '    meta["tags"] = meta.get("tags") or []\n'
        '\n'
        '    # Normaliser les nouveaux champs\n'
        '    meta["chapitre_id"] = meta.get("chapitre_id", None)\n'
        '    chapitres_extra = meta.get("chapitres_extra", [])\n'
        '    if not isinstance(chapitres_extra, list):\n'
        '        chapitres_extra = []\n'
        '    meta["chapitres_extra"] = json.dumps(chapitres_extra)\n'
        '    meta["annee_scolaire"] = str(meta.get("annee_scolaire", ""))\n'
        '\n'
        '    return meta',
    ),
    # ── 2. init_db() : ajouter chapitres_extra au CREATE TABLE ─────────
    (
        "init_db",
        '            source        TEXT,\n'
        '            fichier       TEXT,\n'
        '            modifie_le    TEXT,\n'
        '            latex_exercice TEXT,\n'
        '            latex_solution TEXT\n'
        '        );',
        '            source         TEXT,\n'
        '            fichier        TEXT,\n'
        '            modifie_le     TEXT,\n'
        '            latex_exercice TEXT,\n'
        '            latex_solution TEXT,\n'
        '            chapitre_id    INTEGER,\n'
        '            chapitres_extra TEXT DEFAULT \'[]\',\n'
        '            annee_scolaire TEXT DEFAULT \'\'\n'
        '        );',
    ),
    # ── 3. upsert_exercise() : ajouter les champs dans INSERT ──────────
    (
        "upsert_exercise",
        '    conn.execute("""\n'
        '        INSERT INTO exercices\n'
        '            (id, titre, chapitre, chapitre_nom, section, niveau, difficulte,\n'
        '             auteur, annee, source, fichier, modifie_le, latex_exercice, latex_solution)\n'
        '        VALUES\n'
        '            (:id, :titre, :chapitre, :chapitre_nom, :section, :niveau, :difficulte,\n'
        '             :auteur, :annee, :source, :fichier, :modifie_le, :latex_exercice, :latex_solution)\n'
        '        ON CONFLICT(id) DO UPDATE SET\n'
        '            titre          = excluded.titre,\n'
        '            chapitre       = excluded.chapitre,\n'
        '            chapitre_nom   = excluded.chapitre_nom,\n'
        '            section        = excluded.section,\n'
        '            niveau         = excluded.niveau,\n'
        '            difficulte     = excluded.difficulte,\n'
        '            auteur         = excluded.auteur,\n'
        '            annee          = excluded.annee,\n'
        '            source         = excluded.source,\n'
        '            fichier        = excluded.fichier,\n'
        '            modifie_le     = excluded.modifie_le,\n'
        '            latex_exercice = excluded.latex_exercice,\n'
        '            latex_solution = excluded.latex_solution\n'
        '    """, meta)',
        '    conn.execute("""\n'
        '        INSERT INTO exercices\n'
        '            (id, titre, chapitre, chapitre_nom, section, niveau, difficulte,\n'
        '             auteur, annee, source, fichier, modifie_le, latex_exercice, latex_solution,\n'
        '             chapitre_id, chapitres_extra, annee_scolaire)\n'
        '        VALUES\n'
        '            (:id, :titre, :chapitre, :chapitre_nom, :section, :niveau, :difficulte,\n'
        '             :auteur, :annee, :source, :fichier, :modifie_le, :latex_exercice, :latex_solution,\n'
        '             :chapitre_id, :chapitres_extra, :annee_scolaire)\n'
        '        ON CONFLICT(id) DO UPDATE SET\n'
        '            titre           = excluded.titre,\n'
        '            chapitre        = excluded.chapitre,\n'
        '            chapitre_nom    = excluded.chapitre_nom,\n'
        '            section         = excluded.section,\n'
        '            niveau          = excluded.niveau,\n'
        '            difficulte      = excluded.difficulte,\n'
        '            auteur          = excluded.auteur,\n'
        '            annee           = excluded.annee,\n'
        '            source          = excluded.source,\n'
        '            fichier         = excluded.fichier,\n'
        '            modifie_le      = excluded.modifie_le,\n'
        '            latex_exercice  = excluded.latex_exercice,\n'
        '            latex_solution  = excluded.latex_solution,\n'
        '            chapitre_id     = excluded.chapitre_id,\n'
        '            chapitres_extra = excluded.chapitres_extra,\n'
        '            annee_scolaire  = excluded.annee_scolaire\n'
        '    """, meta)',
    ),
    # ── 4. export_json() : SELECT avec JOIN domaines/chapitres ─────────
    (
        "export_json",
        '    exercices = conn.execute("""\n'
        '        SELECT id, titre, chapitre, chapitre_nom, section,\n'
        '               niveau, difficulte, auteur, annee, modifie_le,\n'
        '               latex_exercice\n'
        '        FROM exercices\n'
        '        ORDER BY chapitre, id\n'
        '    """).fetchall()\n'
        '\n'
        '    cols = ["id","titre","chapitre","chapitre_nom","section",\n'
        '            "niveau","difficulte","auteur","annee","modifie_le",\n'
        '            "latex_exercice"]',
        '    exercices = conn.execute("""\n'
        '        SELECT e.id, e.titre, e.chapitre_id, e.chapitres_extra,\n'
        '               e.annee_scolaire, e.difficulte, e.auteur, e.modifie_le,\n'
        '               e.latex_exercice,\n'
        '               c.nom  AS chapitre_nom,\n'
        '               d.code AS domaine_code,\n'
        '               d.nom  AS domaine_nom\n'
        '        FROM exercices e\n'
        '        LEFT JOIN chapitres c ON c.id = e.chapitre_id\n'
        '        LEFT JOIN domaines  d ON d.id = c.domaine_id\n'
        '        ORDER BY e.chapitre_id, e.id\n'
        '    """).fetchall()\n'
        '\n'
        '    cols = ["id", "titre", "chapitre_id", "chapitres_extra",\n'
        '            "annee_scolaire", "difficulte", "auteur", "modifie_le",\n'
        '            "latex_exercice", "chapitre_nom", "domaine_code", "domaine_nom"]',
    ),
]

def apply():
    if not TARGET.exists():
        print(f"❌  {TARGET} introuvable")
        raise SystemExit(1)

    content = TARGET.read_text(encoding="utf-8")
    original = content
    ok = True

    for label, avant, apres in PATCHES:
        if avant in content:
            content = content.replace(avant, apres, 1)
            print(f"  ✅  {label}")
        elif apres in content:
            print(f"  ⏭   {label} (déjà à jour)")
        else:
            print(f"  ❌  {label} — bloc introuvable")
            ok = False

    if not ok:
        print("\n⚠️  Certains blocs n'ont pas été trouvés. Aucun fichier modifié.")
        return

    if content != original:
        TARGET.with_suffix(".py.bak").write_text(original, encoding="utf-8")
        TARGET.write_text(content, encoding="utf-8")
        print(f"\n✅  vlm_build.py mis à jour (sauvegarde : vlm_build.py.bak)")
    else:
        print("\nAucun changement nécessaire.")

if __name__ == "__main__":
    apply()
