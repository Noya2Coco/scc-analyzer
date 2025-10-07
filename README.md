# SCC History & Discord Reporter

Ce projet automatise l'extraction de l'historique d'un dépôt Git, l'analyse de code avec [scc](https://github.com/boyter/scc), la génération de graphiques d'évolution, et l'envoi de rapports hebdomadaires sur Discord.

## Fonctionnalités
- Extraction de l'historique de code (lignes, complexité, coût, etc.) commit par commit
- Génération de rapports SCC (JSON + TXT)
- Génération de graphiques d'évolution et de qualité
- Envoi automatique d'un rapport synthétique sur Discord avec graphique
- Configuration centralisée (scc_config.json)

## Prérequis
- Python 3.8+
- [scc](https://github.com/boyter/scc) (installé et accessible dans le PATH)
- Git (installé)
- [pandas](https://pandas.pydata.org/), [matplotlib](https://matplotlib.org/), [numpy](https://numpy.org/), [requests](https://requests.readthedocs.io/)

## Installation
1. Clonez ce dépôt
2. Installez les dépendances Python :
   ```bash
   pip install -r requirements.txt
   ```
3. Installez scc (voir https://github.com/boyter/scc)

## Configuration
- Lancez un des scripts, il vous demandera les paramètres manquants et créera `scc_config.json`.
- Modifiez ce fichier pour adapter les chemins, le webhook Discord, etc.

## Utilisation
- **Extraction de l'historique** :
  ```bash
  python extract_scc_history.py
  ```
- **Génération des graphiques** :
  ```bash
  python plot_scc_history.py
  ```
- **Envoi du rapport Discord** :
  ```bash
  python send_scc_discord_report.py
  ```
- **Automatisation (cron Windows)** :
  ```bash
  python scc_cron_job.py
  ```

## Structure des dossiers
- `scc_reports/` : rapports SCC générés (JSON, TXT)
- `scc_graphs/` : graphiques générés (PNG)

## Personnalisation
- Modifiez les scripts pour changer la branche, le dépôt, le format des graphs, etc.
- Le message Discord et le graphique sont personnalisables dans `send_scc_discord_report.py`.

## Exemples de rendu
- Voir le dossier `scc_graphs/` pour les graphiques générés
- Exemple de rapport Discord dans la documentation ou le README

## Licence
MIT

---

*Projet automatisé pour le suivi d'évolution de code et la communication d'équipe !*
