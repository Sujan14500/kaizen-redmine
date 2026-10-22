# Redmine PO Workstation

Desktop tools for Product Owners who work in [Redmine](https://www.redmine.org/).
Each app is one Python file: download, install `requests`, run. No server, no database.

| App | File | What it does |
|---|---|---|
| **Redmine PO Workstation** | `redmine_workstation.py` | Connects to Redmine over its REST API. Grooming workspace, PRD drafts, sprint planner, retrospectives, release notes (Markdown / Word), team view, management dashboard with KPIs and a one-click status report. |
| **PO Home** | `po_home.py` | Personal home base. Tasks typed in plain English, reminders and follow-ups, meetings and notes, client pipeline, contract register, stakeholder update emails, release calendar, team leave, quick links. Works offline; shows a live peek at the Workstation. |

## Requirements

- Python 3.8+ with Tkinter (included in the python.org installers for Windows and macOS; on Linux install `python3-tk`)
- A Redmine instance with the REST API enabled (*Administration → Settings → API → Enable REST web service*)

## Install

```bash
git clone https://github.com/Sujan14500/redmine-po-workstation.git
cd redmine-po-workstation
python -m pip install -r requirements.txt
```

Or download the ZIP from GitHub and unzip it anywhere.

## Run

**Windows:** double-click `Start Redmine Workstation.bat` or `Start PO Home.bat`.

**Any OS:**

```bash
python redmine_workstation.py
python po_home.py
```

Keep both files in the same folder. PO Home opens the Workstation from there.

## First-time setup

1. In Redmine, open **My account** and copy your **API access key** (right sidebar).
2. In the Workstation, enter your Redmine base URL (e.g. `https://redmine.example.com`) and the key, then connect.

### Optional customisation

- **Track tag:** tickets with the Redmine tag in `TRACK_TAG` (top of `redmine_workstation.py`, default `2.0`) show as track "2.0", the rest as "Legacy". Change it to your own tag. Tag columns need a Redmine tags plugin. Without one they show `?`.
- **Holidays:** the default list is India's 2026 public holidays. Edit it in the Workstation's **Sprint Planner** tab. PO Home uses the same list.
- **Start with Windows:** PO Home can start at login. It's off by default. Turn it on in PO Home → Settings.

## Your data

Everything stays on your machine, next to the scripts:

- `PO_Workstation_Data/`: settings (**including your Redmine API key, in plain text**), PRD drafts, backups
- `PO_Home_Data/`: tasks, meetings, clients, contracts

If the folder isn't writable, the apps use your home folder instead. Both folders are in `.gitignore`. Don't commit them or share them.

## Contributing

Issues and pull requests are welcome. Keep each app a single file with no required dependency beyond `requests`.

## License

[MIT](LICENSE)
