# SCC History & Discord Reporter

This project automates the extraction of Git repository history, code analysis with [scc](https://github.com/boyter/scc), generation of evolution graphs, and sending weekly reports to Discord.

## Features
- Extract code history (lines, complexity, cost, etc.) commit by commit
- Generate SCC reports (JSON + TXT)
- Generate evolution and quality graphs
- Automatically send synthetic reports to Discord with graphs
- Centralized configuration via .env file

## Prerequisites
- Python 3.8+
- [scc](https://github.com/boyter/scc) (installed and accessible in PATH)
- Git (installed)
- [pandas](https://pandas.pydata.org/), [matplotlib](https://matplotlib.org/), [numpy](https://numpy.org/), [requests](https://requests.readthedocs.io/), [python-dotenv](https://pypi.org/project/python-dotenv/)

## Installation
1. Clone this repository
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Install scc (see https://github.com/boyter/scc)
4. Copy `.env.example` to `.env` and configure your settings:
   ```bash
   cp .env.example .env
   ```
5. Edit `.env` with your repository URL, Discord webhook, etc.

## Configuration
All configuration is done via the `.env` file:
- `REPO_URL`: Git repository URL to analyze
- `BRANCH`: Branch to analyze (default: main)
- `DISCORD_WEBHOOK_URL`: Discord webhook URL for reports
- `WEBHOOK_AVATAR_URL`: Avatar URL for Discord bot
- `REPORT_DIR`: Directory for SCC reports (default: scc_reports)
- `GRAPH_DIR`: Directory for generated graphs (default: scc_graphs)
- `AUTO_GENERATE_GRAPHS`: Auto-generate graphs (true/false)

## Usage
- **Extract history**:
  ```bash
  python extract_scc_history.py
  ```
- **Generate graphs**:
  ```bash
  python plot_scc_history.py
  ```
- **Send Discord report**:
  ```bash
  python send_scc_discord_report.py
  ```
- **Automation (Windows cron)**:
  ```bash
  python scc_cron_job.py
  ```

## Directory Structure
- `scc_reports/` : Generated SCC reports (JSON, TXT)
- `scc_graphs/` : Generated graphs (PNG)

## Customization
- Modify scripts to change branch, repository, graph format, etc.
- Discord message and graphs are customizable in `send_scc_discord_report.py`.

## Examples
- See `scc_graphs/` folder for generated graphs
- Discord report example in documentation or README

## License
MIT

---

*Automated project for code evolution tracking and team communication!*
