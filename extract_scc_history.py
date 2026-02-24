# extract_scc_history.py
# Python script to clone a repository, iterate through commits, and generate scc reports (json + txt)
import os
import shutil
import subprocess
import tempfile
import json
import re
import argparse
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def load_config():
    """Load configuration from environment variables."""
    config = {
        'REPO_URL': os.getenv('REPO_URL'),
        'BRANCH': os.getenv('BRANCH', 'main'),
        'REPORT_DIR': os.getenv('REPORT_DIR', 'scc_reports'),
        'GRAPH_DIR': os.getenv('GRAPH_DIR', 'scc_graphs'),
        'DISCORD_WEBHOOK_URL': os.getenv('DISCORD_WEBHOOK_URL', ''),
        'AUTO_GENERATE_GRAPHS': os.getenv('AUTO_GENERATE_GRAPHS', 'true').lower() in ('true', '1', 'yes')
    }
    
    if not config['REPO_URL']:
        raise ValueError('REPO_URL must be set in .env file')
    
    return config

config = load_config()
REPO_URL = config['REPO_URL']

def select_latest_version_branch(repo_url):
    """Return the branch name with the highest version like v1.2.3 from remote heads.
    Falls back to 'main' or 'master' if none found. Returns None on error."""
    try:
        res = subprocess.run(['git', 'ls-remote', '--heads', repo_url], capture_output=True, text=True, check=True)
        lines = [l.strip() for l in res.stdout.splitlines() if l.strip()]
        version_branches = []
        for line in lines:
            # line format: <sha>\trefs/heads/<branch>
            parts = line.split('\t')
            if len(parts) != 2:
                continue
            ref = parts[1]
            if ref.startswith('refs/heads/'):
                branch = ref[len('refs/heads/'):]
                m = re.match(r'^v(\d+(?:\.\d+)*)$', branch)
                if m:
                    ver_str = m.group(1)
                    ver_tuple = tuple(int(x) for x in ver_str.split('.'))
                    version_branches.append((ver_tuple, branch))
        if version_branches:
            # pick branch with max version tuple (lexicographic on ints)
            version_branches.sort(key=lambda x: x[0], reverse=True)
            return version_branches[0][1]
        # fallback: try detect 'main' or 'master' among remote heads
        for line in lines:
            parts = line.split('\t')
            if len(parts) != 2:
                continue
            ref = parts[1]
            if ref.endswith('/main'):
                return 'main'
            if ref.endswith('/master'):
                return 'master'
        return None
    except Exception:
        return None

parser = argparse.ArgumentParser(description='Extract SCC history from a repo (with branch auto-detect).')
parser.add_argument('--branch', '-b', help='Branch to analyze (overrides auto-detection)')
args = parser.parse_args()

# Determine branch: CLI override > auto-detected highest v* branch > config BRANCH > 'main'
if args.branch:
    BRANCH = args.branch
else:
    detected = select_latest_version_branch(config.get('REPO_URL'))
    if detected:
        BRANCH = detected
    else:
        BRANCH = config.get('BRANCH') if config.get('BRANCH') else 'main'

OUTPUT_DIR = os.path.abspath(config.get('REPORT_DIR', 'scc_reports'))

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# Use a temporary folder for cloning
temp_dir = tempfile.mkdtemp(prefix='scc_temp_')
print(f"Cloning repository to {temp_dir} ...")

try:
    subprocess.run([
        'git', 'clone', '--no-checkout', '--branch', BRANCH, REPO_URL, temp_dir
    ], check=True)

    os.chdir(temp_dir)
    # List of commits (from most recent to oldest)
    result = subprocess.run(['git', 'rev-list', BRANCH], capture_output=True, text=True, check=True)
    commits = result.stdout.strip().split('\n')

    for commit in commits:
        # Get commit date
        date_result = subprocess.run([
            'git', 'show', '-s', '--format=%ci', commit
        ], capture_output=True, text=True, check=True)
        commit_date = date_result.stdout.strip()
        # Clean formatting for filename
        commit_date_fmt = commit_date.replace(' ', '_').replace(':', '-').replace('/', '-').replace('.', '-')
        report_file = os.path.join(OUTPUT_DIR, f'scc_{commit_date_fmt}.json')
        summary_file = os.path.join(OUTPUT_DIR, f'scc_{commit_date_fmt}_summary.txt')

        if os.path.exists(report_file):
            print(f"Commit {commit} from {commit_date_fmt} already analyzed. Skipping.")
            continue
        print(f"Analyzing {commit} from {commit_date_fmt} ...")
        subprocess.run(['git', 'checkout', '--quiet', commit], check=True)
        # Run scc
        with open(report_file, 'w', encoding='utf-8') as f_json:
            subprocess.run(['scc', '--format', 'json', 'lib/'], stdout=f_json, check=True)
        with open(summary_file, 'w', encoding='utf-8') as f_txt:
            subprocess.run(['scc', 'lib/'], stdout=f_txt, check=True)
finally:
    os.chdir(os.path.dirname(__file__))
    print(f"Removing temporary folder {temp_dir} ...")
    shutil.rmtree(temp_dir, ignore_errors=True)

print(f"Analysis complete. Reports are in: {OUTPUT_DIR}")
