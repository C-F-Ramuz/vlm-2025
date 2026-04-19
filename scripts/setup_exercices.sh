#!/bin/bash
# setup_exercices.sh — Crée la structure complète des dossiers exercices
#
# Usage (depuis la racine du projet vlm-2025) :
#   bash scripts/setup_exercices.sh

set -e
BASE="exercices"

echo "Création de l'arborescence des chapitres..."

# ── MSN31 : Nombres & Opérations ─────────────────────────────────
mkdir -p "$BASE/msn31-nombres/ch01-entiers-divisibilite"
mkdir -p "$BASE/msn31-nombres/ch02-entiers-relatifs"
mkdir -p "$BASE/msn31-nombres/ch03-fractions-pourcentages"
mkdir -p "$BASE/msn31-nombres/ch04-priorite-operations"
mkdir -p "$BASE/msn31-nombres/ch05-puissances-racines"
mkdir -p "$BASE/msn31-nombres/ch06-ecriture-scientifique"
mkdir -p "$BASE/msn31-nombres/ch07-problemes-4-operations"

# ── MSN32 : Géométrie ─────────────────────────────────────────────
mkdir -p "$BASE/msn32-geometrie/ch08-definitions-geometriques"
mkdir -p "$BASE/msn32-geometrie/ch09-constructions"
mkdir -p "$BASE/msn32-geometrie/ch10-isometries"
mkdir -p "$BASE/msn32-geometrie/ch11-calculs-angles"
mkdir -p "$BASE/msn32-geometrie/ch12-pythagore"
mkdir -p "$BASE/msn32-geometrie/ch13-semblables-thales"
mkdir -p "$BASE/msn32-geometrie/ch14-theoremes-metriques"
mkdir -p "$BASE/msn32-geometrie/ch15-trigonometrie"

# ── MSN33 : Algèbre & Fonctions ───────────────────────────────────
mkdir -p "$BASE/msn33-algebre/ch16-fonctions-proportionnalite"
mkdir -p "$BASE/msn33-algebre/ch17-droites"
mkdir -p "$BASE/msn33-algebre/ch18-calcul-litteral"
mkdir -p "$BASE/msn33-algebre/ch19-produits-remarquables"
mkdir -p "$BASE/msn33-algebre/ch20-factorisation"
mkdir -p "$BASE/msn33-algebre/ch21-equations-deg1"
mkdir -p "$BASE/msn33-algebre/ch22-systemes-equations"
mkdir -p "$BASE/msn33-algebre/ch23-equations-deg2"

# ── MSN34 : Grandeurs & Mesures ───────────────────────────────────
mkdir -p "$BASE/msn34-grandeurs/ch24-unites-conversions"
mkdir -p "$BASE/msn34-grandeurs/ch25-aires-perimetres"
mkdir -p "$BASE/msn34-grandeurs/ch26-volumes"
mkdir -p "$BASE/msn34-grandeurs/ch27-developpements"
mkdir -p "$BASE/msn34-grandeurs/ch28-vitesse-masse-volumique"

# ── MSN35 : Statistiques & Probabilités ──────────────────────────
mkdir -p "$BASE/msn35-stats/ch29-statistiques"
mkdir -p "$BASE/msn35-stats/ch30-probabilites"

echo ""
echo "✅ 30 dossiers créés dans exercices/"
echo ""
echo "Rappel de la convention de nommage des fichiers :"
echo "  ex-001.tex, ex-002.tex, ex-003.tex, ..."
echo ""
echo "Rappel des chapitre_id dans le YAML :"
echo "  MSN31 → ch01 à ch07"
echo "  MSN32 → ch08 à ch15"
echo "  MSN33 → ch16 à ch23"
echo "  MSN34 → ch24 à ch28"
echo "  MSN35 → ch29 à ch30"
