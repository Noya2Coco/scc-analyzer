# send_scc_discord_report.py
# Sends a weekly SCC report to Discord
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
# Discord bot name and avatar (not user-configurable)
WEBHOOK_USERNAME = "SCC Bot"
WEBHOOK_AVATAR_URL = os.getenv('WEBHOOK_AVATAR_URL', 'https://icons-for-free.com/iff/png/512/graph+graphic+graphics+icon-1320168051322057462.png')
AUTO_GENERATE_GRAPHS = os.getenv('AUTO_GENERATE_GRAPHS', 'true').lower() in ('true', '1', 'yes')

# Auto-generate graphs if requested
if AUTO_GENERATE_GRAPHS:
    import plot_scc_history

# Load SCC data
json_files = [f for f in os.listdir(REPORT_DIR) if f.endswith('.json')]
data = []
for file in sorted(json_files):
    commit_date_str = file.replace('scc_', '').replace('.json', '')
    # Fix: remove timezone suffix (_+xxxx or _-xxxx)
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
    print('No usable data.')
    exit(1)
df = pd.DataFrame(data).sort_values(by='date')

# Filter last week
now = datetime.now()
week_ago = now - timedelta(days=7)
df_week = df[df['date'] >= week_ago]

# Key statistics
code_change = int(df_week['code'].iloc[-1] - df_week['code'].iloc[0]) if len(df_week) > 1 else 0
files_change = int(df_week['files'].iloc[-1] - df_week['files'].iloc[0]) if len(df_week) > 1 else 0
complexity_change = int(df_week['complexity'].iloc[-1] - df_week['complexity'].iloc[0]) if len(df_week) > 1 else 0
cost_change = int(df_week['cost'].iloc[-1] - df_week['cost'].iloc[0]) if len(df_week) > 1 else 0

max_code = df['code'].max()
max_code_date = df.loc[df['code'].idxmax(), 'date'].strftime('%d/%m/%Y')
max_complexity = df['complexity'].max()
max_complexity_date = df.loc[df['complexity'].idxmax(), 'date'].strftime('%d/%m/%Y')

# Calculate changes
if 'code_change' not in df.columns:
    df['code_change'] = df['code'].diff().fillna(0).astype(int)
if 'complexity_change' not in df.columns:
    df['complexity_change'] = df['complexity'].diff().fillna(0).astype(int)

# Calculate 3-month trends (weekly average over 90 days)
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

# Generate main graph (code/complexity evolution)
plt.figure(figsize=(10,5))
# Plot curves only (no points)
plt.plot(df['date'], df['code'], label='Lines of Code', color='#3498db')
plt.plot(df['date'], df['complexity'], label='Complexity', color='#e74c3c')
plt.title('Code and Complexity Evolution')
plt.xlabel('Date')
plt.ylabel('Value')
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
graph_path = os.path.join(GRAPH_DIR, 'weekly_main.png')
plt.savefig(graph_path)
plt.close()

