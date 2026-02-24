import os
import json
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import re
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

REPORT_DIR = os.getenv('REPORT_DIR', 'scc_reports')
OUTPUT_GRAPH_DIR = os.getenv('GRAPH_DIR', 'scc_graphs')

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
        print(f"Error on {file}: {e}")

if not data:
    print("⚠ No usable files.")
    exit(1)

df = pd.DataFrame(data).sort_values(by='date')

# Calculate differences (changes per commit)
df['code_change'] = df['code'].diff()
df['files_change'] = df['files'].diff()
df['complexity_change'] = df['complexity'].diff()
df['bytes_change'] = df['bytes'].diff()

# Calculate ratios and quality metrics
df['complexity_per_line'] = df['complexity'] / df['code'].replace(0, 1)  # Avoid division by zero
df['bytes_per_file'] = df['bytes'] / df['files'].replace(0, 1)
df['lines_per_file'] = df['code'] / df['files'].replace(0, 1)

# Calculate velocity (changes per time unit)
df['days_since_start'] = (df['date'] - df['date'].min()).dt.days
df['velocity'] = df['code'] / (df['days_since_start'] + 1)  # +1 to avoid division by zero

# Cumulative metrics
df['total_cost_growth'] = (df['cost'] - df['cost'].iloc[0]) / df['cost'].iloc[0] * 100 if df['cost'].iloc[0] > 0 else 0

def make_plot(y, title, ylabel, filename, color='blue'):
    plt.figure(figsize=(10,5))
    # Plot curve only (no points)
    plt.plot(df['date'], df[y], color=color)
    plt.xticks(rotation=45, ha='right')
    plt.title(title)
    plt.xlabel('Date')
    plt.ylabel(ylabel)
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_GRAPH_DIR, filename))
    plt.close()

def make_bar_plot(y, title, ylabel, filename, color='blue'):
    """Bar chart for changes"""
    plt.figure(figsize=(12,6))
    bars = plt.bar(range(len(df)), df[y], color=color, alpha=0.7)
    
    # Color negative bars differently
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
    """Correlation plot between two variables"""
    plt.figure(figsize=(8,6))
    # Replace scatter plot with hexbin (no individual points)
    hb = plt.hexbin(df[x], df[y], gridsize=30, cmap='viridis')
    plt.colorbar(hb, label='Density')
    
    # Trend line
    if len(df) > 1:
        z = np.polyfit(df[x].astype(float), df[y].astype(float), 1)
        p = np.poly1d(z)
        plt.plot(df[x], p(df[x]), "r--", alpha=0.8)
    
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_GRAPH_DIR, filename))
    plt.close()

# Individual existing graphs
make_plot('code', 'Lines of Code', 'Lines of Code', 'lines_of_code.png')
make_plot('complexity', 'Complexity', 'Complexity', 'complexity.png', 'red')
make_plot('files', 'Number of Dart Files', 'Number of Files', 'files_count.png', 'purple')
make_plot('cost', 'Estimated Cost ($)', 'Cost ($)', 'cost.png', 'green')
make_plot('effort', 'Estimated Effort (months)', 'Effort (months)', 'effort.png', 'orange')
make_plot('people', 'Estimated People', 'People', 'people.png', 'grey')
make_plot('bytes', 'Bytes Processed', 'Bytes', 'bytes.png', 'brown')

# NEW COMPARISON GRAPHS

# 1. Changes per commit (lines added/removed)
make_bar_plot('code_change', 'Code Line Changes per Commit', 'Lines Added/Removed', 'code_changes.png')
make_bar_plot('files_change', 'File Changes per Commit', 'Files Added/Removed', 'files_changes.png')
make_bar_plot('complexity_change', 'Complexity Changes per Commit', 'Complexity Added/Removed', 'complexity_changes.png')
make_bar_plot('bytes_change', 'Byte Changes per Commit', 'Bytes Added/Removed', 'bytes_changes.png')

# 2. Quality metrics and ratios
make_plot('complexity_per_line', 'Complexity per Line of Code', 'Complexity/Line', 'complexity_ratio.png', 'darkred')
make_plot('bytes_per_file', 'Average File Size', 'Bytes/File', 'file_size_avg.png', 'darkorange')
make_plot('lines_per_file', 'Average Lines per File', 'Lines/File', 'lines_per_file.png', 'darkblue')

