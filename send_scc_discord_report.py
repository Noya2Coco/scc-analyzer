# send_scc_discord_report.py
# Envoie un rapport SCC hebdomadaire "sublime" sur Discord
import os
import json
import pandas as pd
import matplotlib.pyplot as plt
import requests
import numpy as np
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

REPORT_DIR = os.getenv('REPORT_DIR', 'scc_reports')
GRAPH_DIR = os.getenv('GRAPH_DIR', 'scc_graphs')
WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL', '')
# Nom et avatar du bot Discord (non modifiables par l'utilisateur)
WEBHOOK_USERNAME = "SCC Bot"
WEBHOOK_AVATAR_URL = os.getenv('WEBHOOK_AVATAR_URL', 'https://icons-for-free.com/iff/png/512/graph+graphic+graphics+icon-1320168051322057462.png')
AUTO_GENERATE_GRAPHS = os.getenv('AUTO_GENERATE_GRAPHS', 'true').lower() in ('true', '1', 'yes')

# Génération automatique des graphs si demandé
if AUTO_GENERATE_GRAPHS:
    import plot_scc_history

# Charger les données SCC
json_files = [f for f in os.listdir(REPORT_DIR) if f.endswith('.json')]
data = []
for file in sorted(json_files):
    commit_date_str = file.replace('scc_', '').replace('.json', '')
    # Correction : retirer le suffixe fuseau horaire (_+xxxx ou _-xxxx)
    if '_+' in commit_date_str:
        commit_date_str = commit_date_str.split('_+')[0]
    if '_-' in commit_date_str:
        commit_date_str = commit_date_str.split('_-')[0]
    try:
        commit_date = pd.to_datetime(commit_date_str, format='%Y-%m-%d_%H-%M-%S')
    except:
        continue
    path_json = os.path.join(REPORT_DIR, file)
    path_summary = path_json.replace('.json', '_summary.txt')
    try:
        with open(path_json, 'r', encoding='utf-8') as f:
            report = json.load(f)
            lang = next((l for l in report if l.get('Name') == 'Dart'), None)
            files = lang.get('Count', 0) if lang else 0
            code = lang.get('Code', 0) if lang else 0
            complexity = lang.get('Complexity', 0) if lang else 0
        cost = effort = people = bytes_processed = 0
        if os.path.exists(path_summary):
            with open(path_summary, 'r', encoding='utf-8') as f:
                text = f.read()
                cost_match = re.search(r'Estimated Cost to Develop \(organic\) \$([0-9,]+)', text)
                effort_match = re.search(r'Estimated Schedule Effort \(organic\) ([0-9.]+)', text)
                people_match = re.search(r'Estimated People Required \(organic\) ([0-9.]+)', text)
                bytes_match = re.search(r'Processed ([0-9,]+) bytes', text)
                if cost_match:
                    cost = int(cost_match.group(1).replace(',', ''))
                if effort_match:
                    effort = float(effort_match.group(1))
                if people_match:
                    people = float(people_match.group(1))
                if bytes_match:
                    bytes_processed = int(bytes_match.group(1).replace(',', ''))
        data.append({
            'date': commit_date,
            'files': files,
            'code': code,
            'complexity': complexity,
            'cost': cost,
            'effort': effort,
            'people': people,
            'bytes': bytes_processed
        })
    except Exception as e:
        continue
if not data:
    print('Aucune donnée exploitable.')
    exit(1)
df = pd.DataFrame(data).sort_values(by='date')

# Filtrer la dernière semaine
now = datetime.now()
week_ago = now - timedelta(days=7)
df_week = df[df['date'] >= week_ago]

# Statistiques clés
code_change = int(df_week['code'].iloc[-1] - df_week['code'].iloc[0]) if len(df_week) > 1 else 0
files_change = int(df_week['files'].iloc[-1] - df_week['files'].iloc[0]) if len(df_week) > 1 else 0
complexity_change = int(df_week['complexity'].iloc[-1] - df_week['complexity'].iloc[0]) if len(df_week) > 1 else 0
cost_change = int(df_week['cost'].iloc[-1] - df_week['cost'].iloc[0]) if len(df_week) > 1 else 0

max_code = df['code'].max()
max_code_date = df.loc[df['code'].idxmax(), 'date'].strftime('%d/%m/%Y')
max_complexity = df['complexity'].max()
max_complexity_date = df.loc[df['complexity'].idxmax(), 'date'].strftime('%d/%m/%Y')

