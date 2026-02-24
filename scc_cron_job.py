# scc_cron_job.py
# Script to execute via Windows cron: runs extraction then Discord send
import subprocess
import sys
import os

PYTHON = sys.executable if hasattr(sys, 'executable') else 'python'
BASE_DIR = os.path.dirname(__file__)

# 1. Extract repository information
subprocess.run([PYTHON, os.path.join(BASE_DIR, 'extract_scc_history.py')], check=True)
# 2. Send Discord analysis
subprocess.run([PYTHON, os.path.join(BASE_DIR, 'send_scc_discord_report.py')], check=True)
