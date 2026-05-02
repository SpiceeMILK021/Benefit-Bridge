

# Lets us use newer type-hint styles (like `list[str]`) on older Python.
from __future__ import annotations

# Tools we use throughout the file:
import csv          # for saving the case history spreadsheet
import json         # for saving/loading settings and drafts
import html         # for escaping applicant names in generated HTML
import math         # for math like square roots and rounding
import re           # for finding patterns in text (like a 5-digit ZIP)
import sys          # to check what operating system we're on
import uuid         # to make a random session ID
import webbrowser   # to open Google Maps in the browser
import os           # for checking if files exist and making folders

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None


# A shortcut for making simple "record" classes.
from dataclasses import dataclass
# For getting the current date and time.
from datetime import datetime
# Lets us make a function that already has some arguments filled in.
from functools import partial
# A nicer way to work with file paths.
from pathlib import Path
# Turns text like "123 Main St" into a URL-safe form.
from urllib.parse import quote_plus

# Tkinter = Python's built-in tool for making windows and buttons.
from tkinter import filedialog, messagebox, ttk   # save dialogs, popups, fancy widgets
from tkinter import font as tkfont                # for working with fonts
import tkinter as tk                              # the main tkinter module


# ===========================================================================
# FILE STRUCTURE OVERVIEW
# ---------------------------------------------------------------------------
# 1) Application file paths and local storage
# 2) Program metadata, sample income limits, and state rules
# 3) Office location data and ZIP/city coordinate helpers
# 4) UI choice lists and theme constants
# 5) Runtime helpers, dataclasses, and widget utilities
# 6) Persistence, eligibility rules, and location search
# 7) Draft export builder and main Tkinter app class
# ===========================================================================



# ===========================================================================
# SECTION 1 — APPLICATION FILES AND STORAGE
# ---------------------------------------------------------------------------
# File paths and file names used for settings, drafts, exports, and history.
# ===========================================================================
# The folder this script lives in. Everything we save goes here.
# ===========================================================================
# SECTION 1 — APPLICATION FILES AND STORAGE
# ---------------------------------------------------------------------------

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

# This makes the app find your logo on ANY computer
APP_DIR = Path(resource_path("."))
BRAND_LOGO_PATH = Path(resource_path("benefit_bridge_logo.png"))

# This fixes the "not defined" error by giving the code the list it's looking for
BRAND_LOGO_CANDIDATES = [BRAND_LOGO_PATH]

# These stay the same
CASE_HISTORY_FILE = APP_DIR / "benefit_bridge_case_history.csv"
SETTINGS_FILE = APP_DIR / "benefit_bridge_settings.json"
DRAFT_FILE = APP_DIR / "benefit_bridge_draft.json"
EXPORT_DIR = APP_DIR / "exports"
BRAND_SLOGAN = "You're Closer Than You Think"


# The five programs the app knows about. Each one has:
#   - "name": full title shown to the user
#   - "short_name": short tag used in lists and pills
#   - "description": one-line explanation
#   - "color": accent color for the swatch next to the checkbox
PROGRAMS = {
    "childcare": {
        "name": "Child-care subsidy",
        "short_name": "Child care",
        "description": "Help paying for licensed care while a parent works or studies.",
        "color": "#14b8a6",
    },
    "food": {
        "name": "Food assistance / SNAP-like program",
        "short_name": "Food",
        "description": "Monthly grocery support for households under income limits.",
        "color": "#3b82f6",
    },
    "utility": {
        "name": "Utility bill help",
        "short_name": "Utilities",
        "description": "Energy, water, or emergency bill support.",
        "color": "#f97316",
    },
    "internet": {
        "name": "Internet subsidy",
        "short_name": "Internet",
        "description": "Low-cost internet or digital access support.",
        "color": "#8b5cf6",
    },
    "transportation": {
        "name": "Other: transportation vouchers",
        "short_name": "Transport",
        "description": "Transit passes or rides for work, school, or medical needs.",
        "color": "#f43f5e",
    },
}

# Income limits for child care, by household size (1 person = $4,300/month, etc.).
# These are sample numbers — not real government limits.
CHILDCARE_LIMITS = {
    1: 4300,
    2: 5600,
    3: 6900,
    4: 8200,
    5: 9500,
    6: 10800,
    7: 12100,
    8: 13400,
}

# Income limits for food and internet (based on 200% of the federal poverty line).
FPL_200_LIMITS = {
    1: 2510,
    2: 3407,
    3: 4303,
    4: 5200,
    5: 6097,
    6: 6993,
    7: 7890,
    8: 8787,
}

# Income limits for utility help, by household size.
UTILITY_LIMITS = {
    1: 2950,
    2: 3860,
    3: 4770,
    4: 5680,
    5: 6590,
    6: 7500,
    7: 8410,
    8: 9320,
}

# Income limits for transportation vouchers, by household size.
TRANSPORTATION_LIMITS = {
    1: 2200,
    2: 2980,
    3: 3760,
    4: 4550,
    5: 5330,
    6: 6120,
    7: 6900,
    8: 7690,
}

# State-specific income limits (monthly gross income). Each state has its own set of
# limits for each program. Food and internet use 200% FPL (federal, uniform).
# Childcare limits approximate CCDF eligibility (85% of state median income).
# Utility limits approximate LIHEAP eligibility (150-200% FPL or 60% SMI).
# Transportation limits approximate state transit-assistance program thresholds.
STATE_LIMITS = {
    "Alabama": {
        "childcare":      {1: 3300, 2: 4400, 3: 5500, 4: 6600, 5: 7700, 6: 8800, 7: 9900,  8: 11000},
        "food":           FPL_200_LIMITS,
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 2510, 2: 3407, 3: 4303, 4: 5200, 5: 6097, 6: 6993, 7: 7890,  8: 8787},
        "transportation": {1: 1900, 2: 2600, 3: 3300, 4: 4000, 5: 4700, 6: 5400, 7: 6100,  8: 6800},
    },
    "Alaska": {
        "childcare":      {1: 5100, 2: 6700, 3: 8300, 4: 9900, 5: 11500, 6: 13100, 7: 14700, 8: 16300},
        "food":           FPL_200_LIMITS,
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 4200, 2: 5600, 3: 7000, 4: 8400, 5: 9800,  6: 11200, 7: 12600, 8: 14000},
        "transportation": {1: 2800, 2: 3800, 3: 4800, 4: 5800, 5: 6800,  6: 7800,  7: 8800,  8: 9800},
    },
    "Arizona": {
        "childcare":      {1: 3700, 2: 4900, 3: 6100, 4: 7300, 5: 8500, 6: 9700,  7: 10900, 8: 12100},
        "food":           FPL_200_LIMITS,
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 2700, 2: 3600, 3: 4500, 4: 5400, 5: 6300, 6: 7200,  7: 8100,  8: 9000},
        "transportation": {1: 2100, 2: 2900, 3: 3700, 4: 4500, 5: 5300, 6: 6100,  7: 6900,  8: 7700},
    },
    "Arkansas": {
        "childcare":      {1: 3000, 2: 4000, 3: 5000, 4: 6000, 5: 7000, 6: 8000,  7: 9000,  8: 10000},
        "food":           FPL_200_LIMITS,
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 2400, 2: 3300, 3: 4200, 4: 5100, 5: 6000, 6: 6900,  7: 7800,  8: 8700},
        "transportation": {1: 1800, 2: 2500, 3: 3200, 4: 3900, 5: 4600, 6: 5300,  7: 6000,  8: 6700},
    },
    "California": {
        "childcare":      CHILDCARE_LIMITS,
        "food":           FPL_200_LIMITS,
        "internet":       FPL_200_LIMITS,
        "utility":        UTILITY_LIMITS,
        "transportation": TRANSPORTATION_LIMITS,
    },
    "Colorado": {
        "childcare":      {1: 4700, 2: 6100, 3: 7500, 4: 8900, 5: 10300, 6: 11700, 7: 13100, 8: 14500},
        "food":           FPL_200_LIMITS,
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 3200, 2: 4200, 3: 5200, 4: 6200, 5: 7200,  6: 8200,  7: 9200,  8: 10200},
        "transportation": {1: 2400, 2: 3200, 3: 4000, 4: 4800, 5: 5600,  6: 6400,  7: 7200,  8: 8000},
    },
    "Connecticut": {
        "childcare":      {1: 5000, 2: 6400, 3: 7800, 4: 9200, 5: 10600, 6: 12000, 7: 13400, 8: 14800},
        "food":           FPL_200_LIMITS,
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 3300, 2: 4300, 3: 5300, 4: 6300, 5: 7300,  6: 8300,  7: 9300,  8: 10300},
        "transportation": {1: 2500, 2: 3300, 3: 4100, 4: 4900, 5: 5700,  6: 6500,  7: 7300,  8: 8100},
    },
    "Delaware": {
        "childcare":      {1: 4000, 2: 5200, 3: 6400, 4: 7600, 5: 8800, 6: 10000, 7: 11200, 8: 12400},
        "food":           FPL_200_LIMITS,
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 2900, 2: 3900, 3: 4900, 4: 5900, 5: 6900, 6: 7900,  7: 8900,  8: 9900},
        "transportation": {1: 2200, 2: 3000, 3: 3800, 4: 4600, 5: 5400, 6: 6200,  7: 7000,  8: 7800},
    },
    "District of Columbia": {
        "childcare":      {1: 5500, 2: 7000, 3: 8500, 4: 10000, 5: 11500, 6: 13000, 7: 14500, 8: 16000},
        "food":           FPL_200_LIMITS,
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 3500, 2: 4600, 3: 5700, 4: 6800,  5: 7900,  6: 9000,  7: 10100, 8: 11200},
        "transportation": {1: 2700, 2: 3600, 3: 4500, 4: 5400,  5: 6300,  6: 7200,  7: 8100,  8: 9000},
    },
    "Florida": {
        "childcare":      {1: 3600, 2: 4700, 3: 5800, 4: 6900, 5: 8000, 6: 9100,  7: 10200, 8: 11300},
        "food":           FPL_200_LIMITS,
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 2700, 2: 3600, 3: 4500, 4: 5400, 5: 6300, 6: 7200,  7: 8100,  8: 9000},
        "transportation": {1: 2000, 2: 2700, 3: 3400, 4: 4100, 5: 4800, 6: 5500,  7: 6200,  8: 6900},
    },
    "Georgia": {
        "childcare":      {1: 3500, 2: 4600, 3: 5700, 4: 6800, 5: 7900, 6: 9000,  7: 10100, 8: 11200},
        "food":           FPL_200_LIMITS,
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 2600, 2: 3500, 3: 4400, 4: 5300, 5: 6200, 6: 7100,  7: 8000,  8: 8900},
        "transportation": {1: 2000, 2: 2700, 3: 3400, 4: 4100, 5: 4800, 6: 5500,  7: 6200,  8: 6900},
    },
    "Hawaii": {
        "childcare":      {1: 4900, 2: 6300, 3: 7700, 4: 9100, 5: 10500, 6: 11900, 7: 13300, 8: 14700},
        "food":           FPL_200_LIMITS,
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 3300, 2: 4300, 3: 5300, 4: 6300, 5: 7300,  6: 8300,  7: 9300,  8: 10300},
        "transportation": {1: 2500, 2: 3300, 3: 4100, 4: 4900, 5: 5700,  6: 6500,  7: 7300,  8: 8100},
    },
    "Idaho": {
        "childcare":      {1: 3500, 2: 4600, 3: 5700, 4: 6800, 5: 7900, 6: 9000,  7: 10100, 8: 11200},
        "food":           FPL_200_LIMITS,
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 2600, 2: 3500, 3: 4400, 4: 5300, 5: 6200, 6: 7100,  7: 8000,  8: 8900},
        "transportation": {1: 1900, 2: 2600, 3: 3300, 4: 4000, 5: 4700, 6: 5400,  7: 6100,  8: 6800},
    },
    "Illinois": {
        "childcare":      {1: 4100, 2: 5300, 3: 6500, 4: 7700, 5: 8900, 6: 10100, 7: 11300, 8: 12500},
        "food":           FPL_200_LIMITS,
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 3000, 2: 4000, 3: 5000, 4: 6000, 5: 7000, 6: 8000,  7: 9000,  8: 10000},
        "transportation": {1: 2200, 2: 3000, 3: 3800, 4: 4600, 5: 5400, 6: 6200,  7: 7000,  8: 7800},
    },
    "Indiana": {
        "childcare":      {1: 3600, 2: 4700, 3: 5800, 4: 6900, 5: 8000, 6: 9100,  7: 10200, 8: 11300},
        "food":           FPL_200_LIMITS,
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 2700, 2: 3600, 3: 4500, 4: 5400, 5: 6300, 6: 7200,  7: 8100,  8: 9000},
        "transportation": {1: 2000, 2: 2700, 3: 3400, 4: 4100, 5: 4800, 6: 5500,  7: 6200,  8: 6900},
    },
    "Iowa": {
        "childcare":      {1: 3700, 2: 4800, 3: 5900, 4: 7000, 5: 8100, 6: 9200,  7: 10300, 8: 11400},
        "food":           FPL_200_LIMITS,
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 2800, 2: 3700, 3: 4600, 4: 5500, 5: 6400, 6: 7300,  7: 8200,  8: 9100},
        "transportation": {1: 2000, 2: 2700, 3: 3400, 4: 4100, 5: 4800, 6: 5500,  7: 6200,  8: 6900},
    },
    "Kansas": {
        "childcare":      {1: 3700, 2: 4800, 3: 5900, 4: 7000, 5: 8100, 6: 9200,  7: 10300, 8: 11400},
        "food":           FPL_200_LIMITS,
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 2700, 2: 3600, 3: 4500, 4: 5400, 5: 6300, 6: 7200,  7: 8100,  8: 9000},
        "transportation": {1: 2000, 2: 2700, 3: 3400, 4: 4100, 5: 4800, 6: 5500,  7: 6200,  8: 6900},
    },
    "Kentucky": {
        "childcare":      {1: 3200, 2: 4200, 3: 5200, 4: 6200, 5: 7200, 6: 8200,  7: 9200,  8: 10200},
        "food":           FPL_200_LIMITS,
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 2500, 2: 3400, 3: 4300, 4: 5200, 5: 6100, 6: 7000,  7: 7900,  8: 8800},
        "transportation": {1: 1900, 2: 2600, 3: 3300, 4: 4000, 5: 4700, 6: 5400,  7: 6100,  8: 6800},
    },
    "Louisiana": {
        "childcare":      {1: 3100, 2: 4100, 3: 5100, 4: 6100, 5: 7100, 6: 8100,  7: 9100,  8: 10100},
        "food":           FPL_200_LIMITS,
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 2500, 2: 3400, 3: 4300, 4: 5200, 5: 6100, 6: 7000,  7: 7900,  8: 8800},
        "transportation": {1: 1800, 2: 2500, 3: 3200, 4: 3900, 5: 4600, 6: 5300,  7: 6000,  8: 6700},
    },
    "Maine": {
        "childcare":      {1: 4100, 2: 5300, 3: 6500, 4: 7700, 5: 8900, 6: 10100, 7: 11300, 8: 12500},
        "food":           FPL_200_LIMITS,
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 3200, 2: 4200, 3: 5200, 4: 6200, 5: 7200, 6: 8200,  7: 9200,  8: 10200},
        "transportation": {1: 2200, 2: 3000, 3: 3800, 4: 4600, 5: 5400, 6: 6200,  7: 7000,  8: 7800},
    },
    "Maryland": {
        "childcare":      {1: 5000, 2: 6400, 3: 7800, 4: 9200, 5: 10600, 6: 12000, 7: 13400, 8: 14800},
        "food":           FPL_200_LIMITS,
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 3300, 2: 4300, 3: 5300, 4: 6300, 5: 7300,  6: 8300,  7: 9300,  8: 10300},
        "transportation": {1: 2500, 2: 3300, 3: 4100, 4: 4900, 5: 5700,  6: 6500,  7: 7300,  8: 8100},
    },
    "Massachusetts": {
        "childcare":      {1: 5200, 2: 6700, 3: 8200, 4: 9700, 5: 11200, 6: 12700, 7: 14200, 8: 15700},
        "food":           FPL_200_LIMITS,
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 3400, 2: 4500, 3: 5600, 4: 6700, 5: 7800,  6: 8900,  7: 10000, 8: 11100},
        "transportation": {1: 2600, 2: 3500, 3: 4400, 4: 5300, 5: 6200,  6: 7100,  7: 8000,  8: 8900},
    },
    "Michigan": {
        "childcare":      {1: 3700, 2: 4800, 3: 5900, 4: 7000, 5: 8100, 6: 9200,  7: 10300, 8: 11400},
        "food":           FPL_200_LIMITS,
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 2900, 2: 3900, 3: 4900, 4: 5900, 5: 6900, 6: 7900,  7: 8900,  8: 9900},
        "transportation": {1: 2000, 2: 2700, 3: 3400, 4: 4100, 5: 4800, 6: 5500,  7: 6200,  8: 6900},
    },
    "Minnesota": {
        "childcare":      {1: 4500, 2: 5800, 3: 7100, 4: 8400, 5: 9700, 6: 11000, 7: 12300, 8: 13600},
        "food":           FPL_200_LIMITS,
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 3300, 2: 4300, 3: 5300, 4: 6300, 5: 7300, 6: 8300,  7: 9300,  8: 10300},
        "transportation": {1: 2300, 2: 3100, 3: 3900, 4: 4700, 5: 5500, 6: 6300,  7: 7100,  8: 7900},
    },
    "Mississippi": {
        "childcare":      {1: 2900, 2: 3900, 3: 4900, 4: 5900, 5: 6900, 6: 7900,  7: 8900,  8: 9900},
        "food":           FPL_200_LIMITS,
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 2400, 2: 3300, 3: 4200, 4: 5100, 5: 6000, 6: 6900,  7: 7800,  8: 8700},
        "transportation": {1: 1700, 2: 2300, 3: 2900, 4: 3500, 5: 4100, 6: 4700,  7: 5300,  8: 5900},
    },
    "Missouri": {
        "childcare":      {1: 3500, 2: 4600, 3: 5700, 4: 6800, 5: 7900, 6: 9000,  7: 10100, 8: 11200},
        "food":           FPL_200_LIMITS,
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 2600, 2: 3500, 3: 4400, 4: 5300, 5: 6200, 6: 7100,  7: 8000,  8: 8900},
        "transportation": {1: 1900, 2: 2600, 3: 3300, 4: 4000, 5: 4700, 6: 5400,  7: 6100,  8: 6800},
    },
    "Montana": {
        "childcare":      {1: 3600, 2: 4700, 3: 5800, 4: 6900, 5: 8000, 6: 9100,  7: 10200, 8: 11300},
        "food":           FPL_200_LIMITS,
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 2800, 2: 3700, 3: 4600, 4: 5500, 5: 6400, 6: 7300,  7: 8200,  8: 9100},
        "transportation": {1: 2000, 2: 2700, 3: 3400, 4: 4100, 5: 4800, 6: 5500,  7: 6200,  8: 6900},
    },
    "Nebraska": {
        "childcare":      {1: 3800, 2: 4900, 3: 6000, 4: 7100, 5: 8200, 6: 9300,  7: 10400, 8: 11500},
        "food":           FPL_200_LIMITS,
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 2700, 2: 3600, 3: 4500, 4: 5400, 5: 6300, 6: 7200,  7: 8100,  8: 9000},
        "transportation": {1: 2000, 2: 2700, 3: 3400, 4: 4100, 5: 4800, 6: 5500,  7: 6200,  8: 6900},
    },
    "Nevada": {
        "childcare":      {1: 3900, 2: 5000, 3: 6100, 4: 7200, 5: 8300, 6: 9400,  7: 10500, 8: 11600},
        "food":           FPL_200_LIMITS,
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 2800, 2: 3700, 3: 4600, 4: 5500, 5: 6400, 6: 7300,  7: 8200,  8: 9100},
        "transportation": {1: 2100, 2: 2900, 3: 3700, 4: 4500, 5: 5300, 6: 6100,  7: 6900,  8: 7700},
    },
    "New Hampshire": {
        "childcare":      {1: 4700, 2: 6100, 3: 7500, 4: 8900, 5: 10300, 6: 11700, 7: 13100, 8: 14500},
        "food":           FPL_200_LIMITS,
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 3200, 2: 4200, 3: 5200, 4: 6200, 5: 7200,  6: 8200,  7: 9200,  8: 10200},
        "transportation": {1: 2400, 2: 3200, 3: 4000, 4: 4800, 5: 5600,  6: 6400,  7: 7200,  8: 8000},
    },
    "New Jersey": {
        "childcare":      {1: 5200, 2: 6700, 3: 8200, 4: 9700, 5: 11200, 6: 12700, 7: 14200, 8: 15700},
        "food":           FPL_200_LIMITS,
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 3400, 2: 4500, 3: 5600, 4: 6700, 5: 7800,  6: 8900,  7: 10000, 8: 11100},
        "transportation": {1: 2600, 2: 3500, 3: 4400, 4: 5300, 5: 6200,  6: 7100,  7: 8000,  8: 8900},
    },
    "New Mexico": {
        "childcare":      {1: 3500, 2: 4600, 3: 5700, 4: 6800, 5: 7900, 6: 9000,  7: 10100, 8: 11200},
        "food":           FPL_200_LIMITS,
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 2600, 2: 3500, 3: 4400, 4: 5300, 5: 6200, 6: 7100,  7: 8000,  8: 8900},
        "transportation": {1: 2000, 2: 2700, 3: 3400, 4: 4100, 5: 4800, 6: 5500,  7: 6200,  8: 6900},
    },
    "New York": {
        "childcare":      {1: 4500, 2: 5800, 3: 7100, 4: 8400, 5: 9700, 6: 11000, 7: 12300, 8: 13600},
        "food":           FPL_200_LIMITS,
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 3100, 2: 4000, 3: 4900, 4: 5800, 5: 6700, 6: 7600,  7: 8500,  8: 9400},
        "transportation": {1: 2300, 2: 3100, 3: 3900, 4: 4700, 5: 5500, 6: 6300,  7: 7100,  8: 7900},
    },
    "North Carolina": {
        "childcare":      {1: 3600, 2: 4700, 3: 5800, 4: 6900, 5: 8000, 6: 9100,  7: 10200, 8: 11300},
        "food":           FPL_200_LIMITS,
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 2600, 2: 3500, 3: 4400, 4: 5300, 5: 6200, 6: 7100,  7: 8000,  8: 8900},
        "transportation": {1: 2000, 2: 2700, 3: 3400, 4: 4100, 5: 4800, 6: 5500,  7: 6200,  8: 6900},
    },
    "North Dakota": {
        "childcare":      {1: 4000, 2: 5200, 3: 6400, 4: 7600, 5: 8800, 6: 10000, 7: 11200, 8: 12400},
        "food":           FPL_200_LIMITS,
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 3000, 2: 4000, 3: 5000, 4: 6000, 5: 7000, 6: 8000,  7: 9000,  8: 10000},
        "transportation": {1: 2100, 2: 2900, 3: 3700, 4: 4500, 5: 5300, 6: 6100,  7: 6900,  8: 7700},
    },
    "Ohio": {
        "childcare":      {1: 3600, 2: 4700, 3: 5800, 4: 6900, 5: 8000, 6: 9100,  7: 10200, 8: 11300},
        "food":           FPL_200_LIMITS,
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 2700, 2: 3600, 3: 4500, 4: 5400, 5: 6300, 6: 7200,  7: 8100,  8: 9000},
        "transportation": {1: 2000, 2: 2700, 3: 3400, 4: 4100, 5: 4800, 6: 5500,  7: 6200,  8: 6900},
    },
    "Oklahoma": {
        "childcare":      {1: 3400, 2: 4500, 3: 5600, 4: 6700, 5: 7800, 6: 8900,  7: 10000, 8: 11100},
        "food":           FPL_200_LIMITS,
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 2600, 2: 3500, 3: 4400, 4: 5300, 5: 6200, 6: 7100,  7: 8000,  8: 8900},
        "transportation": {1: 1900, 2: 2600, 3: 3300, 4: 4000, 5: 4700, 6: 5400,  7: 6100,  8: 6800},
    },
    "Oregon": {
        "childcare":      {1: 4500, 2: 5800, 3: 7100, 4: 8400, 5: 9700, 6: 11000, 7: 12300, 8: 13600},
        "food":           FPL_200_LIMITS,
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 3100, 2: 4100, 3: 5100, 4: 6100, 5: 7100, 6: 8100,  7: 9100,  8: 10100},
        "transportation": {1: 2300, 2: 3100, 3: 3900, 4: 4700, 5: 5500, 6: 6300,  7: 7100,  8: 7900},
    },
    "Pennsylvania": {
        "childcare":      {1: 4100, 2: 5300, 3: 6500, 4: 7700, 5: 8900, 6: 10100, 7: 11300, 8: 12500},
        "food":           FPL_200_LIMITS,
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 3000, 2: 4000, 3: 5000, 4: 6000, 5: 7000, 6: 8000,  7: 9000,  8: 10000},
        "transportation": {1: 2200, 2: 3000, 3: 3800, 4: 4600, 5: 5400, 6: 6200,  7: 7000,  8: 7800},
    },
    "Rhode Island": {
        "childcare":      {1: 4400, 2: 5700, 3: 7000, 4: 8300, 5: 9600, 6: 10900, 7: 12200, 8: 13500},
        "food":           FPL_200_LIMITS,
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 3100, 2: 4100, 3: 5100, 4: 6100, 5: 7100, 6: 8100,  7: 9100,  8: 10100},
        "transportation": {1: 2300, 2: 3100, 3: 3900, 4: 4700, 5: 5500, 6: 6300,  7: 7100,  8: 7900},
    },
    "South Carolina": {
        "childcare":      {1: 3400, 2: 4500, 3: 5600, 4: 6700, 5: 7800, 6: 8900,  7: 10000, 8: 11100},
        "food":           FPL_200_LIMITS,
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 2500, 2: 3400, 3: 4300, 4: 5200, 5: 6100, 6: 7000,  7: 7900,  8: 8800},
        "transportation": {1: 1900, 2: 2600, 3: 3300, 4: 4000, 5: 4700, 6: 5400,  7: 6100,  8: 6800},
    },
    "South Dakota": {
        "childcare":      {1: 3700, 2: 4800, 3: 5900, 4: 7000, 5: 8100, 6: 9200,  7: 10300, 8: 11400},
        "food":           FPL_200_LIMITS,
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 2700, 2: 3600, 3: 4500, 4: 5400, 5: 6300, 6: 7200,  7: 8100,  8: 9000},
        "transportation": {1: 2000, 2: 2700, 3: 3400, 4: 4100, 5: 4800, 6: 5500,  7: 6200,  8: 6900},
    },
    "Tennessee": {
        "childcare":      {1: 3400, 2: 4500, 3: 5600, 4: 6700, 5: 7800, 6: 8900,  7: 10000, 8: 11100},
        "food":           FPL_200_LIMITS,
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 2600, 2: 3500, 3: 4400, 4: 5300, 5: 6200, 6: 7100,  7: 8000,  8: 8900},
        "transportation": {1: 1900, 2: 2600, 3: 3300, 4: 4000, 5: 4700, 6: 5400,  7: 6100,  8: 6800},
    },
    "Texas": {
        "childcare":      {1: 3700, 2: 4800, 3: 5900, 4: 7000, 5: 8100, 6: 9200,  7: 10300, 8: 11400},
        "food":           FPL_200_LIMITS,
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 2700, 2: 3600, 3: 4500, 4: 5400, 5: 6300, 6: 7200,  7: 8100,  8: 9000},
        "transportation": {1: 2000, 2: 2700, 3: 3400, 4: 4100, 5: 4800, 6: 5500,  7: 6200,  8: 6900},
    },
    "Utah": {
        "childcare":      {1: 3800, 2: 4900, 3: 6000, 4: 7100, 5: 8200, 6: 9300,  7: 10400, 8: 11500},
        "food":           FPL_200_LIMITS,
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 2700, 2: 3600, 3: 4500, 4: 5400, 5: 6300, 6: 7200,  7: 8100,  8: 9000},
        "transportation": {1: 2000, 2: 2700, 3: 3400, 4: 4100, 5: 4800, 6: 5500,  7: 6200,  8: 6900},
    },
    "Vermont": {
        "childcare":      {1: 4500, 2: 5800, 3: 7100, 4: 8400, 5: 9700, 6: 11000, 7: 12300, 8: 13600},
        "food":           FPL_200_LIMITS,
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 3300, 2: 4300, 3: 5300, 4: 6300, 5: 7300, 6: 8300,  7: 9300,  8: 10300},
        "transportation": {1: 2300, 2: 3100, 3: 3900, 4: 4700, 5: 5500, 6: 6300,  7: 7100,  8: 7900},
    },
    "Virginia": {
        "childcare":      {1: 4400, 2: 5700, 3: 7000, 4: 8300, 5: 9600, 6: 10900, 7: 12200, 8: 13500},
        "food":           FPL_200_LIMITS,
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 3000, 2: 4000, 3: 5000, 4: 6000, 5: 7000, 6: 8000,  7: 9000,  8: 10000},
        "transportation": {1: 2300, 2: 3100, 3: 3900, 4: 4700, 5: 5500, 6: 6300,  7: 7100,  8: 7900},
    },
    "Washington": {
        "childcare":      {1: 5000, 2: 6400, 3: 7800, 4: 9200, 5: 10600, 6: 12000, 7: 13400, 8: 14800},
        "food":           FPL_200_LIMITS,
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 3300, 2: 4300, 3: 5300, 4: 6300, 5: 7300,  6: 8300,  7: 9300,  8: 10300},
        "transportation": {1: 2500, 2: 3300, 3: 4100, 4: 4900, 5: 5700,  6: 6500,  7: 7300,  8: 8100},
    },
    "West Virginia": {
        "childcare":      {1: 3100, 2: 4100, 3: 5100, 4: 6100, 5: 7100, 6: 8100,  7: 9100,  8: 10100},
        "food":           FPL_200_LIMITS,
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 2500, 2: 3400, 3: 4300, 4: 5200, 5: 6100, 6: 7000,  7: 7900,  8: 8800},
        "transportation": {1: 1800, 2: 2500, 3: 3200, 4: 3900, 5: 4600, 6: 5300,  7: 6000,  8: 6700},
    },
    "Wisconsin": {
        "childcare":      {1: 3900, 2: 5000, 3: 6100, 4: 7200, 5: 8300, 6: 9400,  7: 10500, 8: 11600},
        "food":           FPL_200_LIMITS,
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 3000, 2: 4000, 3: 5000, 4: 6000, 5: 7000, 6: 8000,  7: 9000,  8: 10000},
        "transportation": {1: 2100, 2: 2900, 3: 3700, 4: 4500, 5: 5300, 6: 6100,  7: 6900,  8: 7700},
    },
    "Wyoming": {
        "childcare":      {1: 3900, 2: 5000, 3: 6100, 4: 7200, 5: 8300, 6: 9400,  7: 10500, 8: 11600},
        "food":           FPL_200_LIMITS,
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 2800, 2: 3700, 3: 4600, 4: 5500, 5: 6400, 6: 7300,  7: 8200,  8: 9100},
        "transportation": {1: 2100, 2: 2900, 3: 3700, 4: 4500, 5: 5300, 6: 6100,  7: 6900,  8: 7700},
    },
}

