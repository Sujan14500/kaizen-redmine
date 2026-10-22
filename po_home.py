#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PO Home
=======
Your personal home base as a Product Owner:

  * 🧭 Redmine Workstation   – opens the workstation, with a live peek at what needs you
  * 🗂 My PA                 – type tasks in plain English; a daily plate, reminders, follow-ups
  * 📅 Meetings & Notes      – your meetings (added by hand), notes → action items
  * 🤝 Clients & Demos       – client pipeline, demo prep checklists, follow-up emails
  * ⚖️ Legal & Contracts     – contract register with renewal / notice reminders
  * 📣 Stakeholder update    – weekly status email drafted for you
  * 🗓 Release calendar      – sprints, production dates, holidays, demos, deadlines
  * 🏖 Team availability     – leave and capacity
  * 🔗 Quick links · 📚 Templates · 🌿 Focus & breaks

Keep this file in the same folder as redmine_workstation.py.
Run:  python po_home.py        (Windows)
"""

from __future__ import annotations

import calendar as cal
import datetime as dt
import json
import os
import platform
import queue
import re
import shutil
import socket
import subprocess
import sys
import threading
import webbrowser
from collections import Counter
from pathlib import Path

import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox, simpledialog, ttk

APP_NAME = "PO Home"
IS_WINDOWS = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"
HERE = Path(__file__).resolve().parent
SINGLE_PORT = 47391


def _pick_data_dir() -> Path:
    try:
        d = HERE / "PO_Home_Data"
        d.mkdir(exist_ok=True)
        (d / ".w").write_text("ok", encoding="utf-8")
        (d / ".w").unlink()
        return d
    except OSError:
        d = Path.home() / "PO_Home_Data"
        d.mkdir(exist_ok=True)
        return d


DATA_DIR = _pick_data_dir()
DATA_PATH = DATA_DIR / "po_home.json"
WS_SETTINGS = [HERE / "PO_Workstation_Data" / "settings.json", Path.home() / ".redmine_po_workstation.json"]

LIGHT = {
    "bg": "#FAF6F1", "panel": "#FFFFFF", "ink": "#3B3632", "muted": "#8A8078", "line": "#EADFD4",
    "accent": "#C2665C", "accent_dark": "#A3534A", "good": "#6E9C7A", "warn": "#D9A05B", "bad": "#C9665E",
    "info": "#8BA5C4", "header": "#4A3F3A", "soft": "#FBEDE8", "soft_line": "#F0D5CC", "sage_soft": "#EEF4EF",
    "sand_soft": "#FCF3E4", "blue_soft": "#EEF2F8", "lilac": "#B49FCC", "lilac_soft": "#F3EEF8",
    "field": "#FFFFFF", "bar": "#F1E9E1", "head_bg": "#F6EFE8", "hover": "#FFF9F6", "btn_hover": "#F8EEE9",
    "btn_press": "#F1DDD5", "select": "#F6DCD6", "faint": "#B3A99F", "cell_off": "#FBF8F5", "cell_hol": "#F5EFE9",
    "amber": "#B07A2A", "blue": "#6F8DB3", "lilac_ink": "#8A6FB0", "sand_ink": "#C88A3C", "on_accent": "#FFFFFF",
    "hero": "#F6E3DC", "hero2": "#FBF1E6",
}
DARK = {
    "bg": "#1D1A18", "panel": "#282422", "ink": "#ECE4DC", "muted": "#A89C92", "line": "#3B3531",
    "accent": "#E0887C", "accent_dark": "#C46F64", "good": "#8DBE99", "warn": "#E2B26C", "bad": "#E5807A",
    "info": "#9DB6D6", "header": "#F4EBE3", "soft": "#3A2B28", "soft_line": "#5C413B", "sage_soft": "#24302A",
    "sand_soft": "#352B1F", "blue_soft": "#222A35", "lilac": "#B9A3D6", "lilac_soft": "#2D2735",
    "field": "#211E1C", "bar": "#24201E", "head_bg": "#302A27", "hover": "#312B28", "btn_hover": "#3A322E",
    "btn_press": "#463A36", "select": "#4B3430", "faint": "#6C625B", "cell_off": "#221F1D", "cell_hol": "#2C2724",
    "amber": "#E0A85A", "blue": "#95B1D8", "lilac_ink": "#BBA2DD", "sand_ink": "#E2A85C", "on_accent": "#FFFFFF",
    "hero": "#3A2A27", "hero2": "#2F2621",
}
C = dict(LIGHT)
FONTS: dict = {}

DEFAULT_HOLIDAYS_2026 = [
    ("2026-01-01", "New Year’s Day"), ("2026-01-14", "Pongal/Makar Sankranti"), ("2026-01-26", "Republic Day"),
    ("2026-03-04", "Holi"), ("2026-03-19", "Ugadi/Gudi Padwa"), ("2026-09-14", "Ganesh/Vinayaka Chaturthi"),
    ("2026-10-02", "Gandhi Jayanti"), ("2026-10-20", "Dussehra"), ("2026-11-09", "Day after Diwali"),
    ("2026-12-25", "Christmas"),
]
PRIORITIES = ["High", "Normal", "Low"]
TASK_TYPES = ["Task", "Follow-up", "Review", "Meeting prep", "Demo prep", "Legal", "Redmine", "Email", "Call"]
STATUSES = ["Pending", "Waiting", "Done"]   # "Pending" is stored as "Open"
RECURRENCES = ["None", "Daily", "Weekdays", "Weekly", "Every 2 weeks", "Monthly", "Last weekday of month"]
MEETING_REPEATS = ["Does not repeat", "Every weekday (Mon–Fri)", "On the days I tick below", "Weekly", "Every 2 weeks", "Monthly (same date)",
                   "Monthly (same weekday, e.g. 2nd Tue)", "Last weekday of the month"]
TASK_TO_MEETING_REPEAT = {"Custom days": "On the days I tick below", "Daily": "Every weekday (Mon–Fri)", "Weekdays": "Every weekday (Mon–Fri)",
                          "Weekly": "Weekly", "Every 2 weeks": "Every 2 weeks", "Monthly": "Monthly (same date)",
                          "Last weekday of month": "Last weekday of the month"}
MEETING_TYPES = ["Client demo", "Client meeting", "Internal", "Grooming", "1:1", "Other"]
CLIENT_STAGES = ["Lead", "Demo planned", "Demo done", "Proposal", "Negotiation", "Won", "Lost", "On hold"]
CONTRACT_TYPES = ["NDA", "MSA", "SOW", "Amendment", "Order form", "DPA", "Other"]
CONTRACT_STATUS = ["Draft", "In review", "Sent for signature", "Signed", "Expired", "Terminated"]
CONTRACT_CHECKS = ["Parties & signatories correct", "Term & renewal clear", "Termination & notice period",
                   "Payment terms", "Liability & indemnity", "Confidentiality", "IP ownership",
                   "Data protection", "Governing law", "Signed copy filed"]
DEMO_CHECKLIST = ["Demo environment ready", "Demo data set up", "Script / flow agreed", "Attendees confirmed",
                  "Client's earlier questions answered", "Backup plan (recording / screenshots)"]
LEAVE_TYPES = ["Leave", "Sick", "WFH", "Training", "Travel", "Other"]
LEAVE_PARTS = ["Full day", "First half (morning)", "Second half (afternoon)"]


def leave_fraction(lv) -> float:
    """1 for a full day off, 0.5 for a half day."""
    return 0.5 if (lv or {}).get("part", "Full day").startswith(("First", "Second")) else 1.0


def leave_short(lv) -> str:
    part = (lv or {}).get("part", "Full day")
    return "" if part.startswith("Full") else (" ½ AM" if part.startswith("First") else " ½ PM")
DEFAULT_TEMPLATES = [
    ("Polite nudge", "Follow-up",
     "Hi {name},\n\nJust a gentle nudge on {topic}. Could you share an update when you get a moment?\n\nThanks!"),
    ("Demo follow-up", "Clients",
     "Hi {name},\n\nThank you for your time at today's demo of {product}. As discussed, the next steps are:\n"
     "• {next_steps}\n\nPlease let me know if you have any questions.\n\nBest regards,"),
    ("Contract cover email", "Legal",
     "Hi {name},\n\nPlease find attached the {contract} for your review. Kindly share your comments or "
     "sign by {date}.\n\nBest regards,"),
    ("Handover request", "Team",
     "Hi {name},\n\nBefore your last day ({date}), could you please add a status note to each of your open "
     "tickets and let me know who you'd suggest to take them over?\n\nThank you!"),
    ("Weekly status opener", "Status",
     "Hi all,\n\nHere's the weekly product update for {week}.\n"),
]
DAY_NAMES = {"mon": 0, "monday": 0, "tue": 1, "tues": 1, "tuesday": 1, "wed": 2, "wednesday": 2, "thu": 3,
             "thur": 3, "thurs": 3, "thursday": 3, "fri": 4, "friday": 4, "sat": 5, "saturday": 5, "sun": 6,
             "sunday": 6}
MONTHS = {m.lower(): i for i, m in enumerate(cal.month_abbr) if m}
MONTHS.update({m.lower(): i for i, m in enumerate(cal.month_name) if m})


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------
def today() -> dt.date:
    return dt.date.today()


def parse_date(value):
    if not value:
        return None
    if isinstance(value, dt.date):
        return value
    try:
        return dt.date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def parse_user_date(text):
    t = re.sub(r"\s+", " ", (text or "").strip().replace(",", ""))
    for f in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d-%b-%Y", "%d %b %Y", "%d %B %Y", "%d.%m.%Y", "%d-%b-%y"):
        try:
            return dt.datetime.strptime(t, f).date()
        except ValueError:
            pass
    return None


def parse_time(text):
    t = re.sub(r"\b([ap])\.?m\.?", r"\1m", (text or "").strip().lower()).replace(".", ":")
    m = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", t)
    if not m:
        return None
    h, mi, ap = int(m.group(1)), int(m.group(2) or 0), m.group(3)
    if ap == "pm" and h < 12:
        h += 12
    if ap == "am" and h == 12:
        h = 0
    if h > 23 or mi > 59:
        return None
    return f"{h:02d}:{mi:02d}"


def fmt_date(d, day=True):
    d = parse_date(d)
    if not d:
        return "—"
    return d.strftime("%a %d-%b-%Y") if day else d.strftime("%d-%b-%Y")


def short_date(d):
    d = parse_date(d)
    if not d:
        return ""
    if d == today():
        return "Today"
    if d == today() + dt.timedelta(days=1):
        return "Tomorrow"
    if d == today() - dt.timedelta(days=1):
        return "Yesterday"
    return d.strftime("%a %d-%b")


def plural(n, word, pl=None):
    return f"{n} {word if n == 1 else (pl or word + 's')}"


def truncate(text, n):
    text = text or ""
    return text if len(text) <= n else text[:n - 1] + "…"


def norm(name):
    return " ".join((name or "").lower().split())


def new_id(items):
    return max([it.get("id", 0) for it in items] + [0]) + 1


def is_working_day(d, hols):
    return d.weekday() < 5 and d not in hols


def add_working_days(d, n, hols):
    """Move n working days (negative = back)."""
    step = 1 if n >= 0 else -1
    left = abs(n)
    while left:
        d += dt.timedelta(days=step)
        if is_working_day(d, hols):
            left -= 1
    return d


def count_working_days(a, b, hols):
    if not a or not b or b < a:
        return 0
    n, d = 0, a
    while d <= b:
        n += is_working_day(d, hols)
        d += dt.timedelta(days=1)
    return n


def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def save_json(path, data):
    tmp = Path(str(path) + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    tmp.replace(path)


def backup_daily(path: Path, keep=14):
    try:
        root = path.parent / "backups"
        day = root / today().isoformat()
        if path.exists() and not day.exists():
            day.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, day / path.name)
        days = sorted(p for p in root.iterdir() if p.is_dir()) if root.exists() else []
        for old in days[:-keep]:
            shutil.rmtree(old, ignore_errors=True)
    except OSError:
        pass


# --------------------------------------------------------------------------
# Plain-English task capture
# --------------------------------------------------------------------------
TYPE_WORDS = [
    ("Follow-up", r"\b(follow[ -]?up|chase|remind|nudge|check (?:in|with|on))\b"),
    ("Review", r"\b(review|go through|proof ?read|approve)\b"),
    ("Legal", r"\b(contract|nda|msa|sow|legal|agreement|clause|sign(?:ature)?)\b"),
    ("Demo prep", r"\b(demo)\b"),
    ("Meeting prep", r"\b(prep(?:are)? for|agenda|meeting prep)\b"),
    ("Redmine", r"\b(ticket|redmine|groom(?:ing)?|prd|sprint|release notes)\b|#\d{3,}"),
    ("Email", r"\b(email|mail|reply to)\b"),
    ("Call", r"\b(call|phone)\b"),
]
HASH_TYPES = {"followup": "Follow-up", "fu": "Follow-up", "review": "Review", "legal": "Legal",
              "demo": "Demo prep", "prep": "Meeting prep", "redmine": "Redmine", "email": "Email", "call": "Call",
              "task": "Task"}


def _next_weekday(base, wd, force_next=False):
    days = (wd - base.weekday()) % 7
    if days == 0 or force_next:
        days = days or 7
    return base + dt.timedelta(days=days)


def parse_task(text: str, people=(), base=None) -> dict:
    """Understand a line like 'Follow up with Alex on SAP API by Friday 3pm !high'."""
    base = base or today()
    s = " " + (text or "").strip() + " "
    out = {"priority": "Normal", "type": "Task", "person": "", "due": None, "time": "", "status": "Open",
           "recur": "None"}

    def cut(pattern, flags=re.I):
        nonlocal s
        m = re.search(pattern, s, flags)
        if m:
            s = s[:m.start()] + " " + s[m.end():]
        return m

    # priority
    if cut(r"\s!(high|h|urgent|asap|1)\b"):
        out["priority"] = "High"
    elif cut(r"\s!(low|l|3)\b"):
        out["priority"] = "Low"
    elif cut(r"\s!(normal|n|2)\b"):
        out["priority"] = "Normal"
    if re.search(r"\b(urgent|asap|critical|immediately)\b", s, re.I):
        out["priority"] = "High"
    # hashtag type
    m = cut(r"\s#([a-z][a-z-]+)\b")
    if m and m.group(1).lower() in HASH_TYPES:
        out["type"] = HASH_TYPES[m.group(1).lower()]
    # weekday ranges: "every Tue to Fri" (repeats on those days) / "Tue to Fri" (one event over several days)
    m = cut(r"\bevery\s+(mon|tue|tues|wed|thu|thur|thurs|fri|sat|sun)[a-z]*\s*(?:to|till|until|through|-|–)\s*(mon|tue|tues|wed|thu|thur|thurs|fri|sat|sun)[a-z]*\b")
    if m:
        a_, b_ = DAY_NAMES[m.group(1).lower()[:3] if m.group(1).lower()[:3] in DAY_NAMES else m.group(1).lower()], \
            DAY_NAMES[m.group(2).lower()[:3] if m.group(2).lower()[:3] in DAY_NAMES else m.group(2).lower()]
        out["recur"] = "Custom days"
        out["recur_days"] = list(range(a_, b_ + 1)) if a_ <= b_ else list(range(a_, 7)) + list(range(0, b_ + 1))
        d0 = base
        while d0.weekday() not in out["recur_days"]:
            d0 += dt.timedelta(days=1)
        out["due"] = d0
    m = cut(r"\b(?:from\s+)?(mon|tue|tues|wed|thu|thur|thurs|fri|sat|sun)[a-z]*\s+(?:to|till|until|through|-|–)\s+(mon|tue|tues|wed|thu|thur|thurs|fri|sat|sun)[a-z]*\b")
    if m:
        a_ = DAY_NAMES[m.group(1).lower()[:3]]
        b_ = DAY_NAMES[m.group(2).lower()[:3]]
        d0 = base if base.weekday() == a_ else _next_weekday(base, a_)
        d1 = d0
        while d1.weekday() != b_:
            d1 += dt.timedelta(days=1)
        out["due"], out["end"] = d0, d1
    # recurrence
    m = cut(r"\b(?:every\s+(?:other|2(?:nd)?|second|alternate)\s+(week|monday|tuesday|wednesday|thursday|friday|mon|"
            r"tue|wed|thu|fri)|fortnightly|bi-?weekly|every\s+two\s+weeks|alternate\s+(?:weeks|"
            r"monday|tuesday|wednesday|thursday|friday)s?)\b")
    if m:
        out["recur"] = "Every 2 weeks"
        w = (m.group(1) or "").lower()
        if w in DAY_NAMES:
            out["due"] = _next_weekday(base, DAY_NAMES[w])
    m = cut(r"\bevery\s+(day|weekday|week|month|monday|tuesday|wednesday|thursday|friday|mon|tue|wed|thu|fri)\b")
    if m:
        w = m.group(1).lower()
        if w == "day":
            out["recur"] = "Daily"
        elif w == "weekday":
            out["recur"] = "Weekdays"
        elif w == "week":
            out["recur"] = "Weekly"
        elif w == "month":
            out["recur"] = "Monthly"
        else:
            out["recur"] = "Weekly"
            out["due"] = _next_weekday(base, DAY_NAMES[w])
    if cut(r"\b(daily)\b"):
        out["recur"] = "Daily"
    if cut(r"\b(monthly)\b"):
        out["recur"] = "Monthly"
    if cut(r"\b(weekly)\b"):
        out["recur"] = "Weekly"
    m = cut(r"\blast\s+(monday|tuesday|wednesday|thursday|friday)\s+of\s+(?:the\s+)?month\b")
    if m:
        out["recur"] = "Last weekday of month"
        wd = DAY_NAMES[m.group(1).lower()]
        out["due"] = last_weekday_of_month(base, wd)
        out["recur_wd"] = wd
    # time
    m = (cut(r"\b(?:at\s+)?(\d{1,2}(?:[:.]\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.))(?=\W|$)")
         or cut(r"\bat\s+(\d{1,2}[:.]\d{2})\b") or cut(r"(?<![\d/.-])\b((?:[01]?\d|2[0-3]):[0-5]\d)\b(?![/.-]\d)"))
    if m:
        out["time"] = parse_time(m.group(1)) or ""
    # dates
    pre = r"(?:\b(?:by|on|due|before|for)\s+)?"
    m = cut(pre + r"\b(today|tonight|eod)\b")
    if m:
        out["due"] = base
    m = cut(pre + r"\b(yesterday)\b")
    if m:
        out["due"] = base - dt.timedelta(days=1)
    m = cut(pre + r"\b(day after tomorrow)\b")
    if m:
        out["due"] = base + dt.timedelta(days=2)
    m = cut(pre + r"\b(tomorrow|tmrw|tmr)\b")
    if m:
        out["due"] = base + dt.timedelta(days=1)
    m = cut(pre + r"\b(end of (?:the )?week|eow|this week)\b")
    if m:
        out["due"] = _next_weekday(base - dt.timedelta(days=1), 4) if base.weekday() <= 4 else \
            _next_weekday(base, 4)
    m = cut(pre + r"\b(next week)\b")
    if m:
        out["due"] = _next_weekday(base, 0, force_next=True)
    m = cut(pre + r"\b(end of (?:the )?month|eom)\b")
    if m:
        out["due"] = dt.date(base.year, base.month, cal.monthrange(base.year, base.month)[1])
    m = cut(pre + r"\bin\s+(\d{1,2})\s+(day|days|week|weeks)\b")
    if m:
        n = int(m.group(1)) * (7 if m.group(2).startswith("week") else 1)
        out["due"] = base + dt.timedelta(days=n)
    m = cut(pre + r"\b(next\s+)?(monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tue|tues|wed|"
                  r"thu|thur|thurs|fri|sat|sun)\b")
    if m:
        out["due"] = _next_weekday(base, DAY_NAMES[m.group(2).lower()], force_next=bool(m.group(1)))
    m = cut(pre + r"\b(\d{1,2})(?:st|nd|rd|th)?[\s-]+(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*"
                  r"(?:[\s-]+(\d{4}))?\b")
    if m:
        out["due"] = _safe_date(m.group(3), m.group(2), m.group(1), base)
    else:
        m = cut(pre + r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s+(\d{1,2})(?:st|nd|rd|th)?"
                      r"(?:\s+(\d{4}))?\b")
        if m:
            out["due"] = _safe_date(m.group(3), m.group(1), m.group(2), base)
        else:
            m = cut(pre + r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b")
            if m:
                try:
                    y = int(m.group(3)) if m.group(3) else base.year
                    y = y + 2000 if y < 100 else y
                    d = dt.date(y, int(m.group(2)), int(m.group(1)))
                    if not m.group(3) and d < base - dt.timedelta(days=30):
                        d = d.replace(year=d.year + 1)
                    out["due"] = d
                except ValueError:
                    pass
    # waiting on someone
    m = re.search(r"\b(waiting (?:for|on)|awaiting|asked|delegated to)\s+([a-z]+)", s, re.I)
    if m:
        out["status"] = "Waiting"
    # person (from the team list / contacts)
    low = s.lower()
    best = ""
    for p in people:
        full = norm(p)
        first = full.split(" ")[0] if full else ""
        if full and re.search(r"\b" + re.escape(full) + r"\b", low):
            best = p
            break
        if first and len(first) > 2 and re.search(r"\b" + re.escape(first) + r"\b", low) and not best:
            best = p
    out["person"] = best
    # type from words (if no hashtag)
    if out["type"] == "Task":
        for typ, pat in TYPE_WORDS:
            if re.search(pat, s, re.I):
                out["type"] = typ
                break
    if out["status"] == "Waiting" and out["type"] == "Task":
        out["type"] = "Follow-up"
    title = re.sub(r"\s+", " ", s).strip(" ,.-")
    title = re.sub(r"\b(by|on|due|before|at|for)$", "", title, flags=re.I).strip(" ,.-")
    out["title"] = title[:1].upper() + title[1:] if title else (text or "").strip()
    return out


def _safe_date(year, mon, day, base):
    try:
        mi = MONTHS[mon.lower()[:3]] if mon.lower()[:3] in MONTHS else MONTHS[mon.lower()]
        y = int(year) if year else base.year
        d = dt.date(y, mi, int(day))
        if not year and d < base - dt.timedelta(days=60):
            d = d.replace(year=d.year + 1)
        return d
    except (ValueError, KeyError):
        return None


def last_weekday_of_month(base, wd):
    y, m = base.year, base.month
    for _ in range(2):
        last = dt.date(y, m, cal.monthrange(y, m)[1])
        while last.weekday() != wd:
            last -= dt.timedelta(days=1)
        if last >= base:
            return last
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return last


def next_occurrence(task) -> dt.date:
    d = parse_date(task.get("due")) or today()
    r = task.get("recur", "None")
    if r == "Daily":
        return d + dt.timedelta(days=1)
    if r == "Weekdays":
        n = d + dt.timedelta(days=1)
        while n.weekday() >= 5:
            n += dt.timedelta(days=1)
        return n
    if r == "Weekly":
        return d + dt.timedelta(days=7)
    if r == "Every 2 weeks":
        return d + dt.timedelta(days=14)
    if r == "Monthly":
        y, m = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
        return dt.date(y, m, min(d.day, cal.monthrange(y, m)[1]))
    if r == "Last weekday of month":
        wd = task.get("recur_wd", d.weekday())
        return last_weekday_of_month(d + dt.timedelta(days=1), wd)
    return d


def _add_months(d, n):
    y, m = divmod(d.month - 1 + n, 12)
    return d.year + y, m + 1


def series_dates(rule, start, a, b, hols=None, skip_hols=True, days=None):
    """Every date of a repeating meeting between a and b (inclusive). No end date needed."""
    hols = hols or {}
    start = parse_date(start)
    if not start or not rule or rule.startswith("Does not"):
        return []
    out, a = [], max(a, start)

    def ok(d):
        return a <= d <= b and not (skip_hols and d in hols)

    if rule.startswith(("Every weekday", "On the days")):
        allowed = set(days or []) if rule.startswith("On the days") else {0, 1, 2, 3, 4}
        d = a
        while d <= b:
            if d.weekday() in allowed and ok(d):
                out.append(d)
            d += dt.timedelta(days=1)
    elif rule in ("Weekly", "Every 2 weeks"):
        step = 7 if rule == "Weekly" else 14
        k = max(0, (a - start).days // step)
        d = start + dt.timedelta(days=step * k)
        while d <= b:
            if ok(d):
                out.append(d)
            d += dt.timedelta(days=step)
    else:
        nth = (start.day - 1) // 7 + 1
        for i in range(0, 600):
            y, m = _add_months(start, i)
            last_day = cal.monthrange(y, m)[1]
            if rule.startswith("Monthly (same date)"):
                d = dt.date(y, m, min(start.day, last_day))
            elif rule.startswith("Monthly (same weekday"):
                first = dt.date(y, m, 1)
                d = first + dt.timedelta(days=(start.weekday() - first.weekday()) % 7 + 7 * (nth - 1))
                if d.month != m:
                    d -= dt.timedelta(days=7)
            else:  # last weekday of the month
                d = dt.date(y, m, last_day)
                while d.weekday() != start.weekday():
                    d -= dt.timedelta(days=1)
            if d > b:
                break
            if ok(d):
                out.append(d)
    return out


WEEKDAY_SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def repeat_label(rule, start=None, days=None):
    start = parse_date(start)
    if not rule or rule.startswith("Does not"):
        return ""
    if rule.startswith("On the days"):
        ds = sorted(days or [])
        if ds and ds == list(range(ds[0], ds[-1] + 1)) and len(ds) > 2:
            return f"every {WEEKDAY_SHORT[ds[0]]}–{WEEKDAY_SHORT[ds[-1]]}"
        return "every " + ", ".join(WEEKDAY_SHORT[i] for i in ds) if ds else "on chosen days"
    if start and rule == "Weekly":
        return f"every {start.strftime('%A')}"
    if start and rule == "Every 2 weeks":
        return f"every other {start.strftime('%A')}"
    if start and rule.startswith("Monthly (same weekday"):
        nth = ["1st", "2nd", "3rd", "4th", "5th"][(start.day - 1) // 7]
        return f"every {nth} {start.strftime('%A')} of the month"
    if start and rule.startswith("Last weekday"):
        return f"last {start.strftime('%A')} of every month"
    if start and rule.startswith("Monthly (same date)"):
        return f"every month on the {start.day}"
    return "every weekday" if rule.startswith("Every weekday") else rule.lower()


ACTION_LINE = re.compile(r"^\s*(?:[-*•]\s*)?(?:\[\s?\]\s*)?(?:action(?:\s*item)?s?|ai|todo|to do|next step|→|->|"
                         r"follow[ -]?up)\s*[:\-–]\s*(.+)$", re.I)


ACTION_VERBS = (r"send|share|check|update|fix|schedule|prepare|prep|review|confirm|call|email|mail|follow up|create|"
                r"draft|set up|setup|book|ask|plan|finali[sz]e|submit|raise|log|test|deploy|sync|connect|arrange|"
                r"get|collect|reply|write|add|remove|move|close|chase|validate|investigate|look into|circle back|"
                r"reach out|provide|demo|present|organi[sz]e|coordinate|escalate|align|approve|sign|loop in|"
                r"talk to|speak to|discuss|explore|estimate|groom|document|record|upload|download|install|"
                r"configure|migrate|merge|resolve|clarify|inform|notify|remind|invite|"
                r"compile|analy[sz]e|research|design|build|deliver|complete|finish|work on")
_VERB = r"(?:%s)\b" % ACTION_VERBS
_SKIP = re.compile(r"^(?:discussed|decided|decision|agreed that|noted|fyi|note:|update:|status:|attendees|agenda|"
                   r"present:|participants|summary|background|context)\b", re.I)
_FILLER = re.compile(r"^(?:(?:so|and|also|ok|okay|then|plus|next|\\-|–)[,:]?\s+)+", re.I)
_ME = re.compile(r"^(?:i'?ll|i will|i need to|i have to|i must|i'm going to|i am going to|i should|i can|"
                 r"we need to|we'll|we will|we should|we have to|we must|let'?s|need to|have to|must|"
                 r"please|pls|plz|can you|could you)\s+", re.I)


MEETING_START = re.compile(r"^\s*(?:meeting|meet|sync|catch[ -]?up|demo|1[:-]1|one on one|standup|stand-up|"
                           r"review meeting|interview|workshop|session|grooming session|kick[ -]?off)\b", re.I)


MEETING_WORDS = re.compile(r"\b(meeting|meet|sync|scrum|triage|steering|status call|connect|standup|stand-up|stand up|1[:-]1|one on one|catch[ -]?up|demo|"
                           r"call with|sprint review|sprint planning|planning|retro|retrospective|grooming|townhall|"
                           r"town hall|all hands|interview|workshop|kick[ -]?off|huddle|check-in|webinar|session)\b",
                           re.I)


def looks_like_meeting(text, parsed=None):
    """'Demo with Acme Friday 3pm', 'Acme sync every other Tuesday 3pm', 'Standup every weekday 10:30'."""
    parsed = parsed or parse_task(text)
    if MEETING_START.match(text):
        return True
    if re.match(_VERB, text.strip(), re.I):  # "Prepare grooming…", "Send demo…" are tasks
        return False
    repeats = parsed.get("recur", "None") != "None"
    if repeats and parsed.get("time"):  # "Technical Scrum every weekday 11.30 am"
        return True
    return bool(MEETING_WORDS.search(text) and (parsed.get("time") or repeats))


def split_sentences(line):
    line = re.sub(r"^\s*(?:[-*•▪◦]|\d+[.)])\s*", "", line)
    parts = re.split(r"(?<=[.!?;])\s+|\s+(?:–|—|-{1,2})\s+|\s*\|\s*", line)
    return [p.strip(" .;") for p in parts if p and len(p.strip()) > 3]


def free_text_action(sent, people=()):
    """Spot an action in a plain sentence like 'Alex will share the API doc by Thursday' or
    'need to send revised pricing to Acme'. Returns cleaned text or None."""
    whole = _FILLER.sub("", sent.strip())
    if len(whole.split()) < 3:
        return None
    clauses = [whole] + [c for c in re.split(r",\s+|\s+(?:but|and so|so|and then|then)\s+", whole) if c != whole]
    for loose in (False, True):  # clear "who does what" first, then any line with a date
        for c in (clauses if not loose else [whole]):
            hit = _action_clause(_FILLER.sub("", c.strip()), people, loose)
            if hit:
                return hit
    return None


def _action_clause(s, people, loose=False):
    if len(s.split()) < 3 or _SKIP.match(s):
        return None
    low = s.lower()
    firsts = {norm(p).split(" ")[0] for p in people if norm(p)}
    # 1. Me / us: "I'll send…", "we need to share…", "let's schedule…", "can you loop in…"
    m = _ME.match(s)
    if m:
        rest = _FILLER.sub("", s[m.end():])
        if re.match(_VERB, rest, re.I):
            return rest
    # 2. Plain instruction: "Send the deck to Ravi by Friday"
    if re.match(_VERB, s, re.I) and not re.match(r"(?:discuss|explore|research|call|demo|sync|present|record|"
                                                 r"review)\b", s, re.I):
        return s
    # 3. Someone else: "Alex will share…", "ravi to send…", "they will confirm…"
    m = re.match(r"^([A-Za-z]+)(?:\s+said|\s+mentioned|\s+promised)?\s+(?:that\s+)?(?:they\s+|he\s+|she\s+)?"
                 r"(?:will|'ll|to|should|needs? to|has to|have to|is going to|are going to|agreed to|promised to|"
                 r"offered to)\s+(.*)$", s, re.I)
    if m and (m.group(1).lower() in firsts or m.group(1).lower() in ("they", "he", "she", "client", "team")
              or m.group(1)[0].isupper()) and re.match(_VERB, m.group(2), re.I):
        return s
    # 4. "pending from Alex: API doc", "waiting on Ravi for the sample data"
    m = re.search(r"\b(?:pending (?:from|with|on)|waiting (?:for|on)|awaiting)\s+([A-Za-z]+)\b[:\s,-]*(.*)", s, re.I)
    if m and (m.group(1).lower() in firsts or m.group(1)[0].isupper()):
        rest = m.group(2).strip() or s
        return f"Waiting for {m.group(1).capitalize()}: {rest}"
    if not loose:
        return None
    # 5. Any line with a date in it: "Acme proposal 25 Oct", "SSO timeline confirm by Friday"
    if parse_task(s, people).get("due") and len(s.split()) >= 2:
        return s
    # 6. A team member + a verb + a deadline anywhere in the sentence
    if (any(f and f in re.findall(r"[a-z]+", low) for f in firsts) and re.search(_VERB, low) and
            re.search(r"\b(by|before|until|eod|eow|tomorrow|today|next week|monday|tuesday|wednesday|thursday|"
                      r"friday)\b", low)):
        return s
    return None


ACTION_HEADER = re.compile(r"^(?:action items?|actions?|next steps?|to ?dos?|follow[ -]?ups?|tasks|"
                           r"takeaways|owners?)\s*:?$", re.I)


def extract_actions(notes: str, people=()) -> list:
    """Find action items in pasted meeting notes."""
    found = []
    in_section = False
    for raw in (notes or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        bare = re.sub(r"^[#*_\s]+|[*_\s]+$", "", line)
        if ACTION_HEADER.match(bare):
            in_section = True
            continue
        if in_section and (bare.endswith(":") or line.startswith("#")):
            in_section = False
        m = ACTION_LINE.match(line)
        text = m.group(1).strip() if m else None
        if not text and in_section:
            text = re.sub(r"^\s*(?:[-*•▪◦]|\d+[.)]|\[\s?[xX]?\])\s*", "", line).strip() or None
        if not text:
            m1 = re.match(r"^\s*(?:[-*•]\s*)?(?:TODO|AI|ACTION)\s+(.+)$", line)
            if m1:
                text = m1.group(1).strip()
        if not text:
            m2 = re.match(r"^\s*(?:[-*•]\s*)?\[\s?\]\s*(.+)$", line)
            if m2:
                text = m2.group(1).strip()
        if not text:
            m3 = re.match(r"^\s*(?:[-*•]\s*)?@(\w+)\s+(.+)$", line)
            if m3:
                text = f"{m3.group(1)} {m3.group(2)}"
        texts = [text] if text else [x for x in (free_text_action(sent, people) for sent in split_sentences(line))
                                     if x]
        for text in texts:
            t = parse_task(text, people)
            t["mine"] = bool(re.match(_VERB, text, re.I))  # starts with a verb = something I do
            if t["title"] and len(t["title"]) > 3 and norm(t["title"]) not in {norm(f["title"]) for f in found}:
                found.append(t)
    return found


def todo_lines(notes: str, people=()) -> list:
    """To-do scratch pad: every line is a task (dates/people/priority are read from the line)."""
    out = []
    for raw in (notes or "").splitlines():
        line = re.sub(r"^\s*(?:[-*•▪◦]|\d+[.)]|\[\s?[xX]?\])\s*", "", raw).strip()
        if len(line) < 3 or line.endswith(":"):
            continue
        t = parse_task(line, people)
        if t["title"]:
            t["mine"] = not re.match(r"^[A-Z][a-z]+\s+(?:to|will|should)\s", line)
            out.append(t)
    return out


def task_score(t, hols=None) -> float:
    """Higher = do it sooner. Used for 'Top 3 for today'."""
    d = parse_date(t.get("due"))
    sc = {"High": 6, "Normal": 3, "Low": 0}.get(t.get("priority"), 3)
    if d:
        delta = (d - today()).days
        if delta < 0:
            sc += 8 + min(10, -delta)
        elif delta == 0:
            sc += 7
        elif delta == 1:
            sc += 3
        elif delta <= 3:
            sc += 1
    if t.get("type") in ("Legal", "Demo prep"):
        sc += 2
    if t.get("status") == "Waiting":
        sc -= 3
    return sc



# --------------------------------------------------------------------------
# Sprint maths (same rules as the Redmine Workstation's Sprint Planner)
# --------------------------------------------------------------------------
def next_working_day(d, hols):
    for _ in range(400):
        if is_working_day(d, hols):
            return d
        d += dt.timedelta(days=1)
    return d


def plan_sprints(start, mode, length, count, hols, prefix="Sprint", first_no=1):
    sprints = []
    s = next_working_day(start, hols)
    for i in range(max(1, count)):
        if mode == "working":
            end, n = s, 1
            while n < max(1, length):
                end += dt.timedelta(days=1)
                n += is_working_day(end, hols)
        else:
            end = s + dt.timedelta(days=7 * max(1, length) - 1)
            while end > s and not is_working_day(end, hols):
                end -= dt.timedelta(days=1)
        sprints.append({"name": f"{prefix} {first_no + i}".strip(), "start": s, "end": end, "kind": "Sprint"})
        s = next_working_day(end + dt.timedelta(days=1), hols)
    return sprints


def plan_from_cfg(cfg, hols):
    out = []
    start = parse_date(cfg.get("start"))
    count = int(cfg.get("count", 3))
    if start and count > 0:
        length = cfg.get("weeks", 2) if cfg.get("mode") == "calendar" else cfg.get("wdays", 10)
        regular = plan_sprints(start, cfg.get("mode", "calendar"), int(length), count, hols,
                               cfg.get("prefix", "Sprint"), int(cfg.get("first", 1)))
        if regular and count >= 2 and cfg.get("regression", True):
            last = regular[-1]
            last["kind"] = "Regression"
            extra = int(cfg.get("reg_extra", 0) or 0)
            end, n = last["end"], 0
            while n < extra:
                end += dt.timedelta(days=1)
                n += is_working_day(end, hols)
            last["end"] = end
        out.extend(regular)
    for i, ex in enumerate(cfg.get("extras") or []):
        a, b = parse_date(ex.get("start")), parse_date(ex.get("end"))
        if a:
            out.append({"name": ex.get("name") or f"Patch {i + 1}", "start": a, "end": b if b and b >= a else a,
                        "kind": ex.get("kind", "Patch release")})
    out.sort(key=lambda sp: (sp["start"], sp["end"]))
    closed = cfg.get("closed") or {}
    for sp in out:
        if sp["name"] in closed:
            sp["closed"] = True
    return out

# --------------------------------------------------------------------------
# Link to the Redmine Workstation (read-only)
# --------------------------------------------------------------------------
class Workstation:
    def __init__(self, app):
        self.app = app
        self._cfg, self._mtime = {}, None

    @property
    def path(self) -> Path:
        p = self.app.d["settings"].get("workstation_path") or ""
        return Path(p) if p else HERE / "redmine_workstation.py"

    def settings(self) -> dict:
        for f in WS_SETTINGS:
            try:
                m = f.stat().st_mtime
            except OSError:
                continue
            if m != self._mtime:
                self._cfg, self._mtime = load_json(f, {}), m
            return self._cfg
        return {}

    def holidays(self) -> dict:
        raw = self.settings().get("holidays")
        if raw is None:
            raw = DEFAULT_HOLIDAYS_2026
        out = {}
        for item in raw:
            d = parse_date(item[0])
            if d:
                out[d] = item[1] if len(item) > 1 else "Holiday"
        return out

    def team(self) -> list:
        return [m for m in (self.settings().get("team") or []) if m.get("name")]

    def plans(self) -> list:
        """[(release, [sprints...], plan)] from the workstation's Sprint Planner (calculated the same way)."""
        cfg = self.settings().get("sprint_plans") or {}
        hols = self.holidays()
        out = []
        for key, plan in cfg.items():
            try:
                out.append((key, plan_from_cfg(plan or {}, hols), plan))
            except (TypeError, ValueError):
                pass
        return out

    def current_sprint(self):
        t = today()
        soon = None
        for key, sprints, plan in self.plans():
            for i, sp in enumerate(sprints):
                if sp.get("closed"):
                    continue
                if sp["start"] <= t <= sp["end"]:
                    return key, sp
                # a holiday / weekend between two sprints counts as the next sprint
                if sp["start"] > t and (i == 0 and (sp["start"] - t).days <= 3 or
                                        i > 0 and sprints[i - 1]["end"] < t):
                    if soon is None or sp["start"] < soon[1]["start"]:
                        soon = (key, sp)
        return soon

    def production_dates(self):
        out = []
        for key, plan in (self.settings().get("sprint_plans") or {}).items():
            d = parse_date((plan or {}).get("prod_date"))
            if d:
                out.append((d, key))
        return sorted(out)

    def peek(self) -> dict:
        cfg = self.settings()
        t = today()
        grooms = {k: parse_date(v) for k, v in (cfg.get("groom_dates") or {}).items()}
        future = sorted({d for d in grooms.values() if d and d >= t})
        nxt = future[0] if future else None
        leavers = sorted((parse_date(m.get("relieving")), m["name"]) for m in self.team()
                         if m.get("status", "Active") == "Active" and parse_date(m.get("relieving"))
                         and parse_date(m["relieving"]) >= t)
        follow = [k for k, v in (cfg.get("ticket_notes") or {}).items()
                  if parse_date((v or {}).get("follow_up")) and parse_date(v["follow_up"]) <= t]
        return {"connected": bool(cfg.get("base_url")), "next_groom": nxt,
                "groom_count": sum(1 for d in grooms.values() if d == nxt) if nxt else 0,
                "leavers": leavers, "follow_ups": follow, "sprint": self.current_sprint(),
                "production": [p for p in self.production_dates() if p[0] >= t]}

    def plate_items(self) -> list:
        """Things from the workstation that belong on today's plate."""
        p = self.peek()
        t = today()
        hols = self.holidays()
        items = []
        if p["next_groom"] and (p["next_groom"] - t).days <= 1:
            items.append(("Redmine", f"Grooming session {short_date(p['next_groom'])}: "
                                     f"{plural(p['groom_count'], 'ticket')} to groom", p["next_groom"]))
        for d, name in p["leavers"]:
            if (d - t).days <= 14:
                items.append(("Team", f"{name} leaves {fmt_date(d)} ({(d - t).days} days): check the handover", d))
        if p["follow_ups"]:
            items.append(("Redmine", f"{plural(len(p['follow_ups']), 'ticket follow-up')} due in the workstation", t))
        if p["sprint"]:
            key, sp = p["sprint"]
            left = count_working_days(t + dt.timedelta(days=1), sp["end"], hols)
            if left <= 2:
                items.append(("Sprint", f"{key} · {sp['name']} ends {short_date(sp['end'])}: close it with comments",
                              sp["end"]))
        for d, key in p["production"]:
            wd = count_working_days(t + dt.timedelta(days=1), d, hols)
            if wd <= 5:
                items.append(("Release", f"🚀 {key} goes to production {short_date(d)} ({plural(wd, 'working day')})", d))
        return items

    def launch(self):
        path = self.path
        if not path.exists():
            p = filedialog.askopenfilename(parent=self.app, title="Where is redmine_workstation.py?",
                                           filetypes=[("Python file", "*.py")])
            if not p:
                return
            self.app.d["settings"]["workstation_path"] = p
            self.app.save()
            path = Path(p)
        exe = Path(sys.executable)
        pyw = exe.with_name("pythonw.exe")
        runner = str(pyw) if IS_WINDOWS and pyw.exists() else str(exe)
        try:
            subprocess.Popen([runner, str(path)], cwd=str(path.parent))
            self.app.set_status("Opening the Redmine Workstation…")
        except OSError as exc:
            messagebox.showerror(APP_NAME, f"Could not start the workstation:\n{exc}", parent=self.app)


