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

# Charger la configuration centralisée
CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'scc_config.json')
if not os.path.exists(CONFIG_PATH):
    raise FileNotFoundError('Fichier de configuration scc_config.json manquant.')
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    config = json.load(f)

REPORT_DIR = config.get('REPORT_DIR', 'scc_reports')
GRAPH_DIR = config.get('GRAPH_DIR', 'scc_graphs')
WEBHOOK_URL = config.get('DISCORD_WEBHOOK_URL', '')
# Nom et avatar du bot Discord (non modifiables par l'utilisateur)
WEBHOOK_USERNAME = "SCC Bot"
# Remplace cette URL par celle de ton image hébergée publiquement (ex: imgur, github raw, etc.)
WEBHOOK_AVATAR_URL = "https://png.pngtree.com/background/20240102/original/pngtree-graph-red-flat-icon-isolated-statistics-profile-symbol-photo-picture-image_7072156.jpg"
AUTO_GENERATE_GRAPHS = config.get('AUTO_GENERATE_GRAPHS', True)

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
max_code_date = df.loc[df['code'].idxmax(), 'date'].strftime('%Y-%m-%d')
max_complexity = df['complexity'].max()
max_complexity_date = df.loc[df['complexity'].idxmax(), 'date'].strftime('%Y-%m-%d')

# Calculer les changements
if 'code_change' not in df.columns:
    df['code_change'] = df['code'].diff().fillna(0).astype(int)
if 'complexity_change' not in df.columns:
    df['complexity_change'] = df['complexity'].diff().fillna(0).astype(int)

# Générer un graphique principal (évolution code/complexité)
plt.figure(figsize=(10,5))
plt.plot(df['date'], df['code'], label='Lignes de code', color='#3498db', marker='o')
plt.plot(df['date'], df['complexity'], label='Complexité', color='#e74c3c', marker='s')
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
• 🟪 +{df['complexity_change'].max():,} complexité le {df.loc[top_cplx, 'date'].strftime('%d/%m/%Y')}
"""

# Résumé visuel rapide
if code_change > 100:
    headline = '🔥 **Semaine record de développement !**'
elif code_change < 0:
    headline = '📉 **Semaine de refactoring ou nettoyage !**'
else:
    headline = '📊 **Semaine stable**'

# Lien vers le repo
repo_url = config.get('REPO_URL', '')
repo_link = f'\n🔗 [Voir le dépôt analysé]({repo_url})' if repo_url else ''

# Message Discord formaté amélioré (sans redondance de titre)
summary = f"""
{headline}{repo_link}\n\n**Période :** {week_ago.strftime('%d/%m/%Y')} → {now.strftime('%d/%m/%Y')}\n\n**Lignes de code :** {df_week['code'].iloc[-1] if len(df_week) else df['code'].iloc[-1]:,} {'🟩' if code_change > 0 else '🟥'} ({code_change:+,} {'⬆️' if code_change > 0 else '⬇️' if code_change < 0 else '➖'})\n**Fichiers Dart :** {df_week['files'].iloc[-1] if len(df_week) else df['files'].iloc[-1]:,} {'🟦' if files_change > 0 else '🟥'} ({files_change:+,} {'⬆️' if files_change > 0 else '⬇️' if files_change < 0 else '➖'})\n**Complexité :** {df_week['complexity'].iloc[-1] if len(df_week) else df['complexity'].iloc[-1]:,} {'🟪' if complexity_change > 0 else '🟧'} ({complexity_change:+,} {'⬆️' if complexity_change > 0 else '⬇️' if complexity_change < 0 else '➖'})\n**Coût estimé :** ${df_week['cost'].iloc[-1] if len(df_week) else df['cost'].iloc[-1]:,} {'💸' if cost_change > 0 else '💰'} ({cost_change:+,} {'⬆️' if cost_change > 0 else '⬇️' if cost_change < 0 else '➖'})\n\n━━━━━━━━━━━━━━━━━━━━\n\n🏆 **Records**\n• Lignes de code max : {max_code:,} ({max_code_date})\n• Complexité max : {max_complexity:,} ({max_complexity_date})\n\n━━━━━━━━━━━━━━━━━━━━\n\n📈 **Tendances**\n• Croissance hebdo : {code_change:+,} lignes\n• Fichiers créés/supprimés : {files_change:+,}\n• Complexité ajoutée/supprimée : {complexity_change:+,}\n\n━━━━━━━━━━━━━━━━━━━━\n{top_summary}\n_Envoyé automatiquement par SCC Bot_\n"""

embed = {
    "title": "✨ Rapport Hebdomadaire SCC ✨",
    "description": summary,
    "color": 0x3498db,
    "image": {"url": "attachment://weekly_changes.png"},
    "footer": {"text": f"Powered by SCC Bot • Généré le {now.strftime('%d/%m/%Y à %H:%M')}"}
}
payload = {"embeds": [embed], "username": WEBHOOK_USERNAME, "avatar_url": WEBHOOK_AVATAR_URL}
files = {
    'file': (os.path.basename(graph_path_changes), open(graph_path_changes, 'rb'), 'image/png')
}
data = {
    "payload_json": json.dumps(payload)
}

# Envoi sur Discord
resp = requests.post(WEBHOOK_URL, data=data, files=files)
if resp.status_code == 204 or resp.status_code == 200:
    print('✅ Rapport envoyé sur Discord !')
else:
    print(f'Erreur Discord: {resp.status_code} {resp.text}')