# ===========================================================================
# SECTION 3 — SAMPLE SERVICE LOCATIONS
# ---------------------------------------------------------------------------
# Sample list of offices the app can show. Each office has a name, address,
# city, ZIP, and the list of programs it can help with.
# ===========================================================================
LOCATIONS = [
    {
        "name": "Community Child Care Center",
        "address": "701 W Maude Ave, Sunnyvale, CA 94085",
        "city": "Sunnyvale",
        "zip": "94085",
        "programs": ["childcare"],
    },
    {
        "name": "Sunnyvale Community Services",
        "address": "1160 Kern Ave, Sunnyvale, CA 94085",
        "city": "Sunnyvale",
        "zip": "94085",
        "programs": ["food", "utility"],
    },
    {
        "name": "Mountain View Family Resource Center",
        "address": "201 S Rengstorff Ave, Mountain View, CA 94040",
        "city": "Mountain View",
        "zip": "94040",
        "programs": ["childcare", "food", "transportation"],
    },
    {
        "name": "Santa Clara County Social Services Agency",
        "address": "333 W Julian St, San Jose, CA 95110",
        "city": "San Jose",
        "zip": "95110",
        "programs": ["food", "childcare", "utility"],
    },
    {
        "name": "Digital Access Navigator Desk",
        "address": "180 Woz Way, San Jose, CA 95110",
        "city": "San Jose",
        "zip": "95110",
        "programs": ["internet"],
    },
    {
        "name": "Santa Clara Utility Assistance Office",
        "address": "1500 Warburton Ave, Santa Clara, CA 95050",
        "city": "Santa Clara",
        "zip": "95050",
        "programs": ["utility", "internet"],
    },
    {
        "name": "Palo Alto Family Assistance Hub",
        "address": "250 Hamilton Ave, Palo Alto, CA 94301",
        "city": "Palo Alto",
        "zip": "94301",
        "programs": ["childcare", "food", "internet"],
    },
    {
        "name": "Fremont Resource Center",
        "address": "39155 Liberty St, Fremont, CA 94538",
        "city": "Fremont",
        "zip": "94538",
        "programs": ["food", "utility", "transportation"],
    },
    {
        "name": "Oakland Community Action Partnership",
        "address": "150 Frank H. Ogawa Plaza, Oakland, CA 94612",
        "city": "Oakland",
        "zip": "94612",
        "programs": ["food", "utility", "internet"],
    },
    {
        "name": "San Francisco Human Services Agency",
        "address": "170 Otis St, San Francisco, CA 94103",
        "city": "San Francisco",
        "zip": "94103",
        "programs": ["food", "childcare", "utility"],
    },
    {
        "name": "Los Angeles Family Benefits Center",
        "address": "2615 S Grand Ave, Los Angeles, CA 90007",
        "city": "Los Angeles",
        "zip": "90007",
        "programs": ["food", "childcare", "utility", "internet"],
    },
    {
        "name": "San Diego Neighborhood House",
        "address": "841 S 41st St, San Diego, CA 92113",
        "city": "San Diego",
        "zip": "92113",
        "programs": ["food", "utility", "transportation"],
    },
    {
        "name": "Sacramento Family Resource Desk",
        "address": "1725 28th St, Sacramento, CA 95816",
        "city": "Sacramento",
        "zip": "95816",
        "programs": ["childcare", "food", "internet"],
    },
]

# Maps a ZIP code to (latitude, longitude) so we can measure distance
# between the user's ZIP and an office's ZIP.
ZIP_COORDS = {
    "90007": (34.0288, -118.2849),
    "92113": (32.6976, -117.1185),
    "94040": (37.3861, -122.0839),
    "94043": (37.4068, -122.0776),
    "94085": (37.3894, -122.0180),
    "94086": (37.3716, -122.0212),
    "94087": (37.3502, -122.0322),
    "94089": (37.4111, -122.0104),
    "94103": (37.7725, -122.4147),
    "94301": (37.4447, -122.1484),
    "94538": (37.5042, -121.9644),
    "94612": (37.8086, -122.2682),
    "95050": (37.3541, -121.9552),
    "95051": (37.3483, -121.9844),
    "95054": (37.3938, -121.9638),
    "95110": (37.3427, -121.9073),
    "95112": (37.3547, -121.8863),
    "95816": (38.5715, -121.4686),
}

# Same idea as ZIP_COORDS, but for city names. So a user can type
# "san jose" instead of a ZIP and we still find nearby offices.
CITY_COORDS = {
    "fremont": ZIP_COORDS["94538"],
    "los angeles": ZIP_COORDS["90007"],
    "mountain view": ZIP_COORDS["94040"],
    "oakland": ZIP_COORDS["94612"],
    "palo alto": ZIP_COORDS["94301"],
    "sacramento": ZIP_COORDS["95816"],
    "san diego": ZIP_COORDS["92113"],
    "san francisco": ZIP_COORDS["94103"],
    "san jose": ZIP_COORDS["95110"],
    "santa clara": ZIP_COORDS["95050"],
    "sunnyvale": ZIP_COORDS["94086"],
    "berkeley": (37.8716, -122.2730),
    "long beach": (33.7701, -118.1937),
    "anaheim": (33.8366, -117.9143),
    "riverside": (33.9533, -117.3962),
    "fresno": (36.7378, -119.7871),
    "bakersfield": (35.3733, -119.0187),
    "stockton": (37.9577, -121.2908),
    "modesto": (37.6391, -120.9969),
    "oxnard": (34.1975, -119.1771),
    "irvine": (33.6846, -117.8265),
    "pasadena": (34.1478, -118.1445),
    "glendale": (34.1425, -118.2551),
    "huntington beach": (33.6595, -118.0023),
    "santa ana": (33.7455, -117.8677),
    "chula vista": (32.6401, -117.0842),
    "moreno valley": (33.9425, -117.2297),
    "fontana": (34.0922, -117.4350),
    "salinas": (36.6777, -121.6555),
    "hayward": (37.6688, -122.0808),
}

# ===========================================================================
# SECTION 4 — STARTUP HELPERS
# ---------------------------------------------------------------------------
# Functions used to initialize lookup tables and provide small runtime helpers.
# ===========================================================================
def _extend_zip_pin_codes() -> None:
    """Fill in lots of extra ZIP codes around California so distance search
    works for most cities — these are fake/approximate coords, just for demo."""
    # Each "cluster" is: (center latitude, center longitude, list of ZIPs).
    # We then nudge each ZIP a tiny bit off the center so they aren't all on
    # top of each other on a map.
    clusters: list[tuple[float, float, list[str]]] = [
        # South Bay / Peninsula
        (
            37.34,
            -121.89,
            "95111 95113 95116 95117 95118 95119 95120 95121 95123 95124 95125 95126 95127 95128 95129 95130 95131 95132 95133 95134 95135 95136 95138 95139 95148 95150 95151 95152 95153 95154 95155 95156 95157 95158 95159 95160 95161 95164 95170 95172 95173 95190 95191 95192 95193 95194 95196".split(),
        ),
        (
            37.39,
            -122.08,
            "94022 94024 94025 94026 94027 94028 94030 94061 94062 94063 94065 94070 94302 94303 94304 94305 94306 94309".split(),
        ),
        (
            37.38,
            -122.02,
            "94041 94042 94043 94044 94045 94046 94047 94048 94049 94050 94051 94052 94053 94054 94055 94056 94057 94058 94059 94060 94064 94066 94067 94068 94069 94071 94072 94073 94074 94075 94076 94077 94078 94079 94080 94081 94082 94083 94084 94088 94090 94091 94092 94093 94094 94095 94096 94097 94098 94099".split(),
        ),
        (
            37.77,
            -122.42,
            "94102 94104 94105 94107 94108 94109 94110 94111 94114 94115 94116 94117 94118 94121 94122 94123 94124 94127 94128 94129 94130 94131 94132 94133 94134 94158 94159 94160 94161 94162 94163 94164".split(),
        ),
        (
            37.80,
            -122.27,
            "94601 94602 94603 94605 94606 94607 94608 94609 94610 94611 94612 94613 94618 94619 94620 94621 94702 94703 94704 94705 94706 94707 94708 94709 94710 94720".split(),
        ),
        (
            37.50,
            -121.96,
            "94536 94537 94538 94539 94555 94557 94560 94587 94588".split(),
        ),
        (
            34.05,
            -118.25,
            "90001 90002 90003 90004 90005 90006 90007 90008 90010 90011 90012 90013 90014 90015 90016 90017 90018 90019 90020 90021 90022 90023 90024 90025 90026 90027 90028 90029 90031 90032 90033 90034 90035 90036 90037 90038 90039 90040 90041 90042 90043 90044 90045 90046 90047 90048 90049 90056 90057 90058 90059 90061 90062 90063 90064 90065 90066 90067 90068 90069 90071 90077 90079 90089 90094 90095".split(),
        ),
        (
            33.77,
            -118.19,
            "90801 90802 90803 90804 90805 90806 90807 90808 90809 90810 90813 90814 90815 90822 90831 90832 90833 90840 90842 90844 90845 90846 90847 90848 90853 90895 90899".split(),
        ),
        (
            33.68,
            -117.80,
            "92602 92603 92604 92606 92612 92614 92617 92618 92620 92623 92625 92626 92627 92630 92637 92647 92648 92649 92650 92651 92652 92653 92655 92656 92657 92660 92661 92662 92663 92672 92675 92676 92677 92678 92679 92683 92684 92685 92688 92690 92691 92692 92693 92694 92697 92698".split(),
        ),
        (
            32.72,
            -117.16,
            "92101 92102 92103 92104 92105 92106 92107 92108 92109 92110 92111 92113 92114 92115 92116 92117 92119 92120 92121 92122 92123 92124 92126 92127 92128 92129 92130 92131 92132 92134 92135 92136 92139 92140 92145 92147 92154 92155 92159 92160 92161 92163 92165 92166 92167 92168 92169 92170 92171 92172 92173 92174 92175 92176 92177 92178 92179 92182 92186 92187 92191 92192 92193 92195 92196 92197 92198 92199".split(),
        ),
        (
            38.58,
            -121.49,
            "95814 95815 95816 95817 95818 95819 95820 95821 95822 95823 95824 95825 95826 95827 95828 95829 95830 95831 95832 95833 95834 95835 95837 95838 95841 95842 95843 95864 95865 95866 95867 95894 95899".split(),
        ),
        (
            36.74,
            -119.79,
            "93650 93701 93702 93703 93704 93705 93706 93707 93708 93709 93710 93711 93720 93721 93722 93723 93724 93725 93726 93727 93728 93730 93740 93741 93744 93745 93747 93750 93755 93760 93761 93764 93765 93771 93772 93773 93774 93775 93776 93777 93778 93779 93786 93790 93791 93792 93793 93794".split(),
        ),
        (
            35.37,
            -119.02,
            "93301 93302 93303 93304 93305 93306 93307 93308 93309 93311 93312 93313 93314 93380 93381 93382 93383 93384 93385 93386 93387 93388 93389 93390".split(),
        ),
        (
            37.96,
            -121.29,
            "95201 95202 95203 95204 95205 95206 95207 95208 95209 95210 95211 95212 95213 95215 95219 95267 95269 95296 95297".split(),
        ),
        (
            37.64,
            -121.00,
            "95350 95351 95352 95353 95354 95355 95356 95357 95358 95367 95368 95397".split(),
        ),
        (
            34.20,
            -119.18,
            "93001 93003 93004 93010 93012 93015 93030 93033 93035 93036 93040 93041 93043 93060 93063 93064 93065 93066 93067".split(),
        ),
        (
            33.95,
            -117.40,
            "92501 92502 92503 92504 92505 92506 92507 92508 92509 92514 92515 92516 92517 92518 92519 92521 92522 92532 92553 92554 92555 92556 92557 92561 92562 92563 92564 92570 92571 92572 92581 92582 92583 92584 92585 92586 92587 92589 92590 92591 92592 92593 92595 92596 92599".split(),
        ),
        (
            33.84,
            -117.91,
            "92801 92802 92803 92804 92805 92806 92807 92808 92809 92812 92814 92815 92816 92817 92821 92822 92823 92825 92831 92832 92833 92834 92835 92836 92837 92838 92840 92841 92842 92843 92844 92845 92846 92850 92856 92857 92859 92860 92861 92862 92863 92864 92865 92866 92867 92868 92869 92870 92871 92877 92878 92879 92880 92881 92882 92883 92885 92886 92887".split(),
        ),
        (
            32.64,
            -117.08,
            "91902 91910 91911 91913 91914 91915 91950 91951 91942 91945 91948".split(),
        ),
        (
            37.67,
            -122.08,
            "94541 94542 94544 94545 94546 94552 94557 94580 94586 94587".split(),
        ),
    ]
    # Walk through each cluster and add every ZIP we haven't already added.
    for lat0, lon0, codes in clusters:
        for i, code in enumerate(codes):
            # If we already have real coords for this ZIP, keep them.
            if code in ZIP_COORDS:
                continue
            # Spread the points out a little around the cluster center,
            # using simple math on the index to fake a scatter.
            dlat = ((i * 11) % 9 - 4) * 0.012
            dlon = ((i * 17) % 11 - 5) * 0.012
            ZIP_COORDS[code] = (round(lat0 + dlat, 4), round(lon0 + dlon, 4))


