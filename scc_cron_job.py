# scc_cron_job.py
# Script à exécuter par le cron Windows : lance l'extraction puis l'envoi Discord
import subprocess
import sys
import os

PYTHON = sys.executable if hasattr(sys, 'executable') else 'python'
BASE_DIR = os.path.dirname(__file__)

# 1. Extraction des infos du dépôt
subprocess.run([PYTHON, os.path.join(BASE_DIR, 'extract_scc_history.py')], check=True)
# 2. Envoi de l'analyse Discord
subprocess.run([PYTHON, os.path.join(BASE_DIR, 'send_scc_discord_report.py')], check=True)