# --------------------------------------------------------------------------
# Reusable UI bits
# --------------------------------------------------------------------------
def make_table(parent, columns, height=10, tree_col=None):
    frame = ttk.Frame(parent)
    tv = ttk.Treeview(frame, columns=[c[0] for c in columns], show="tree headings" if tree_col else "headings",
                      height=height)
    if tree_col:
        tv.heading("#0", text=tree_col[0], anchor="w")
        tv.column("#0", width=tree_col[1], stretch=True)
    for key, text, width in columns:
        tv.heading(key, text=text, anchor="w")
        tv.column(key, width=width, minwidth=40, stretch=key in ("title", "subject", "text", "notes", "link"),
                  anchor="w")
    sb = ttk.Scrollbar(frame, orient="vertical", command=tv.yview)
    tv.configure(yscrollcommand=sb.set)
    tv.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")
    tv.tag_configure("hot", foreground=C["bad"])
    tv.tag_configure("warm", foreground=C["amber"])
    tv.tag_configure("muted", foreground=C["faint"])
    tv.tag_configure("group", font=FONTS["small_bold"], background=C["head_bg"])
    tv.tag_configure("good", foreground=C["good"])
    return frame, tv


def form_dialog(parent, title, fields, values=None, width=460):
    """fields: (key, label, kind, options) with kind in entry/combo/choice/date/time/text/check.
    Returns a dict of values, or None when cancelled."""
    values = values or {}
    win = tk.Toplevel(parent)
    win.title(title)
    win.configure(bg=C["bg"])
    win.transient(parent)
    win.resizable(True, True)
    frm = ttk.Frame(win, padding=16, style="Bg.TFrame")
    frm.pack(fill="both", expand=True)
    widgets, result = {}, {}
    for r, (key, label, kind, opts) in enumerate(fields):
        ttk.Label(frm, text=label).grid(row=r, column=0, sticky="nw", pady=5, padx=(0, 12))
        val = values.get(key, "")
        if kind == "text":
            w = make_text(frm, height=opts or 5, width=48)
            w.insert("1.0", val or "")
            w.grid(row=r, column=1, sticky="nsew", pady=5)
            frm.rowconfigure(r, weight=1)
        elif kind in ("combo", "choice"):
            v = tk.StringVar(value=val if val else (opts[0] if kind == "choice" and opts else ""))
            w = ttk.Combobox(frm, textvariable=v, values=list(opts or []), width=44,
                             state="readonly" if kind == "choice" else "normal")
            w.grid(row=r, column=1, sticky="ew", pady=5)
            w.var = v
        elif kind == "check":
            v = tk.BooleanVar(value=bool(val))
            w = ttk.Checkbutton(frm, variable=v, text=opts or "")
            w.grid(row=r, column=1, sticky="w", pady=5)
            w.var = v
        elif kind == "days":
            w = ttk.Frame(frm, style="Bg.TFrame")
            w.grid(row=r, column=1, sticky="w", pady=5)
            w.vars = []
            for i, n in enumerate(WEEKDAY_SHORT):
                v = tk.BooleanVar(value=i in (val or []))
                ttk.Checkbutton(w, text=n, variable=v).pack(side="left", padx=(0, 8))
                w.vars.append(v)
        else:
            shown = val
            if kind == "date" and val:
                d = parse_date(val)
                shown = d.strftime("%d-%m-%Y") if d else val
            v = tk.StringVar(value=shown or "")
            w = ttk.Entry(frm, textvariable=v, width=46)
            w.grid(row=r, column=1, sticky="ew", pady=5)
            w.var = v
            if kind == "date":
                def pick(var=v):
                    d = pick_date(win, parse_user_date(var.get()) or today())
                    if d == "clear":
                        var.set("")
                    elif d:
                        var.set(d.strftime("%d-%m-%Y"))
                ttk.Button(frm, text="📅", width=3, command=pick).grid(row=r, column=2, sticky="w", padx=6)
            if kind == "time":
                ttk.Label(frm, text="e.g. 15:30 or 3:30 pm", style="Muted.TLabel").grid(row=r, column=2, sticky="w",
                                                                                     padx=6)
        widgets[key] = (kind, w)
    frm.columnconfigure(1, weight=1)

    def ok(_e=None):
        out = {}
        for key, (kind, w) in widgets.items():
            if kind == "text":
                out[key] = w.get("1.0", "end").strip()
            elif kind == "days":
                out[key] = [i for i, v in enumerate(w.vars) if v.get()]
            elif kind == "check":
                out[key] = bool(w.var.get())
            else:
                raw = w.var.get().strip()
                if kind == "date":
                    if raw:
                        d = parse_user_date(raw)
                        if not d:
                            messagebox.showinfo(APP_NAME, f"Please type '{key}' like 26-10-2026.", parent=win)
                            return
                        raw = d.isoformat()
                elif kind == "time" and raw:
                    tm = parse_time(raw)
                    if not tm:
                        messagebox.showinfo(APP_NAME, "Please type the time like 15:30 or 3:30 pm.", parent=win)
                        return
                    raw = tm
                out[key] = raw
        result.update(out)
        result["_ok"] = True
        win.destroy()

    bb = ttk.Frame(frm, style="Bg.TFrame")
    bb.grid(row=len(fields), column=0, columnspan=3, sticky="e", pady=(14, 0))
    ttk.Button(bb, text="Cancel", command=win.destroy).pack(side="right")
    ttk.Button(bb, text="Save", style="Accent.TButton", command=ok).pack(side="right", padx=8)
    win.bind("<Escape>", lambda e: win.destroy())
    win.update_idletasks()
    win.minsize(width, win.winfo_reqheight())
    center_on(win, parent)
    try:
        win.grab_set()
    except tk.TclError:
        pass
    parent.wait_window(win)
    if result.get("_ok"):
        result.pop("_ok")
        return result
    return None


class Toast(tk.Toplevel):
    """A gentle reminder that pops up in the bottom-right corner."""
    stack = []

    def __init__(self, app, title, lines, buttons=(), colour=None):
        super().__init__(app)
        self.app = app
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg=colour or C["accent"])
        inner = tk.Frame(self, bg=C["panel"], padx=16, pady=12)
        inner.pack(fill="both", expand=True, padx=(5, 1), pady=1)
        tk.Label(inner, text=title, bg=C["panel"], fg=C["header"], font=FONTS["h3"], anchor="w",
                 justify="left", wraplength=360).pack(fill="x")
        for ln in list(lines)[:8]:
            tk.Label(inner, text=ln, bg=C["panel"], fg=C["ink"], font=FONTS["body"], anchor="w", justify="left",
                     wraplength=360).pack(fill="x", pady=(3, 0))
        bb = tk.Frame(inner, bg=C["panel"])
        bb.pack(fill="x", pady=(10, 0))
        for label, cb in list(buttons) + [("Dismiss", None)]:
            def run(c=cb):
                self.close()
                if c:
                    c()
            ttk.Button(bb, text=label, command=run, style="Accent.TButton" if cb else "TButton").pack(side="right",
                                                                                                    padx=(6, 0))
        Toast.stack.append(self)
        self.update_idletasks()
        self._place()
        try:
            app.bell()
        except tk.TclError:
            pass

    def _place(self):
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        y = sh - 60
        for t in Toast.stack:
            if t.winfo_exists():
                t.update_idletasks()
                h = t.winfo_reqheight()
                y -= h + 10
                t.geometry(f"400x{h}+{sw - 420}+{y}")

    def close(self):
        if self in Toast.stack:
            Toast.stack.remove(self)
        self.destroy()
        for t in Toast.stack:
            t._place()
            break


class AppTile(tk.Frame):
    """A small launcher tile on the home page."""

    def __init__(self, parent, icon, title, colour, soft, command):
        super().__init__(parent, bg=C["panel"], highlightbackground=C["line"], highlightthickness=1, cursor="hand2")
        self.command = command
        tk.Frame(self, bg=colour, width=4).pack(side="left", fill="y")
        body = tk.Frame(self, bg=C["panel"])
        body.pack(side="left", fill="both", expand=True, padx=(10, 10), pady=10)
        top = tk.Frame(body, bg=C["panel"])
        top.pack(fill="x")
        self.icon = tk.Label(top, text=icon, bg=soft, fg=colour, font=FONTS["icon"], width=2, padx=4)
        self.icon.pack(side="left")
        self.title = tk.Label(top, text=title, bg=C["panel"], fg=C["header"], font=FONTS["h3"], anchor="w")
        self.title.pack(side="left", padx=(8, 0))
        self.badge = tk.Label(top, text="", bg=C["accent"], fg=C["on_accent"], font=FONTS["small_bold"], padx=7)
        self.sub = tk.Label(body, text="", bg=C["panel"], fg=C["muted"], font=FONTS["small"], anchor="w",
                            justify="left", wraplength=200)
        self.sub.pack(fill="x", pady=(6, 0))
        self._plain = [self, body, top, self.title, self.sub]
        for w in self._plain + [self.icon, self.badge]:
            w.bind("<Button-1>", lambda e: self.command())
            w.bind("<Enter>", lambda e: self._hover(True))
            w.bind("<Leave>", lambda e: self._hover(False))
        self.bind("<Configure>", lambda e: self.sub.configure(wraplength=max(140, e.width - 40)))

    def _hover(self, on):
        bg = C["hover"] if on else C["panel"]
        for w in self._plain:
            w.configure(bg=bg)
        self.configure(highlightbackground=C["accent"] if on else C["line"])

    def set(self, text, badge=None, hot=False):
        self.sub.configure(text=text)
        if badge:
            self.badge.configure(text=str(badge), bg=C["bad"] if hot else C["accent"])
            self.badge.pack(side="right", before=self.title)
        else:
            self.badge.pack_forget()


