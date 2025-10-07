import os
import json
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import re

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'scc_config.json')
if not os.path.exists(CONFIG_PATH):
    raise FileNotFoundError('Fichier de configuration scc_config.json manquant.')
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    config = json.load(f)

REPORT_DIR = config.get('REPORT_DIR', 'scc_reports')
OUTPUT_GRAPH_DIR = config.get('GRAPH_DIR', 'scc_graphs')

if not os.path.exists(OUTPUT_GRAPH_DIR):
    os.makedirs(OUTPUT_GRAPH_DIR)

data = []
json_files = [f for f in os.listdir(REPORT_DIR) if f.endswith('.json')]

for file in sorted(json_files):
    commit_date_str = file.replace('scc_', '').replace('.json', '')
    if '_+' in commit_date_str or '_-' in commit_date_str:
        commit_date_str = commit_date_str.split('_+')[0]
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

        print(f"{commit_date} | Code: {code}, Compl: {complexity}, $: {cost}, Effort: {effort}, People: {people}")

    except Exception as e:
        print(f"Erreur sur {file} : {e}")

if not data:
    print("⚠ Aucun fichier exploitable.")
    exit(1)

df = pd.DataFrame(data).sort_values(by='date')

# Calcul des différences (changements par commit)
df['code_change'] = df['code'].diff()
df['files_change'] = df['files'].diff()
df['complexity_change'] = df['complexity'].diff()
df['bytes_change'] = df['bytes'].diff()

# Calcul des ratios et métriques de qualité
df['complexity_per_line'] = df['complexity'] / df['code'].replace(0, 1)  # Éviter division par zéro
df['bytes_per_file'] = df['bytes'] / df['files'].replace(0, 1)
df['lines_per_file'] = df['code'] / df['files'].replace(0, 1)

# Calcul de la vélocité (changements par unité de temps)
df['days_since_start'] = (df['date'] - df['date'].min()).dt.days
df['velocity'] = df['code'] / (df['days_since_start'] + 1)  # +1 pour éviter division par zéro

# Métriques cumulatives
df['total_cost_growth'] = (df['cost'] - df['cost'].iloc[0]) / df['cost'].iloc[0] * 100 if df['cost'].iloc[0] > 0 else 0

def make_plot(y, title, ylabel, filename, color='blue'):
    plt.figure(figsize=(10,5))
    plt.plot(df['date'], df[y], marker='o', color=color)
    plt.xticks(rotation=45, ha='right')
    plt.title(title)
    plt.xlabel('Date')
    plt.ylabel(ylabel)
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_GRAPH_DIR, filename))
    plt.close()

def make_bar_plot(y, title, ylabel, filename, color='blue'):
    """Graphique en barres pour les changements"""
    plt.figure(figsize=(12,6))
    bars = plt.bar(range(len(df)), df[y], color=color, alpha=0.7)
    
    # Colorier les barres négatives différemment
    for i, bar in enumerate(bars):
        if df[y].iloc[i] < 0:
            bar.set_color('red')
        elif df[y].iloc[i] > 0:
            bar.set_color('green')
        else:
            bar.set_color('gray')
    
    plt.xticks(range(len(df)), [d.strftime('%m-%d') for d in df['date']], rotation=45, ha='right')
    plt.title(title)
    plt.xlabel('Date')
    plt.ylabel(ylabel)
    plt.grid(True, alpha=0.3)
    plt.axhline(y=0, color='black', linestyle='-', alpha=0.5)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_GRAPH_DIR, filename))
    plt.close()

def make_correlation_plot(x, y, title, xlabel, ylabel, filename):
    """Graphique de corrélation entre deux variables"""
    plt.figure(figsize=(8,6))
    plt.scatter(df[x], df[y], alpha=0.6, c=range(len(df)), cmap='viridis')
    plt.colorbar(label='Ordre chronologique')
    
    # Ligne de tendance
    if len(df) > 1:
        z = np.polyfit(df[x], df[y], 1)
        p = np.poly1d(z)
        plt.plot(df[x], p(df[x]), "r--", alpha=0.8)
    
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_GRAPH_DIR, filename))
    plt.close()

