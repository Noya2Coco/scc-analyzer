# extract_scc_history.py
# Script Python pour cloner un dépôt, parcourir les commits, et générer les rapports scc (json + txt)
import os
import shutil
import subprocess
import tempfile
import json

def ask_param(prompt, default=None):
    val = input(f"{prompt} [{default if default is not None else ''}]: ").strip()
    return val if val else default

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'scc_config.json')
def load_config():
    # Valeurs attendues et prompts
    required = [
        ("REPO_URL", "Entrez l'URL du dépôt Git à analyser"),
        ("BRANCH", "Entrez le nom de la branche à analyser"),
        ("REPORT_DIR", "Répertoire de sortie des rapports"),
        ("GRAPH_DIR", "Répertoire de sortie des graphs"),
        ("DISCORD_WEBHOOK_URL", "URL du webhook Discord (laisser vide si non utilisé)"),
        ("AUTO_GENERATE_GRAPHS", "Générer automatiquement les graphs ? (true/false)")
    ]
    config = {}
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
    changed = False
    for key, prompt in required:
        if key not in config or config[key] in (None, ""):
            default = "true" if key == "AUTO_GENERATE_GRAPHS" else ""
            val = ask_param(prompt, default)
            if key == "AUTO_GENERATE_GRAPHS":
                val = val.lower() in ("true", "1", "yes", "oui", "y")
            config[key] = val
            changed = True
    if changed:
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
    return config
def save_config(repo_url, branch, output_dir):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump({'REPO_URL': repo_url, 'BRANCH': branch, 'REPORT_DIR': output_dir}, f, indent=2)

config = load_config()
REPO_URL = config['REPO_URL']
BRANCH = config['BRANCH']
OUTPUT_DIR = os.path.abspath(config.get('REPORT_DIR', 'scc_reports'))

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# Utilisation d'un dossier temporaire pour le clone
temp_dir = tempfile.mkdtemp(prefix='scc_temp_')
print(f"Clonage du dépôt dans {temp_dir} ...")

try:
    subprocess.run([
        'git', 'clone', '--no-checkout', '--branch', BRANCH, REPO_URL, temp_dir
    ], check=True)

    os.chdir(temp_dir)
    # Liste des commits (du plus récent au plus ancien)
    result = subprocess.run(['git', 'rev-list', BRANCH], capture_output=True, text=True, check=True)
    commits = result.stdout.strip().split('\n')

    for commit in commits:
        # Récupérer la date du commit
        date_result = subprocess.run([
            'git', 'show', '-s', '--format=%ci', commit
        ], capture_output=True, text=True, check=True)
        commit_date = date_result.stdout.strip()
        # Nettoyage du formatage pour le nom de fichier
        commit_date_fmt = commit_date.replace(' ', '_').replace(':', '-').replace('/', '-').replace('.', '-')
        report_file = os.path.join(OUTPUT_DIR, f'scc_{commit_date_fmt}.json')
        summary_file = os.path.join(OUTPUT_DIR, f'scc_{commit_date_fmt}_summary.txt')

        if os.path.exists(report_file):
            print(f"Commit {commit} du {commit_date_fmt} déjà analysé. On passe.")
            continue
        print(f"Analyse de {commit} du {commit_date_fmt} ...")
        subprocess.run(['git', 'checkout', '--quiet', commit], check=True)
        # Lancer scc
        with open(report_file, 'w', encoding='utf-8') as f_json:
            subprocess.run(['scc', '--format', 'json', 'lib/'], stdout=f_json, check=True)
        with open(summary_file, 'w', encoding='utf-8') as f_txt:
            subprocess.run(['scc', 'lib/'], stdout=f_txt, check=True)
finally:
    os.chdir(os.path.dirname(__file__))
    print(f"Suppression du dossier temporaire {temp_dir} ...")
    shutil.rmtree(temp_dir, ignore_errors=True)

print(f"Analyse terminée. Les rapports sont dans : {OUTPUT_DIR}")