# Calculer les changements
if 'code_change' not in df.columns:
    df['code_change'] = df['code'].diff().fillna(0).astype(int)
if 'complexity_change' not in df.columns:
    df['complexity_change'] = df['complexity'].diff().fillna(0).astype(int)

# Calcul des tendances sur 3 mois (moyenne hebdomadaire sur 90 jours)
three_months_ago = now - timedelta(days=90)
df_3m = df[df['date'] >= three_months_ago]
if len(df_3m) >= 2:
    span_days = (df_3m['date'].max() - df_3m['date'].min()).days
    weeks = max(1, span_days / 7.0)
    avg_weekly_code = int(round((df_3m['code'].iloc[-1] - df_3m['code'].iloc[0]) / weeks))
    avg_weekly_files = int(round((df_3m['files'].iloc[-1] - df_3m['files'].iloc[0]) / weeks))
    avg_weekly_complexity = int(round((df_3m['complexity'].iloc[-1] - df_3m['complexity'].iloc[0]) / weeks))
    avg_weekly_cost = int(round((df_3m['cost'].iloc[-1] - df_3m['cost'].iloc[0]) / weeks))
else:
    avg_weekly_code = avg_weekly_files = avg_weekly_complexity = avg_weekly_cost = 0

# Générer un graphique principal (évolution code/complexité)
plt.figure(figsize=(10,5))
# Tracer uniquement des courbes (sans points)
plt.plot(df['date'], df['code'], label='Lignes de code', color='#3498db')
plt.plot(df['date'], df['complexity'], label='Complexité', color='#e74c3c')
plt.title('Évolution du code et de la complexité')
plt.xlabel('Date')
plt.ylabel('Valeur')
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
graph_path = os.path.join(GRAPH_DIR, 'weekly_main.png')
plt.savefig(graph_path)
plt.close()