# 3. Velocity and temporal trends
make_plot('velocity', 'Development Velocity', 'Lines/Day', 'velocity.png', 'darkgreen')

# 4. Correlation graphs
make_correlation_plot('code', 'complexity', 'Code vs Complexity Correlation', 'Lines of Code', 'Complexity', 'correlation_code_complexity.png')
make_correlation_plot('files', 'complexity', 'Files vs Complexity Correlation', 'Number of Files', 'Complexity', 'correlation_files_complexity.png')
make_correlation_plot('code', 'cost', 'Code vs Cost Correlation', 'Lines of Code', 'Cost ($)', 'correlation_code_cost.png')

# 5. Advanced comparative graphs

# Evolution of cumulative changes
plt.figure(figsize=(12,8))
plt.subplot(2, 2, 1)
plt.plot(df['date'], df['code_change'].cumsum(), color='blue', label='Code')
plt.plot(df['date'], df['files_change'].cumsum(), color='purple', label='Files')
plt.xticks(rotation=45, ha='right')
plt.title('Cumulative Changes')
plt.xlabel('Date')
plt.ylabel('Cumulative Changes')
plt.legend()
plt.grid(True, alpha=0.3)

# Distribution of change sizes
plt.subplot(2, 2, 2)
plt.hist(df['code_change'].dropna(), bins=20, alpha=0.7, color='blue', edgecolor='black')
plt.title('Code Change Distribution')
plt.xlabel('Lines Added/Removed')
plt.ylabel('Frequency')
plt.grid(True, alpha=0.3)

# Evolution of efficiency (complexity/cost)
plt.subplot(2, 2, 3)
efficiency = df['complexity'] / df['cost'].replace(0, 1)
plt.plot(df['date'], efficiency, color='red')
plt.xticks(rotation=45, ha='right')
plt.title('Efficiency (Complexity/Cost)')
plt.xlabel('Date')
plt.ylabel('Efficiency')
plt.grid(True, alpha=0.3)

# Growth trend
plt.subplot(2, 2, 4)
growth_rate = df['code'].pct_change() * 100
plt.plot(df['date'], growth_rate, color='green')
plt.axhline(y=0, color='black', linestyle='--', alpha=0.5)
plt.xticks(rotation=45, ha='right')
plt.title('Code Growth Rate (%)')
plt.xlabel('Date')
plt.ylabel('Growth (%)')
plt.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_GRAPH_DIR, 'advanced_comparisons.png'), dpi=300)
plt.close()

# 6. Detailed temporal analysis
plt.figure(figsize=(14,6))

# Activity by day of week
df['day_of_week'] = df['date'].dt.day_name()
day_activity = df.groupby('day_of_week')['code_change'].sum().abs()
day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
day_activity = day_activity.reindex([day for day in day_order if day in day_activity.index])

plt.subplot(1, 2, 1)
plt.bar(range(len(day_activity)), day_activity.values, color='skyblue')
plt.xticks(range(len(day_activity)), [day[:3] for day in day_activity.index], rotation=45)
plt.title('Activity by Day of Week')
plt.xlabel('Day')
plt.ylabel('Absolute Changes')
plt.grid(True, alpha=0.3)

# Last 30 days trend
plt.subplot(1, 2, 2)
if len(df) >= 30:
    recent_df = df.tail(30)
    plt.plot(recent_df['date'], recent_df['code'], color='blue', label='Code')
    plt.plot(recent_df['date'], recent_df['complexity'], color='red', label='Complexity')
    plt.xticks(rotation=45, ha='right')
    plt.title('Last 30 Commits Trend')
    plt.xlabel('Date')
    plt.ylabel('Value')
    plt.legend()
    plt.grid(True, alpha=0.3)
else:
    plt.text(0.5, 0.5, 'Not enough data\n(< 30 commits)', 
             ha='center', va='center', transform=plt.gca().transAxes, fontsize=12)
    plt.title('Last 30 Commits Trend')

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_GRAPH_DIR, 'temporal_analysis.png'), dpi=300)
plt.close()