def center_on(win, parent):
    """Place a pop-up window in the middle of the app window."""
    try:
        win.update_idletasks()
        w, h = win.winfo_reqwidth(), win.winfo_reqheight()
        x = parent.winfo_rootx() + max(0, (parent.winfo_width() - w) // 2)
        y = parent.winfo_rooty() + max(0, (parent.winfo_height() - h) // 3)
        win.geometry(f"+{x}+{y}")
    except tk.TclError:
        pass


def choice_dialog(parent, title, text, options):
    """Ask the user to pick one of a few buttons. Returns the option text, or None if cancelled."""
    res = {}
    win = tk.Toplevel(parent)
    win.title(title)
    win.configure(bg=C["bg"])
    win.transient(parent)
    frm = ttk.Frame(win, padding=18, style="Bg.TFrame")
    frm.pack(fill="both", expand=True)
    ttk.Label(frm, text=text, justify="left", wraplength=420).pack(anchor="w", pady=(0, 12))
    for i, o in enumerate(options):
        ttk.Button(frm, text=o, style="Accent.TButton" if i == 0 else "TButton",
                   command=lambda oo=o: (res.setdefault("v", oo), win.destroy())).pack(fill="x", pady=3)
    ttk.Button(frm, text="Cancel", command=win.destroy).pack(fill="x", pady=(10, 0))
    win.bind("<Escape>", lambda e: win.destroy())
    center_on(win, parent)
    try:
        win.grab_set()
    except tk.TclError:
        pass
    parent.wait_window(win)
    return res.get("v")


def pick_date(parent, initial=None, title="Pick a date", quick=()):
    """A small calendar. Returns a date, "clear" (no date), or None (cancelled)."""
    initial = initial or today()
    res = {}
    win = tk.Toplevel(parent)
    win.title(title)
    win.configure(bg=C["bg"])
    win.transient(parent)
    win.resizable(False, False)
    frm = tk.Frame(win, bg=C["bg"], padx=14, pady=12)
    frm.pack()
    state = {"month": initial.replace(day=1)}
    if quick:
        qr = tk.Frame(frm, bg=C["bg"])
        qr.pack(fill="x", pady=(0, 8))
        for i, (label, d) in enumerate(quick):
            ttk.Button(qr, text=label, command=lambda dd=d: done(dd)).grid(row=i // 3, column=i % 3, sticky="ew",
                                                                         padx=2, pady=2)
    head = tk.Frame(frm, bg=C["bg"])
    head.pack(fill="x")
    lbl = tk.Label(head, text="", bg=C["bg"], fg=C["header"], font=FONTS["h3"], width=18)
    grid = tk.Frame(frm, bg=C["bg"])

    def done(value):
        res["v"] = value
        win.destroy()

    def draw():
        for w in grid.winfo_children():
            w.destroy()
        m0 = state["month"]
        lbl.configure(text=m0.strftime("%B %Y"))
        for i, n in enumerate(("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su")):
            tk.Label(grid, text=n, bg=C["bg"], fg=C["muted"], font=FONTS["small_bold"], width=4).grid(row=0, column=i)
        start = m0 - dt.timedelta(days=m0.weekday())
        for k in range(42):
            d = start + dt.timedelta(days=k)
            sel, tod = d == initial, d == today()
            fg = C["faint"] if d.month != m0.month else (C["on_accent"] if sel else
                                                          (C["accent"] if tod else C["ink"]))
            bg = C["accent"] if sel else (C["soft"] if tod else C["panel"])
            b = tk.Label(grid, text=str(d.day), bg=bg, fg=fg, width=4, pady=4, cursor="hand2",
                         font=FONTS["small_bold"] if (sel or tod) else FONTS["small"])
            b.grid(row=1 + k // 7, column=k % 7, padx=1, pady=1)
            b.bind("<Button-1>", lambda e, dd=d: done(dd))

    def move(step):
        y, m = state["month"].year, state["month"].month + step
        y, m = (y + 1, 1) if m > 12 else ((y - 1, 12) if m < 1 else (y, m))
        state["month"] = dt.date(y, m, 1)
        draw()

    ttk.Button(head, text="◀", width=3, command=lambda: move(-1)).pack(side="left")
    lbl.pack(side="left", expand=True)
    ttk.Button(head, text="▶", width=3, command=lambda: move(1)).pack(side="right")
    grid.pack(pady=(6, 0))
    bb = tk.Frame(frm, bg=C["bg"])
    bb.pack(fill="x", pady=(8, 0))
    ttk.Button(bb, text="No date", command=lambda: done("clear")).pack(side="left")
    ttk.Button(bb, text="Cancel", command=win.destroy).pack(side="right")
    draw()
    win.bind("<Escape>", lambda e: win.destroy())
    center_on(win, parent)
    try:
        win.grab_set()
    except tk.TclError:
        pass
    parent.wait_window(win)
    return res.get("v")


def make_text(parent, height=10, **kw):
    return tk.Text(parent, height=height, wrap="word", font=FONTS["body"], relief="flat", highlightthickness=1,
                   highlightbackground=C["line"], highlightcolor=C["accent"], bg=C["field"], fg=C["ink"],
                   insertbackground=C["ink"], selectbackground=C["select"], selectforeground=C["ink"],
                   padx=12, pady=10, undo=True, **kw)


# --------------------------------------------------------------------------
# The app
# --------------------------------------------------------------------------
class POHome(tk.Tk):
    CARDS = [
        ("ws", "🧭", "Redmine", "accent", "soft"),
        ("pa", "🗂", "My PA", "accent_dark", "soft"),
        ("clients", "🤝", "Clients & Demos", "good", "sage_soft"),
        ("library", "🗃", "Decks & Docs", "sand_ink", "sand_soft"),
        ("legal", "⚖", "Legal & Contracts", "lilac_ink", "lilac_soft"),
        ("calendar", "🗓", "Release calendar", "blue", "blue_soft"),
        ("team", "🏖", "Team availability", "good", "sage_soft"),
        ("links", "🔗", "Quick links", "muted", "cell_hol"),
        ("templates", "📚", "Templates", "sand_ink", "sand_soft"),
        ("focus", "🌿", "Focus & breaks", "good", "sage_soft"),
    ]

    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("1440x900")
        self.minsize(1100, 700)
        self.d = self._load()
        C.update(DARK if self.d["settings"].get("theme") == "dark" else LIGHT)
        self.configure(bg=C["bg"])
        self._init_fonts()
        self._init_style()
        self.ws = Workstation(self)
        self.expand_series()
        if not self.d["links"]:
            self.d["links"] = self._default_links()
        self._queue = queue.Queue()
        self.views, self.cur_view = {}, None
        self.var_status = tk.StringVar(value="")
        self._build_shell()
        self.show("home")
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(200, self._poll)
        self.after(1500, self.tick)
        self.after(800, self._ensure_autostart)
        self.bind_all("<Control-n>", lambda e: self.quick_add_dialog())
        self.bind_all("<Control-k>", lambda e: self.quick_find())

    # ----- look & feel -------------------------------------------------------
    def _init_fonts(self):
        families = set(tkfont.families(self))
        base = tkfont.nametofont("TkDefaultFont").actual("family")
        fam = next((f for f in ("Segoe UI", "Helvetica Neue", "DejaVu Sans") if f in families), base)
        serif = next((f for f in ("Georgia", "Cambria", "DejaVu Serif") if f in families), fam)
        emoji = next((f for f in ("Segoe UI Emoji", "Apple Color Emoji", "Noto Color Emoji") if f in families), fam)
        b = 12 if IS_MAC else 10
        FONTS.update({"body": (fam, b), "small": (fam, b - 1), "small_bold": (fam, b - 1, "bold"),
                      "h1": (serif, b + 9, "bold"), "h2": (serif, b + 4, "bold"), "h3": (fam, b + 1, "bold"),
                      "hero": (serif, b + 14, "bold"), "big": (serif, b + 30, "bold"), "kpi": (serif, b + 12, "bold"),
                      "icon": (emoji, b + 6), "mono": ("Consolas" if IS_WINDOWS else "DejaVu Sans Mono", b)})
        for named in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
            try:
                tkfont.nametofont(named).configure(family=fam, size=b)
            except tk.TclError:
                pass

    def _init_style(self):
        st = ttk.Style(self)
        try:
            st.theme_use("clam")
        except tk.TclError:
            pass
        st.configure(".", background=C["bg"], foreground=C["ink"], font=FONTS["body"], fieldbackground=C["field"],
                     insertcolor=C["ink"], selectbackground=C["select"], selectforeground=C["ink"])
        for name in ("Bg.TFrame", "TFrame"):
            st.configure(name, background=C["bg"])
        st.configure("TLabel", background=C["bg"], foreground=C["ink"])
        st.configure("Muted.TLabel", background=C["bg"], foreground=C["muted"], font=FONTS["small"])
        st.configure("H1.TLabel", background=C["bg"], foreground=C["header"], font=FONTS["h1"])
        st.configure("H2.TLabel", background=C["bg"], foreground=C["header"], font=FONTS["h2"])
        st.configure("TLabelframe", background=C["bg"], bordercolor=C["line"], lightcolor=C["line"],
                     darkcolor=C["line"], relief="solid", borderwidth=1)
        st.configure("TLabelframe.Label", background=C["bg"], foreground=C["header"], font=FONTS["h3"])
        st.configure("TButton", padding=(12, 6), relief="flat", borderwidth=1, background=C["field"],
                     foreground=C["ink"], bordercolor=C["line"], lightcolor=C["field"], darkcolor=C["field"])
        st.map("TButton", background=[("active", C["btn_hover"]), ("pressed", C["btn_press"])],
               foreground=[("disabled", C["faint"])])
        st.configure("Accent.TButton", background=C["accent"], foreground=C["on_accent"], bordercolor=C["accent"],
                     lightcolor=C["accent"], darkcolor=C["accent"], padding=(14, 6), font=FONTS["small_bold"])
        st.map("Accent.TButton", background=[("active", C["accent_dark"]), ("pressed", C["accent_dark"])])
        st.configure("TEntry", fieldbackground=C["field"], foreground=C["ink"], bordercolor=C["line"],
                     lightcolor=C["line"], darkcolor=C["line"], padding=5, insertcolor=C["ink"])
        st.configure("Capture.TEntry", fieldbackground=C["field"], foreground=C["ink"], bordercolor=C["soft_line"],
                     lightcolor=C["soft_line"], darkcolor=C["soft_line"], padding=9, insertcolor=C["ink"])
        st.configure("TCombobox", fieldbackground=C["field"], background=C["field"], foreground=C["ink"],
                     bordercolor=C["line"], lightcolor=C["line"], darkcolor=C["line"], arrowsize=14, padding=3,
                     arrowcolor=C["muted"])
        st.map("TCombobox", fieldbackground=[("readonly", C["field"])], foreground=[("readonly", C["ink"])],
               selectbackground=[("readonly", C["field"])], selectforeground=[("readonly", C["ink"])])
        self.option_add("*TCombobox*Listbox.background", C["field"])
        self.option_add("*TCombobox*Listbox.foreground", C["ink"])
        self.option_add("*TCombobox*Listbox.selectBackground", C["select"])
        self.option_add("*TCombobox*Listbox.selectForeground", C["ink"])
        for name in ("TCheckbutton", "TRadiobutton"):
            st.configure(name, background=C["bg"], foreground=C["ink"], indicatorbackground=C["field"],
                         indicatorforeground=C["ink"])
            st.map(name, indicatorcolor=[("selected", C["accent"]), ("!selected", C["field"])],
                   background=[("active", C["bg"])])
        st.configure("Treeview", rowheight=30, background=C["field"], fieldbackground=C["field"], foreground=C["ink"],
                     bordercolor=C["line"], lightcolor=C["line"], darkcolor=C["line"])
        st.configure("Treeview.Heading", font=FONTS["small_bold"], background=C["head_bg"], foreground=C["header"],
                     relief="flat", bordercolor=C["line"], lightcolor=C["head_bg"], darkcolor=C["head_bg"],
                     padding=(6, 6))
        st.map("Treeview.Heading", background=[("active", C["btn_hover"])])
        st.map("Treeview", background=[("selected", C["select"])], foreground=[("selected", C["ink"])])
        st.configure("Vertical.TScrollbar", background=C["bar"], troughcolor=C["bg"], bordercolor=C["bg"],
                     arrowcolor=C["muted"], lightcolor=C["bar"], darkcolor=C["bar"])
        st.map("Vertical.TScrollbar", background=[("active", C["btn_hover"])])
        st.configure("TSpinbox", fieldbackground=C["field"], foreground=C["ink"], bordercolor=C["line"],
                     arrowcolor=C["muted"])
        st.configure("TPanedwindow", background=C["bg"])
        st.configure("Sash", sashthickness=6, gripcount=0, background=C["bg"])

    def toggle_theme(self):
        s = self.d["settings"]
        s["theme"] = "light" if s.get("theme") == "dark" else "dark"
        self.save()
        self.apply_theme()

    def apply_theme(self):
        """Rebuild every screen in the new colours."""
        if hasattr(self, "txt_notes"):
            self._store_detail()
        self._meet_sel = None
        C.update(DARK if self.d["settings"].get("theme") == "dark" else LIGHT)
        for t in list(Toast.stack):
            t.close()
        current = self.cur_view or "home"
        for w in list(self.winfo_children()):
            w.destroy()
        for k, v in list(self.__dict__.items()):
            if isinstance(v, tk.Misc) and v is not self:
                delattr(self, k)
            elif isinstance(v, dict) and v and all(isinstance(x, tk.Misc) for x in v.values()):
                delattr(self, k)
        self.views, self.cur_view = {}, None
        self.configure(bg=C["bg"])
        self._init_style()
        self._build_shell()
        self.show(current)

    # ----- data --------------------------------------------------------------
    def _load(self):
        d = load_json(DATA_PATH, {})
        d.setdefault("settings", {})
        s = d["settings"]
        for k, v in {"work_start": "10:00", "work_end": "20:00", "wrap_time": "19:30", "nudge_days": 3,
                     "autostart": False, "close_to_background": True, "your_name": "", "focus_work": 45,
                     "focus_break": 10, "demo_prep_days": 3, "workstation_path": "", "theme": "light",
                     "auto_followup": True}.items():
            s.setdefault(k, v)
        for k in ("tasks", "meetings", "clients", "contracts", "leave", "links", "templates", "library"):
            d.setdefault(k, [])
        d.setdefault("flags", {})
        if not d["templates"]:
            d["templates"] = [{"id": i + 1, "name": n, "category": c, "text": t}
                              for i, (n, c, t) in enumerate(DEFAULT_TEMPLATES)]
        backup_daily(DATA_PATH)
        return d

    def save(self):
        try:
            save_json(DATA_PATH, self.d)
        except OSError as exc:
            self.set_status(f"⚠ Could not save: {exc}")

    def people(self) -> list:
        names = [m["name"] for m in self.ws.team()]
        for c in self.d["clients"]:
            names += [x.strip() for x in re.split(r"[,;]", c.get("contacts", "")) if x.strip()]
        return sorted(set(names), key=str.lower)

    def set_status(self, text):
        self.var_status.set(text)

    # ----- shell ---------------------------------------------------------------
    def _bar_button(self, bar, text, cmd, last=False):
        b = tk.Label(bar, text=text, bg=C["soft"], fg=C["ink"], padx=14, pady=5, font=FONTS["small_bold"],
                     cursor="hand2")
        b.pack(side="right", padx=(8, 18) if last else (8, 0))
        b.bind("<Button-1>", lambda e: cmd())
        b.bind("<Enter>", lambda e: b.configure(bg=C["btn_press"]))
        b.bind("<Leave>", lambda e: b.configure(bg=C["soft"]))
        return b

    def _build_shell(self):
        bar = tk.Frame(self, bg=C["panel"], highlightbackground=C["line"], highlightthickness=1)
        bar.pack(fill="x", side="top")
        home = tk.Label(bar, text="✿  PO Home", bg=C["panel"], fg=C["accent"], font=FONTS["h1"], cursor="hand2")
        home.pack(side="left", padx=(18, 12), pady=10)
        home.bind("<Button-1>", lambda e: self.show("home"))
        self.lbl_where = tk.Label(bar, text="", bg=C["panel"], fg=C["muted"], font=FONTS["body"])
        self.lbl_where.pack(side="left", pady=10)
        dark = self.d["settings"].get("theme") == "dark"
        self._bar_button(bar, "⏻  Quit", self.quit_app, last=True)
        self._bar_button(bar, "⚙  Settings", self.settings_dialog)
        self._bar_button(bar, "☀  Light" if dark else "🌙  Dark", self.toggle_theme)
        self._bar_button(bar, "🔎  Find a deck  (Ctrl+K)", self.quick_find)
        self._bar_button(bar, "✍  Quick add  (Ctrl+N)", self.quick_add_dialog)
        self._bar_button(bar, "🏠  Home", lambda: self.show("home"))
        sbar = tk.Frame(self, bg=C["bar"])
        sbar.pack(fill="x", side="bottom")
        tk.Label(sbar, textvariable=self.var_status, bg=C["bar"], fg=C["muted"], anchor="w",
                 font=FONTS["small"]).pack(side="left", fill="x", expand=True, padx=12, pady=4)
        self.body = ttk.Frame(self, style="Bg.TFrame")
        self.body.pack(fill="both", expand=True)

    def show(self, name):
        if self.cur_view == "pa" and name != "pa":
            self._leave_meetings()
        if self.cur_view and self.cur_view in self.views:
            self.views[self.cur_view].pack_forget()
        if name not in self.views:
            frame = ttk.Frame(self.body, style="Bg.TFrame", padding=(22, 14, 22, 12))
            getattr(self, f"build_{name}")(frame)
            self.views[name] = frame
        self.views[name].pack(fill="both", expand=True)
        self.cur_view = name
        titles = {k: t for k, _, t, _, _ in self.CARDS}
        self.lbl_where.configure(text="" if name == "home" else f"›  {titles.get(name, name)}")
        refresh = getattr(self, f"refresh_{name}", None)
        if refresh:
            refresh()

    def view_header(self, frame, title, subtitle, buttons=()):
        head = ttk.Frame(frame, style="Bg.TFrame")
        head.pack(fill="x", pady=(0, 10))
        left = ttk.Frame(head, style="Bg.TFrame")
        left.pack(side="left")
        ttk.Label(left, text=title, style="H1.TLabel").pack(anchor="w")
        ttk.Label(left, text=subtitle, style="Muted.TLabel").pack(anchor="w")
        for text, cmd, accent in reversed(list(buttons)):
            ttk.Button(head, text=text, command=cmd, style="Accent.TButton" if accent else "TButton").pack(
                side="right", padx=(6, 0))
        return head

    # ----- background work -------------------------------------------------------
    def run_async(self, work, done, busy=None):
        if busy:
            self.set_status(busy)

        def runner():
            try:
                self._queue.put((done, work(), None))
            except Exception as exc:
                self._queue.put((done, None, exc))

        threading.Thread(target=runner, daemon=True).start()

    def _poll(self):
        try:
            while True:
                item = self._queue.get_nowait()
                if item[0] == "SHOW":
                    self.bring_to_front()
                    continue
                done, res, exc = item
                if exc:
                    self.set_status(f"⚠ {exc}")
                else:
                    done(res)
        except queue.Empty:
            pass
        self.after(200, self._poll)

    def bring_to_front(self):
        self.deiconify()
        self.lift()
        try:
            self.attributes("-topmost", True)
            self.after(300, lambda: self.attributes("-topmost", False))
        except tk.TclError:
            pass
        self.focus_force()

    # ----- home ------------------------------------------------------------------
    CAPTURE_HINT = ("Type it the way you'd say it:  Follow up with Alex on SAP API by Friday !high   ·   "
                    "Prepare grooming every monday   ·   start with 'Meeting…' (or click 📅 Meeting) for a meeting")

    def capture_bar(self, parent, on_added=None, extra=()):
        wrap = tk.Frame(parent, bg=C["panel"], highlightbackground=C["soft_line"], highlightthickness=1)
        wrap.pack(fill="x", pady=(4, 2))
        inner = tk.Frame(wrap, bg=C["panel"])
        inner.pack(fill="x", padx=12, pady=(10, 4))
        mode = {"v": "task", "manual": False}
        seg = tk.Frame(inner, bg=C["line"])
        seg.pack(side="left")
        b_task = tk.Label(seg, text="✓ Task", padx=12, pady=6, font=FONTS["small_bold"], cursor="hand2")
        b_meet = tk.Label(seg, text="📅 Meeting", padx=12, pady=6, font=FONTS["small_bold"], cursor="hand2")
        b_task.pack(side="left", padx=(1, 0), pady=1)
        b_meet.pack(side="left", padx=1, pady=1)
        var = tk.StringVar()
        e = ttk.Entry(inner, textvariable=var, font=FONTS["h3"], style="Capture.TEntry")
        e.pack(side="left", fill="x", expand=True, padx=10)
        add_btn = ttk.Button(inner, text="Add task", style="Accent.TButton")
        preview = tk.Label(wrap, text=self.CAPTURE_HINT, bg=C["panel"], fg=C["muted"], font=FONTS["small"],
                           anchor="w", justify="left")
        preview.pack(fill="x", padx=14, pady=(0, 8))

        def paint():
            on, off = (b_task, b_meet) if mode["v"] == "task" else (b_meet, b_task)
            on.configure(bg=C["accent"], fg=C["on_accent"])
            off.configure(bg=C["panel"], fg=C["ink"])
            add_btn.configure(text="Add task" if mode["v"] == "task" else "Add meeting")

        def set_mode(v, manual=True):
            mode["v"] = v
            mode["manual"] = manual
            paint()
            describe()
            e.focus_set()

        b_task.bind("<Button-1>", lambda ev: set_mode("task"))
        b_meet.bind("<Button-1>", lambda ev: set_mode("meeting"))

        def describe(*_):
            txt = var.get().strip()
            if not txt:
                mode["manual"] = mode["manual"] and mode["v"] == "meeting"
                if not mode["manual"]:
                    mode["v"] = "task"
                    paint()
                preview.configure(text=self.CAPTURE_HINT if mode["v"] == "task" else
                                  "Type the meeting, e.g.  Acme sync tomorrow 3pm   ·   Standup every weekday 10:30am   ·   "
                                  "Review every other Friday 4pm")
                return
            t = parse_task(txt, self.people())
            if not mode["manual"]:
                auto = "meeting" if (MEETING_START.match(txt) or looks_like_meeting(txt, t)) else "task"
                if auto != mode["v"]:
                    mode["v"] = auto
                    paint()
            if mode["v"] == "meeting":
                mt = self._meeting_from_text(txt, preview=True)
                preview.configure(text=f"📅 Meeting: {mt['title']}   ·   {fmt_date(mt['date'])} "
                                       f"{mt['time'] or '(no time)'}   ·   {mt['type']}" +
                                  (f"   ·   until {fmt_date(mt['end_date'])}" if mt.get("end_date") else "") +
                                  (f"   ·   🔁 {repeat_label(mt['repeats'], mt['date'], t.get('recur_days'))}"
                                   if mt["repeats"] else "") +
                                  (f"   ·   🤝 {mt['client']}" if mt["client"] else "") +
                                  "      (Enter to add · click ✓ Task if this should be a task)")
                return
            bits = [f"✓ {t['title']}", f"📅 {fmt_date(t['due']) if t['due'] else 'no date'}" +
                    (f" {t['time']}" if t['time'] else ""), f"⚑ {t['priority']}", f"🏷 {t['type']}"]
            if t["person"]:
                bits.append(f"👤 {t['person']}")
            if t["status"] == "Waiting":
                bits.append("⏳ waiting on them")
            if t["recur"] != "None":
                bits.append(f"🔁 {t['recur']}")
            preview.configure(text="   ·   ".join(bits) + "      (Enter to add)")

        def add(_e=None):
            txt = var.get().strip()
            if not txt:
                return
            if mode["v"] == "meeting":
                mt = self._meeting_from_text(txt)
                var.set("")
                self.set_status(f"📅 Meeting added: {mt['title']} · {fmt_date(mt['date'])} {mt['time']}. "
                                f"Its notes are in My PA → 📝 Notes.")
            else:
                t = self.add_task_from_text(txt)
                var.set("")
                self.set_status(f"Added: {t['title']}" + (f" · due {fmt_date(t['due'])}" if t.get("due") else ""))
            mode["manual"] = False
            describe()
            if on_added:
                on_added()
            if self.cur_view == "home":
                self.refresh_home()

        var.trace_add("write", describe)
        e.bind("<Return>", add)
        add_btn.configure(command=add)
        add_btn.pack(side="left")
        for text, cmd in extra:
            ttk.Button(inner, text=text, command=cmd).pack(side="left", padx=(6, 0))
        paint()
        return e

    def _panel(self, parent, title, sub="", link=None):
        box = tk.Frame(parent, bg=C["panel"], highlightbackground=C["line"], highlightthickness=1)
        head = tk.Frame(box, bg=C["panel"])
        head.pack(fill="x", padx=18, pady=(14, 4))
        tk.Label(head, text=title, bg=C["panel"], fg=C["header"], font=FONTS["h2"]).pack(side="left")
        lbl = tk.Label(head, text=sub, bg=C["panel"], fg=C["muted"], font=FONTS["small"])
        lbl.pack(side="left", padx=10, pady=(4, 0))
        if link:
            ln = tk.Label(head, text=link[0], bg=C["panel"], fg=C["accent"], font=FONTS["small_bold"], cursor="hand2")
            ln.pack(side="right")
            ln.bind("<Button-1>", lambda e: link[1]())
        return box, lbl

    def build_home(self, f):
        # Hero: greeting + today at a glance
        hero = tk.Frame(f, bg=C["hero"])
        hero.pack(fill="x")
        left = tk.Frame(hero, bg=C["hero"])
        left.pack(side="left", fill="y", padx=22, pady=16)
        self.lbl_hello = tk.Label(left, text="", bg=C["hero"], fg=C["header"], font=FONTS["hero"], anchor="w")
        self.lbl_hello.pack(anchor="w")
        self.lbl_hello_sub = tk.Label(left, text="", bg=C["hero"], fg=C["muted"], font=FONTS["body"], anchor="w",
                                      justify="left", wraplength=620)
        self.lbl_hello_sub.pack(anchor="w", pady=(4, 0))
        chips = tk.Frame(hero, bg=C["hero"])
        chips.pack(side="right", padx=16, pady=14)
        self.chips = {}
        for key, label, cmd in (("today", "due today", lambda: self._open_pa("☀ My day")),
                                ("overdue", "overdue", lambda: self._open_pa("☀ My day")),
                                ("meet", "meetings today", lambda: self._open_pa("📅 Meetings")),
                                ("waiting", "waiting on others", lambda: self._open_pa("Waiting on others")),
                                ("prod", "to production", lambda: self.show("calendar"))):
            chip = tk.Frame(chips, bg=C["panel"], cursor="hand2", highlightthickness=1,
                            highlightbackground=C["line"])
            chip.pack(side="left", padx=5)
            num = tk.Label(chip, text="0", bg=C["panel"], fg=C["header"], font=FONTS["kpi"], width=4)
            num.pack(padx=12, pady=(8, 0))
            lab = tk.Label(chip, text=label, bg=C["panel"], fg=C["muted"], font=FONTS["small"])
            lab.pack(padx=12, pady=(0, 8))
            for w in (chip, num, lab):
                w.bind("<Button-1>", lambda e, c=cmd: c())
            self.chips[key] = num
        # Capture
        cap = tk.Frame(f, bg=C["bg"])
        cap.pack(fill="x", pady=(12, 0))
        self.home_entry = self.capture_bar(cap, extra=[("📝 Paste meeting notes", self.paste_notes_dialog)])
        # Main: your day + apps
        main = tk.Frame(f, bg=C["bg"])
        main.pack(fill="both", expand=True, pady=(12, 0))
        main.columnconfigure(0, weight=11, uniform="m")
        main.columnconfigure(1, weight=9, uniform="m")
        main.rowconfigure(0, weight=1)
        day, self.lbl_day_sub = self._panel(main, "Your day", "", ("Open My PA  →", lambda: self.show("pa")))
        day.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self.next_box = tk.Frame(day, bg=C["soft"])
        self.next_box.pack(fill="x", padx=18, pady=(6, 8))
        cols = tk.Frame(day, bg=C["panel"])
        cols.pack(fill="both", expand=True, padx=18, pady=(0, 14))
        cols.columnconfigure(0, weight=1, uniform="d")
        cols.columnconfigure(1, weight=1, uniform="d")
        self.day_left = tk.Frame(cols, bg=C["panel"])
        self.day_left.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        self.day_right = tk.Frame(cols, bg=C["panel"])
        self.day_right.grid(row=0, column=1, sticky="nsew")
        apps, _ = self._panel(main, "Your apps", "click to open")
        apps.grid(row=0, column=1, sticky="nsew")
        grid = tk.Frame(apps, bg=C["panel"])
        grid.pack(fill="both", expand=True, padx=14, pady=(4, 14))
        self.cards = {}
        for i, (key, icon, title, colour, soft) in enumerate(self.CARDS):
            tile = AppTile(grid, icon, title, C[colour], C[soft],
                           (lambda: self.ws.launch()) if key == "ws" else (lambda k=key: self.show(k)))
            tile.grid(row=i // 2, column=i % 2, sticky="nsew", padx=4, pady=4)
            self.cards[key] = tile
        for c in range(2):
            grid.columnconfigure(c, weight=1, uniform="ap")
        for r in range((len(self.CARDS) + 1) // 2):
            grid.rowconfigure(r, weight=1)

    def refresh_home(self):
        if not hasattr(self, "lbl_hello"):
            return
        h = dt.datetime.now().hour
        hello = "Good morning" if h < 12 else ("Good afternoon" if h < 17 else "Good evening")
        name = self.d["settings"].get("your_name") or ""
        self.lbl_hello.configure(text=f"{hello}{', ' + name if name else ''} ✿")
        t = today()
        hols = self.ws.holidays()
        sub = [t.strftime("%A, %d %B %Y")]
        if t in hols:
            sub.append(f"🎉 {hols[t]} (holiday)")
        sp = self.ws.current_sprint()
        if sp:
            sub.append(f"{sp[0]} · {sp[1]['name']} ends {short_date(sp[1]['end'])}")
        self.lbl_hello_sub.configure(text="   ·   ".join(sub))
        open_t = [x for x in self.d["tasks"] if x.get("status") != "Done"]
        overdue = sum(1 for x in open_t if parse_date(x.get("due")) and parse_date(x["due"]) < t)
        self.chips["today"].configure(text=str(sum(1 for x in open_t if parse_date(x.get("due")) == t)))
        self.chips["overdue"].configure(text=str(overdue), fg=C["bad"] if overdue else C["header"])
        self.chips["meet"].configure(text=str(sum(1 for m in self.d["meetings"] if parse_date(m.get("date")) == t)))
        self.chips["waiting"].configure(text=str(sum(1 for x in open_t if x.get("status") == "Waiting")))
        prods = [p for p in self.ws.production_dates() if p[0] >= t]
        if prods:
            wd = count_working_days(t + dt.timedelta(days=1), prods[0][0], hols)
            self.chips["prod"].configure(text=f"{wd}d")
            self.chips["prod"].master.winfo_children()[1].configure(text=f"days to 🚀 {truncate(prods[0][1], 10)}")
        else:
            self.chips["prod"].configure(text="—")
        self.refresh_cards()
        self.refresh_home_panel()

    def refresh_cards(self):
        if not hasattr(self, "cards"):
            return
        t = today()
        open_t = [x for x in self.d["tasks"] if x.get("status") != "Done"]
        due_today = sum(1 for x in open_t if parse_date(x.get("due")) == t)
        overdue = sum(1 for x in open_t if parse_date(x.get("due")) and parse_date(x["due"]) < t)
        waiting = sum(1 for x in open_t if x.get("status") == "Waiting")
        p = self.ws.peek()
        ws_bits = []
        if p["next_groom"]:
            ws_bits.append(f"{plural(p['groom_count'], 'ticket')} to groom {short_date(p['next_groom'])}")
        if p["leavers"]:
            d, n = p["leavers"][0]
            ws_bits.append(f"{n.split(' ')[0]} leaves in {(d - t).days}d")
        self.cards["ws"].set(" · ".join(ws_bits) or ("Open your Redmine tools" if p["connected"]
                                                      else "Open and connect"), len(p["follow_ups"]) or None)
        n_meet = sum(1 for m in self.d["meetings"] if parse_date(m.get("date")) == t)
        self.cards["pa"].set(f"{due_today} tasks · {plural(n_meet, 'meeting')} today · {waiting} waiting",
                             (due_today + overdue) or None, overdue > 0)
        upcoming = [m for m in self.d["meetings"] if parse_date(m.get("date")) and parse_date(m["date"]) >= t]
        demos = [m for m in upcoming if m.get("type") == "Client demo"]
        self.cards["clients"].set(f"{plural(len(self.d['clients']), 'client')} · {plural(len(demos), 'demo')} ahead",
                                  len(demos) or None)
        lib = self.d["library"]
        favs = [x for x in lib if x.get("fav")]
        self.cards["library"].set(f"{plural(len(lib), 'file')}" + (f" · ★ {truncate(favs[0]['name'], 22)}"
                                                                   if favs else " · sales decks, proposals…"))
        acts = [c for c in self.d["contracts"] if self.contract_act_by(c) and
                (self.contract_act_by(c) - t).days <= 60 and c.get("status") not in ("Expired", "Terminated")]
        self.cards["legal"].set(f"{plural(len(self.d['contracts']), 'contract')} · {len(acts)} need action soon",
                                len(acts) or None, any((self.contract_act_by(c) - t).days <= 14 for c in acts))
        self.cards["calendar"].set("Sprints, releases, holidays, demos")
        out = [lv for lv in self.d["leave"] if parse_date(lv.get("from")) and parse_date(lv.get("to"))
               and parse_date(lv["from"]) <= t + dt.timedelta(days=6) and parse_date(lv["to"]) >= t]
        self.cards["team"].set(f"{plural(len(out), 'person', 'people')} out this week")
        self.cards["links"].set(f"{plural(len(self.d['links']), 'saved link')}")
        self.cards["templates"].set(f"{plural(len(self.d['templates']), 'message')} ready to copy")
        f = self.d.get("focus") or {}
        n = f.get("sessions", 0) if f.get("date") == t.isoformat() else 0
        self.cards["focus"].set(f"{plural(n, 'focus block')} today 🌿")

    def plate_lists(self):
        """Everything that belongs on today's plate, best first."""
        t = today()
        open_t = [x for x in self.d["tasks"] if x.get("status") != "Done"]
        mine = [x for x in open_t if parse_date(x.get("due")) and parse_date(x["due"]) <= t]
        top = sorted(open_t, key=lambda x: -task_score(x))[:3]
        meetings = sorted((m for m in self.d["meetings"] if parse_date(m.get("date")) == t),
                          key=lambda m: m.get("time") or "99")
        return top, mine, meetings, self.ws.plate_items(), self.contract_alerts()

    def plate_data(self):
        return self.plate_lists()

    def _next_meeting(self, meetings):
        now = dt.datetime.now()
        for m in meetings:
            tm = parse_time(m.get("time") or "")
            if not tm:
                continue
            start = dt.datetime.combine(today(), dt.time(int(tm[:2]), int(tm[3:])))
            if start + dt.timedelta(minutes=45) >= now:
                return m, start
        return None, None

    def refresh_home_panel(self):
        if not hasattr(self, "day_left"):
            return
        for box in (self.next_box, self.day_left, self.day_right):
            for w in box.winfo_children():
                w.destroy()
        top, mine, meetings, ws_items, alerts = self.plate_data()
        t = today()
        overdue = sum(1 for x in mine if parse_date(x["due"]) < t)
        self.lbl_day_sub.configure(text=f"{plural(len(mine), 'task')} due · {overdue} overdue · "
                                        f"{plural(len(meetings), 'meeting')}")
        # Next up
        m, start = self._next_meeting(meetings)
        nb = self.next_box
        tk.Label(nb, text="NEXT UP", bg=C["soft"], fg=C["accent"], font=FONTS["small_bold"]).pack(
            side="left", padx=(14, 10), pady=12)
        if m:
            mins = int((start - dt.datetime.now()).total_seconds() // 60)
            when = "now" if mins <= 0 else (f"in {mins} min" if mins < 60 else f"in {mins // 60}h {mins % 60:02d}m")
            tk.Label(nb, text=f"{m['time']}  {truncate(m['title'], 70)}", bg=C["soft"], fg=C["header"],
                     font=FONTS["h3"]).pack(side="left")
            tk.Label(nb, text=f"  ·  {when}" + (f"  ·  {m['client']}" if m.get("client") else ""), bg=C["soft"],
                     fg=C["muted"], font=FONTS["body"]).pack(side="left")
            ttk.Button(nb, text="Open notes", command=lambda mm=m: self._open_meeting(mm)).pack(side="right",
                                                                                              padx=10, pady=6)
        else:
            tk.Label(nb, text="No more meetings today. A good time for focused work 🌿", bg=C["soft"],
                     fg=C["ink"], font=FONTS["body"]).pack(side="left")
            ttk.Button(nb, text="🎯 Start focus", command=lambda: self.show("focus")).pack(side="right", padx=10,
                                                                                          pady=6)

        def section(parent, title):
            tk.Label(parent, text=title, bg=C["panel"], fg=C["accent"], font=FONTS["small_bold"],
                     anchor="w").pack(fill="x", pady=(10, 4))

        def row(parent, text, sub="", task=None, colour=None, width=30, cmd=None, muted=False):
            fr = tk.Frame(parent, bg=C["panel"], cursor="hand2" if cmd else "")
            fr.pack(fill="x", pady=2)
            if task:
                b = tk.Label(fr, text="○", bg=C["panel"], fg=C["accent"], font=FONTS["h3"], cursor="hand2")
                b.pack(side="left")
                b.bind("<Enter>", lambda e: b.configure(text="✔"))
                b.bind("<Leave>", lambda e: b.configure(text="○"))
                b.bind("<Button-1>", lambda e, tk_=task: (self.complete_task(tk_), self.refresh_home()))
            if sub:  # the small grey label on the right goes first so the sentence can wrap around it
                tk.Label(fr, text=sub, bg=C["panel"], fg=C["muted"], font=FONTS["small"]).pack(side="right",
                                                                                            anchor="n", pady=2)
            pw = parent.winfo_width()
            wrap = max(220, (pw if pw > 50 else 380) - (110 if sub else 40))
            lb = tk.Label(fr, text=text, bg=C["panel"], font=FONTS["body"], anchor="w", justify="left",
                          wraplength=wrap, fg=C["faint"] if muted else (colour or C["ink"]))
            lb.pack(side="left", padx=(4, 0), fill="x", expand=True)
            if cmd:
                for w in (fr, lb):
                    w.bind("<Button-1>", lambda e: cmd())

        L, R = self.day_left, self.day_right
        section(L, "✨ TOP 3 FOR TODAY")
        if not top:
            row(L, "Nothing yet. Add a task above ✍")
        for x in top:
            d = parse_date(x.get("due"))
            row(L, x["title"], short_date(d) if d else "", task=x, colour=C["bad"] if d and d < t else None)
        section(L, "🔔 ALSO NEEDS YOU")
        extra = ws_items + alerts
        waiting = [x for x in self.d["tasks"] if x.get("status") == "Waiting" and x.get("waiting_since") and
                   (t - parse_date(x["waiting_since"])).days >= int(self.d["settings"].get("nudge_days", 3))]
        for x in waiting[:2]:
            extra.append(("Waiting", f"⏳ {(x.get('person') or 'Someone').split(' ')[0]}: {x['title']}", t))
        if not extra:
            row(L, "All clear 🌿")
        for kind, text, d in extra[:5]:
            row(L, text, width=46)
        section(R, "📅 TODAY'S MEETINGS")
        now_hm = dt.datetime.now().strftime("%H:%M")
        if not meetings:
            row(R, "No meetings today")
        for mt in meetings[:6]:
            past = bool(mt.get("time")) and mt["time"] < now_hm
            note = ("✓ notes" if mt.get("notes") else "add notes") if past else mt.get("type", "")
            row(R, f"{mt.get('time') or '--:--'}   {mt['title']}", note, width=30, muted=past and bool(mt.get("notes")),
                cmd=lambda mm=mt: self._open_meeting(mm))
        nxt = sorted((mt for mt in self.d["meetings"] if parse_date(mt.get("date")) and not mt.get("series_id") and
                      t < parse_date(mt["date"]) <= t + dt.timedelta(days=7)),
                     key=lambda mt: (mt["date"], mt.get("time") or ""))
        if nxt:
            section(R, "🗓 COMING UP")
            for mt in nxt[:4]:
                icon = "🎬 " if mt.get("type") == "Client demo" else ""
                row(R, f"{icon}{mt['title']}", short_date(mt["date"]), width=30,
                    cmd=lambda mm=mt: self._open_meeting(mm))

    # ----- tasks -------------------------------------------------------------------
    def add_task_from_text(self, text, extra=None):
        t = parse_task(text, self.people())
        task = {"id": new_id(self.d["tasks"]), "title": t["title"], "notes": "", "due": t["due"].isoformat()
                if t["due"] else "", "time": t["time"], "priority": t["priority"], "type": t["type"],
                "person": t["person"], "status": t["status"], "recur": t["recur"], "created": today().isoformat()}
        if t.get("recur_wd") is not None:
            task["recur_wd"] = t["recur_wd"]
        if task["status"] == "Waiting":
            task["waiting_since"] = today().isoformat()
        task.update(extra or {})
        self.d["tasks"].append(task)
        self.save()
        return task

    def _meeting_from_text(self, text, preview=False):
        t = parse_task(text, self.people())
        low = text.lower()
        client = next((c["name"] for c in self.d["clients"] if norm(c["name"]) and
                       re.search(r"\b%s\b" % re.escape(norm(c["name"])), low)), "")
        kind = "Client demo" if "demo" in low else ("Client meeting" if client else
                                                    ("Grooming" if "groom" in low else
                                                     ("1:1" if re.search(r"\b1[:-]1\b|one on one", low) else
                                                      "Internal")))
        title = re.sub(r"^\s*meeting\s*[:\-–]\s*", "", t["title"], flags=re.I) or t["title"]
        m = {"title": title[:1].upper() + title[1:], "date": (t["due"] or today()).isoformat(),
             "time": t["time"], "type": kind, "client": client, "attendees": t["person"] or "", "agenda": "",
             "notes": "", "checklist": {}}
        if t.get("end"):
            m["end_date"] = t["end"].isoformat()
        rule = TASK_TO_MEETING_REPEAT.get(t["recur"])
        if rule == "Monthly (same date)" and t["due"] is None:
            rule = None
        m["repeats"] = rule or ""
        if preview:
            return m
        m.pop("repeats")
        m["id"] = new_id(self.d["meetings"])
        self.d["meetings"].append(m)
        if rule:
            self._start_series(m, rule, True, t.get("recur_days"))
        self._meeting_tasks(m)
        self.save()
        if self.cur_view == "pa":
            self.refresh_pa()
        return m

    def complete_task(self, task):
        task["status"] = "Done"
        task["done_at"] = today().isoformat()
        if task.get("recur", "None") != "None":
            nxt = dict(task)
            nxt.update({"id": new_id(self.d["tasks"]), "status": "Open", "due": next_occurrence(task).isoformat(),
                        "reminded": False, "done_at": ""})
            self.d["tasks"].append(nxt)
        self.save()
        self.refresh_cards()

    def task_dialog(self, task=None):
        fields = [("title", "What", "entry", None), ("notes", "Notes", "text", 4), ("due", "Due date", "date", None),
                  ("time", "Remind me at", "time", None), ("priority", "Priority", "choice", PRIORITIES),
                  ("type", "Type", "choice", TASK_TYPES), ("person", "Person", "combo", self.people()),
                  ("status", "Status", "choice", STATUSES), ("recur", "Repeats", "choice", RECURRENCES)]
        shown = dict(task or {"priority": "Normal", "type": "Task", "status": "Open", "recur": "None"})
        shown["status"] = "Pending" if shown.get("status", "Open") == "Open" else shown["status"]
        vals = form_dialog(self, "Edit task" if task else "New task", fields, shown)
        if not vals or not vals.get("title"):
            return None
        if vals.get("status") == "Pending":
            vals["status"] = "Open"
        if task is None:
            task = {"id": new_id(self.d["tasks"]), "created": today().isoformat()}
            self.d["tasks"].append(task)
        if vals.get("status") == "Waiting" and task.get("status") != "Waiting":
            vals["waiting_since"] = today().isoformat()
        if vals.get("time") != task.get("time") or vals.get("due") != task.get("due"):
            vals["reminded"] = False
        if vals.get("status") == "Done" and task.get("status") != "Done":
            task.update(vals)
            task["status"] = "Open"
            self.complete_task(task)
        else:
            task.update(vals)
        self.save()
        return task

    def quick_add_dialog(self):
        txt = simpledialog.askstring("Quick add", "What do you need to remember?\n(e.g. 'Call Sam next week about "
                                                  "capacity !high')", parent=self)
        if txt and txt.strip():
            t = self.add_task_from_text(txt.strip())
            self.set_status(f"Added: {t['title']}")
            self.refresh_cards()
            self.refresh_home_panel()
            if self.cur_view == "pa":
                self.refresh_pa()

    # ----- My PA -------------------------------------------------------------------
    PA_VIEWS = ["☀ Today", "📆 Upcoming", "🗂 All", "⏳ Waiting", "📅 Meetings", "✔ Done"]
    PA_ALIASES = {"☀ My day": "☀ Today", "Next 7 days": "📆 Upcoming", "🗂 Everything": "🗂 All",
                  "All pending": "🗂 All", "Waiting on others": "⏳ Waiting", "Done (30 days)": "✔ Done",
                  "Repeating": "📅 Meetings"}
    NOTE_TODO = "🗒 To-do list: every line becomes a task"
    NOTE_NEW = "➕ New meeting…"

    def build_pa(self, f):
        self.view_header(f, "My PA", "Tick a task when it's done. Click 📅 on a task to give it any date.",
                         [("📋 Plan my day with Claude", self.pa_prompt, False),
                          ("📅 New meeting", self.pa_new_meeting, False), ("➕ New task", self.pa_new, True)])
        self.capture_bar(f, on_added=self.refresh_pa)
        body = ttk.Frame(f, style="Bg.TFrame")
        body.pack(fill="both", expand=True, pady=(10, 0))
        self._build_notes_panel(body)
        main = tk.Frame(body, bg=C["bg"])
        main.pack(side="left", fill="both", expand=True)
        # view tabs
        tabs = tk.Frame(main, bg=C["bg"])
        tabs.pack(fill="x")
        self.pa_view = tk.StringVar(value=self.PA_VIEWS[0])
        self.pa_nav = {}
        for v in self.PA_VIEWS:
            lb = tk.Label(tabs, text=v, bg=C["panel"], fg=C["ink"], font=FONTS["small_bold"], padx=14, pady=7,
                          cursor="hand2", highlightthickness=1, highlightbackground=C["line"])
            lb.pack(side="left", padx=(0, 6))
            lb.bind("<Button-1>", lambda e, vv=v: (self.pa_view.set(vv), self.refresh_pa()))
            self.pa_nav[v] = lb
        # selection / undo bar
        self.pa_bar = tk.Frame(main, bg=C["bg"])
        self.pa_bar.pack(fill="x", pady=(8, 4))
        self.lbl_pa_top = tk.Label(self.pa_bar, text="", bg=C["bg"], fg=C["muted"], font=FONTS["small"],
                                   anchor="w")
        self.lbl_pa_top.pack(side="left")
        self.pa_selbar = tk.Frame(self.pa_bar, bg=C["soft"])
        self.lbl_pa_sel = tk.Label(self.pa_selbar, text="", bg=C["soft"], fg=C["header"], font=FONTS["small_bold"])
        self.lbl_pa_sel.pack(side="left", padx=(10, 6), pady=4)
        for text, cmd, acc in (("✔ Done", self.pa_done, True), ("📅 Move date", self.pa_move, False),
                               ("⏩ +1 day", self.pa_one_day_later, False), ("✏ Edit", self.pa_edit, False),
                               ("🗑 Delete", self.pa_delete, False), ("✖", self._pa_clear_sel, False)):
            ttk.Button(self.pa_selbar, text=text, command=cmd, style="Accent.TButton" if acc else "TButton").pack(
                side="left", padx=(0, 4), pady=3)
        self.pa_undo = tk.Frame(self.pa_bar, bg=C["sage_soft"])
        self.lbl_undo = tk.Label(self.pa_undo, text="", bg=C["sage_soft"], fg=C["good"], font=FONTS["small_bold"])
        self.lbl_undo.pack(side="left", padx=(10, 6), pady=4)
        ttk.Button(self.pa_undo, text="↺ Undo", command=self._pa_undo).pack(side="left", padx=(0, 4), pady=3)
        # the list
        holder = tk.Frame(main, bg=C["panel"], highlightbackground=C["line"], highlightthickness=1)
        holder.pack(fill="both", expand=True)
        self.pa_canvas = tk.Canvas(holder, bg=C["panel"], highlightthickness=0, bd=0)
        sb = ttk.Scrollbar(holder, orient="vertical", command=self.pa_canvas.yview)
        self.pa_canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.pa_canvas.pack(side="left", fill="both", expand=True)
        self.pa_list = tk.Frame(self.pa_canvas, bg=C["panel"])
        win = self.pa_canvas.create_window((0, 0), window=self.pa_list, anchor="nw")
        self.pa_canvas.bind("<Configure>", lambda e: self.pa_canvas.itemconfigure(win, width=e.width))
        self.pa_list.bind("<Configure>", lambda e: self.pa_canvas.configure(scrollregion=self.pa_canvas.bbox("all")))
        self.bind_all("<MouseWheel>", self._pa_wheel, add="+")
        self.bind_all("<Button-4>", lambda e: self._pa_wheel(e, -1), add="+")
        self.bind_all("<Button-5>", lambda e: self._pa_wheel(e, 1), add="+")
        self._pa_sel, self._pa_rows, self._pa_last_done = set(), {}, []

    def _pa_wheel(self, e, step=None):
        if self.cur_view != "pa" or not hasattr(self, "pa_canvas"):
            return
        try:
            w = self.winfo_containing(e.x_root, e.y_root)
        except (KeyError, tk.TclError):
            return
        if w is None or not str(w).startswith(str(self.pa_canvas)):
            return
        self.pa_canvas.yview_scroll(step * 3 if step else int(-e.delta / 120) * 3 or (-1 if e.delta > 0 else 1),
                                    "units")

    # ----- rows ---------------------------------------------------------------------------
    def _chip(self, parent, text, fg, bg, cmd=None, bold=False):
        lb = tk.Label(parent, text=text, bg=bg, fg=fg, font=FONTS["small_bold"] if bold else FONTS["small"],
                      padx=7, pady=1, cursor="hand2" if cmd else "")
        lb.pack(side="left", padx=(0, 6))
        if cmd:
            lb.bind("<Button-1>", lambda e: cmd())
        return lb

    def _source_chip(self, x):
        if x.get("source") == "Workstation":
            return "🧭 Workstation", C["accent_dark"], C["soft"]
        if x.get("source") == "Contract":
            return "⚖ Contract", C["lilac_ink"], C["lilac_soft"]
        lab = self._source_label(x)
        if lab:
            return lab, C["blue"], C["blue_soft"]
        return "", "", ""

    def _group(self, title, count, colour=None):
        g = tk.Frame(self.pa_list, bg=C["panel"])
        g.pack(fill="x", padx=14, pady=(14, 2))
        tk.Label(g, text=title, bg=C["panel"], fg=colour or C["accent"], font=FONTS["small_bold"]).pack(side="left")
        tk.Label(g, text=f"  {count}", bg=C["panel"], fg=C["muted"], font=FONTS["small"]).pack(side="left")
        tk.Frame(self.pa_list, bg=C["line"], height=1).pack(fill="x", padx=14)

    def _row_frame(self, key):
        sel = key in self._pa_sel
        row = tk.Frame(self.pa_list, bg=C["select"] if sel else C["panel"], cursor="hand2")
        row.pack(fill="x", padx=8, pady=0)
        self._pa_rows[key] = row
        return row

    def _bind_row(self, key, widgets, on_double):
        for w in widgets:
            w.bind("<Button-1>", lambda e, k=key: self._pa_click(k))
            w.bind("<Control-Button-1>" if not IS_MAC else "<Command-Button-1>",
                   lambda e, k=key: self._pa_click(k, toggle=True))
            w.bind("<Double-1>", lambda e: on_double())
            w.bind("<Button-3>", lambda e, k=key: self._pa_menu(e, k))

    def _task_card(self, x):
        key = ("t", x["id"])
        row = self._row_frame(key)
        bg = row["bg"]
        t = today()
        done = x.get("status") == "Done"
        d = parse_date(x.get("due"))
        overdue = bool(d and d < t and not done)
        box = tk.Label(row, text="☑" if done else "☐", bg=bg, fg=C["good"] if done else C["accent"],
                       font=(FONTS["icon"][0], 18), cursor="hand2", padx=8)
        box.pack(side="left", anchor="n", pady=4)
        box.bind("<Button-1>", lambda e: self._pa_toggle(x))
        mid = tk.Frame(row, bg=bg)
        mid.pack(side="left", fill="x", expand=True, pady=6)
        f = tkfont.Font(font=FONTS["body"])
        if done:
            f.configure(overstrike=1)
        elif x.get("priority") == "High":
            f.configure(weight="bold")
        title = tk.Label(mid, text=x["title"] + (" 🔁" if x.get("recur", "None") != "None" else ""), bg=bg,
                         fg=C["faint"] if done else (C["bad"] if overdue else C["ink"]), font=f, anchor="w",
                         justify="left", wraplength=max(300, self.pa_canvas.winfo_width() - 330))
        title.pack(fill="x")
        title._font = f
        chips = tk.Frame(mid, bg=bg)
        chips.pack(fill="x", pady=(2, 0))
        if done:
            self._chip(chips, f"✔ done {short_date(x.get('done_at'))}", C["good"], C["sage_soft"])
        if x.get("priority") == "High" and not done:
            self._chip(chips, "⚑ High", C["bad"], C["soft"], bold=True)
        if x.get("person"):
            self._chip(chips, f"👤 {x['person']}", C["ink"], C["cell_hol"])
        if x.get("status") == "Waiting" and x.get("waiting_since"):
            days = (t - parse_date(x["waiting_since"])).days
            self._chip(chips, f"⏳ waiting {days} d", C["amber"], C["sand_soft"])
        st, sfg, sbg = self._source_chip(x)
        if st:
            self._chip(chips, st, sfg, sbg)
        right = tk.Frame(row, bg=bg)
        right.pack(side="right", padx=(6, 10), anchor="n", pady=6)
        due_txt = (f"📅 {short_date(d)}" + (f" {x['time']}" if x.get("time") else "")) if d else "📅 Set date"
        dl = tk.Label(right, text=due_txt, bg=C["soft"] if overdue else C["cell_hol"],
                      fg=C["bad"] if overdue else (C["ink"] if d else C["muted"]),
                      font=FONTS["small_bold"] if overdue else FONTS["small"], padx=8, pady=2, cursor="hand2")
        dl.pack(side="left", padx=(0, 6))
        dl.bind("<Button-1>", lambda e: self._pa_pick_date(x))
        for icon, cmd in (("✏", lambda: self._pa_edit_task(x)), ("🗑", lambda: self._pa_delete_one(("t", x["id"])))):
            b = tk.Label(right, text=icon, bg=bg, fg=C["muted"], font=FONTS["h3"], cursor="hand2", padx=4)
            b.pack(side="left")
            b.bind("<Button-1>", lambda e, c=cmd: c())
        self._bind_row(key, [row, mid, title, chips], lambda: self._pa_edit_task(x))
        tk.Frame(self.pa_list, bg=C["line"], height=1).pack(fill="x", padx=50)

    def _meeting_card(self, m, label_when=None, repeat_text=""):
        key = ("m", m["id"])
        row = self._row_frame(key)
        bg = row["bg"]
        d = parse_date(m.get("date"))
        e = parse_date(m.get("end_date"))
        icon = {"Client demo": "🎬", "Client meeting": "🤝", "Grooming": "🧹", "1:1": "☕"}.get(m.get("type"), "📅")
        tk.Label(row, text=icon, bg=bg, font=(FONTS["icon"][0], 16), padx=10).pack(side="left", anchor="n", pady=4)
        mid = tk.Frame(row, bg=bg)
        mid.pack(side="left", fill="x", expand=True, pady=6)
        title = tk.Label(mid, text=m["title"] + (" 🔁" if m.get("series_id") else ""), bg=bg, fg=C["blue"],
                         font=FONTS["h3"], anchor="w")
        title.pack(fill="x")
        chips = tk.Frame(mid, bg=bg)
        chips.pack(fill="x", pady=(2, 0))
        if repeat_text:
            self._chip(chips, f"🔁 {repeat_text}", C["blue"], C["blue_soft"])
        if m.get("client"):
            self._chip(chips, f"🤝 {m['client']}", C["good"], C["sage_soft"])
        past = d and (d < today() or (d == today() and m.get("time") and
                                      m["time"] < dt.datetime.now().strftime("%H:%M")))
        if past:
            self._chip(chips, "📝 notes ✓" if (m.get("notes") or "").strip() else "📝 add notes",
                       C["good"] if m.get("notes") else C["amber"], C["sage_soft"] if m.get("notes") else C["sand_soft"])
        tc = self._task_count(m=m)
        if tc:
            self._chip(chips, f"✓ {tc}", C["ink"], C["cell_hol"])
        right = tk.Frame(row, bg=bg)
        right.pack(side="right", padx=(6, 10), anchor="n", pady=6)
        when = label_when or ((f"{d.strftime('%a %d')} → {e.strftime('%a %d-%b')}" if d and e else short_date(d))
                              + (f"  {m['time']}" if m.get("time") else ""))
        tk.Label(right, text=when, bg=C["blue_soft"], fg=C["blue"], font=FONTS["small_bold"], padx=8, pady=2).pack(
            side="left", padx=(0, 6))
        for icon_, cmd in (("📝", lambda: self._select_meeting(m["id"])), ("✏", lambda: self._pa_edit_meeting(m)),
                           ("🗑", lambda: self._pa_delete_one(("m", m["id"])))):
            b = tk.Label(right, text=icon_, bg=bg, fg=C["muted"], font=FONTS["h3"], cursor="hand2", padx=4)
            b.pack(side="left")
            b.bind("<Button-1>", lambda e_, c=cmd: c())
        self._bind_row(key, [row, mid, title, chips], lambda: self._pa_edit_meeting(m))
        tk.Frame(self.pa_list, bg=C["line"], height=1).pack(fill="x", padx=50)

    # ----- interactions ----------------------------------------------------------------------
    def _pa_click(self, key, toggle=False):
        if toggle:
            self._pa_sel ^= {key}
        else:
            self._pa_sel = {key}
        for k, row in self._pa_rows.items():
            if row.winfo_exists():
                self._paint_row(row, k in self._pa_sel)
        if key[0] == "m" and not toggle:
            self._set_note_target(("m", key[1]))
        self._pa_selbar_update()

    def _paint_row(self, row, on):
        bg = C["select"] if on else C["panel"]

        def walk(w):
            try:
                if w.cget("bg") in (C["panel"], C["select"]):
                    w.configure(bg=bg)
            except tk.TclError:
                pass
            for c in w.winfo_children():
                walk(c)

        walk(row)

    def _pa_selbar_update(self):
        n = len(self._pa_sel)
        if n:
            self.lbl_pa_sel.configure(text=f"{plural(n, 'item')} selected")
            self.pa_selbar.pack(side="right")
        else:
            self.pa_selbar.pack_forget()

    def _pa_clear_sel(self):
        self._pa_sel = set()
        for k, row in self._pa_rows.items():
            if row.winfo_exists():
                self._paint_row(row, False)
        self._pa_selbar_update()

    def _pa_toggle(self, x):
        """Tick = done, untick = pending again."""
        if x.get("status") == "Done":
            x["status"], x["done_at"] = "Open", ""
            self.save()
            self.set_status(f"'{truncate(x['title'], 50)}' is pending again.")
            self.pa_undo.pack_forget()
        else:
            before = len(self.d["tasks"])
            self.complete_task(x)
            created = self.d["tasks"][before:]
            self._pa_last_done = [(x, created)]
            self.lbl_undo.configure(text=f"✔ Done: {truncate(x['title'], 40)}")
            self.pa_undo.pack(side="right", padx=(0, 6))
            self.after(12000, lambda: self.pa_undo.winfo_exists() and self.pa_undo.pack_forget())
        self.refresh_pa()
        self.refresh_cards()

    def _pa_undo(self):
        for x, created in self._pa_last_done:
            x["status"], x["done_at"] = "Open", ""
            ids = {c["id"] for c in created}
            self.d["tasks"] = [t for t in self.d["tasks"] if t["id"] not in ids]
        self._pa_last_done = []
        self.save()
        self.pa_undo.pack_forget()
        self.refresh_pa()

    def _pa_pick_date(self, x):
        d = pick_date(self, parse_date(x.get("due")) or today(), title="When should this be done?",
                      quick=self._quick_dates())
        if d is None:
            return
        x["due"] = "" if d == "clear" else d.isoformat()
        x["reminded"] = False
        self.save()
        self.refresh_pa()
        self.set_status(f"'{truncate(x['title'], 40)}' → {fmt_date(x['due']) if x['due'] else 'no date'}")

    def _pa_edit_task(self, x):
        if self.task_dialog(x):
            self.refresh_pa()

    def _pa_edit_meeting(self, m):
        if self.meeting_dialog(m):
            self.refresh_pa()
            if self._detail == ("m", m["id"]):
                self._detail = None
                self._set_note_target(("m", m["id"]))

    def _pa_delete_one(self, key):
        self._pa_sel = {key}
        self.pa_delete()

    def _sync_auto_tasks(self):
        """Workstation and contract reminders become normal tasks (once each), labelled with where they came from."""
        known = set(self.d["flags"].get("auto_keys") or [])
        added = 0
        for kind, text, d in self.ws.plate_items() + self.contract_alerts():
            core = re.sub(r"\s*\((?:[^)]*\d[^)]*)\)", "", text)
            k = norm(re.sub(r"\b\d+\s+(?:days?|working days?|ticket follow-ups?|ticket follow-up)\b", "#", core))
            k = f"{kind}|{k}|{d.isoformat() if d else ''}" if kind != "Redmine" or "follow-up" not in text \
                else f"{kind}|follow-ups|{today().isoformat()}"
            if k in known:
                continue
            known.add(k)
            src = "Contract" if kind == "Contract" else "Workstation"
            self.d["tasks"].append({"id": new_id(self.d["tasks"]), "title": core.lstrip("⚖🚀 ").strip(),
                                    "notes": f"Added automatically from the {src.lower()} reminders.",
                                    "due": (d or today()).isoformat(), "time": "", "priority":
                                    "High" if kind in ("Release", "Contract") else "Normal",
                                    "type": "Legal" if src == "Contract" else "Redmine", "person": "",
                                    "status": "Open", "recur": "None", "created": today().isoformat(),
                                    "source": src, "auto_key": k})
            added += 1
        if added:
            self.d["flags"]["auto_keys"] = sorted(known)[-500:]
            self.save()

    # ----- list rendering ----------------------------------------------------------------------
    def refresh_pa(self):
        if not hasattr(self, "pa_list"):
            return
        self._sync_auto_tasks()
        view = self.PA_ALIASES.get(self.pa_view.get(), self.pa_view.get())
        if view not in self.PA_VIEWS:
            view = self.PA_VIEWS[0]
        self.pa_view.set(view)
        for w in self.pa_list.winfo_children():
            w.destroy()
        self._pa_rows = {}
        t = today()
        tasks = self.d["tasks"]
        open_t = [x for x in tasks if x.get("status") != "Done"]
        key = lambda x: (parse_date(x.get("due")) or dt.date(9999, 1, 1), x.get("time") or "99", -task_score(x))
        shown = 0

        def tasks_block(title, items, colour=None):
            nonlocal shown
            if items:
                self._group(title, len(items), colour)
                for x in items:
                    self._task_card(x)
                shown += len(items)

        def meetings_block(title, ms):
            nonlocal shown
            if ms:
                self._group(title, len(ms), C["blue"])
                for m in ms:
                    self._meeting_card(m)
                shown += len(ms)

        if view == "☀ Today":
            meetings_block("📅 MEETINGS TODAY", self._meetings_between(t, t))
            tasks_block("⚠ OVERDUE", sorted([x for x in open_t if parse_date(x.get("due")) and
                                             parse_date(x["due"]) < t], key=key), C["bad"])
            tasks_block("☀ TODAY", sorted([x for x in open_t if parse_date(x.get("due")) == t], key=key))
            tasks_block("⏳ WAITING ON OTHERS: TIME TO FOLLOW UP", sorted(
                [x for x in open_t if x.get("status") == "Waiting" and
                 not (parse_date(x.get("due")) and parse_date(x["due"]) <= t) and x.get("waiting_since") and
                 (t - parse_date(x["waiting_since"])).days >= int(self.d["settings"].get("nudge_days", 3))],
                key=key), C["amber"])
            tasks_block("✔ DONE TODAY", [x for x in tasks if x.get("status") == "Done" and
                                         x.get("done_at") == t.isoformat()], C["good"])
        elif view == "📆 Upcoming":
            for i in range(1, 15):
                d = t + dt.timedelta(days=i)
                ms = self._one_offs(d, d)
                ts = sorted([x for x in open_t if parse_date(x.get("due")) == d], key=key)
                if ms or ts:
                    self._group(("TOMORROW · " if i == 1 else "") + d.strftime("%A %d %B").upper(), len(ms) + len(ts))
                    for m in ms:
                        self._meeting_card(m)
                    for x in ts:
                        self._task_card(x)
                    shown += len(ms) + len(ts)
            tasks_block("🔭 LATER", sorted([x for x in open_t if parse_date(x.get("due")) and
                                            parse_date(x["due"]) > t + dt.timedelta(days=14)], key=key))
            tasks_block("🗒 NO DATE YET", sorted([x for x in open_t if not x.get("due")], key=key), C["muted"])
        elif view == "🗂 All":
            hols = self.ws.holidays()
            nxt = next_working_day(t + dt.timedelta(days=1), hols)
            week_end = t + dt.timedelta(days=6 - t.weekday())
            pend = [x for x in open_t if x.get("status") != "Waiting"]
            for title, a, b, col in (("⚠ OVERDUE", None, t - dt.timedelta(days=1), C["bad"]), ("☀ TODAY", t, t, None),
                                     (f"🌅 {nxt.strftime('%A').upper()}", t + dt.timedelta(days=1), nxt, None),
                                     ("🗓 REST OF THIS WEEK", nxt + dt.timedelta(days=1), week_end, None),
                                     ("📆 LATER", max(week_end, nxt) + dt.timedelta(days=1), None, None)):
                tasks_block(title, sorted([x for x in pend if parse_date(x.get("due")) and
                                           (a is None or parse_date(x["due"]) >= a) and
                                           (b is None or parse_date(x["due"]) <= b)], key=key), col)
            tasks_block("🗒 NO DATE", sorted([x for x in pend if not x.get("due")], key=key), C["muted"])
            tasks_block("⏳ WAITING ON OTHERS", sorted([x for x in open_t if x.get("status") == "Waiting"], key=key),
                        C["amber"])
        elif view == "⏳ Waiting":
            tasks_block("⏳ WAITING ON OTHERS", sorted([x for x in open_t if x.get("status") == "Waiting"], key=key),
                        C["amber"])
        elif view == "📅 Meetings":
            meetings_block("☀ TODAY", self._meetings_between(t, t))
            reps = self._series_current()
            if reps:
                self._group("🔁 REPEATING MEETINGS", len(reps), C["blue"])
                for sr, m in reps:
                    nxt = next((x for x in self._meetings_between(t, t + dt.timedelta(days=120))
                                if x.get("series_id") == sr["id"]), m)
                    self._meeting_card(m, label_when=f"next {short_date(nxt['date'])}" +
                                       (f"  {m['time']}" if m.get("time") else ""),
                                       repeat_text=repeat_label(sr["rule"], sr["start"], sr.get("days")))
                shown += len(reps)
            meetings_block("🗓 COMING UP", self._one_offs(t + dt.timedelta(days=1), t + dt.timedelta(days=365)))
            meetings_block("🕘 PAST 30 DAYS", [m for m in reversed(self._meetings_between(t - dt.timedelta(days=30),
                                                                                         t - dt.timedelta(days=1)))
                                              if not m.get("series_id") or (m.get("notes") or "").strip()])
        else:  # Done
            done = sorted([x for x in tasks if x.get("status") == "Done" and parse_date(x.get("done_at"))],
                          key=lambda x: x["done_at"], reverse=True)
            mon = t - dt.timedelta(days=t.weekday())
            for title, a, b in (("✔ TODAY", t, t), ("✔ YESTERDAY", t - dt.timedelta(days=1), t - dt.timedelta(days=1)),
                                ("✔ EARLIER THIS WEEK", mon, t - dt.timedelta(days=2)),
                                ("✔ LAST WEEK", mon - dt.timedelta(days=7), mon - dt.timedelta(days=1)),
                                ("✔ EARLIER", t - dt.timedelta(days=90), mon - dt.timedelta(days=8))):
                if a > b:
                    continue
                tasks_block(title, [x for x in done if a <= parse_date(x["done_at"]) <= b], C["good"])
        if not shown:
            tk.Label(self.pa_list, text={"✔ Done": "Nothing ticked off yet. Tick ☐ next to a task when it's done.",
                                         "☀ Today": "Nothing due today. 🌿 Add a task above, or look at 📆 Upcoming."}
                     .get(view, "Nothing here."), bg=C["panel"], fg=C["muted"], font=FONTS["h3"]).pack(pady=40)
        self._pa_sel = {k for k in self._pa_sel if k in self._pa_rows}
        self._pa_selbar_update()
        # tabs + counts
        counts = {"☀ Today": sum(1 for x in open_t if parse_date(x.get("due")) and parse_date(x["due"]) <= t) +
                  len(self._meetings_between(t, t)),
                  "📆 Upcoming": sum(1 for x in open_t if parse_date(x.get("due")) and
                                    t < parse_date(x["due"]) <= t + dt.timedelta(days=14)),
                  "🗂 All": len(open_t), "⏳ Waiting": sum(1 for x in open_t if x.get("status") == "Waiting"),
                  "📅 Meetings": len(self._meetings_between(t, t)) + len(self.d.get("series", [])),
                  "✔ Done": sum(1 for x in tasks if x.get("status") == "Done")}
        for v, lb in self.pa_nav.items():
            on = v == view
            lb.configure(text=f"{v}  {counts.get(v, '')}", bg=C["accent"] if on else C["panel"],
                         fg=C["on_accent"] if on else C["ink"])
        top = sorted(open_t, key=lambda x: -task_score(x))[:3]
        self.lbl_pa_top.configure(text=("✨ Top 3: " + "   ·   ".join(truncate(x["title"], 34) for x in top))
                                  if top and view != "✔ Done" else "")
        self.pa_canvas.yview_moveto(0)
        if hasattr(self, "cb_note"):
            self._fill_note_choices()

    # ----- actions on selected rows ---------------------------------------------------------
    def _sel_tasks(self):
        ids = {k[1] for k in self._pa_sel if k[0] == "t"}
        return [x for x in self.d["tasks"] if x["id"] in ids]

    def _sel_meetings(self):
        ids = {k[1] for k in self._pa_sel if k[0] == "m"}
        return [m for m in self.d["meetings"] if m["id"] in ids]

    def _need_selection(self):
        messagebox.showinfo(APP_NAME, "First click a task (Ctrl+click to pick several).", parent=self)

    def _pa_menu(self, event, key):
        if key not in self._pa_sel:
            self._pa_click(key)
        menu = tk.Menu(self, tearoff=0)
        if self._sel_tasks():
            menu.add_command(label="✔  Done", command=self.pa_done)
            menu.add_command(label="↺  Pending (not done yet)", command=self.pa_pending)
        mv = tk.Menu(menu, tearoff=0)
        for label, d in self._quick_dates():
            mv.add_command(label=f"{label}   ({fmt_date(d, day=False)})", command=lambda dd=d: self._move_to(dd))
        mv.add_separator()
        mv.add_command(label="Pick a date…", command=self.pa_move)
        mv.add_command(label="No date", command=lambda: self._move_to(None))
        menu.add_cascade(label="📅  Move to", menu=mv)
        menu.add_command(label="⏩  One day later (only this one)", command=self.pa_one_day_later)
        menu.add_command(label="✏  Edit…", command=self.pa_edit)
        if self._sel_tasks():
            menu.add_command(label="✉  Copy a nudge message", command=self.pa_nudge)
        if self._sel_meetings():
            menu.add_command(label="📝  Open notes", command=lambda: self._select_meeting(self._sel_meetings()[0]["id"]))
        menu.add_separator()
        menu.add_command(label="🗑  Delete", command=self.pa_delete)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _select_meeting(self, mid):
        self._pa_sel = {("m", mid)}
        if ("m", mid) not in self._pa_rows:
            self.pa_view.set("📅 Meetings")
            self.refresh_pa()
        else:
            self._pa_click(("m", mid))
        self._set_note_target(("m", mid))

    def pa_show_detail(self):
        pass

    # ----- notes panel (right) -------------------------------------------------------
    def _build_notes_panel(self, body):
        p = self.pa_detail = tk.Frame(body, bg=C["panel"], highlightbackground=C["line"], highlightthickness=1,
                                      width=400)
        p.pack(side="right", fill="y", padx=(12, 0))
        p.pack_propagate(False)
        tk.Label(p, text="📝 Notes", bg=C["panel"], fg=C["header"], font=FONTS["h2"]).pack(anchor="w", padx=14,
                                                                                         pady=(12, 2))
        tk.Label(p, text="1. Pick the meeting   2. Type or paste notes   3. Click 'Add tasks from notes'",
                 bg=C["panel"], fg=C["muted"], font=FONTS["small"], anchor="w", justify="left",
                 wraplength=370).pack(fill="x", padx=14)
        self.var_note_target = tk.StringVar()
        self.cb_note = ttk.Combobox(p, textvariable=self.var_note_target, state="readonly", font=FONTS["body"])
        self.cb_note.pack(fill="x", padx=14, pady=(8, 2))
        self.cb_note.bind("<<ComboboxSelected>>", lambda e: self._note_target_chosen())
        self.lbl_det_sub = tk.Label(p, text="", bg=C["panel"], fg=C["muted"], font=FONTS["small"], anchor="w",
                                    justify="left", wraplength=370)
        self.lbl_det_sub.pack(fill="x", padx=14, pady=(0, 2))
        self.lbl_from = tk.Label(p, text="", bg=C["panel"], fg=C["ink"], font=FONTS["small"], anchor="w",
                                 justify="left", wraplength=370)
        self.lbl_from.pack(fill="x", padx=14, pady=(0, 6))
        bb = tk.Frame(p, bg=C["panel"])
        bb.pack(fill="x", padx=14, side="bottom", pady=(6, 12))
        r1 = tk.Frame(bb, bg=C["panel"])
        r1.pack(fill="x")
        r2 = tk.Frame(bb, bg=C["panel"])
        r2.pack(fill="x", pady=(6, 0))
        ttk.Button(r1, text="✅ Add tasks from notes", style="Accent.TButton",
                   command=self.notes_find_tasks).pack(side="left")
        ttk.Button(r1, text="✨ Find with Claude", command=self.claude_actions).pack(side="left", padx=6)
        self.btn_email = ttk.Button(r2, text="✉ Follow-up email", command=self.meet_email)
        self.btn_email.pack(side="left")
        self.btn_edit_meet = ttk.Button(r2, text="✏ Edit meeting", command=self._edit_note_meeting)
        self.btn_edit_meet.pack(side="left", padx=6)
        self.lbl_det_hint = tk.Label(p, text="Lines with a date (e.g. 'Acme proposal by 25 Oct') become tasks on "
                                             "that date. Notes save by themselves.", bg=C["panel"], fg=C["muted"],
                                     font=FONTS["small"], anchor="w", justify="left", wraplength=370)
        self.lbl_det_hint.pack(fill="x", padx=14, side="bottom")
        self.txt_notes = make_text(p, height=10)
        self.txt_notes.pack(fill="both", expand=True, padx=14)
        self._autosave_job = None

        def typed(_e=None):
            if self._autosave_job:
                self.after_cancel(self._autosave_job)
            self._autosave_job = self.after(2000, self._store_detail)

        self.txt_notes.bind("<KeyRelease>", typed)
        self.txt_notes.bind("<<Paste>>", lambda e: self.after(400, typed))
        self._detail, self._meet_sel, self._note_map = None, None, {}
        self._fill_note_choices()
        self._set_note_target(("todo", None))

    def _meeting_label(self, m):
        d = parse_date(m.get("date"))
        rep = " 🔁" if m.get("series_id") else ""
        return f"{short_date(d) if d else ''} {m.get('time') or ''} · {m['title']}{rep}".replace("  ", " ").strip()

    def _fill_note_choices(self):
        t = today()
        ms = self._one_offs(t - dt.timedelta(days=14), t + dt.timedelta(days=30))
        ms += [cur for _sr, cur in self._series_current()]
        ms.sort(key=lambda m: (abs((parse_date(m["date"]) - t).days), m.get("time") or ""))
        self._note_map = {self.NOTE_TODO: ("todo", None)}
        labels = [self.NOTE_TODO]
        for m in ms:
            lab = self._meeting_label(m)
            while lab in self._note_map:
                lab += " "
            self._note_map[lab] = ("m", m["id"])
            labels.append(lab)
        labels.append(self.NOTE_NEW)
        self.cb_note.configure(values=labels)

    def _label_for(self, target):
        return next((k for k, v in self._note_map.items() if v == target), None)

    def _note_target_chosen(self):
        lab = self.var_note_target.get()
        if lab == self.NOTE_NEW:
            name = simpledialog.askstring("New meeting", "Meeting name, and when if you like:\n(e.g. 'Acme sync "
                                                         "tomorrow 3pm' or just 'Standup')", parent=self)
            if not name or not name.strip():
                self.var_note_target.set(self._label_for(self._detail) or self.NOTE_TODO)
                return
            m = self._meeting_from_text(name.strip())
            self.refresh_pa()
            self._set_note_target(("m", m["id"]))
            self.txt_notes.focus_set()
            return
        self._set_note_target(self._note_map.get(lab, ("todo", None)))

    def _set_note_target(self, target):
        """Switch the notes box to a meeting (or the to-do list), saving the previous one."""
        if target == self._detail:
            return
        prev = self._detail
        self._store_detail()
        if prev and prev[0] == "m":
            self.after(60, lambda pid=prev[1]: self.check_actions(pid))
        self._fill_note_choices()
        if target[0] == "m" and not self._label_for(target):
            m = next((x for x in self.d["meetings"] if x["id"] == target[1]), None)
            if m:
                lab = self._meeting_label(m)
                self._note_map[lab] = target
                self.cb_note.configure(values=list(self.cb_note.cget("values")) + [lab])
        self._detail = target
        self._meet_sel = target[1] if target[0] == "m" else None
        self.var_note_target.set(self._label_for(target) or self.NOTE_TODO)
        self.txt_notes.delete("1.0", "end")
        if target[0] == "m":
            m = self._sel_meeting()
            bits = [fmt_date(m.get("date")), m.get("time") or "", m.get("type", ""), m.get("client", "")]
            sr = self._series_of(m)
            if sr:
                bits.append(f"🔁 {repeat_label(sr['rule'], sr['start'], sr.get('days'))}")
            self.lbl_det_sub.configure(text="  ·  ".join(b for b in bits if b))
            self.txt_notes.insert("1.0", m.get("notes") or "")
            self._show_tasks_from(m)
            self.btn_email.state(["!disabled"])
            self.btn_edit_meet.state(["!disabled"])
        else:
            self.lbl_det_sub.configure(text="A scratch pad. Each line becomes a task; put the date in the line, "
                                            "e.g. 'Send SOW to Acme Friday'.")
            self.txt_notes.insert("1.0", self.d["flags"].get("todo_notes", ""))
            self.lbl_from.configure(text="")
            self.btn_email.state(["disabled"])
            self.btn_edit_meet.state(["disabled"])

    def _show_tasks_from(self, m):
        ts = self._tasks_from(m)
        if not ts:
            self.lbl_from.configure(text="No tasks from this meeting yet.", fg=C["muted"])
            return
        lines = [("✔ " if x.get("status") == "Done" else ("⏳ " if x.get("status") == "Waiting" else "○ ")) +
                 truncate(x["title"], 42) + (f"  · {short_date(x['due'])}" if x.get("due") else "") for x in ts[:6]]
        more = f"\n+ {len(ts) - 6} more" if len(ts) > 6 else ""
        self.lbl_from.configure(text=f"Tasks from this meeting ({len(ts)}):\n" + "\n".join(lines) + more,
                                fg=C["ink"])

    def _store_detail(self):
        if not getattr(self, "_detail", None) or not hasattr(self, "txt_notes"):
            return
        kind, oid = self._detail
        if kind == "m":
            self._store_notes(oid)
        else:
            txt = self.txt_notes.get("1.0", "end").strip()
            if txt != self.d["flags"].get("todo_notes", ""):
                self.d["flags"]["todo_notes"] = txt
                self.save()

    def notes_find_tasks(self):
        self._store_detail()
        if self._detail and self._detail[0] == "m":
            self.meet_actions()
            return
        text = self.d["flags"].get("todo_notes", "")
        acts = todo_lines(text, self.people())
        if not acts:
            messagebox.showinfo(APP_NAME, "Type one task per line first, e.g.\n\nSend SOW to Acme Friday\n"
                                          "Review PRD for #10240 tomorrow\nAlex to share handover doc by 28 Oct",
                                parent=self)
            return
        self.actions_preview(acts, None, on_added=self._todo_done)

    def _todo_done(self):
        self.d["flags"]["todo_notes"] = ""
        self.save()
        if self._detail and self._detail[0] == "todo":
            self.txt_notes.delete("1.0", "end")

    def _edit_note_meeting(self):
        m = self._sel_meeting()
        if m and self.meeting_dialog(m):
            self.refresh_pa()
            self._detail = None
            self._set_note_target(("m", m["id"]))

    def paste_notes_dialog(self):
        """Home page '📝 Paste meeting notes': open My PA with the notes box ready."""
        self._open_pa("☀ My day")
        t = today()
        now = dt.datetime.now().strftime("%H:%M")
        todays = [m for m in self._meetings_between(t, t) if not m.get("time") or m["time"] <= now]
        self._set_note_target(("m", todays[-1]["id"]) if todays else ("todo", None))
        self.txt_notes.focus_set()

    # ----- list rows -----------------------------------------------------------------
    def _one_offs(self, a, b):
        """Meetings in a date range, leaving out repeating ones (those are listed once, separately)."""
        return [m for m in self._meetings_between(a, b) if not m.get("series_id") or m.get("moved")]

    def _series_current(self):
        """For each repeating meeting: today's occurrence, else the latest past one, else the next one."""
        t = today()
        out = []
        for sr in self.d.get("series", []):
            inst = sorted((m for m in self.d["meetings"] if m.get("series_id") == sr["id"]),
                          key=lambda m: (m["date"], m.get("time") or ""))
            past = [m for m in inst if parse_date(m["date"]) <= t]
            cur = past[-1] if past else (inst[0] if inst else None)
            if cur:
                out.append((sr, cur))
        return out

    def _meetings_between(self, a, b):
        """Meetings that happen on any day from a to b (multi-day events count on every day they run)."""
        def hit(m):
            d = parse_date(m.get("date"))
            if not d:
                return False
            e = parse_date(m.get("end_date")) or d
            return d <= b and e >= a
        return sorted((m for m in self.d["meetings"] if hit(m)), key=lambda m: (m["date"], m.get("time") or "99"))

    def pa_new_meeting(self):
        m = self.meeting_dialog()
        if m:
            self.refresh_pa()
            self._select_meeting(m["id"])

    def _source_label(self, x):
        m = next((mm for mm in self.d["meetings"] if mm["id"] == x.get("meeting_id")), None) \
            if x.get("meeting_id") else None
        if not m:
            return ""
        d = parse_date(m.get("date"))
        return f"📅 {truncate(m['title'], 18)} {d.strftime('%d-%b') if d else ''}"

    def _tasks_from(self, m=None, sr=None):
        ids = {m["id"]} if m else {x["id"] for x in self.d["meetings"] if sr and x.get("series_id") == sr["id"]}
        return [x for x in self.d["tasks"] if x.get("meeting_id") in ids]

    def _task_count(self, m=None, sr=None):
        ts = self._tasks_from(m, sr)
        if not ts:
            return ""
        done = sum(1 for x in ts if x.get("status") == "Done")
        return f"{plural(len(ts), 'task')}" + (f" ({done} done)" if done else "")

    def _quick_dates(self):
        t = today()
        hols = self.ws.holidays()
        nxt = next_working_day(t + dt.timedelta(days=1), hols)
        mon = t + dt.timedelta(days=7 - t.weekday())
        fri = t + dt.timedelta(days=(4 - t.weekday()) % 7)
        out = [("Today", t), ("Tomorrow" if nxt == t + dt.timedelta(days=1) else "Next working day", nxt)]
        if fri not in (t, nxt):
            out.append(("This Friday", fri))
        out.append(("Next Monday", mon))
        out.append(("In a week", t + dt.timedelta(days=7)))
        return out

    def pa_new(self):
        if self.task_dialog():
            self.refresh_pa()
            self.refresh_cards()

    def pa_edit(self):
        ms = self._sel_meetings()
        if ms:
            if self.meeting_dialog(ms[0]):
                self.refresh_pa()
                if self._detail == ("m", ms[0]["id"]):
                    self._detail = None
                    self._set_note_target(("m", ms[0]["id"]))
            return
        sel = self._sel_tasks()
        if not sel:
            return self._need_selection()
        if self.task_dialog(sel[0]):
            self.refresh_pa()

    def pa_done(self):
        sel = self._sel_tasks()
        if not sel:
            return self._need_selection()
        n = 0
        for x in sel:
            if x.get("status") != "Done":
                self.complete_task(x)
                n += 1
        self.refresh_pa()
        self.set_status(f"✔ {plural(n, 'task')} done. (Changed your mind? Select it and click ↺ Pending.)")

    def pa_pending(self):
        sel = self._sel_tasks()
        if not sel:
            return self._need_selection()
        for x in sel:
            x["status"] = "Open"
            x["done_at"] = ""
            x.pop("waiting_since", None)
        self.save()
        self.refresh_pa()
        self.refresh_cards()
        self.set_status(f"{plural(len(sel), 'task')} marked as pending.")

    def pa_one_day_later(self):
        tasks, ms = self._sel_tasks(), self._sel_meetings()
        if not tasks and not ms:
            return self._need_selection()
        first = parse_date((tasks or ms)[0].get("due") or (tasks or ms)[0].get("date")) or today()
        self._move_to(next_working_day(first + dt.timedelta(days=1), self.ws.holidays()))

    def pa_move(self):
        tasks, ms = self._sel_tasks(), self._sel_meetings()
        if not tasks and not ms:
            return self._need_selection()
        first = parse_date((tasks or ms)[0].get("due") or (tasks or ms)[0].get("date"))
        d = pick_date(self, first or today(), title="Move to which day?", quick=self._quick_dates())
        if d is not None:
            self._move_to(None if d == "clear" else d)

    def _move_to(self, d):
        tasks, ms = self._sel_tasks(), self._sel_meetings()
        for x in tasks:
            x["due"] = d.isoformat() if d else ""
            x["reminded"] = False
            if x.get("status") == "Done":
                x["status"], x["done_at"] = "Open", ""
        for m in ms:
            if d:
                sr = self._series_of(m)
                if sr and m.get("date") not in (sr.get("skip_dates") or []):
                    sr.setdefault("skip_dates", []).append(m["date"])  # don't re-create it on the old day
                span = (parse_date(m.get("end_date")) - parse_date(m["date"])) if m.get("end_date") else None
                m["date"] = d.isoformat()
                if span is not None:
                    m["end_date"] = (d + span).isoformat()
                m["reminded"] = m["reminded_day"] = False
                m["moved"] = True
        self.save()
        self.refresh_pa()
        self.refresh_cards()
        what = plural(len(tasks) + len(ms), "item")
        self.set_status(f"Moved {what} to {fmt_date(d)}." if d else f"Removed the date from {what}.")

    def pa_delete(self):
        tasks, ms = self._sel_tasks(), self._sel_meetings()
        if not tasks and not ms:
            return self._need_selection()
        bits = [plural(len(tasks), "task")] if tasks else []
        if ms:
            bits.append(plural(len(ms), "meeting") + " (and its notes)")
        if not ms and not messagebox.askyesno(APP_NAME, f"Delete {' and '.join(bits)}?", parent=self):
            return
        tids, mids = {x["id"] for x in tasks}, {m["id"] for m in ms}
        if ms and not self.delete_meetings(ms):
            return
        self.d["tasks"] = [x for x in self.d["tasks"] if x["id"] not in tids]
        if self._detail and self._detail[0] == "m" and self._detail[1] in mids:
            self._detail = None
            self._set_note_target(("todo", None))
        self.save()
        self.refresh_pa()
        self.refresh_cards()
        self.set_status(f"Deleted {' and '.join(bits)}.")

    def pa_nudge(self):
        sel = self._sel_tasks()
        if not sel:
            return self._need_selection()
        x = sel[0]
        who = (x.get("person") or "there").split(" ")[0]
        msg = (f"Hi {who},\n\nJust a gentle nudge on: {x['title']}.\nCould you share an update when you get a "
               f"moment?\n\nThanks!\n{self.d['settings'].get('your_name', '')}")
        self.clipboard_clear()
        self.clipboard_append(msg)
        self.set_status("Nudge message copied. Paste it into Teams or email (Ctrl+V).")

    def pa_adopt(self):
        pass

    def pa_prompt(self):
        top, mine, meetings, ws_items, alerts = self.plate_data()
        open_t = [x for x in self.d["tasks"] if x.get("status") != "Done"]
        lines = [f"- [{x.get('priority')}] {x['title']} (due {x.get('due') or 'no date'}, {x.get('type')}"
                 + (f", with {x['person']}" if x.get("person") else "") + f", {x.get('status')})" for x in open_t[:60]]
        s = self.d["settings"]
        text = ("You are my personal assistant. I am a Product Owner. My working hours today are "
                f"{s['work_start']}–{s['work_end']}. Using my list below, suggest a realistic plan for today: the 3 "
                "most important things, a rough time plan around my meetings, what I can delegate or push, and "
                "any follow-up messages I should send. Be brief and practical.\n\n"
                f"Today: {today().strftime('%A %d %B %Y')}\n\nMeetings today:\n" +
                ("\n".join(f"- {m.get('time') or '?'} {m['title']} ({m.get('type')})" for m in meetings) or "- none") +
                "\n\nOther things needing me:\n" + ("\n".join(f"- {t}" for _, t, _ in ws_items + alerts) or "- none") +
                "\n\nMy open tasks:\n" + ("\n".join(lines) or "- none") + "\n")
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo(APP_NAME, "Your day's details are on the clipboard.\n\nPaste them into Claude (claude.ai) "
                                      "with Ctrl+V for a suggested plan.", parent=self)

    # ----- Meetings & Notes -----------------------------------------------------------
    def meeting_dialog(self, m=None, preset=None):
        clients = [c["name"] for c in self.d["clients"]]
        series = self._series_of(m)
        fields = [("title", "Meeting", "entry", None), ("date", "Date", "date", None), ("time", "Time", "time", None),
                  ("end_date", "Ends on (multi-day)", "date", None),
                  ("repeats", "Repeats", "choice", MEETING_REPEATS),
                  ("days", "Days (for 'tick below')", "days", None),
                  ("skip_hols", "Holidays", "check", "Skip public holidays (from your holiday list)"),
                  ("type", "Type", "choice", MEETING_TYPES), ("client", "Client (optional)", "combo", clients),
                  ("attendees", "Attendees", "entry", None), ("agenda", "Agenda / prep notes", "text", 4)]
        start = dict(m or dict({"date": today().isoformat(), "type": "Internal"}, **(preset or {})))
        start["repeats"] = (series or {}).get("rule") or start.get("repeats") or MEETING_REPEATS[0]
        start["skip_hols"] = (series or {}).get("skip_hols", True)
        start["days"] = (series or {}).get("days") or start.get("days") or []
        vals = form_dialog(self, "Edit meeting" if m else "New meeting", fields, start)
        if not vals or not vals.get("title") or not vals.get("date"):
            return None
        rule, skip, days = vals.pop("repeats"), vals.pop("skip_hols"), vals.pop("days")
        repeating = not rule.startswith("Does not")
        if rule.startswith("On the days") and not days:
            messagebox.showinfo(APP_NAME, "Tick the days this meeting happens on (e.g. Tue, Wed, Thu, Fri).",
                                parent=self)
            return None
        if vals.get("end_date") and (vals["end_date"] <= vals["date"] or repeating):
            vals["end_date"] = "" if vals["end_date"] <= vals["date"] else vals["end_date"]
            if repeating and vals["end_date"]:
                messagebox.showinfo(APP_NAME, "A repeating meeting can't also span several days, so 'Ends on' "
                                              "was ignored.", parent=self)
                vals["end_date"] = ""
        if m is None:
            m = {"id": new_id(self.d["meetings"]), "notes": "", "checklist": {}}
            self.d["meetings"].append(m)
        elif series:
            template = ("title", "time", "type", "client", "attendees", "agenda")
            changed = any((vals.get(k) or "") != (m.get(k) or "") for k in template)
            rule_changed = (rule != series.get("rule") or bool(skip) != bool(series.get("skip_hols", True)) or
                            sorted(days) != sorted(series.get("days") or []))
            if changed or rule_changed:
                scope = choice_dialog(self, "Repeating meeting", f"'{m['title']}' repeats "
                                      f"{repeat_label(series['rule'], series['start'], series.get('days'))}.\n"
                                      f"Apply your changes to:",
                                      ["Only this meeting", "This and all following meetings"])
                if scope is None:
                    return None
                if scope.startswith("This and"):
                    self._split_series(m, vals, rule if repeating else None, skip, days)
                    self.save()
                    return m
                if rule_changed:
                    self.set_status("The 'Repeats' change needs 'This and all following meetings', so it was "
                                    "not applied.")
            if vals.get("date") != m.get("date"):
                series.setdefault("skip_dates", []).append(m.get("date"))
        if vals.get("date") != m.get("date") or vals.get("time") != m.get("time"):
            m["reminded"] = False
            m["reminded_day"] = False
        m.update(vals)
        if repeating and not series:
            self._start_series(m, rule, skip, days)
        self._meeting_tasks(m)
        self.save()
        return m

    # ----- repeating meetings ------------------------------------------------------------
    def _series_of(self, m):
        sid = (m or {}).get("series_id")
        return next((x for x in self.d.setdefault("series", []) if x["id"] == sid), None) if sid else None

    def _start_series(self, m, rule, skip=True, days=None):
        sid = new_id(self.d.setdefault("series", []))
        if rule.startswith("On the days") and days:
            d0 = parse_date(m["date"])
            while d0.weekday() not in days:
                d0 += dt.timedelta(days=1)
            m["date"] = d0.isoformat()
        self.d["series"].append({"id": sid, "rule": rule, "start": m["date"], "skip_hols": bool(skip),
                                 "days": list(days or []),
                                 "end": "", "skip_dates": [], **{k: m.get(k, "") for k in
                                                                 ("title", "time", "type", "client", "attendees",
                                                                  "agenda")}})
        m["series_id"] = sid
        self.expand_series()

    def _split_series(self, m, vals, rule, skip, days=None):
        """'This and all following': end the old series the day before, start a new one from this meeting."""
        old = self._series_of(m)
        d0 = parse_date(m["date"])
        if old:
            if d0 <= parse_date(old["start"]):
                self.d["series"] = [x for x in self.d["series"] if x["id"] != old["id"]]
            else:
                old["end"] = (d0 - dt.timedelta(days=1)).isoformat()
            keep = []
            for x in self.d["meetings"]:
                if x is not m and x.get("series_id") == old["id"] and parse_date(x["date"]) >= d0:
                    if (x.get("notes") or "").strip():
                        x["series_id"] = None
                        x.update({k: v for k, v in vals.items() if k != "date"})
                        keep.append(x)
                    continue
                keep.append(x)
            self.d["meetings"] = keep
        m.update(vals)
        m["series_id"] = None
        m["reminded"] = m["reminded_day"] = False
        if rule:
            self._start_series(m, rule, skip, days)
        self._meeting_tasks(m)

    def expand_series(self):
        """Keep repeating meetings filled in for the next 90 days (they never end unless you stop them)."""
        t = today()
        horizon = t + dt.timedelta(days=90)
        hols = self.ws.holidays()
        changed = False
        for sr in self.d.setdefault("series", []):
            end = parse_date(sr.get("end")) or horizon
            have = {x["date"] for x in self.d["meetings"] if x.get("series_id") == sr["id"]}
            have |= set(sr.get("skip_dates") or [])
            for d in series_dates(sr["rule"], sr["start"], max(t, parse_date(sr["start"])), min(end, horizon),
                                  hols, sr.get("skip_hols", True), sr.get("days")):
                if d.isoformat() in have:
                    continue
                self.d["meetings"].append({"id": new_id(self.d["meetings"]), "date": d.isoformat(), "notes": "",
                                           "checklist": {}, "series_id": sr["id"],
                                           **{k: sr.get(k, "") for k in ("title", "time", "type", "client",
                                                                         "attendees", "agenda")}})
                changed = True
        for x in self.d["meetings"]:  # prep / follow-up tasks only once a repeat is a week away
            d = parse_date(x.get("date"))
            if x.get("series_id") and not x.get("auto_done") and d and t <= d <= t + dt.timedelta(days=7):
                self._meeting_tasks(x)
                x["auto_done"] = True
                changed = True
        if changed:
            self.save()

    def _meeting_tasks(self, m):
        d = parse_date(m.get("date"))
        if m.get("series_id") and d and d > today() + dt.timedelta(days=7):
            return
        if m.get("type") == "Client demo":
            self._ensure_demo_prep(m)
        self._ensure_followup(m)

    def delete_meetings(self, ms):
        """Delete meetings; for repeating ones ask 'only this' or 'this and all following'."""
        rep = [m for m in ms if m.get("series_id")]
        scope = "Only this meeting"
        if rep:
            scope = choice_dialog(self, "Delete repeating meeting",
                                  f"'{rep[0]['title']}' is a repeating meeting. Delete:",
                                  ["Only this meeting", "This and all following meetings"])
            if scope is None:
                return False
        elif not messagebox.askyesno(APP_NAME, f"Delete {plural(len(ms), 'meeting')} and its notes?", parent=self):
            return False
        drop = {m["id"] for m in ms}
        for m in rep:
            sr = self._series_of(m)
            if not sr:
                continue
            if scope.startswith("This and"):
                d0 = parse_date(m["date"])
                if d0 <= parse_date(sr["start"]):
                    self.d["series"] = [x for x in self.d["series"] if x["id"] != sr["id"]]
                else:
                    sr["end"] = (d0 - dt.timedelta(days=1)).isoformat()
                drop |= {x["id"] for x in self.d["meetings"] if x.get("series_id") == sr["id"] and
                         parse_date(x["date"]) >= d0}
            else:
                sr.setdefault("skip_dates", []).append(m["date"])
        self.d["meetings"] = [x for x in self.d["meetings"] if x["id"] not in drop]
        self.save()
        return True

    def _ensure_followup(self, m):
        """Client meetings and demos get a 'send follow-up' task the next working day, automatically."""
        if m.get("type") not in ("Client demo", "Client meeting") or not self.d["settings"].get("auto_followup", True):
            return
        d = parse_date(m.get("date"))
        if not d:
            return
        due = next_working_day(d + dt.timedelta(days=1), self.ws.holidays())
        who = m.get("client") or m["title"]
        title = f"Send follow-up to {who}: {m['title']}" if m.get("client") else f"Send follow-up: {m['title']}"
        existing = [x for x in self.d["tasks"] if x.get("meeting_id") == m["id"] and x.get("auto") == "followup"]
        if existing:
            if existing[0].get("status") != "Done":
                existing[0].update({"title": title, "due": due.isoformat()})
            return
        self.d["tasks"].append({"id": new_id(self.d["tasks"]), "title": title, "notes": "Use '✉ Follow-up email' in "
                                "Meetings & Notes for a ready draft.", "due": due.isoformat(), "time": "",
                                "priority": "High" if m.get("type") == "Client demo" else "Normal",
                                "type": "Follow-up", "person": "", "status": "Open", "recur": "None",
                                "created": today().isoformat(), "meeting_id": m["id"], "auto": "followup"})

    def _ensure_demo_prep(self, m):
        d = parse_date(m.get("date"))
        if not d:
            return
        hols = self.ws.holidays()
        prep = add_working_days(d, -int(self.d["settings"].get("demo_prep_days", 3)), hols)
        if prep < today():
            prep = today()
        existing = [x for x in self.d["tasks"] if x.get("meeting_id") == m["id"] and x.get("type") == "Demo prep"]
        title = f"Prepare for demo: {m['title']}" + (f" ({m['client']})" if m.get("client") else "")
        if existing:
            if existing[0].get("status") != "Done":
                existing[0].update({"title": title, "due": prep.isoformat()})
        else:
            self.d["tasks"].append({"id": new_id(self.d["tasks"]), "title": title, "notes": "Use the demo checklist in "
                                    "Clients & Demos.", "due": prep.isoformat(), "time": "", "priority": "High",
                                    "type": "Demo prep", "person": "", "status": "Open", "recur": "None",
                                    "created": today().isoformat(), "meeting_id": m["id"]})

    def _sel_meeting(self):
        mid = getattr(self, "_meet_sel", None)
        return next((m for m in self.d["meetings"] if m["id"] == mid), None) if mid else None

    def _store_notes(self, mid):
        m = next((x for x in self.d["meetings"] if x["id"] == mid), None)
        if m is not None and hasattr(self, "txt_notes"):
            txt = self.txt_notes.get("1.0", "end").strip()
            if txt != (m.get("notes") or ""):
                m["notes"] = txt
                self.save()

    def meet_actions(self):
        """'Find action items' button: new ones first; if all were seen already, offer them all again."""
        m = self._sel_meeting()
        if not m:
            return
        self._store_notes(m["id"])
        if not (m.get("notes") or "").strip():
            messagebox.showinfo(APP_NAME, "Type or paste the meeting notes first.", parent=self)
            return
        if self.check_actions(m["id"]):
            return
        acts = extract_actions(m["notes"], self.people())
        if not acts:
            if messagebox.askyesno(APP_NAME, "I couldn't spot any action items in these notes.\n\nShall I ask "
                                             "Claude instead? (best for very messy notes)", parent=self):
                self.claude_actions()
            return
        self.actions_preview(acts, m)

    def _leave_meetings(self):
        """Leaving My PA: save what's in the notes box and check a meeting's notes for actions."""
        if hasattr(self, "txt_notes"):
            self._store_detail()
            mid = getattr(self, "_meet_sel", None)
            if mid:
                self.after(80, lambda: self.check_actions(mid))

    def check_actions(self, mid) -> bool:
        """Look for NEW action items in a meeting's notes and ask to add them. Returns True if any were found."""
        m = next((x for x in self.d["meetings"] if x["id"] == mid), None)
        if not m or not (m.get("notes") or "").strip():
            return False
        seen = set(m.get("actions_seen") or [])
        new = [a for a in extract_actions(m["notes"], self.people()) if norm(a["title"]) not in seen]
        if not new:
            return False
        self.actions_preview(new, m)
        return True

    def actions_preview(self, acts, m=None, on_added=None):
        if getattr(self, "_actions_open", False):
            return
        self._actions_open = True
        win = tk.Toplevel(self)
        win.title("Action items found")
        win.configure(bg=C["bg"])
        win.transient(self)
        frm = ttk.Frame(win, padding=18, style="Bg.TFrame")
        frm.pack(fill="both", expand=True)
        where = f" in '{m['title']}'" if m else ""
        ttk.Label(frm, text=f"✅ I found {plural(len(acts), 'action item')}{where}", style="H2.TLabel").pack(anchor="w")
        ttk.Label(frm, text="They're all ticked. Untick anything you don't want, then click Add. "
                            "Things other people owe you go to 'Waiting on others'.",
                  style="Muted.TLabel").pack(anchor="w", pady=(0, 10))
        me = norm(self.d["settings"].get("your_name"))
        rows = []
        not_names = {"we", "team", "need", "needs", "please", "all", "everyone", "client", "they", "you", "i"}
        for a in acts:
            v = tk.BooleanVar(value=True)
            if not a["person"]:
                mm = re.match(r"^([A-Z][a-z]+)\s+(?:to|will|should|needs to)\s", a["title"])
                if mm and mm.group(1).lower() not in not_names and not (me and me.startswith(mm.group(1).lower())):
                    a["person"] = mm.group(1)
            mine = a.get("mine") or not a["person"] or bool(me and norm(a["person"]).startswith(me))
            desc = f"{a['title']}   —   {fmt_date(a['due']) if a['due'] else 'no date'}" + \
                   (f"   ·   👤 {a['person']}" if a["person"] else "") + ("" if mine else "   ·   ⏳ waiting on them")
            ttk.Checkbutton(frm, text=desc, variable=v).pack(anchor="w", pady=3)
            rows.append((v, a, mine))

        def finish():
            if m is not None:
                m["actions_seen"] = sorted(set(m.get("actions_seen") or []) | {norm(a["title"]) for a in acts})
                self.save()
            self._actions_open = False
            win.destroy()

        def add():
            n = 0
            for v, a, mine in rows:
                if not v.get():
                    continue
                title = a["title"]
                if mine and a["person"]:
                    first = re.escape(a["person"].split(" ")[0])
                    title = re.sub(rf"^{first}\s+(?:to|will|should|needs to)\s+", "", title, flags=re.I)
                    title = title[:1].upper() + title[1:]
                task = {"id": new_id(self.d["tasks"]), "title": title,
                        "notes": f"From meeting: {m['title']} ({fmt_date(m.get('date'))})" if m else "",
                        "due": a["due"].isoformat() if a["due"] else "", "time": a["time"],
                        "priority": a["priority"], "type": a["type"] if mine else "Follow-up",
                        "person": a["person"], "status": "Open" if mine else "Waiting", "recur": "None",
                        "created": today().isoformat(), "meeting_id": m["id"] if m else None}
                if not mine:
                    task["waiting_since"] = today().isoformat()
                if not task["due"]:
                    task["due"] = (today() if mine else add_working_days(today(), 3, self.ws.holidays())).isoformat()
                self.d["tasks"].append(task)
                n += 1
            finish()
            if on_added:
                on_added()
            if m is not None and getattr(self, "_detail", None) == ("m", m["id"]) and hasattr(self, "lbl_from"):
                self._show_tasks_from(m)
            self._refresh_open()
            self.set_status(f"Added {plural(n, 'task')} to My PA. They're in ☀ My day / Next 7 days by their dates.")

        bb = ttk.Frame(frm, style="Bg.TFrame")
        bb.pack(fill="x", pady=(14, 0))
        ttk.Button(bb, text="Skip these", command=finish).pack(side="right")
        ttk.Button(bb, text="Add to My PA", style="Accent.TButton", command=add).pack(side="right", padx=8)
        win.protocol("WM_DELETE_WINDOW", finish)
        win.bind("<Return>", lambda e: add())
        center_on(win, self)
        try:
            win.grab_set()
        except tk.TclError:
            pass

    def meet_email(self):
        m = self._sel_meeting()
        if not m:
            return
        notes = self.txt_notes.get("1.0", "end").strip()
        acts = extract_actions(notes, self.people())
        lines = [f"• {a['title']}" + (f" — {a['person']}" if a["person"] else "") +
                 (f" (by {fmt_date(a['due'], day=False)})" if a["due"] else "") for a in acts]
        txt = (f"Subject: {m['title']} – summary & next steps\n\nHi all,\n\nThank you for joining "
               f"{m['title']} on {fmt_date(m.get('date'), day=False)}.\n\nAction items:\n" +
               ("\n".join(lines) or "• (add action items)") +
               "\n\nPlease let me know if I missed anything.\n\nBest regards,\n" + self.d["settings"].get("your_name", ""))
        self.clipboard_clear()
        self.clipboard_append(txt)
        self.set_status("Follow-up email copied. Paste it into Outlook (Ctrl+V).")

    def claude_actions(self):
        """For messy notes: Claude reads them, you paste its reply back, the actions land in My PA."""
        self._store_detail()
        m = self._sel_meeting()
        notes = ((m.get("notes") if m else self.d["flags"].get("todo_notes")) or "").strip()
        if not notes:
            messagebox.showinfo(APP_NAME, "Type or paste your notes first.", parent=self)
            return
        me = self.d["settings"].get("your_name") or "me"
        where = f"a meeting: '{m['title']}' on {fmt_date(m.get('date'))}" if m else "my to-do scratch pad"
        prompt = (f"These are my rough notes from {where}. "
                  f"I am {me}. Today is {today().strftime('%A %d-%m-%Y')}.\n"
                  f"People who may be mentioned: {', '.join(self.people()) or '-'}.\n\n"
                  "Find EVERY action item, even if it is only implied. Reply with ONLY lines in exactly this format, "
                  "one per action, nothing else:\n"
                  "ACTION | <who: write 'me' if it is mine, otherwise the person's name> | <what, short and clear> | "
                  "<due date as DD-MM-YYYY, or leave empty>\n"
                  "Then one final line:\nSUMMARY | <the meeting in two sentences>\n\n"
                  f"NOTES:\n{notes}\n")
        self.clipboard_clear()
        self.clipboard_append(prompt)
        try:
            webbrowser.open("https://claude.ai/new")
        except Exception:
            pass
        win = tk.Toplevel(self)
        win.title("Find action items with Claude")
        win.configure(bg=C["bg"])
        win.transient(self)
        frm = ttk.Frame(win, padding=18, style="Bg.TFrame")
        frm.pack(fill="both", expand=True)
        ttk.Label(frm, text="✨ Find action items with Claude", style="H2.TLabel").pack(anchor="w")
        ttk.Label(frm, text="1.  Claude has opened in your browser and your notes are copied.\n"
                            "2.  Click in Claude's message box, press Ctrl+V, then Enter.\n"
                            "3.  Copy Claude's whole reply and paste it below (Ctrl+V), then click 'Add actions'.",
                  justify="left").pack(anchor="w", pady=(6, 10))
        txt = make_text(frm, height=14, width=90)
        txt.pack(fill="both", expand=True)
        txt.focus_set()

        def add():
            reply = txt.get("1.0", "end").strip()
            if not reply:
                return
            acts, summary = self._parse_claude_reply(reply)
            if not acts:
                messagebox.showinfo(APP_NAME, "I couldn't find 'ACTION | …' lines in that reply. Please paste "
                                              "Claude's whole answer.", parent=win)
                return
            if m and summary and "Summary (Claude):" not in (m.get("notes") or ""):
                m["notes"] = f"Summary (Claude): {summary}\n\n" + (m.get("notes") or "")
                self.save()
                if getattr(self, "_meet_sel", None) == m["id"] and hasattr(self, "txt_notes"):
                    self.txt_notes.delete("1.0", "end")
                    self.txt_notes.insert("1.0", m["notes"])
            win.destroy()
            self.actions_preview(acts, m, on_added=None if m else self._todo_done)

        bb = ttk.Frame(frm, style="Bg.TFrame")
        bb.pack(fill="x", pady=(10, 0))
        ttk.Button(bb, text="Cancel", command=win.destroy).pack(side="right")
        ttk.Button(bb, text="Add actions", style="Accent.TButton", command=add).pack(side="right", padx=8)
        ttk.Button(bb, text="📋 Copy the notes for Claude again",
                   command=lambda: (self.clipboard_clear(), self.clipboard_append(prompt))).pack(side="left")
        center_on(win, self)

    def _parse_claude_reply(self, reply):
        people = self.people()
        acts, summary = [], ""
        for line in reply.splitlines():
            line = line.strip().strip("`*-• ")
            if line.upper().startswith("SUMMARY"):
                summary = line.split("|", 1)[-1].strip(" :")
                continue
            if not line.upper().startswith("ACTION") or "|" not in line:
                continue
            parts = [p.strip() for p in line.split("|")] + ["", "", ""]
            who, what, due = parts[1], parts[2], parts[3]
            if not what:
                continue
            t = parse_task(what, people)
            t["title"] = what[:1].upper() + what[1:]
            d = parse_user_date(due) or parse_date(due)
            if d:
                t["due"] = d
            mine = who.lower() in ("me", "i", "myself", "") or norm(who) == norm(self.d["settings"].get("your_name"))
            t["mine"] = mine
            if not mine:
                full = next((p for p in people if norm(p) == norm(who) or norm(p).split(" ")[0] == norm(who)
                             .split(" ")[0]), who)
                t["person"] = full
            acts.append(t)
        return acts, summary

    # ----- Clients & Demos ------------------------------------------------------------
    PROSPECT_STAGES = ["Lead", "First call done", "Demo planned", "Demo done", "Proposal sent", "Negotiation",
                       "Won", "Lost", "On hold"]
    CURRENT_STATUS = ["Active", "Onboarding", "At risk", "Inactive"]

    def client_dialog(self, c=None, kind=None):
        kind = (c or {}).get("kind") or kind or "Current"
        stages = self.CURRENT_STATUS if kind == "Current" else self.PROSPECT_STAGES
        fields = [("name", "Client / company", "entry", None), ("kind", "Type", "choice", ["Current", "Prospect"]),
                  ("stage", "Status / stage", "choice", stages), ("urls", "Their app links (one per line)", "text", 2),
                  ("contacts", "Contacts (comma separated)", "entry", None),
                  ("evaluating", "What they use / are evaluating", "entry", None),
                  ("next_step", "Next step", "entry", None), ("next_date", "Next step date", "date", None),
                  ("notes", "Notes", "text", 4)]
        vals = form_dialog(self, "Edit client" if c else ("New client" if kind == "Current" else "New prospect"),
                           fields, c or {"kind": kind, "stage": stages[0]})
        if not vals or not vals.get("name"):
            return None
        if vals["kind"] == "Current" and vals["stage"] not in self.CURRENT_STATUS:
            vals["stage"] = "Active"
        if vals["kind"] == "Prospect" and vals["stage"] not in self.PROSPECT_STAGES:
            vals["stage"] = "Lead"
        if c is None:
            c = {"id": new_id(self.d["clients"]), "created": today().isoformat()}
            self.d["clients"].append(c)
        c.update(vals)
        self.save()
        return c

    def _seed_clients(self):
        """One-time: give older client records a 'kind'."""
        if self.d["flags"].get("clients_seeded_v1"):
            return
        for c in self.d["clients"]:
            c.setdefault("kind", "Prospect" if c.get("stage") in CLIENT_STAGES else "Current")
        self.d["flags"]["clients_seeded_v1"] = True
        self.save()

    def build_clients(self, f):
        self._seed_clients()
        self.view_header(f, "Clients & Demos", "Your current clients and the companies you're pursuing, with their "
                                               "demos, meetings and notes in one place.",
                         [("🎯 New prospect", lambda: self.client_new("Prospect"), False),
                          ("➕ New client", lambda: self.client_new("Current"), True)])
        tabs = tk.Frame(f, bg=C["bg"])
        tabs.pack(fill="x", pady=(0, 8))
        self.cl_kind = tk.StringVar(value="Current")
        self.cl_tabs = {}
        for k, label in (("Current", "🏢 Current clients"), ("Prospect", "🎯 Prospects (pursuing)")):
            lb = tk.Label(tabs, text=label, bg=C["panel"], fg=C["ink"], font=FONTS["h3"], padx=16, pady=8,
                          cursor="hand2", highlightthickness=1, highlightbackground=C["line"])
            lb.pack(side="left", padx=(0, 6))
            lb.bind("<Button-1>", lambda e, kk=k: (self.cl_kind.set(kk), setattr(self, "_cl_sel", None),
                                                   self.refresh_clients()))
            self.cl_tabs[k] = lb
        self.pipe = tk.Frame(tabs, bg=C["bg"])
        self.pipe.pack(side="right")
        body = tk.Frame(f, bg=C["bg"])
        body.pack(fill="both", expand=True)
        # left: client cards
        left = tk.Frame(body, bg=C["panel"], highlightbackground=C["line"], highlightthickness=1, width=360)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        self.cl_canvas = tk.Canvas(left, bg=C["panel"], highlightthickness=0)
        sb = ttk.Scrollbar(left, orient="vertical", command=self.cl_canvas.yview)
        self.cl_canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.cl_canvas.pack(side="left", fill="both", expand=True)
        self.cl_list = tk.Frame(self.cl_canvas, bg=C["panel"])
        w = self.cl_canvas.create_window((0, 0), window=self.cl_list, anchor="nw")
        self.cl_canvas.bind("<Configure>", lambda e: self.cl_canvas.itemconfigure(w, width=e.width))
        self.cl_list.bind("<Configure>", lambda e: self.cl_canvas.configure(scrollregion=self.cl_canvas.bbox("all")))
        # right: detail
        self.cl_detail = tk.Frame(body, bg=C["bg"])
        self.cl_detail.pack(side="left", fill="both", expand=True, padx=(12, 0))
        self._cl_sel, self._cl_meet = None, None

    def refresh_clients(self):
        if not hasattr(self, "cl_list"):
            return
        kind = self.cl_kind.get()
        for k, lb in self.cl_tabs.items():
            n = sum(1 for c in self.d["clients"] if c.get("kind", "Current") == k)
            lb.configure(text=("🏢 Current clients" if k == "Current" else "🎯 Prospects (pursuing)") + f"  {n}",
                         bg=C["accent"] if k == kind else C["panel"], fg=C["on_accent"] if k == kind else C["ink"])
        for w in self.pipe.winfo_children():
            w.destroy()
        clients = [c for c in self.d["clients"] if c.get("kind", "Current") == kind]
        if kind == "Prospect":
            counts = Counter(c.get("stage", "Lead") for c in clients)
            for st in self.PROSPECT_STAGES[:7]:
                tk.Label(self.pipe, text=f"{st} {counts.get(st, 0)}", bg=C["panel"], fg=C["muted"] if not
                         counts.get(st) else C["header"], font=FONTS["small"], padx=8, pady=3,
                         highlightthickness=1, highlightbackground=C["line"]).pack(side="left", padx=2)
        for w in self.cl_list.winfo_children():
            w.destroy()
        order = {s: i for i, s in enumerate(self.PROSPECT_STAGES + self.CURRENT_STATUS)}
        clients.sort(key=lambda c: (order.get(c.get("stage"), 99), c["name"].lower()))
        if not clients:
            tk.Label(self.cl_list, text="No prospects yet.\nClick '🎯 New prospect'." if kind == "Prospect" else
                     "No clients yet.\nClick '➕ New client'.", bg=C["panel"], fg=C["muted"], font=FONTS["h3"],
                     justify="center").pack(pady=40)
        if self._cl_sel not in {c["id"] for c in clients}:
            self._cl_sel = clients[0]["id"] if clients else None
        t = today()
        for c in clients:
            on = c["id"] == self._cl_sel
            bg = C["select"] if on else C["panel"]
            card = tk.Frame(self.cl_list, bg=bg, cursor="hand2", highlightthickness=1,
                            highlightbackground=C["accent"] if on else C["line"])
            card.pack(fill="x", padx=10, pady=(8, 0))
            top = tk.Frame(card, bg=bg)
            top.pack(fill="x", padx=12, pady=(10, 2))
            nm = tk.Label(top, text=c["name"], bg=bg, fg=C["header"], font=FONTS["h3"], anchor="w")
            nm.pack(side="left")
            stc = {"Active": C["good"], "Won": C["good"], "At risk": C["bad"], "Lost": C["bad"],
                   "Inactive": C["muted"], "On hold": C["muted"]}.get(c.get("stage"), C["accent"])
            tk.Label(top, text=c.get("stage", ""), bg=stc, fg="white", font=FONTS["small_bold"], padx=6).pack(
                side="right")
            meets = [m for m in self.d["meetings"] if norm(m.get("client")) == norm(c["name"])]
            nxt = sorted((m for m in meets if parse_date(m.get("date")) and parse_date(m["date"]) >= t),
                         key=lambda m: m["date"])
            line = (f"Next: {nxt[0]['title']} · {short_date(nxt[0]['date'])}" if nxt else
                    (f"Next step: {c['next_step']}" if c.get("next_step") else f"{plural(len(meets), 'meeting')}"))
            sub = tk.Label(card, text=line, bg=bg, fg=C["muted"], font=FONTS["small"], anchor="w")
            sub.pack(fill="x", padx=12, pady=(0, 10))
            for wdg in (card, top, nm, sub):
                wdg.bind("<Button-1>", lambda e, cid=c["id"]: (setattr(self, "_cl_sel", cid),
                                                               setattr(self, "_cl_meet", None),
                                                               self.refresh_clients()))
        self.client_show()

    def _sel_client(self):
        return next((c for c in self.d["clients"] if c["id"] == self._cl_sel), None)

    def client_show(self):
        d = self.cl_detail
        if self._cl_meet and hasattr(self, "cl_notes"):
            self._cl_store_notes()
        for w in d.winfo_children():
            w.destroy()
        c = self._sel_client()
        if not c:
            return
        head = tk.Frame(d, bg=C["panel"], highlightbackground=C["line"], highlightthickness=1)
        head.pack(fill="x")
        hr = tk.Frame(head, bg=C["panel"])
        hr.pack(fill="x", padx=16, pady=(12, 4))
        tk.Label(hr, text=c["name"], bg=C["panel"], fg=C["header"], font=FONTS["h1"]).pack(side="left")
        tk.Label(hr, text=f"  {c.get('kind', 'Current')} · {c.get('stage', '')}", bg=C["panel"], fg=C["muted"],
                 font=FONTS["body"]).pack(side="left", pady=(6, 0))
        for txt, cmd in (("🗑", self.client_delete), ("✏ Edit", self.client_edit),
                         ("📋 Demo prep for Claude", self.client_prompt)):
            ttk.Button(hr, text=txt, command=cmd).pack(side="right", padx=(6, 0))
        info = tk.Frame(head, bg=C["panel"])
        info.pack(fill="x", padx=16, pady=(0, 12))
        for url in [u.strip() for u in (c.get("urls") or "").splitlines() if u.strip()]:
            lk = tk.Label(info, text=f"🔗 {url}", bg=C["panel"], fg=C["blue"], font=FONTS["body"], cursor="hand2",
                          anchor="w")
            lk.pack(fill="x")
            lk.bind("<Button-1>", lambda e, u=url: webbrowser.open(u))
        bits = [("👥", c.get("contacts")), ("🧩", c.get("evaluating")),
                ("➡", (c.get("next_step") or "") + (f" · {fmt_date(c['next_date'])}" if c.get("next_date") else ""))]
        for icon, val in bits:
            if val:
                tk.Label(info, text=f"{icon} {val}", bg=C["panel"], fg=C["ink"], font=FONTS["body"],
                         anchor="w").pack(fill="x")
        if c.get("notes"):
            tk.Label(info, text=c["notes"], bg=C["panel"], fg=C["muted"], font=FONTS["small"], anchor="w",
                     justify="left", wraplength=760).pack(fill="x", pady=(4, 0))
        # meetings & demos
        mh = tk.Frame(d, bg=C["bg"])
        mh.pack(fill="x", pady=(12, 6))
        tk.Label(mh, text="🎬 Demos & meetings", bg=C["bg"], fg=C["header"], font=FONTS["h2"]).pack(side="left")
        ttk.Button(mh, text="📝 Add meeting notes", command=lambda: self.client_demo("Client meeting", past=True)).pack(
            side="right")
        ttk.Button(mh, text="🎬 Schedule a demo", style="Accent.TButton",
                   command=lambda: self.client_demo("Client demo")).pack(side="right", padx=6)
        body = tk.Frame(d, bg=C["bg"])
        body.pack(fill="both", expand=True)
        ml = tk.Frame(body, bg=C["panel"], highlightbackground=C["line"], highlightthickness=1, width=330)
        ml.pack(side="left", fill="y")
        ml.pack_propagate(False)
        meets = sorted((m for m in self.d["meetings"] if norm(m.get("client")) == norm(c["name"])),
                       key=lambda m: (m.get("date") or "", m.get("time") or ""), reverse=True)
        if not meets:
            tk.Label(ml, text="No demos or meetings yet.\n\n'🎬 Schedule a demo' for an upcoming one,\nor "
                              "'📝 Add meeting notes' for one\nthat already happened.", bg=C["panel"], fg=C["muted"],
                     justify="center").pack(pady=30)
        if self._cl_meet not in {m["id"] for m in meets}:
            self._cl_meet = meets[0]["id"] if meets else None
        t = today()
        for m in meets:
            on = m["id"] == self._cl_meet
            bg = C["select"] if on else C["panel"]
            r = tk.Frame(ml, bg=bg, cursor="hand2")
            r.pack(fill="x")
            dd = parse_date(m.get("date"))
            icon = "🎬" if m.get("type") == "Client demo" else "🤝"
            a = tk.Label(r, text=f"{icon} {m['title']}", bg=bg, fg=C["ink"], font=FONTS["body"], anchor="w")
            a.pack(fill="x", padx=12, pady=(8, 0))
            state = ("notes ✓" if (m.get("notes") or "").strip() else ("upcoming" if dd and dd >= t else "add notes"))
            b = tk.Label(r, text=f"{fmt_date(dd)} {m.get('time') or ''} · {state}", bg=bg,
                         fg=C["blue"] if state == "upcoming" else (C["good"] if state == "notes ✓" else C["amber"]),
                         font=FONTS["small"], anchor="w")
            b.pack(fill="x", padx=12, pady=(0, 8))
            tk.Frame(ml, bg=C["line"], height=1).pack(fill="x")
            for wdg in (r, a, b):
                wdg.bind("<Button-1>", lambda e, mid=m["id"]: self._cl_pick_meeting(mid))
        right = tk.Frame(body, bg=C["panel"], highlightbackground=C["line"], highlightthickness=1)
        right.pack(side="left", fill="both", expand=True, padx=(10, 0))
        m = next((x for x in meets if x["id"] == self._cl_meet), None)
        if not m:
            return
        rt = tk.Frame(right, bg=C["panel"])
        rt.pack(fill="x", padx=14, pady=(12, 4))
        tk.Label(rt, text=m["title"], bg=C["panel"], fg=C["header"], font=FONTS["h2"]).pack(side="left")
        ttk.Button(rt, text="✏", width=3, command=lambda: (self.meeting_dialog(m), self.client_show())).pack(
            side="right")
        tk.Label(right, text=f"{fmt_date(m.get('date'))} {m.get('time') or ''} · {m.get('type', '')}",
                 bg=C["panel"], fg=C["muted"], font=FONTS["small"], anchor="w").pack(fill="x", padx=14)
        if m.get("type") == "Client demo" and parse_date(m.get("date")) and parse_date(m["date"]) >= t:
            ck = tk.Frame(right, bg=C["panel"])
            ck.pack(fill="x", padx=14, pady=(6, 0))
            m.setdefault("checklist", {})
            done = sum(1 for k in DEMO_CHECKLIST if m["checklist"].get(k))
            tk.Label(ck, text=f"Demo prep {done}/{len(DEMO_CHECKLIST)}", bg=C["panel"], fg=C["accent"],
                     font=FONTS["small_bold"]).pack(anchor="w")
            grid = tk.Frame(ck, bg=C["panel"])
            grid.pack(fill="x")
            for i, item in enumerate(DEMO_CHECKLIST):
                v = tk.BooleanVar(value=bool(m["checklist"].get(item)))

                def toggle(it=item, var=v):
                    m["checklist"][it] = var.get()
                    self.save()

                tk.Checkbutton(grid, text=item, variable=v, command=toggle, bg=C["panel"], fg=C["ink"],
                               selectcolor=C["field"], activebackground=C["panel"], anchor="w").grid(
                    row=i // 2, column=i % 2, sticky="w")
        tk.Label(right, text="📝 Notes from this meeting / demo (type or paste anything)", bg=C["panel"],
                 fg=C["header"], font=FONTS["h3"], anchor="w").pack(fill="x", padx=14, pady=(10, 4))
        self.cl_notes = make_text(right, height=8)
        self.cl_notes.pack(fill="both", expand=True, padx=14)
        self.cl_notes.insert("1.0", m.get("notes") or "")
        self.cl_notes.bind("<FocusOut>", lambda e: self._cl_store_notes())
        bb = tk.Frame(right, bg=C["panel"])
        bb.pack(fill="x", padx=14, pady=10)
        ttk.Button(bb, text="✅ Save & add tasks from notes", style="Accent.TButton",
                   command=self._cl_tasks_from_notes).pack(side="left")
        ttk.Button(bb, text="✉ Follow-up email", command=self._cl_email).pack(side="left", padx=6)
        tf = self._tasks_from(m)
        if tf:
            tk.Label(bb, text=f"✓ {plural(len(tf), 'task')} from this meeting in My PA", bg=C["panel"],
                     fg=C["good"], font=FONTS["small_bold"]).pack(side="left", padx=8)

    def _cl_pick_meeting(self, mid):
        self._cl_store_notes()
        self._cl_meet = mid
        self.client_show()

    def _cl_store_notes(self):
        m = next((x for x in self.d["meetings"] if x["id"] == self._cl_meet), None)
        if m is None or not hasattr(self, "cl_notes"):
            return
        try:
            txt = self.cl_notes.get("1.0", "end").strip()
        except tk.TclError:
            return
        if txt != (m.get("notes") or ""):
            m["notes"] = txt
            self.save()

    def _cl_tasks_from_notes(self):
        self._cl_store_notes()
        m = next((x for x in self.d["meetings"] if x["id"] == self._cl_meet), None)
        if not m or not (m.get("notes") or "").strip():
            messagebox.showinfo(APP_NAME, "Type or paste the notes first.", parent=self)
            return
        acts = extract_actions(m["notes"], self.people())
        seen = set(m.get("actions_seen") or [])
        new = [a for a in acts if norm(a["title"]) not in seen] or acts
        if not new:
            if messagebox.askyesno(APP_NAME, "I couldn't spot action items. Ask Claude instead?", parent=self):
                self._meet_sel = m["id"]
                self.claude_actions()
            return
        self.actions_preview(new, m, on_added=self.client_show)

    def _cl_email(self):
        self._cl_store_notes()
        m = next((x for x in self.d["meetings"] if x["id"] == self._cl_meet), None)
        if not m:
            return
        acts = extract_actions(m.get("notes") or "", self.people())
        lines = [f"• {a['title']}" + (f" — {a['person']}" if a["person"] else "") +
                 (f" (by {fmt_date(a['due'], day=False)})" if a["due"] else "") for a in acts]
        txt = (f"Subject: {m['title']} – summary & next steps\n\nHi all,\n\nThank you for your time on "
               f"{fmt_date(m.get('date'), day=False)}.\n\nNext steps:\n" + ("\n".join(lines) or "• (add next steps)") +
               "\n\nPlease let me know if I missed anything.\n\nBest regards,\n" + self.d["settings"].get("your_name", ""))
        self.clipboard_clear()
        self.clipboard_append(txt)
        self.set_status("Follow-up email copied. Paste it into Outlook (Ctrl+V).")

    def client_new(self, kind="Current"):
        c = self.client_dialog(kind=kind)
        if c:
            self.cl_kind.set(c.get("kind", kind))
            self._cl_sel = c["id"]
            self.refresh_clients()
            self.refresh_cards()

    def client_edit(self):
        c = self._sel_client()
        if c and self.client_dialog(c):
            self.cl_kind.set(c.get("kind", "Current"))
            self.refresh_clients()

    def client_delete(self):
        c = self._sel_client()
        if c and messagebox.askyesno(APP_NAME, f"Delete '{c['name']}'? (Their meetings and notes stay in My PA.)",
                                     parent=self):
            self.d["clients"] = [x for x in self.d["clients"] if x["id"] != c["id"]]
            self._cl_sel = None
            self.save()
            self.refresh_clients()

    def client_demo(self, kind="Client demo", past=False):
        c = self._sel_client()
        if not c:
            messagebox.showinfo(APP_NAME, "Pick a client on the left first.", parent=self)
            return
        when = today() if past else add_working_days(today(), 5, self.ws.holidays())
        title = (f"Demo – {c['name']}" if kind == "Client demo" else f"Meeting – {c['name']}")
        m = self.meeting_dialog(preset={"type": kind, "client": c["name"], "title": title,
                                        "date": when.isoformat()})
        if m:
            if kind == "Client demo" and c.get("kind") == "Prospect" and c.get("stage") in ("Lead", "First call done"):
                c["stage"] = "Demo planned"
                c["next_step"], c["next_date"] = "Demo", m["date"]
                self.save()
            self._cl_meet = m["id"]
            self.refresh_clients()
            self.set_status("Saved. Add your notes on the right." if past else
                            "Demo saved. A prep task and a follow-up task were added to My PA.")

    def client_prompt(self):
        c = self._sel_client()
        if not c:
            messagebox.showinfo(APP_NAME, "Select a client first.", parent=self)
            return
        hist = [f"- {fmt_date(m.get('date'), day=False)} {m['title']} ({m.get('type')}): "
                f"{truncate((m.get('notes') or '').replace(chr(10), ' '), 400)}"
                for m in self.d["meetings"] if norm(m.get("client")) == norm(c["name"])]
        txt = (f"Help me prepare for a product demo.\n\nClient: {c['name']}\nContacts: {c.get('contacts') or '-'}\n"
               f"They are evaluating: {c.get('evaluating') or '-'}\nStage: {c.get('stage')}\n"
               f"Notes: {c.get('notes') or '-'}\n\nEarlier meetings:\n" + ("\n".join(hist) or "- none") +
               "\n\nGive me: a 20-minute demo flow, the 5 questions they are most likely to ask with short answers, "
               "risks to avoid during the demo, and a follow-up email draft.\n")
        self.clipboard_clear()
        self.clipboard_append(txt)
        messagebox.showinfo(APP_NAME, "Demo prep details copied. Paste into Claude (Ctrl+V).", parent=self)

    # ----- Legal & Contracts ----------------------------------------------------------
    def contract_act_by(self, c):
        base = parse_date(c.get("renewal")) or parse_date(c.get("end"))
        if not base:
            return None
        try:
            notice = int(c.get("notice_days") or 0)
        except ValueError:
            notice = 0
        return base - dt.timedelta(days=notice)

    def contract_alerts(self):
        out = []
        t = today()
        for c in self.d["contracts"]:
            if c.get("status") in ("Expired", "Terminated"):
                continue
            a = self.contract_act_by(c)
            if a and (a - t).days <= 14:
                when = "was due " + fmt_date(a) if a < t else f"by {fmt_date(a)} ({(a - t).days} days)"
                out.append(("Contract", f"⚖ {c['party']} {c.get('type', '')}: decide renew / give notice {when}", a))
            if c.get("status") in ("In review", "Sent for signature") and c.get("status_since"):
                age = (t - (parse_date(c["status_since"]) or t)).days
                if age >= 7:
                    out.append(("Contract", f"⚖ {c['party']} {c.get('type', '')} has been '{c['status']}' for "
                                            f"{age} days: chase it", t))
        return out

    def contract_dialog(self, c=None):
        fields = [("party", "Party / client", "combo", [x["name"] for x in self.d["clients"]]),
                  ("type", "Type", "choice", CONTRACT_TYPES), ("title", "Title / short description", "entry", None),
                  ("status", "Status", "choice", CONTRACT_STATUS), ("owner", "Owner", "combo", self.people()),
                  ("start", "Start date", "date", None), ("end", "End date", "date", None),
                  ("renewal", "Renewal date", "date", None), ("notice_days", "Notice period (days)", "entry", None),
                  ("link", "File / link (OneDrive, SharePoint…)", "entry", None), ("notes", "Notes", "text", 4)]
        vals = form_dialog(self, "Edit contract" if c else "New contract", fields,
                           c or {"type": "NDA", "status": "Draft", "notice_days": "30"})
        if not vals or not vals.get("party"):
            return None
        if vals.get("notice_days") and not str(vals["notice_days"]).strip().isdigit():
            messagebox.showinfo(APP_NAME, "Notice period should be a number of days, e.g. 30.", parent=self)
            return None
        if c is None:
            c = {"id": new_id(self.d["contracts"]), "checks": {}}
            self.d["contracts"].append(c)
        if vals.get("status") != c.get("status"):
            vals["status_since"] = today().isoformat()
            c["alerted"] = []
        if vals.get("renewal") != c.get("renewal") or vals.get("end") != c.get("end"):
            c["alerted"] = []
        c.update(vals)
        self.save()
        return c

    def build_legal(self, f):
        self.view_header(f, "Legal & Contracts", "A register of NDAs, MSAs, SOWs and more. 'Act by' = renewal (or end) "
                                                 "date minus the notice period. I'll remind you 60, 30, 14 and 7 days "
                                                 "before.",
                         [("📋 Review prompt for Claude", self.legal_prompt, False),
                          ("➕ New contract", self.legal_new, True)])
        pw = ttk.PanedWindow(f, orient="horizontal")
        pw.pack(fill="both", expand=True)
        left = ttk.Frame(pw, style="Bg.TFrame")
        right = ttk.Frame(pw, style="Bg.TFrame", padding=(12, 0, 0, 0))
        pw.add(left, weight=5)
        pw.add(right, weight=2)
        bar = ttk.Frame(left, style="Bg.TFrame")
        bar.pack(fill="x", pady=(0, 6))
        ttk.Button(bar, text="✏ Edit", command=self.legal_edit).pack(side="left")
        ttk.Button(bar, text="🔗 Open file", command=self.legal_open).pack(side="left", padx=6)
        ttk.Button(bar, text="🗑 Delete", command=self.legal_delete).pack(side="left")
        frm, self.tv_leg = make_table(left, [("type", "Type", 80), ("status", "Status", 130), ("owner", "Owner", 120),
                                             ("end", "Ends", 110), ("act", "Act by", 110), ("left", "Days left", 80),
                                             ("checks", "Checklist", 80)], height=18, tree_col=("Party", 220))
        frm.pack(fill="both", expand=True)
        self.tv_leg.bind("<<TreeviewSelect>>", lambda e: self.legal_show())
        self.tv_leg.bind("<Double-1>", lambda e: self.legal_edit())
        self.lbl_leg = ttk.Label(right, text="Review checklist", style="H2.TLabel")
        self.lbl_leg.pack(anchor="w")
        self.leg_box = ttk.Frame(right, style="Bg.TFrame")
        self.leg_box.pack(fill="both", expand=True, pady=(6, 0))
        ttk.Label(right, text="ⓘ This is a tracker, not legal advice. Please have legal review the final terms.",
                  style="Muted.TLabel", wraplength=300, justify="left").pack(anchor="w", pady=(8, 0))

    def refresh_legal(self):
        if not hasattr(self, "tv_leg"):
            return
        tv = self.tv_leg
        sel = tv.selection()
        tv.delete(*tv.get_children())
        t = today()

        def k(c):
            a = self.contract_act_by(c)
            return (c.get("status") in ("Expired", "Terminated"), a or dt.date(9999, 1, 1))

        for c in sorted(self.d["contracts"], key=k):
            a = self.contract_act_by(c)
            left = (a - t).days if a else None
            closed = c.get("status") in ("Expired", "Terminated")
            done = sum(1 for x in CONTRACT_CHECKS if (c.get("checks") or {}).get(x))
            tag = ("muted",) if closed else (("hot",) if left is not None and left <= 14 else
                                            (("warm",) if left is not None and left <= 60 else ()))
            tv.insert("", "end", iid=f"k{c['id']}", text=f"{c['party']}" + (f" – {c['title']}" if c.get("title")
                                                                              else ""),
                      values=(c.get("type", ""), c.get("status", ""), c.get("owner", ""),
                              fmt_date(c.get("end"), day=False) if c.get("end") else "",
                              fmt_date(a, day=False) if a else "", "" if left is None else left,
                              f"{done}/{len(CONTRACT_CHECKS)}"), tags=tag)
        if not self.d["contracts"]:
            tv.insert("", "end", text="No contracts yet. Click '➕ New contract'.", tags=("muted",))
        for s in sel:
            if tv.exists(s):
                tv.selection_set(s)

    def _sel_contract(self):
        sel = [s for s in self.tv_leg.selection() if s.startswith("k")]
        if not sel:
            return None
        return next((c for c in self.d["contracts"] if c["id"] == int(sel[0][1:])), None)

    def legal_show(self):
        c = self._sel_contract()
        for w in self.leg_box.winfo_children():
            w.destroy()
        if not c:
            return
        c.setdefault("checks", {})
        self.lbl_leg.configure(text=f"Review checklist · {c['party']}")
        for item in CONTRACT_CHECKS:
            v = tk.BooleanVar(value=bool(c["checks"].get(item)))

            def toggle(it=item, var=v):
                c["checks"][it] = var.get()
                self.save()
                self.refresh_legal()

            ttk.Checkbutton(self.leg_box, text=item, variable=v, command=toggle).pack(anchor="w", pady=2)
        if c.get("notes"):
            ttk.Label(self.leg_box, text=truncate(c["notes"], 300), style="Muted.TLabel", wraplength=300,
                      justify="left").pack(anchor="w", pady=(8, 0))

    def legal_new(self):
        if self.contract_dialog():
            self.refresh_legal()
            self.refresh_cards()

    def legal_edit(self):
        c = self._sel_contract()
        if c and self.contract_dialog(c):
            self.refresh_legal()
            self.legal_show()

    def legal_delete(self):
        c = self._sel_contract()
        if c and messagebox.askyesno(APP_NAME, f"Delete the contract with {c['party']}?", parent=self):
            self.d["contracts"] = [x for x in self.d["contracts"] if x["id"] != c["id"]]
            self.save()
            self.refresh_legal()

    def legal_open(self):
        c = self._sel_contract()
        if not c or not c.get("link"):
            messagebox.showinfo(APP_NAME, "Add a file path or link to this contract first (✏ Edit).", parent=self)
            return
        link = c["link"].strip().strip('"')
        try:
            if re.match(r"^https?://", link):
                webbrowser.open(link)
            elif IS_WINDOWS:
                os.startfile(link)  # noqa
            else:
                subprocess.Popen(["xdg-open", link])
        except OSError as exc:
            messagebox.showerror(APP_NAME, f"Couldn't open it:\n{exc}", parent=self)

    def legal_prompt(self):
        c = self._sel_contract()
        if not c:
            messagebox.showinfo(APP_NAME, "Select a contract first.", parent=self)
            return
        txt = (f"I'm a Product Owner reviewing a {c.get('type')} with {c['party']}. I'll paste the contract text "
               "below. Please give me, in plain English:\n1. A one-paragraph summary\n2. Key dates: term, renewal, "
               "notice period, payment\n3. Anything unusual or one-sided I should raise with legal\n4. Obligations on "
               "our side (what we must deliver / do)\n5. Questions to ask before signing\nCheck in particular: " +
               ", ".join(CONTRACT_CHECKS) + ".\nRemind me this is not legal advice.\n\nCONTRACT TEXT:\n"
               "(paste here)\n")
        self.clipboard_clear()
        self.clipboard_append(txt)
        messagebox.showinfo(APP_NAME, "Copied. Paste into Claude, then paste the contract text under it.",
                            parent=self)

    # ----- Release calendar -----------------------------------------------------------
    def build_calendar(self, f):
        head = self.view_header(f, "Release calendar", "Sprints, regression, production, holidays, meetings, contract "
                                                       "deadlines and team leave in one place. Click a day for details.")
        nav = ttk.Frame(head, style="Bg.TFrame")
        nav.pack(side="right")
        ttk.Button(nav, text="◀", width=3, command=lambda: self.cal_move(-1)).pack(side="left")
        self.lbl_month = ttk.Label(nav, text="", style="H2.TLabel", width=16, anchor="center")
        self.lbl_month.pack(side="left", padx=6)
        ttk.Button(nav, text="▶", width=3, command=lambda: self.cal_move(1)).pack(side="left")
        ttk.Button(nav, text="Today", command=lambda: self.cal_move(0)).pack(side="left", padx=(8, 0))
        body = ttk.Frame(f, style="Bg.TFrame")
        body.pack(fill="both", expand=True)
        side = tk.Frame(body, bg=C["panel"], highlightbackground=C["line"], highlightthickness=1, width=300)
        side.pack(side="right", fill="y", padx=(12, 0))
        side.pack_propagate(False)
        self.cal_grid = tk.Frame(body, bg=C["line"])
        self.cal_grid.pack(side="left", fill="both", expand=True)
        self.lbl_day = tk.Label(side, text="", bg=C["panel"], fg=C["header"], font=FONTS["h2"], anchor="w",
                                justify="left", wraplength=270)
        self.lbl_day.pack(fill="x", padx=14, pady=(14, 6))
        self.day_box = tk.Frame(side, bg=C["panel"])
        self.day_box.pack(fill="both", expand=True, padx=14)
        leg = tk.Frame(side, bg=C["panel"])
        leg.pack(fill="x", padx=14, pady=12)
        for colour, text in ((C["accent"], "Sprint / regression"), (C["amber"], "Production 🚀"),
                             (C["info"], "Meetings & demos"), (C["lilac_ink"], "Contracts ⚖"), (C["good"], "Team & leave"),
                             (C["muted"], "Holidays")):
            r = tk.Frame(leg, bg=C["panel"])
            r.pack(fill="x")
            tk.Label(r, text="●", bg=C["panel"], fg=colour).pack(side="left")
            tk.Label(r, text=text, bg=C["panel"], fg=C["muted"], font=FONTS["small"]).pack(side="left")
        self.cal_month = today().replace(day=1)
        self.cal_day = today()

    def cal_move(self, step):
        if step == 0:
            self.cal_month = today().replace(day=1)
            self.cal_day = today()
        else:
            y, m = self.cal_month.year, self.cal_month.month + step
            y, m = (y + 1, 1) if m > 12 else ((y - 1, 12) if m < 1 else (y, m))
            self.cal_month = dt.date(y, m, 1)
        self.refresh_calendar()

    def events_between(self, a, b):
        ev = {}

        def add(d, colour, text):
            if a <= d <= b:
                ev.setdefault(d, []).append((colour, text))

        hols = self.ws.holidays()
        for d, name in hols.items():
            add(d, C["muted"], f"🎉 {name}")
        for key, sprints, plan in self.ws.plans():
            for sp in sprints:
                col = C["accent_dark"] if sp["kind"] == "Regression" else C["accent"]
                add(sp["start"], col, f"▶ {key} {sp['name']} starts")
                add(sp["end"], col, f"■ {key} {sp['name']} ends" + (" · regression" if sp["kind"] == "Regression" else ""))
            pd_ = parse_date((plan or {}).get("prod_date"))
            if pd_:
                add(pd_, C["amber"], f"🚀 {key} production")
        for m in self.d["meetings"]:
            d = parse_date(m.get("date"))
            if d:
                icon = "🎬" if m.get("type") == "Client demo" else "📅"
                e = parse_date(m.get("end_date")) or d
                while d <= e:
                    add(d, C["info"], f"{icon} {m.get('time') or ''} {m['title']}".replace("  ", " "))
                    d += dt.timedelta(days=1)
        for c in self.d["contracts"]:
            if c.get("status") in ("Expired", "Terminated"):
                continue
            act = self.contract_act_by(c)
            if act:
                add(act, C["lilac_ink"], f"⚖ Act by: {c['party']} {c.get('type', '')}")
            e = parse_date(c.get("end"))
            if e:
                add(e, C["lilac_ink"], f"⚖ {c['party']} {c.get('type', '')} ends")
        for lv in self.d["leave"]:
            s, e = parse_date(lv.get("from")), parse_date(lv.get("to"))
            if s and e:
                d = max(s, a)
                while d <= min(e, b):
                    if is_working_day(d, hols):
                        add(d, C["good"], f"🏖 {lv['person'].split(' ')[0]} – {lv.get('type', 'Leave')}")
                    d += dt.timedelta(days=1)
        for m in self.ws.team():
            r = parse_date(m.get("relieving"))
            if r:
                add(r, C["good"], f"👋 {m['name']} – last day")
        for x in self.d["tasks"]:
            d = parse_date(x.get("due"))
            if d and x.get("status") != "Done" and x.get("priority") == "High":
                add(d, C["bad"], f"✓ {x['title']}")
        return ev

    def refresh_calendar(self):
        if not hasattr(self, "cal_grid"):
            return
        for w in self.cal_grid.winfo_children():
            w.destroy()
        first = self.cal_month
        self.lbl_month.configure(text=first.strftime("%B %Y"))
        start = first - dt.timedelta(days=first.weekday())
        weeks = 6
        end = start + dt.timedelta(days=7 * weeks - 1)
        ev = self.events_between(start, end)
        hols = self.ws.holidays()
        for i, name in enumerate(("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")):
            tk.Label(self.cal_grid, text=name, bg=C["head_bg"], fg=C["muted"], font=FONTS["small_bold"]).grid(
                row=0, column=i, sticky="nsew", padx=(0, 1), pady=(0, 1))
        for k in range(7 * weeks):
            d = start + dt.timedelta(days=k)
            out_month = d.month != first.month
            bg = C["cell_off"] if (out_month or d.weekday() >= 5) else (C["cell_hol"] if d in hols else C["panel"])
            cell = tk.Frame(self.cal_grid, bg=bg, cursor="hand2",
                            highlightthickness=2 if d == today() else 0, highlightbackground=C["accent"])
            cell.grid(row=1 + k // 7, column=k % 7, sticky="nsew", padx=(0, 1), pady=(0, 1))
            num = tk.Label(cell, text=str(d.day), bg=bg, fg=C["accent"] if d == today() else
                           (C["soft_line"] if out_month else C["header"]), font=FONTS["small_bold"], anchor="w")
            num.pack(fill="x", padx=6, pady=(4, 0))
            widgets = [cell, num]
            items = ev.get(d, [])
            for colour, text in items[:4]:
                lb = tk.Label(cell, text=truncate(text, 24), bg=bg, fg=colour, font=FONTS["small"], anchor="w")
                lb.pack(fill="x", padx=6)
                widgets.append(lb)
            if len(items) > 4:
                lb = tk.Label(cell, text=f"+{len(items) - 4} more", bg=bg, fg=C["muted"], font=FONTS["small"],
                              anchor="w")
                lb.pack(fill="x", padx=6)
                widgets.append(lb)
            for w in widgets:
                w.bind("<Button-1>", lambda e, dd=d: self.cal_select(dd))
        for c in range(7):
            self.cal_grid.columnconfigure(c, weight=1, uniform="cal")
        for r in range(1, weeks + 1):
            self.cal_grid.rowconfigure(r, weight=1, uniform="calr")
        self._cal_ev = ev
        self.cal_select(self.cal_day if start <= self.cal_day <= end else first)

    def cal_select(self, d):
        self.cal_day = d
        for w in self.day_box.winfo_children():
            w.destroy()
        hols = self.ws.holidays()
        sub = "Holiday" if d in hols else ("Weekend" if d.weekday() >= 5 else "Working day")
        self.lbl_day.configure(text=f"{d.strftime('%A')}, {fmt_date(d, day=False)}\n{sub}")
        items = getattr(self, "_cal_ev", {}).get(d, [])
        if not items:
            tk.Label(self.day_box, text="Nothing planned.", bg=C["panel"], fg=C["muted"], font=FONTS["body"]).pack(
                anchor="w")
        for colour, text in items:
            tk.Label(self.day_box, text=text, bg=C["panel"], fg=colour, font=FONTS["body"], anchor="w",
                     justify="left", wraplength=270).pack(fill="x", pady=2)
        bb = tk.Frame(self.day_box, bg=C["panel"])
        bb.pack(fill="x", pady=(12, 0))
        ttk.Button(bb, text="➕ Meeting on this day",
                   command=lambda: (self.meeting_dialog(preset={"date": d.isoformat()}), self.refresh_calendar())
                   ).pack(anchor="w")

    # ----- Team availability ----------------------------------------------------------
    def build_team(self, f):
        self.view_header(f, "Team availability", "Leave, WFH and last days for the next two weeks, plus capacity for "
                                                 "the current sprint. The team list comes from the Workstation's Team "
                                                 "tab.", [("🗑 Delete", self.leave_delete, False),
                                                          ("✏ Edit", self.leave_edit, False),
                                                          ("➕ Add leave", self.leave_new, True)])
        self.team_grid = tk.Frame(f, bg=C["line"])
        self.team_grid.pack(fill="x")
        self.lbl_capacity = ttk.Label(f, text="", style="Muted.TLabel", wraplength=1200, justify="left")
        self.lbl_capacity.pack(anchor="w", pady=(10, 6))
        frm, self.tv_leave = make_table(f, [("from", "From", 150), ("to", "To", 150), ("type", "Type", 100),
                                            ("days", "Working days", 100), ("note", "Note", 300)], height=8,
                                        tree_col=("Person", 200))
        frm.pack(fill="both", expand=True)
        self.tv_leave.bind("<Double-1>", lambda e: self.leave_edit())

    def _team_names(self):
        names = [m["name"] for m in self.ws.team() if m.get("status", "Active") == "Active"]
        for lv in self.d["leave"]:
            if lv.get("person") and lv["person"] not in names:
                names.append(lv["person"])
        return names

    def _leave_on(self, person, d):
        for lv in self.d["leave"]:
            if lv.get("person") == person:
                a, b = parse_date(lv.get("from")), parse_date(lv.get("to"))
                if a and b and a <= d <= b:
                    return lv
        return None

    def _out_on(self, person, d):
        lv = self._leave_on(person, d)
        return lv.get("type", "Leave") if lv else None

    def refresh_team(self):
        if not hasattr(self, "team_grid"):
            return
        for w in self.team_grid.winfo_children():
            w.destroy()
        hols = self.ws.holidays()
        t = today()
        mon = t - dt.timedelta(days=t.weekday())
        days = [mon + dt.timedelta(days=i) for i in range(14) if (mon + dt.timedelta(days=i)).weekday() < 5]
        tk.Label(self.team_grid, text="Person", bg=C["head_bg"], fg=C["muted"], font=FONTS["small_bold"], anchor="w",
                 padx=8).grid(row=0, column=0, sticky="nsew", padx=(0, 1), pady=(0, 1))
        for j, d in enumerate(days):
            tk.Label(self.team_grid, text=d.strftime("%a\n%d %b"), bg=C["head_bg"], fg=C["accent"] if d == t else
                     C["muted"], font=FONTS["small_bold"]).grid(row=0, column=j + 1, sticky="nsew", padx=(0, 1),
                                                               pady=(0, 1))
        team = {m["name"]: m for m in self.ws.team()}
        names = self._team_names()
        if not names:
            tk.Label(self.team_grid, text="No team yet. Add people in the Workstation's Team tab, or add leave "
                                          "for anyone here.", bg=C["panel"], fg=C["muted"], padx=10, pady=10).grid(
                row=1, column=0, columnspan=len(days) + 1, sticky="nsew")
        for i, name in enumerate(names, 1):
            tk.Label(self.team_grid, text=name, bg=C["panel"], fg=C["ink"], anchor="w", padx=8,
                     font=FONTS["small"]).grid(row=i, column=0, sticky="nsew", padx=(0, 1), pady=(0, 1))
            rel = parse_date((team.get(name) or {}).get("relieving"))
            for j, d in enumerate(days):
                txt, bg, fg = "", C["panel"], C["ink"]
                if d in hols:
                    txt, bg, fg = "Holiday", C["cell_hol"], C["muted"]
                elif rel and d > rel:
                    txt, bg, fg = "—", C["cell_hol"], C["soft_line"]
                elif rel and d == rel:
                    txt, bg, fg = "👋 Last", C["soft"], C["accent"]
                else:
                    lv = self._leave_on(name, d)
                    kind = lv.get("type", "Leave") if lv else None
                    if kind:
                        txt = kind + leave_short(lv)
                        bg, fg = (C["blue_soft"], C["blue"]) if kind in ("WFH", "Training") else (C["sage_soft"], C["good"])
                tk.Label(self.team_grid, text=txt, bg=bg, fg=fg, font=FONTS["small"], width=8).grid(
                    row=i, column=j + 1, sticky="nsew", padx=(0, 1), pady=(0, 1))
        self.team_grid.columnconfigure(0, weight=2)
        for j in range(len(days)):
            self.team_grid.columnconfigure(j + 1, weight=1, uniform="tg")
        sp = self.ws.current_sprint()
        if sp:
            key, s = sp
            devs = [m for m in self.ws.team() if m.get("status", "Active") == "Active" and
                    "develop" in (m.get("designation") or "").lower()]
            total, lost, parts = 0, 0, []
            for m in devs:
                rel = parse_date(m.get("relieving"))
                d, avail, gone = max(s["start"], t), 0, 0
                while d <= s["end"]:
                    if is_working_day(d, hols):
                        lv = self._leave_on(m["name"], d)
                        if rel and d > rel:
                            gone += 1
                        elif lv and lv.get("type") != "WFH":
                            off = leave_fraction(lv)
                            gone += off
                            avail += 1 - off
                        else:
                            avail += 1
                    d += dt.timedelta(days=1)
                total += avail
                lost += gone
                if gone:
                    parts.append(f"{m['name'].split(' ')[0]} −{gone:g}")
            self.lbl_capacity.configure(text=f"🧮 Capacity for the rest of {key} · {s['name']} (ends "
                                             f"{fmt_date(s['end'], day=False)}): {total:g} developer-days available, "
                                             f"{lost:g} lost to leave / last days" +
                                             (f"  ({', '.join(parts)})" if parts else "") + ".")
        else:
            self.lbl_capacity.configure(text="🧮 Capacity shows here when the Workstation's Sprint Planner has a "
                                             "sprint running today.")
        tv = self.tv_leave
        tv.delete(*tv.get_children())
        for lv in sorted(self.d["leave"], key=lambda x: x.get("from") or "", reverse=True):
            a, b = parse_date(lv.get("from")), parse_date(lv.get("to"))
            tv.insert("", "end", iid=f"l{lv['id']}", text=lv.get("person", ""),
                      values=(fmt_date(a), fmt_date(b), lv.get("type", "") + leave_short(lv),
                              f"{count_working_days(a, b, hols) * leave_fraction(lv):g}",
                              lv.get("note", "")), tags=("muted",) if b and b < t else ())

    def leave_dialog(self, lv=None):
        fields = [("person", "Person", "combo", self._team_names() or self.people()),
                  ("from", "From", "date", None), ("to", "To", "date", None), ("type", "Type", "choice", LEAVE_TYPES),
                  ("part", "Day part", "choice", LEAVE_PARTS), ("note", "Note", "entry", None)]
        vals = form_dialog(self, "Edit leave" if lv else "Add leave", fields,
                           lv or {"from": today().isoformat(), "to": today().isoformat(), "type": "Leave",
                                  "part": "Full day"})
        if not vals or not vals.get("person") or not vals.get("from"):
            return None
        if not vals.get("to") or vals["to"] < vals["from"]:
            vals["to"] = vals["from"]
        if lv is None:
            lv = {"id": new_id(self.d["leave"])}
            self.d["leave"].append(lv)
        lv.update(vals)
        self.save()
        return lv

    def _sel_leave(self):
        sel = self.tv_leave.selection()
        return next((x for x in self.d["leave"] if sel and x["id"] == int(sel[0][1:])), None)

    def leave_new(self):
        if self.leave_dialog():
            self.refresh_team()
            self.refresh_cards()

    def leave_edit(self):
        lv = self._sel_leave()
        if lv and self.leave_dialog(lv):
            self.refresh_team()

    def leave_delete(self):
        lv = self._sel_leave()
        if lv and messagebox.askyesno(APP_NAME, f"Delete this leave for {lv['person']}?", parent=self):
            self.d["leave"] = [x for x in self.d["leave"] if x["id"] != lv["id"]]
            self.save()
            self.refresh_team()

    # ----- Quick links ------------------------------------------------------------------
    def _default_links(self):
        base = (self.ws.settings().get("base_url") or "").rstrip("/")
        links = []
        if base:
            links += [("Redmine – My page", f"{base}/my/page", "Redmine"),
                      ("Redmine – Issues", f"{base}/issues", "Redmine")]
        links += [("Outlook (web)", "https://outlook.office.com/mail/", "Microsoft 365"),
                  ("Outlook calendar", "https://outlook.office.com/calendar/", "Microsoft 365"),
                  ("Teams", "https://teams.microsoft.com/", "Microsoft 365"),
                  ("OneDrive", "https://www.office.com/onedrive", "Microsoft 365"),
                  ("Claude", "https://claude.ai/", "AI")]
        return [{"id": i + 1, "name": n, "url": u, "group": g} for i, (n, u, g) in enumerate(links)]

    def build_links(self, f):
        self.view_header(f, "Quick links", "Everything you open every day, one click away. Links can be websites or "
                                           "files/folders on your computer.",
                         [("🗑 Delete", self.link_delete, False), ("✏ Edit", self.link_edit, False),
                          ("➕ Add link", self.link_new, True)])
        if not self.d["links"]:
            self.d["links"] = self._default_links()
            self.save()
        self.links_box = tk.Frame(f, bg=C["bg"])
        self.links_box.pack(fill="both", expand=True)
        self._link_sel = None

    def refresh_links(self):
        if not hasattr(self, "links_box"):
            return
        for w in self.links_box.winfo_children():
            w.destroy()
        groups = {}
        for ln in self.d["links"]:
            groups.setdefault(ln.get("group") or "Other", []).append(ln)
        r = 0
        for g in sorted(groups, key=str.lower):
            tk.Label(self.links_box, text=g.upper(), bg=C["bg"], fg=C["accent"], font=FONTS["small_bold"]).grid(
                row=r, column=0, columnspan=4, sticky="w", pady=(10, 4))
            r += 1
            for i, ln in enumerate(groups[g]):
                sel = ln["id"] == self._link_sel
                card = tk.Frame(self.links_box, bg=C["soft"] if sel else C["panel"], highlightthickness=1,
                                highlightbackground=C["accent"] if sel else C["line"], cursor="hand2")
                card.grid(row=r + i // 4, column=i % 4, sticky="nsew", padx=(0, 8), pady=(0, 8))
                a = tk.Label(card, text="🔗 " + ln["name"], bg=card["bg"], fg=C["header"], font=FONTS["h3"],
                             anchor="w")
                a.pack(fill="x", padx=12, pady=(10, 0))
                b = tk.Label(card, text=truncate(ln["url"], 42), bg=card["bg"], fg=C["muted"], font=FONTS["small"],
                             anchor="w")
                b.pack(fill="x", padx=12, pady=(0, 10))
                for w in (card, a, b):
                    w.bind("<Button-1>", lambda e, x=ln: self.link_click(x))
                    w.bind("<Double-1>", lambda e, x=ln: self.link_open(x))
            r += (len(groups[g]) + 3) // 4
        for c in range(4):
            self.links_box.columnconfigure(c, weight=1, uniform="ql")
        tk.Label(self.links_box, text="Click once to select (for Edit / Delete) · double-click to open.",
                 bg=C["bg"], fg=C["muted"], font=FONTS["small"]).grid(row=r + 1, column=0, columnspan=4, sticky="w",
                                                                     pady=(8, 0))

    def link_click(self, ln):
        self._link_sel = ln["id"]
        self.refresh_links()

    def link_open(self, ln):
        url = ln["url"].strip().strip('"')
        try:
            if re.match(r"^(https?|mailto):", url):
                webbrowser.open(url)
            elif IS_WINDOWS:
                os.startfile(url)  # noqa
            else:
                subprocess.Popen(["xdg-open", url])
            self.set_status(f"Opening {ln['name']}…")
        except OSError as exc:
            messagebox.showerror(APP_NAME, f"Couldn't open it:\n{exc}", parent=self)

    def link_dialog(self, ln=None):
        groups = sorted({x.get("group") or "Other" for x in self.d["links"]})
        vals = form_dialog(self, "Edit link" if ln else "Add link",
                           [("name", "Name", "entry", None), ("url", "Website or file path", "entry", None),
                            ("group", "Group", "combo", groups)], ln or {"group": "Work"})
        if not vals or not vals.get("name") or not vals.get("url"):
            return
        if ln is None:
            ln = {"id": new_id(self.d["links"])}
            self.d["links"].append(ln)
        ln.update(vals)
        self.save()
        self.refresh_links()

    def _sel_link(self):
        return next((x for x in self.d["links"] if x["id"] == self._link_sel), None)

    def link_new(self):
        self.link_dialog()

    def link_edit(self):
        ln = self._sel_link()
        if ln:
            self.link_dialog(ln)
        else:
            messagebox.showinfo(APP_NAME, "Click a link once to select it first.", parent=self)

    def link_delete(self):
        ln = self._sel_link()
        if ln and messagebox.askyesno(APP_NAME, f"Delete the link '{ln['name']}'?", parent=self):
            self.d["links"] = [x for x in self.d["links"] if x["id"] != ln["id"]]
            self._link_sel = None
            self.save()
            self.refresh_links()

    # ----- Templates ------------------------------------------------------------------
    def build_templates(self, f):
        self.view_header(f, "Templates & snippets", "Messages you send again and again. Words in {curly brackets} are "
                                                    "filled in when you copy.",
                         [("🗑 Delete", self.tpl_delete, False), ("➕ New template", self.tpl_new, False),
                          ("📄 Fill in & copy", self.tpl_copy, True)])
        pw = ttk.PanedWindow(f, orient="horizontal")
        pw.pack(fill="both", expand=True)
        left = ttk.Frame(pw, style="Bg.TFrame")
        right = ttk.Frame(pw, style="Bg.TFrame", padding=(12, 0, 0, 0))
        pw.add(left, weight=2)
        pw.add(right, weight=5)
        frm, self.tv_tpl = make_table(left, [("category", "Category", 110)], height=18, tree_col=("Template", 220))
        frm.pack(fill="both", expand=True)
        self.tv_tpl.bind("<<TreeviewSelect>>", lambda e: self.tpl_show())
        row = ttk.Frame(right, style="Bg.TFrame")
        row.pack(fill="x")
        ttk.Label(row, text="Name").pack(side="left")
        self.var_tpl_name = tk.StringVar()
        ttk.Entry(row, textvariable=self.var_tpl_name, width=34).pack(side="left", padx=6)
        ttk.Label(row, text="Category").pack(side="left", padx=(10, 0))
        self.var_tpl_cat = tk.StringVar()
        ttk.Combobox(row, textvariable=self.var_tpl_cat, width=16,
                     values=["Follow-up", "Clients", "Legal", "Team", "Status", "Other"]).pack(side="left", padx=6)
        ttk.Button(row, text="💾 Save", command=self.tpl_save).pack(side="right")
        self.txt_tpl = make_text(right)
        self.txt_tpl.pack(fill="both", expand=True, pady=(8, 0))
        self._tpl_sel = None

    def refresh_templates(self):
        if not hasattr(self, "tv_tpl"):
            return
        tv = self.tv_tpl
        tv.delete(*tv.get_children())
        for x in sorted(self.d["templates"], key=lambda x: (x.get("category", ""), x["name"].lower())):
            tv.insert("", "end", iid=f"p{x['id']}", text=x["name"], values=(x.get("category", ""),))
        if self._tpl_sel and tv.exists(f"p{self._tpl_sel}"):
            tv.selection_set(f"p{self._tpl_sel}")
        elif tv.get_children():
            tv.selection_set(tv.get_children()[0])

    def _cur_tpl(self):
        return next((x for x in self.d["templates"] if x["id"] == self._tpl_sel), None)

    def tpl_show(self):
        sel = self.tv_tpl.selection()
        if not sel:
            return
        self._tpl_sel = int(sel[0][1:])
        x = self._cur_tpl()
        if x:
            self.var_tpl_name.set(x["name"])
            self.var_tpl_cat.set(x.get("category", ""))
            self.txt_tpl.delete("1.0", "end")
            self.txt_tpl.insert("1.0", x.get("text", ""))

    def tpl_save(self):
        x = self._cur_tpl()
        if not x:
            return
        x.update(name=self.var_tpl_name.get().strip() or x["name"], category=self.var_tpl_cat.get().strip(),
                 text=self.txt_tpl.get("1.0", "end").rstrip())
        self.save()
        self.refresh_templates()
        self.set_status("Template saved.")

    def tpl_new(self):
        name = simpledialog.askstring("New template", "Name of the template:", parent=self)
        if not name:
            return
        x = {"id": new_id(self.d["templates"]), "name": name.strip(), "category": "Other",
             "text": "Hi {name},\n\n\n\nThanks!\n" + self.d["settings"].get("your_name", "")}
        self.d["templates"].append(x)
        self._tpl_sel = x["id"]
        self.save()
        self.refresh_templates()

    def tpl_delete(self):
        x = self._cur_tpl()
        if x and messagebox.askyesno(APP_NAME, f"Delete the template '{x['name']}'?", parent=self):
            self.d["templates"] = [t for t in self.d["templates"] if t["id"] != x["id"]]
            self._tpl_sel = None
            self.save()
            self.refresh_templates()

    def tpl_copy(self):
        text = self.txt_tpl.get("1.0", "end").rstrip()
        if not text:
            return
        for key in dict.fromkeys(re.findall(r"\{(\w+)\}", text)):
            val = simpledialog.askstring("Fill in", f"{key.replace('_', ' ').capitalize()}:", parent=self)
            if val is None:
                return
            text = text.replace("{" + key + "}", val)
        self.clipboard_clear()
        self.clipboard_append(text)
        self.set_status("Copied. Paste it anywhere with Ctrl+V.")

    # ----- Focus & breaks -------------------------------------------------------------
    def build_focus(self, f):
        self.view_header(f, "Focus & breaks", "Work in calm blocks: focus, then a real break. I'll tell you when time's "
                                              "up.")
        box = tk.Frame(f, bg=C["panel"], highlightbackground=C["line"], highlightthickness=1)
        box.pack(fill="both", expand=True)
        self.lbl_focus_mode = tk.Label(box, text="Ready when you are", bg=C["panel"], fg=C["muted"], font=FONTS["h2"])
        self.lbl_focus_mode.pack(pady=(50, 0))
        self.lbl_timer = tk.Label(box, text="45:00", bg=C["panel"], fg=C["accent"], font=(FONTS["big"][0], 72, "bold"))
        self.lbl_timer.pack(pady=10)
        self.var_focus_what = tk.StringVar()
        row = tk.Frame(box, bg=C["panel"])
        row.pack()
        tk.Label(row, text="What are you focusing on?", bg=C["panel"], fg=C["ink"]).pack(side="left")
        ttk.Entry(row, textvariable=self.var_focus_what, width=40).pack(side="left", padx=8)
        bb = tk.Frame(box, bg=C["panel"])
        bb.pack(pady=18)
        s = self.d["settings"]
        ttk.Button(bb, text=f"🎯 Focus {s['focus_work']} min", style="Accent.TButton",
                   command=lambda: self.focus_start("focus")).pack(side="left", padx=4)
        ttk.Button(bb, text=f"☕ Break {s['focus_break']} min", command=lambda: self.focus_start("break")).pack(
            side="left", padx=4)
        ttk.Button(bb, text="25 min", command=lambda: self.focus_start("focus", 25)).pack(side="left", padx=4)
        ttk.Button(bb, text="■ Stop", command=self.focus_stop).pack(side="left", padx=4)
        self.lbl_focus_stats = tk.Label(box, text="", bg=C["panel"], fg=C["muted"], font=FONTS["body"])
        self.lbl_focus_stats.pack()
        tips = ("🌿 Stand up and stretch  ·  💧 Drink some water  ·  👀 Look 20 feet away for 20 seconds  ·  "
                "🚶 A short walk helps more than scrolling")
        tk.Label(box, text=tips, bg=C["panel"], fg=C["muted"], font=FONTS["small"]).pack(side="bottom", pady=20)
        self._focus = None

    def refresh_focus(self):
        f = self.d.get("focus") or {}
        n = f.get("sessions", 0) if f.get("date") == today().isoformat() else 0
        mins = f.get("minutes", 0) if f.get("date") == today().isoformat() else 0
        self.lbl_focus_stats.configure(text=f"Today: {plural(n, 'focus session')} · {mins} focused minutes")

    def focus_start(self, mode, minutes=None):
        s = self.d["settings"]
        minutes = minutes or int(s["focus_work"] if mode == "focus" else s["focus_break"])
        self._focus = {"mode": mode, "end": dt.datetime.now() + dt.timedelta(minutes=minutes), "minutes": minutes}
        what = self.var_focus_what.get().strip()
        self.lbl_focus_mode.configure(text=("🎯 Focusing" + (f" on: {what}" if what else "")) if mode == "focus"
                                      else "☕ Break time – step away from the screen", fg=C["header"])
        self._focus_tick()

    def focus_stop(self):
        self._focus = None
        self.lbl_focus_mode.configure(text="Ready when you are", fg=C["muted"])
        self.lbl_timer.configure(text=f"{int(self.d['settings']['focus_work']):02d}:00")

    def _focus_tick(self):
        if not self._focus:
            return
        left = (self._focus["end"] - dt.datetime.now()).total_seconds()
        if left <= 0:
            mode = self._focus["mode"]
            self._focus = None
            if mode == "focus":
                f = self.d.get("focus") or {}
                if f.get("date") != today().isoformat():
                    f = {"date": today().isoformat(), "sessions": 0, "minutes": 0}
                f["sessions"] += 1
                f["minutes"] += self._focus_minutes_done
                self.d["focus"] = f
                self.save()
                Toast(self, "🎯 Focus block done – well done!", ["Time for a short break: stretch, water, eyes off "
                                                                "the screen."],
                      [("Start break", lambda: (self.show("focus"), self.focus_start("break")))], C["good"])
            else:
                Toast(self, "☕ Break's over", ["Ready for the next focus block?"],
                      [("Start focus", lambda: (self.show("focus"), self.focus_start("focus")))], C["good"])
            self.focus_stop()
            if self.cur_view == "focus":
                self.refresh_focus()
            self.refresh_cards()
            return
        self._focus_minutes_done = self._focus["minutes"]
        m, s = divmod(int(left), 60)
        self.lbl_timer.configure(text=f"{m:02d}:{s:02d}")
        self.after(1000, self._focus_tick)

    # ----- Decks & Docs library -------------------------------------------------------
    LIB_CATEGORIES = ["Sales deck", "Product demo", "Proposal", "Case study", "Pricing", "Company profile",
                      "Training", "Other"]
    LIB_TYPES = ("*.pptx", "*.ppt", "*.pdf", "*.docx", "*.doc", "*.xlsx", "*.xls", "*.key", "*.mp4")

    def build_library(self, f):
        self.view_header(f, "Decks & Docs", "Your sales decks, proposals and documents in one place. Search also "
                                            "looks at the words inside your slides. Press Ctrl+K from anywhere.",
                         [("📁 Add a folder", self.lib_add_folder, False), ("➕ Add files", self.lib_add_files, True)])
        top = tk.Frame(f, bg=C["bg"])
        top.pack(fill="x", pady=(0, 8))
        self.var_lib_q = tk.StringVar()
        e = ttk.Entry(top, textvariable=self.var_lib_q, font=FONTS["h3"], style="Capture.TEntry")
        e.pack(side="left", fill="x", expand=True)
        e.bind("<Escape>", lambda ev: self.var_lib_q.set(""))
        self.var_lib_q.trace_add("write", lambda *a: self.refresh_library())
        self.lib_chips = tk.Frame(f, bg=C["bg"])
        self.lib_chips.pack(fill="x", pady=(0, 8))
        self.lib_filter = "All"
        body = tk.Frame(f, bg=C["bg"])
        body.pack(fill="both", expand=True)
        side = tk.Frame(body, bg=C["panel"], highlightbackground=C["line"], highlightthickness=1, width=340)
        side.pack(side="right", fill="y", padx=(12, 0))
        side.pack_propagate(False)
        self.lib_side = side
        holder = tk.Frame(body, bg=C["bg"])
        holder.pack(side="left", fill="both", expand=True)
        self.lib_canvas = tk.Canvas(holder, bg=C["bg"], highlightthickness=0)
        sb = ttk.Scrollbar(holder, orient="vertical", command=self.lib_canvas.yview)
        self.lib_canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.lib_canvas.pack(side="left", fill="both", expand=True)
        self.lib_grid = tk.Frame(self.lib_canvas, bg=C["bg"])
        win = self.lib_canvas.create_window((0, 0), window=self.lib_grid, anchor="nw")
        self.lib_canvas.bind("<Configure>", lambda ev: (self.lib_canvas.itemconfigure(win, width=ev.width),
                                                        self._lib_layout(ev.width)))
        self.lib_grid.bind("<Configure>", lambda ev: self.lib_canvas.configure(
            scrollregion=self.lib_canvas.bbox("all")))
        self.lib_canvas.bind_all("<MouseWheel>", self._lib_wheel, add="+")
        self._lib_sel, self._lib_cols, self._lib_wrap = None, 3, 200
        self.after(100, e.focus_set)

    def _lib_wheel(self, ev):
        if self.cur_view == "library" and hasattr(self, "lib_canvas"):
            self.lib_canvas.yview_scroll(int(-ev.delta / 120) or (-1 if ev.delta > 0 else 1), "units")

    def _lib_layout(self, width):
        cols = max(1, min(4, width // 250))
        wrap = max(120, width // cols - 50)
        if cols != self._lib_cols or abs(wrap - self._lib_wrap) > 20:
            self._lib_cols, self._lib_wrap = cols, wrap
            self.refresh_library()

    @staticmethod
    def lib_extract(path):
        """Read the words inside a .pptx/.docx/.xlsx so search can find them. Returns (text, slides)."""
        import html
        import zipfile
        p = Path(path)
        ext = p.suffix.lower()
        try:
            with zipfile.ZipFile(p) as z:
                names = z.namelist()
                if ext == ".pptx":
                    slides = sorted((n for n in names if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)),
                                    key=lambda n: int(re.findall(r"\d+", n)[-1]))
                    parts = []
                    for n in slides:
                        parts.append(" ".join(re.findall(r"<a:t>([^<]*)</a:t>", z.read(n).decode("utf-8", "ignore"))))
                    return html.unescape(" | ".join(parts))[:40000], len(slides)
                if ext == ".docx" and "word/document.xml" in names:
                    xml = z.read("word/document.xml").decode("utf-8", "ignore")
                    return html.unescape(" ".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", xml)))[:40000], 0
                if ext == ".xlsx" and "xl/sharedStrings.xml" in names:
                    xml = z.read("xl/sharedStrings.xml").decode("utf-8", "ignore")
                    return html.unescape(" ".join(re.findall(r"<t[^>]*>([^<]*)</t>", xml)))[:40000], 0
        except (OSError, zipfile.BadZipFile, KeyError, ValueError):
            pass
        return "", 0

    def _lib_index(self, item):
        p = Path(item["path"])
        try:
            m = p.stat().st_mtime
        except OSError:
            item["missing"] = True
            return
        item["missing"] = False
        if item.get("mtime") != m:
            item["text"], item["slides"] = self.lib_extract(p)
            item["mtime"] = m

    def _lib_add_paths(self, paths, ask_details=True):
        paths = [Path(p) for p in paths]
        known = {norm(x["path"]) for x in self.d["library"]}
        paths = [p for p in paths if norm(str(p)) not in known]
        if not paths:
            self.set_status("Those files are already in your library.")
            return
        details = {"category": "Sales deck", "tags": "", "copy": False}
        if ask_details:
            vals = form_dialog(self, f"Add {plural(len(paths), 'file')}", [
                ("category", "Category", "choice", self.LIB_CATEGORIES),
                ("tags", "Clients / tags (optional)", "combo", [c["name"] for c in self.d["clients"]]),
                ("copy", "Keep a copy", "check", "Keep a safe copy inside PO Home (leave unticked to always open "
                                                 "the latest version of the original)")], details)
            if vals is None:
                return
            details.update(vals)
        store = DATA_DIR / "Library"
        n = 0
        for p in paths:
            target = p
            if details.get("copy"):
                try:
                    store.mkdir(parents=True, exist_ok=True)
                    target = store / p.name
                    k = 1
                    while target.exists():
                        target = store / f"{p.stem} ({k}){p.suffix}"
                        k += 1
                    shutil.copy2(p, target)
                except OSError as exc:
                    self.set_status(f"Couldn't copy {p.name}: {exc}")
                    target = p
            item = {"id": new_id(self.d["library"]), "name": p.stem, "path": str(target),
                    "copied": target != p, "category": details["category"], "tags": details.get("tags", ""),
                    "notes": "", "added": today().isoformat(), "opened": "", "opens": 0, "fav": False}
            self._lib_index(item)
            self.d["library"].append(item)
            n += 1
        self.save()
        self.refresh_library()
        self.set_status(f"Added {plural(n, 'file')} to Decks & Docs.")

    def lib_add_files(self):
        paths = filedialog.askopenfilenames(parent=self, title="Choose your decks and documents", filetypes=[
            ("Presentations & documents", " ".join(self.LIB_TYPES)), ("All files", "*.*")])
        if paths:
            self._lib_add_paths(paths)

    def lib_add_folder(self):
        folder = filedialog.askdirectory(parent=self, title="Choose a folder with your decks")
        if not folder:
            return
        exts = {t[1:] for t in self.LIB_TYPES}
        found = []
        for root, _dirs, files in os.walk(folder):
            for fn in files:
                if Path(fn).suffix.lower() in exts and not fn.startswith("~$"):
                    found.append(Path(root) / fn)
            if len(found) > 400:
                break
        if not found:
            messagebox.showinfo(APP_NAME, "I didn't find any PowerPoint, PDF, Word or Excel files in that folder.",
                                parent=self)
            return
        self._lib_add_paths(found)

    def lib_matches(self, q):
        """(score, item, snippet) for items matching the search words, best first."""
        words = [w for w in norm(q).split() if w]
        out = []
        for x in self.d["library"]:
            hay_meta = norm(" ".join([x["name"], x.get("category", ""), x.get("tags", ""), x.get("notes", ""),
                                      Path(x["path"]).name]))
            hay_text = (x.get("text") or "").lower()
            score, snippet = 0, ""
            ok = True
            for w in words:
                if w in hay_meta:
                    score += 10
                elif w in hay_text:
                    score += 3
                    if not snippet:
                        i = hay_text.find(w)
                        snippet = "…" + (x.get("text") or "")[max(0, i - 60): i + 80].replace("|", "·") + "…"
                else:
                    ok = False
                    break
            if ok:
                score += (5 if x.get("fav") else 0) + min(5, x.get("opens", 0))
                out.append((score, x, snippet))
        out.sort(key=lambda r: (-r[0], -(parse_date(r[1].get("opened")) or dt.date(1970, 1, 1)).toordinal()))
        return out

    def refresh_library(self):
        if not hasattr(self, "lib_grid"):
            return
        for x in self.d["library"]:
            self._lib_index(x)
        # filter chips
        for w in self.lib_chips.winfo_children():
            w.destroy()
        cats = ["All", "★ Favourites", "Recently opened"] + sorted({x.get("category", "Other") for x in
                                                                   self.d["library"]})
        for c in cats:
            on = c == self.lib_filter
            ch = tk.Label(self.lib_chips, text=c, bg=C["accent"] if on else C["panel"],
                          fg=C["on_accent"] if on else C["ink"], font=FONTS["small_bold"], padx=12, pady=4,
                          cursor="hand2", highlightthickness=1, highlightbackground=C["line"])
            ch.pack(side="left", padx=(0, 6))
            ch.bind("<Button-1>", lambda e, cc=c: (setattr(self, "lib_filter", cc), self.refresh_library()))
        q = self.var_lib_q.get().strip()
        rows = self.lib_matches(q) if q else [(0, x, "") for x in sorted(
            self.d["library"], key=lambda x: (not x.get("fav"), x["name"].lower()))]
        if self.lib_filter == "★ Favourites":
            rows = [r for r in rows if r[1].get("fav")]
        elif self.lib_filter == "Recently opened":
            rows = sorted([r for r in rows if r[1].get("opened")], key=lambda r: r[1]["opened"], reverse=True)[:20]
        elif self.lib_filter != "All":
            rows = [r for r in rows if r[1].get("category") == self.lib_filter]
        self._lib_rows = rows
        for w in self.lib_grid.winfo_children():
            w.destroy()
        cols = self._lib_cols
        if not self.d["library"]:
            tk.Label(self.lib_grid, text="Your library is empty.\n\nClick '➕ Add files' to add your sales decks, "
                                         "proposals and documents,\nor '📁 Add a folder' to add a whole folder at once.",
                     bg=C["bg"], fg=C["muted"], font=FONTS["h3"], justify="center").grid(row=0, column=0, pady=80)
            self.lib_grid.columnconfigure(0, weight=1)
        elif not rows:
            tk.Label(self.lib_grid, text="Nothing matches. Try fewer words.", bg=C["bg"], fg=C["muted"],
                     font=FONTS["h3"]).grid(row=0, column=0, pady=60, sticky="w")
        for i, (_sc, x, snip) in enumerate(rows):
            self._lib_card(self.lib_grid, x, snip).grid(row=i // cols, column=i % cols, sticky="nsew", padx=(0, 10),
                                                        pady=(0, 10))
        for c in range(4):
            self.lib_grid.columnconfigure(c, weight=1 if c < cols else 0, uniform="lib" if c < cols else "")
        if rows and self._lib_sel not in {r[1]["id"] for r in rows}:
            self._lib_sel = rows[0][1]["id"]
        self._lib_detail()

    def _lib_icon(self, x):
        ext = Path(x["path"]).suffix.lower()
        return {".pptx": "📊", ".ppt": "📊", ".key": "📊", ".pdf": "📕", ".docx": "📄", ".doc": "📄",
                ".xlsx": "📈", ".xls": "📈", ".mp4": "🎞"}.get(ext, "📁")

    def _lib_card(self, parent, x, snip):
        sel = x["id"] == self._lib_sel
        bg = C["soft"] if sel else C["panel"]
        card = tk.Frame(parent, bg=bg, highlightthickness=1, highlightbackground=C["accent"] if sel else C["line"],
                        cursor="hand2")
        top = tk.Frame(card, bg=bg)
        top.pack(fill="x", padx=12, pady=(12, 0))
        tk.Label(top, text=self._lib_icon(x), bg=bg, font=(FONTS["icon"][0], 22)).pack(side="left")
        star = tk.Label(top, text="★" if x.get("fav") else "☆", bg=bg, fg=C["warn"] if x.get("fav") else C["faint"],
                        font=FONTS["h2"], cursor="hand2")
        star.pack(side="right")
        star.bind("<Button-1>", lambda e: self.lib_fav(x))
        name = tk.Label(card, text=x["name"], bg=bg, fg=C["header"], font=FONTS["h3"], anchor="w", justify="left",
                        wraplength=self._lib_wrap)
        name.pack(fill="x", padx=12, pady=(6, 0))
        bits = [x.get("category", "")]
        if x.get("slides"):
            bits.append(plural(x["slides"], "slide"))
        if x.get("tags"):
            bits.append(x["tags"])
        meta = tk.Label(card, text=" · ".join(b for b in bits if b), bg=bg, fg=C["muted"], font=FONTS["small"],
                        anchor="w", justify="left", wraplength=self._lib_wrap)
        meta.pack(fill="x", padx=12)
        foot = ("⚠ file not found" if x.get("missing") else
                (f"Opened {short_date(x['opened'])}" if x.get("opened") else "Not opened yet"))
        low = tk.Label(card, text=snip or foot, bg=bg, fg=C["bad"] if x.get("missing") else C["faint"],
                       font=FONTS["small"], anchor="w", justify="left", wraplength=self._lib_wrap)
        low.pack(fill="x", padx=12, pady=(4, 12))
        for w in (card, top, name, meta, low):
            w.bind("<Button-1>", lambda e: self._lib_select(x))
            w.bind("<Double-1>", lambda e: self.lib_open(x))
        return card

    def _lib_select(self, x):
        self._lib_sel = x["id"]
        self.refresh_library()

    def _lib_cur(self):
        return next((x for x in self.d["library"] if x["id"] == self._lib_sel), None)

    def _lib_detail(self):
        side = self.lib_side
        for w in side.winfo_children():
            w.destroy()
        x = self._lib_cur()
        if not x:
            tk.Label(side, text="Select a file to see its details.", bg=C["panel"], fg=C["muted"]).pack(padx=16,
                                                                                                     pady=20)
            return
        tk.Label(side, text=self._lib_icon(x), bg=C["panel"], font=(FONTS["icon"][0], 34)).pack(anchor="w", padx=16,
                                                                                               pady=(16, 0))
        tk.Label(side, text=x["name"], bg=C["panel"], fg=C["header"], font=FONTS["h2"], anchor="w", justify="left",
                 wraplength=300).pack(fill="x", padx=16)
        info = [("Category", x.get("category", "")), ("Clients / tags", x.get("tags") or "—"),
                ("Slides", str(x["slides"]) if x.get("slides") else "—"),
                ("Added", fmt_date(x.get("added"), day=False)),
                ("Last opened", fmt_date(x.get("opened"), day=False) if x.get("opened") else "never"),
                ("Stored", "copy inside PO Home" if x.get("copied") else "your original file"),
                ("Location", x["path"])]
        for k, v in info:
            r = tk.Frame(side, bg=C["panel"])
            r.pack(fill="x", padx=16, pady=1)
            tk.Label(r, text=k, bg=C["panel"], fg=C["muted"], font=FONTS["small"], width=12, anchor="nw").pack(
                side="left", anchor="n")
            tk.Label(r, text=v, bg=C["panel"], fg=C["bad"] if k == "Location" and x.get("missing") else C["ink"],
                     font=FONTS["small"], anchor="w", justify="left", wraplength=200).pack(side="left", fill="x")
        if x.get("notes"):
            tk.Label(side, text=x["notes"], bg=C["panel"], fg=C["ink"], font=FONTS["small"], anchor="w",
                     justify="left", wraplength=300).pack(fill="x", padx=16, pady=(8, 0))
        if x.get("text"):
            first = x["text"].split("|")[0].strip()
            if first:
                tk.Label(side, text=f"First slide: “{truncate(first, 120)}”", bg=C["panel"], fg=C["muted"],
                         font=FONTS["small"], anchor="w", justify="left", wraplength=300).pack(fill="x", padx=16,
                                                                                              pady=(8, 0))
        bb = tk.Frame(side, bg=C["panel"])
        bb.pack(fill="x", padx=16, pady=14)
        ttk.Button(bb, text="▶ Open", style="Accent.TButton", command=lambda: self.lib_open(x)).pack(fill="x")
        for text, cmd in (("📂 Show in folder", lambda: self.lib_folder(x)), ("📋 Copy file path", lambda: self.lib_copy(x)),
                          ("★ Unfavourite" if x.get("fav") else "☆ Favourite", lambda: self.lib_fav(x)),
                          ("✏ Edit details", lambda: self.lib_edit(x)), ("🗑 Remove from library", lambda: self.lib_remove(x))):
            ttk.Button(bb, text=text, command=cmd).pack(fill="x", pady=(6, 0))

    def _relink(self, x):
        if not messagebox.askyesno(APP_NAME, f"I can't find '{Path(x['path']).name}'. It may have been moved or "
                                             f"renamed.\n\nDo you want to point me to it?", parent=self):
            return False
        p = filedialog.askopenfilename(parent=self, title=f"Where is {x['name']}?")
        if not p:
            return False
        x["path"] = p
        x["mtime"] = None
        self._lib_index(x)
        self.save()
        return True

    def lib_open(self, x):
        if not Path(x["path"]).exists() and not self._relink(x):
            return
        try:
            if IS_WINDOWS:
                os.startfile(x["path"])  # noqa
            else:
                subprocess.Popen(["xdg-open", x["path"]])
        except OSError as exc:
            messagebox.showerror(APP_NAME, f"Couldn't open it:\n{exc}", parent=self)
            return
        x["opened"] = today().isoformat()
        x["opens"] = x.get("opens", 0) + 1
        self.save()
        self.set_status(f"Opening {x['name']}…")
        if self.cur_view == "library":
            self.refresh_library()

    def lib_folder(self, x):
        p = Path(x["path"])
        if not p.exists() and not self._relink(x):
            return
        p = Path(x["path"])
        try:
            if IS_WINDOWS:
                subprocess.Popen(["explorer", "/select,", str(p)])
            else:
                subprocess.Popen(["xdg-open", str(p.parent)])
        except OSError as exc:
            messagebox.showerror(APP_NAME, f"Couldn't open the folder:\n{exc}", parent=self)

    def lib_copy(self, x):
        self.clipboard_clear()
        self.clipboard_append(x["path"])
        self.set_status("File path copied. In Outlook, click Attach → Browse and paste it (Ctrl+V) into the "
                        "file name box.")

    def lib_fav(self, x):
        x["fav"] = not x.get("fav")
        self.save()
        self.refresh_library()

    def lib_edit(self, x):
        vals = form_dialog(self, "Edit details", [("name", "Name", "entry", None),
                                                  ("category", "Category", "choice", self.LIB_CATEGORIES),
                                                  ("tags", "Clients / tags", "combo",
                                                   [c["name"] for c in self.d["clients"]]),
                                                  ("notes", "Notes (when to use it…)", "text", 4)], x)
        if vals:
            x.update(vals)
            self.save()
            self.refresh_library()

    def lib_remove(self, x):
        extra = "\n\nThe copy kept inside PO Home will also be deleted." if x.get("copied") else \
            "\n\nYour original file is NOT deleted."
        if not messagebox.askyesno(APP_NAME, f"Remove '{x['name']}' from the library?{extra}", parent=self):
            return
        if x.get("copied"):
            try:
                Path(x["path"]).unlink()
            except OSError:
                pass
        self.d["library"] = [i for i in self.d["library"] if i["id"] != x["id"]]
        self._lib_sel = None
        self.save()
        self.refresh_library()

    def quick_find(self):
        """Ctrl+K: type a few letters, press Enter to open a deck or link."""
        win = tk.Toplevel(self)
        win.title("Find a deck or link")
        win.configure(bg=C["bg"])
        win.transient(self)
        frm = ttk.Frame(win, padding=16, style="Bg.TFrame")
        frm.pack(fill="both", expand=True)
        ttk.Label(frm, text="🔎 Find a deck, document or link", style="H2.TLabel").pack(anchor="w")
        var = tk.StringVar()
        e = ttk.Entry(frm, textvariable=var, font=FONTS["h3"], style="Capture.TEntry", width=60)
        e.pack(fill="x", pady=(8, 8))
        lb = tk.Listbox(frm, height=12, font=FONTS["body"], bg=C["field"], fg=C["ink"], relief="flat",
                        highlightthickness=1, highlightbackground=C["line"], selectbackground=C["select"],
                        selectforeground=C["ink"], activestyle="none")
        lb.pack(fill="both", expand=True)
        hint = ttk.Label(frm, text="↑ ↓ to choose · Enter to open · Esc to close", style="Muted.TLabel")
        hint.pack(anchor="w", pady=(6, 0))
        results = []

        def update(*_):
            results.clear()
            q = var.get().strip()
            if q:
                results.extend(("lib", x) for _s, x, _sn in self.lib_matches(q)[:12])
                words = norm(q).split()
                results.extend(("link", ln) for ln in self.d["links"]
                               if all(w in norm(ln["name"] + " " + ln.get("group", "")) for w in words))
            else:
                recent = sorted((x for x in self.d["library"] if x.get("opened") or x.get("fav")),
                                key=lambda x: (not x.get("fav"), x.get("opened") or ""), reverse=False)[:10]
                results.extend(("lib", x) for x in recent)
            lb.delete(0, "end")
            for kind, x in results[:16]:
                if kind == "lib":
                    lb.insert("end", f"  {self._lib_icon(x)}  {x['name']}    ·  {x.get('category', '')}"
                                     + ("  ★" if x.get("fav") else ""))
                else:
                    lb.insert("end", f"  🔗  {x['name']}    ·  {x.get('group', 'link')}")
            if results:
                lb.selection_set(0)
            elif not self.d["library"]:
                lb.insert("end", "  Your library is empty. Open 'Decks & Docs' to add files.")

        def go(_e=None):
            sel = lb.curselection()
            if not sel or sel[0] >= len(results):
                return
            kind, x = results[sel[0]]
            win.destroy()
            if kind == "lib":
                self.lib_open(x)
            else:
                self.link_open(x)

        def move(step):
            if not results:
                return "break"
            cur = (lb.curselection() or (0,))[0]
            nxt = max(0, min(min(len(results), 16) - 1, cur + step))
            lb.selection_clear(0, "end")
            lb.selection_set(nxt)
            lb.see(nxt)
            return "break"

        var.trace_add("write", update)
        e.bind("<Return>", go)
        e.bind("<Down>", lambda ev: move(1))
        e.bind("<Up>", lambda ev: move(-1))
        lb.bind("<Double-1>", go)
        win.bind("<Escape>", lambda ev: win.destroy())
        update()
        center_on(win, self)
        e.focus_set()

    # ----- Settings -------------------------------------------------------------------
    def settings_dialog(self):
        s = self.d["settings"]
        fields = [("your_name", "Your name", "entry", None), ("work_start", "Work starts", "time", None),
                  ("work_end", "Work ends", "time", None), ("wrap_time", "End-of-day wrap-up at", "time", None),
                  ("nudge_days", "Nudge me after (days waiting)", "entry", None),
                  ("demo_prep_days", "Demo prep task (working days before)", "entry", None),
                  ("focus_work", "Focus block (minutes)", "entry", None),
                  ("focus_break", "Break (minutes)", "entry", None),
                  ("workstation_path", "Redmine Workstation file", "entry", None),
                  ("theme", "Look", "choice", ["light", "dark"]),
                  ("auto_followup", "Client meetings", "check",
                   "Add a 'send follow-up' task after every client meeting or demo"),
                  ("autostart", "Start", "check", "Start PO Home when Windows starts"),
                  ("close_to_background", "Close button", "check",
                   "Keep running in the background (so reminders still work)")]
        vals = form_dialog(self, "Settings", fields, dict(s, workstation_path=s.get("workstation_path") or
                                                          str(self.ws.path)))
        if not vals:
            return
        for k in ("nudge_days", "demo_prep_days", "focus_work", "focus_break"):
            try:
                vals[k] = max(1, int(str(vals[k]).strip()))
            except ValueError:
                vals[k] = s.get(k)
        if vals.get("workstation_path") == str(HERE / "redmine_workstation.py"):
            vals["workstation_path"] = ""
        theme_changed = vals.get("theme") != s.get("theme")
        s.update(vals)
        self.save()
        self._ensure_autostart()
        if theme_changed:
            self.apply_theme()
        elif self.cur_view == "home":
            self.refresh_home()
        self.set_status("Settings saved.")

    # ----- Reminders ------------------------------------------------------------------
    def in_hours(self, now=None):
        now = now or dt.datetime.now()
        s = self.d["settings"]
        if not is_working_day(now.date(), self.ws.holidays()):
            return False
        hm = now.strftime("%H:%M")
        return (s.get("work_start") or "10:00") <= hm < (s.get("work_end") or "20:00")

    def _flag(self, name, value=None):
        if value is None:
            return self.d["flags"].get(name)
        self.d["flags"][name] = value
        self.save()

    def tick(self):
        try:
            if self.cur_view == "home" and self.state() != "iconic" and not Toast.stack:
                self.refresh_home()
            self._tick()
        except Exception as exc:  # never let a reminder crash the app
            self.set_status(f"Reminder check hit a problem: {exc}")
        self.after(30_000, self.tick)

    def _tick(self):
        now = dt.datetime.now()
        t = now.date()
        hm = now.strftime("%H:%M")
        s = self.d["settings"]
        hols = self.ws.holidays()
        working = self.in_hours(now)
        if self._flag("series_day") != t.isoformat():
            self._flag("series_day", t.isoformat())
            self.expand_series()
        # Meetings: 10 minutes before (any time – you put them there), demos the working day before.
        for m in self.d["meetings"]:
            d, tm = parse_date(m.get("date")), parse_time(m.get("time") or "")
            e = parse_date(m.get("end_date")) or d
            done_today = m.get("reminded") == t.isoformat() or (m.get("reminded") is True and e == d)
            if d and e and d <= t <= e and tm and not done_today:
                start = dt.datetime.combine(t, dt.time(int(tm[:2]), int(tm[3:])))
                if start - dt.timedelta(minutes=10) <= now < start + dt.timedelta(minutes=5):
                    m["reminded"] = t.isoformat() if e != d else True
                    self.save()
                    lines = [f"{tm} · {m.get('type', '')}" + (f" · {m['client']}" if m.get("client") else "")]
                    if m.get("agenda"):
                        lines.append(truncate(m["agenda"], 160))
                    Toast(self, f"📅 Starting soon: {m['title']}", lines,
                          [("Open notes", lambda mm=m: self._open_meeting(mm))], C["info"])
            if m.get("type") == "Client demo" and d and working and not m.get("reminded_day") and \
                    next_working_day(t + dt.timedelta(days=1), hols) == d:
                m["reminded_day"] = True
                self.save()
                left = [k for k in DEMO_CHECKLIST if not (m.get("checklist") or {}).get(k)]
                Toast(self, f"🎬 Demo {short_date(d).lower()}: {m['title']}",
                      [f"{len(DEMO_CHECKLIST) - len(left)}/{len(DEMO_CHECKLIST)} prep items ready."] +
                      [f"○ {k}" for k in left[:4]], [("Open checklist", lambda: self.show("clients"))], C["info"])
        if not working:
            return
        # Morning summary (first time you're here each working day)
        if self._flag("morning") != t.isoformat():
            self._flag("morning", t.isoformat())
            self.morning_summary()
            return
        # Timed task reminders
        for x in self.d["tasks"]:
            if x.get("status") == "Done" or x.get("reminded"):
                continue
            d, tm = parse_date(x.get("due")), parse_time(x.get("time") or "")
            if d and tm and (d < t or (d == t and tm <= hm)):
                x["reminded"] = True
                self.save()
                Toast(self, f"⏰ {x['title']}", [f"Due {short_date(d)} {tm}" + (f" · {x['person']}"
                                                                                 if x.get("person") else "")],
                      [("Done ✔", lambda xx=x: (self.complete_task(xx), self._refresh_open())),
                       ("Snooze 15 min", lambda xx=x: self._snooze(xx, 15))])
        # Waiting-on-others nudges (once a day, an hour after you start)
        start = parse_time(s.get("work_start") or "10:00") or "10:00"
        after = (dt.datetime.combine(t, dt.time(int(start[:2]), int(start[3:]))) + dt.timedelta(hours=1)).strftime(
            "%H:%M")
        if hm >= after and self._flag("nudges") != t.isoformat():
            self._flag("nudges", t.isoformat())
            old = [x for x in self.d["tasks"] if x.get("status") == "Waiting" and x.get("waiting_since") and
                   (t - parse_date(x["waiting_since"])).days >= int(s.get("nudge_days", 3))]
            if old:
                Toast(self, f"⏳ {plural(len(old), 'thing')} you're waiting on",
                      [f"• {x.get('person') or 'Someone'}: {truncate(x['title'], 50)} "
                       f"({(t - parse_date(x['waiting_since'])).days} days)" for x in old[:5]],
                      [("See them", lambda: self._open_pa("Waiting on others"))], C["warn"])
        # Contracts: 60 / 30 / 14 / 7 days before act-by
        for c in self.d["contracts"]:
            if c.get("status") in ("Expired", "Terminated"):
                continue
            a = self.contract_act_by(c)
            if not a:
                continue
            left = (a - t).days
            sent = set(c.get("alerted") or [])
            due = [th for th in (60, 30, 14, 7, 0) if left <= th and th not in sent]
            if due:
                c["alerted"] = sorted(sent | {th for th in (60, 30, 14, 7, 0) if left <= th})
                self.save()
                Toast(self, f"⚖ {c['party']} {c.get('type', '')}: act by {fmt_date(a, day=False)}",
                      [("Overdue! " if left < 0 else f"{left} days left. ") +
                       "Decide whether to renew, renegotiate or give notice."],
                      [("Open contracts", lambda: self.show("legal"))], C["lilac_ink"])
        # End-of-day wrap-up
        if hm >= (s.get("wrap_time") or "19:30") and self._flag("wrap") != t.isoformat():
            self._flag("wrap", t.isoformat())
            self.wrap_up()
        # Friday weekly review
        wk = f"{t.isocalendar()[0]}-W{t.isocalendar()[1]}"
        if t.weekday() == 4 and hm >= "17:00" and self._flag("weekly") != wk:
            self._flag("weekly", wk)
            mon = t - dt.timedelta(days=t.weekday())
            done = sum(1 for x in self.d["tasks"] if x.get("status") == "Done" and parse_date(x.get("done_at")) and
                       parse_date(x["done_at"]) >= mon)
            nxt = [x for x in self.d["tasks"] if x.get("status") != "Done" and parse_date(x.get("due")) and
                   parse_date(x["due"]) <= t + dt.timedelta(days=7)]
            Toast(self, "🌟 Weekly review", [f"You finished {plural(done, 'task')} this week. Nice work!",
                                             f"{plural(len(nxt), 'task')} lined up for next week."],
                  [("Plan next week", lambda: self._open_pa("Next 7 days"))], C["good"])

    def _snooze(self, x, minutes):
        when = dt.datetime.now() + dt.timedelta(minutes=minutes)
        x["due"] = when.date().isoformat()
        x["time"] = when.strftime("%H:%M")
        x["reminded"] = False
        self.save()

    def _refresh_open(self):
        if self.cur_view == "home":
            self.refresh_home()
        if self.cur_view == "pa":
            self.refresh_pa()

    def _open_pa(self, view=None):
        self.bring_to_front()
        self.show("pa")
        if view:
            self.pa_view.set(view)
            self.refresh_pa()

    def _open_meeting(self, m):
        self.bring_to_front()
        self.show("pa")
        self._select_meeting(m["id"])

    def morning_summary(self):
        top, mine, meetings, ws_items, alerts = self.plate_data()
        t = today()
        overdue = [x for x in mine if parse_date(x["due"]) < t]
        lines = [f"{plural(len(mine) - len(overdue), 'task')} due today" +
                 (f", {len(overdue)} overdue" if overdue else "") + f" · {plural(len(meetings), 'meeting')}"]
        for m in meetings[:3]:
            lines.append(f"📅 {m.get('time') or '--:--'}  {truncate(m['title'], 44)}")
        for i, x in enumerate(top, 1):
            lines.append(f"{i}. {truncate(x['title'], 50)}")
        for _, text, _ in (ws_items + alerts)[:2]:
            lines.append(f"🔔 {truncate(text, 60)}")
        h = dt.datetime.now().hour
        hello = "Good morning" if h < 12 else ("Good afternoon" if h < 17 else "Good evening")
        Toast(self, f"☀ {hello}, {self.d['settings'].get('your_name', '')}! Here's your plate", lines,
              [("Open My PA", lambda: self._open_pa("☀ My day"))])

    def wrap_up(self):
        t = today()
        left = [x for x in self.d["tasks"] if x.get("status") != "Done" and parse_date(x.get("due")) and
                parse_date(x["due"]) <= t and x.get("status") != "Waiting"]
        done = sum(1 for x in self.d["tasks"] if x.get("done_at") == t.isoformat())
        if not left:
            Toast(self, "🌙 All done for today!", [f"You finished {plural(done, 'task')}. Time to switch off. 🌿"],
                  colour=C["good"])
            return

        def move():
            nxt = next_working_day(t + dt.timedelta(days=1), self.ws.holidays())
            for x in left:
                x["due"] = nxt.isoformat()
                x["reminded"] = False
            self.save()
            self._refresh_open()
            self.set_status(f"Moved {plural(len(left), 'task')} to {fmt_date(nxt)}.")

        Toast(self, "🌙 Wrapping up the day", [f"Done today: {done}. Still open: {len(left)}."] +
              [f"○ {truncate(x['title'], 50)}" for x in left[:4]],
              [("Move all to next working day", move), ("Review", lambda: self._open_pa("☀ My day"))])

    # ----- Start with Windows, close & quit ---------------------------------------------
    def _startup_file(self):
        appdata = os.environ.get("APPDATA")
        if not IS_WINDOWS or not appdata:
            return None
        return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / "PO Home.vbs"

    def _ensure_autostart(self):
        f = self._startup_file()
        if not f:
            return
        try:
            if self.d["settings"].get("autostart"):
                exe = Path(sys.executable)
                pyw = exe.with_name("pythonw.exe")
                runner = pyw if pyw.exists() else exe
                script = Path(__file__).resolve()
                vbs = ('Set sh = CreateObject("WScript.Shell")\r\n'
                       f'sh.CurrentDirectory = "{script.parent}"\r\n'
                       f'sh.Run """{runner}"" ""{script}"" --background", 1, False\r\n')
                if not f.exists() or f.read_text(encoding="utf-8", errors="ignore") != vbs:
                    f.parent.mkdir(parents=True, exist_ok=True)
                    f.write_text(vbs, encoding="utf-8")
            elif f.exists():
                f.unlink()
        except OSError as exc:
            self.set_status(f"Couldn't set up 'start with Windows': {exc}")

    def _on_close(self):
        if not self.d["settings"].get("close_to_background", True):
            self.quit_app(ask=False)
            return
        if not self._flag("told_background"):
            self._flag("told_background", True)
            messagebox.showinfo(APP_NAME, "PO Home will keep running in the background so it can remind you.\n\n"
                                          "It's minimised to your taskbar. To close it completely, use ⏻ Quit at the "
                                          "top right.", parent=self)
        if hasattr(self, "txt_notes"):
            self._store_detail()
        self.iconify()

    def quit_app(self, ask=True):
        if ask and not messagebox.askyesno(APP_NAME, "Quit PO Home?\n\nReminders stop until you open it again.",
                                           parent=self):
            return
        if hasattr(self, "txt_notes"):
            self._store_detail()
        self.save()
        self.destroy()


# --------------------------------------------------------------------------
# One copy at a time
# --------------------------------------------------------------------------
def already_running() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", SINGLE_PORT), timeout=0.6) as s:
            s.sendall(b"SHOW")
        return True
    except OSError:
        return False


def listen_for_others(app):
    try:
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if not IS_WINDOWS:
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("127.0.0.1", SINGLE_PORT))
        srv.listen(2)
    except OSError:
        return

    def loop():
        while True:
            try:
                conn, _ = srv.accept()
                with conn:
                    if conn.recv(16).startswith(b"SHOW"):
                        app._queue.put(("SHOW", None, None))
            except OSError:
                break

    threading.Thread(target=loop, daemon=True).start()


def hide_console():
    """If Windows opened a black console window just for PO Home (double-clicking the .py file), hide it.
    A terminal you opened yourself (VS Code, PowerShell) is left alone."""
    if not IS_WINDOWS:
        return
    try:
        import ctypes
        k32 = ctypes.windll.kernel32
        hwnd = k32.GetConsoleWindow()
        if not hwnd:
            return
        procs = (ctypes.c_uint * 8)()
        if k32.GetConsoleProcessList(procs, 8) <= 2:
            ctypes.windll.user32.ShowWindow(hwnd, 0)
    except (AttributeError, OSError):
        pass


def main():
    if already_running():
        return
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    app = POHome()
    hide_console()
    listen_for_others(app)
    if "--background" in sys.argv:
        app.after(400, app.iconify)
    app.mainloop()


if __name__ == "__main__":
    main()
