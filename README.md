# VLM Mathématiques — Guide du projet

## Structure du projet

```
vlm-math/
│
├── exercices/                  ← SOURCE DE VÉRITÉ
│   ├── ch01-algebre/
│   │   ├── ex-001.tex
│   │   └── ex-002.tex
│   ├── ch02-geometrie/
│   └── ch03-trigonometrie/
│
├── scripts/
│   └── vlm_build.py            ← Script principal (parse + DB + JSON + LaTeX)
│
├── latex/
│   ├── templates/
│   │   └── main.tex            ← Template principal (élève + corrigé)
│   ├── generated/              ← Chapitres auto-générés (ne pas éditer !)
│   └── output/                 ← PDFs compilés
│
├── site/
│   ├── index.html              ← Interface de recherche web
│   ├── exercices.json          ← Données pour le site (auto-généré)
│   └── pdfs/                   ← PDFs déployés
│
├── vlm.db                      ← Base SQLite (auto-générée)
├── Makefile                    ← Commandes de build
└── .github/workflows/build.yml ← CI/CD automatique
```

---

## Format d'un fichier exercice

Chaque exercice est un fichier `.tex` autonome avec un en-tête YAML :

```latex
% ---
% id: EX-CH01-001          ← Identifiant unique (obligatoire)
% titre: Mon exercice       ← Titre court
% chapitre: 1               ← Numéro de chapitre
% chapitre_nom: Algèbre     ← Nom du chapitre
% section: Équations        ← Section dans le chapitre
% tags: [équation, algèbre] ← Mots-clés pour la recherche
% niveau: secondaire2       ← Niveau scolaire
% difficulte: 2             ← 1=facile, 2=moyen, 3=difficile
% auteur: Dupont M.         ← Auteur
% annee: 2025               ← Année
% objectifs:                ← Objectifs pédagogiques
%   - Savoir faire X
%   - Comprendre Y
% ---

\begin{exercice}{EX-CH01-001}{Titre de l'exercice}
  ...énoncé en LaTeX...
\end{exercice}

\begin{solution}{EX-CH01-001}
  ...solution en LaTeX...
\end{solution}
```

---

## Commandes quotidiennes

```bash
# Ajouter un exercice
cp exercices/ch01-algebre/ex-001.tex exercices/ch01-algebre/ex-042.tex
# → Éditer le fichier, changer l'ID, le titre, les tags...

# Builder (parse + DB + chapitres + JSON)
make build

# Générer les PDFs
make all          # les deux versions
make eleve        # version élève seulement
make corrige      # version corrigée seulement

# Lancer le site en local
make site         # → http://localhost:8080

# Nettoyer les fichiers LaTeX temporaires
make clean
```

---

## Workflow collaboratif (Git)

```bash
# 1. Récupérer les dernières modifications
git pull

# 2. Créer une branche pour vos exercices
git checkout -b ajout/ch02-exercices-vecteurs

# 3. Ajouter vos fichiers .tex
# ... créer exercices/ch02-geometrie/ex-012.tex ...

# 4. Vérifier localement
make build

# 5. Pousser et créer une Pull Request
git add exercices/ch02-geometrie/ex-012.tex
git commit -m "Ajout exercice EX-CH02-012 : vecteurs colinéaires"
git push

# → GitHub Actions compile automatiquement les PDFs
# → La PR peut être relue par un collègue avant merge
```

---

## Recherche dans la base SQLite

```bash
# Ouvrir la base en ligne de commande
sqlite3 vlm.db

# Tous les exercices d'un chapitre
SELECT id, titre FROM exercices WHERE chapitre = 1;

# Exercices par tag
SELECT e.id, e.titre FROM exercices e
JOIN tags t ON t.exercice_id = e.id
WHERE t.tag = 'discriminant';

# Exercices faciles de trigonométrie
SELECT id, titre, difficulte FROM exercices
WHERE chapitre_nom = 'Trigonométrie' AND difficulte = 1
ORDER BY id;
```

---

## Dépendances à installer

```bash
# Python
pip install pyyaml

# LaTeX (Ubuntu/Debian)
sudo apt install texlive-full latexmk

# LaTeX (macOS)
brew install --cask mactex
```