# Generate variations per commit graph (code_change and complexity_change)
plt.figure(figsize=(12,6))
bar_width = 0.4
x = np.arange(len(df))
# Dynamic colors based on sign
code_colors = ['#2ecc40' if v > 0 else '#3498db' for v in df['code_change']]
cplx_colors = ['#e74c3c' if v > 0 else '#f1c40f' for v in df['complexity_change']]
# Side-by-side bars
bars_code = plt.bar(x - bar_width/2, df['code_change'], width=bar_width, color=code_colors, alpha=0.8, label='Δ Lines of Code (⬆️ green, ⬇️ blue)')
bars_cplx = plt.bar(x + bar_width/2, df['complexity_change'], width=bar_width, color=cplx_colors, alpha=0.8, label='Δ Complexity (⬆️ red, ⬇️ orange)')
# Spaced dates (1 in 7)
step = max(1, len(df)//14)
plt.xticks(x[::step], [d.strftime('%m-%d') for d in df['date']][::step], rotation=45, ha='right', fontsize=9)
plt.title('Changes per Commit (lines of code & complexity)')
plt.xlabel('Date')
plt.ylabel('Variation')
# Explicit legend
from matplotlib.patches import Patch
legend_elements = [
    Patch(facecolor='#2ecc40', label='Lines of Code ↑ (green)'),
    Patch(facecolor='#3498db', label='Lines of Code ↓ (blue)'),
    Patch(facecolor='#e74c3c', label='Complexity ↑ (red)'),
    Patch(facecolor='#f1c40f', label='Complexity ↓ (orange)')
]
plt.legend(handles=legend_elements)
plt.grid(True, alpha=0.3)
plt.tight_layout()
graph_path_changes = os.path.join(GRAPH_DIR, 'weekly_changes.png')
plt.savefig(graph_path_changes)
plt.close()

# Top 3 commits (addition, deletion, complexity peak)
top_add = df['code_change'].idxmax()
top_del = df['code_change'].idxmin()
top_cplx = df['complexity_change'].idxmax()
top_summary = f"""
**Top commits:**
• ➕ {df['code_change'].max():,} lines on {df.loc[top_add, 'date'].strftime('%d/%m/%Y')}
• ➖ {df['code_change'].min():,} lines on {df.loc[top_del, 'date'].strftime('%d/%m/%Y')}
• 🟥 +{df['complexity_change'].max():,} complexity on {df.loc[top_cplx, 'date'].strftime('%d/%m/%Y')}
"""

# Quick visual summary
if code_change > 100:
    headline = '🔥 **Record development week!**'
elif code_change < 0:
    headline = '📉 **Refactoring or cleanup week!**'
else:
    headline = '📊 **Stable week**'

# Link to repo
repo_url = os.getenv('REPO_URL', '')
repo_link = f'\n🔗 [View analyzed repository]({repo_url})' if repo_url else ''

# Discord formatted message — description (embed title set separately)
summary = f"""
{headline}{repo_link}

**Period:** {week_ago.strftime('%d/%m/%Y')} → {now.strftime('%d/%m/%Y')}

**Lines of Code:** {df_week['code'].iloc[-1] if len(df_week) else df['code'].iloc[-1]:,} {'🟩' if code_change > 0 else '🟥'} ({code_change:+,} {'⬆️' if code_change > 0 else '⬇️' if code_change < 0 else '➖'})
**Dart Files:** {df_week['files'].iloc[-1] if len(df_week) else df['files'].iloc[-1]:,} {'🟦' if files_change > 0 else '🟥'} ({files_change:+,} {'⬆️' if files_change > 0 else '⬇️' if files_change < 0 else '➖'})
**Complexity:** {df_week['complexity'].iloc[-1] if len(df_week) else df['complexity'].iloc[-1]:,} {'🟥' if complexity_change > 0 else '🟧'} ({complexity_change:+,} {'⬆️' if complexity_change > 0 else '⬇️' if complexity_change < 0 else '➖'})
**Estimated Cost:** ${df_week['cost'].iloc[-1] if len(df_week) else df['cost'].iloc[-1]:,} {'💸' if cost_change > 0 else '💰'} ({cost_change:+,} {'⬆️' if cost_change > 0 else '⬇️' if cost_change < 0 else '➖'})

━━━━━━━━━━━━━━━━━━━━

🏆 **Records**
• Max lines of code: {max_code:,} ({max_code_date})
• Max complexity: {max_complexity:,} ({max_complexity_date})

━━━━━━━━━━━━━━━━━━━━

📈 **Trends (weekly average over 3 months)**
• Weekly growth: {avg_weekly_code:+,} lines
• Files: {avg_weekly_files:+,}
• Complexity: {avg_weekly_complexity:+,}

━━━━━━━━━━━━━━━━━━━━
{top_summary}
_Sent automatically by SCC Bot_
"""

ratio_path = os.path.join(GRAPH_DIR, 'ratio_curves.png')

# Calculate top-N files by LOC in Flutter project (if present)
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
    lines = ['**Top 10 files (by Lines of Code):**']
    for i, (p, total, code, comment, blank) in enumerate(top_list, start=1):
        try:
            rel = os.path.relpath(p, start=project_root)
        except Exception:
            rel = p
        lines.append(f"{i}. `{rel}` — {code:,} lines (total {total:,}, comments {comment:,}, blank {blank:,})")
    top_block = "\n".join(lines)
    # store the block to add later (embed_ratio not yet defined)
    # limit size to stay under Discord embed limit (~4096 chars)
    if len(top_block) > 3700:
        top_block = top_block[:3690] + '\n...'

# Prepare two embeds: 1) summary + weekly_changes.png  2) normalized curves (ratio_curves.png)
embed_main = {
    "title": "✨ Weekly SCC Report ✨",
    "description": summary,
    "color": 0x3498db,
    "author": {"name": WEBHOOK_USERNAME, "icon_url": WEBHOOK_AVATAR_URL},
    "image": {"url": "attachment://weekly_changes.png"},
    "footer": {"text": f"Powered by SCC Bot • Generated on {now.strftime('%d/%m/%Y at %H:%M') }"}
}
embed_ratio = {
    "title": "📊 Ratio Curves (normalized)",
    "description": "Normalized comparison of useful ratios (lines/file, lines/complexity, ...)",
    "color": 0x2ecc71,
    "image": {"url": "attachment://ratio_curves.png"}
}

# If we calculated a top_block above, add it now to the description
try:
    if top_list:
        desc = embed_ratio.get('description', '') + '\n\n' + top_block
        if len(desc) > 3800:
            desc = desc[:3790] + '\n...'
        embed_ratio['description'] = desc
except NameError:
    # top_list/top_block not defined: nothing to do
    pass

payload = {"embeds": [embed_main, embed_ratio], "username": WEBHOOK_USERNAME, "avatar_url": WEBHOOK_AVATAR_URL}

# Build list of files to send. Discord accepts multiple files under the same 'file' key.
files_to_send = []
if os.path.exists(graph_path_changes):
    files_to_send.append((os.path.basename(graph_path_changes), graph_path_changes))
else:
    print(f'⚠️ Missing graph: {graph_path_changes}')
if os.path.exists(ratio_path):
    files_to_send.append((os.path.basename(ratio_path), ratio_path))
else:
    print(f'⚠️ Missing graph: {ratio_path}')

data = {
    "payload_json": json.dumps(payload)
}

# Open files in a context manager to ensure closure
opened = []
try:
    for fname, fpath in files_to_send:
        f = open(fpath, 'rb')
        opened.append(f)
    # Build explicit file0/file1/... mapping to avoid
    # some endpoints only accepting a single 'file' key.
    files = []
    for i, (fname, _) in enumerate(files_to_send):
        field_name = f'file{i}'
        # find corresponding fileobj (opened list matches files_to_send order)
        fileobj = opened[i]
        # try to guess mime type, default to image/png
        mime = 'image/png'
        files.append((field_name, (fname, fileobj, mime)))

    # Debug: list attached files and multipart fields
    print('📎 Attached files:', [fname for fname, _ in files_to_send])
    print('📎 Multipart fields sent:', [f[0] for f in files])

    # Send to Discord — payload_json + files named file0,file1,...
    resp = requests.post(WEBHOOK_URL, data=data, files=files)
    print('Discord response:', resp.status_code, resp.text)
    if resp.status_code in (200, 204):
        print('✅ Report sent to Discord! (with attachments if present)')
    else:
        print(f'Discord error: {resp.status_code} {resp.text}')
finally:
    for f in opened:
        try:
            f.close()
        except Exception:
            pass
