#!/usr/bin/env bash
set -euo pipefail

# ------------------------------------------------------------------------------
# Script: loc_rank.sh
# Objectif:
#   Générer un classement des fichiers source du projet en fonction
#   du nombre de lignes de code (LOC), avec séparation :
#     - lignes de code
#     - lignes de commentaires
#     - lignes vides
#
# Dossier analysé:
#   - Par défaut: lib/
#   - Le dossier lib/l10n/ est ignoré automatiquement
#
# Utilisation:
#   ./tools/loc_rank.sh
#   ./tools/loc_rank.sh ./lib
#
# Variables d'environnement configurables:
#
#   SORT_BY
#     Détermine le critère de tri du classement.
#     Valeurs possibles:
#       - code   : nombre de lignes de code (défaut)
#       - total  : nombre total de lignes
#       - file   : ordre alphabétique des fichiers
#
#     Exemple:
#       SORT_BY=total ./tools/loc_rank.sh
#
#   MAX_FILES
#     Limite le nombre de fichiers affichés dans le classement.
#     Valeurs:
#       - 0 : aucun limite (défaut)
#       - N : affiche uniquement les N premiers fichiers
#
#     Exemple:
#       MAX_FILES=25 ./tools/loc_rank.sh
#
#   BAR_WIDTH
#     Largeur de la barre de proportion affichée à droite.
#     Valeur par défaut: 26
#
#     Exemple:
#       BAR_WIDTH=40 ./tools/loc_rank.sh
#
#   NO_COLOR
#     Désactive l'affichage en couleur (utile pour export ou CI).
#     Valeurs:
#       - 0 : couleurs activées (défaut)
#       - 1 : couleurs désactivées
#
#     Exemple:
#       NO_COLOR=1 ./tools/loc_rank.sh
#
#   SHOW_HEADER
#     Affiche ou masque l'en-tête du tableau.
#     Valeurs:
#       - 1 : afficher l'en-tête (défaut)
#       - 0 : masquer l'en-tête
#
# Extensions analysées:
#   dart
#
# ------------------------------------------------------------------------------

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# Default target: prefer the project's `lib/` folder if present
# (Git Bash / MSYS and native Windows paths supported)
if [[ -d "/c/Users/nrcoe/Documents/mytwip_mobile/lib" ]]; then
  DEFAULT_TARGET="/c/Users/nrcoe/Documents/mytwip_mobile/lib"
elif [[ -d "C:/Users/nrcoe/Documents/mytwip_mobile/lib" ]]; then
  DEFAULT_TARGET="C:/Users/nrcoe/Documents/mytwip_mobile/lib"
else
  DEFAULT_TARGET="$ROOT_DIR/lib"
fi

# Allow overriding with first arg; otherwise use DEFAULT_TARGET
TARGET_DIR="${1:-$DEFAULT_TARGET}"

SORT_BY="${SORT_BY:-code}"   # code | total | file
MAX_FILES="${MAX_FILES:-10}"  # default: top 10 files
SHOW_HEADER="${SHOW_HEADER:-1}"
NO_COLOR="${NO_COLOR:-0}"

if [[ ! -d "$TARGET_DIR" ]]; then
  echo "Erreur: dossier introuvable: $TARGET_DIR" >&2
  exit 1
fi

if [[ -t 1 && "$NO_COLOR" != "1" ]]; then
  BOLD=$'\033[1m'
  DIM=$'\033[2m'
  RESET=$'\033[0m'
  RED=$'\033[31m'
  GREEN=$'\033[32m'
  YELLOW=$'\033[33m'
  BLUE=$'\033[34m'
  MAGENTA=$'\033[35m'
  CYAN=$'\033[36m'
  GRAY=$'\033[90m'
else
  BOLD=""; DIM=""; RESET=""
  RED=""; GREEN=""; YELLOW=""; BLUE=""; MAGENTA=""; CYAN=""; GRAY=""
fi

BAR_WIDTH="${BAR_WIDTH:-26}"