# 7. Statistical summary of changes
print("\n📊 CHANGE STATISTICS:")
print(f"├─ Largest code addition: {df['code_change'].max():.0f} lines")
print(f"├─ Largest code deletion: {df['code_change'].min():.0f} lines")
print(f"├─ Average change per commit: {df['code_change'].mean():.1f} lines")
print(f"├─ Median of changes: {df['code_change'].median():.1f} lines")
print(f"├─ Standard deviation: {df['code_change'].std():.1f} lines")
print(f"└─ Commits with additions: {(df['code_change'] > 0).sum()}/{len(df)} ({(df['code_change'] > 0).mean()*100:.1f}%)")

# 8. Correlation heatmap
correlation_data = df[['code', 'complexity', 'files', 'cost', 'effort', 'people', 'bytes']].corr()

plt.figure(figsize=(10,8))
im = plt.imshow(correlation_data, cmap='RdBu_r', aspect='auto', vmin=-1, vmax=1)
plt.colorbar(im, label='Correlation')

# Add values in cells
for i in range(len(correlation_data.columns)):
    for j in range(len(correlation_data.columns)):
        plt.text(j, i, f'{correlation_data.iloc[i, j]:.2f}', 
                ha='center', va='center', fontweight='bold')

plt.xticks(range(len(correlation_data.columns)), correlation_data.columns, rotation=45, ha='right')
plt.yticks(range(len(correlation_data.columns)), correlation_data.columns)
plt.title('Metrics Correlation Matrix')
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_GRAPH_DIR, 'correlation_matrix.png'), dpi=300)
plt.close()

# Combined normalized graph
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
        # Plot normalized curve only (no points)
        plt.plot(df['date'], norm, label=col.capitalize(), color=color)

plt.xticks(rotation=45, ha='right')
plt.title('Normalized Evolution of Indicators')
plt.xlabel('Date')
plt.ylabel('Normalized Value (0-1)')
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_GRAPH_DIR, 'combined_normalized.png'))
plt.close()

# 9. Normalized ratio curves (min-max per series)
# These curves compare useful ratios while rescaling
# each series to 0-1 scale to avoid one series dominating the axis.
ratios = {
    'Lines / File': df['code'] / df['files'].replace(0, pd.NA),
    'Complexity / Lines': df['complexity'] / df['code'].replace(0, pd.NA),
    'Complexity / File': df['complexity'] / df['files'].replace(0, pd.NA),
    'Bytes / File': df['bytes'] / df['files'].replace(0, pd.NA)
}

ratio_df = pd.DataFrame({k: v.replace([np.inf, -np.inf], pd.NA).fillna(0) for k, v in ratios.items()})

# Min-max normalization per-series (avoid division by zero)
norm_den = (ratio_df.max() - ratio_df.min()).replace(0, 1)
ratio_norm = (ratio_df - ratio_df.min()) / norm_den

plt.figure(figsize=(12, 6))
colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
for i, col in enumerate(ratio_norm.columns):
    # Plot curves only (no points) for cleaner reading
    plt.plot(df['date'], ratio_norm[col], label=col, color=colors[i % len(colors)])

plt.xticks(rotation=45, ha='right')
plt.title('Comparative Ratio Curves (normalized per series 0-1)')
plt.xlabel('Date')
plt.ylabel('Normalized Value (0-1)')
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_GRAPH_DIR, 'ratio_curves.png'), dpi=300)
plt.close()

print(f"\n✅ Graphs generated in {OUTPUT_GRAPH_DIR}")
print(f"📈 New graphs added:")
print("   ├─ Changes per commit (code_changes.png, files_changes.png, etc.)")
print("   ├─ Quality metrics (complexity_ratio.png, file_size_avg.png, etc.)")
print("   ├─ Development velocity (velocity.png)")
print("   ├─ Correlations (correlation_*.png)")
print("   ├─ Advanced comparisons (advanced_comparisons.png)")
print("   ├─ Temporal analysis (temporal_analysis.png)")
print("   └─ Correlation matrix (correlation_matrix.png)")