# Graphes individuels existants
make_plot('code', 'Lignes de code', 'Lignes de code', 'lines_of_code.png')
make_plot('complexity', 'Complexité', 'Complexité', 'complexity.png', 'red')
make_plot('files', 'Nombre de fichiers Dart', 'Nombre de fichiers', 'files_count.png', 'purple')
make_plot('cost', 'Coût estimé ($)', 'Coût ($)', 'cost.png', 'green')
make_plot('effort', 'Effort estimé (mois)', 'Effort (mois)', 'effort.png', 'orange')
make_plot('people', 'Personnes estimées', 'Personnes', 'people.png', 'grey')
make_plot('bytes', 'Octets traités', 'Octets', 'bytes.png', 'brown')

# NOUVEAUX GRAPHIQUES DE COMPARAISON

# 1. Changements par commit (lignes ajoutées/supprimées)
make_bar_plot('code_change', 'Changement de lignes de code par commit', 'Lignes ajoutées/supprimées', 'code_changes.png')
make_bar_plot('files_change', 'Changement de fichiers par commit', 'Fichiers ajoutés/supprimés', 'files_changes.png')
make_bar_plot('complexity_change', 'Changement de complexité par commit', 'Complexité ajoutée/supprimée', 'complexity_changes.png')
make_bar_plot('bytes_change', 'Changement d\'octets par commit', 'Octets ajoutés/supprimés', 'bytes_changes.png')

# 2. Métriques de qualité et ratios
make_plot('complexity_per_line', 'Complexité par ligne de code', 'Complexité/Ligne', 'complexity_ratio.png', 'darkred')
make_plot('bytes_per_file', 'Taille moyenne des fichiers', 'Octets/Fichier', 'file_size_avg.png', 'darkorange')
make_plot('lines_per_file', 'Lignes moyennes par fichier', 'Lignes/Fichier', 'lines_per_file.png', 'darkblue')

# 3. Vélocité et tendances temporelles
make_plot('velocity', 'Vélocité de développement', 'Lignes/Jour', 'velocity.png', 'darkgreen')

# 4. Graphiques de corrélation
make_correlation_plot('code', 'complexity', 'Corrélation Code vs Complexité', 'Lignes de code', 'Complexité', 'correlation_code_complexity.png')
make_correlation_plot('files', 'complexity', 'Corrélation Fichiers vs Complexité', 'Nombre de fichiers', 'Complexité', 'correlation_files_complexity.png')
make_correlation_plot('code', 'cost', 'Corrélation Code vs Coût', 'Lignes de code', 'Coût ($)', 'correlation_code_cost.png')

# 5. Graphiques comparatifs avancés

# Évolution des changements cumulés
plt.figure(figsize=(12,8))
plt.subplot(2, 2, 1)
plt.plot(df['date'], df['code_change'].cumsum(), marker='o', color='blue', label='Code')
plt.plot(df['date'], df['files_change'].cumsum(), marker='s', color='purple', label='Fichiers')
plt.xticks(rotation=45, ha='right')
plt.title('Changements cumulés')
plt.xlabel('Date')
plt.ylabel('Changements cumulés')
plt.legend()
plt.grid(True, alpha=0.3)

# Distribution des tailles de changements
plt.subplot(2, 2, 2)
plt.hist(df['code_change'].dropna(), bins=20, alpha=0.7, color='blue', edgecolor='black')
plt.title('Distribution des changements de code')
plt.xlabel('Lignes ajoutées/supprimées')
plt.ylabel('Fréquence')
plt.grid(True, alpha=0.3)

# Évolution de l'efficacité (complexité/coût)
plt.subplot(2, 2, 3)
efficiency = df['complexity'] / df['cost'].replace(0, 1)
plt.plot(df['date'], efficiency, marker='o', color='red')
plt.xticks(rotation=45, ha='right')
plt.title('Efficacité (Complexité/Coût)')
plt.xlabel('Date')
plt.ylabel('Efficacité')
plt.grid(True, alpha=0.3)

# Tendance de croissance
plt.subplot(2, 2, 4)
growth_rate = df['code'].pct_change() * 100
plt.plot(df['date'], growth_rate, marker='o', color='green')
plt.axhline(y=0, color='black', linestyle='--', alpha=0.5)
plt.xticks(rotation=45, ha='right')
plt.title('Taux de croissance du code (%)')
plt.xlabel('Date')
plt.ylabel('Croissance (%)')
plt.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_GRAPH_DIR, 'advanced_comparisons.png'), dpi=300)
plt.close()

# 6. Analyse temporelle détaillée
plt.figure(figsize=(14,6))

# Activité par jour de la semaine
df['day_of_week'] = df['date'].dt.day_name()
day_activity = df.groupby('day_of_week')['code_change'].sum().abs()
day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
day_activity = day_activity.reindex([day for day in day_order if day in day_activity.index])