print_help() {
  cat <<EOF
Usage: $(basename "$0") [path]
  path: dossier cible (par défaut: lib/ à la racine du projet)

Variables:
  SORT_BY=code|total|file   (défaut: code)
  MAX_FILES=0|N            (défaut: 0 = pas de limite)
  BAR_WIDTH=N              (défaut: 26)
  NO_COLOR=1               (désactive les couleurs)
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  print_help
  exit 0
fi

tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT

is_comment_line() {
  local line="$1"
  [[ "$line" =~ ^[[:space:]]*// ]] && return 0
  [[ "$line" =~ ^[[:space:]]*/\* ]] && return 0
  [[ "$line" =~ ^[[:space:]]*\* ]] && return 0
  return 1
}

count_file() {
  local file="$1"
  local total=0 blank=0 comment=0 code=0
  while IFS= read -r line || [[ -n "$line" ]]; do
    total=$((total + 1))
    if [[ "$line" =~ ^[[:space:]]*$ ]]; then
      blank=$((blank + 1))
    elif is_comment_line "$line"; then
      comment=$((comment + 1))
    else
      code=$((code + 1))
    fi
  done < "$file"
  printf "%s\t%d\t%d\t%d\t%d\n" "$file" "$total" "$code" "$comment" "$blank" >> "$tmp"
}

export -f is_comment_line
export -f count_file

while IFS= read -r -d '' f; do
  count_file "$f"
done < <(find "$TARGET_DIR" \
  -type d -name "l10n" -prune -o \
  -type f -name "*.dart" \
  -print0
)

if [[ ! -s "$tmp" ]]; then
  echo "Aucun fichier source trouvé dans: $TARGET_DIR" >&2
  exit 0
fi

max_metric=0
while IFS=$'\t' read -r file total code comment blank; do
  metric="$code"
  case "$SORT_BY" in
    code)  metric="$code" ;;
    total) metric="$total" ;;
    file)  metric="${#file}" ;;
    *)     metric="$code" ;;
  esac
  if (( metric > max_metric )); then
    max_metric="$metric"
  fi
done < "$tmp"

sort_cmd=(sort -t $'\t')
case "$SORT_BY" in
  total) sort_cmd+=(-k2,2nr -k1,1) ;;
  file)  sort_cmd+=(-k1,1) ;;
  *)     sort_cmd+=(-k3,3nr -k1,1) ;;
esac

rank=0
printed=0

make_bar() {
  local val="$1" max="$2"
  if (( max <= 0 )); then
    printf "%*s" "$BAR_WIDTH" ""
    return
  fi
  local filled=$(( (val * BAR_WIDTH) / max ))
  (( filled < 0 )) && filled=0
  (( filled > BAR_WIDTH )) && filled=$BAR_WIDTH
  local empty=$(( BAR_WIDTH - filled ))
  printf "%s%*s%s%*s" "${GREEN}" "$filled" "" "${GRAY}" "$empty" ""
}

path_rel() {
  local p="$1"
  if [[ "$p" == "$ROOT_DIR/"* ]]; then
    printf "%s" "${p#"$ROOT_DIR/"}"
  else
    printf "%s" "$p"
  fi
}

if [[ "$SHOW_HEADER" == "1" ]]; then
  echo "${BOLD}${CYAN}Classement LOC${RESET}  ${DIM}(dossier: $(path_rel "$TARGET_DIR"), tri: $SORT_BY)${RESET}"
  printf "${BOLD}%-4s %-60s %9s %9s %9s %9s  %s${RESET}\n" "#" "Fichier" "TOTAL" "CODE" "COMM" "VIDES" "PROPORTION"
  printf "%-4s %-60s %9s %9s %9s %9s  %s\n" "----" "------------------------------------------------------------" "---------" "---------" "---------" "---------" "--------------------------"
fi

while IFS=$'\t' read -r file total code comment blank; do
  rank=$((rank + 1))
  if (( MAX_FILES > 0 && printed >= MAX_FILES )); then
    break
  fi

  rel="$(path_rel "$file")"
  metric="$code"
  case "$SORT_BY" in
    total) metric="$total" ;;
    file)  metric="${#rel}" ;;
    *)     metric="$code" ;;
  esac

  bar="$(make_bar "$metric" "$max_metric")"

  file_disp="$rel"
  if (( ${#file_disp} > 60 )); then
    file_disp="…${file_disp: -59}"
  fi

  printf "%-4d ${BOLD}%-60s${RESET} %9d %9d %9d %9d  [%s${RESET}]\n" \
    "$rank" "$file_disp" "$total" "$code" "$comment" "$blank" "$bar"

  printed=$((printed + 1))
done < <("${sort_cmd[@]}" "$tmp")

sum_total=0
sum_code=0
sum_comment=0
sum_blank=0
count_files=0
while IFS=$'\t' read -r _ total code comment blank; do
  sum_total=$((sum_total + total))
  sum_code=$((sum_code + code))
  sum_comment=$((sum_comment + comment))
  sum_blank=$((sum_blank + blank))
  count_files=$((count_files + 1))
done < "$tmp"

echo
echo "${BOLD}${MAGENTA}Résumé${RESET}"
printf "%-18s %d\n" "Fichiers analysés:" "$count_files"
printf "%-18s %d\n" "Total lignes:" "$sum_total"
printf "%-18s %d\n" "Code:" "$sum_code"
printf "%-18s %d\n" "Commentaires:" "$sum_comment"
printf "%-18s %d\n" "Vides:" "$sum_blank"