# Générer un graphique des variations par commit (code_change et complexity_change)
plt.figure(figsize=(12,6))
bar_width = 0.4
x = np.arange(len(df))
# Couleurs dynamiques selon le signe
code_colors = ['#2ecc40' if v > 0 else '#3498db' for v in df['code_change']]
cplx_colors = ['#e74c3c' if v > 0 else '#f1c40f' for v in df['complexity_change']]
# Barres côte à côte
bars_code = plt.bar(x - bar_width/2, df['code_change'], width=bar_width, color=code_colors, alpha=0.8, label='Δ Lignes de code (⬆️ vert, ⬇️ bleu)')
bars_cplx = plt.bar(x + bar_width/2, df['complexity_change'], width=bar_width, color=cplx_colors, alpha=0.8, label='Δ Complexité (⬆️ rouge, ⬇️ orange)')
# Dates espacées (1 sur 7)
step = max(1, len(df)//14)
plt.xticks(x[::step], [d.strftime('%m-%d') for d in df['date']][::step], rotation=45, ha='right', fontsize=9)
plt.title('Changements par commit (lignes de code & complexité)')
plt.xlabel('Date')
plt.ylabel('Variation')
# Légende explicite
from matplotlib.patches import Patch
legend_elements = [
    Patch(facecolor='#2ecc40', label='Lignes de code ↑ (vert)'),
    Patch(facecolor='#3498db', label='Lignes de code ↓ (bleu)'),
    Patch(facecolor='#e74c3c', label='Complexité ↑ (rouge)'),
    Patch(facecolor='#f1c40f', label='Complexité ↓ (orange)')
]
plt.legend(handles=legend_elements)
plt.grid(True, alpha=0.3)
plt.tight_layout()
graph_path_changes = os.path.join(GRAPH_DIR, 'weekly_changes.png')
plt.savefig(graph_path_changes)
plt.close()

# Top 3 commits (ajout, suppression, pic complexité)
top_add = df['code_change'].idxmax()
top_del = df['code_change'].idxmin()
top_cplx = df['complexity_change'].idxmax()
top_summary = f"""
**Top commits :**
• ➕ {df['code_change'].max():,} lignes le {df.loc[top_add, 'date'].strftime('%d/%m/%Y')}
• ➖ {df['code_change'].min():,} lignes le {df.loc[top_del, 'date'].strftime('%d/%m/%Y')}
• 🟥 +{df['complexity_change'].max():,} complexité le {df.loc[top_cplx, 'date'].strftime('%d/%m/%Y')}
"""

# Résumé visuel rapide
if code_change > 100:
    headline = '🔥 **Semaine record de développement !**'
elif code_change < 0:
    headline = '📉 **Semaine de refactoring ou nettoyage !**'
else:
    headline = '📊 **Semaine stable**'

# Lien vers le repo
repo_url = os.getenv('REPO_URL', '')
repo_link = f'\n🔗 [Voir le dépôt analysé]({repo_url})' if repo_url else ''

# Message Discord formaté — description (embed title set separately)
summary = f"""
{headline}{repo_link}

**Période :** {week_ago.strftime('%d/%m/%Y')} → {now.strftime('%d/%m/%Y')}

**Lignes de code :** {df_week['code'].iloc[-1] if len(df_week) else df['code'].iloc[-1]:,} {'🟩' if code_change > 0 else '🟥'} ({code_change:+,} {'⬆️' if code_change > 0 else '⬇️' if code_change < 0 else '➖'})
**Fichiers Dart :** {df_week['files'].iloc[-1] if len(df_week) else df['files'].iloc[-1]:,} {'🟦' if files_change > 0 else '🟥'} ({files_change:+,} {'⬆️' if files_change > 0 else '⬇️' if files_change < 0 else '➖'})
**Complexité :** {df_week['complexity'].iloc[-1] if len(df_week) else df['complexity'].iloc[-1]:,} {'🟥' if complexity_change > 0 else '🟧'} ({complexity_change:+,} {'⬆️' if complexity_change > 0 else '⬇️' if complexity_change < 0 else '➖'})
**Coût estimé :** ${df_week['cost'].iloc[-1] if len(df_week) else df['cost'].iloc[-1]:,} {'💸' if cost_change > 0 else '💰'} ({cost_change:+,} {'⬆️' if cost_change > 0 else '⬇️' if cost_change < 0 else '➖'})

━━━━━━━━━━━━━━━━━━━━

🏆 **Records**
• Lignes de code max : {max_code:,} ({max_code_date})
• Complexité max : {max_complexity:,} ({max_complexity_date})

━━━━━━━━━━━━━━━━━━━━

📈 **Tendances (moyenne hebdo sur 3 mois)**
• Croissance hebdo : {avg_weekly_code:+,} lignes
• Fichiers : {avg_weekly_files:+,}
• Complexité : {avg_weekly_complexity:+,}

━━━━━━━━━━━━━━━━━━━━
{top_summary}
_Envoyé automatiquement par SCC Bot_
"""

ratio_path = os.path.join(GRAPH_DIR, 'ratio_curves.png')

# Calculer le top-N des fichiers par LOC dans le projet Flutter (si présent)
def compute_top_loc(top=10):
    """Compute top-N files by code lines.
    Restrict scan to the `lib/` directory when present and only count `.dart` files.
    Ignore common generated/build directories to avoid noisy results (build, .dart_tool, test, etc.).
    """
    exts = ('.dart',)
    candidates = [r"C:\\Users\\nrcoe\\Documents\\mytwip_mobile", "/c/Users/nrcoe/Documents/mytwip_mobile", os.path.join(os.path.dirname(__file__), '..')]
    target = None
    for c in candidates:
        if os.path.exists(c):
            target = c
            break
    if not target:
        return [], None

    # If there's a lib/ subdirectory, prefer it (we only want source files in lib/)
    lib_dir = os.path.join(target, 'lib')
    if os.path.isdir(lib_dir):
        target = lib_dir

    entries = []
    skip_dirs = {'l10n', 'build', '.dart_tool', '.gradle', 'ios', 'android', 'test', '.git'}
    for root, dirs, files in os.walk(target):
        # mutate dirs in-place so os.walk won't descend into these
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for fn in files:
            if fn.endswith(exts):
                path = os.path.join(root, fn)
                try:
                    total = code = comment = blank = 0
                    with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
                        for line in fh:
                            total += 1
                            s = line.strip()
                            if s == '':
                                blank += 1
                            elif s.startswith('//') or s.startswith('/*') or s.startswith('*'):
                                comment += 1
                            else:
                                code += 1
                    entries.append((path, total, code, comment, blank))
                except Exception:
                    continue
    entries.sort(key=lambda x: x[2], reverse=True)
    return entries[:top], target

top_list, project_root = compute_top_loc(top=10)
if top_list:
    lines = ['**Top 10 fichiers (par Lignes de code) :**']
    for i, (p, total, code, comment, blank) in enumerate(top_list, start=1):
        try:
            rel = os.path.relpath(p, start=project_root)
        except Exception:
            rel = p
        lines.append(f"{i}. `{rel}` — {code:,} lignes (total {total:,}, comm {comment:,}, vides {blank:,})")
    top_block = "\n".join(lines)
    # stocker le bloc pour l'ajouter plus tard (embed_ratio n'est pas encore défini)
    # limiter la taille pour rester sous la limite d'embed Discord (~4096 chars)
    if len(top_block) > 3700:
        top_block = top_block[:3690] + '\n...'

# Préparer deux embeds : 1) résumé + weekly_changes.png  2) courbes normalisées (ratio_curves.png)
embed_main = {
    "title": "✨ Rapport Hebdomadaire SCC ✨",
    "description": summary,
    "color": 0x3498db,
    "author": {"name": WEBHOOK_USERNAME, "icon_url": WEBHOOK_AVATAR_URL},
    "image": {"url": "attachment://weekly_changes.png"},
    "footer": {"text": f"Powered by SCC Bot • Généré le {now.strftime('%d/%m/%Y à %H:%M') }"}
}
embed_ratio = {
    "title": "📊 Courbes de ratios (normalisées)",
    "description": "Comparaison normalisée des ratios utiles (lignes/fichier, lignes/complexité, ...)",
    "color": 0x2ecc71,
    "image": {"url": "attachment://ratio_curves.png"}
}

# Si on a calculé un top_block plus haut, l'ajouter maintenant à la description
try:
    if top_list:
        desc = embed_ratio.get('description', '') + '\n\n' + top_block
        if len(desc) > 3800:
            desc = desc[:3790] + '\n...'
        embed_ratio['description'] = desc
except NameError:
    # top_list/top_block non définis : rien à faire
    pass

payload = {"embeds": [embed_main, embed_ratio], "username": WEBHOOK_USERNAME, "avatar_url": WEBHOOK_AVATAR_URL}

# Construire la liste de fichiers à envoyer. Discord accepte plusieurs fichiers sous la même clé 'file'.
files_to_send = []
if os.path.exists(graph_path_changes):
    files_to_send.append((os.path.basename(graph_path_changes), graph_path_changes))
else:
    print(f'⚠️ Graphique manquant: {graph_path_changes}')
if os.path.exists(ratio_path):
    files_to_send.append((os.path.basename(ratio_path), ratio_path))
else:
    print(f'⚠️ Graphique manquant: {ratio_path}')

data = {
    "payload_json": json.dumps(payload)
}

# Ouvrir les fichiers dans un context manager pour s'assurer de leur fermeture
opened = []
try:
    for fname, fpath in files_to_send:
        f = open(fpath, 'rb')
        opened.append(f)
    # Construire un mapping explicite file0/file1/... pour éviter que
    # certains endpoints n'acceptent qu'une seule clé 'file'.
    files = []
    for i, (fname, _) in enumerate(files_to_send):
        field_name = f'file{i}'
        # trouver le fileobj correspondant (opened list matches files_to_send order)
        fileobj = opened[i]
        # essayer de deviner le mime type, tomber sur image/png par défaut
        mime = 'image/png'
        files.append((field_name, (fname, fileobj, mime)))

    # Debug: lister les fichiers attachés et les champs multipart
    print('📎 Fichiers attachés :', [fname for fname, _ in files_to_send])
    print('📎 Champs multipart envoyés :', [f[0] for f in files])

    # Envoi sur Discord — payload_json + fichiers nommés file0,file1,...
    resp = requests.post(WEBHOOK_URL, data=data, files=files)
    print('Discord response:', resp.status_code, resp.text)
    if resp.status_code in (200, 204):
        print('✅ Rapport envoyé sur Discord ! (avec pièces jointes si présentes)')
    else:
        print(f'Erreur Discord: {resp.status_code} {resp.text}')
finally:
    for f in opened:
        try:
            f.close()
        except Exception:
            pass
