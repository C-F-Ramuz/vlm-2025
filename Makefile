# ============================================================
#  VLM Math — Makefile
#  Commandes disponibles :
#    make build      → Parse + base + LaTeX + JSON
#    make eleve      → PDF version élève (sans solutions)
#    make corrige    → PDF version corrigée (avec solutions)
#    make all        → Les deux PDFs
#    make site       → Lance le serveur de dev du site
#    make clean      → Nettoie les fichiers temporaires LaTeX
# ============================================================

PYTHON     = python3
LATEX      = latexmk
LATEX_DIR  = latex
TMPL_DIR   = $(LATEX_DIR)/templates
OUT_DIR    = $(LATEX_DIR)/output
SCRIPT     = scripts/vlm_build.py

.PHONY: build eleve corrige all site clean test-eleve test-corrige

## ── 1. Build : parse + DB + JSON ──────────────────────────────
build:
	@echo "▶ Build de la base de données et génération LaTeX..."
	$(PYTHON) $(SCRIPT)

## ── 2. PDF élève (sans solutions) ─────────────────────────────
eleve: build
	@echo "▶ Compilation PDF élève..."
	@mkdir -p $(OUT_DIR)
	$(LATEX) -C -jobname=vlm-eleve -outdir=$(OUT_DIR) $(TMPL_DIR)/main.tex 2>/dev/null || true
	$(LATEX) -pdf \
	  -jobname=vlm-eleve \
	  -outdir=$(OUT_DIR) \
	  $(TMPL_DIR)/main.tex
	@echo "✅ PDF élève : $(OUT_DIR)/vlm-eleve.pdf"

## ── 3. PDF corrigé (avec solutions) ───────────────────────────
corrige: build
	@echo "▶ Compilation PDF corrigé..."
	@mkdir -p $(OUT_DIR)
	$(LATEX) -C -jobname=vlm-corrige -outdir=$(OUT_DIR) $(TMPL_DIR)/main.tex 2>/dev/null || true
	$(LATEX) -pdf \
	  -jobname=vlm-corrige \
	  -outdir=$(OUT_DIR) \
	  -usepretex="\def\AVECSOLUTIONS{1}" \
	  $(TMPL_DIR)/main.tex
	@echo "✅ PDF corrigé : $(OUT_DIR)/vlm-corrige.pdf"

## ── 4. Les deux PDFs ───────────────────────────────────────────
all: eleve corrige

## ── 5. Serveur de dev du site ──────────────────────────────────
site:
	@echo "▶ Lancement du serveur de développement..."
	cd site && $(PYTHON) -m http.server 8080

## ── 6. Nettoyage ───────────────────────────────────────────────
clean:
	@echo "▶ Nettoyage..."
	find $(LATEX_DIR) -name "*.aux" -o -name "*.log" \
	  -o -name "*.toc" -o -name "*.fls" \
	  -o -name "*.fdb_latexmk" | xargs rm -f
	@echo "✅ Nettoyage terminé"
	
## ── Test exercice individuel ───────────────────────────────────
test-eleve:
	@read -p "ID de l'exercice (ex: EX-CH01-001): " id; \
	$(PYTHON) $(SCRIPT); \
	mkdir -p latex/output/individual; \
	rm -f latex/output/individual/$$id*.pdf latex/output/individual/$$id*.aux \
	      latex/output/individual/$$id*.log latex/output/individual/$$id*.fls \
	      latex/output/individual/$$id*.fdb_latexmk; \
	pdflatex -output-directory=latex/output/individual \
	  "\input{latex/individual/$$id}"; \
	open latex/output/individual/$$id.pdf

test-corrige:
	@read -p "ID de l'exercice (ex: EX-CH01-001): " id; \
	$(PYTHON) $(SCRIPT); \
	mkdir -p latex/output/individual; \
	rm -f latex/output/individual/$$id*.pdf latex/output/individual/$$id*.aux \
	      latex/output/individual/$$id*.log latex/output/individual/$$id*.fls \
	      latex/output/individual/$$id*.fdb_latexmk; \
	pdflatex -output-directory=latex/output/individual \
	  "\def\AVECSOLUTIONS{1}\input{latex/individual/$$id}"; \
	open latex/output/individual/$$id.pdf