plt.subplot(1, 2, 1)
plt.bar(range(len(day_activity)), day_activity.values, color='skyblue')
plt.xticks(range(len(day_activity)), [day[:3] for day in day_activity.index], rotation=45)
plt.title('Activité par jour de la semaine')
plt.xlabel('Jour')
plt.ylabel('Changements absolus')
plt.grid(True, alpha=0.3)

# Tendance sur les 30 derniers jours
plt.subplot(1, 2, 2)
if len(df) >= 30:
    recent_df = df.tail(30)
    plt.plot(recent_df['date'], recent_df['code'], marker='o', color='blue', label='Code')
    plt.plot(recent_df['date'], recent_df['complexity'], marker='s', color='red', label='Complexité')
    plt.xticks(rotation=45, ha='right')
    plt.title('Tendance des 30 derniers commits')
    plt.xlabel('Date')
    plt.ylabel('Valeur')
    plt.legend()
    plt.grid(True, alpha=0.3)
else:
    plt.text(0.5, 0.5, 'Pas assez de données\n(< 30 commits)', 
             ha='center', va='center', transform=plt.gca().transAxes, fontsize=12)
    plt.title('Tendance des 30 derniers commits')

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_GRAPH_DIR, 'temporal_analysis.png'), dpi=300)
plt.close()

# 7. Résumé statistique des changements
print("\n📊 STATISTIQUES DE CHANGEMENTS:")
print(f"├─ Plus gros ajout de code: {df['code_change'].max():.0f} lignes")
print(f"├─ Plus grosse suppression: {df['code_change'].min():.0f} lignes")
print(f"├─ Changement moyen par commit: {df['code_change'].mean():.1f} lignes")
print(f"├─ Médiane des changements: {df['code_change'].median():.1f} lignes")
print(f"├─ Écart-type: {df['code_change'].std():.1f} lignes")
print(f"└─ Commits avec ajouts: {(df['code_change'] > 0).sum()}/{len(df)} ({(df['code_change'] > 0).mean()*100:.1f}%)")

# 8. Heatmap des corrélations
correlation_data = df[['code', 'complexity', 'files', 'cost', 'effort', 'people', 'bytes']].corr()

plt.figure(figsize=(10,8))
im = plt.imshow(correlation_data, cmap='RdBu_r', aspect='auto', vmin=-1, vmax=1)
plt.colorbar(im, label='Corrélation')

# Ajouter les valeurs dans les cellules
for i in range(len(correlation_data.columns)):
    for j in range(len(correlation_data.columns)):
        plt.text(j, i, f'{correlation_data.iloc[i, j]:.2f}', 
                ha='center', va='center', fontweight='bold')

plt.xticks(range(len(correlation_data.columns)), correlation_data.columns, rotation=45, ha='right')
plt.yticks(range(len(correlation_data.columns)), correlation_data.columns)
plt.title('Matrice de corrélation des métriques')
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_GRAPH_DIR, 'correlation_matrix.png'), dpi=300)
plt.close()

# Graphe combiné normalisé
plt.figure(figsize=(12,6))
for col, color in [
    ('code', 'blue'),
    ('complexity', 'red'),
    ('cost', 'green'),
    ('effort', 'orange'),
    ('people', 'grey'),
    ('files', 'purple'),
    ('bytes', 'brown')
]:
    if df[col].max() > df[col].min():
        norm = (df[col] - df[col].min()) / (df[col].max() - df[col].min())
        plt.plot(df['date'], norm, marker='o', label=col.capitalize(), color=color)

plt.xticks(rotation=45, ha='right')
plt.title('Évolution normalisée des indicateurs')
plt.xlabel('Date')
plt.ylabel('Valeur normalisée (0-1)')
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_GRAPH_DIR, 'combined_normalized.png'))
plt.close()

print(f"\n✅ Graphiques générés dans {OUTPUT_GRAPH_DIR}")
print(f"📈 Nouveaux graphiques ajoutés:")
print("   ├─ Changements par commit (code_changes.png, files_changes.png, etc.)")
print("   ├─ Métriques de qualité (complexity_ratio.png, file_size_avg.png, etc.)")
print("   ├─ Vélocité de développement (velocity.png)")
print("   ├─ Corrélations (correlation_*.png)")
print("   ├─ Comparaisons avancées (advanced_comparisons.png)")
print("   ├─ Analyse temporelle (temporal_analysis.png)")
print("   └─ Matrice de corrélation (correlation_matrix.png)")