# Run the helper above right now so ZIP_COORDS is filled in before the app starts.
_extend_zip_pin_codes()

# ===========================================================================
# SECTION 5 — FORM CHOICE OPTIONS
# ---------------------------------------------------------------------------
# Lists used to populate dropdowns and selection controls in the form.
# ===========================================================================
# Choices for the "Employment" dropdown on step 2.
EMPLOYMENT_OPTIONS = [
    "Working",
    "In school or job training",
    "Working and in school",
    "Looking for work",
    "Not working or in school",
    "Retired",
]

# Choices for the "Age range" dropdown.
AGE_OPTIONS = ["Child", "Adult", "Senior"]
#Choices for "State" dropdown.
STATE_OPTIONS = ["Alabama", "Alaska", "American Samoa", "Arizona", "Arkansas", "California", "Colorado", "Connecticut", "Delaware", "District of Columbia", "Florida", "Georgia", "Guam", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota", "Minor Outlying Islands", "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico", "New York", "North Carolina", "North Dakota", "Northern Mariana Islands", "Ohio", "Oklahoma", "Oregon", "Pennsylvania", "Puerto Rico", "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas", "U.S. Virgin Islands", "Utah", "Vermont",("Virginia"), ("Washington"), ("West Virginia"), ("Wisconsin"), ("Wyoming")]
# Choices for the "Search radius (miles)" dropdown on the results screen.
RADIUS_OPTIONS = ["5", "10", "25", "50", "100"]

# ===========================================================================
# SECTION 6 — APP THEME AND VISUAL CONSTANTS
# ---------------------------------------------------------------------------
# Colors, version text, and visual palette mappings used by the UI throughout.
# ===========================================================================
# Version number shown in the About box and the footer.
APP_VERSION = "2.0.0"

# Background color for each eligibility status pill.
STATUS_COLORS = {
    "Highly eligible": "#134e2a",     # dark green
    "Partially eligible": "#5c4510",  # dark amber
    "Unlikely": "#5c1f1f",            # dark red
}

# Text color for each pill (chosen to read clearly on the bg above).
STATUS_TEXT_COLORS = {
    "Highly eligible": "#bbf7d0",
    "Partially eligible": "#fde68a",
    "Unlikely": "#fecaca",
}

# Shorter labels for narrow pill chips so the text doesn't get cut off.
STATUS_PILL_SHORT = {
    "Highly eligible": "High match",
    "Partially eligible": "Partial",
    "Unlikely": "Unlikely",
}


def status_pill_caption(full_status: str) -> str:
    # Look up the short caption; if not found, just use the full status.
    return STATUS_PILL_SHORT.get(full_status, full_status)


# ---------------------------------------------------------------------------
# Dark theme color palette. Every color in the UI comes from here.
# ---------------------------------------------------------------------------
ACCENT = "#38bdf8"          # bright sky blue — main highlight
ACCENT_DIM = "#0ea5e9"      # darker version of accent
ACCENT_GLOW = "#22d3ee"     # cyan glow used for hover rings
APP_BG = "#0a0e14"          # main app background (very dark)
APP_BG_ELEVATED = "#0f141c" # slightly lighter bg (for footer)
CARD_BG = "#121826"         # background of cards
CARD_BG_HOVER = "#171d2e"   # card bg when hovered
RAIL_BG = "#0d1118"         # left progress rail background
BORDER = "#2a3447"          # subtle borders around cards/inputs
BORDER_FOCUS = ACCENT       # border color when an input is focused
TEXT = "#e8eef9"            # main text color (near-white)
MUTED = "#94a3b8"           # secondary/hint text (gray)
SUBTEXT = "#c5d1e8"         # body paragraph text
PRIMARY = "#3b82f6"         # primary button color
PRIMARY_HOVER = "#2563eb"   # primary button when hovered
PRIMARY_PRESSED = "#1d4ed8" # primary button while clicked
INPUT_BG = "#1a2233"        # background for text inputs
HEADER_BG = "#0f141c"       # top header bar bg
SHADOW = "#05070a"          # very dark shadow under cards
SUCCESS = "#34d399"         # green for "good" stats
WARNING = "#fbbf24"         # yellow for "needs review"


def preferred_ui_font(tk_ref: tk.Misc | None = None) -> str:
    """Pick the first nice-looking font that's actually installed.
    If we just used "Helvetica" everywhere, on some systems Tk would fall back
    to an ugly default. So we ask Tk what fonts exist and pick the best one."""
    # Use the given Tk widget as a reference, or fall back to the default root.
    ref = tk_ref if tk_ref is not None else getattr(tk, "_default_root", None)
    if ref is None:
        # Tk isn't running yet — return a safe default.
        return "Helvetica"
    # Get the set of font names installed on this system.
    families = set(tkfont.families(ref))
    # Try each preferred font in order and return the first one that exists.
    for name in (".SF NS Text", "SF Pro Text", "Segoe UI", "Helvetica Neue", "Avenir Next"):
        if name in families:
            return name
    return "Helvetica"


# Default font family. Gets replaced with a nicer one once Tk starts up.
FONT_FAMILY = "Helvetica"

# For each program, the documents the user should bring to an office visit.
PROGRAM_CHECKLISTS: dict[str, list[str]] = {
    "childcare": [
        "Photo ID for parent or guardian",
        "Proof of income (recent pay stubs or tax return)",
        "Proof of work, school, or training schedule",
        "Child birth certificate or school enrollment",
    ],
    "food": [
        "Photo ID for applicant",
        "Proof of household income",
        "Rent or mortgage statement (if requested)",
        "Utility bill showing address",
    ],
    "utility": [
        "Past-due bill or shutoff notice",
        "Photo ID",
        "Proof of income",
        "Lease or document showing service address",
    ],
    "internet": [
        "Photo ID",
        "Proof of income or participation in another aid program",
        "Statement of need (work, school, health, or benefits access)",
    ],
    "transportation": [
        "Photo ID",
        "Appointment letter, employer letter, or class schedule",
        "Proof of income",
    ],
}

# Items everyone should bring no matter which program they're applying for.
MASTER_DOCUMENT_LIST = [
    "Government-issued photo ID for each adult applying",
    "Social Security cards or numbers for household members (if required locally)",
    "Last 30 days of pay stubs or self-employment records",
    "Bank statements (last 2–3 months) if requested",
    "Proof of address (lease, utility bill, or official mail)",
]


# ===========================================================================
# SECTION 7 — DATA CONTAINERS
# ---------------------------------------------------------------------------
# Small dataclasses used to store eligibility checks and program results.
# ===========================================================================
# A single rule we check against the user (e.g. "is income under the limit?").
# Stores the result of the check plus the text to show if it passed or failed.
@dataclass
class RuleCheck:
    name: str           # short label like "Income"
    passed: bool        # True if the user passed this rule
    pass_text: str      # text to show when the rule passes
    fail_text: str      # text to show when the rule fails
    close: bool = False     # True if the user is "almost" passing
    critical: bool = False  # True if failing this rule alone disqualifies them


# The combined result for one program (after running all its rules).
@dataclass
class ProgramResult:
    status: str             # "Highly eligible", "Partially eligible", or "Unlikely"
    explanation: str        # plain-English summary
    passed: list[str]       # list of pass texts from rules they met
    missed: list[str]       # list of fail texts from rules they didn't meet


def draw_rounded_rect(canvas: tk.Canvas, x1: int, y1: int, x2: int, y2: int, radius: int, **kwargs) -> int:
    """Draw a rectangle with rounded corners on a Tk canvas.
    Tk has no built-in rounded rectangle, so we fake one by drawing a
    smoothed polygon whose corner points are pulled in by `radius` pixels."""
    # The list of (x, y) points that outline the rounded rectangle.
    points = [
        x1 + radius, y1,
        x2 - radius, y1,
        x2, y1,
        x2, y1 + radius,
        x2, y2 - radius,
        x2, y2,
        x2 - radius, y2,
        x1 + radius, y2,
        x1, y2,
        x1, y2 - radius,
        x1, y1 + radius,
        x1, y1,
    ]
    # smooth=True tells Tk to round off the corners.
    return canvas.create_polygon(points, smooth=True, **kwargs)


def widget_background(widget: tk.Widget, fallback: str = APP_BG) -> str:
    """Get the background color of a Tk widget, with a safe fallback if Tk errors out."""
    try:
        return str(widget.cget("bg"))
    except tk.TclError:
        # Some widgets don't support "bg" — return the fallback color instead.
        return fallback


class RoundedCard(tk.Frame):
    """A card with rounded corners. Tk frames are always rectangular, so we
    cheat: we draw the rounded shape on a Canvas, then put a regular Frame
    on top of it for the actual content."""

    def __init__(self, parent: tk.Widget, background: str = APP_BG) -> None:
        # Set up this widget as a normal frame with no border or highlight.
        super().__init__(parent, bg=background, bd=0, highlightthickness=0)
        self.radius = 22   # how rounded the corners are (in pixels)
        self.margin = 8    # gap between the rounded shape and the inner content
        # The canvas is where we draw the rounded background + shadow.
        self.canvas = tk.Canvas(self, bg=background, bd=0, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        # The body frame sits on top of the canvas — this is where real widgets go.
        self.body = tk.Frame(self.canvas, bg=CARD_BG, bd=0, highlightthickness=0)
        # Place the body frame on the canvas at (margin, margin).
        self.window_id = self.canvas.create_window((self.margin, self.margin), window=self.body, anchor="nw")
        # Whenever the canvas resizes, redraw the rounded shape.
        self.canvas.bind("<Configure>", self._redraw)
        # Whenever the body grows (more widgets added), resize the canvas to match.
        self.body.bind("<Configure>", self._sync_size)

    def _sync_size(self, _event: tk.Event | None = None) -> None:
        # Make the canvas big enough to fit the body plus margins on each side.
        width = max(120, self.body.winfo_reqwidth() + self.margin * 2)
        height = max(60, self.body.winfo_reqheight() + self.margin * 2)
        self.canvas.configure(width=width, height=height)
        self._redraw()

    def _redraw(self, _event: tk.Event | None = None) -> None:
        # Pick the bigger of the canvas size and the body size, so we always cover everything.
        width = max(self.canvas.winfo_width(), self.body.winfo_reqwidth() + self.margin * 2)
        height = max(self.canvas.winfo_height(), self.body.winfo_reqheight() + self.margin * 2)
        # Wipe the old shape so we can draw fresh.
        self.canvas.delete("card-shape")
        # First, draw a slightly offset dark shape to act as a soft drop shadow.
        draw_rounded_rect(self.canvas, self.margin + 2, self.margin + 3, width - 2, height - 2, self.radius, fill=SHADOW, outline="", tags="card-shape")
        # Then draw the real card on top of the shadow.
        draw_rounded_rect(self.canvas, self.margin, self.margin, width - 4, height - 5, self.radius, fill=CARD_BG, outline=BORDER, width=1, tags="card-shape")
        # Move the card-shape behind the body frame so the body widgets show on top.
        self.canvas.tag_lower("card-shape")
        # Tell the body frame how wide it can be, and reposition it.
        self.canvas.itemconfigure(self.window_id, width=max(1, width - self.margin * 2))
        self.canvas.coords(self.window_id, self.margin, self.margin)


class PillLabel(tk.Canvas):
    """A small rounded badge with text inside (like the 'High match' chip).
    We use a Canvas so we can draw the rounded shape ourselves."""

    def __init__(self, parent: tk.Widget, text: str, fill: str, foreground: str, background: str = CARD_BG) -> None:
        # Start as a plain canvas with no border.
        super().__init__(parent, bg=background, bd=0, highlightthickness=0)
        # Save the colors and text so we can redraw later if they change.
        self._fill = fill                # pill background color
        self._foreground = foreground    # text color
        self._background = background    # area outside the pill
        self._text = text
        # Create the bold font used for the pill text.
        self._pill_font = tkfont.Font(family=FONT_FAMILY, size=10, weight="bold")
        self._redraw_pill()

    def set_text(self, text: str) -> None:
        # Public method: change the text and redraw.
        self._text = text
        self._redraw_pill()

    def _redraw_pill(self) -> None:
        # Erase whatever is on the canvas right now.
        self.delete("all")
        text = self._text
        # Measure the text and add padding so the pill fits the text snugly.
        width = self._pill_font.measure(text) + 36
        height = self._pill_font.metrics("linespace") + 16
        # Resize the canvas to match the pill size.
        super().configure(width=width, height=height, bg=self._background)
        # Draw the rounded background.
        draw_rounded_rect(self, 1, 1, width - 1, height - 1, 16, fill=self._fill, outline="")
        # Draw the text in the center of the pill.
        self.create_text(width // 2, height // 2, text=text, fill=self._foreground, font=self._pill_font)


class ModernButton(tk.Canvas):
    """A custom button drawn on a Canvas. We use a canvas instead of Tk's
    built-in button so we can have rounded corners and hover effects."""

    # Color sets for the four button styles. Each style has colors for
    # the normal, hover (mouse over), and pressed (clicked) states, plus
    # a foreground (text) color.
    THEMES = {
        "primary": {"normal": PRIMARY, "hover": PRIMARY_HOVER, "pressed": PRIMARY_PRESSED, "fg": "#f8fafc"},
        "secondary": {"normal": "#1e293b", "hover": "#273549", "pressed": "#334155", "fg": TEXT},
        "ghost": {"normal": CARD_BG, "hover": CARD_BG_HOVER, "pressed": "#1e293b", "fg": TEXT},
        "accent": {"normal": "#0c4a6e", "hover": "#075985", "pressed": "#0369a1", "fg": ACCENT_GLOW},
    }

    def __init__(self, parent: tk.Widget, text: str, command, variant: str = "secondary", background: str | None = None) -> None:
        # Save the basic info about this button.
        self.text = text         # the label
        self.command = command   # the function to call when clicked
        self.variant = variant   # which color theme to use ("primary"/"secondary"/etc.)
        self.state = "normal"    # "normal" or "disabled"
        # Bold font for the button label.
        self.button_font = tkfont.Font(family=FONT_FAMILY, size=11, weight="bold")
        self.height = 48         # button height in pixels
        self.pad_x = 38          # horizontal padding around the text
        self._corner_r = 18      # corner radius
        # If the caller didn't say what background color to use, copy the parent's.
        self.background = background or widget_background(parent)
        # Calculate how wide the button needs to be to fit its text + padding.
        width = self._width_for_text(text)
        # Initialize the underlying canvas.
        super().__init__(parent, width=width, height=self.height, bg=self.background, bd=0, highlightthickness=0, cursor="hand2")
        self._hover = False  # tracks whether the mouse is over the button
        # Connect mouse events to handler methods.
        self.bind("<Enter>", self._on_enter)                    # mouse enters
        self.bind("<Leave>", self._on_leave)                    # mouse leaves
        self.bind("<ButtonPress-1>", lambda _event: self._draw("pressed"))  # mouse clicks down
        self.bind("<ButtonRelease-1>", self._release)           # mouse clicks up
        # Draw the button in its normal state to start.
        self._draw("normal")

    def _on_enter(self, _event: tk.Event) -> None:
        # Mouse moved onto the button — switch to hover style.
        self._hover = True
        self._draw("hover")

    def _on_leave(self, _event: tk.Event) -> None:
        # Mouse moved off the button — back to normal.
        self._hover = False
        self._draw("normal")

    def _width_for_text(self, text: str) -> int:
        # Measure the text and pad it. Always at least 96px wide.
        return max(96, self.button_font.measure(text) + self.pad_x * 2)

    def _release(self, _event: tk.Event) -> None:
        # Mouse let go of click. If the button is enabled, run the command.
        if self.state != "disabled" and self.command:
            self.command()
        # After click, go back to "hover" if the mouse is still over us, else "normal".
        self._draw("hover" if self.state != "disabled" and self._hover else "normal")

    def _draw(self, mode: str) -> None:
        # Wipe the canvas before redrawing.
        self.delete("all")
        theme = self.THEMES[self.variant]
        disabled = self.state == "disabled"
        # Pick the fill and text colors based on disabled vs. mode.
        fill = "#334155" if disabled else theme[mode]
        fg = "#64748b" if disabled else theme["fg"]
        width = int(self.cget("width"))
        # If the user is hovering (and the button is enabled), draw a soft outline ring around it.
        r = getattr(self, "_corner_r", 18)
        if not disabled and mode == "hover":
            glow = ACCENT_GLOW if self.variant == "primary" else BORDER
            draw_rounded_rect(self, 0, 0, width, self.height, r + 2, fill="", outline=glow, width=2)
        # Draw the actual button shape.
        draw_rounded_rect(self, 2, 2, width - 2, self.height - 2, r, fill=fill, outline="")
        # Place the text in the center.
        self.create_text(width // 2, self.height // 2, text=self.text, fill=fg, font=self.button_font)
        # Show a hand cursor when enabled, normal arrow when disabled.
        super().configure(cursor="arrow" if disabled else "hand2")

    def configure(self, cnf=None, **kwargs) -> None:  # type: ignore[override]
        """Update the button's text, state, command, etc. Mimics Tk's standard configure()."""
        # Combine positional and keyword options into one dict.
        options = {}
        if cnf:
            options.update(cnf)
        options.update(kwargs)
        # If the text changed, update it and resize the button.
        if "text" in options:
            self.text = options.pop("text")
            super().configure(width=self._width_for_text(self.text))
        # If the state changed (e.g. disabled), save it.
        if "state" in options:
            self.state = options.pop("state")
        # If a new command was given, replace the old one.
        if "command" in options:
            self.command = options.pop("command")
        # Pass any leftover options through to the canvas.
        if options:
            super().configure(**options)
        # Redraw to reflect any changes.
        if hasattr(self, "button_font"):
            self._draw("normal")

    # Some Tk code uses .config() instead of .configure() — make them the same.
    config = configure


class ScrollableFrame(ttk.Frame):
    """A scrollable column. Tk doesn't let you scroll a Frame directly,
    so we put a Canvas inside this Frame, then put another Frame inside
    the Canvas. We can scroll the Canvas, which scrolls the inner Frame.

    Mouse-wheel handling is tricky because the results page has scrollable
    frames inside scrollable frames. We bind the mouse wheel ONCE on the
    root window, then route the event to the right frame based on where
    the cursor is."""

    # Class-level (shared) variables. These remember which frame is "active"
    # (last hovered) and whether we've already set up the mousewheel binding.
    _active: ScrollableFrame | None = None
    _wheel_bound: bool = False

    def __init__(self, parent: tk.Widget, background: str = APP_BG) -> None:
        super().__init__(parent)
        self._bg = background
        # Canvas that does the actual scrolling.
        self.canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0, background=background)
        # Vertical scrollbar wired to the canvas's yview.
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        # The inner frame is where the actual content goes.
        self.inner = tk.Frame(self.canvas, background=background)
        # Place the inner frame on the canvas at top-left.
        self.window_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        # Tell the canvas to update the scrollbar position as it scrolls.
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        # Lay out: canvas fills most of the space, scrollbar on the right.
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        # When the inner frame's size changes, recalculate the scroll region.
        self.inner.bind("<Configure>", self._update_scroll_region)
        # When the canvas resizes, make the inner frame match its width.
        self.canvas.bind("<Configure>", self._resize_inner)
        # Track when the mouse enters this scroll frame so we know which one is active.
        self.bind("<Enter>", self._activate)
        self.canvas.bind("<Enter>", self._activate)
        self.inner.bind("<Enter>", self._activate)
        # Clean up when this frame is destroyed.
        self.bind("<Destroy>", self._on_destroy)

    @classmethod
    def hook_mousewheel(cls, root: tk.Misc) -> None:
        """Set up mouse-wheel scrolling for the whole app. Only call this once."""
        if cls._wheel_bound:
            return
        # bind_all means: catch this event no matter what widget the mouse is over.
        # <MouseWheel> is for Windows/macOS. <Button-4>/<Button-5> are for Linux.
        root.bind_all("<MouseWheel>", cls._on_mousewheel_all)
        root.bind_all("<Button-4>", cls._on_linux_up_all)
        root.bind_all("<Button-5>", cls._on_linux_down_all)
        cls._wheel_bound = True

    def _activate(self, _event: tk.Event) -> None:
        # Mark this frame as the currently-active scroll target.
        ScrollableFrame._active = self

    def _on_destroy(self, event: tk.Event) -> None:
        # If the active frame is being destroyed, forget about it.
        if event.widget == self and ScrollableFrame._active is self:
            ScrollableFrame._active = None

    @classmethod
    def _scroll_target(cls, event: tk.Event) -> ScrollableFrame | None:
        """Figure out which ScrollableFrame the mouse is actually inside.
        Walks up the widget tree from the event widget until we find one."""
        w = getattr(event, "widget", None)
        while w is not None:
            if isinstance(w, ScrollableFrame):
                try:
                    # Make sure it actually exists and is on screen.
                    if w.winfo_exists() and w.winfo_ismapped():
                        return w
                except tk.TclError:
                    pass
            try:
                # Move up to the parent widget and try again.
                w = w.master  # type: ignore[assignment]
            except (AttributeError, tk.TclError):
                break
        # Fallback: use whichever frame was last hovered.
        return cls._active

    @classmethod
    def _apply_wheel_delta(cls, sf: ScrollableFrame, delta: int) -> None:
        """Actually scroll the given frame by the wheel amount."""
        try:
            # Skip if the frame was destroyed or hidden.
            if not sf.winfo_exists() or not sf.winfo_ismapped():
                return
        except tk.TclError:
            return
        c = sf.canvas
        if sys.platform == "darwin":
            # macOS sends small delta values, so we use a fixed step.
            if delta:
                step = 3 if delta > 0 else -3
                c.yview_scroll(step, "units")
        elif delta:
            # On Windows the delta is in multiples of 120; convert to scroll units.
            c.yview_scroll(int(-1 * (delta / 120)), "units")

    @classmethod
    def _on_mousewheel_all(cls, event: tk.Event) -> None:
        # Wheel event on Win/Mac: find the right frame and scroll it.
        sf = cls._scroll_target(event)
        if sf is None:
            return
        cls._apply_wheel_delta(sf, getattr(event, "delta", 0) or 0)

    @classmethod
    def _on_linux_up_all(cls, event: tk.Event) -> None:
        # Linux scroll-up event.
        sf = cls._scroll_target(event)
        if sf is None:
            return
        try:
            if sf.winfo_exists() and sf.winfo_ismapped():
                sf.canvas.yview_scroll(-3, "units")
        except tk.TclError:
            pass

    @classmethod
    def _on_linux_down_all(cls, event: tk.Event) -> None:
        # Linux scroll-down event.
        sf = cls._scroll_target(event)
        if sf is None:
            return
        try:
            if sf.winfo_exists() and sf.winfo_ismapped():
                sf.canvas.yview_scroll(3, "units")
        except tk.TclError:
            pass

    def _update_scroll_region(self, _event: tk.Event) -> None:
        # Tell the canvas how big its scrollable area is (= the size of the inner frame).
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _resize_inner(self, event: tk.Event) -> None:
        # When the canvas changes width, stretch the inner frame to match.
        self.canvas.itemconfigure(self.window_id, width=event.width)


# --- Persistence & small UX helpers (settings, maps, clipboard, toasts) ----------


def resolve_brand_logo_path() -> Path | None:
    """Find the first logo file that actually exists, or return None if no logo is available."""
    for candidate in BRAND_LOGO_CANDIDATES:
        if candidate.exists():
            return candidate
    return None

def load_logo():
    if Image is None or ImageTk is None:
        # Pillow is not installed, so loading the logo is not available.
        return None

    logo_path = next((p for p in BRAND_LOGO_CANDIDATES if p.exists()), None)
    if not logo_path:
        print("⚠️ No logo found")
        return None

    img = Image.open(logo_path)

    # Adjust this to the size you want the logo to appear
    DISPLAY_SIZE = (180, 180)
    img = img.resize(DISPLAY_SIZE, Image.LANCZOS)

    return ImageTk.PhotoImage(img)



def default_settings() -> dict[str, object]:
    """The default settings used the very first time the app runs."""
    return {"font_scale": 0, "reduce_motion": False, "autosave_draft": True}


def load_settings() -> dict[str, object]:
    """Read the settings file off disk. If it's missing or broken, use defaults."""
    if not SETTINGS_FILE.exists():
        return default_settings()
    try:
        # Read the file and parse it as JSON.
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        # Start with defaults, then overwrite with any saved values that exist.
        # This way, missing keys get safe default values.
        base = default_settings()
        base.update({k: data[k] for k in base if k in data})
        return base
    except (json.JSONDecodeError, OSError):
        # File is corrupt or unreadable — fall back to defaults.
        return default_settings()


def save_settings(data: dict[str, object]) -> None:
    """Write settings out to disk as nicely-formatted JSON."""
    try:
        SETTINGS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError:
        # If the disk is full or read-only, just silently skip.
        pass


def open_location_in_maps(address: str) -> None:
    """Open the user's default browser with a Google Maps search for the address."""
    # quote_plus encodes spaces and special characters so the URL is valid.
    webbrowser.open(f"https://www.google.com/maps/search/?api=1&query={quote_plus(address)}")


def copy_to_clipboard(widget: tk.Misc, text: str) -> None:
    """Put `text` on the system clipboard using Tk's clipboard API."""
    widget.clipboard_clear()       # remove anything already there
    widget.clipboard_append(text)  # put our new text on
    widget.update_idletasks()      # force Tk to actually push it through


def export_session_json(
    path: Path,
    session_id: str,
    selected_programs: list[str],
    user_data: dict[str, object],
    eligibility: dict[str, ProgramResult],
    locations: list[dict[str, object]],
    radius: str,
) -> None:
    """Save a complete snapshot of the session to a JSON file. This makes it
    easy to share results, archive them, or hand them off to another tool."""
    # Create the exports folder if it doesn't already exist.
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    # Build the dictionary that will become the JSON file.
    payload = {
        # When the export happened, formatted like 2026-04-29T12:34:56.
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "session_id": session_id,
        "app_version": APP_VERSION,
        "selected_programs": selected_programs,
        # JSON only handles basic types — anything else gets converted to string.
        "user_data": {k: (v if isinstance(v, (str, int, float, bool, type(None))) else str(v)) for k, v in user_data.items()},
        # Convert each ProgramResult dataclass into a plain dict for JSON.
        "eligibility": {k: {"status": v.status, "explanation": v.explanation, "passed": v.passed, "missed": v.missed} for k, v in eligibility.items()},
        # Slim down each office to just the fields worth exporting.
        "locations": [
            {
                "name": item["location"]["name"],
                "address": item["location"]["address"],
                "programs": item["programs"],
                "distance_text": item["distance_text"],
            }
            for item in locations
        ],
        "radius_miles": radius,
    }
    # Write the dictionary as pretty-printed JSON.
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


class BenefitBridgeApp(tk.Tk):
    """Main app window. This is the brain of the program.

    Quick map of how it works:
    - `_build_shell()` builds the parts that stay on screen always:
       header at the top, progress rail on the left, nav buttons at the bottom.
    - `show_step()` swaps in the body of step 1, 2, or 3.
    - `go_next()` / `go_back()` move the user between steps.
    - The actual eligibility math comes from `benefit_bridge_core.py`.
    """

    def __init__(self) -> None:
        # Initialize the underlying Tk window.
        super().__init__()
        # Replace our placeholder font with whatever nice font is installed.
        global FONT_FAMILY
        FONT_FAMILY = preferred_ui_font(self)

        # Window appearance: title bar, starting size, minimum size, bg color.
        self.title("Benefit Bridge")
        self.geometry("1180x820")    # initial width x height
        self.minsize(960, 700)       # don't let user shrink below this
        self.configure(bg=APP_BG)

        # Random short ID shown in the header so each run is identifiable.
        self.session_id = uuid.uuid4().hex[:10].upper()
        # Load saved user preferences (or defaults if none).
        self._settings = load_settings()
        # The income the user originally entered, used for "what-if" slider math.
        self._baseline_monthly: float = 0.0
        # Track scheduled timers so we can cancel them later.
        self._toast_after: str | None = None   # for the toast popup
        self._draft_after: str | None = None   # for autosave timer
        # Try to load the logo; may be None if no logo exists.
        self.brand_logo_image: tk.PhotoImage | None = self._load_brand_logo()

        # Lists/dicts that hold the wizard's state as the user fills it in.
        self.selected_programs: list[str] = []   # which checkboxes are ticked
        self.user_data: dict[str, object] = {}   # the whole household profile
        self.eligibility: dict[str, ProgramResult] = {}   # results by program
        self.location_results: list[dict[str, object]] = []  # nearby offices
        self._location_view: list[dict[str, object]] = []    # filtered/sorted view of above
        # One BooleanVar per program checkbox so Tk can track its on/off state.
        self.program_vars: dict[str, tk.BooleanVar] = {}
        for _key in PROGRAMS:
            self.program_vars[_key] = tk.BooleanVar(value=False)

        # Tk "variables" — special objects that automatically sync with widgets.
        # If you change the variable, the widget updates, and vice-versa.
        self.income_var = tk.StringVar()                         # income amount typed in
        self.income_period_var = tk.StringVar(value="Monthly")   # "Monthly" or "Yearly"
        self.name_var = tk.StringVar()                           # applicant name
        self.household_var = tk.IntVar(value=3)                  # household size
        self.location_var = tk.StringVar()                       # ZIP or city
        self.state_var = tk.StringVar(value="California")       # state dropdown
        self.age_var = tk.StringVar(value="Adult")               # age range dropdown
        self.employment_var = tk.StringVar(value=EMPLOYMENT_OPTIONS[0])  # employment dropdown
        self.residency_var = tk.BooleanVar(value=True)           # is a US resident?
        self.child_under_13_var = tk.BooleanVar(value=True)      # has young child?
        self.utility_hardship_var = tk.BooleanVar(value=False)   # behind on utilities?
        self.internet_need_var = tk.BooleanVar(value=True)       # needs internet?
        self.transportation_need_var = tk.BooleanVar(value=False)  # needs transit?
        self.radius_var = tk.StringVar(value="10")               # search radius miles

        # Variables for the results page filters.
        self.office_search_var = tk.StringVar()                  # office search text
        self.office_sort_var = tk.StringVar(value="distance")    # sort by distance/name
        self.income_scenario_pct = tk.DoubleVar(value=100.0)     # "what-if" income slider

        # Which step (0, 1, or 2) of the wizard we're on.
        self.current_step = 0
        # The labels in the left progress rail; we update their colors as steps change.
        self.step_labels: list[tk.Label] = []

        # Set up styles, build the persistent UI, hook up shortcuts.
        self._configure_styles()
        self._build_shell()
        ScrollableFrame.hook_mousewheel(self)
        self._bind_shortcuts()
        # Always start on step 0. Drafts are loaded only when the user clicks "Load draft".
        self.show_step(0)
        # Start the footer clock ticking.
        self._tick_clock()

    def _configure_styles(self) -> None:
        """Set the colors and fonts on Tk's built-in (themed) widgets so they
        match the dark theme. Without this, ttk widgets use the OS default look."""
        # ttk.Style is the object you use to change ttk widget appearance.
        self.style = ttk.Style(self)
        try:
            # "clam" is one of Tk's built-in themes — easier to customize.
            self.style.theme_use("clam")
        except tk.TclError:
            pass
        fs = self._font_size(11)  # base font size, possibly bumped up for accessibility
        # Configure each widget class with our colors and fonts.
        self.style.configure("TFrame", background=APP_BG)
        self.style.configure("TLabel", background=APP_BG, foreground=TEXT, font=(FONT_FAMILY, fs))
        self.style.configure("Title.TLabel", font=(FONT_FAMILY, self._font_size(26), "bold"), foreground=TEXT)
        self.style.configure("Subtitle.TLabel", font=(FONT_FAMILY, self._font_size(12)), foreground=MUTED)
        self.style.configure("TCheckbutton", background=CARD_BG, foreground=TEXT, font=(FONT_FAMILY, fs))
        # When a checkbox is hovered, give it a subtle bg change.
        self.style.map("TCheckbutton", background=[("active", CARD_BG_HOVER)])
        # Dropdown menu (Combobox) styling.
        self.style.configure(
            "TCombobox",
            padding=(10, 8),
            fieldbackground=INPUT_BG,
            background=INPUT_BG,
            foreground=TEXT,
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
            arrowcolor=MUTED,
        )
        # Keep the same field bg whether or not the dropdown is editable.
        self.style.map("TCombobox", fieldbackground=[("readonly", INPUT_BG)])
        # Slider style.
        self.style.configure("Horizontal.TScale", background=CARD_BG, troughcolor=INPUT_BG)
        # Scrollbar style.
        self.style.configure(
            "TScrollbar",
            background=INPUT_BG,
            troughcolor=RAIL_BG,
            bordercolor=BORDER,
            arrowcolor=MUTED,
            borderwidth=0,
            relief="flat",
            width=14,
        )
        self.style.map("TScrollbar", background=[("active", CARD_BG_HOVER), ("pressed", BORDER)])
        # Make the combobox dropdown list use our font.
        self.option_add("*TCombobox*Listbox.font", (FONT_FAMILY, fs))
        # Match dialog box background to our app background.
        self.option_add("*Dialog.background", APP_BG)

    def _font_size(self, base: int) -> int:
        """Adjust a base font size by the user's accessibility setting.
        Settings can shift sizes up or down; we clamp so it never gets crazy."""
        return int(clamp(base + int(self._settings.get("font_scale", 0)), 9, 22))

    def _button(self, parent: tk.Widget, text: str, command, variant: str = "secondary") -> ModernButton:
        # Quick helper: make a ModernButton that matches its parent's background.
        return ModernButton(parent, text, command, variant, widget_background(parent))

    def _load_brand_logo(self) -> tk.PhotoImage | None:
        """Load the logo image and shrink it if it's too big. Returns None if no logo."""
        logo_path = resolve_brand_logo_path()
        if not logo_path:
            return None
        try:
            # Tk's PhotoImage handles GIF and PNG out of the box.
            image = tk.PhotoImage(file=str(logo_path))
        except tk.TclError:
            # File exists but isn't a valid image — skip it.
            return None
        # If the logo is too tall, shrink it down by an integer factor.
        max_h = 70
        if image.height() > max_h:
            ratio = max(1, math.ceil(image.height() / max_h))
            image = image.subsample(ratio, ratio)
        return image

    def _surface(self, parent: tk.Widget) -> tk.Widget:
        """If parent is a RoundedCard, return its inner body so children sit
        on the visible card area. Otherwise just return parent unchanged."""
        return parent.body if isinstance(parent, RoundedCard) else parent

    def _card(self, parent: tk.Widget) -> RoundedCard:
        # Shortcut for making a new rounded card that matches its parent's bg.
        return RoundedCard(parent, widget_background(parent))

    def _clear(self, parent: tk.Widget) -> None:
        # Remove every widget that's a direct child of `parent`.
        for child in parent.winfo_children():
            child.destroy()

    def _focus_ring(self, widget: tk.Widget) -> None:
        """Make a widget's border light up in accent color when focused."""
        # FocusIn = user tabbed into or clicked the widget.
        widget.bind("<FocusIn>", lambda _event: widget.configure(highlightbackground=BORDER_FOCUS))
        # FocusOut = focus moved elsewhere.
        widget.bind("<FocusOut>", lambda _event: widget.configure(highlightbackground=BORDER))

    def _build_shell(self) -> None:
        """Build all the chrome that stays on screen across all three steps:
        the top header, the left progress rail, the bottom nav, the footer."""

        # === HEADER (top bar) ===========================================
        # A fixed-height bar across the top of the window.
        header = tk.Frame(self, bg=HEADER_BG, height=104, highlightbackground=BORDER, highlightthickness=1)
        header.pack(fill="x")
        # pack_propagate(False) means the frame keeps its set height even if
        # nothing inside requests that much space.
        header.pack_propagate(False)

        # Left side of the header: logo + title + slogan.
        left_brand = tk.Frame(header, bg=HEADER_BG)
        left_brand.pack(side="left", anchor="w", padx=28, pady=(14, 0))

        # Show the logo image if we successfully loaded one.
        if self.brand_logo_image is not None:
            tk.Label(left_brand, image=self.brand_logo_image, bg=HEADER_BG).pack(side="left", padx=(0, 14))

        # Stack the title and slogan vertically.
        title_group = tk.Frame(left_brand, bg=HEADER_BG)
        title_group.pack(side="left", anchor="w")

        # Big app name.
        tk.Label(
            title_group,
            text="Benefit Bridge",
            bg=HEADER_BG,
            fg=TEXT,
            font=(FONT_FAMILY, self._font_size(26), "bold"),
        ).pack(anchor="w")
        # Tagline below.
        tk.Label(
            title_group,
            text=BRAND_SLOGAN,
            bg=HEADER_BG,
            fg=ACCENT_GLOW,
            font=(FONT_FAMILY, self._font_size(13), "bold"),
        ).pack(anchor="w", pady=(4, 0))

        # Right side of header: pills + tool buttons.
        right_header = tk.Frame(header, bg=HEADER_BG)
        right_header.pack(side="right", padx=20, pady=(18, 0))

        # Two info pills, packed right-to-left.
        PillLabel(right_header, f"Session {self.session_id}", "#0c1a2e", ACCENT, HEADER_BG).pack(side="right")


        # Row of utility buttons (Export, Settings, etc.).
        tools = tk.Frame(right_header, bg=HEADER_BG)
        tools.pack(side="right", padx=(0, 8))
        self._button(tools, "Export JSON", self.action_export_json, "secondary").pack(side="left", padx=3)
        self._button(tools, "Settings", self.action_settings, "ghost").pack(side="left", padx=3)
        self._button(tools, "Shortcuts", self.action_shortcuts_dialog, "ghost").pack(side="left", padx=3)
        self._button(tools, "About", self.action_about, "ghost").pack(side="left", padx=3)

        # === BODY (everything below the header) =========================
        body = tk.Frame(self, bg=APP_BG)
        body.pack(fill="both", expand=True)

        # === LEFT PROGRESS RAIL =========================================
        # Fixed-width sidebar that shows step 1/2/3.
        self.rail = tk.Frame(body, bg=RAIL_BG, width=260, highlightbackground=BORDER, highlightthickness=1)
        self.rail.pack(side="left", fill="y")
        self.rail.pack_propagate(False)

        # The three steps shown in the rail.
        steps = [("1", "Choose subsidies"), ("2", "Household profile"), ("3", "Results & offices")]
        # Section heading for the rail.
        tk.Label(self.rail, text="Progress", bg=RAIL_BG, fg=MUTED, font=(FONT_FAMILY, self._font_size(11), "bold")).pack(anchor="w", padx=22, pady=(26, 8))
        # One label per step, saved in self.step_labels so we can recolor them later.
        for number, label in steps:
            item = tk.Label(self.rail, text=f"{number}. {label}", bg=RAIL_BG, fg=MUTED, font=(FONT_FAMILY, self._font_size(12)), padx=12, pady=11, anchor="w")
            item.pack(fill="x", padx=14, pady=3)
            self.step_labels.append(item)

        # A small disclaimer pinned to the bottom of the rail.
        self._rail_hint = tk.Label(
            self.rail,
            text=f"{BRAND_SLOGAN}. Sample rules only — always confirm with the office before applying.",
            wraplength=200,
            justify="left",
            bg=RAIL_BG,
            fg=MUTED,
            font=(FONT_FAMILY, self._font_size(10)),
        )
        self._rail_hint.pack(side="bottom", anchor="w", padx=20, pady=22)
        # When the rail is resized, recompute the wrap width of the disclaimer.
        self.rail.bind("<Configure>", self._rail_resize_hint)

        # === MAIN CONTENT AREA (right side of body) =====================
        main = tk.Frame(body, bg=APP_BG)
        main.pack(side="left", fill="both", expand=True)

        # Important: pack the nav buttons FIRST and to the bottom. Otherwise,
        # if the step's content is very tall, it could push the buttons
        # off-screen and the user couldn't continue.
        self.nav = tk.Frame(main, bg=APP_BG)
        self.nav.pack(side="bottom", fill="x", padx=26, pady=(0, 10))
        # Then pack the content area which fills the remaining space.
        self.content = tk.Frame(main, bg=APP_BG)
        self.content.pack(fill="both", expand=True, padx=26, pady=(20, 12))

        # === NAV BUTTONS (Back / Start over / Drafts / Next) ============
        self.back_button = self._button(self.nav, "Back", self.go_back, "secondary")
        self.back_button.pack(side="left")
        self._button(self.nav, "Start over", self.start_over, "ghost").pack(side="left", padx=10)
        self._button(self.nav, "Save draft", self.action_save_draft_now, "ghost").pack(side="left", padx=4)
        # Loading drafts is opt-in via this button instead of a popup at startup.
        self._button(self.nav, "Load draft", self.action_load_draft_now, "ghost").pack(side="left", padx=4)
        self.next_button = self._button(self.nav, "Next", self.go_next, "primary")
        self.next_button.pack(side="right")

        # === FOOTER (status bar at bottom) ==============================
        footer = tk.Frame(self, bg=APP_BG_ELEVATED, height=32, highlightbackground=BORDER, highlightthickness=1)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)
        # Left side: status messages (updated as actions happen).
        self.footer_left = tk.Label(
            footer,
            text="Ready",
            bg=APP_BG_ELEVATED,
            fg=MUTED,
            font=(FONT_FAMILY, self._font_size(10)),
            anchor="w",
        )
        self.footer_left.pack(side="left", padx=16, pady=6, fill="x", expand=True)
        # Right side: clock + version (updated by _tick_clock).
        self.footer_right = tk.Label(
            footer,
            text=f"v{APP_VERSION}",
            bg=APP_BG_ELEVATED,
            fg=MUTED,
            font=(FONT_FAMILY, self._font_size(10)),
            anchor="e",
        )
        self.footer_right.pack(side="right", padx=16, pady=6)

    def _rail_resize_hint(self, event: tk.Event) -> None:
        # When the left rail's width changes, recompute the wrap width
        # for the disclaimer text so it doesn't overflow.
        if event.widget == self.rail:
            self._rail_hint.configure(wraplength=max(140, int(event.width) - 36))

    def _status(self, message: str) -> None:
        # Update the message shown on the left side of the footer.
        self.footer_left.configure(text=message)

    def _tick_clock(self) -> None:
        # Update the footer's right-side label with the current time and version.
        # lstrip("0") removes a leading zero from "01:23 PM" -> "1:23 PM".
        self.footer_right.configure(text=f"{datetime.now().strftime('%I:%M %p').lstrip('0')} · v{APP_VERSION}")
        # Schedule this method to run again in 30 seconds (30_000 ms).
        self.after(30_000, self._tick_clock)

    def _toast(self, message: str, ms: int = 2800) -> None:
        """Show a temporary message box (a 'toast') that fades after `ms` milliseconds.
        We use this instead of messagebox.showinfo because messagebox blocks the user."""
        # If a previous toast is still scheduled to disappear, cancel it.
        if self._toast_after:
            try:
                self.after_cancel(self._toast_after)
            except tk.TclError:
                pass
        # Create a new top-level window for the toast.
        top = tk.Toplevel(self)
        # Hide the OS title bar/borders so it looks like a floating notification.
        top.overrideredirect(True)
        # Keep the toast on top of all other windows.
        top.attributes("-topmost", True)
        top.configure(bg=CARD_BG)
        # Outer frame with an accent-colored border.
        frm = tk.Frame(top, bg=CARD_BG, highlightbackground=ACCENT, highlightthickness=1, padx=18, pady=12)
        frm.pack()
        # The actual message text.
        tk.Label(frm, text=message, bg=CARD_BG, fg=TEXT, font=(FONT_FAMILY, self._font_size(11))).pack()
        # Position the toast near the top-center of the main window.
        x = self.winfo_rootx() + self.winfo_width() // 2 - 160
        y = self.winfo_rooty() + 72
        top.geometry(f"320x64+{max(0, x)}+{max(0, y)}")
        # Auto-destroy the toast after `ms` milliseconds.
        self._toast_after = self.after(ms, top.destroy)

    def _bind_shortcuts(self) -> None:
        """Set up keyboard shortcuts for the whole app."""
        # Binding on `self` (the root) — fires no matter which widget has focus.
        self.bind("<Control-e>", lambda _e: self.action_export_json())                       # Ctrl+E exports
        self.bind("<Control-s>", lambda _e: self.action_save_draft_now())                    # Ctrl+S saves draft
        self.bind("<Control-q>", lambda _e: (self._write_draft(), self.destroy()))           # Ctrl+Q quits (saving first)
        self.bind("<F1>", lambda _e: self.action_shortcuts_dialog())                         # F1 shows shortcuts

    def _schedule_draft_autosave(self) -> None:
        """Schedule an autosave for ~1.8 seconds from now. If called again
        before that fires, the old timer is cancelled — this is called
        'debouncing'. Result: while the user is typing, we don't save
        constantly; we save once they stop."""
        # Skip if the user disabled autosave in Settings.
        if not self._settings.get("autosave_draft", True):
            return
        # Cancel any pending autosave that hasn't fired yet.
        if self._draft_after:
            try:
                self.after_cancel(self._draft_after)
            except tk.TclError:
                pass
        # Schedule _write_draft to run in 1800 ms (1.8 seconds).
        self._draft_after = self.after(1800, self._write_draft)

    def _write_draft(self) -> None:
        """Save the current wizard state to disk so it can be reloaded later."""
        # Clear our timer reference now that we're firing.
        self._draft_after = None
        try:
            # Build the snapshot. Use simple JSON-friendly types so anyone
            # can open this file in a text editor.
            payload = {
                "saved_at": datetime.now().isoformat(timespec="seconds"),
                "step": self.current_step,
                # Pull the value out of each Tk variable.
                "programs": {k: v.get() for k, v in self.program_vars.items()},
                "name": self.name_var.get(),
                "income": self.income_var.get(),
                "income_period": self.income_period_var.get(),
                "household": self.household_var.get(),
                "location": self.location_var.get(),
                "state": self.state_var.get(),
                "age": self.age_var.get(),
                "employment": self.employment_var.get(),
                "resident": self.residency_var.get(),
                "child_under_13": self.child_under_13_var.get(),
                "utility_hardship": self.utility_hardship_var.get(),
                "internet_need": self.internet_need_var.get(),
                "transportation_need": self.transportation_need_var.get(),
            }
            # Write the JSON file.
            DRAFT_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            self._status("Draft saved locally")
        except OSError:
            # Disk problem (full, permission denied, etc.) — show a message.
            self._status("Could not save draft (disk error)")

    def _load_draft_if_present(self) -> bool:
        """Read the saved draft from disk and refill the form with it.

        Returns True if it loaded something, False if there's no draft
        or it was unreadable. We split the popup from the load logic so
        the caller can decide whether to show feedback.
        """
        if not DRAFT_FILE.exists():
            return False
        try:
            data = json.loads(DRAFT_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            # Draft file exists but is broken — give up.
            return False
        # Refill each program checkbox from the saved values.
        for k, v in data.get("programs", {}).items():
            if k in self.program_vars:
                self.program_vars[k].set(bool(v))
        # Refill all the form fields. .get(key, default) means: use
        # default if the key isn't in the saved data.
        self.name_var.set(str(data.get("name", "")))
        self.income_var.set(str(data.get("income", "")))
        self.income_period_var.set(str(data.get("income_period", "Monthly")))
        self.household_var.set(int(data.get("household", 3)))
        self.location_var.set(str(data.get("location", "")))
        self.state_var.set(str(data.get("state", "California")))
        self.age_var.set(str(data.get("age", "Adult")))
        self.employment_var.set(str(data.get("employment", EMPLOYMENT_OPTIONS[0])))
        self.residency_var.set(bool(data.get("resident", True)))
        self.child_under_13_var.set(bool(data.get("child_under_13", True)))
        self.utility_hardship_var.set(bool(data.get("utility_hardship", False)))
        self.internet_need_var.set(bool(data.get("internet_need", True)))
        self.transportation_need_var.set(bool(data.get("transportation_need", False)))
        # Update the in-memory list of selected programs based on what's checked.
        self.selected_programs = [k for k, v in self.program_vars.items() if v.get()]
        # Figure out which step to jump to (clamped to a valid value 0-2).
        step = int(data.get("step", 0))
        step = clamp(step, 0, 2)
        # If the saved step was step 3 (results), we need to recompute the results.
        if step == 2:
            if not self.selected_programs:
                # No programs picked — drop back to step 0.
                step = 0
            elif self.collect_user_data():
                # Profile is valid — recompute eligibility and locations.
                self._baseline_monthly = float(self.user_data["monthly_income"])
                self.income_scenario_pct.set(100.0)
                self.eligibility = compute_eligibility(self.selected_programs, self.user_data)
                self.refresh_location_data()
            else:
                # Profile was incomplete — drop back to step 1.
                step = 1
        self._status("Draft restored")
        self.show_step(step)
        return True

    def action_save_draft_now(self) -> None:
        # Triggered by Ctrl+S or the "Save draft" button.
        self._write_draft()
        self._toast("Draft saved to disk")

    def action_load_draft_now(self) -> None:
        """Handler for the 'Load draft' button."""
        # Give clear feedback in every case so the button never feels broken.
        if not DRAFT_FILE.exists():
            self._toast("No draft found yet")
            return
        if self._load_draft_if_present():
            self._toast("Draft loaded")
        else:
            self._toast("Draft could not be loaded")

    def action_export_json(self) -> None:
        # Triggered by Ctrl+E or the Export JSON button.
        # Need eligibility results before we can export anything meaningful.
        if not self.eligibility:
            messagebox.showinfo("Export JSON", "Run eligibility first (complete step 3).")
            return
        # Build the export filename using the session ID.
        path = EXPORT_DIR / f"benefit_bridge_export_{self.session_id}.json"
        # Hand off to the standalone export function.
        export_session_json(path, self.session_id, self.selected_programs, self.user_data, self.eligibility, self.location_results, self.radius_var.get())
        self._status(f"Exported JSON → {path.name}")
        self._toast("Session exported as JSON")

    def action_about(self) -> None:
        # Show a simple info popup with the version + tagline + session ID.
        messagebox.showinfo(
            "About Benefit Bridge",
            f"Benefit Bridge {APP_VERSION}\n\n"
            f"{BRAND_SLOGAN}\n\n"
            "Demo eligibility estimator and office finder.\n"
            "Replace sample rules and locations before real-world use.\n\n"
            f"Session ID: {self.session_id}",
        )

    def action_shortcuts_dialog(self) -> None:
        # Show the list of keyboard shortcuts.
        messagebox.showinfo(
            "Keyboard shortcuts",
            "Ctrl+E — Export last results as JSON\n"
            "Ctrl+S — Save draft now\n"
            "Ctrl+Q — Quit (saves draft first)\n"
            "F1 — This help\n",
        )

    def action_settings(self) -> None:
        """Open the Settings popup window where the user can change font size,
        reduce motion, and toggle autosave."""
        # Toplevel = a new window separate from the main one.
        win = tk.Toplevel(self)
        win.title("Settings")
        win.configure(bg=CARD_BG)
        win.geometry("420x260")
        # Inner frame with padding.
        body = tk.Frame(win, bg=CARD_BG, padx=22, pady=18)
        body.pack(fill="both", expand=True)

        # Heading.
        tk.Label(body, text="Accessibility & data", bg=CARD_BG, fg=TEXT, font=(FONT_FAMILY, 14, "bold")).pack(anchor="w")

        # === Text size row ===
        scale_row = tk.Frame(body, bg=CARD_BG)
        scale_row.pack(fill="x", pady=(14, 6))
        tk.Label(scale_row, text="Text size offset", bg=CARD_BG, fg=MUTED, font=(FONT_FAMILY, 11)).pack(side="left")
        # Tk variable holding the current text-size offset value.
        var = tk.IntVar(value=int(self._settings.get("font_scale", 0)))
        # Spinbox = number input with up/down arrows. Range -2 to +4.
        tk.Spinbox(scale_row, from_=-2, to=4, textvariable=var, width=6, bg=INPUT_BG, fg=TEXT, buttonbackground=BORDER).pack(side="right")

        # === Reduce motion checkbox ===
        motion = tk.BooleanVar(value=bool(self._settings.get("reduce_motion", False)))
        tk.Checkbutton(body, text="Reduce motion (disable button pulse)", variable=motion, bg=CARD_BG, fg=TEXT, selectcolor=INPUT_BG, activebackground=CARD_BG, activeforeground=TEXT).pack(anchor="w", pady=8)

        # === Autosave checkbox ===
        autosave = tk.BooleanVar(value=bool(self._settings.get("autosave_draft", True)))
        tk.Checkbutton(body, text="Autosave draft while you work", variable=autosave, bg=CARD_BG, fg=TEXT, selectcolor=INPUT_BG, activebackground=CARD_BG, activeforeground=TEXT).pack(anchor="w")

        # Inner function that runs when "Save" is clicked.
        def save_and_close() -> None:
            # Pull the current values out of the variables and put them in our settings dict.
            self._settings["font_scale"] = int(var.get())
            self._settings["reduce_motion"] = bool(motion.get())
            self._settings["autosave_draft"] = bool(autosave.get())
            # Persist to disk.
            save_settings(self._settings)
            # Re-apply styles so font size changes show up immediately.
            self._configure_styles()
            self._status("Settings saved")
            # Close the settings window.
            win.destroy()

        # The Save button at the bottom-right.
        self._button(body, "Save", save_and_close, "primary").pack(anchor="e", pady=(18, 0))

    def _text_wrap(self) -> int:
        """How wide a paragraph of text should wrap, based on the current
        window size. We recompute this each time so it adapts when the
        window is resized."""
        # Force pending layout updates so winfo_width() returns the real size.
        self.update_idletasks()
        try:
            # Use the step host frame's width if it exists, otherwise the content area.
            ref = getattr(self, "_step_host", self.content)
            # Clamp between 280 and 860 so it doesn't get absurdly narrow or wide.
            return max(280, min(860, int(ref.winfo_width()) - 56))
        except tk.TclError:
            return 560  # fallback if Tk isn't ready

    def _pane_text_wrap(self) -> int:
        """Same idea as _text_wrap but for the two-column results page."""
        self.update_idletasks()
        try:
            # Each pane is ~half the window minus padding.
            return max(300, min(720, int(self.winfo_width()) // 2 - 120))
        except tk.TclError:
            return 420

    def show_step(self, step: int) -> None:
        """Switch the wizard to the given step (0, 1, or 2)."""
        self.current_step = step
        # Wipe whatever was in the content area before.
        self._clear(self.content)
        # Wrap the step's content in a scroll frame so long pages still fit.
        # The nav bar at the bottom stays put even if content scrolls.
        step_scroll = ScrollableFrame(self.content, APP_BG)
        step_scroll.pack(fill="both", expand=True)
        # `_step_host` is where step builders pack their widgets.
        self._step_host = step_scroll.inner
        # Update the colors of the step labels in the left rail.
        self._update_step_rail()
        # Build the right body for this step and update the Next button label.
        if step == 0:
            self._build_program_screen()
            self.back_button.configure(state="disabled")
            self.next_button.configure(text="Continue")
        elif step == 1:
            self._build_info_screen()
            self.back_button.configure(state="normal")
            self.next_button.configure(text="Check Eligibility")
        else:
            self._build_results_screen()
            self.back_button.configure(state="normal")
            self.next_button.configure(text="Draft Application")
        # Schedule an autosave whenever a step shows up.
        self._schedule_draft_autosave()
        # Update the footer message.
        self._status(f"Step {step + 1} of 3")

    def _update_step_rail(self) -> None:
        """Recolor the three step labels in the left rail to show progress.
        Active = accent color, completed = green, future = muted gray."""
        for index, label in enumerate(self.step_labels):
            if index == self.current_step:
                # Highlighted current step.
                label.configure(bg=CARD_BG, fg=ACCENT, font=(FONT_FAMILY, self._font_size(12), "bold"))
            elif index < self.current_step:
                # Completed step (green).
                label.configure(bg=RAIL_BG, fg=SUCCESS, font=(FONT_FAMILY, self._font_size(12), "bold"))
            else:
                # Upcoming step (muted).
                label.configure(bg=RAIL_BG, fg=MUTED, font=(FONT_FAMILY, self._font_size(12)))

    def _build_program_screen(self) -> None:
        """Build step 1: pick which programs to check."""
        # === Page header text ===
        ttk.Label(self._step_host, text="Welcome", style="Title.TLabel").pack(anchor="w")
        tk.Label(
            self._step_host,
            text="Pick programs, answer one shared profile, then review eligibility, offices, and a printable packing list.",
            bg=APP_BG,
            fg=MUTED,
            font=(FONT_FAMILY, self._font_size(12)),
            wraplength=self._text_wrap(),
            justify="left",
        ).pack(anchor="w", pady=(6, 14))

        # === Three info "chip" cards across the top ===
        chips = tk.Frame(self._step_host, bg=APP_BG)
        chips.pack(fill="x", pady=(0, 22))
        # Each chip's wrap width is about a third of the available area.
        chip_wrap = max(200, min(280, self._text_wrap() // 3))
        # Loop over the chip data and build one card per item.
        for label, sub in (
            ("Smart reuse", "One questionnaire powers every program you pick."),
            ("Office radar", "Distance-ranked sites — hundreds of demo ZIP codes statewide."),
            ("Audit trail", "CSV history + JSON export for handoff."),
        ):
            c = self._card(chips)
            c.pack(side="left", fill="x", expand=True, padx=(0, 14))
            cb = self._surface(c)  # the inner body of the rounded card
            # Bold title.
            tk.Label(cb, text=label, bg=CARD_BG, fg=TEXT, font=(FONT_FAMILY, self._font_size(13), "bold")).pack(anchor="w", padx=18, pady=(16, 6))
            # Description text.
            tk.Label(cb, text=sub, bg=CARD_BG, fg=MUTED, font=(FONT_FAMILY, self._font_size(11)), wraplength=chip_wrap, justify="left").pack(anchor="w", padx=18, pady=(0, 18))

        # === Main "pick subsidies" card ===
        card = self._card(self._step_host)
        card.pack(fill="x", expand=False)
        card_body = self._surface(card)

        # Card heading.
        tk.Label(card_body, text="Which type of subsidy?", bg=CARD_BG, fg=TEXT, font=(FONT_FAMILY, self._font_size(20), "bold")).pack(anchor="w", padx=24, pady=(24, 8))
        # Subtitle / instruction.
        tk.Label(
            card_body,
            text="Choose one or more programs. Use Select all if you want a full scan.",
            bg=CARD_BG,
            fg=MUTED,
            font=(FONT_FAMILY, self._font_size(11)),
            wraplength=self._text_wrap() - 48,
            justify="left",
        ).pack(anchor="w", padx=24, pady=(0, 18))

        # Wrap width for each program's description.
        row_wrap = max(320, self._text_wrap() - 72)
        # Build one row for each program in the PROGRAMS dict.
        for key, program in PROGRAMS.items():
            # Outer block with a thin border.
            block = tk.Frame(card_body, bg=CARD_BG_HOVER, highlightbackground=BORDER, highlightthickness=1)
            block.pack(fill="x", padx=18, pady=12)
            # Inner padded container.
            inner = tk.Frame(block, bg=CARD_BG_HOVER)
            inner.pack(fill="x", padx=16, pady=16)
            # Top row: color swatch + checkbox + program name.
            head = tk.Frame(inner, bg=CARD_BG_HOVER)
            head.pack(fill="x", anchor="w")
            # Vertical color bar matching the program's accent color.
            swatch = tk.Frame(head, bg=program["color"], width=8, height=36)
            swatch.pack(side="left", fill="y", padx=(0, 14))
            swatch.pack_propagate(False)
            # The checkbox itself, hooked up to the BooleanVar for this program.
            ttk.Checkbutton(head, text=program["name"], variable=self.program_vars[key]).pack(side="left", anchor="nw", pady=(2, 0))
            # The program's description below the checkbox row.
            tk.Label(
                inner,
                text=program["description"],
                bg=CARD_BG_HOVER,
                fg=SUBTEXT,
                font=(FONT_FAMILY, self._font_size(11)),
                wraplength=row_wrap,
                justify="left",
            ).pack(anchor="w", padx=(22, 8), pady=(12, 0))

        # === Buttons at the bottom of the card ===
        actions = tk.Frame(card_body, bg=CARD_BG)
        actions.pack(fill="x", padx=22, pady=(22, 26))
        self._button(actions, "Select all", self.select_all_programs, "secondary").pack(side="left")
        self._button(actions, "Clear", self.clear_programs, "ghost").pack(side="left", padx=10)
        self._button(actions, "Suggest common bundle", self.suggest_program_bundle, "accent").pack(side="right")

    def _build_info_screen(self) -> None:
        """Build step 2: the form for the household profile."""
        # === Title and intro paragraph ===
        ttk.Label(self._step_host, text="Household profile", style="Title.TLabel").pack(anchor="w")
        tk.Label(
            self._step_host,
            text="Answer once — every selected program reuses this profile. You can go back and edit before running the check.",
            bg=APP_BG,
            fg=MUTED,
            font=(FONT_FAMILY, self._font_size(12)),
            wraplength=self._text_wrap(),
            justify="left",
        ).pack(anchor="w", pady=(6, 16))

        # === ZIP code tip card ===
        tip = self._card(self._step_host)
        tip.pack(fill="x", pady=(0, 12))
        tb = self._surface(tip)
        tk.Label(
            tb,
            text="Tip: enter any 5-digit ZIP from the expanded demo set (e.g. 95125, 94110, 90026, 92104, 95825, 93722, 92806) for distance math; cities still match by name.",
            bg=CARD_BG,
            fg=ACCENT,
            font=(FONT_FAMILY, self._font_size(10)),
            wraplength=self._text_wrap() - 36,
            justify="left",
        ).pack(anchor="w", padx=18, pady=14)

        # === Two-column form layout ===
        # Left column = basic info, right column = program-specific yes/no questions.
        wrapper = tk.Frame(self._step_host, bg=APP_BG)
        wrapper.pack(fill="both", expand=True)
        left = self._card(wrapper)
        right = self._card(wrapper)
        left.pack(side="left", fill="both", expand=True, padx=(0, 12))
        right.pack(side="left", fill="both", expand=True, padx=(12, 0))

        # === Left column: basic personal info ===
        self._section_title(left, "Basic personal info")
        # Each _field_row builds a labeled row with a widget under it.
        # The lambda creates the actual input widget — done lazily so we
        # control which parent row it goes into.
        self._field_row(left, "Name", lambda row: self._entry(row, self.name_var), "Enter the applicant's full name.")
        self._field_row(left, "Income", lambda row: self._income_field(row), "Enter monthly income, or yearly income and choose Yearly.")
        self._field_row(left, "Household size", lambda row: self._spinbox(row, self.household_var, 1, 12), "Everyone who shares income and expenses.")
        self._field_row(left, "State", lambda row: self._combo(row, self.state_var, STATE_OPTIONS), "Choose the state for your location.")
        self._field_row(left, "ZIP code", lambda row: self._entry(row, self.location_var), "Used to find nearby offices in the sample dataset.")
        self._field_row(left, "Age range", lambda row: self._combo(row, self.age_var, AGE_OPTIONS), "")
        # Employment goes in the right column (continuing the form there).
        self._field_row(right, "Employment or school status", lambda row: self._combo(row, self.employment_var, EMPLOYMENT_OPTIONS), "")

        # === Right column: program-specific yes/no questions ===
        self._section_title(right, "Program-specific details")
        self._check_row(right, "US resident or qualified non-citizen", self.residency_var, "Used by food, utility, and internet sample checks.")
        self._check_row(right, "A child in the household is under age 13", self.child_under_13_var, "Used by the child-care subsidy check.")
        self._check_row(right, "Behind on utility bill or received a shutoff notice", self.utility_hardship_var, "Used by utility bill help.")
        self._check_row(right, "Need home internet for work, school, health, or benefits", self.internet_need_var, "Used by internet subsidy.")
        self._check_row(right, "Need transportation for work, school, or medical appointments", self.transportation_need_var, "Used by transportation vouchers.")

        # === Bottom summary card: which programs are selected ===
        # Join the short names of selected programs with commas.
        selected_names = ", ".join(PROGRAMS[key]["short_name"] for key in self.selected_programs)
        summary = self._card(self._step_host)
        summary.pack(fill="x", pady=(18, 0))
        summary_body = self._surface(summary)
        tk.Label(summary_body, text="Selected programs", bg=CARD_BG, fg=MUTED, font=(FONT_FAMILY, self._font_size(10), "bold")).pack(anchor="w", padx=18, pady=(14, 2))
        tk.Label(
            summary_body,
            # If nothing is selected yet, show "None yet" instead of an empty string.
            text=selected_names or "None yet",
            bg=CARD_BG,
            fg=TEXT,
            font=(FONT_FAMILY, self._font_size(12)),
            wraplength=self._text_wrap() - 36,
            justify="left",
        ).pack(anchor="w", padx=18, pady=(0, 14))

    def _build_results_screen(self) -> None:
        """Build step 3: the results workspace (digest stats, controls, list of offices)."""
        # === Title and intro paragraph ===
        ttk.Label(self._step_host, text="Results workspace", style="Title.TLabel").pack(anchor="w")
        tk.Label(
            self._step_host,
            text="Estimates only — not a government decision. Use filters, what-if income, maps, and exports to prepare a real visit.",
            bg=APP_BG,
            fg=MUTED,
            font=(FONT_FAMILY, self._font_size(12)),
            wraplength=self._text_wrap(),
            justify="left",
        ).pack(anchor="w", pady=(10, 18))

        # === Count how many programs landed in each status bucket ===
        # `sum(1 for k in ...)` is a quick way to count things matching a condition.
        highly = sum(1 for k in self.selected_programs if self.eligibility[k].status == "Highly eligible")
        partial = sum(1 for k in self.selected_programs if self.eligibility[k].status == "Partially eligible")
        unlikely = sum(1 for k in self.selected_programs if self.eligibility[k].status == "Unlikely")

        # === Digest card: three big numbers ===
        digest = self._card(self._step_host)
        digest.pack(fill="x", pady=(0, 18))
        dg = self._surface(digest)
        rowd = tk.Frame(dg, bg=CARD_BG)
        rowd.pack(fill="x", padx=22, pady=(22, 22))
        # Build one big-number cell per status bucket.
        for title, value, color in (
            ("Highly eligible", str(highly), SUCCESS),
            ("Partially eligible", str(partial), WARNING),
            ("Unlikely", str(unlikely), MUTED),
        ):
            cell = tk.Frame(rowd, bg=CARD_BG)
            cell.pack(side="left", padx=(0, 44))
            # Large colored number on top.
            tk.Label(cell, text=value, bg=CARD_BG, fg=color, font=(FONT_FAMILY, self._font_size(26), "bold")).pack(anchor="w", pady=(0, 6))
            # Smaller label below it.
            tk.Label(cell, text=title, bg=CARD_BG, fg=MUTED, font=(FONT_FAMILY, self._font_size(11)), wraplength=140, justify="left").pack(anchor="w")

        # === Controls card: location, radius, action buttons, what-if slider, search/sort ===
        controls = self._card(self._step_host)
        controls.pack(fill="x", pady=(0, 18))
        controls_body = self._surface(controls)

        # Top row of the controls card: just the user's location.
        top = tk.Frame(controls_body, bg=CARD_BG)
        top.pack(fill="x", padx=22, pady=(20, 14))
        loc_lbl = tk.Label(
            top,
            # .get(key, default) returns "Not provided" if no location was set.
            text=f"Location: {self.user_data.get('location_input', 'Not provided')}",
            bg=CARD_BG,
            fg=TEXT,
            font=(FONT_FAMILY, self._font_size(13), "bold"),
            wraplength=self._text_wrap() - 80,
            justify="left",
        )
        loc_lbl.pack(anchor="w", fill="x")

        # Second row: radius picker + action buttons.
        row_btns = tk.Frame(controls_body, bg=CARD_BG)
        row_btns.pack(fill="x", padx=22, pady=(0, 16))
        # Radius dropdown grouped together.
        rad_frame = tk.Frame(row_btns, bg=CARD_BG)
        rad_frame.pack(side="left")
        tk.Label(rad_frame, text="Search radius", bg=CARD_BG, fg=MUTED, font=(FONT_FAMILY, self._font_size(11))).pack(side="left", padx=(0, 8))
        ttk.Combobox(rad_frame, values=RADIUS_OPTIONS, width=7, state="readonly", textvariable=self.radius_var).pack(side="left")
        tk.Label(rad_frame, text="miles", bg=CARD_BG, fg=MUTED, font=(FONT_FAMILY, self._font_size(11))).pack(side="left", padx=(8, 16))
        self._button(rad_frame, "Update map list", self.refresh_locations, "secondary").pack(side="left", padx=6)
        # Other action buttons in the same row.
        self._button(row_btns, "Save CSV history", self.save_case_history, "ghost").pack(side="left", padx=6)
        self._button(row_btns, "Copy summary", self.copy_results_summary, "ghost").pack(side="left", padx=6)
        self._button(row_btns, "Edit profile", lambda: self.show_step(1), "ghost").pack(side="right", padx=6)

        # Third row: the "what-if" income slider.
        mid = tk.Frame(controls_body, bg=CARD_BG)
        mid.pack(fill="x", padx=22, pady=(8, 18))
        tk.Label(
            mid,
            text="What-if income (percent of the amount you entered — drag, then release to recalculate)",
            bg=CARD_BG,
            fg=MUTED,
            font=(FONT_FAMILY, self._font_size(11)),
            wraplength=self._text_wrap() - 48,
            justify="left",
        ).pack(anchor="w", pady=(0, 10))
        # Slider row: the slider on the left, a "100%" label on the right.
        sc_row = tk.Frame(mid, bg=CARD_BG)
        sc_row.pack(fill="x", pady=(4, 0))
        # Scale (slider) from 50% to 150% of the user's actual income.
        scale = ttk.Scale(sc_row, from_=50, to=150, variable=self.income_scenario_pct, orient="horizontal")
        scale.pack(side="left", fill="x", expand=True, padx=(0, 12))
        # Label that shows the current slider value.
        self._scenario_value_lbl = tk.Label(
            sc_row,
            text="100%",
            bg=CARD_BG,
            fg=ACCENT,
            font=(FONT_FAMILY, self._font_size(12), "bold"),
            width=7,
        )
        self._scenario_value_lbl.pack(side="right")

        # Helper that updates the percent label as the slider moves.
        def _slide(_event: tk.Event | None = None) -> None:
            self._scenario_value_lbl.configure(text=f"{self.income_scenario_pct.get():.0f}%")

        # While dragging, update the label live.
        scale.bind("<Motion>", _slide)
        # Only recompute eligibility when the user lets go of the slider.
        # (Recomputing on every pixel move would be too slow.)
        scale.bind("<ButtonRelease-1>", lambda _e: self.apply_income_scenario())
        # Show the initial label.
        _slide()

        # Bottom row: office search + sort + filter buttons.
        bot = tk.Frame(controls_body, bg=CARD_BG)
        bot.pack(fill="x", padx=22, pady=(4, 22))
        tk.Label(bot, text="Office list", bg=CARD_BG, fg=TEXT, font=(FONT_FAMILY, self._font_size(12), "bold")).pack(anchor="w", pady=(0, 10))
        row_f = tk.Frame(bot, bg=CARD_BG)
        row_f.pack(fill="x", pady=(0, 8))
        # Search box.
        tk.Label(row_f, text="Search", bg=CARD_BG, fg=MUTED, font=(FONT_FAMILY, self._font_size(11))).pack(side="left")
        se = tk.Entry(
            row_f,
            textvariable=self.office_search_var,
            bg=INPUT_BG,
            fg=TEXT,
            insertbackground=TEXT,         # cursor color
            relief="flat",
            bd=0,
            width=32,
            font=(FONT_FAMILY, self._font_size(11)),
            highlightthickness=2,
            highlightbackground=BORDER,
            highlightcolor=BORDER_FOCUS,   # color when the entry is focused
        )
        self._focus_ring(se)               # accent border on focus
        se.pack(side="left", padx=(10, 20), ipady=8)
        # Sort dropdown.
        tk.Label(row_f, text="Sort by", bg=CARD_BG, fg=MUTED, font=(FONT_FAMILY, self._font_size(11))).pack(side="left")
        ttk.Combobox(row_f, values=("distance", "name"), width=11, state="readonly", textvariable=self.office_sort_var).pack(side="left", padx=(10, 14))
        self._button(row_f, "Apply filter", self._office_filter_changed, "secondary").pack(side="left", padx=6)
        self._button(row_f, "Copy all addresses", self.copy_all_office_addresses, "ghost").pack(side="right", padx=6)

        # === Document checklist card ===
        docs = self._card(self._step_host)
        docs.pack(fill="x", pady=(0, 18))
        db = self._surface(docs)
        tk.Label(db, text="Visit checklist (sample)", bg=CARD_BG, fg=TEXT, font=(FONT_FAMILY, self._font_size(15), "bold")).pack(anchor="w", padx=22, pady=(20, 6))
        tk.Label(
            db,
            text="Bring originals when possible. Offices may ask for different items.",
            bg=CARD_BG,
            fg=MUTED,
            font=(FONT_FAMILY, self._font_size(11)),
            wraplength=self._text_wrap() - 48,
            justify="left",
        ).pack(anchor="w", padx=22, pady=(0, 14))
        # Build the lines for the checklist: master list first, then any
        # extra items needed for each selected program.
        lines: list[str] = []
        lines.extend(f"• {item}" for item in MASTER_DOCUMENT_LIST)
        for pk in self.selected_programs:
            for line in PROGRAM_CHECKLISTS.get(pk, []):
                # Tag program-specific lines with the short name in brackets.
                lines.append(f"• [{PROGRAMS[pk]['short_name']}] {line}")
        # "Well" is just the inset background that frames the read-only Text widget.
        well = tk.Frame(db, bg=BORDER, bd=0, highlightthickness=0)
        well.pack(fill="x", padx=22, pady=(0, 22))
        # Multi-line read-only text area showing the checklist.
        chk = tk.Text(
            well,
            height=11,
            wrap="word",
            bg=INPUT_BG,
            fg=SUBTEXT,
            font=(FONT_FAMILY, self._font_size(11)),
            relief="flat",
            highlightthickness=0,
            bd=0,
            padx=18,
            pady=18,
        )
        # Insert all lines starting at the very beginning ("1.0" = line 1, char 0).
        chk.insert("1.0", "\n".join(lines))
        # Disable so the user can't type into it (still selectable for copying).
        chk.configure(state="disabled")
        chk.pack(fill="x", padx=3, pady=3)

        # === Two-column split pane: eligibility cards | nearby offices ===
        # PanedWindow lets the user drag the divider between the two columns.
        pane = tk.PanedWindow(self._step_host, orient="horizontal", bg=APP_BG, sashwidth=10, bd=0, sashrelief="flat")
        pane.pack(fill="both", expand=True, pady=(4, 0))
        # Each side is its own scrollable frame.
        self.results_frame = ScrollableFrame(pane, background=APP_BG)
        self.locations_frame = ScrollableFrame(pane, background=APP_BG)
        # Add to the pane with minimum widths so neither side disappears.
        pane.add(self.results_frame, minsize=440)
        pane.add(self.locations_frame, minsize=460)

        # Calculate the filtered/sorted office list and render both columns.
        self._sync_location_view()
        self._render_eligibility_cards()
        self._render_location_cards()

    def apply_income_scenario(self, _event: tk.Event | None = None) -> None:
        """Re-run rules against hypothetical monthly income (slider % of saved baseline)."""
        if not self.user_data:
            return
        pct = float(self.income_scenario_pct.get())
        u = dict(self.user_data)
        u["monthly_income"] = self._baseline_monthly * (pct / 100.0)
        self.eligibility = compute_eligibility(self.selected_programs, u)
        self.refresh_location_data()
        self._sync_location_view()
        self._render_eligibility_cards()
        self._render_location_cards()
        self._status(f"What-if income applied at {pct:.0f}% of reported monthly")

    def _sync_location_view(self) -> None:
        """Filter + sort the in-memory office list for the right-hand column."""
        q = self.office_search_var.get().strip().lower()
        items = list(self.location_results)
        if q:
            items = [
                x
                for x in items
                if q in str(x["location"]["name"]).lower()
                or q in str(x["location"]["address"]).lower()
                or q in str(x["location"].get("city", "")).lower()
            ]
        mode = self.office_sort_var.get()
        if mode == "name":
            items.sort(key=lambda it: str(it["location"]["name"]).lower())
        else:
            items.sort(key=lambda it: (9999.0 if it["distance"] is None else float(it["distance"]), str(it["location"]["name"]).lower()))
        self._location_view = items

    def _office_filter_changed(self, *_args: object) -> None:
        if self.current_step != 2:
            return
        self._sync_location_view()
        self._render_location_cards()

    def copy_results_summary(self) -> None:
        """Clipboard-friendly snapshot for email or SMS to a navigator."""
        lines = [
            f"Benefit Bridge session {self.session_id}",
            f"Location: {self.user_data.get('location_input', '')}",
            f"Monthly income (baseline): {format_money(self._baseline_monthly)}",
            "",
        ]
        for k in self.selected_programs:
            r = self.eligibility[k]
            lines.append(f"{PROGRAMS[k]['short_name']}: {r.status}")
        copy_to_clipboard(self, "\n".join(lines))
        self._toast("Summary copied to clipboard")

    def copy_all_office_addresses(self) -> None:
        if not self._location_view:
            self._toast("No offices in the current list")
            return
        block = "\n\n".join(f"{item['location']['name']}\n{item['location']['address']}" for item in self._location_view)
        copy_to_clipboard(self, block)
        self._toast("All visible addresses copied")

    def _render_eligibility_cards(self) -> None:
        self._clear(self.results_frame.inner)
        wl = self._pane_text_wrap()
        tk.Label(self.results_frame.inner, text="Eligibility detail", bg=APP_BG, fg=TEXT, font=(FONT_FAMILY, self._font_size(17), "bold")).pack(anchor="w", pady=(0, 16))
        for program_key in self.selected_programs:
            program = PROGRAMS[program_key]
            result = self.eligibility[program_key]
            card = self._card(self.results_frame.inner)
            card.pack(fill="x", pady=(0, 18), padx=(0, 10))
            card_body = self._surface(card)
            tk.Label(
                card_body,
                text=program["name"],
                bg=CARD_BG,
                fg=TEXT,
                font=(FONT_FAMILY, self._font_size(14), "bold"),
                wraplength=wl,
                justify="left",
            ).pack(anchor="w", padx=22, pady=(20, 8))
            badge_row = tk.Frame(card_body, bg=CARD_BG)
            badge_row.pack(fill="x", padx=22, pady=(0, 10))
            PillLabel(
                badge_row,
                status_pill_caption(result.status),
                STATUS_COLORS[result.status],
                STATUS_TEXT_COLORS[result.status],
                CARD_BG,
            ).pack(anchor="w")
            tk.Label(
                card_body,
                text=result.explanation,
                bg=CARD_BG,
                fg=SUBTEXT,
                font=(FONT_FAMILY, self._font_size(11)),
                wraplength=wl,
                justify="left",
            ).pack(anchor="w", padx=22, pady=(0, 14))
            if result.passed:
                self._mini_list(card_body, "Rules met", result.passed, SUCCESS)
            if result.missed:
                self._mini_list(card_body, "Needs review", result.missed, WARNING)

    def _render_location_cards(self) -> None:
        self._clear(self.locations_frame.inner)
        wl = self._pane_text_wrap()
        tk.Label(self.locations_frame.inner, text="Nearby offices", bg=APP_BG, fg=TEXT, font=(FONT_FAMILY, self._font_size(17), "bold")).pack(anchor="w", pady=(0, 16))
        eligible_keys = self.programs_for_locations()
        if not eligible_keys:
            self._empty_card(
                self.locations_frame.inner,
                "No offices shown",
                "Offices appear only for programs marked Highly eligible or Partially eligible. Increase income scenario or adjust answers, then update the list.",
            )
            return
        if not self.location_results:
            self._empty_card(
                self.locations_frame.inner,
                "No offices in radius",
                "Try a larger radius or a sample city such as Sunnyvale, San Jose, Oakland, Los Angeles, San Diego, or Sacramento.",
            )
            return
        if not self._location_view:
            self._empty_card(self.locations_frame.inner, "No filter matches", "Clear the office search box or type part of a name, city, or street.")
            return
        for item in self._location_view:
            location = item["location"]
            matching_programs = item["programs"]
            distance_text = item["distance_text"]
            card = self._card(self.locations_frame.inner)
            card.pack(fill="x", pady=(0, 18), padx=(0, 10))
            card_body = self._surface(card)
            tk.Label(
                card_body,
                text=location["name"],
                bg=CARD_BG,
                fg=TEXT,
                font=(FONT_FAMILY, self._font_size(14), "bold"),
                wraplength=wl,
                justify="left",
            ).pack(anchor="w", padx=22, pady=(20, 8))
            meta = tk.Frame(card_body, bg=CARD_BG)
            meta.pack(fill="x", padx=22, pady=(0, 10))
            PillLabel(meta, distance_text, "#273549", TEXT, CARD_BG).pack(anchor="w")
            tk.Label(
                card_body,
                text=location["address"],
                bg=CARD_BG,
                fg=MUTED,
                font=(FONT_FAMILY, self._font_size(11)),
                wraplength=wl,
                justify="left",
            ).pack(anchor="w", padx=22, pady=(0, 10))
            program_names = ", ".join(PROGRAMS[key]["short_name"] for key in matching_programs)
            best_status = self.best_status_for(matching_programs)
            next_step = f"Handles {program_names}. Best match status for overlapping programs: {best_status}."
            tk.Label(
                card_body,
                text=next_step,
                bg=CARD_BG,
                fg=SUBTEXT,
                font=(FONT_FAMILY, self._font_size(11)),
                wraplength=wl,
                justify="left",
            ).pack(anchor="w", padx=22, pady=(0, 14))
            actions = tk.Frame(card_body, bg=CARD_BG)
            actions.pack(fill="x", padx=22, pady=(0, 22))
            addr = str(location["address"])
            self._button(actions, "Copy address", partial(copy_to_clipboard, self, addr), "secondary").pack(side="left", padx=(0, 6))
            self._button(actions, "Open in Maps", partial(open_location_in_maps, addr), "ghost").pack(side="left")

    def _mini_list(self, parent: tk.Widget, title: str, items: list[str], color: str) -> None:
        parent = self._surface(parent)
        container = tk.Frame(parent, bg=CARD_BG)
        container.pack(fill="x", padx=22, pady=(0, 14))
        wl = max(280, self._pane_text_wrap() - 24)
        tk.Label(container, text=title, bg=CARD_BG, fg=color, font=(FONT_FAMILY, self._font_size(11), "bold")).pack(anchor="w", pady=(0, 6))
        for item in items:
            tk.Label(container, text=f"• {item}", bg=CARD_BG, fg=MUTED, font=(FONT_FAMILY, self._font_size(11)), wraplength=wl, justify="left").pack(anchor="w", pady=(4, 0))

    def _empty_card(self, parent: tk.Widget, title: str, body: str) -> None:
        card = self._card(parent)
        card.pack(fill="x", padx=(0, 10), pady=(0, 18))
        card_body = self._surface(card)
        wl = max(280, self._pane_text_wrap() - 24)
        tk.Label(card_body, text=title, bg=CARD_BG, fg=TEXT, font=(FONT_FAMILY, self._font_size(14), "bold")).pack(anchor="w", padx=22, pady=(20, 8))
        tk.Label(card_body, text=body, bg=CARD_BG, fg=MUTED, font=(FONT_FAMILY, self._font_size(11)), wraplength=wl, justify="left").pack(anchor="w", padx=22, pady=(0, 22))

    def _section_title(self, parent: tk.Widget, text: str) -> None:
        parent = self._surface(parent)
        tk.Label(parent, text=text, bg=CARD_BG, fg=TEXT, font=(FONT_FAMILY, self._font_size(15), "bold")).pack(anchor="w", padx=18, pady=(18, 8))

    def _income_field(self, parent: tk.Widget) -> tk.Frame:
        parent = self._surface(parent)
        frame = tk.Frame(parent, bg=CARD_BG)
        entry = tk.Entry(
            frame,
            textvariable=self.income_var,
            bg=INPUT_BG,
            fg=TEXT,
            insertbackground=TEXT,
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=BORDER_FOCUS,
            font=(FONT_FAMILY, self._font_size(11)),
        )
        self._focus_ring(entry)
        entry.pack(side="left", fill="x", expand=True)
        combo = ttk.Combobox(frame, values=["Monthly", "Yearly"], state="readonly", textvariable=self.income_period_var, width=10)
        combo.pack(side="left", padx=(8, 0))
        return frame

    def _entry(self, parent: tk.Widget, variable: tk.StringVar) -> tk.Entry:
        parent = self._surface(parent)
        entry = tk.Entry(
            parent,
            textvariable=variable,
            bg=INPUT_BG,
            fg=TEXT,
            insertbackground=TEXT,
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=BORDER_FOCUS,
            font=(FONT_FAMILY, self._font_size(11)),
        )
        self._focus_ring(entry)
        return entry

    def _spinbox(self, parent: tk.Widget, variable: tk.IntVar, minimum: int, maximum: int) -> tk.Spinbox:
        parent = self._surface(parent)
        spinbox = tk.Spinbox(
            parent,
            from_=minimum,
            to=maximum,
            textvariable=variable,
            bg=INPUT_BG,
            fg=TEXT,
            insertbackground=TEXT,
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=BORDER_FOCUS,
            width=8,
            font=(FONT_FAMILY, self._font_size(11)),
            buttonbackground=BORDER,
        )
        self._focus_ring(spinbox)
        return spinbox

    def _combo(self, parent: tk.Widget, variable: tk.StringVar, values: list[str]) -> ttk.Combobox:
        return ttk.Combobox(self._surface(parent), values=values, state="readonly", textvariable=variable)

    def _field_row(self, parent: tk.Widget, label: str, widget_factory, hint: str) -> None:
        parent = self._surface(parent)
        row = tk.Frame(parent, bg=CARD_BG)
        row.pack(fill="x", padx=18, pady=9)
        tk.Label(row, text=label, bg=CARD_BG, fg=TEXT, font=(FONT_FAMILY, self._font_size(10), "bold")).pack(anchor="w")
        widget = widget_factory(row)
        widget.pack(fill="x", pady=(5, 2))
        if hint:
            tk.Label(row, text=hint, bg=CARD_BG, fg=MUTED, font=(FONT_FAMILY, self._font_size(9)), wraplength=max(220, self._text_wrap() // 2 - 40), justify="left").pack(anchor="w")

    def _check_row(self, parent: tk.Widget, label: str, variable: tk.BooleanVar, hint: str) -> None:
        parent = self._surface(parent)
        row = tk.Frame(parent, bg=CARD_BG)
        row.pack(fill="x", padx=18, pady=10)
        ttk.Checkbutton(row, text=label, variable=variable).pack(anchor="w")
        tk.Label(row, text=hint, bg=CARD_BG, fg=MUTED, font=(FONT_FAMILY, self._font_size(9)), wraplength=max(220, self._text_wrap() // 2 - 40), justify="left").pack(anchor="w", padx=24, pady=(2, 0))

    def select_all_programs(self) -> None:
        for variable in self.program_vars.values():
            variable.set(True)

    def clear_programs(self) -> None:
        for variable in self.program_vars.values():
            variable.set(False)

    def suggest_program_bundle(self) -> None:
        """One-click preset for the most common “household basics” combo in demos."""
        for key in ("food", "utility", "internet"):
            self.program_vars[key].set(True)
        self._toast("Applied suggested bundle: food + utilities + internet")

    def collect_programs(self) -> bool:
        self.selected_programs = [key for key, variable in self.program_vars.items() if variable.get()]
        if not self.selected_programs:
            messagebox.showwarning("Choose a subsidy", "Select at least one subsidy type.")
            return False
        return True

    def collect_user_data(self) -> bool:
        income_text = self.income_var.get().strip()
        try:
            income_amount = parse_money(income_text)
        except ValueError:
            messagebox.showwarning("Check income", "Enter a valid income amount.")
            return False

        if income_amount < 0:
            messagebox.showwarning("Check income", "Income cannot be negative.")
            return False

        period = self.income_period_var.get()
        monthly_income = income_amount / 12 if period == "Yearly" else income_amount

        try:
            household_size = int(self.household_var.get())
        except (TypeError, tk.TclError, ValueError):
            messagebox.showwarning("Check household size", "Household size must be a number.")
            return False

        if household_size < 1 or household_size > 12:
            messagebox.showwarning("Check household size", "Household size must be between 1 and 12.")
            return False

        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("Check name", "Enter the applicant's name.")
            return False

        location_input = self.location_var.get().strip()
        if not location_input:
            messagebox.showwarning("Check location", "Enter your ZIP code or city.")
            return False

        self.user_data = {
            "applicant_name": name,
            "income_entered": income_amount,
            "income_period": period,
            "monthly_income": monthly_income,
            "household_size": household_size,
            "location_input": location_input,
            "zip": extract_zip(location_input),
            "city": extract_city(location_input),
            "state": self.state_var.get(),
            "age_range": self.age_var.get(),
            "employment_status": self.employment_var.get(),
            "resident": self.residency_var.get(),
            "child_under_13": self.child_under_13_var.get(),
            "utility_hardship": self.utility_hardship_var.get(),
            "internet_need": self.internet_need_var.get(),
            "transportation_need": self.transportation_need_var.get(),
        }
        return True

    def refresh_locations(self) -> None:
        self.refresh_location_data()
        self._sync_location_view()
        self._render_location_cards()

    def refresh_location_data(self) -> None:
        try:
            radius = float(self.radius_var.get())
        except ValueError:
            radius = 10.0
        self.location_results = find_locations(self.user_data, self.eligibility, radius)

    def programs_for_locations(self) -> list[str]:
        return [
            key
            for key in self.selected_programs
            if self.eligibility.get(key)
            and self.eligibility[key].status in {"Highly eligible", "Partially eligible"}
        ]

    def best_status_for(self, program_keys: list[str]) -> str:
        if any(self.eligibility[key].status == "Highly eligible" for key in program_keys):
            return "Highly eligible"
        if any(self.eligibility[key].status == "Partially eligible" for key in program_keys):
            return "Partially eligible"
        return "Unlikely"

    def save_case_history(self) -> None:
        if not self.eligibility:
            messagebox.showwarning("No results", "Run the eligibility check first.")
            return
        append_case_history(
            CASE_HISTORY_FILE,
            self.selected_programs,
            self.user_data,
            self.eligibility,
            self.location_results,
            self.radius_var.get(),
        )
        messagebox.showinfo("Case history saved", f"Saved this run to:\n{CASE_HISTORY_FILE}")

    def save_draft_application(self) -> None:
        if not self.eligibility:
            messagebox.showwarning("No results", "Run the eligibility check first.")
            return
        default_name = f"benefit_bridge_application_{datetime.now().strftime('%Y%m%d_%H%M')}.html"
        path = filedialog.asksaveasfilename(
            title="Save draft application",
            defaultextension=".html",
            initialfile=default_name,
            filetypes=[("HTML document", "*.html"), ("All files", "*.*")],
        )
        if not path:
            return
        html = build_draft_application(
            self.selected_programs,
            self.user_data,
            self.eligibility,
            self.location_results,
            self.radius_var.get(),
            self.session_id,
        )
        Path(path).write_text(html, encoding="utf-8")
        webbrowser.open(Path(path).as_uri())
        messagebox.showinfo("Draft saved", f"Application draft saved and opened in your browser:\n{path}")

    def go_next(self) -> None:
        # This method is the "wizard brain":
        # step 0 -> validate selected programs
        # step 1 -> validate profile and compute results
        # step 2 -> export printable report
        if self.current_step == 0:
            if self.collect_programs():
                self.show_step(1)
        elif self.current_step == 1:
            if self.collect_user_data():
                self._baseline_monthly = float(self.user_data["monthly_income"])
                self.income_scenario_pct.set(100.0)
                self.office_search_var.set("")
                self.office_sort_var.set("distance")
                self.eligibility = compute_eligibility(self.selected_programs, self.user_data)
                self.refresh_location_data()
                self.show_step(2)
        else:
            self.save_draft_application()

    def go_back(self) -> None:
        if self.current_step > 0:
            self.show_step(self.current_step - 1)

    def start_over(self) -> None:
        if not messagebox.askyesno("Start over", "Clear this run and start again?"):
            return
        for variable in self.program_vars.values():
            variable.set(False)
        self.income_var.set("")
        self.income_period_var.set("Monthly")
        self.household_var.set(3)
        self.location_var.set("")
        self.state_var.set("California")
        self.age_var.set("Adult")
        self.employment_var.set(EMPLOYMENT_OPTIONS[0])
        self.residency_var.set(True)
        self.child_under_13_var.set(True)
        self.utility_hardship_var.set(False)
        self.internet_need_var.set(True)
        self.transportation_need_var.set(False)
        self.radius_var.set("10")
        self.office_search_var.set("")
        self.office_sort_var.set("distance")
        self.income_scenario_pct.set(100.0)
        self._baseline_monthly = 0.0
        self._location_view = []
        self.selected_programs = []
        self.user_data = {}
        self.eligibility = {}
        self.location_results = []
        self.show_step(0)


def parse_money(value: str) -> float:
    cleaned = value.replace("$", "").replace(",", "").strip()
    if not cleaned:
        raise ValueError("empty amount")
    amount = float(cleaned)
    if not math.isfinite(amount):
        raise ValueError("invalid amount")
    return amount


def extract_zip(location_input: str) -> str | None:
    match = re.search(r"\b\d{5}\b", location_input)
    if match:
        return match.group(0)
    stripped = location_input.strip()
    return stripped if stripped.isdigit() and len(stripped) == 5 else None


def extract_city(location_input: str) -> str | None:
    if extract_zip(location_input):
        return None
    city = re.sub(r"[^A-Za-z ]", " ", location_input).strip().lower()
    city = " ".join(city.split())
    if not city:
        return None
    for known_city in sorted(CITY_COORDS, key=len, reverse=True):
        if re.search(rf"\b{re.escape(known_city)}\b", city):
            return known_city
    return city


def compute_eligibility(selected_programs: list[str], user_data: dict[str, object]) -> dict[str, ProgramResult]:
    results: dict[str, ProgramResult] = {}
    state = str(user_data.get("state", "California"))
    limits = STATE_LIMITS.get(state, STATE_LIMITS["California"])
    for program_key in selected_programs:
        if program_key == "childcare":
            checks = childcare_checks(user_data, limits["childcare"])
        elif program_key == "food":
            checks = food_checks(user_data, limits["food"])
        elif program_key == "utility":
            checks = utility_checks(user_data, limits["utility"])
        elif program_key == "internet":
            checks = internet_checks(user_data, limits["internet"])
        else:
            checks = transportation_checks(user_data, limits["transportation"])
        results[program_key] = classify_program(program_key, checks)
    return results


def childcare_checks(user: dict[str, object], childcare_limits: dict[int, int]) -> list[RuleCheck]:
    limit = limit_for_household(childcare_limits, int(user["household_size"]), 1300)
    income = float(user["monthly_income"])
    working_or_studying = user["employment_status"] in {"Working", "In school or job training", "Working and in school"}
    return [
        income_check(income, limit, "Income is within the sample child-care limit"),
        RuleCheck(
            "Parent activity",
            working_or_studying,
            "Parent or caregiver is working, in school, or in job training.",
            "Child-care programs usually require a parent to work, study, or train.",
            close=user["employment_status"] == "Looking for work",
        ),
        RuleCheck(
            "Child age",
            bool(user["child_under_13"]),
            "A child in the household is under age 13.",
            "This sample child-care subsidy is focused on children under age 13.",
            critical=True,
        ),
    ]


def food_checks(user: dict[str, object], food_limits: dict[int, int]) -> list[RuleCheck]:
    limit = limit_for_household(food_limits, int(user["household_size"]), 897)
    income = float(user["monthly_income"])
    return [
        income_check(income, limit, "Income is within the sample food assistance limit"),
        RuleCheck(
            "Residency",
            bool(user["resident"]),
            "Household meets the sample residency condition.",
            "Food assistance often requires US residency or qualified non-citizen status.",
            critical=True,
        ),
    ]


def utility_checks(user: dict[str, object], utility_limits: dict[int, int]) -> list[RuleCheck]:
    limit = limit_for_household(utility_limits, int(user["household_size"]), 910)
    income = float(user["monthly_income"])
    return [
        income_check(income, limit, "Income is within the sample utility assistance limit"),
        RuleCheck(
            "Bill hardship",
            bool(user["utility_hardship"]),
            "Household reports utility bill hardship.",
            "Utility bill help is often prioritized for shutoff notices or past-due bills.",
        ),
        RuleCheck(
            "Residency",
            bool(user["resident"]),
            "Household meets the sample residency condition.",
            "Many utility programs require local residency or qualified status.",
            critical=True,
        ),
    ]


def internet_checks(user: dict[str, object], internet_limits: dict[int, int]) -> list[RuleCheck]:
    limit = limit_for_household(internet_limits, int(user["household_size"]), 897)
    income = float(user["monthly_income"])
    return [
        income_check(income, limit, "Income is within the sample internet subsidy limit"),
        RuleCheck(
            "Internet need",
            bool(user["internet_need"]),
            "Household reports a need for home internet access.",
            "The sample internet subsidy expects a work, school, health, or benefits need.",
        ),
        RuleCheck(
            "Residency",
            bool(user["resident"]),
            "Household meets the sample residency condition.",
            "Internet subsidies may require local residency or qualified status.",
            critical=True,
        ),
    ]


def transportation_checks(user: dict[str, object], transportation_limits: dict[int, int]) -> list[RuleCheck]:
    limit = limit_for_household(transportation_limits, int(user["household_size"]), 780)
    income = float(user["monthly_income"])
    active_status = user["employment_status"] in {
        "Working",
        "In school or job training",
        "Working and in school",
        "Looking for work",
    }
    return [
        income_check(income, limit, "Income is within the sample transportation limit"),
        RuleCheck(
            "Transportation need",
            bool(user["transportation_need"]),
            "Household reports a transportation need.",
            "Voucher programs usually require a work, school, or medical transportation need.",
        ),
        RuleCheck(
            "Activity",
            active_status or user["age_range"] == "Senior",
            "Applicant has a work, school, job-search, or senior mobility reason.",
            "Transportation vouchers usually need a work, school, job-search, medical, or senior mobility reason.",
            close=user["employment_status"] == "Retired",
        ),
    ]


def income_check(income: float, limit: float, label: str) -> RuleCheck:
    return RuleCheck(
        "Income",
        income <= limit,
        f"{label}: {format_money(income)} monthly is at or below {format_money(limit)}.",
        f"Income is above the sample limit: {format_money(income)} monthly vs. {format_money(limit)}.",
        close=income <= limit * 1.15,
    )


def classify_program(program_key: str, checks: list[RuleCheck]) -> ProgramResult:
    passed = [check.pass_text for check in checks if check.passed]
    missed = [check.fail_text for check in checks if not check.passed]
    failures = [check for check in checks if not check.passed]
    critical_failures = [check for check in failures if check.critical]
    close_failures = [check for check in failures if check.close]

    if not failures:
        status = "Highly eligible"
    elif critical_failures:
        status = "Unlikely"
    elif len(failures) <= 2 and (len(close_failures) == len(failures) or len(failures) == 1):
        status = "Partially eligible"
    else:
        status = "Unlikely"

    explanation = plain_language_explanation(program_key, status, passed, missed)
    return ProgramResult(status=status, explanation=explanation, passed=passed, missed=missed)


def plain_language_explanation(program_key: str, status: str, passed: list[str], missed: list[str]) -> str:
    program_name = PROGRAMS[program_key]["short_name"].lower()
    if status == "Highly eligible":
        return f"You likely qualify for {program_name} because the sample rules are all met."
    if status == "Partially eligible":
        return f"You may qualify for {program_name}, but one or two details need review. An office can confirm whether exceptions or alternate rules apply."
    primary_reason = missed[0] if missed else "multiple sample rules were not met."
    return f"You may not qualify for {program_name} based on this estimate because {primary_reason}"


def limit_for_household(table: dict[int, int], household_size: int, extra_person_amount: int) -> int:
    if household_size in table:
        return table[household_size]
    largest = max(table)
    return table[largest] + (household_size - largest) * extra_person_amount


def find_locations(user_data: dict[str, object], eligibility: dict[str, ProgramResult], radius_miles: float) -> list[dict[str, object]]:
    eligible_programs = {
        key
        for key, result in eligibility.items()
        if result.status in {"Highly eligible", "Partially eligible"}
    }
    user_coord = resolve_user_coord(user_data)
    user_zip = user_data.get("zip")
    user_city = user_data.get("city")
    results = []

    for location in LOCATIONS:
        matching_programs = [key for key in location["programs"] if key in eligible_programs]
        if not matching_programs:
            continue

        loc_coord = ZIP_COORDS.get(location["zip"])
        distance = miles_between(user_coord, loc_coord) if user_coord and loc_coord else None
        same_zip = user_zip and user_zip == location["zip"]
        same_city = user_city and user_city == location["city"].lower()

        if distance is not None:
            if distance > radius_miles:
                continue
        elif not (same_zip or same_city):
            continue

        results.append(
            {
                "location": location,
                "programs": matching_programs,
                "distance": distance,
                "distance_text": format_distance(distance, same_zip),
            }
        )

    results.sort(key=lambda item: (9999 if item["distance"] is None else item["distance"], item["location"]["name"].lower()))
    return results


def resolve_user_coord(user_data: dict[str, object]) -> tuple[float, float] | None:
    user_zip = user_data.get("zip")
    if user_zip and user_zip in ZIP_COORDS:
        return ZIP_COORDS[str(user_zip)]
    city = user_data.get("city")
    if city and str(city).lower() in CITY_COORDS:
        return CITY_COORDS[str(city).lower()]
    return None


def miles_between(start: tuple[float, float] | None, end: tuple[float, float] | None) -> float | None:
    if not start or not end:
        return None
    lat1, lon1 = map(math.radians, start)
    lat2, lon2 = map(math.radians, end)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return 3958.8 * c


def format_distance(distance: float | None, same_zip: bool | None = False) -> str:
    if same_zip:
        return "same ZIP"
    if distance is None:
        return "nearby"
    if distance < 0.2:
        return "same area"
    return f"{distance:.1f} mi"


def format_money(value: float) -> str:
    return f"${value:,.0f}"


def append_case_history(
    path: Path,
    selected_programs: list[str],
    user_data: dict[str, object],
    eligibility: dict[str, ProgramResult],
    locations: list[dict[str, object]],
    radius: str,
) -> None:
    file_exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "timestamp",
                "selected_programs",
                "monthly_income",
                "household_size",
                "location",
                "age_range",
                "employment_status",
                "radius_miles",
                "eligibility",
                "location_count",
            ],
        )
        if not file_exists:
            writer.writeheader()
        writer.writerow(
            {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "selected_programs": "; ".join(selected_programs),
                "monthly_income": f"{float(user_data['monthly_income']):.2f}",
                "household_size": user_data["household_size"],
                "location": user_data["location_input"],
                "age_range": user_data["age_range"],
                "employment_status": user_data["employment_status"],
                "radius_miles": radius,
                "eligibility": "; ".join(f"{key}: {result.status}" for key, result in eligibility.items()),
                "location_count": len(locations),
            }
        )


_PROGRAM_DOCS: dict[str, list[str]] = {
    "childcare": [
        "Government-issued photo ID (driver's license, passport, or state ID)",
        "Child's birth certificate or proof of age",
        "Proof of income — last 3 pay stubs, or most recent tax return if self-employed",
        "Proof of employment, school enrollment, or job-training participation",
        "Proof of residency — current lease, mortgage statement, or utility bill",
        "Child's immunization / health records",
        "Social Security numbers for all household members",
        "Name and address of current or desired child-care provider",
    ],
    "food": [
        "Government-issued photo ID for each adult applicant",
        "Social Security cards (or numbers) for all household members",
        "Proof of income — pay stubs, employer letter, or benefit award letters",
        "Proof of residency — lease, utility bill, or bank statement",
        "Proof of citizenship or qualified immigration status",
        "Recent bank statements (checking and savings)",
        "Documentation of any recurring expenses (rent, utilities, child support)",
    ],
    "utility": [
        "Most recent utility bill(s) — electric, gas, or water",
        "Government-issued photo ID",
        "Proof of income — pay stubs or benefit award letters for all adults",
        "Social Security numbers for all household members",
        "Proof of residency — lease or mortgage statement matching the service address",
        "Shut-off notice or past-due bill (if applicable — can strengthen your case)",
    ],
    "internet": [
        "Government-issued photo ID",
        "Proof of income OR proof of participation in a qualifying program (SNAP, Medicaid, Lifeline, etc.)",
        "Proof of residency — any document showing your current address",
        "Social Security number or Tribal ID",
    ],
    "transportation": [
        "Government-issued photo ID",
        "Proof of income — pay stubs, benefit letters, or tax return",
        "Proof of residency — utility bill, lease, or bank statement",
        "Documentation of transportation need (employer letter, medical appointment letter, school enrollment)",
        "Proof of disability (if applicable — may qualify for enhanced benefits)",
    ],
}

_PROGRAM_DESCRIPTIONS: dict[str, str] = {
    "childcare": (
        "The Child Care and Development Fund (CCDF) helps low- and moderate-income families "
        "pay for licensed child care while a parent works, attends school, or participates in "
        "job training. Subsidies go directly to approved providers, reducing or eliminating "
        "your out-of-pocket cost."
    ),
    "food": (
        "The Supplemental Nutrition Assistance Program (SNAP) provides monthly electronic "
        "benefits (EBT card) to help households buy groceries. Benefit amounts are based on "
        "household size and income. Most applicants can apply online, by mail, or in person "
        "at their local social services office."
    ),
    "utility": (
        "The Low Income Home Energy Assistance Program (LIHEAP) helps qualifying households "
        "pay heating and cooling bills, make energy-related home repairs, and avoid utility "
        "shut-offs. Benefits are typically paid directly to your utility provider."
    ),
    "internet": (
        "The Affordable Connectivity Program (ACP) and related state programs provide eligible "
        "households with a monthly discount on broadband service and, in some cases, a one-time "
        "discount on a laptop or tablet. Eligibility is often linked to other federal assistance "
        "programs such as SNAP or Medicaid."
    ),
    "transportation": (
        "State and local transit-assistance programs offer free or reduced-fare transit passes, "
        "mileage reimbursement for medical trips, or ride vouchers for qualifying individuals "
        "traveling to work, school, medical appointments, or job training."
    ),
}

_STATUS_BADGE: dict[str, tuple[str, str]] = {
    "Highly eligible":    ("#d1fae5", "#065f46"),
    "Partially eligible": ("#fef3c7", "#92400e"),
    "Unlikely":           ("#fee2e2", "#991b1b"),
}

_STATUS_ICON: dict[str, str] = {
    "Highly eligible":    "✓",
    "Partially eligible": "~",
    "Unlikely":           "✗",
}


def _html_badge(status: str) -> str:
    bg, fg = _STATUS_BADGE.get(status, ("#e5e7eb", "#374151"))
    icon = _STATUS_ICON.get(status, "")
    return (
        f'<span style="display:inline-block;padding:4px 14px;border-radius:999px;'
        f'background:{bg};color:{fg};font-weight:700;font-size:13px;letter-spacing:.3px;">'
        f'{icon}&nbsp;{status}</span>'
    )


def _html_checklist(items: list[str]) -> str:
    rows = "".join(
        f'<li style="margin-bottom:8px;display:flex;align-items:flex-start;gap:10px;">'
        f'<span style="margin-top:2px;width:18px;height:18px;border:2px solid #cbd5e1;'
        f'border-radius:4px;flex-shrink:0;display:inline-block;"></span>'
        f'<span>{item}</span></li>'
        for item in items
    )
    return f'<ul style="list-style:none;padding:0;margin:0;">{rows}</ul>'


def build_draft_application(
    selected_programs: list[str],
    user_data: dict[str, object],
    eligibility: dict[str, ProgramResult],
    locations: list[dict[str, object]],
    radius: str,
    session_id: str = "",
) -> str:
    now = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    applicant_name = html.escape(str(user_data.get("applicant_name", "")).strip() or "Applicant")
    state = str(user_data.get("state", ""))
    income_str = format_money(float(user_data["monthly_income"]))
    household = user_data["household_size"]
    location_input = user_data.get("location_input", "")
    age_range = user_data.get("age_range", "")
    employment = user_data.get("employment_status", "")
    resident = "Yes" if user_data.get("resident") else "No"
    child_u13 = "Yes" if user_data.get("child_under_13") else "No"
    utility_hardship = "Yes" if user_data.get("utility_hardship") else "No"
    internet_need = "Yes" if user_data.get("internet_need") else "No"
    transport_need = "Yes" if user_data.get("transportation_need") else "No"

    # ── summary pills row ─────────────────────────────────────────────────────
    summary_pills = "".join(
        f'<div style="display:flex;align-items:center;gap:12px;padding:12px 0;'
        f'border-bottom:1px solid #f1f5f9;">'
        f'<span style="font-weight:600;color:#1e293b;min-width:190px;">'
        f'{PROGRAMS[k]["name"]}</span>'
        f'{_html_badge(eligibility[k].status)}</div>'
        for k in selected_programs
    )

    # ── per-program detail sections ───────────────────────────────────────────
    program_sections = ""
    for k in selected_programs:
        result = eligibility[k]
        prog = PROGRAMS[k]
        bg, fg = _STATUS_BADGE.get(result.status, ("#e5e7eb", "#374151"))
        description = _PROGRAM_DESCRIPTIONS.get(k, prog["description"])
        docs = _PROGRAM_DOCS.get(k, [])

        passed_html = "".join(
            f'<li style="margin-bottom:6px;color:#065f46;">&#10003;&nbsp;{t}</li>'
            for t in result.passed
        )
        missed_html = "".join(
            f'<li style="margin-bottom:6px;color:#92400e;">&#9888;&nbsp;{t}</li>'
            for t in result.missed
        )
        rules_html = ""
        if passed_html:
            rules_html += (
                f'<p style="font-weight:600;color:#374151;margin:16px 0 6px;">Rules met</p>'
                f'<ul style="margin:0;padding-left:20px;">{passed_html}</ul>'
            )
        if missed_html:
            rules_html += (
                f'<p style="font-weight:600;color:#374151;margin:16px 0 6px;">Items to review with staff</p>'
                f'<ul style="margin:0;padding-left:20px;">{missed_html}</ul>'
            )

        program_sections += f"""
        <div style="background:#fff;border-radius:14px;border:1px solid #e2e8f0;
                    box-shadow:0 1px 4px rgba(0,0,0,.06);margin-bottom:28px;overflow:hidden;">
          <!-- program header bar -->
          <div style="background:{bg};padding:18px 28px;display:flex;align-items:center;
                      justify-content:space-between;flex-wrap:wrap;gap:10px;">
            <div>
              <div style="font-size:11px;text-transform:uppercase;letter-spacing:1px;
                          color:{fg};font-weight:700;margin-bottom:4px;">
                {prog['short_name']}
              </div>
              <div style="font-size:20px;font-weight:800;color:{fg};">{prog['name']}</div>
            </div>
            {_html_badge(result.status)}
          </div>
          <!-- body -->
          <div style="padding:24px 28px;">
            <p style="color:#475569;line-height:1.7;margin:0 0 14px;">{description}</p>
            <div style="background:#f8fafc;border-left:4px solid {bg};border-radius:0 8px 8px 0;
                        padding:14px 18px;margin-bottom:16px;color:#334155;font-style:italic;">
              {result.explanation}
            </div>
            {rules_html}
            <!-- checklist -->
            <div style="margin-top:24px;padding-top:20px;border-top:1px solid #f1f5f9;">
              <p style="font-weight:700;color:#1e293b;font-size:15px;margin:0 0 14px;">
                &#128203;&nbsp;Documents to bring
              </p>
              {_html_checklist(docs)}
            </div>
          </div>
        </div>
        """

    # ── nearby offices ────────────────────────────────────────────────────────
    if locations:
        office_rows = ""
        for item in locations[:10]:
            loc = item["location"]
            prog_tags = "".join(
                f'<span style="display:inline-block;padding:2px 10px;border-radius:999px;'
                f'background:#eff6ff;color:#1d4ed8;font-size:11px;font-weight:600;margin:2px;">'
                f'{PROGRAMS[p]["short_name"]}</span>'
                for p in item["programs"] if p in PROGRAMS
            )
            office_rows += f"""
            <div style="padding:16px 0;border-bottom:1px solid #f1f5f9;">
              <div style="font-weight:700;color:#1e293b;font-size:15px;">{loc['name']}</div>
              <div style="color:#64748b;margin:4px 0 8px;font-size:13px;">
                &#128205;&nbsp;{loc['address']}&nbsp;&nbsp;
                <span style="color:#94a3b8;">({item['distance_text']})</span>
              </div>
              <div>{prog_tags}</div>
            </div>
            """
        offices_section = f"""
        <div style="background:#fff;border-radius:14px;border:1px solid #e2e8f0;
                    box-shadow:0 1px 4px rgba(0,0,0,.06);margin-bottom:28px;overflow:hidden;">
          <div style="background:#0f172a;padding:18px 28px;">
            <div style="font-size:11px;text-transform:uppercase;letter-spacing:1px;
                        color:#94a3b8;font-weight:700;margin-bottom:4px;">Offices</div>
            <div style="font-size:20px;font-weight:800;color:#f8fafc;">
              Nearby offices within {radius} miles
            </div>
          </div>
          <div style="padding:8px 28px 20px;">{office_rows}</div>
        </div>
        """
    else:
        offices_section = (
            '<p style="color:#64748b;font-style:italic;">No offices found within the selected radius.</p>'
        )

    session_line = (
        f'<span style="color:#94a3b8;font-size:12px;">Session&nbsp;{session_id}&nbsp;&bull;&nbsp;</span>'
        if session_id else ""
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Benefit Bridge — {applicant_name}'s preparation aid</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    *, *::before, *::after {{ box-sizing: border-box; }}
    body {{
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: #f1f5f9;
      color: #1e293b;
      margin: 0;
      padding: 40px 16px 80px;
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }}
    .page {{ max-width: 820px; margin: 0 auto; }}
    @media print {{
      body {{ background: #fff; padding: 0; }}
      .no-print {{ display: none !important; }}
    }}
  </style>
</head>
<body>
<div class="page">

  <!-- ── header ── -->
  <div style="background:linear-gradient(135deg,#0f172a 0%,#1e3a5f 100%);
              border-radius:18px;padding:40px 40px 36px;margin-bottom:28px;
              color:#f8fafc;position:relative;overflow:hidden;">
    <div style="position:absolute;top:-40px;right:-40px;width:220px;height:220px;
                border-radius:50%;background:rgba(255,255,255,.04);pointer-events:none;"></div>
    <div style="font-size:11px;text-transform:uppercase;letter-spacing:2px;
                color:#7dd3fc;font-weight:700;margin-bottom:10px;">
      Benefit Bridge &bull; You're Closer Than You Think
    </div>
    <h1 style="margin:0 0 8px;font-size:32px;font-weight:800;letter-spacing:-.5px;">
      {applicant_name}'s preparation aid
    </h1>
    <p style="margin:0;color:#94a3b8;font-size:14px;">
      {session_line}Generated {now}
    </p>
    <div style="margin-top:24px;padding-top:20px;border-top:1px solid rgba(255,255,255,.1);
                font-size:13px;color:#cbd5e1;">
      This document is a preparation aid — not an official application. Bring it and the
      listed documents to your nearest office to begin the official process.
    </div>
  </div>

  <!-- ── profile card ── -->
  <div style="background:#fff;border-radius:14px;border:1px solid #e2e8f0;
              box-shadow:0 1px 4px rgba(0,0,0,.06);margin-bottom:28px;overflow:hidden;">
    <div style="background:#0f172a;padding:18px 28px;">
      <div style="font-size:11px;text-transform:uppercase;letter-spacing:1px;
                  color:#94a3b8;font-weight:700;margin-bottom:4px;">Applicant</div>
      <div style="font-size:20px;font-weight:800;color:#f8fafc;">Household Profile</div>
    </div>
    <div style="padding:24px 28px;">
      <table style="width:100%;border-collapse:collapse;font-size:14px;">
        <tr>
          <td style="padding:9px 0;color:#64748b;width:45%;border-bottom:1px solid #f1f5f9;">Monthly income</td>
          <td style="padding:9px 0;font-weight:600;border-bottom:1px solid #f1f5f9;">{income_str}</td>
          <td style="padding:9px 0;color:#64748b;width:25%;border-bottom:1px solid #f1f5f9;">Household size</td>
          <td style="padding:9px 0;font-weight:600;border-bottom:1px solid #f1f5f9;">{household} {("person" if int(household) == 1 else "people")}</td>
        </tr>
        <tr>
          <td style="padding:9px 0;color:#64748b;border-bottom:1px solid #f1f5f9;">Location</td>
          <td style="padding:9px 0;font-weight:600;border-bottom:1px solid #f1f5f9;" colspan="3">{location_input}{(", " + state) if state else ""}</td>
        </tr>
        <tr>
          <td style="padding:9px 0;color:#64748b;border-bottom:1px solid #f1f5f9;">Age range</td>
          <td style="padding:9px 0;font-weight:600;border-bottom:1px solid #f1f5f9;">{age_range}</td>
          <td style="padding:9px 0;color:#64748b;border-bottom:1px solid #f1f5f9;">Employment status</td>
          <td style="padding:9px 0;font-weight:600;border-bottom:1px solid #f1f5f9;">{employment}</td>
        </tr>
        <tr>
          <td style="padding:9px 0;color:#64748b;border-bottom:1px solid #f1f5f9;">US resident</td>
          <td style="padding:9px 0;font-weight:600;border-bottom:1px solid #f1f5f9;">{resident}</td>
          <td style="padding:9px 0;color:#64748b;border-bottom:1px solid #f1f5f9;">Child under 13</td>
          <td style="padding:9px 0;font-weight:600;border-bottom:1px solid #f1f5f9;">{child_u13}</td>
        </tr>
        <tr>
          <td style="padding:9px 0;color:#64748b;border-bottom:1px solid #f1f5f9;">Utility hardship</td>
          <td style="padding:9px 0;font-weight:600;border-bottom:1px solid #f1f5f9;">{utility_hardship}</td>
          <td style="padding:9px 0;color:#64748b;border-bottom:1px solid #f1f5f9;">Internet need</td>
          <td style="padding:9px 0;font-weight:600;border-bottom:1px solid #f1f5f9;">{internet_need}</td>
        </tr>
        <tr>
          <td style="padding:9px 0;color:#64748b;">Transportation need</td>
          <td style="padding:9px 0;font-weight:600;" colspan="3">{transport_need}</td>
        </tr>
      </table>
    </div>
  </div>

  <!-- ── eligibility summary ── -->
  <div style="background:#fff;border-radius:14px;border:1px solid #e2e8f0;
              box-shadow:0 1px 4px rgba(0,0,0,.06);margin-bottom:28px;overflow:hidden;">
    <div style="background:#0f172a;padding:18px 28px;">
      <div style="font-size:11px;text-transform:uppercase;letter-spacing:1px;
                  color:#94a3b8;font-weight:700;margin-bottom:4px;">Overview</div>
      <div style="font-size:20px;font-weight:800;color:#f8fafc;">Eligibility at a Glance</div>
    </div>
    <div style="padding:8px 28px 20px;">{summary_pills}</div>
  </div>

  <!-- ── per-program sections ── -->
  {program_sections}

  <!-- ── nearby offices ── -->
  {offices_section}

  <!-- ── footer ── -->
  <div style="text-align:center;color:#94a3b8;font-size:12px;line-height:1.8;margin-top:40px;">
    <strong style="color:#64748b;">Benefit Bridge</strong> &bull;
    These estimates are for preparation purposes only and do not constitute an official
    eligibility determination. Program rules, income limits, and required documents vary
    by state, county, and funding year. Always verify requirements with the administering agency.<br/>
    Generated {now}
  </div>

</div>
</body>
</html>"""


def summarize_location_results(items: list[dict[str, object]]) -> str:
    if not items:
        return "No matching offices found."
    top = items[0]
    location = top["location"]
    programs = ", ".join(PROGRAMS[key]["short_name"] for key in top["programs"])
    return f"Closest match: {location['name']} ({top['distance_text']}) for {programs}."
    if not items:
        return "No matching offices found."
    top = items[0]
    location = top["location"]
    programs = ", ".join(PROGRAMS[key]["short_name"] for key in top["programs"])
    return f"Closest match: {location['name']} ({top['distance_text']}) for {programs}."


def clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def safe_get_program_short_names(program_keys: list[str]) -> str:
    return ", ".join(PROGRAMS[key]["short_name"] for key in program_keys if key in PROGRAMS)


def sanitize_location_text(text: str) -> str:
    return " ".join(text.strip().split())


if __name__ == "__main__":
    app = BenefitBridgeApp()
    app.mainloop()


