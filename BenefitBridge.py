

# this lets us use newer python type hints (like list[str]) even on older python versions
from __future__ import annotations

# these are the standard python libraries we need throughout the whole file
import csv          # for writing and reading csv spreadsheet files (the case history log)
import json         # for reading and writing json files (settings, drafts, exports)
import html         # for safely embedding user text inside html so special characters don't break anything
import math         # for math operations like ceiling and square root
import re           # for searching text with patterns (like finding a 5 digit zip code)
import sys          # for checking runtime info like the frozen pyinstaller path
import webbrowser   # for opening a url in the user's default web browser (google maps links)
import os           # for working with file paths and checking if files or folders exist

try:
    # try to import pillow, which lets us load and resize images like the logo
    from PIL import Image, ImageTk
except ImportError:
    # if pillow is not installed, set both to none so the rest of the code can check for that
    Image = None
    ImageTk = None


# dataclass is a shortcut for making simple data container classes with less boilerplate
from dataclasses import dataclass
# datetime lets us get the current date and time and format it as a string
from datetime import datetime
# partial lets us pre fill some arguments of a function and use the result like a new function
from functools import partial
# path makes working with file and folder paths much cleaner than raw strings
from pathlib import Path
# quote_plus turns text like "123 main st" into url safe form like "123+main+st"
from urllib.parse import quote_plus

# tkinter is python's built in gui toolkit for making windows buttons and widgets
from tkinter import filedialog, messagebox, ttk   # file save dialogs, popup dialogs, and themed widgets
from tkinter import font as tkfont                # for measuring and working with fonts
import tkinter as tk                              # the main tkinter module that everything builds on
from zip_data import ZIP_COORDS, CITY_COORDS      # our lookup tables that map zip codes and city names to coordinates


# this file is organized into these main sections:
# 1. application file paths and local storage
# 2. program metadata, sample income limits, and state rules
# 3. office location data and zip and city coordinate helpers
# 4. ui choice lists and theme constants
# 5. runtime helpers, dataclasses, and widget utilities
# 6. persistence, eligibility rules, and location search
# 7. draft export builder and main tkinter app class


# section 1: application files and storage
# these are all the file paths and names used for settings, drafts, exports, and history

def resource_path(relative_path):
    # when the app is bundled by pyinstaller, files are unpacked to sys._meipass at runtime
    # when running as a regular python script, we just use the folder the script lives in
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    # join the base folder with whatever relative path was asked for
    return os.path.join(base_path, relative_path)

# the base folder where we look for bundled files and also where we save user data
APP_DIR = Path(resource_path("."))
# the expected location of the logo image file
BRAND_LOGO_PATH = Path(resource_path("benefit_bridge_logo.png"))

# a list of places to look for the logo; we try each one until we find one that exists
BRAND_LOGO_CANDIDATES = [BRAND_LOGO_PATH]

# the path to the csv file where each eligibility check session gets logged
CASE_HISTORY_FILE = APP_DIR / "benefit_bridge_case_history.csv"
# the path to the json file where user settings like font size are saved
SETTINGS_FILE = APP_DIR / "benefit_bridge_settings.json"
# the path to the json file where an in progress form is auto saved as a draft
DRAFT_FILE = APP_DIR / "benefit_bridge_draft.json"
# the path to the json file where the user's favorite office locations are saved
FAVORITES_FILE = APP_DIR / "benefit_bridge_favorites.json"
# the folder where json exports of full sessions are saved
EXPORT_DIR = APP_DIR / "exports"
# the tagline that shows up in the header and about box
BRAND_SLOGAN = "You're Closer Than You Think"


# section 2: the five assistance programs this app can check eligibility for
# this dictionary is the single source of truth for all program info
# every other part of the code looks up program names and colors from here using the key
# each program has: name (long title), short_name (compact label), description, and color (hex accent)
PROGRAMS = {
    # childcare covers federal and state subsidy programs like ccdf that help working parents pay for licensed daycare
    "childcare": {
        "name": "Child-care subsidy",
        "short_name": "Child care",
        "description": "Help paying for licensed care while a parent works or studies.",
        "color": "#14b8a6",   # teal
    },
    # food covers snap (food stamps) and wic; both are checked using state specific income limits
    "food": {
        "name": "Food assistance / SNAP-like program",
        "short_name": "Food",
        "description": "Monthly grocery support for households under income limits.",
        "color": "#3b82f6",   # blue
    },
    # utility covers programs like liheap that help pay electric gas or water bills especially with a shutoff notice
    "utility": {
        "name": "Utility bill help",
        "short_name": "Utilities",
        "description": "Energy, water, or emergency bill support.",
        "color": "#f97316",   # orange
    },
    # internet covers programs like the affordable connectivity program that subsidize home internet for low income households
    "internet": {
        "name": "Internet subsidy",
        "short_name": "Internet",
        "description": "Low-cost internet or digital access support.",
        "color": "#8b5cf6",   # purple
    },
    # transportation covers state transit voucher programs like bus passes or rideshare credits for work school or appointments
    "transportation": {
        "name": "Other: transportation vouchers",
        "short_name": "Transport",
        "description": "Transit passes or rides for work, school, or medical needs.",
        "color": "#f43f5e",   # rose red
    },
}



# federal poverty line tables
# the fpl is a dollar amount the us government publishes each year that defines what "poverty" means for a given family size
# benefits programs use a multiple of this number (like 130% or 200%) as their income cutoff
# the values below are monthly dollar amounts (the annual fpl divided by 12 then rounded)
# the dictionary key is the number of people in the household and the value is the monthly income limit in dollars

# 100% fpl is the raw poverty line; most programs use a multiple of this
# for example a family of 4 earning 2750 dollars per month or less is at exactly 100% fpl
FPL_BASE_LIMITS = {
    1: 1330,
    2: 1803,
    3: 2276.5,
    4: 2750,
    5: 3223,
    6: 3696.5,
    7: 4170,
    8: 4643,
}

# 200% fpl is double the poverty line and is used for internet subsidy income limits
# so a family of 4 has a limit of about 5500 dollars per month at this level
FPL_200_LIMITS = {size: amount * 2 for size, amount in FPL_BASE_LIMITS.items()}

# 150% fpl is one and a half times the poverty line and is used as the floor for utility program limits
FPL_150_LIMITS = {size: amount * 1.5 for size, amount in FPL_BASE_LIMITS.items()}

# this is just another name for the base fpl table so the food eligibility code can reference it clearly
FPL_100_LIMITS = FPL_BASE_LIMITS

# alaska and hawaii fpl tables
# the federal government publishes separate higher fpl numbers for alaska and hawaii
# because the cost of living there is much higher than the rest of the country
# alaska is about 25% higher and hawaii is about 15% higher
# these tables only go up to 8 people; for bigger households you add the extra person amount

ALASKA_FPL_BASE = {1: 1662, 2: 2254, 3: 2846, 4: 3438, 5: 4030, 6: 4622, 7: 5214, 8: 5806}
ALASKA_FPL_EXTRA_PERSON = 592   # add this amount per person when the household is bigger than 8

HAWAII_FPL_BASE = {1: 1528, 2: 2073, 3: 2618, 4: 3163, 5: 3708, 6: 4253, 7: 4798, 8: 5343}
HAWAII_FPL_EXTRA_PERSON = 545   # add this amount per person when the household is bigger than 8

# snap gross income test multipliers by state (2026 bbce rules)
# snap normally has a federal gross income cutoff at 130% fpl
# but most states have adopted broad based categorical eligibility (bbce) which lets them raise that ceiling
# this dictionary maps each state to its actual snap income multiplier
# states not listed here default to 200% which is the most generous level used by big states like california new york and florida
# example: texas uses 1.65 so a family of 4 earning up to 4537 dollars per month can still qualify for snap
SNAP_STATE_MULTIPLIERS: dict[str, float] = {
    # 130% are the strictest states that use the federal minimum with no bbce expansion
    "Alabama": 1.30, "Arkansas": 1.30, "Georgia": 1.30, "Idaho": 1.30,
    "Indiana": 1.30, "Kansas": 1.30, "Mississippi": 1.30, "Missouri": 1.30,
    "Ohio": 1.30, "Oklahoma": 1.30, "South Carolina": 1.30, "South Dakota": 1.30,
    "Tennessee": 1.30, "Utah": 1.30, "Wyoming": 1.30,
    # iowa uses 160%
    "Iowa": 1.60,
    # these states use 165%
    "Illinois": 1.65, "Nebraska": 1.65, "Texas": 1.65,
    # these states use 185%
    "Arizona": 1.85, "New Jersey": 1.85, "Rhode Island": 1.85, "Vermont": 1.85,
    # all other states not listed here default to 200% inside food_eligibility()
}





# extra person amounts for households bigger than 8 people
# the fpl tables above only go up to 8 people
# for households with 9 or more people we add a fixed dollar amount per extra person
# these are the 100% fpl "per additional person" dollar values used as the starting point
# food uses this directly; internet doubles it since internet uses 200% fpl
FPL_BASE_EXTRA_PERSON_AMOUNTS = {
    "food": 473,       # 473 dollars per month per person beyond 8 at 100% fpl
    "internet": 473,   # same base amount, gets doubled to 200% fpl below
}

# the 200% fpl versions of the extra person amounts used by internet subsidy calculations
FPL_EXTRA_PERSON_AMOUNTS = {program: amount * 2 for program, amount in FPL_BASE_EXTRA_PERSON_AMOUNTS.items()}

# the 150% fpl version of the food extra person amount used when calculating the utility program floor
FPL_150_EXTRA_PERSON_AMOUNT = FPL_BASE_EXTRA_PERSON_AMOUNTS["food"] * 1.5

# state specific extra person increments for childcare, utility, and transportation
# when a household has more than 8 people this table tells us how much to add per extra person
# childcare values come from ccdf 2025 data (difference between family of 4 and family of 3 limits)
# utility values are estimated from liheap state data
# transportation values are estimated from state transit assistance data
# food and internet are not in this table; food uses snap logic and internet uses the federal 200% fpl amount above
STATE_EXTRA_PERSON_AMOUNTS: dict[str, dict[str, int]] = {
    "Alabama": {"childcare": 771, "utility": 154, "transportation": 700},
    "Alaska": {"childcare": 1180, "utility": 209, "transportation": 1000},
    "Arizona": {"childcare": 706, "utility": 169, "transportation": 800},
    "Arkansas": {"childcare": 982, "utility": 142, "transportation": 700},
    "California": {"childcare": 1240, "utility": 200, "transportation": 790},
    "Colorado": {"childcare": 792, "utility": 218, "transportation": 800},
    "Connecticut": {"childcare": 1167, "utility": 234, "transportation": 800},
    "Delaware": {"childcare": 792, "utility": 194, "transportation": 780},
    "District of Columbia": {"childcare": 1345, "utility": 303, "transportation": 900},
    "Florida": {"childcare": 642, "utility": 162, "transportation": 780},
    "Georgia": {"childcare": 635, "utility": 173, "transportation": 750},
    "Hawaii": {"childcare": 1182, "utility": 208, "transportation": 1100},
    "Idaho": {"childcare": 749, "utility": 164, "transportation": 750},
    "Illinois": {"childcare": 1009, "utility": 199, "transportation": 800},
    "Indiana": {"childcare": 672, "utility": 167, "transportation": 750},
    "Iowa": {"childcare": 717, "utility": 183, "transportation": 750},
    "Kansas": {"childcare": 1115, "utility": 177, "transportation": 750},
    "Kentucky": {"childcare": 1091, "utility": 156, "transportation": 700},
    "Louisiana": {"childcare": 985, "utility": 151, "transportation": 700},
    "Maine": {"childcare": 1745, "utility": 183, "transportation": 750},
    "Maryland": {"childcare": 1201, "utility": 237, "transportation": 800},
    "Massachusetts": {"childcare": 970, "utility": 258, "transportation": 850},
    "Michigan": {"childcare": 856, "utility": 180, "transportation": 750},
    "Minnesota": {"childcare": 787, "utility": 222, "transportation": 800},
    "Mississippi": {"childcare": 823, "utility": 135, "transportation": 700},
    "Missouri": {"childcare": 642, "utility": 170, "transportation": 750},
    "Montana": {"childcare": 829, "utility": 174, "transportation": 750},
    "Nebraska": {"childcare": 792, "utility": 183, "transportation": 750},
    "Nevada": {"childcare": 525, "utility": 158, "transportation": 800},
    "New Hampshire": {"childcare": 1513, "utility": 234, "transportation": 800},
    "New Jersey": {"childcare": 897, "utility": 247, "transportation": 850},
    "New Mexico": {"childcare": 1793, "utility": 139, "transportation": 700},
    "New York": {"childcare": 1449, "utility": 206, "transportation": 850},
    "North Carolina": {"childcare": 857, "utility": 170, "transportation": 750},
    "North Dakota": {"childcare": 1232, "utility": 199, "transportation": 750},
    "Ohio": {"childcare": 621, "utility": 177, "transportation": 750},
    "Oklahoma": {"childcare": 1020, "utility": 145, "transportation": 700},
    "Oregon": {"childcare": 896, "utility": 194, "transportation": 800},
    "Pennsylvania": {"childcare": 897, "utility": 195, "transportation": 800},
    "Rhode Island": {"childcare": 897, "utility": 209, "transportation": 850},
    "South Carolina": {"childcare": 1113, "utility": 160, "transportation": 700},
    "South Dakota": {"childcare": 936, "utility": 177, "transportation": 750},
    "Tennessee": {"childcare": 1115, "utility": 158, "transportation": 700},
    "Texas": {"childcare": 1170, "utility": 168, "transportation": 750},
    "Utah": {"childcare": 1265, "utility": 184, "transportation": 750},
    "Vermont": {"childcare": 1793, "utility": 203, "transportation": 800},
    "Virginia": {"childcare": 1519, "utility": 215, "transportation": 750},
    "Washington": {"childcare": 963, "utility": 220, "transportation": 800},
    "West Virginia": {"childcare": 1028, "utility": 147, "transportation": 700},
    "Wisconsin": {"childcare": 897, "utility": 192, "transportation": 750},
    "Wyoming": {"childcare": 785, "utility": 172, "transportation": 750},
}

# state income limits table
# this is the main lookup table the app uses to decide if someone might qualify for a program
# for each state it stores monthly gross income limits organized by program and household size
# how to read it: if a family of 4 in alabama earns less than 4500 dollars per month they are under the childcare limit
# sources for these numbers:
#   childcare: ccdf eligibility thresholds from 2026
#   utility: liheap, set to the higher of 150% fpl or 60% of the state median income
#   internet: 200% fpl, which is the same federal standard in every state
#   transportation: state transit assistance program thresholds (estimated)
#   food: not in this table at all; it is handled separately by food_eligibility() using snap_state_multipliers
STATE_LIMITS = {
    "Alabama": {
        "childcare":      {1: 2187, 2: 2958, 3: 3729, 4: 4500, 5: 5271, 6: 6042, 7: 6813, 8: 7584},
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 2662, 2: 3481, 3: 4300, 4: 5119, 5: 5938, 6: 6757, 7: 6910,  8: 7064},
        "transportation": {1: 1900, 2: 2600, 3: 3300, 4: 4000, 5: 4700, 6: 5400, 7: 6100,  8: 6800},
    },
    "Alaska": {
        "childcare":      {1: 3832, 2: 5012, 3: 6192, 4: 7372, 5: 8552, 6: 9732, 7: 10912, 8: 12092},
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 3620, 2: 4734, 3: 5848, 4: 6962, 5: 8076,  6: 9190,  7: 9399,  8: 9608},
        "transportation": {1: 2800, 2: 3800, 3: 4800, 4: 5800, 5: 6800,  6: 7800,  7: 8800,  8: 9800},
    },
    "Arizona": {
        "childcare":      {1: 2007, 2: 2713, 3: 3419, 4: 4125, 5: 4831, 6: 5537, 7: 6243, 8: 6949},
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 2937, 2: 3840, 3: 4744, 4: 5647, 5: 6551, 6: 7454,  7: 7624,  8: 7793},
        "transportation": {1: 2100, 2: 2900, 3: 3700, 4: 4500, 5: 5300, 6: 6100,  7: 6900,  8: 7700},
    },
    "Arkansas": {
        "childcare":      {1: 3187, 2: 4169, 3: 5151, 4: 6133, 5: 7115, 6: 8097, 7: 9079, 8: 10061},
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 2460, 2: 3217, 3: 3974, 4: 4731, 5: 5488, 6: 6245,  7: 6387,  8: 6529},
        "transportation": {1: 1800, 2: 2500, 3: 3200, 4: 3900, 5: 4600, 6: 5300,  7: 6000,  8: 6700},
    },
    "California": {
        "childcare":      {1: 4992, 2: 6232, 3: 7472, 4: 8712, 5: 9952, 6: 11192, 7: 12432, 8: 13672},
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 3459, 2: 4523, 3: 5587, 4: 6651, 5: 7715, 6: 8779, 7: 8979, 8: 9178},
        "transportation": {1: 2200, 2: 2980, 3: 3760, 4: 4550, 5: 5330, 6: 6120, 7: 6900, 8: 7690},
    },
    "Colorado": {
        "childcare":      {1: 2249, 2: 3041, 3: 3833, 4: 4625, 5: 5417, 6: 6209, 7: 7001, 8: 7793},
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 3775, 2: 4936, 3: 6097, 4: 7259, 5: 8420,  6: 9582,  7: 9799,  8: 10017},
        "transportation": {1: 2400, 2: 3200, 3: 4000, 4: 4800, 5: 5600,  6: 6400,  7: 7200,  8: 8000},
    },
    "Connecticut": {
        "childcare":      {1: 3792, 2: 4959, 3: 6126, 4: 7293, 5: 8460, 6: 9627, 7: 10794, 8: 11961},
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 4060, 2: 5309, 3: 6558, 4: 7807, 5: 9056,  6: 10305, 7: 10539, 8: 10773},
        "transportation": {1: 2500, 2: 3300, 3: 4100, 4: 4900, 5: 5700,  6: 6500,  7: 7300,  8: 8100},
    },
    "Delaware": {
        "childcare":      {1: 2249, 2: 3041, 3: 3833, 4: 4625, 5: 5417, 6: 6209, 7: 7001, 8: 7793},
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 3365, 2: 4400, 3: 5436, 4: 6471, 5: 7507, 6: 8542,  7: 8736,  8: 8930},
        "transportation": {1: 2200, 2: 3000, 3: 3800, 4: 4600, 5: 5400, 6: 6200,  7: 7000,  8: 7800},
    },
    "District of Columbia": {
        "childcare":      {1: 3765, 2: 5110, 3: 6455, 4: 7800, 5: 9145, 6: 10490, 7: 11835, 8: 13180},
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 5252, 2: 6868, 3: 8484, 4: 10100, 5: 11716, 6: 13332, 7: 13635, 8: 13938},
        "transportation": {1: 2700, 2: 3600, 3: 4500, 4: 5400,  5: 6300,  6: 7200,  7: 8100,  8: 9000},
    },
    "Florida": {
        "childcare":      {1: 1824, 2: 2466, 3: 3108, 4: 3750, 5: 4392, 6: 5034, 7: 5676, 8: 6318},
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 2811, 2: 3676, 3: 4541, 4: 5406, 5: 6271, 6: 7136,  7: 7298,  8: 7460},
        "transportation": {1: 2000, 2: 2700, 3: 3400, 4: 4100, 5: 4800, 6: 5500,  7: 6200,  8: 6900},
    },
    "Georgia": {
        "childcare":      {1: 2063, 2: 2698, 3: 3333, 4: 3968, 5: 4603, 6: 5238, 7: 5873, 8: 6508},
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 2993, 2: 3914, 3: 4835, 4: 5756, 5: 6677, 6: 7598,  7: 7770,  8: 7943},
        "transportation": {1: 2000, 2: 2700, 3: 3400, 4: 4100, 5: 4800, 6: 5500,  7: 6200,  8: 6900},
    },
    "Hawaii": {
        "childcare":      {1: 3838, 2: 5020, 3: 6202, 4: 7384, 5: 8566, 6: 9748, 7: 10930, 8: 12112},
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 3600, 2: 4708, 3: 5815, 4: 6923, 5: 8031,  6: 9138,  7: 9346,  8: 9554},
        "transportation": {1: 2500, 2: 3300, 3: 4100, 4: 4900, 5: 5700,  6: 6500,  7: 7300,  8: 8100},
    },
    "Idaho": {
        "childcare":      {1: 2128, 2: 2877, 3: 3626, 4: 4375, 5: 5124, 6: 5873, 7: 6622, 8: 7371},
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 2836, 2: 3708, 3: 4581, 4: 5454, 5: 6326, 6: 7199,  7: 7362,  8: 7526},
        "transportation": {1: 1900, 2: 2600, 3: 3300, 4: 4000, 5: 4700, 6: 5400,  7: 6100,  8: 6800},
    },
    "Illinois": {
        "childcare":      {1: 2823, 2: 3832, 3: 4841, 4: 5850, 5: 6859, 6: 7868, 7: 8877, 8: 9886},
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 3441, 2: 4500, 3: 5558, 4: 6617, 5: 7676, 6: 8735,  7: 8933,  8: 9132},
        "transportation": {1: 2200, 2: 3000, 3: 3800, 4: 4600, 5: 5400, 6: 6200,  7: 7000,  8: 7800},
    },
    "Indiana": {
        "childcare":      {1: 1884, 2: 2556, 3: 3228, 4: 3900, 5: 4572, 6: 5244, 7: 5916, 8: 6588},
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 2886, 2: 3774, 3: 4662, 4: 5551, 5: 6439, 6: 7327,  7: 7493,  8: 7660},
        "transportation": {1: 2000, 2: 2700, 3: 3400, 4: 4100, 5: 4800, 6: 5500,  7: 6200,  8: 6900},
    },
    "Iowa": {
        "childcare":      {1: 2009, 2: 2726, 3: 3443, 4: 4160, 5: 4877, 6: 5594, 7: 6311, 8: 7028},
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 3179, 2: 4157, 3: 5135, 4: 6113, 5: 7092, 6: 8070,  7: 8253,  8: 8437},
        "transportation": {1: 2000, 2: 2700, 3: 3400, 4: 4100, 5: 4800, 6: 5500,  7: 6200,  8: 6900},
    },
    "Kansas": {
        "childcare":      {1: 3621, 2: 4736, 3: 5851, 4: 6966, 5: 8081, 6: 9196, 7: 10311, 8: 11426},
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 3061, 2: 4003, 3: 4945, 4: 5887, 5: 6829, 6: 7771,  7: 7947,  8: 8124},
        "transportation": {1: 2000, 2: 2700, 3: 3400, 4: 4100, 5: 4800, 6: 5500,  7: 6200,  8: 6900},
    },
    "Kentucky": {
        "childcare":      {1: 3549, 2: 4640, 3: 5731, 4: 6822, 5: 7913, 6: 9004, 7: 10095, 8: 11186},
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 2707, 2: 3540, 3: 4374, 4: 5207, 5: 6040, 6: 6873,  7: 7029,  8: 7185},
        "transportation": {1: 1900, 2: 2600, 3: 3300, 4: 4000, 5: 4700, 6: 5400,  7: 6100,  8: 6800},
    },
    "Louisiana": {
        "childcare":      {1: 3203, 2: 4188, 3: 5173, 4: 6158, 5: 7143, 6: 8128, 7: 9113, 8: 10098},
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 2617, 2: 3422, 3: 4227, 4: 5032, 5: 5837, 6: 6642,  7: 6793,  8: 6944},
        "transportation": {1: 1800, 2: 2500, 3: 3200, 4: 3900, 5: 4600, 6: 5300,  7: 6000,  8: 6700},
    },
    "Maine": {
        "childcare":      {1: 5673, 2: 7418, 3: 9163, 4: 10908, 5: 12653, 6: 14398, 7: 16143, 8: 17888},
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 3173, 2: 4149, 3: 5125, 4: 6101, 5: 7077, 6: 8053,  7: 8236,  8: 8419},
        "transportation": {1: 2200, 2: 3000, 3: 3800, 4: 4600, 5: 5400, 6: 6200,  7: 7000,  8: 7800},
    },
    "Maryland": {
        "childcare":      {1: 3900, 2: 5101, 3: 6302, 4: 7503, 5: 8704, 6: 9905, 7: 11106, 8: 12307},
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 4113, 2: 5378, 3: 6644, 4: 7909, 5: 9175,  6: 10440, 7: 10678, 8: 10915},
        "transportation": {1: 2500, 2: 3300, 3: 4100, 4: 4900, 5: 5700,  6: 6500,  7: 7300,  8: 8100},
    },
    "Massachusetts": {
        "childcare":      {1: 3152, 2: 4122, 3: 5092, 4: 6062, 5: 7032, 6: 8002, 7: 8972, 8: 9942},
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 4465, 2: 5839, 3: 7213, 4: 8587, 5: 9961,  6: 11335, 7: 11593, 8: 11851},
        "transportation": {1: 2600, 2: 3500, 3: 4400, 4: 5300, 5: 6200,  6: 7100,  7: 8000,  8: 8900},
    },
    "Michigan": {
        "childcare":      {1: 2432, 2: 3288, 3: 4144, 4: 5000, 5: 5856, 6: 6712, 7: 7568, 8: 8424},
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 3114, 2: 4073, 3: 5031, 4: 5989, 5: 6948, 6: 7906,  7: 8085,  8: 8265},
        "transportation": {1: 2000, 2: 2700, 3: 3400, 4: 4100, 5: 4800, 6: 5500,  7: 6200,  8: 6900},
    },
    "Minnesota": {
        "childcare":      {1: 2560, 2: 3347, 3: 4134, 4: 4921, 5: 5708, 6: 6495, 7: 7282, 8: 8069},
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 3846, 2: 5030, 3: 6213, 4: 7397, 5: 8580, 6: 9764,  7: 9986,  8: 10208},
        "transportation": {1: 2300, 2: 3100, 3: 3900, 4: 4700, 5: 5500, 6: 6300,  7: 7100,  8: 7900},
    },
    "Mississippi": {
        "childcare":      {1: 2676, 2: 3499, 3: 4322, 4: 5145, 5: 5968, 6: 6791, 7: 7614, 8: 8437},
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 2341, 2: 3061, 3: 3781, 4: 4501, 5: 5221, 6: 5942,  7: 6077,  8: 6212},
        "transportation": {1: 1700, 2: 2300, 3: 2900, 4: 3500, 5: 4100, 6: 4700,  7: 5300,  8: 5900},
    },
    "Missouri": {
        "childcare":      {1: 1824, 2: 2466, 3: 3108, 4: 3750, 5: 4392, 6: 5034, 7: 5676, 8: 6318},
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 2942, 2: 3847, 3: 4752, 4: 5657, 5: 6562, 6: 7467,  7: 7637,  8: 7806},
        "transportation": {1: 1900, 2: 2600, 3: 3300, 4: 4000, 5: 4700, 6: 5400,  7: 6100,  8: 6800},
    },
    "Montana": {
        "childcare":      {1: 2323, 2: 3152, 3: 3981, 4: 4810, 5: 5639, 6: 6468, 7: 7297, 8: 8126},
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 3010, 2: 3936, 3: 4862, 4: 5789, 5: 6715, 6: 7641,  7: 7815,  8: 7988},
        "transportation": {1: 2000, 2: 2700, 3: 3400, 4: 4100, 5: 4800, 6: 5500,  7: 6200,  8: 6900},
    },
    "Nebraska": {
        "childcare":      {1: 2249, 2: 3041, 3: 3833, 4: 4625, 5: 5417, 6: 6209, 7: 7001, 8: 7793},
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 3168, 2: 4143, 3: 5117, 4: 6092, 5: 7067, 6: 8042,  7: 8224,  8: 8407},
        "transportation": {1: 2000, 2: 2700, 3: 3400, 4: 4100, 5: 4800, 6: 5500,  7: 6200,  8: 6900},
    },
    "Nevada": {
        "childcare":      {1: 1706, 2: 2231, 3: 2756, 4: 3281, 5: 3806, 6: 4331, 7: 4856, 8: 5381},
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 2731, 2: 3571, 3: 4411, 4: 5251, 5: 6092, 6: 6932,  7: 7089,  8: 7247},
        "transportation": {1: 2100, 2: 2900, 3: 3700, 4: 4500, 5: 5300, 6: 6100,  7: 6900,  8: 7700},
    },
    "New Hampshire": {
        "childcare":      {1: 4914, 2: 6427, 3: 7940, 4: 9453, 5: 10966, 6: 12479, 7: 13992, 8: 15505},
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 4059, 2: 5309, 3: 6558, 4: 7807, 5: 9056,  6: 10305, 7: 10539, 8: 10773},
        "transportation": {1: 2400, 2: 3200, 3: 4000, 4: 4800, 5: 5600,  6: 6400,  7: 7200,  8: 8000},
    },
    "New Jersey": {
        "childcare":      {1: 2509, 2: 3406, 3: 4303, 4: 5200, 5: 6097, 6: 6994, 7: 7891, 8: 8788},
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 4273, 2: 5587, 3: 6902, 4: 8217, 5: 9532,  6: 10846, 7: 11093, 8: 11339},
        "transportation": {1: 2600, 2: 3500, 3: 4400, 4: 5300, 5: 6200,  6: 7100,  7: 8000,  8: 8900},
    },
    "New Mexico": {
        "childcare":      {1: 5021, 2: 6814, 3: 8607, 4: 10400, 5: 12193, 6: 13986, 7: 15779, 8: 17572},
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 2405, 2: 3144, 3: 3884, 4: 4624, 5: 5364, 6: 6104,  7: 6243,  8: 6381},
        "transportation": {1: 2000, 2: 2700, 3: 3400, 4: 4100, 5: 4800, 6: 5500,  7: 6200,  8: 6900},
    },
    "New York": {
        "childcare":      {1: 4706, 2: 6155, 3: 7604, 4: 9053, 5: 10502, 6: 11951, 7: 13400, 8: 14849},
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 3563, 2: 4660, 3: 5756, 4: 6853, 5: 7949, 6: 9045,  7: 9251,  8: 9456},
        "transportation": {1: 2300, 2: 3100, 3: 3900, 4: 4700, 5: 5500, 6: 6300,  7: 7100,  8: 7900},
    },
    "North Carolina": {
        "childcare":      {1: 2429, 2: 3286, 3: 4143, 4: 5000, 5: 5857, 6: 6714, 7: 7571, 8: 8428},
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 2938, 2: 3842, 3: 4746, 4: 5650, 5: 6554, 6: 7458,  7: 7628,  8: 7797},
        "transportation": {1: 2000, 2: 2700, 3: 3400, 4: 4100, 5: 4800, 6: 5500,  7: 6200,  8: 6900},
    },
    "North Dakota": {
        "childcare":      {1: 3999, 2: 5231, 3: 6463, 4: 7695, 5: 8927, 6: 10159, 7: 11391, 8: 12623},
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 3446, 2: 4507, 3: 5567, 4: 6628, 5: 7688, 6: 8749,  7: 8947,  8: 9146},
        "transportation": {1: 2100, 2: 2900, 3: 3700, 4: 4500, 5: 5300, 6: 6100,  7: 6900,  8: 7700},
    },
    "Ohio": {
        "childcare":      {1: 1762, 2: 2383, 3: 3004, 4: 3625, 5: 4246, 6: 4867, 7: 5488, 8: 6109},
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 3063, 2: 4006, 3: 4948, 4: 5891, 5: 6833, 6: 7775,  7: 7952,  8: 8129},
        "transportation": {1: 2000, 2: 2700, 3: 3400, 4: 4100, 5: 4800, 6: 5500,  7: 6200,  8: 6900},
    },
    "Oklahoma": {
        "childcare":      {1: 3317, 2: 4337, 3: 5357, 4: 6377, 5: 7397, 6: 8417, 7: 9437, 8: 10457},
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 2510, 2: 3282, 3: 4054, 4: 4826, 5: 5599, 6: 6371,  7: 6516,  8: 6660},
        "transportation": {1: 1900, 2: 2600, 3: 3300, 4: 4000, 5: 4700, 6: 5400,  7: 6100,  8: 6800},
    },
    "Oregon": {
        "childcare":      {1: 2512, 2: 3408, 3: 4304, 4: 5200, 5: 6096, 6: 6992, 7: 7888, 8: 8784},
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 3361, 2: 4395, 3: 5429, 4: 6463, 5: 7497, 6: 8531,  7: 8724,  8: 8918},
        "transportation": {1: 2300, 2: 3100, 3: 3900, 4: 4700, 5: 5500, 6: 6300,  7: 7100,  8: 7900},
    },
    "Pennsylvania": {
        "childcare":      {1: 2509, 2: 3406, 3: 4303, 4: 5200, 5: 6097, 6: 6994, 7: 7891, 8: 8788},
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 3372, 2: 4409, 3: 5447, 4: 6484, 5: 7522, 6: 8559,  7: 8754,  8: 8948},
        "transportation": {1: 2200, 2: 3000, 3: 3800, 4: 4600, 5: 5400, 6: 6200,  7: 7000,  8: 7800},
    },
    "Rhode Island": {
        "childcare":      {1: 2509, 2: 3406, 3: 4303, 4: 5200, 5: 6097, 6: 6994, 7: 7891, 8: 8788},
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 3618, 2: 4731, 3: 5844, 4: 6957, 5: 8070, 6: 9183,  7: 9392,  8: 9600},
        "transportation": {1: 2300, 2: 3100, 3: 3900, 4: 4700, 5: 5500, 6: 6300,  7: 7100,  8: 7900},
    },
    "South Carolina": {
        "childcare":      {1: 3615, 2: 4728, 3: 5841, 4: 6954, 5: 8067, 6: 9180, 7: 10293, 8: 11406},
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 2768, 2: 3620, 3: 4472, 4: 5324, 5: 6175, 6: 7027,  7: 7187,  8: 7346},
        "transportation": {1: 1900, 2: 2600, 3: 3300, 4: 4000, 5: 4700, 6: 5400,  7: 6100,  8: 6800},
    },
    "South Dakota": {
        "childcare":      {1: 2626, 2: 3562, 3: 4498, 4: 5434, 5: 6370, 6: 7306, 7: 8242, 8: 9178},
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 3068, 2: 4012, 3: 4956, 4: 5900, 5: 6844, 6: 7788,  7: 7965,  8: 8142},
        "transportation": {1: 2000, 2: 2700, 3: 3400, 4: 4100, 5: 4800, 6: 5500,  7: 6200,  8: 6900},
    },
    "Tennessee": {
        "childcare":      {1: 3623, 2: 4738, 3: 5853, 4: 6968, 5: 8083, 6: 9198, 7: 10313, 8: 11428},
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 2738, 2: 3581, 3: 4424, 4: 5266, 5: 6109, 6: 6952,  7: 7110,  8: 7268},
        "transportation": {1: 1900, 2: 2600, 3: 3300, 4: 4000, 5: 4700, 6: 5400,  7: 6100,  8: 6800},
    },
    "Texas": {
        "childcare":      {1: 3801, 2: 4971, 3: 6141, 4: 7311, 5: 8481, 6: 9651, 7: 10821, 8: 11991},
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 2918, 2: 3816, 3: 4714, 4: 5612, 5: 6510, 6: 7408,  7: 7576,  8: 7744},
        "transportation": {1: 2000, 2: 2700, 3: 3400, 4: 4100, 5: 4800, 6: 5500,  7: 6200,  8: 6900},
    },
    "Utah": {
        "childcare":      {1: 4107, 2: 5372, 3: 6637, 4: 7902, 5: 9167, 6: 10432, 7: 11697, 8: 12962},
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 3183, 2: 4162, 3: 5141, 4: 6120, 5: 7100, 6: 8079,  7: 8262,  8: 8446},
        "transportation": {1: 2000, 2: 2700, 3: 3400, 4: 4100, 5: 4800, 6: 5500,  7: 6200,  8: 6900},
    },
    "Vermont": {
        "childcare":      {1: 5021, 2: 6814, 3: 8607, 4: 10400, 5: 12193, 6: 13986, 7: 15779, 8: 17572},
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 3518, 2: 4601, 3: 5684, 4: 6766, 5: 7849, 6: 8931,  7: 9134,  8: 9337},
        "transportation": {1: 2300, 2: 3100, 3: 3900, 4: 4700, 5: 5500, 6: 6300,  7: 7100,  8: 7900},
    },
    "Virginia": {
        "childcare":      {1: 4935, 2: 6454, 3: 7973, 4: 9492, 5: 11011, 6: 12530, 7: 14049, 8: 15568},
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 3731, 2: 4880, 3: 6028, 4: 7176, 5: 8324, 6: 9472,  7: 9687,  8: 9903},
        "transportation": {1: 2300, 2: 3100, 3: 3900, 4: 4700, 5: 5500, 6: 6300,  7: 7100,  8: 7900},
    },
    "Washington": {
        "childcare":      {1: 3131, 2: 4094, 3: 5057, 4: 6020, 5: 6983, 6: 7946, 7: 8909, 8: 9872},
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 3817, 2: 4992, 3: 6166, 4: 7341, 5: 8515,  6: 9690,  7: 9910,  8: 10130},
        "transportation": {1: 2500, 2: 3300, 3: 4100, 4: 4900, 5: 5700,  6: 6500,  7: 7300,  8: 8100},
    },
    "West Virginia": {
        "childcare":      {1: 3338, 2: 4366, 3: 5394, 4: 6422, 5: 7450, 6: 8478, 7: 9506, 8: 10534},
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 2550, 2: 3335, 3: 4120, 4: 4904, 5: 5689, 6: 6474,  7: 6621,  8: 6768},
        "transportation": {1: 1800, 2: 2500, 3: 3200, 4: 3900, 5: 4600, 6: 5300,  7: 6000,  8: 6700},
    },
    "Wisconsin": {
        "childcare":      {1: 2509, 2: 3406, 3: 4303, 4: 5200, 5: 6097, 6: 6994, 7: 7891, 8: 8788},
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 3322, 2: 4344, 3: 5366, 4: 6388, 5: 7411, 6: 8433,  7: 8624,  8: 8816},
        "transportation": {1: 2100, 2: 2900, 3: 3700, 4: 4500, 5: 5300, 6: 6100,  7: 6900,  8: 7700},
    },
    "Wyoming": {
        "childcare":      {1: 2195, 2: 2980, 3: 3765, 4: 4550, 5: 5335, 6: 6120, 7: 6905, 8: 7690},
        "internet":       FPL_200_LIMITS,
        "utility":        {1: 2988, 2: 3908, 3: 4827, 4: 5747, 5: 6666, 6: 7585,  7: 7758,  8: 7930},
        "transportation": {1: 2100, 2: 2900, 3: 3700, 4: 4500, 5: 5300, 6: 6100,  7: 6900,  8: 7700},
    },
}

# section 3: service locations
# all office locations are stored in locations.json so you can add new offices without touching this python file
# we load that file right now at startup and store the list in memory
with open(resource_path("locations.json"), encoding="utf-8") as _lf:
    LOCATIONS: list[dict] = json.load(_lf)

# section 5: form choice options
# these are the lists that fill in the dropdown menus on the household profile form

# choices for the employment status dropdown on step 2
EMPLOYMENT_OPTIONS = [
    "Working",
    "In school or job training",
    "Working and in school",
    "Looking for work",
    "Not working or in school",
    "Retired",
]

# choices for the age range dropdown
AGE_OPTIONS = ["Child", "Adult", "Senior"]
# choices for the state dropdown covering all us states and territories
STATE_OPTIONS = ["Alabama", "Alaska", "American Samoa", "Arizona", "Arkansas", "California", "Colorado", "Connecticut", "Delaware", "District of Columbia", "Florida", "Georgia", "Guam", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota", "Minor Outlying Islands", "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico", "New York", "North Carolina", "North Dakota", "Northern Mariana Islands", "Ohio", "Oklahoma", "Oregon", "Pennsylvania", "Puerto Rico", "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas", "U.S. Virgin Islands", "Utah", "Vermont",("Virginia"), ("Washington"), ("West Virginia"), ("Wisconsin"), ("Wyoming")]
# choices for the office search radius dropdown on the results screen (in miles)
RADIUS_OPTIONS = ["5", "10", "25", "50", "100"]

# section 6: app theme and visual constants
# these are all the colors, the version number, and the visual palette used throughout the ui

# version number shown in the about popup and the footer
APP_VERSION = "2.0.0"

# background color for each eligibility status pill badge
STATUS_COLORS = {
    "Highly eligible": "#134e2a",     # dark green background
    "Partially eligible": "#5c4510",  # dark amber background
    "Unlikely": "#5c1f1f",            # dark red background
}

# text color for each pill badge chosen to be readable on the dark backgrounds above
STATUS_TEXT_COLORS = {
    "Highly eligible": "#bbf7d0",
    "Partially eligible": "#fde68a",
    "Unlikely": "#fecaca",
}

# shorter label text for each status used in narrow pill chips where the full text would get cut off
STATUS_PILL_SHORT = {
    "Highly eligible": "High match",
    "Partially eligible": "Partial",
    "Unlikely": "Unlikely",
}


def status_pill_caption(full_status: str) -> str:
    # look up the short label for a status; fall back to the full status text if it is not in the table
    return STATUS_PILL_SHORT.get(full_status, full_status)


# dark theme color palette; every color used anywhere in the ui comes from this list of constants
ACCENT = "#38bdf8"          # bright sky blue used as the main highlight color
ACCENT_DIM = "#0ea5e9"      # a slightly darker blue used as a secondary highlight
ACCENT_GLOW = "#22d3ee"     # cyan used for glowing hover rings around focused elements
APP_BG = "#0a0e14"          # the main app background color (very dark near black)
APP_BG_ELEVATED = "#0f141c" # slightly lighter background used for the footer bar
CARD_BG = "#121826"         # background color of content cards
CARD_BG_HOVER = "#171d2e"   # card background when the mouse is hovering over it
RAIL_BG = "#0d1118"         # background color of the left progress rail sidebar
BORDER = "#2a3447"          # subtle border color drawn around cards and input fields
BORDER_FOCUS = ACCENT       # border color used when an input field has keyboard focus
TEXT = "#e8eef9"            # main text color (near white)
MUTED = "#94a3b8"           # secondary or hint text color (medium gray)
SUBTEXT = "#c5d1e8"         # body paragraph text color (slightly dimmer than main text)
PRIMARY = "#3b82f6"         # blue color for primary action buttons
PRIMARY_HOVER = "#2563eb"   # primary button color when the mouse is hovering over it
PRIMARY_PRESSED = "#1d4ed8" # primary button color while the user is clicking it
INPUT_BG = "#1a2233"        # background color for text input fields
HEADER_BG = "#0f141c"       # background color of the top header bar
SHADOW = "#05070a"          # very dark color used for drop shadows under cards
SUCCESS = "#34d399"         # green color used to indicate a good or passing result
WARNING = "#fbbf24"         # yellow color used to flag something that needs attention


def preferred_ui_font(tk_ref: tk.Misc | None = None) -> str:
    """pick the nicest font that is actually installed on this computer.
    we ask tkinter what fonts are available and return the first one from our preference list.
    this prevents ugly fallback fonts on systems that do not have our first choice."""
    # use the given tk widget as a reference point for the font query, or fall back to the default root window
    ref = tk_ref if tk_ref is not None else getattr(tk, "_default_root", None)
    if ref is None:
        # tkinter is not running yet so we cannot query fonts; return a safe fallback
        return "Helvetica"
    # get the set of all font family names installed on this system
    families = set(tkfont.families(ref))
    # go through our preferred fonts in order and return the first one that is actually installed
    for name in (".SF NS Text", "SF Pro Text", "Segoe UI", "Helvetica Neue", "Avenir Next"):
        if name in families:
            return name
    return "Helvetica"


# placeholder font family used before tkinter starts; replaced with a nicer font once the app window opens
FONT_FAMILY = "Helvetica"

# for each program this lists the documents the user should bring when they visit an office
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

# documents that everyone should bring regardless of which program they are applying for
MASTER_DOCUMENT_LIST = [
    "Government-issued photo ID for each adult applying",
    "Social Security cards or numbers for household members (if required locally)",
    "Last 30 days of pay stubs or self-employment records",
    "Bank statements (last 2–3 months) if requested",
    "Proof of address (lease, utility bill, or official mail)",
]


# section 7: data containers
# these are small dataclasses used to store the results of eligibility checks

# a single rule that gets checked against the user such as "is your income under the limit?"
# it stores whether the check passed and what text to show for either outcome
@dataclass
class RuleCheck:
    name: str           # short label for this rule like "income"
    passed: bool        # true if the user passed this rule
    pass_text: str      # the message to show the user when they pass this rule
    fail_text: str      # the message to show the user when they fail this rule
    close: bool = False     # true if the user is close to passing but not quite there
    critical: bool = False  # true if failing this one rule alone means they definitely do not qualify


# the combined result for one program after running all of its rules
@dataclass
class ProgramResult:
    status: str             # one of "highly eligible", "partially eligible", or "unlikely"
    explanation: str        # a plain english summary sentence shown to the user
    passed: list[str]       # list of all the pass messages from rules the user met
    missed: list[str]       # list of all the fail messages from rules the user did not meet


def draw_rounded_rect(canvas: tk.Canvas, x1: int, y1: int, x2: int, y2: int, radius: int, **kwargs) -> int:
    """draw a rectangle with rounded corners on a tkinter canvas.
    tkinter has no built in rounded rectangle shape, so we fake one by drawing a
    smoothed polygon and pulling each corner inward by the radius amount."""
    # build the list of x y points that trace the outline of the rounded rectangle
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
    # smooth=true tells tkinter to curve the corners of the polygon
    return canvas.create_polygon(points, smooth=True, **kwargs)


def widget_background(widget: tk.Widget, fallback: str = APP_BG) -> str:
    """get the background color of a tkinter widget, with a safe fallback color if tkinter throws an error."""
    try:
        return str(widget.cget("bg"))
    except tk.TclError:
        # some widgets do not support the bg option so we return the fallback color instead
        return fallback


class RoundedCard(tk.Frame):
    """a card widget that appears to have rounded corners.
    tkinter frames are always rectangular, so we fake the look by drawing a
    rounded shape on a canvas and then placing a regular frame on top of it for the content."""

    def __init__(self, parent: tk.Widget, background: str = APP_BG) -> None:
        # initialize this as a regular frame with no border or highlight ring
        super().__init__(parent, bg=background, bd=0, highlightthickness=0)
        self.radius = 22   # how many pixels of rounding the corners get
        self.margin = 8    # the gap in pixels between the rounded shape and the content inside
        # the canvas is the drawing surface where we paint the rounded background shape and shadow
        self.canvas = tk.Canvas(self, bg=background, bd=0, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        # the body frame sits on top of the canvas and this is where you put the actual child widgets
        self.body = tk.Frame(self.canvas, bg=CARD_BG, bd=0, highlightthickness=0)
        # embed the body frame inside the canvas at position (margin, margin) measured from the top left
        self.window_id = self.canvas.create_window((self.margin, self.margin), window=self.body, anchor="nw")
        # whenever the canvas size changes, redraw the rounded shape to match
        self.canvas.bind("<Configure>", self._redraw)
        # whenever the body grows because more widgets were added, grow the canvas to match
        self.body.bind("<Configure>", self._sync_size)

    def _sync_size(self, _event: tk.Event | None = None) -> None:
        # make the canvas just big enough to hold the body frame plus the margin gap on each side
        width = max(120, self.body.winfo_reqwidth() + self.margin * 2)
        height = max(60, self.body.winfo_reqheight() + self.margin * 2)
        self.canvas.configure(width=width, height=height)
        self._redraw()

    def _redraw(self, _event: tk.Event | None = None) -> None:
        # figure out how big we need to draw by taking the larger of the canvas size vs the body size
        width = max(self.canvas.winfo_width(), self.body.winfo_reqwidth() + self.margin * 2)
        height = max(self.canvas.winfo_height(), self.body.winfo_reqheight() + self.margin * 2)
        # wipe anything previously drawn on the canvas before redrawing
        self.canvas.delete("card-shape")
        # draw a slightly offset dark rounded shape first to create a soft drop shadow effect
        draw_rounded_rect(self.canvas, self.margin + 2, self.margin + 3, width - 2, height - 2, self.radius, fill=SHADOW, outline="", tags="card-shape")
        # draw the actual card shape on top of the shadow
        draw_rounded_rect(self.canvas, self.margin, self.margin, width - 4, height - 5, self.radius, fill=CARD_BG, outline=BORDER, width=1, tags="card-shape")
        # push the drawn shapes behind the body frame so the widgets inside the body show on top
        self.canvas.tag_lower("card-shape")
        # tell the body frame how wide it is allowed to be and set its position
        self.canvas.itemconfigure(self.window_id, width=max(1, width - self.margin * 2))
        self.canvas.coords(self.window_id, self.margin, self.margin)


class ModernCheckbox(tk.Frame):
    """a custom checkbox widget that looks modern with a colored checked state and a hover glow effect."""

    def __init__(self, parent: tk.Widget, text: str = "", variable: tk.BooleanVar | None = None,
                 command: callable | None = None, bg: str = CARD_BG, fg: str = TEXT) -> None:
        super().__init__(parent, bg=bg)

        # use the provided variable or create a new boolean variable starting at false
        self.variable = variable or tk.BooleanVar(value=False)
        self.command = command
        self.bg_color = bg
        self.fg_color = fg

        # the container frame that holds the drawn checkbox square
        self.checkbox_frame = tk.Frame(self, bg=bg)
        self.checkbox_frame.pack(side="left", anchor="w")

        # a small canvas where we draw the checkbox box and checkmark ourselves
        self.checkbox_canvas = tk.Canvas(
            self.checkbox_frame,
            width=24, height=24,
            bg=bg,
            highlightthickness=0,
            bd=0,
            cursor="hand2"
        )
        self.checkbox_canvas.pack(pady=2)

        # if a text label was given, place it to the right of the checkbox box
        if text:
            self.label = tk.Label(
                self,
                text=text,
                bg=bg,
                fg=fg,
                font=(FONT_FAMILY, 10),
                cursor="hand2"
            )
            self.label.pack(side="left", anchor="w", padx=(8, 0))

        # track whether the mouse is currently over this widget for hover styling
        self._hover = False
        self._animation_id = None

        # connect mouse events so the checkbox responds to hover and clicks
        self.checkbox_canvas.bind("<Enter>", self._on_hover)
        self.checkbox_canvas.bind("<Leave>", self._on_leave)
        self.checkbox_canvas.bind("<Button-1>", self._on_click)
        if text:
            # also respond to hovering and clicking the text label next to the box
            self.label.bind("<Enter>", self._on_hover)
            self.label.bind("<Leave>", self._on_leave)
            self.label.bind("<Button-1>", self._on_click)

        # whenever the variable changes (checked or unchecked) redraw the checkbox
        self.variable.trace("w", lambda *args: self._redraw())
        self._redraw()

    def _on_hover(self, _event=None):
        # mouse entered the widget, switch to hover appearance
        self._hover = True
        self._redraw()

    def _on_leave(self, _event=None):
        # mouse left the widget, switch back to normal appearance
        self._hover = False
        self._redraw()

    def _on_click(self, _event=None):
        # toggle the checked state when clicked
        self.variable.set(not self.variable.get())
        if self.command:
            self.command()

    def _redraw(self):
        # erase the canvas and draw fresh based on current state
        self.checkbox_canvas.delete("all")

        is_checked = self.variable.get()
        size = 24

        # pick border and fill colors based on whether the box is checked or hovered
        border_color = "#4f46e5" if is_checked else ("#cbd5e1" if self._hover else "#d1d5db")
        bg_color = "#4f46e5" if is_checked else ("#f0f9ff" if self._hover else "white")

        # draw the main box shape (simplified to a rectangle for better macos compatibility)
        self.checkbox_canvas.create_rectangle(
            2, 2, size-2, size-2,
            fill=bg_color,
            outline=border_color,
            width=2,
            tags="box"
        )

        # draw a faint outer glow rectangle when hovered but not yet checked
        if self._hover and not is_checked:
            self.checkbox_canvas.create_rectangle(
                1, 1, size-1, size-1,
                fill="",
                outline=border_color,
                width=1,
                tags="glow"
            )

        # draw the white checkmark lines when the box is checked
        if is_checked:
            checkmark_color = "white"
            # two lines form the checkmark: a short diagonal going down then a longer one going up
            self.checkbox_canvas.create_line(6, 12, 10, 16, fill=checkmark_color, width=2, tags="check")
            self.checkbox_canvas.create_line(10, 16, 18, 6, fill=checkmark_color, width=2, tags="check")


class PillLabel(tk.Canvas):
    """a small rounded badge widget with text inside, like the "high match" chip.
    we use a canvas so we can draw the rounded pill shape ourselves."""

    def __init__(self, parent: tk.Widget, text: str, fill: str, foreground: str, background: str = CARD_BG) -> None:
        # initialize as a plain canvas with no visible border
        super().__init__(parent, bg=background, bd=0, highlightthickness=0)
        # save all the display properties so we can redraw if they change later
        self._fill = fill                # the background color of the pill shape itself
        self._foreground = foreground    # the text color inside the pill
        self._background = background    # the color of the area outside the pill shape
        self._text = text
        # create the bold font used for the short label inside the pill
        self._pill_font = tkfont.Font(family=FONT_FAMILY, size=10, weight="bold")
        self._redraw_pill()

    def set_text(self, text: str) -> None:
        # update the pill text and redraw it
        self._text = text
        self._redraw_pill()

    def _redraw_pill(self) -> None:
        # wipe the canvas before redrawing
        self.delete("all")
        text = self._text
        # measure how wide the text is and add padding so the pill fits the text snugly
        width = self._pill_font.measure(text) + 36
        height = self._pill_font.metrics("linespace") + 16
        # resize the canvas to exactly match the pill size we just calculated
        super().configure(width=width, height=height, bg=self._background)
        # draw the rounded pill shape as a filled rounded rectangle
        draw_rounded_rect(self, 1, 1, width - 1, height - 1, 16, fill=self._fill, outline="")
        # draw the label text centered inside the pill
        self.create_text(width // 2, height // 2, text=text, fill=self._foreground, font=self._pill_font)


class ModernButton(tk.Canvas):
    """a custom button widget drawn on a canvas so it can have rounded corners and hover color effects.
    tkinter's built in button cannot do rounded corners so we draw it ourselves."""

    # color sets for the four button style variants
    # each style has colors for normal state, hover (mouse over), and pressed (clicked), plus the text color
    THEMES = {
        "primary": {"normal": PRIMARY, "hover": PRIMARY_HOVER, "pressed": PRIMARY_PRESSED, "fg": "#f8fafc"},
        "secondary": {"normal": "#1e293b", "hover": "#273549", "pressed": "#334155", "fg": TEXT},
        "ghost": {"normal": CARD_BG, "hover": CARD_BG_HOVER, "pressed": "#1e293b", "fg": TEXT},
        "accent": {"normal": "#0c4a6e", "hover": "#075985", "pressed": "#0369a1", "fg": ACCENT_GLOW},
    }

    def __init__(self, parent: tk.Widget, text: str, command, variant: str = "secondary", background: str | None = None) -> None:
        # store the basic properties of this button
        self.text = text         # the label text shown on the button
        self.command = command   # the function to call when the user clicks
        self.variant = variant   # the color style to use, such as "primary", "secondary", "ghost", or "accent"
        self.state = "normal"    # either "normal" or "disabled"
        # bold font for the text label on the button
        self.button_font = tkfont.Font(family=FONT_FAMILY, size=11, weight="bold")
        self.height = 48         # button height in pixels
        self.pad_x = 38          # horizontal padding added on each side of the text
        self._corner_r = 18      # how rounded the button corners are
        # if no background color was given, copy the background color of the parent widget
        self.background = background or widget_background(parent)
        # calculate the width needed to fit the text plus the left and right padding
        width = self._width_for_text(text)
        # initialize the underlying canvas with the right size, background, and hand cursor
        super().__init__(parent, width=width, height=self.height, bg=self.background, bd=0, highlightthickness=0, cursor="hand2")
        self._hover = False  # tracks whether the mouse is currently over the button
        # hook up mouse events to the drawing methods
        self.bind("<Enter>", self._on_enter)                    # fires when the mouse enters the button area
        self.bind("<Leave>", self._on_leave)                    # fires when the mouse leaves the button area
        self.bind("<ButtonPress-1>", lambda _event: self._draw("pressed"))  # fires when the mouse button presses down
        self.bind("<ButtonRelease-1>", self._release)           # fires when the mouse button is released
        # draw the button in its starting normal state
        self._draw("normal")

    def _on_enter(self, _event: tk.Event) -> None:
        # the mouse moved onto the button so switch to the hover appearance
        self._hover = True
        self._draw("hover")

    def _on_leave(self, _event: tk.Event) -> None:
        # the mouse moved off the button so go back to the normal appearance
        self._hover = False
        self._draw("normal")

    def _width_for_text(self, text: str) -> int:
        # measure the text width in pixels and add padding on both sides; always at least 96 pixels wide
        return max(96, self.button_font.measure(text) + self.pad_x * 2)

    def _release(self, _event: tk.Event) -> None:
        # the mouse button was released; if the button is enabled run the command
        if self.state != "disabled" and self.command:
            self.command()
        # after the click, stay in hover state if the mouse is still over the button, otherwise go back to normal
        self._draw("hover" if self.state != "disabled" and self._hover else "normal")

    def _draw(self, mode: str) -> None:
        # erase the canvas before drawing fresh
        self.delete("all")
        theme = self.THEMES[self.variant]
        disabled = self.state == "disabled"
        # choose fill and text colors: grayed out if disabled, otherwise use the theme colors for this mode
        fill = "#334155" if disabled else theme[mode]
        fg = "#64748b" if disabled else theme["fg"]
        width = int(self.cget("width"))
        # when the mouse is hovering and the button is enabled, draw a soft glow ring around the outside
        r = getattr(self, "_corner_r", 18)
        if not disabled and mode == "hover":
            glow = ACCENT_GLOW if self.variant == "primary" else BORDER
            draw_rounded_rect(self, 0, 0, width, self.height, r + 2, fill="", outline=glow, width=2)
        # draw the main button shape as a rounded rectangle
        draw_rounded_rect(self, 2, 2, width - 2, self.height - 2, r, fill=fill, outline="")
        # draw the label text centered inside the button
        self.create_text(width // 2, self.height // 2, text=self.text, fill=fg, font=self.button_font)
        # show a hand cursor when the button is clickable and an arrow cursor when it is disabled
        super().configure(cursor="arrow" if disabled else "hand2")

    def configure(self, cnf=None, **kwargs) -> None:  # type: ignore[override]
        """update the button's text, state, command, or other properties; works the same as tkinter's standard configure."""
        # combine any positional config dict and keyword arguments into one dict
        options = {}
        if cnf:
            options.update(cnf)
        options.update(kwargs)
        # if the text changed, update it and resize the canvas to fit the new text
        if "text" in options:
            self.text = options.pop("text")
            super().configure(width=self._width_for_text(self.text))
        # if the state changed (for example to disabled) save the new value
        if "state" in options:
            self.state = options.pop("state")
        # if a new click handler was provided, replace the old one
        if "command" in options:
            self.command = options.pop("command")
        # pass any remaining options through to the underlying canvas
        if options:
            super().configure(**options)
        # redraw the button to reflect any changes we just made
        if hasattr(self, "button_font"):
            self._draw("normal")

    # config is an alias for configure so both names work the same way
    config = configure


class CanvasScrollbar(tk.Canvas):
    """a vertical scrollbar drawn on a canvas so we can style it ourselves with a rounded thumb."""

    def __init__(self, parent, command=None, width=10, bg="#222", thumb_color="#888"):
        super().__init__(parent, width=width, height=1, highlightthickness=0, bg=bg)

        self.command = command
        self.thumb_color = thumb_color
        self._start = 0   # how far from the top the visible portion starts (0.0 to 1.0)
        self._end = 1     # how far from the top the visible portion ends (0.0 to 1.0)
        self._dragging = False

        # connect mouse events for clicking and dragging the scrollbar thumb
        self.bind("<Button-1>", self._click)
        self.bind("<B1-Motion>", self._drag)
        self.bind("<ButtonRelease-1>", self._release)
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Enter>", lambda e: self.config(cursor="hand2"))
        self.bind("<Leave>", lambda e: self.config(cursor=""))

    def set(self, start, end):
        """update the scrollbar thumb position; start and end are fractions between 0.0 and 1.0."""
        self._start = max(0.0, min(1.0, float(start)))
        self._end = max(0.0, min(1.0, float(end)))
        self._draw()

    def _draw(self):
        """erase and redraw the rounded scrollbar thumb at the correct position."""
        self.delete("all")

        h = self.winfo_height()
        w = self.winfo_width()

        if h < 4 or w < 4:
            return  # canvas is too small to draw anything meaningful

        # figure out where the thumb starts and ends in pixel coordinates
        thumb_start = int(self._start * h)
        thumb_end = int(self._end * h)
        thumb_height = thumb_end - thumb_start

        # enforce a minimum thumb height so it is always grabbable
        min_thumb = max(16, int(h * 0.05))
        if thumb_height < min_thumb:
            thumb_height = min_thumb
            thumb_end = thumb_start + thumb_height

        # keep the thumb within the bounds of the canvas
        thumb_start = max(0, min(thumb_start, h - thumb_height))
        thumb_end = min(h, thumb_start + thumb_height)

        radius = w // 2

        # draw the middle rectangular body of the thumb
        self.create_rectangle(
            2, thumb_start + radius,
            w - 2, thumb_end - radius,
            fill=self.thumb_color,
            outline=""
        )

        # draw the top rounded cap using an oval
        if thumb_start + 2 * radius <= thumb_end:
            self.create_oval(
                2, thumb_start,
                w - 2, thumb_start + 2 * radius,
                fill=self.thumb_color,
                outline=""
            )

        # draw the bottom rounded cap using an oval
        if thumb_end - 2 * radius >= thumb_start:
            self.create_oval(
                2, thumb_end - 2 * radius,
                w - 2, thumb_end,
                fill=self.thumb_color,
                outline=""
            )

    def _click(self, event):
        """start dragging when the user clicks on the scrollbar."""
        self._dragging = True
        self._drag(event)

    def _drag(self, event):
        """as the user drags, convert the mouse y position into a scroll fraction and notify the canvas."""
        if not self.command:
            return

        h = self.winfo_height()
        if h <= 0:
            return

        # convert the y position of the mouse into a 0.0 to 1.0 fraction of the total height
        fraction = event.y / h
        fraction = max(0.0, min(1.0, fraction))

        self.command("moveto", fraction)

    def _release(self, _event):
        """stop dragging when the user lets go of the mouse button."""
        self._dragging = False


class HorizontalCanvasScrollbar(tk.Canvas):
    """a horizontal scrollbar drawn on a canvas so we can style it with a rounded thumb."""

    def __init__(self, parent, command=None, height=10, bg="#222", thumb_color="#888"):
        super().__init__(parent, height=height, width=1, highlightthickness=0, bg=bg)

        self.command = command
        self.thumb_color = thumb_color
        self._start = 0   # left edge of the visible area as a fraction from 0.0 to 1.0
        self._end = 1     # right edge of the visible area as a fraction from 0.0 to 1.0
        self._dragging = False

        # connect mouse events for clicking and dragging the scrollbar thumb
        self.bind("<Button-1>", self._click)
        self.bind("<B1-Motion>", self._drag)
        self.bind("<ButtonRelease-1>", self._release)
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Enter>", lambda e: self.config(cursor="hand2"))
        self.bind("<Leave>", lambda e: self.config(cursor=""))

    def set(self, start, end):
        """update the scrollbar thumb position; start and end are fractions between 0.0 and 1.0."""
        self._start = max(0.0, min(1.0, float(start)))
        self._end = max(0.0, min(1.0, float(end)))
        self._draw()

    def _draw(self):
        """erase and redraw the rounded horizontal scrollbar thumb at the correct position."""
        self.delete("all")

        h = self.winfo_height()
        w = self.winfo_width()

        if h < 4 or w < 4:
            return  # canvas is too small to draw anything meaningful

        # convert the start and end fractions into pixel positions along the width
        thumb_start = int(self._start * w)
        thumb_end = int(self._end * w)
        thumb_width = thumb_end - thumb_start

        # enforce a minimum thumb width so it is always easy to grab
        min_thumb = max(16, int(w * 0.05))
        if thumb_width < min_thumb:
            thumb_width = min_thumb
            thumb_end = thumb_start + thumb_width

        # keep the thumb within the bounds of the canvas
        thumb_start = max(0, min(thumb_start, w - thumb_width))
        thumb_end = min(w, thumb_start + thumb_width)

        radius = h // 2

        # draw the middle rectangular body of the thumb
        self.create_rectangle(
            thumb_start + radius, 2,
            thumb_end - radius, h - 2,
            fill=self.thumb_color,
            outline=""
        )

        # draw the left rounded cap using an oval
        if thumb_start + 2 * radius <= thumb_end:
            self.create_oval(
                thumb_start, 2,
                thumb_start + 2 * radius, h - 2,
                fill=self.thumb_color,
                outline=""
            )

        # draw the right rounded cap using an oval
        if thumb_end - 2 * radius >= thumb_start:
            self.create_oval(
                thumb_end - 2 * radius, 2,
                thumb_end, h - 2,
                fill=self.thumb_color,
                outline=""
            )

    def _click(self, event):
        """start dragging when the user clicks on the scrollbar."""
        self._dragging = True
        self._drag(event)

    def _drag(self, event):
        """as the user drags, convert the mouse x position into a scroll fraction and notify the canvas."""
        if not self.command:
            return

        w = self.winfo_width()
        if w <= 0:
            return

        # convert the x position of the mouse into a 0.0 to 1.0 fraction of the total width
        fraction = event.x / w
        fraction = max(0.0, min(1.0, fraction))

        self.command("moveto", fraction)

    def _release(self, _event):
        """stop dragging when the user releases the mouse button."""
        self._dragging = False


class HorizontalScrollableFrame(ttk.Frame):
    """a frame that can scroll horizontally; useful for rows of cards that are wider than the window."""

    _active = None
    _wheel_bound = False

    def __init__(self, parent: ttk.Widget, background: str = APP_BG) -> None:
        super().__init__(parent)

        self._bg = background

        # the main canvas that the content slides inside when scrolling horizontally
        self.canvas = tk.Canvas(
            self,
            borderwidth=0,
            highlightthickness=0,
            background=background,
            xscrollincrement=20,
        )

        # our custom horizontal scrollbar that sits along the bottom
        self.scrollbar = HorizontalCanvasScrollbar(
            self,
            command=self._scroll_command,
            height=10,
            bg=background,
            thumb_color="#888"
        )

        # the actual content frame that lives inside the canvas and holds child widgets
        self.inner = tk.Frame(self.canvas, background=background)

        # embed the inner frame into the canvas starting at the top left corner
        self.window_id = self.canvas.create_window(
            (0, 0),
            window=self.inner,
            anchor="nw"
        )

        # link the canvas scroll position to the scrollbar so they stay in sync
        self.canvas.configure(xscrollcommand=self._on_scroll)

        # put the canvas on top and the scrollbar along the bottom
        self.canvas.pack(side="top", fill="both", expand=True)
        self.scrollbar.pack(side="bottom", fill="x")

        # when the inner frame grows, update how far the canvas can scroll
        self.inner.bind("<Configure>", self._update_scroll_region)
        # when the canvas is resized, adjust the height of the inner frame to match
        self.canvas.bind("<Configure>", self._resize_inner)

        # track which scrollable frame is currently under the mouse
        self.bind("<Enter>", self._activate)
        self.canvas.bind("<Enter>", self._activate)
        self.inner.bind("<Enter>", self._activate)

        # arrow key bindings so the user can scroll with the keyboard
        self.canvas.bind("<Left>", self._on_key_left)
        self.canvas.bind("<Right>", self._on_key_right)

        self.bind("<Destroy>", self._on_destroy)

    def _update_scroll_region(self, _event=None):
        # recalculate the total scrollable area after the inner frame changes size
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _resize_inner(self, event):
        # keep the inner frame's height the same as the canvas height so it fills vertically
        self.canvas.itemconfig(self.window_id, height=event.height)

    def _activate(self, _event):
        # mark this frame as the active scrollable target and give it keyboard focus
        HorizontalScrollableFrame._active = self
        self.canvas.focus_set()

    def _on_destroy(self, event):
        # when this widget is destroyed, clear the active reference so we do not keep a dead pointer
        if event.widget == self:
            if HorizontalScrollableFrame._active is self:
                HorizontalScrollableFrame._active = None

    def _on_scroll(self, start, end):
        # called by the canvas whenever its scroll position changes; passes the position to the scrollbar
        self.scrollbar.set(start, end)

    def _scroll_command(self, *args):
        # called by the scrollbar when the user drags; passes the command to the canvas
        self.canvas.xview(*args)

    def _on_key_left(self, _event):
        # scroll left 3 units when the left arrow key is pressed
        self.canvas.xview_scroll(-3, "units")

    def _on_key_right(self, _event):
        # scroll right 3 units when the right arrow key is pressed
        self.canvas.xview_scroll(3, "units")


class ScrollableFrame(ttk.Frame):
    """a frame that can scroll vertically using a custom drawn scrollbar and keyboard shortcuts."""

    _active = None      # the scrollable frame that the mouse is currently hovering over
    _wheel_bound = False  # whether we have already hooked up the global mousewheel event

    def __init__(self, parent: tk.Widget, background: str = APP_BG) -> None:
        super().__init__(parent)

        self._bg = background

        # the main canvas that the content slides inside when scrolling
        self.canvas = tk.Canvas(
            self,
            borderwidth=0,
            highlightthickness=0,
            background=background,
            highlightcolor=background,
            highlightbackground=background,
            yscrollincrement=20,
        )
        self.canvas.config(takefocus=True)  # allow the canvas to receive keyboard events

        # our custom vertical scrollbar placed along the right side
        self.scrollbar = CanvasScrollbar(
            self,
            command=self._scroll_command,
            width=10,
            bg=background,
            thumb_color="#888"
        )

        # the actual content frame inside the canvas where child widgets are placed
        self.inner = tk.Frame(self.canvas, background=background)

        # embed the inner frame into the canvas starting at the top left
        self.window_id = self.canvas.create_window(
            (0, 0),
            window=self.inner,
            anchor="nw"
        )

        # link the canvas scroll position to the scrollbar so they stay in sync
        self.canvas.configure(yscrollcommand=self._on_scroll)

        # canvas fills the left side and the scrollbar goes along the right
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # when the inner frame changes size, update the scroll region so scrolling still works
        self.inner.bind("<Configure>", self._update_scroll_region)
        # when the canvas is resized, stretch the inner frame to match its width
        self.canvas.bind("<Configure>", self._resize_inner)

        # track which scrollable frame is under the mouse for mousewheel routing
        self.bind("<Enter>", self._activate)
        self.canvas.bind("<Enter>", self._activate)
        self.inner.bind("<Enter>", self._activate)

        # keyboard scrolling bindings on the canvas
        self.canvas.bind("<KeyPress-Up>", self._on_key_up)
        self.canvas.bind("<KeyPress-Down>", self._on_key_down)
        self.canvas.bind("<KeyPress-Prior>", self._on_page_up)
        self.canvas.bind("<KeyPress-Next>", self._on_page_down)
        self.canvas.bind("<KeyPress-Home>", self._on_home)
        self.canvas.bind("<KeyPress-End>", self._on_end)

        # also bind keyboard scrolling at the frame level for more reliable event capture
        self.bind("<KeyPress-Up>", self._on_key_up)
        self.bind("<KeyPress-Down>", self._on_key_down)
        self.bind("<KeyPress-Prior>", self._on_page_up)
        self.bind("<KeyPress-Next>", self._on_page_down)
        self.bind("<KeyPress-Home>", self._on_home)
        self.bind("<KeyPress-End>", self._on_end)

        self.bind("<Destroy>", self._on_destroy)

    def _update_scroll_region(self, _event=None):
        # recalculate how far the canvas can scroll based on the total content size
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _resize_inner(self, event):
        # stretch the inner frame to match the canvas width so content fills the full area
        self.canvas.itemconfig(self.window_id, width=event.width)

    def _activate(self, _event):
        # remember this as the active scroll target and give the canvas keyboard focus
        ScrollableFrame._active = self
        self.canvas.focus_set()

    def _on_destroy(self, event):
        # when this widget is destroyed, clear the active reference so we do not hold onto it
        if event.widget == self:
            if ScrollableFrame._active is self:
                ScrollableFrame._active = None

    def _on_scroll(self, start, end):
        # called by the canvas when its scroll position changes; updates the scrollbar to match
        self.scrollbar.set(start, end)

    def _scroll_command(self, *args):
        # called by the scrollbar when the user drags it; passes the scroll command to the canvas
        self.canvas.yview(*args)

    def _on_key_up(self, _event):
        # scroll up 3 units when the up arrow key is pressed
        self.canvas.yview_scroll(-3, "units")

    def _on_key_down(self, _event):
        # scroll down 3 units when the down arrow key is pressed
        self.canvas.yview_scroll(3, "units")

    def _on_page_up(self, _event):
        # scroll up a full page (10 units) when the page up key is pressed
        self.canvas.yview_scroll(-10, "units")

    def _on_page_down(self, _event):
        # scroll down a full page (10 units) when the page down key is pressed
        self.canvas.yview_scroll(10, "units")

    def _on_home(self, _event):
        """scroll all the way to the top when the home key is pressed."""
        self.canvas.yview_moveto(0)

    def _on_end(self, _event):
        """scroll all the way to the bottom when the end key is pressed."""
        self.canvas.yview_moveto(1)

    @classmethod
    def hook_mousewheel(cls, root: tk.Misc) -> None:
        # hook up global mousewheel events once so any scrollable frame in the app can receive them
        if cls._wheel_bound:
            return

        root.bind_all("<MouseWheel>", cls._on_mousewheel_all)
        root.bind_all("<Button-4>", cls._on_linux_up_all)
        root.bind_all("<Button-5>", cls._on_linux_down_all)

        cls._wheel_bound = True

    @classmethod
    def _scroll_target(cls, event):
        """walk up the widget tree from the event's widget to find the nearest scrollable frame."""
        w = getattr(event, "widget", None)

        while w is not None:
            if isinstance(w, ScrollableFrame):
                try:
                    if w.winfo_exists() and w.winfo_ismapped():
                        return w
                except tk.TclError:
                    pass
            try:
                w = w.master
            except Exception:
                break

        # fall back to whichever frame was last active under the mouse
        return cls._active

    @classmethod
    def _on_mousewheel_all(cls, event):
        """handle mousewheel scrolling on windows and macos."""
        target = cls._scroll_target(event)
        if target:
            delta = getattr(event, "delta", 0)
            if delta == 0:
                return
            # a standard mouse click sends delta=120; a trackpad sends smaller values
            # we scale it so one click scrolls about 3 units (which is 60px at yscrollincrement=20)
            units = max(1, abs(delta) // 40) * (-1 if delta > 0 else 1)
            target.canvas.yview_scroll(units, "units")

    @classmethod
    def _on_linux_up_all(cls, event):
        # on linux the scroll wheel sends button 4 events for scrolling up
        target = cls._scroll_target(event)
        if target:
            target.canvas.yview_scroll(-3, "units")

    @classmethod
    def _on_linux_down_all(cls, event):
        # on linux the scroll wheel sends button 5 events for scrolling down
        target = cls._scroll_target(event)
        if target:
            target.canvas.yview_scroll(3, "units")


# persistence helpers and small ux utilities for settings, maps, clipboard, and toast popups


def resolve_brand_logo_path() -> Path | None:
    """look through the candidate logo paths and return the first one that actually exists on disk, or none."""
    for candidate in BRAND_LOGO_CANDIDATES:
        if candidate.exists():
            return candidate
    return None

def load_logo():
    # if pillow is not installed we cannot load the logo image
    if Image is None or ImageTk is None:
        return None

    # find the first candidate logo file that exists on disk
    logo_path = next((p for p in BRAND_LOGO_CANDIDATES if p.exists()), None)
    if not logo_path:
        print("no logo found")
        return None

    img = Image.open(logo_path)

    # resize the logo to the display size we want it to appear at
    DISPLAY_SIZE = (180, 180)
    img = img.resize(DISPLAY_SIZE, Image.LANCZOS)

    return ImageTk.PhotoImage(img)



def _loc_key(location: dict) -> str:
    """build a stable unique string key for a location so we can store it in the favorites set."""
    return f"{location['name']}|{location['address']}"


def _maps_query(location: dict) -> str:
    """build the best possible search string to pass to google maps for a given office location.
    we try in this order: lat and lng coordinates (most precise), full address if it already has a zip, or address plus city state zip."""
    # if we have exact coordinates, use them; they are completely unambiguous
    if location.get("lat") and location.get("lng"):
        return f"{location['lat']},{location['lng']}"
    addr = str(location.get("address", ""))
    zip_code = str(location.get("zip", ""))
    if zip_code and zip_code in addr:
        return addr  # the zip code is already in the address field so it is specific enough
    city = str(location.get("city", ""))
    state = str(location.get("state", ""))
    # join whichever of city, state, and zip are available into a string to append to the address
    extras = ", ".join(p for p in [city, state, zip_code] if p)
    return f"{addr}, {extras}" if extras else addr


def open_location_in_maps(address: str) -> None:
    """open a google maps search for the given address in the user's default web browser."""
    webbrowser.open(f"https://www.google.com/maps/search/?api=1&query={quote_plus(address)}")


def open_directions_in_maps(destination: str, origin: str = "") -> None:
    """open google maps in directions mode going from the user's location to the office.
    if origin is empty, google maps will use the device's current location as the starting point."""
    url = f"https://www.google.com/maps/dir/?api=1&destination={quote_plus(destination)}"
    if origin:
        url += f"&origin={quote_plus(origin)}"
    webbrowser.open(url)


def copy_to_clipboard(widget: tk.Misc, text: str) -> None:
    """copy the given text to the system clipboard using tkinter's built in clipboard api."""
    widget.clipboard_clear()       # clear whatever was on the clipboard before
    widget.clipboard_append(text)  # put our text on the clipboard
    widget.update_idletasks()      # flush pending tkinter events to make sure the clipboard update goes through


def export_session_json(
    path: Path,
    session_id: str,
    selected_programs: list[str],
    user_data: dict[str, object],
    eligibility: dict[str, ProgramResult],
    locations: list[dict[str, object]],
    radius: str,
) -> None:
    """save a complete snapshot of this session to a json file so results can be shared, archived, or handed off."""
    # make sure the exports folder exists; create it if needed
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    # build the dictionary that will be written as json
    payload = {
        # the timestamp when this export was created, formatted as an iso date and time string
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "session_id": session_id,
        "app_version": APP_VERSION,
        "selected_programs": selected_programs,
        # json can only store basic types, so anything else gets converted to a string
        "user_data": {k: (v if isinstance(v, (str, int, float, bool, type(None))) else str(v)) for k, v in user_data.items()},
        # convert each programresult dataclass into a plain dictionary so json can hold it
        "eligibility": {k: {"status": v.status, "explanation": v.explanation, "passed": v.passed, "missed": v.missed} for k, v in eligibility.items()},
        # include only the most important office fields rather than the full location record
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
    # write the dictionary to the file as nicely indented json text
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


class BenefitBridgeApp(tk.Tk):
    """the main application window; this class is the central brain of the entire program.
    _build_shell() creates the parts that stay visible on every step: header, left rail, nav buttons.
    show_step() swaps in the right content for step 0, 1, or 2.
    go_next() and go_back() move the user forward and backward through the wizard.
    the eligibility math functions live in benefit_bridge_core.py and are called from here."""

    def __init__(self) -> None:
        # start the underlying tkinter window
        super().__init__()
        # now that tkinter is running, replace the placeholder font with a nicer installed one
        global FONT_FAMILY
        FONT_FAMILY = preferred_ui_font(self)

        # set the window title, starting size, minimum size, and background color
        self.title("Benefit Bridge")
        self.geometry("1180x820")    # initial window size in pixels
        self.minsize(960, 700)       # prevent the user from shrinking below this size
        self.configure(bg=APP_BG)

        # generate a short id for this session so each run is identifiable in exports
        self.session_id = datetime.now().strftime("%Y%m%d%H%M%S")
        # the monthly income the user originally typed in, saved so the what if slider can calculate percentages
        self._baseline_monthly: float = 0.0
        # references to scheduled timer callbacks so we can cancel them if needed
        self._toast_after: str | None = None   # timer for hiding the floating toast notification
        self._draft_after: str | None = None   # timer for debounced autosave
        # attempt to load the logo image; will be none if no logo file is found
        self.brand_logo_image: tk.PhotoImage | None = self._load_brand_logo()

        # these lists and dicts hold the wizard state as the user works through the steps
        self.selected_programs: list[str] = []   # keys of the programs whose checkboxes are ticked
        self.user_data: dict[str, object] = {}   # the complete household profile collected from step 1
        self.eligibility: dict[str, ProgramResult] = {}   # eligibility results keyed by program name
        self.location_results: list[dict[str, object]] = []  # nearby offices found after running the check
        self._location_view: list[dict[str, object]] = []    # the filtered and sorted version shown in the ui
        # one tkinter booelan variable per program so the checkboxes track their own on off state
        self.program_vars: dict[str, tk.BooleanVar] = {}
        for _key in PROGRAMS:
            self.program_vars[_key] = tk.BooleanVar(value=False)

        # tkinter variables are special objects that automatically stay in sync with the widgets bound to them
        # if you change the variable the widget updates, and if the user changes the widget the variable updates
        self.income_var = tk.StringVar()                         # the income amount the user types in
        self.income_period_var = tk.StringVar(value="Monthly")   # whether the income is monthly or yearly
        self.name_var = tk.StringVar()                           # the applicant's name
        self.household_var = tk.IntVar(value=3)                  # number of people in the household
        self.location_var = tk.StringVar()                       # the zip code or city name entered
        self.state_var = tk.StringVar(value="California")        # the selected state
        self.age_var = tk.StringVar(value="Adult")               # the selected age range
        self.employment_var = tk.StringVar(value=EMPLOYMENT_OPTIONS[0])  # the selected employment status
        self.residency_var = tk.BooleanVar(value=True)           # whether the applicant is a us resident
        self.healthy_var = tk.BooleanVar(value=True)             # whether they are looking for nutritious food
        self.child_under_13_var = tk.BooleanVar(value=True)      # whether there is a child under 13 in the home
        self.child_under_5_var = tk.BooleanVar(value=False)      # whether there is a child under 5 (for wic)
        self.pregnant_var = tk.BooleanVar(value=False)           # whether the applicant is pregnant (for wic)
        self.postpartum_var = tk.BooleanVar(value=False)         # whether the applicant is postpartum (for wic)
        self.breastfeeding_var = tk.BooleanVar(value=False)      # whether the applicant is breastfeeding (for wic)
        self.utility_hardship_var = tk.BooleanVar(value=False)   # whether they are behind on a utility bill
        self.internet_need_var = tk.BooleanVar(value=True)       # whether they need home internet
        self.transportation_need_var = tk.BooleanVar(value=False) # whether they need transportation help
        self.radius_var = tk.StringVar(value="10")               # the office search radius in miles
        self._radius_dbl = tk.DoubleVar(value=10.0)              # the numeric version of the radius for the slider

        # variables used by the filters and controls on the results page
        self.office_search_var = tk.StringVar()                  # text the user types to search offices
        self.office_sort_var = tk.StringVar(value="distance")    # whether to sort offices by distance or name
        self.income_scenario_pct = tk.DoubleVar(value=100.0)     # the what if income slider value (100 = their actual income)
        self.prog_filter_vars: dict[str, tk.BooleanVar] = {k: tk.BooleanVar(value=True) for k in PROGRAMS}
        self.show_favorites_var = tk.BooleanVar(value=False)
        self.favorite_keys: set[str] = self._load_favorites()

        # which step of the wizard is currently showing: 0, 1, or 2
        self.current_step = 0
        # references to the step labels in the left rail so we can update their colors as steps change
        self.step_labels: list[tk.Label] = []

        # configure widget styles, build the persistent chrome, then hook up keyboard shortcuts
        self._configure_styles()
        self._build_shell()
        ScrollableFrame.hook_mousewheel(self)
        self._bind_shortcuts()
        # always start on step 0 (program picker); drafts are only loaded when the user explicitly clicks "load draft"
        self.show_step(0)

    def _configure_styles(self) -> None:
        """apply dark theme colors and fonts to tkinter's built in ttk widgets.
        without this the ttk widgets would just show the operating system's default look."""
        # ttk.Style is the object you use to change how ttk widgets look
        self.style = ttk.Style(self)
        try:
            # the "clam" theme is one of tkinter's built in themes and is easier to customize than others
            self.style.theme_use("clam")
        except tk.TclError:
            pass
        fs = self._font_size(11)  # the base font size, adjusted for any accessibility scale setting
        # apply colors and fonts to each ttk widget type
        self.style.configure("TFrame", background=APP_BG)
        self.style.configure("TLabel", background=APP_BG, foreground=TEXT, font=(FONT_FAMILY, fs))
        self.style.configure("Title.TLabel", font=(FONT_FAMILY, self._font_size(26), "bold"), foreground=TEXT)
        self.style.configure("Subtitle.TLabel", font=(FONT_FAMILY, self._font_size(12)), foreground=MUTED)
        self.style.configure("TCheckbutton", background=CARD_BG, foreground=TEXT, font=(FONT_FAMILY, fs))
        # give checkboxes a subtle background change when the mouse hovers over them
        self.style.map("TCheckbutton", background=[("active", CARD_BG_HOVER)])
        # style the dropdown combobox to match the dark theme
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
        # keep the same field background color whether or not the dropdown is in readonly mode
        self.style.map("TCombobox", fieldbackground=[("readonly", INPUT_BG)])
        # style the horizontal slider track
        self.style.configure("Horizontal.TScale", background=CARD_BG, troughcolor=INPUT_BG)
        # style the built in scrollbar (used as a fallback in some places)
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
        # make the dropdown list inside comboboxes use our preferred font
        self.option_add("*TCombobox*Listbox.font", (FONT_FAMILY, fs))
        # match the background of any dialog popups to our app background
        self.option_add("*Dialog.background", APP_BG)

    def _font_size(self, base: int) -> int:
        """calculate the actual font size to use; clamped between 9 and 22."""
        return int(clamp(base, 9, 22))

    def _button(self, parent: tk.Widget, text: str, command, variant: str = "secondary") -> ModernButton:
        # convenience wrapper: create a modernbutton that automatically inherits the parent's background color
        return ModernButton(parent, text, command, variant, widget_background(parent))

    def _load_brand_logo(self) -> tk.PhotoImage | None:
        """load the logo image file and shrink it to fit in the header; returns none if no logo file is found."""
        logo_path = resolve_brand_logo_path()
        if not logo_path:
            return None
        max_h = 70  # the logo should appear at most 70 points tall in the header
        # if pillow is installed use it for a high quality smooth resize
        if Image is not None and ImageTk is not None:
            try:
                pil_img = Image.open(str(logo_path))
                # calculate the device pixel ratio so the logo looks sharp on high dpi retina displays
                # winfo_fpixels("1i") returns about 144 on a 2x retina screen and 72 on a standard screen
                try:
                    dpr = max(1.0, self.winfo_fpixels('1i') / 72.0)
                except Exception:
                    dpr = 1.0
                target_h = round(max_h * dpr)
                new_w = max(1, round(pil_img.width * target_h / pil_img.height))
                pil_img = pil_img.resize((new_w, target_h), Image.LANCZOS)
                return ImageTk.PhotoImage(pil_img)
            except Exception:
                return None
        # fallback path used when pillow is not installed: use tkinter's built in image loading
        try:
            image = tk.PhotoImage(file=str(logo_path))
        except tk.TclError:
            return None
        if image.height() > max_h:
            ratio = max(1, math.ceil(image.height() / max_h))
            # keep a reference to the original image so the subsampled version is not garbage collected
            self._brand_logo_original = image
            image = image.subsample(ratio, ratio)
        return image

    def _surface(self, parent: tk.Widget) -> tk.Widget:
        """if the parent is a roundedcard, return its inner body frame where children should be placed.
        otherwise just return the parent widget itself unchanged."""
        return parent.body if isinstance(parent, RoundedCard) else parent

    def _card(self, parent: tk.Widget) -> RoundedCard:
        # convenience wrapper: create a new roundedcard that inherits the parent's background color
        return RoundedCard(parent, widget_background(parent))

    def _clear(self, parent: tk.Widget) -> None:
        # destroy all child widgets inside the given parent widget so the space is empty
        for child in parent.winfo_children():
            child.destroy()

    def _focus_ring(self, widget: tk.Widget) -> None:
        """make the border of a widget glow in the accent color when it has keyboard focus."""
        # focusin fires when the user tabs into or clicks the widget
        widget.bind("<FocusIn>", lambda _event: widget.configure(highlightbackground=BORDER_FOCUS))
        # focusout fires when focus moves to a different widget
        widget.bind("<FocusOut>", lambda _event: widget.configure(highlightbackground=BORDER))

    def _build_shell(self) -> None:
        """build all the persistent chrome that stays visible across all three steps:
        the header bar at the top, the progress rail on the left, the nav buttons at the bottom, and the footer."""

        # header bar across the top of the window with a fixed height
        header = tk.Frame(self, bg=HEADER_BG, height=104, highlightbackground=BORDER, highlightthickness=1)
        header.pack(fill="x")
        # pack_propagate(false) makes the frame keep its exact set height even if its children are smaller
        header.pack_propagate(False)

        # the left side of the header holds the logo, the app name, and the tagline
        left_brand = tk.Frame(header, bg=HEADER_BG)
        left_brand.pack(side="left", anchor="w", padx=28, pady=(14, 0))

        # only show the logo label if we successfully loaded a logo image
        if self.brand_logo_image is not None:
            logo_label = tk.Label(left_brand, image=self.brand_logo_image, bg=HEADER_BG)
            logo_label.pack(side="left", padx=(0, 14))

        # a small vertical group for stacking the app name above the tagline
        title_group = tk.Frame(left_brand, bg=HEADER_BG)
        title_group.pack(side="left", anchor="w")

        # the large app name label
        tk.Label(
            title_group,
            text="Benefit Bridge",
            bg=HEADER_BG,
            fg=TEXT,
            font=(FONT_FAMILY, self._font_size(26), "bold"),
        ).pack(anchor="w")
        # the tagline shown below the app name
        tk.Label(
            title_group,
            text=BRAND_SLOGAN,
            bg=HEADER_BG,
            fg=ACCENT_GLOW,
            font=(FONT_FAMILY, self._font_size(13), "bold"),
        ).pack(anchor="w", pady=(4, 0))

        # the right side of the header holds the utility buttons
        right_header = tk.Frame(header, bg=HEADER_BG)
        right_header.pack(side="right", padx=20, pady=(18, 0))

        # a row of small utility buttons along the top right
        tools = tk.Frame(right_header, bg=HEADER_BG)
        tools.pack(side="right", padx=(0, 8))
        self._button(tools, "Export JSON", self.action_export_json, "secondary").pack(side="left", padx=3)
        self._button(tools, "About", self.action_about, "ghost").pack(side="left", padx=3)

        # the body frame fills everything below the header
        body = tk.Frame(self, bg=APP_BG)
        body.pack(fill="both", expand=True)

        # the left progress rail is a fixed width sidebar showing which step the user is on
        self.rail = tk.Frame(body, bg=RAIL_BG, width=260, highlightbackground=BORDER, highlightthickness=1)
        self.rail.pack(side="left", fill="y")
        self.rail.pack_propagate(False)

        # these are the three step names shown inside the rail
        steps = [("1", "Choose subsidies"), ("2", "Household profile"), ("3", "Results & offices")]
        # the "progress" heading at the top of the rail
        tk.Label(self.rail, text="Progress", bg=RAIL_BG, fg=MUTED, font=(FONT_FAMILY, self._font_size(11), "bold")).pack(anchor="w", padx=22, pady=(26, 8))
        # create one label per step and save them in step_labels so we can change their color later
        for number, label in steps:
            item = tk.Label(self.rail, text=f"{number}. {label}", bg=RAIL_BG, fg=MUTED, font=(FONT_FAMILY, self._font_size(12)), padx=12, pady=11, anchor="w")
            item.pack(fill="x", padx=14, pady=3)
            self.step_labels.append(item)

        # the main content area fills everything to the right of the rail
        main = tk.Frame(body, bg=APP_BG)
        main.pack(side="left", fill="both", expand=True)

        # we pack the nav buttons first and push them to the bottom
        # this ensures they are never pushed off screen even when the step content is very tall
        self.nav = tk.Frame(main, bg=APP_BG)
        self.nav.pack(side="bottom", fill="x", padx=26, pady=(0, 10))
        # the content area fills the remaining space above the nav buttons
        self.content = tk.Frame(main, bg=APP_BG)
        self.content.pack(fill="both", expand=True, padx=26, pady=(20, 12))

        # navigation buttons: back on the left, next on the right, start over and drafts in the middle
        self.back_button = self._button(self.nav, "Back", self.go_back, "secondary")
        self.back_button.pack(side="left")
        self._nav_startover_btn = self._button(self.nav, "Start over", self.start_over, "ghost")
        self._nav_startover_btn.pack(side="left", padx=10)
        self._nav_savedraft_btn = self._button(self.nav, "Save draft", self.action_save_draft_now, "ghost")
        self._nav_savedraft_btn.pack(side="left", padx=4)
        self._nav_loaddraft_btn = self._button(self.nav, "Load draft", self.action_load_draft_now, "ghost")
        self._nav_loaddraft_btn.pack(side="left", padx=4)
        self.next_button = self._button(self.nav, "Next", self.go_next, "primary")
        self.next_button.pack(side="right")

        # the footer is a thin status bar along the very bottom of the window
        footer = tk.Frame(self, bg=APP_BG_ELEVATED, height=32, highlightbackground=BORDER, highlightthickness=1)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)
        # the left side of the footer shows status messages that update as actions happen
        self.footer_left = tk.Label(
            footer,
            text="Ready",
            bg=APP_BG_ELEVATED,
            fg=MUTED,
            font=(FONT_FAMILY, self._font_size(10)),
            anchor="w",
        )
        self.footer_left.pack(side="left", padx=16, pady=6, fill="x", expand=True)
    def _rail_resize_hint(self, _event: tk.Event) -> None:
        pass

    def _status(self, message: str) -> None:
        # update the message text shown on the left side of the footer bar
        self.footer_left.configure(text=message)

    def _toast(self, message: str, ms: int = 2800) -> None:
        """show a temporary floating notification (a toast) that disappears after the given number of milliseconds.
        we use this instead of a blocking messagebox so the user can keep working."""
        # if a previous toast is still scheduled to close, cancel it before creating a new one
        if self._toast_after:
            try:
                self.after_cancel(self._toast_after)
            except tk.TclError:
                pass
        # create a new separate window for the toast notification
        top = tk.Toplevel(self)
        # hide the os title bar and borders so it looks like a floating popup rather than a window
        top.overrideredirect(True)
        # keep the toast on top of all other windows so it is always visible
        top.attributes("-topmost", True)
        top.configure(bg=CARD_BG)
        # outer frame with an accent colored highlight border
        frm = tk.Frame(top, bg=CARD_BG, highlightbackground=ACCENT, highlightthickness=1, padx=18, pady=12)
        frm.pack()
        # the actual notification message text
        tk.Label(frm, text=message, bg=CARD_BG, fg=TEXT, font=(FONT_FAMILY, self._font_size(11))).pack()
        # position the toast near the top center of the main window
        x = self.winfo_rootx() + self.winfo_width() // 2 - 160
        y = self.winfo_rooty() + 72
        top.geometry(f"320x64+{max(0, x)}+{max(0, y)}")
        # schedule the toast window to destroy itself after the specified number of milliseconds
        self._toast_after = self.after(ms, top.destroy)

    def _bind_shortcuts(self) -> None:
        """register keyboard shortcuts that work no matter which widget currently has focus."""
        # binding on self (the root window) means these fire from anywhere in the app
        self.bind("<Control-e>", lambda _e: self.action_export_json())          # ctrl+e exports results as json
        self.bind("<Control-s>", lambda _e: self.action_save_draft_now())       # ctrl+s saves the current draft
        self.bind("<Control-q>", lambda _e: (self._write_draft(), self.destroy())) # ctrl+q saves draft then quits

    def _schedule_draft_autosave(self) -> None:
        """schedule an autosave to happen about 1.8 seconds from now.
        if this is called again before the timer fires, the old timer is cancelled and a new one starts.
        this is called debouncing: while the user is typing we do not save constantly; we save once they pause."""
        # cancel any autosave that is already pending
        if self._draft_after:
            try:
                self.after_cancel(self._draft_after)
            except tk.TclError:
                pass
        # schedule the actual save to happen 1800 milliseconds (1.8 seconds) from now
        self._draft_after = self.after(1800, self._write_draft)

    def _write_draft(self) -> None:
        """save a snapshot of the current wizard state to the draft json file on disk."""
        # clear the timer reference now that the save is actually running
        self._draft_after = None
        try:
            # build the snapshot dictionary using only simple json compatible types
            payload = {
                "saved_at": datetime.now().isoformat(timespec="seconds"),
                "step": self.current_step,
                # read the current value out of each tkinter variable
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
                "healthy": self.healthy_var.get(),
                "child_under_13": self.child_under_13_var.get(),
                "child_under_5": self.child_under_5_var.get(),
                "utility_hardship": self.utility_hardship_var.get(),
                "internet_need": self.internet_need_var.get(),
                "transportation_need": self.transportation_need_var.get(),
            }
            # write the snapshot to the draft file as formatted json
            DRAFT_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except OSError:
            pass

    def _load_draft_if_present(self) -> bool:
        """read the saved draft from disk and refill the form with it.

        returns true if it loaded something, false if there is no draft
        or it was unreadable. the popup is split from the load logic so
        the caller can decide whether to show feedback.
        """
        if not DRAFT_FILE.exists():
            return False
        try:
            data = json.loads(DRAFT_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            # draft file exists but is broken so give up
            return False
        # refill each program checkbox from the saved values
        for k, v in data.get("programs", {}).items():
            if k in self.program_vars:
                self.program_vars[k].set(bool(v))
        # refill all the form fields. .get(key, default) means: use
        # the default if the key is not in the saved data
        self.name_var.set(str(data.get("name", "")))
        self.income_var.set(str(data.get("income", "")))
        self.income_period_var.set(str(data.get("income_period", "Monthly")))
        self.household_var.set(int(data.get("household", 3)))
        self.location_var.set(str(data.get("location", "")))
        self.state_var.set(str(data.get("state", "California")))
        self.age_var.set(str(data.get("age", "Adult")))
        self.employment_var.set(str(data.get("employment", EMPLOYMENT_OPTIONS[0])))
        self.residency_var.set(bool(data.get("resident", True)))
        self.healthy_var.set(bool(data.get("healthy", True)))
        self.child_under_13_var.set(bool(data.get("child_under_13", True)))
        self.child_under_5_var.set(bool(data.get("child_under_5", False)))
        self.utility_hardship_var.set(bool(data.get("utility_hardship", False)))
        self.internet_need_var.set(bool(data.get("internet_need", True)))
        self.transportation_need_var.set(bool(data.get("transportation_need", False)))
        # update the runtime list of selected programs based on what is checked
        self.selected_programs = [k for k, v in self.program_vars.items() if v.get()]
        # figure out which step to jump to (clamped to a valid value 0 to 2)
        step = int(data.get("step", 0))
        step = clamp(step, 0, 2)
        # if the saved step was the results step, we need to recompute the results
        if step == 2:
            if not self.selected_programs:
                # no programs picked so drop back to step 0
                step = 0
            elif self.collect_user_data():
                # profile is valid so recompute eligibility and locations
                self._baseline_monthly = float(self.user_data["monthly_income"])
                self.income_scenario_pct.set(100.0)
                self.eligibility = compute_eligibility(self.selected_programs, self.user_data)
                self.refresh_location_data()
            else:
                # profile was incomplete so drop back to step 1
                step = 1
        self._status("Draft restored")
        self.show_step(step)
        return True

    def action_save_draft_now(self) -> None:
        # triggered by ctrl+s or the save draft button
        self._write_draft()
        self._toast("Draft saved to disk")

    def action_load_draft_now(self) -> None:
        """handler for the load draft button."""
        # give clear feedback in every case so the button never feels broken
        if not DRAFT_FILE.exists():
            self._toast("No draft found yet")
            return
        if self._load_draft_if_present():
            self._toast("Draft loaded")
        else:
            self._toast("Draft could not be loaded")

    def action_export_json(self) -> None:
        # triggered by ctrl+e or the export json button in the header
        # we need eligibility results before we can export anything meaningful
        if not self.eligibility:
            messagebox.showinfo("Export JSON", "Run eligibility first (complete step 3).")
            return
        # build the export file name using the session id so each export is unique
        path = EXPORT_DIR / f"benefit_bridge_export_{self.session_id}.json"
        # pass everything to the standalone export function which handles writing the file
        export_session_json(path, self.session_id, self.selected_programs, self.user_data, self.eligibility, self.location_results, self.radius_var.get())
        self._status(f"Exported JSON → {path.name}")
        self._toast("Session exported as JSON")

    def action_about(self) -> None:
        # show a simple info popup with the app version, tagline, and current session id
        messagebox.showinfo(
            "About Benefit Bridge",
            f"Benefit Bridge {APP_VERSION}\n\n"
            f"{BRAND_SLOGAN}\n\n"
            "Demo eligibility estimator and office finder.\n"
            "Replace sample rules and locations before real-world use.\n\n"
            f"Session ID: {self.session_id}",
        )

    def _text_wrap(self) -> int:
        """calculate how wide in pixels a paragraph of text should wrap based on the current window size.
        we recalculate this each call so it adapts automatically when the window is resized."""
        # flush any pending layout work so winfo_width returns the current real size
        self.update_idletasks()
        try:
            # use the step host frame width if available; fall back to the content area width
            ref = getattr(self, "_step_host", self.content)
            # clamp to a reasonable range so text is never absurdly narrow or wide
            return max(280, min(860, int(ref.winfo_width()) - 56))
        except tk.TclError:
            return 560  # safe fallback when tkinter is not fully ready yet

    def _pane_text_wrap(self) -> int:
        """same idea as _text_wrap but sized for the two column results page where each pane is about half the window."""
        self.update_idletasks()
        try:
            # each pane is roughly half the window width minus padding
            return max(300, min(720, int(self.winfo_width()) // 2 - 120))
        except tk.TclError:
            return 420

    def show_step(self, step: int) -> None:
        """switch the wizard to the given step number (0, 1, or 2) and rebuild the content area."""
        self.current_step = step
        # clear whatever content was in the content area from the previous step
        self._clear(self.content)
        # wrap the new step content in a scrollable frame so even very long pages still fit
        # the nav buttons at the bottom are pinned outside this scroll area so they always stay visible
        step_scroll = ScrollableFrame(self.content, APP_BG)
        step_scroll.pack(fill="both", expand=True)
        # _step_host is the inner frame where each step's build method places its widgets
        self._step_host = step_scroll.inner
        # recolor the step labels in the left rail to reflect the new current step
        self._update_step_rail()
        # build the content for the new step and update the next button label to match
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
        # schedule an autosave shortly after the step loads
        self._schedule_draft_autosave()
        # update the footer to show which step the user is on
        self._status(f"Step {step + 1} of 3")

    def _update_step_rail(self) -> None:
        """recolor the three step labels in the left rail to show the user's progress.
        the current step is highlighted in accent color, completed steps are green, and future steps are muted gray."""
        for index, label in enumerate(self.step_labels):
            if index == self.current_step:
                # this is the step the user is currently on
                label.configure(bg=CARD_BG, fg=ACCENT, font=(FONT_FAMILY, self._font_size(12), "bold"))
            elif index < self.current_step:
                # this step is already completed
                label.configure(bg=RAIL_BG, fg=SUCCESS, font=(FONT_FAMILY, self._font_size(12), "bold"))
            else:
                # this step has not been reached yet
                label.configure(bg=RAIL_BG, fg=MUTED, font=(FONT_FAMILY, self._font_size(12)))

    def _build_program_screen(self) -> None:
        """build step 0 (the first screen): the program picker where the user chooses which benefits to check."""
        # large welcome heading at the top
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

        # three small feature highlight cards that scroll horizontally if the window is narrow
        chips_container = HorizontalScrollableFrame(self._step_host, APP_BG)
        chips_container.pack(fill="x", pady=(0, 22))
        chips = chips_container.inner
        # each chip is about a third of the available width
        chip_wrap = max(200, min(280, self._text_wrap() // 3))
        # build one small card for each feature bullet point
        for label, sub in (
            ("Smart reuse", "One questionnaire powers every program you pick."),
            ("Office radar", "Distance-ranked sites — hundreds of demo ZIP codes statewide."),
            ("Audit trail", "CSV history + JSON export for handoff."),
        ):
            c = self._card(chips)
            c.pack(side="left", fill="both", expand=False, padx=(0, 14))
            cb = self._surface(c)  # get the inner body frame of the rounded card
            # bold title label at the top of the chip
            tk.Label(cb, text=label, bg=CARD_BG, fg=TEXT, font=(FONT_FAMILY, self._font_size(13), "bold")).pack(anchor="w", padx=18, pady=(16, 6))
            # description text below the title
            tk.Label(cb, text=sub, bg=CARD_BG, fg=MUTED, font=(FONT_FAMILY, self._font_size(11)), wraplength=chip_wrap, justify="left").pack(anchor="w", padx=18, pady=(0, 18))

        # the main card where the user picks which programs to check
        card = self._card(self._step_host)
        card.pack(fill="x", expand=False)
        card_body = self._surface(card)

        # heading inside the card
        tk.Label(card_body, text="Which type of subsidy?", bg=CARD_BG, fg=TEXT, font=(FONT_FAMILY, self._font_size(20), "bold")).pack(anchor="w", padx=24, pady=(24, 8))
        # subtitle instruction text
        tk.Label(
            card_body,
            text="Choose one or more programs. Use Select all if you want a full scan.",
            bg=CARD_BG,
            fg=MUTED,
            font=(FONT_FAMILY, self._font_size(11)),
            wraplength=self._text_wrap() - 48,
            justify="left",
        ).pack(anchor="w", padx=24, pady=(0, 18))

        # the wrap width for each program description line
        row_wrap = max(320, self._text_wrap() - 72)
        # build one program row block for each program in the programs dictionary
        for key, program in PROGRAMS.items():
            # outer bordered block for this program row
            block = tk.Frame(card_body, bg=CARD_BG_HOVER, highlightbackground=BORDER, highlightthickness=1)
            block.pack(fill="x", padx=18, pady=12)
            # inner padded frame inside the border
            inner = tk.Frame(block, bg=CARD_BG_HOVER)
            inner.pack(fill="x", padx=16, pady=16)
            # top row with a color swatch, the checkbox, and the program name label
            head = tk.Frame(inner, bg=CARD_BG_HOVER)
            head.pack(fill="x", anchor="w")
            # a narrow vertical color bar in the program's accent color
            swatch = tk.Frame(head, bg=program["color"], width=8, height=36)
            swatch.pack(side="left", fill="y", padx=(0, 14))
            swatch.pack_propagate(False)
            # the checkbox tied to the tkinter variable for this program
            ModernCheckbox(head, text=program["name"], variable=self.program_vars[key], bg=CARD_BG_HOVER, fg=TEXT).pack(side="left", anchor="nw", pady=(2, 0))
            # the program description text shown below the checkbox row
            tk.Label(
                inner,
                text=program["description"],
                bg=CARD_BG_HOVER,
                fg=SUBTEXT,
                font=(FONT_FAMILY, self._font_size(11)),
                wraplength=row_wrap,
                justify="left",
            ).pack(anchor="w", padx=(22, 8), pady=(12, 0))

        # action buttons at the bottom of the program picker card
        actions = tk.Frame(card_body, bg=CARD_BG)
        actions.pack(fill="x", padx=22, pady=(22, 26))
        self._button(actions, "Select all", self.select_all_programs, "secondary").pack(side="left")
        self._button(actions, "Clear", self.clear_programs, "ghost").pack(side="left", padx=10)
        self._button(actions, "Suggest common bundle", self.suggest_program_bundle, "accent").pack(side="right")

        # the quick eligibility estimator card showing income limits for a family of 4
        est_card = self._card(self._step_host)
        est_card.pack(fill="x", pady=(18, 0))
        eb = self._surface(est_card)
        state = self.state_var.get()
        # look up the selected state's income limits (fall back to california if the state is not in the table)
        state_lims = STATE_LIMITS.get(state, STATE_LIMITS["California"])
        snap_mult = SNAP_STATE_MULTIPLIERS.get(state, 2.0)
        tk.Label(eb, text="Quick eligibility snapshot", bg=CARD_BG, fg=TEXT, font=(FONT_FAMILY, self._font_size(15), "bold")).pack(anchor="w", padx=22, pady=(20, 4))
        tk.Label(eb, text="Typical income limits, family of 4" + f" · {state}", bg=CARD_BG, fg=MUTED, font=(FONT_FAMILY, self._font_size(11)), wraplength=self._text_wrap() - 48, justify="left").pack(anchor="w", padx=22, pady=(0, 14))
        # the income limit rows for each program for a family of 4
        est_rows = [
            ("childcare",       state_lims.get("childcare", {}).get(4, 0)),
            ("food",            snap_mult * FPL_100_LIMITS[4]),
            ("utility",         state_lims.get("utility", {}).get(4, 0)),
            ("internet",        FPL_200_LIMITS[4]),
            ("transportation",  state_lims.get("transportation", {}).get(4, 0)),
        ]
        # draw one row per program with a color dot, a name, and the monthly income limit
        for prog_key, limit in est_rows:
            prog = PROGRAMS[prog_key]
            row = tk.Frame(eb, bg=CARD_BG)
            row.pack(fill="x", padx=22, pady=3)
            swatch = tk.Frame(row, bg=prog["color"], width=10, height=18)
            swatch.pack(side="left", padx=(0, 10))
            swatch.pack_propagate(False)
            tk.Label(row, text=prog["short_name"], bg=CARD_BG, fg=TEXT, font=(FONT_FAMILY, self._font_size(11)), width=14, anchor="w").pack(side="left")
            tk.Label(row, text=f"under ${limit:,.0f} / mo", bg=CARD_BG, fg=MUTED, font=(FONT_FAMILY, self._font_size(11))).pack(side="left")
        tk.Frame(eb, height=14, bg=CARD_BG).pack()

    def _build_info_screen(self) -> None:
        """build step 1: the household profile form where the user enters their information."""
        # large heading at the top of the form
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

        # the form uses a two column layout: basic info on the left, program specific questions on the right
        wrapper = tk.Frame(self._step_host, bg=APP_BG)
        wrapper.pack(fill="both", expand=True)
        left = self._card(wrapper)
        right = self._card(wrapper)
        left.pack(side="left", fill="both", expand=True, padx=(0, 12))
        right.pack(side="left", fill="both", expand=True, padx=(12, 0))

        # left column: basic personal information fields
        self._section_title(left, "Basic personal info")
        # each _field_row builds a labeled input field; the lambda creates the widget inside the row
        self._field_row(left, "Name", lambda row: self._entry(row, self.name_var), "Enter the applicant's full name.")
        self._field_row(left, "Income", lambda row: self._income_field(row), "Enter monthly income, or yearly income and choose Yearly.")
        self._field_row(left, "Household size", lambda row: self._spinbox(row, self.household_var, 1, 12), "Everyone who shares income and expenses.")
        self._field_row(left, "State", lambda row: self._combo(row, self.state_var, STATE_OPTIONS), "Choose the state for your location.")
        self._field_row(left, "ZIP code", lambda row: self._entry(row, self.location_var), "Used to find nearby offices.")
        self._field_row(left, "Age range", lambda row: self._combo(row, self.age_var, AGE_OPTIONS), "")
        # the employment field is placed at the top of the right column to continue the form flow
        self._field_row(right, "Employment or school status", lambda row: self._combo(row, self.employment_var, EMPLOYMENT_OPTIONS), "")

        # right column: yes or no questions specific to each program being checked
        self._section_title(right, "Program-specific details")
        self._check_row(right, "US resident or qualified non-citizen", self.residency_var, "Used by food, utility, and internet sample checks.")
        self._check_row(right, "Are you specifically looking for food with high nutritional value?", self.healthy_var, "It is highly recommended that you select this.")
        self._check_row(right, "A child in the household is under age 13", self.child_under_13_var, "Used by the child-care subsidy check.")
        self._check_row(right, "A child in the household is under age 5 (WIC)", self.child_under_5_var, "Used by the WIC food assistance check.")
        self._check_row(right, "Pregnant (WIC)", self.pregnant_var, "Used by the WIC food assistance check.")
        self._check_row(right, "Postpartum (within past 6 months, WIC)", self.postpartum_var, "Used by the WIC food assistance check.")
        self._check_row(right, "Breastfeeding (WIC)", self.breastfeeding_var, "Used by the WIC food assistance check.")
        self._check_row(right, "Behind on utility bill or received a shutoff notice", self.utility_hardship_var, "Used by utility bill help.")
        self._check_row(right, "Need home internet for work, school, health, or benefits", self.internet_need_var, "Used by internet subsidy.")
        self._check_row(right, "Need transportation for work, school, or medical appointments", self.transportation_need_var, "Used by transportation vouchers.")

        # a summary card at the bottom showing which programs the user has selected
        # join the short names with commas for a compact readable list
        selected_names = ", ".join(PROGRAMS[key]["short_name"] for key in self.selected_programs)
        summary = self._card(self._step_host)
        summary.pack(fill="x", pady=(18, 0))
        summary_body = self._surface(summary)
        tk.Label(summary_body, text="Selected programs", bg=CARD_BG, fg=MUTED, font=(FONT_FAMILY, self._font_size(10), "bold")).pack(anchor="w", padx=18, pady=(14, 2))
        tk.Label(
            summary_body,
            # if no programs are selected yet show "none yet" instead of an empty string
            text=selected_names or "None yet",
            bg=CARD_BG,
            fg=TEXT,
            font=(FONT_FAMILY, self._font_size(12)),
            wraplength=self._text_wrap() - 36,
            justify="left",
        ).pack(anchor="w", padx=18, pady=(0, 14))

    def _build_results_screen(self) -> None:
        """build step 2: the results workspace showing eligibility scores, office locations, and controls."""
        # large heading at the top
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

        # count how many programs landed in each eligibility status bucket
        # sum(1 for ...) is a compact way to count items that match a condition
        highly = sum(1 for k in self.selected_programs if self.eligibility[k].status == "Highly eligible")
        partial = sum(1 for k in self.selected_programs if self.eligibility[k].status == "Partially eligible")
        unlikely = sum(1 for k in self.selected_programs if self.eligibility[k].status == "Unlikely")

        # the digest card shows three big colored numbers summarizing the results
        digest = self._card(self._step_host)
        digest.pack(fill="x", pady=(0, 18))
        dg = self._surface(digest)
        rowd = tk.Frame(dg, bg=CARD_BG)
        rowd.pack(fill="x", padx=22, pady=(22, 22))
        # build one big number cell for each status category
        for title, value, color in (
            ("Highly eligible", str(highly), SUCCESS),
            ("Partially eligible", str(partial), WARNING),
            ("Unlikely", str(unlikely), MUTED),
        ):
            cell = tk.Frame(rowd, bg=CARD_BG)
            cell.pack(side="left", padx=(0, 44))
            # the large number in the status color
            tk.Label(cell, text=value, bg=CARD_BG, fg=color, font=(FONT_FAMILY, self._font_size(26), "bold")).pack(anchor="w", pady=(0, 6))
            # smaller descriptive label below the number
            tk.Label(cell, text=title, bg=CARD_BG, fg=MUTED, font=(FONT_FAMILY, self._font_size(11)), wraplength=140, justify="left").pack(anchor="w")

        # the controls card holds the location, radius slider, action buttons, what if slider, and office search
        controls = self._card(self._step_host)
        controls.pack(fill="x", pady=(0, 18))
        controls_body = self._surface(controls)

        # top row: show the user's location
        top = tk.Frame(controls_body, bg=CARD_BG)
        top.pack(fill="x", padx=22, pady=(20, 14))
        loc_lbl = tk.Label(
            top,
            # if no location was set, show "not provided" as a friendly fallback
            text=f"Location: {self.user_data.get('location_input', 'Not provided')}",
            bg=CARD_BG,
            fg=TEXT,
            font=(FONT_FAMILY, self._font_size(13), "bold"),
            wraplength=self._text_wrap() - 80,
            justify="left",
        )
        loc_lbl.pack(anchor="w", fill="x")

        # second row: the radius slider and action buttons
        row_btns = tk.Frame(controls_body, bg=CARD_BG)
        row_btns.pack(fill="x", padx=22, pady=(0, 16))
        # the radius slider grouped with its label and value display
        rad_frame = tk.Frame(row_btns, bg=CARD_BG)
        rad_frame.pack(side="left")
        tk.Label(rad_frame, text="Search radius", bg=CARD_BG, fg=MUTED, font=(FONT_FAMILY, self._font_size(11))).pack(side="left", padx=(0, 8))
        self._radius_lbl = tk.Label(rad_frame, text="10 mi", bg=CARD_BG, fg=ACCENT, font=(FONT_FAMILY, self._font_size(11), "bold"), width=6)
        self._radius_lbl.pack(side="left", padx=(0, 8))
        rad_slider = ttk.Scale(rad_frame, from_=5, to=100, variable=self._radius_dbl, orient="horizontal", length=160)
        rad_slider.pack(side="left", padx=(0, 16))

        def _rad_motion(_event=None):
            # update the radius label live as the slider moves
            v = round(self._radius_dbl.get())
            self._radius_lbl.configure(text=f"{v} mi")

        def _rad_release(_event=None):
            # when the user lets go of the slider, lock in the value and refresh the office list
            v = round(self._radius_dbl.get())
            self._radius_lbl.configure(text=f"{v} mi")
            self.radius_var.set(str(v))
            self.refresh_locations()

        rad_slider.bind("<Motion>", _rad_motion)
        rad_slider.bind("<ButtonRelease-1>", _rad_release)
        # the other action buttons that go in the same row as the radius slider
        self._button(row_btns, "Save CSV history", self.save_case_history, "ghost").pack(side="left", padx=6)
        self._button(row_btns, "Copy summary", self.copy_results_summary, "ghost").pack(side="left", padx=6)
        self._button(row_btns, "Print list", self.print_office_list, "ghost").pack(side="left", padx=6)
        self._button(row_btns, "Edit profile", lambda: self.show_step(1), "ghost").pack(side="right", padx=6)

        # third row: the what if income slider lets the user ask "what if my income were higher or lower"
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
        # the slider and its current percent value label side by side
        sc_row = tk.Frame(mid, bg=CARD_BG)
        sc_row.pack(fill="x", pady=(4, 0))
        # slider ranges from 50% to 150% of the user's actual income
        scale = ttk.Scale(sc_row, from_=50, to=150, variable=self.income_scenario_pct, orient="horizontal")
        scale.pack(side="left", fill="x", expand=True, padx=(0, 12))
        # label showing the current slider value as a percentage
        self._scenario_value_lbl = tk.Label(
            sc_row,
            text="100%",
            bg=CARD_BG,
            fg=ACCENT,
            font=(FONT_FAMILY, self._font_size(12), "bold"),
            width=7,
        )
        self._scenario_value_lbl.pack(side="right")

        def _slide(_event: tk.Event | None = None) -> None:
            # update the percentage label live as the slider moves
            self._scenario_value_lbl.configure(text=f"{self.income_scenario_pct.get():.0f}%")

        # update the label continuously while dragging
        scale.bind("<Motion>", _slide)
        # only recalculate eligibility when the user releases the slider to avoid slowness during dragging
        scale.bind("<ButtonRelease-1>", lambda _e: self.apply_income_scenario())
        # show the starting label right away
        _slide()

        # a label that shows what changed when the user adjusts the what if slider
        self._scenario_change_lbl = tk.Label(
            mid,
            text="",
            bg=CARD_BG,
            fg=ACCENT,
            font=(FONT_FAMILY, self._font_size(11)),
            wraplength=self._text_wrap() - 48,
            justify="left",
        )
        self._scenario_change_lbl.pack(anchor="w", pady=(8, 0))

        # bottom row of the controls card: the office search box, sort dropdown, and filter checkboxes
        bot = tk.Frame(controls_body, bg=CARD_BG)
        bot.pack(fill="x", padx=22, pady=(4, 22))
        tk.Label(bot, text="Office list", bg=CARD_BG, fg=TEXT, font=(FONT_FAMILY, self._font_size(12), "bold")).pack(anchor="w", pady=(0, 10))
        row_f = tk.Frame(bot, bg=CARD_BG)
        row_f.pack(fill="x", pady=(0, 8))
        # the search box for typing part of an office name, city, or street
        tk.Label(row_f, text="Search", bg=CARD_BG, fg=MUTED, font=(FONT_FAMILY, self._font_size(11))).pack(side="left")
        se = tk.Entry(
            row_f,
            textvariable=self.office_search_var,
            bg=INPUT_BG,
            fg=TEXT,
            insertbackground=TEXT,         # the cursor color inside the text field
            relief="flat",
            bd=0,
            width=32,
            font=(FONT_FAMILY, self._font_size(11)),
            highlightthickness=2,
            highlightbackground=BORDER,
            highlightcolor=BORDER_FOCUS,   # the highlight border color when the field is focused
        )
        self._focus_ring(se)               # make the border glow accent color when focused
        se.pack(side="left", padx=(10, 20), ipady=8)
        # the dropdown to sort offices by distance or by name
        tk.Label(row_f, text="Sort by", bg=CARD_BG, fg=MUTED, font=(FONT_FAMILY, self._font_size(11))).pack(side="left")
        ttk.Combobox(row_f, values=("distance", "name"), width=11, state="readonly", textvariable=self.office_sort_var).pack(side="left", padx=(10, 14))
        self._button(row_f, "Apply filter", self._office_filter_changed, "secondary").pack(side="left", padx=6)
        self._button(row_f, "Copy all addresses", self.copy_all_office_addresses, "ghost").pack(side="right", padx=6)

        # a row of per program filter checkboxes and the favorites only toggle
        prog_row = tk.Frame(bot, bg=CARD_BG)
        prog_row.pack(fill="x", pady=(0, 4))
        tk.Label(prog_row, text="Show:", bg=CARD_BG, fg=MUTED, font=(FONT_FAMILY, self._font_size(11))).pack(side="left", padx=(0, 8))
        for prog_key, prog in PROGRAMS.items():
            cb = ttk.Checkbutton(
                prog_row,
                text=prog["short_name"],
                variable=self.prog_filter_vars[prog_key],
                command=self._office_filter_changed,
            )
            cb.pack(side="left", padx=(0, 10))
        ttk.Separator(prog_row, orient="vertical").pack(side="left", fill="y", padx=10)
        ttk.Checkbutton(
            prog_row,
            text="Favorites only ★",
            variable=self.show_favorites_var,
            command=self._office_filter_changed,
        ).pack(side="left")

        # the document checklist card showing what documents to bring when visiting an office
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
        # build the checklist: universal items first, then program specific items with the program name in brackets
        lines: list[str] = []
        lines.extend(f"• {item}" for item in MASTER_DOCUMENT_LIST)
        for pk in self.selected_programs:
            for line in PROGRAM_CHECKLISTS.get(pk, []):
                lines.append(f"• [{PROGRAMS[pk]['short_name']}] {line}")
        # the "well" is a slightly inset frame that gives the text area a border effect
        well = tk.Frame(db, bg=BORDER, bd=0, highlightthickness=0)
        well.pack(fill="x", padx=22, pady=(0, 22))
        # a multiline read only text area showing the checklist items
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
        # insert all the checklist lines starting at position 1.0 (line 1, character 0)
        chk.insert("1.0", "\n".join(lines))
        # disable editing so the user cannot type in this area, but they can still select and copy text
        chk.configure(state="disabled")
        chk.pack(fill="x", padx=3, pady=3)

        # a split pane dividing the screen between eligibility cards on the left and nearby offices on the right
        # the user can drag the divider to resize the two columns
        pane = tk.PanedWindow(self._step_host, orient="horizontal", bg=APP_BG, sashwidth=10, bd=0, sashrelief="flat")
        pane.pack(fill="both", expand=True, pady=(4, 0))
        # each column is a separate scrollable frame
        self.results_frame = ScrollableFrame(pane, background=APP_BG)
        self.locations_frame = ScrollableFrame(pane, background=APP_BG)
        # add both to the pane with minimum widths so neither side can collapse to nothing
        pane.add(self.results_frame, minsize=440)
        pane.add(self.locations_frame, minsize=460)

        # calculate the filtered and sorted office list then render both columns
        self._sync_location_view()
        self._render_eligibility_cards()
        self._render_location_cards()

    def apply_income_scenario(self, _event: tk.Event | None = None) -> None:
        """re run eligibility using a hypothetical monthly income equal to the slider percentage of the user's actual income."""
        if not self.user_data:
            return
        pct = float(self.income_scenario_pct.get())
        # save the current statuses so we can compare them after recalculation
        old_statuses = {k: self.eligibility[k].status for k in self.selected_programs}
        u = dict(self.user_data)
        # scale the baseline monthly income by the slider percentage
        u["monthly_income"] = self._baseline_monthly * (pct / 100.0)
        self.eligibility = compute_eligibility(self.selected_programs, u)
        # build the "what changed" message by comparing old and new statuses
        changes = []
        for k in self.selected_programs:
            old = old_statuses.get(k, "")
            new = self.eligibility[k].status
            if old != new:
                short = PROGRAMS[k]["short_name"]
                # the up arrow means the eligibility improved; down means it got worse
                arrow = "↑" if new == "Highly eligible" or (new == "Partially eligible" and old == "Unlikely") else "↓"
                changes.append(f"{short}: {new} {arrow}")
        if hasattr(self, "_scenario_change_lbl"):
            if changes:
                self._scenario_change_lbl.configure(
                    text=f"At {pct:.0f}%: " + "  •  ".join(changes),
                    fg=SUCCESS if any("↑" in c for c in changes) else WARNING,
                )
            else:
                self._scenario_change_lbl.configure(text=f"No change at {pct:.0f}% — all programs stay the same", fg=MUTED)
        self.refresh_location_data()
        self._sync_location_view()
        self._render_eligibility_cards()
        self._render_location_cards()
        self._status(f"What-if income applied at {pct:.0f}% of reported monthly")

    def _sync_location_view(self) -> None:
        """filter and sort the in memory office list and store the result in _location_view for the right hand column."""
        q = self.office_search_var.get().strip().lower()
        items = list(self.location_results)
        if q:
            # keep only offices whose name, address, or city contains the search text
            items = [
                x
                for x in items
                if q in str(x["location"]["name"]).lower()
                or q in str(x["location"]["address"]).lower()
                or q in str(x["location"].get("city", "")).lower()
            ]
        # apply program filter only when at least one program checkbox is unchecked
        active_progs = {k for k, v in self.prog_filter_vars.items() if v.get()}
        if active_progs != set(PROGRAMS.keys()):
            items = [x for x in items if any(p in active_progs for p in x["programs"])]
        # apply favorites filter if the "favorites only" checkbox is ticked
        if self.show_favorites_var.get():
            items = [x for x in items if _loc_key(x["location"]) in self.favorite_keys]
        mode = self.office_sort_var.get()
        if mode == "name":
            items.sort(key=lambda it: str(it["location"]["name"]).lower())
        else:
            # sort by distance (with a large sentinel for unknown distances) then alphabetically as a tiebreaker
            items.sort(key=lambda it: (9999.0 if it["distance"] is None else float(it["distance"]), str(it["location"]["name"]).lower()))
        self._location_view = items

    def _office_filter_changed(self, *_args: object) -> None:
        # called whenever a filter checkbox or the search box changes; only do work on the results screen
        if self.current_step != 2:
            return
        self._sync_location_view()
        self._render_location_cards()

    def copy_results_summary(self) -> None:
        """copy a plain text summary of eligibility results to the clipboard; useful for emailing or texting to a caseworker."""
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

    def print_office_list(self) -> None:
        if not self._location_view:
            messagebox.showwarning("No offices", "No offices in current filter view.")
            return
        EXPORT_DIR.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = EXPORT_DIR / f"office_list_{ts}.html"
        progs_label = ", ".join(PROGRAMS[k]["short_name"] for k in self.selected_programs)
        rows_html = []
        for item in self._location_view:
            loc = item["location"]
            prog_names = ", ".join(PROGRAMS[k]["short_name"] for k in item["programs"])
            rows_html.append(
                f"<div class='office'>"
                f"<div class='name'>{html.escape(str(loc['name']))}</div>"
                f"<div class='addr'>{html.escape(str(loc['address']))}</div>"
                f"<div class='tags'>{html.escape(prog_names)} &nbsp;·&nbsp; {html.escape(item['distance_text'])}</div>"
                f"</div>"
            )
        page = (
            "<!DOCTYPE html><html><head><meta charset='utf-8'>"
            f"<title>Benefit Bridge — Office List</title>"
            "<style>"
            "body{font-family:sans-serif;max-width:680px;margin:40px auto;color:#1e293b}"
            "h1{color:#0369a1;margin-bottom:4px}h2{color:#334155;font-size:15px;margin-top:24px}"
            ".meta{color:#64748b;font-size:13px;margin-bottom:24px}"
            ".office{border-bottom:1px solid #e2e8f0;padding:12px 0}"
            ".name{font-weight:600;font-size:14px}"
            ".addr{color:#475569;font-size:13px;margin:3px 0}"
            ".tags{color:#0369a1;font-size:12px}"
            "footer{color:#94a3b8;font-size:11px;margin-top:36px;border-top:1px solid #e2e8f0;padding-top:10px}"
            "@media print{footer{position:fixed;bottom:0}}"
            "</style></head><body>"
            "<h1>Benefit Bridge</h1>"
            f"<div class='meta'>"
            f"<b>Location:</b> {html.escape(str(self.user_data.get('location_input', '')))}&nbsp;&nbsp;"
            f"<b>Programs:</b> {html.escape(progs_label)}&nbsp;&nbsp;"
            f"<b>Generated:</b> {datetime.now().strftime('%b %d, %Y')}"
            f"</div>"
            f"<h2>Nearby offices ({len(self._location_view)})</h2>"
            + "".join(rows_html)
            + "<footer>Estimates only — not a government decision. Confirm eligibility with the office before applying.</footer>"
            "</body></html>"
        )
        path.write_text(page, encoding="utf-8")
        webbrowser.open(path.as_uri())
        self._toast("Office list opened in browser — use your browser's Print function")

    def _render_eligibility_cards(self) -> None:
        # clear the left panel and rebuild one card per selected program
        self._clear(self.results_frame.inner)
        wl = self._pane_text_wrap()
        tk.Label(self.results_frame.inner, text="Eligibility detail", bg=APP_BG, fg=TEXT, font=(FONT_FAMILY, self._font_size(17), "bold")).pack(anchor="w", pady=(0, 16))
        for program_key in self.selected_programs:
            program = PROGRAMS[program_key]
            result = self.eligibility[program_key]
            card = self._card(self.results_frame.inner)
            card.pack(fill="x", pady=(0, 18), padx=(0, 10))
            card_body = self._surface(card)
            # for food programs try to extract the specific sub programs (snap or wic) from the passed text for a more useful title
            display_name = program["name"]
            if program_key == "food" and result.passed:
                # look for the pattern "income qualifies for snap (165% limit) and wic (185% limit)" in the passed messages
                for passed_item in result.passed:
                    if "qualifies for" in passed_item:
                        parts = passed_item.split("qualifies for ")
                        if len(parts) > 1:
                            display_name = "Food: " + parts[1].split(":")[0]
                        break
            tk.Label(
                card_body,
                text=display_name,
                bg=CARD_BG,
                fg=TEXT,
                font=(FONT_FAMILY, self._font_size(14), "bold"),
                wraplength=wl,
                justify="left",
            ).pack(anchor="w", padx=22, pady=(20, 8))
            badge_row = tk.Frame(card_body, bg=CARD_BG)
            badge_row.pack(fill="x", padx=22, pady=(0, 10))
            # the status pill badge showing "high match", "partial", or "unlikely"
            PillLabel(
                badge_row,
                status_pill_caption(result.status),
                STATUS_COLORS[result.status],
                STATUS_TEXT_COLORS[result.status],
                CARD_BG,
            ).pack(anchor="w")
            # the plain english explanation paragraph below the badge
            tk.Label(
                card_body,
                text=result.explanation,
                bg=CARD_BG,
                fg=SUBTEXT,
                font=(FONT_FAMILY, self._font_size(11)),
                wraplength=wl,
                justify="left",
            ).pack(anchor="w", padx=22, pady=(0, 14))
            # show the rules they met in green and the rules that need review in yellow
            if result.passed:
                self._mini_list(card_body, "Rules met", result.passed, SUCCESS)
            if result.missed:
                self._mini_list(card_body, "Needs review", result.missed, WARNING)

    def _render_location_cards(self) -> None:
        # clear the right panel and rebuild one card per visible office location
        self._clear(self.locations_frame.inner)
        wl = self._pane_text_wrap()
        tk.Label(self.locations_frame.inner, text="Nearby offices", bg=APP_BG, fg=TEXT, font=(FONT_FAMILY, self._font_size(17), "bold")).pack(anchor="w", pady=(0, 16))
        eligible_keys = self.programs_for_locations()
        # if no programs are eligible, show a card explaining why no offices appear
        if not eligible_keys:
            self._empty_card(
                self.locations_frame.inner,
                "No offices shown",
                "Offices appear only for programs marked Highly eligible or Partially eligible. Increase income scenario or adjust answers, then update the list.",
            )
            return
        # if there are eligible programs but no offices within the radius, show a helpful message
        if not self.location_results:
            self._empty_card(
                self.locations_frame.inner,
                "No offices in radius",
                "Try a larger radius or a sample city such as Sunnyvale, San Jose, Oakland, Los Angeles, San Diego, or Sacramento.",
            )
            return
        # if there are offices but the filters removed them all, tell the user to clear the search
        if not self._location_view:
            self._empty_card(self.locations_frame.inner, "No filter matches", "Clear the office search box or type part of a name, city, or street.")
            return
        # build one card per office in the current filtered and sorted view
        for item in self._location_view:
            location = item["location"]
            matching_programs = item["programs"]
            distance_text = item["distance_text"]
            card = self._card(self.locations_frame.inner)
            card.pack(fill="x", pady=(0, 18), padx=(0, 10))
            card_body = self._surface(card)
            # office name at the top of the card
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
            # a pill badge showing the distance to this office
            PillLabel(meta, distance_text, "#273549", TEXT, CARD_BG).pack(anchor="w")
            # the street address below the distance pill
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
            # a short summary of which programs this office handles and the best eligibility status
            tk.Label(
                card_body,
                text=next_step,
                bg=CARD_BG,
                fg=SUBTEXT,
                font=(FONT_FAMILY, self._font_size(11)),
                wraplength=wl,
                justify="left",
            ).pack(anchor="w", padx=22, pady=(0, 14))
            # a row of buttons the user can click to act on this office
            actions = tk.Frame(card_body, bg=CARD_BG)
            actions.pack(fill="x", padx=22, pady=(0, 22))
            addr = str(location["address"])
            origin = str(self.user_data.get("location_input", ""))
            self._button(actions, "Copy address", partial(copy_to_clipboard, self, addr), "secondary").pack(side="left", padx=(0, 6))
            self._button(actions, "Open in Maps", partial(open_location_in_maps, _maps_query(location)), "ghost").pack(side="left", padx=(0, 6))
            self._button(actions, "Directions", partial(open_directions_in_maps, _maps_query(location), origin), "ghost").pack(side="left")
            fav_key = _loc_key(location)
            # pick the star label based on whether this office is already saved as a favorite
            star_label = "★ Saved" if fav_key in self.favorite_keys else "☆ Save"
            self._button(actions, star_label, partial(self._toggle_favorite, fav_key), "ghost").pack(side="right")

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
        row.pack(fill="x", padx=18, pady=12)
       
        # use the custom dark themed checkbox widget instead of the default system one
        checkbox = ModernCheckbox(row, text=label, variable=variable, bg=CARD_BG, fg=TEXT)
        checkbox.pack(anchor="w")
       
        if hint:
            tk.Label(row, text=hint, bg=CARD_BG, fg=MUTED, font=(FONT_FAMILY, self._font_size(9)), wraplength=max(220, self._text_wrap() // 2 - 40), justify="left").pack(anchor="w", padx=8, pady=(4, 0))

    def select_all_programs(self) -> None:
        for variable in self.program_vars.values():
            variable.set(True)

    def clear_programs(self) -> None:
        for variable in self.program_vars.values():
            variable.set(False)

    def suggest_program_bundle(self) -> None:
        """one-click preset that selects the most common household basics programs for demos."""
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
            "healthy": self.healthy_var.get(),
            "child_under_13": self.child_under_13_var.get(),
            "child_under_5": self.child_under_5_var.get(),
            "pregnant": self.pregnant_var.get(),
            "postpartum": self.postpartum_var.get(),
            "breastfeeding": self.breastfeeding_var.get(),
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

    def _load_favorites(self) -> set[str]:
        if FAVORITES_FILE.exists():
            try:
                return set(json.loads(FAVORITES_FILE.read_text(encoding="utf-8")))
            except Exception:
                pass
        return set()

    def _save_favorites(self) -> None:
        try:
            FAVORITES_FILE.write_text(json.dumps(list(self.favorite_keys)), encoding="utf-8")
        except Exception:
            pass

    def _toggle_favorite(self, key: str) -> None:
        if key in self.favorite_keys:
            self.favorite_keys.discard(key)
        else:
            self.favorite_keys.add(key)
        self._save_favorites()
        self._sync_location_view()
        self._render_location_cards()

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
        )
        Path(path).write_text(html, encoding="utf-8")
        webbrowser.open(Path(path).as_uri())
        messagebox.showinfo("Draft saved", f"Application draft saved and opened in your browser:\n{path}")

    def go_next(self) -> None:
        """
        handles the next button. the behavior depends on which step the user is on.

        step 0 (program selection):
            validate that at least one program checkbox is ticked.
            if ok, advance to step 1.

        step 1 (household profile):
            validate all form fields (income, household size, location, etc.).
            if ok, run compute_eligibility() to get the pass/fail results.
            find nearby offices, then advance to step 2 (results screen).

        step 2 (results):
            the next button becomes save application and saves a printable report.
        """
        if self.current_step == 0:
            # step 0 to 1: make sure at least one program is checked
            if self.collect_programs():
                self.show_step(1)
        elif self.current_step == 1:
            # step 1 to 2: validate the profile then run the eligibility engine
            if self.collect_user_data():
                # remember the income the user entered so the what if slider works correctly
                self._baseline_monthly = float(self.user_data["monthly_income"])
                # reset the scenario slider and search filters so results start clean
                self.income_scenario_pct.set(100.0)
                self.office_search_var.set("")
                self.office_sort_var.set("distance")
                # run all the eligibility checks and store the results
                self.eligibility = compute_eligibility(self.selected_programs, self.user_data)
                # find offices near the user that can help with programs they qualify for
                self.refresh_location_data()
                # advance to the results screen
                self.show_step(2)
        else:
            # step 2: save the application to disk
            self.save_draft_application()

    def go_back(self) -> None:
        """go back one step. does nothing if already on step 0 (the first step)."""
        if self.current_step > 0:
            self.show_step(self.current_step - 1)

    def start_over(self) -> None:
        """
        reset all form fields and results back to their initial default values.
        asks the user to confirm first because this action clears all their work.
        """
        # show a yes/no dialog and bail out if they click no
        if not messagebox.askyesno("Start over", "Clear this run and start again?"):
            return
        # reset all program checkboxes to unchecked
        for variable in self.program_vars.values():
            variable.set(False)
        # reset every form field to its default value
        self.income_var.set("")                          # clear income amount
        self.income_period_var.set("Monthly")            # default: monthly
        self.household_var.set(3)                        # default household size
        self.location_var.set("")                        # clear zip or city
        self.state_var.set("California")                 # default state
        self.age_var.set("Adult")                        # default age range
        self.employment_var.set(EMPLOYMENT_OPTIONS[0])   # first option = "Working"
        self.residency_var.set(True)
        self.healthy_var.set(True)                       # default: is healthy
        self.child_under_13_var.set(True)                # default: has child under 13
        self.child_under_5_var.set(False)                # default: no child under 5
        self.utility_hardship_var.set(False)             # default: no utility hardship
        self.internet_need_var.set(True)                 # default: has internet need
        self.transportation_need_var.set(False)          # default: no transportation need
        self.radius_var.set("10")                        # default search radius: 10 miles
        self._radius_dbl.set(10.0)                       # reset slider position
        self.office_search_var.set("")                   # clear office search box
        self.office_sort_var.set("distance")             # default sort: closest first
        for v in self.prog_filter_vars.values():
            v.set(True)
        self.show_favorites_var.set(False)
        self.income_scenario_pct.set(100.0)              # reset what if slider to 100%
        self._baseline_monthly = 0.0                     # reset the baseline income
        self._location_view = []                         # clear filtered location results
        self.selected_programs = []                      # clear selected programs list
        self.user_data = {}                              # clear the household profile dict
        self.eligibility = {}                            # clear all eligibility results
        self.location_results = []                       # clear the list of nearby offices
        # go back to the first step
        self.show_step(0)


def parse_money(value: str) -> float:
    """
    convert what the user typed in the income field into a plain float.
    handles common formats like "$2,750", "2750", "2,750.00".

    strips the dollar sign and commas first, then converts to a float.
    raises valueerror if the string is empty or not a valid finite number
    (for example "infinity" or "NaN" would pass float() but fail isfinite).
    """
    # remove dollar signs and commas so "2,750" becomes "2750" before converting
    cleaned = value.replace("$", "").replace(",", "").strip()
    if not cleaned:
        raise ValueError("empty amount")   # user left the field blank
    amount = float(cleaned)
    if not math.isfinite(amount):
        raise ValueError("invalid amount")  # reject inf, negative inf, or not a number
    return amount


def extract_zip(location_input: str) -> str | None:
    """
    pull a 5-digit zip code out of whatever the user typed in the location field.
    works for inputs like "94085", "Sunnyvale, CA 94085", "ZIP: 94085", etc.

    returns the zip as a string (for example "94085"), or none if no zip is found.
    """
    # look for any sequence of exactly 5 digits surrounded by word boundaries
    match = re.search(r"\b\d{5}\b", location_input)
    if match:
        return match.group(0)   # return the first 5 digit match we found
    # fallback: if the whole input is just 5 digits with no spaces, treat it as a zip
    stripped = location_input.strip()
    return stripped if stripped.isdigit() and len(stripped) == 5 else None


def extract_city(location_input: str) -> str | None:
    """
    try to extract a recognizable city name from the user's location input.
    only used when there is no zip code in the input.

    strategy:
      1. strip everything that is not a letter or space.
      2. lowercase and collapse multiple spaces.
      3. check if any known city name (from city_coords) appears as a whole word.
         we check longest city names first to avoid "san" matching before "san jose".
      4. if no known city matches, return the cleaned text as is (best effort).

    returns none if the input had a zip (handled by extract_zip instead).
    """
    # if there is a zip in the input we do not need a city
    if extract_zip(location_input):
        return None
    # strip everything except letters and spaces then lowercase
    city = re.sub(r"[^A-Za-z ]", " ", location_input).strip().lower()
    # collapse multiple spaces into one (for example "san  jose" becomes "san jose")
    city = " ".join(city.split())
    if not city:
        return None   # input had no letters at all
    # check against known cities with longest names first to avoid partial matches
    for known_city in sorted(CITY_COORDS, key=len, reverse=True):
        if re.search(rf"\b{re.escape(known_city)}\b", city):
            return known_city   # found a match so return the canonical city name
    # no known city found so return whatever the user typed, cleaned up
    return city


def extra_person_amount(state: str, program_key: str) -> int:
    # look up the per extra person dollar increment for this state and program
    # first checks the state specific table and if not found falls back to
    # the federal fpl based defaults (used for internet). returns 0 if unknown
    return STATE_EXTRA_PERSON_AMOUNTS.get(state, {}).get(program_key, FPL_EXTRA_PERSON_AMOUNTS.get(program_key, 0))


def utility_eligibility_limit(utility_limits: dict[int, int], household_size: int, state: str) -> float:
    # utility programs use whichever limit is higher: the state's own table
    # or 150% of the federal poverty line. this protects households in states
    # with a low state limit but a relatively high poverty line
    state_limit = limit_for_household(utility_limits, household_size, extra_person_amount(state, "utility"))
    fpl_limit = limit_for_household(FPL_150_LIMITS, household_size, FPL_150_EXTRA_PERSON_AMOUNT)
    return max(state_limit, fpl_limit)


def compute_eligibility(selected_programs: list[str], user_data: dict[str, object]) -> dict[str, ProgramResult]:
    """
    run every selected program's eligibility rules and return a result for each.

    food is handled separately by food_eligibility() because it has dual-path
    logic (snap + wic) and state-specific fpl tables. every other program goes
    through the standard checks then classify_program() pipeline.
    """
    results: dict[str, ProgramResult] = {}
    state = str(user_data.get("state", "California"))
    # load this state's income limit tables and fall back to california if unknown
    limits = STATE_LIMITS.get(state, STATE_LIMITS["California"])
    for program_key in selected_programs:
        if program_key == "childcare":
            checks = childcare_checks(user_data, limits["childcare"], state)
        elif program_key == "food":
            # food gets its own function and skips the generic classify_program() step
            results[program_key] = food_eligibility(user_data, state)
            continue
        elif program_key == "utility":
            checks = utility_checks(user_data, limits["utility"], state)
        elif program_key == "internet":
            checks = internet_checks(user_data, limits["internet"], state)
        else:
            checks = transportation_checks(user_data, limits["transportation"], state)
        # turn the list of rule checks into a single pass/fail result with an explanation
        results[program_key] = classify_program(program_key, checks)
    return results


def childcare_checks(user: dict[str, object], childcare_limits: dict[int, int], state: str) -> list[RuleCheck]:
    """
    returns a list of rules to check for childcare subsidy eligibility.
    three rules:
      1. income must be under the state's childcare limit.
      2. the parent/guardian must be working, studying, or in training.
         (looking for work is treated as close, meaning borderline, not a hard fail.)
      3. there must be a child under 13 in the household. (critical: no child means instant unlikely.)
    """
    # get the income limit for this specific household size in this state
    limit = limit_for_household(childcare_limits, int(user["household_size"]), extra_person_amount(state, "childcare"))
    income = float(user["monthly_income"])
    # check if the parent has a qualifying activity (work, school, or training)
    working_or_studying = user["employment_status"] in {"Working", "In school or job training", "Working and in school"}
    return [
        income_check(income, limit, "Income is within the sample child-care limit"),
        RuleCheck(
            "Parent activity",
            working_or_studying,
            "Parent or caregiver is working, in school, or in job training.",
            "Child-care programs usually require a parent to work, study, or train.",
            close=user["employment_status"] == "Looking for work",  # looking for work is borderline, not a full pass
        ),
        RuleCheck(
            "Child age",
            bool(user["child_under_13"]),
            "A child in the household is under age 13.",
            "This sample child-care subsidy is focused on children under age 13.",
            critical=True,  # critical means failing this one rule alone causes unlikely status
        ),
    ]


def food_eligibility(user: dict[str, object], state: str) -> ProgramResult:
    """
    checks eligibility for two food assistance programs at the same time.

      snap (supplemental nutrition assistance program, also known as food stamps):
        income limit = 100% fpl times the state's bbce multiplier (for example 1.65 for texas)
        multiplier comes from snap_state_multipliers and defaults to 2.00 for broad states

      wic (women, infants, and children):
        only checked if there is a child under 5 in the household
        income limit = 100% fpl times 1.85 (fixed nationally at 185%)

    alaska and hawaii get their own higher fpl base tables because the federal
    government publishes separate poverty thresholds for those two states.

    returns a programresult directly (skips the generic classify_program step)
    because the dual-path logic and custom explanations do not fit the standard
    rulecheck model used by other programs.
    """
    # pull the four things we need from the user's form data
    household_size = int(user["household_size"])
    gross_income = float(user["monthly_income"])
    has_child_under_5 = bool(user.get("child_under_5", False))  # defaults to false for old drafts
    resident = bool(user["resident"])

    # step 1: pick the right fpl base table for this state
    # alaska and hawaii have higher fpl values published by hhs
    # everyone else uses the standard continental us fpl table
    if state == "Alaska":
        base_fpl = ALASKA_FPL_BASE
        extra_person = ALASKA_FPL_EXTRA_PERSON
    elif state == "Hawaii":
        base_fpl = HAWAII_FPL_BASE
        extra_person = HAWAII_FPL_EXTRA_PERSON
    else:
        base_fpl = FPL_100_LIMITS
        extra_person = FPL_BASE_EXTRA_PERSON_AMOUNTS["food"]

    # step 2: look up the 100% fpl dollar amount for this household size
    # if the household is bigger than 8, extend the table by adding extra_person per head
    fpl_100 = limit_for_household(base_fpl, household_size, extra_person)

    # step 3: calculate the actual income limits for each program
    snap_multiplier = SNAP_STATE_MULTIPLIERS.get(state, 2.00)  # 2.00 = 200% for broad states
    snap_limit = fpl_100 * snap_multiplier   # e.g. 2750 times 1.65 = 4537 for a texas family of 4
    wic_limit = fpl_100 * 1.85              # e.g. 2750 times 1.85 = 5088 nationally
    snap_pct = int(snap_multiplier * 100)    # e.g. 1.65 becomes 165 (used in explanation text)

    # step 4: residency is a hard requirement for both programs. fail immediately if not met.
    if not resident:
        return ProgramResult(
            status="Unlikely",
            explanation="You may not qualify for food assistance based on this estimate because food assistance often requires US residency or qualified non-citizen status.",
            passed=[],
            missed=["Food assistance often requires US residency or qualified non-citizen status."],
        )

    # step 5: check both program paths independently
    snap_eligible = gross_income <= snap_limit
    # wic requires: child under 5 or pregnant or postpartum or breastfeeding
    has_wic_criterion = (
        has_child_under_5 or
        user.get("pregnant", False) or
        user.get("postpartum", False) or
        user.get("breastfeeding", False)
    )
    wic_eligible = has_wic_criterion and gross_income <= wic_limit

    # step 6: if they qualify for either snap or wic (or both), return a highly eligible result
    if snap_eligible or wic_eligible:
        # build a list like ["SNAP (165% limit)", "WIC (185% limit)"]
        programs_qualified = []
        if snap_eligible:
            programs_qualified.append(f"SNAP ({snap_pct}% limit)")
        if wic_eligible:
            programs_qualified.append("WIC (185% limit)")
        qual_str = " and ".join(programs_qualified)  # joins them with "and" if both qualify
        explanation = f"Eligible for {qual_str}."
        # if income is above 100% fpl but still under the snap ceiling, warn that the
        # actual snap benefit amount is calculated after deducting rent and childcare
        if gross_income > fpl_100:
            explanation += " Note: Actual SNAP benefits depend on the Net Income Test (income minus rent/childcare)."
        return ProgramResult(
            status="Highly eligible",
            explanation=explanation,
            passed=[
                f"Income qualifies for {qual_str}: {format_money(gross_income)}/month.",
                "Household meets the sample residency condition.",
            ],
            missed=[],
        )

    # step 7: not eligible for either. check if they are close (within 15% of a limit).
    # being close triggers "partially eligible" instead of "unlikely"
    close = gross_income <= snap_limit * 1.15 or (has_wic_criterion and gross_income <= wic_limit * 1.15)
    # build a plain english explanation of why they did not qualify
    reason = (
        f"Income is above the food assistance limits: {format_money(gross_income)}/month vs. "
        f"SNAP limit {format_money(snap_limit)} ({snap_pct}%)"
    )
    if has_wic_criterion:
        reason += f" and WIC limit {format_money(wic_limit)} (185%)"
    reason += "."
    return ProgramResult(
        status="Partially eligible" if close else "Unlikely",
        explanation=f"You may not qualify for food assistance based on this estimate because {reason}",
        passed=["Household meets the sample residency condition."],
        missed=[reason],
    )


def utility_checks(user: dict[str, object], utility_limits: dict[int, int], state: str) -> list[RuleCheck]:
    """
    three rules for utility bill assistance:
      1. income must be under whichever is higher: the state limit or 150% fpl.
      2. household must report a bill hardship (past-due bill or shutoff notice).
      3. must be a us resident or qualified non-citizen. (critical: instant unlikely if not.)
    """
    household_size = int(user["household_size"])
    # use the higher of state limit vs. 150% fpl (see utility_eligibility_limit for details)
    limit = utility_eligibility_limit(utility_limits, household_size, state)
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


def internet_checks(user: dict[str, object], internet_limits: dict[int, int], state: str) -> list[RuleCheck]:
    """
    three rules for internet subsidy eligibility:
      1. income must be under 200% fpl (the same limit for all states).
      2. household must have a qualifying reason for needing internet (work, school, health, benefits).
      3. must be a us resident. (critical: instant unlikely if not.)
    """
    # internet uses a federal uniform limit that is the same for all states (200% fpl)
    limit = limit_for_household(internet_limits, int(user["household_size"]), extra_person_amount(state, "internet"))
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


def transportation_checks(user: dict[str, object], transportation_limits: dict[int, int], state: str) -> list[RuleCheck]:
    """
    three rules for transportation voucher eligibility:
      1. income must be under the state's transportation limit.
      2. household must report a transportation need (work, school, medical).
      3. applicant must have an active reason: working, studying, job-seeking, or a senior.
         (retired is treated as close, meaning borderline, not a hard fail.)
    """
    limit = limit_for_household(transportation_limits, int(user["household_size"]), extra_person_amount(state, "transportation"))
    income = float(user["monthly_income"])
    # these statuses count as actively needing transportation assistance
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
            active_status or user["age_range"] == "Senior",  # seniors qualify automatically
            "Applicant has a work, school, job-search, or senior mobility reason.",
            "Transportation vouchers usually need a work, school, job-search, medical, or senior mobility reason.",
            close=user["employment_status"] == "Retired",  # retired is borderline, not a hard fail
        ),
    ]


def income_check(income: float, limit: float, label: str) -> RuleCheck:
    # reusable helper that builds a standard income rule check
    # close is true if the income is within 15% above the limit, used to
    # show partially eligible instead of unlikely when someone is nearly there
    return RuleCheck(
        "Income",
        income <= limit,
        f"{label}: {format_money(income)} monthly is at or below {format_money(limit)}.",
        f"Income is above the sample limit: {format_money(income)} monthly vs. {format_money(limit)}.",
        close=income <= limit * 1.15,
    )


def classify_program(program_key: str, checks: list[RuleCheck]) -> ProgramResult:
    """
    takes the list of rule checks for a program and decides the overall status.

      "highly eligible"    means passed every single rule
      "partially eligible" means failed 1 or 2 rules but all failures are borderline (close)
                           or only one rule was failed at all
      "unlikely"           means failed a critical rule or failed too many rules to be borderline

    then generates a plain english explanation and bundles it all into a programresult.
    """
    # split checks into passed and failed lists
    passed = [check.pass_text for check in checks if check.passed]
    missed = [check.fail_text for check in checks if not check.passed]
    failures = [check for check in checks if not check.passed]
    critical_failures = [check for check in failures if check.critical]   # instant disqualifiers
    close_failures = [check for check in failures if check.close]         # borderline failures

    if not failures:
        # passed everything, best possible result
        status = "Highly eligible"
    elif critical_failures:
        # any critical failure (for example no child under 13 for childcare) means unlikely with no exceptions
        status = "Unlikely"
    elif len(failures) <= 2 and (len(close_failures) == len(failures) or len(failures) == 1):
        # failed 1 or 2 rules but all of them are borderline so worth showing a partial result
        status = "Partially eligible"
    else:
        # too many failures or failures that are not borderline
        status = "Unlikely"

    explanation = plain_language_explanation(program_key, status, passed, missed)
    return ProgramResult(status=status, explanation=explanation, passed=passed, missed=missed)


def plain_language_explanation(program_key: str, status: str, passed: list[str], missed: list[str]) -> str:
    # generates a single plain english sentence summarizing the result.
    # food has its own custom explanation built inside food_eligibility(),
    # so this function is only called for childcare, utility, internet, and transportation
    program_name = PROGRAMS[program_key]["short_name"].lower()
    if status == "Highly eligible":
        return f"You likely qualify for {program_name} because the sample rules are all met."
    if status == "Partially eligible":
        return f"You may qualify for {program_name}, but one or two details need review. An office can confirm whether exceptions or alternate rules apply."
    # unlikely: lead with the primary reason they did not qualify
    primary_reason = missed[0] if missed else "multiple sample rules were not met."
    return f"You may not qualify for {program_name} based on this estimate because {primary_reason}"


def limit_for_household(table: dict[int, int], household_size: int, extra_person_amount: int) -> int:
    """
    looks up the income limit for a given household size from a table.
    the tables only go up to 8 people. if the household is larger,
    we extend the table by adding extra_person_amount for each person beyond 8.

    example: table has an 8-person limit of $4,643. a 10-person household
    would be: $4,643 + (2 x $473) = $5,589.
    """
    if household_size in table:
        return table[household_size]
    # household is larger than the table so extend it
    largest = max(table)
    return table[largest] + (household_size - largest) * extra_person_amount


def find_locations(user_data: dict[str, object], eligibility: dict[str, ProgramResult], radius_miles: float) -> list[dict[str, object]]:
    """
    find offices from the locations list that:
      1. offer at least one program the user is eligible for (highly or partially eligible)
      2. are within radius_miles of the user's zip or city

    returns a list of dicts sorted by distance (closest first).
    each dict has: location (the raw locations entry), programs (list of matching
    program keys), distance (miles as float or none), distance_text (readable string).
    """
    # build a set of program keys the user qualifies for. only those are worth showing offices for.
    eligible_programs = {
        key
        for key, result in eligibility.items()
        if result.status in {"Highly eligible", "Partially eligible"}  # skip unlikely results
    }

    # try to get the user's (lat, lon) from their zip or city so we can measure distance
    user_coord = resolve_user_coord(user_data)
    user_zip = user_data.get("zip")     # e.g. "94085"
    user_city = user_data.get("city")   # e.g. "sunnyvale"
    results = []

    for location in LOCATIONS:
        # only keep offices that offer at least one program the user qualifies for
        matching_programs = [key for key in location["programs"] if key in eligible_programs]
        if not matching_programs:
            continue   # this office cannot help so skip it

        # if the user wants healthy food only, skip food locations that are not marked healthy
        if user_data.get("healthy") and "food" in matching_programs and not location.get("healthy"):
            continue

        # get the office's (lat, lon) so we can measure how far it is
        loc_coord = ZIP_COORDS.get(location["zip"])
        # compute distance in miles if we have both coordinates, otherwise none
        distance = miles_between(user_coord, loc_coord) if user_coord and loc_coord else None
        # these are used as a fallback when we do not have coordinates
        same_zip = user_zip and user_zip == location["zip"]
        same_city = user_city and user_city == location["city"].lower()

        if distance is not None:
            # we have real coordinates so only include if within the chosen radius
            if distance > radius_miles:
                continue   # too far away
        elif not (same_zip or same_city):
            # no coordinates so only include if the zip or city matches exactly
            continue

        results.append(
            {
                "location": location,               # the full office entry from locations
                "programs": matching_programs,      # which programs this office can help with
                "distance": distance,               # float miles, or none if unknown
                "distance_text": format_distance(distance, same_zip),  # e.g. "2.3 mi"
            }
        )

    # sort by distance first (9999 pushes unknowns to the bottom), then alphabetically by name
    results.sort(key=lambda item: (9999 if item["distance"] is None else item["distance"], item["location"]["name"].lower()))
    return results


def resolve_user_coord(user_data: dict[str, object]) -> tuple[float, float] | None:
    """
    figure out the user's (latitude, longitude) from what they typed.
    first tries to match by zip code, then by city name.
    returns none if neither is found in our coordinate tables.
    """
    user_zip = user_data.get("zip")
    if user_zip and user_zip in ZIP_COORDS:
        # found their zip in our table so use that coordinate directly
        return ZIP_COORDS[str(user_zip)]
    city = user_data.get("city")
    if city and str(city).lower() in CITY_COORDS:
        # found their city so use the city's center coordinate
        return CITY_COORDS[str(city).lower()]
    # neither zip nor city matched so we cannot place them on a map
    return None


def miles_between(start: tuple[float, float] | None, end: tuple[float, float] | None) -> float | None:
    """
    calculate the straight-line distance in miles between two (lat, lon) points
    using the haversine formula. this is the standard way to get accurate
    distances on a sphere (the earth) from coordinates.

    returns none if either coordinate is missing.
    """
    if not start or not end:
        return None   # cannot measure without both points
    # convert degrees to radians because python's math functions expect radians
    lat1, lon1 = map(math.radians, start)
    lat2, lon2 = map(math.radians, end)
    # haversine formula calculates the shortest path distance between two points on a sphere
    dlat = lat2 - lat1   # difference in latitude
    dlon = lon2 - lon1   # difference in longitude
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return 3958.8 * c   # 3958.8 is the earth's radius in miles


def format_distance(distance: float | None, same_zip: bool | None = False) -> str:
    """
    convert a raw mile distance into a human-friendly label for display.
    used in the location cards (for example "2.3 mi", "same ZIP", "nearby").
    """
    if same_zip:
        return "same ZIP"       # user and office share a zip so they are very close
    if distance is None:
        return "nearby"         # no coords available so just say nearby
    if distance < 0.2:
        return "same area"      # under a quarter mile, basically next door
    return f"{distance:.1f} mi"  # e.g. "4.7 mi"


def format_money(value: float) -> str:
    """format a dollar amount with a dollar sign and thousands comma. no cents.
    example: 1330.0 becomes "$1,330" and 12750.5 becomes "$12,751"
    """
    return f"${value:,.0f}"


def append_case_history(
    path: Path,                                    # path to the csv file on disk
    selected_programs: list[str],                  # which programs were checked
    user_data: dict[str, object],                  # the household's profile
    eligibility: dict[str, ProgramResult],         # the eligibility results
    locations: list[dict[str, object]],            # nearby offices found
    radius: str,                                   # search radius in miles (as a string)
) -> None:
    """
    append one row to the case history csv file.

    each row is a snapshot of a single screening session: who was screened,
    which programs were checked, and what the results were. this lets staff
    review usage over time without storing any personally identifiable info.

    the csv is created automatically if it does not exist yet.
    new rows are always appended (not overwritten) so history is never lost.
    """
    # check if the file already exists so we know whether to write the header row
    file_exists = path.exists()
    # open in append mode so existing rows are never overwritten
    with path.open("a", newline="", encoding="utf-8") as file:
        # dictwriter lets us write dicts as rows, using the fieldnames as column headers
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "timestamp",          # when this screening happened
                "selected_programs",  # which programs the user checked
                "monthly_income",     # monthly gross income entered
                "household_size",     # number of people in the household
                "location",           # zip or city the user entered
                "age_range",          # age group of the applicant
                "employment_status",  # their employment situation
                "radius_miles",       # how wide the office search was
                "eligibility",        # results per program (e.g. "food: Highly eligible")
                "location_count",     # how many nearby offices were found
            ],
        )
        # only write the header once, when the file is brand new
        if not file_exists:
            writer.writeheader()
        # write one row for this session
        writer.writerow(
            {
                "timestamp": datetime.now().isoformat(timespec="seconds"),   # e.g. "2026-04-29T14:23:00"
                "selected_programs": "; ".join(selected_programs),           # e.g. "food; utility"
                "monthly_income": f"{float(user_data['monthly_income']):.2f}",  # e.g. "2750.00"
                "household_size": user_data["household_size"],               # e.g. 4
                "location": user_data["location_input"],                     # what the user typed
                "age_range": user_data["age_range"],                         # e.g. "Adult"
                "employment_status": user_data["employment_status"],         # e.g. "Working"
                "radius_miles": radius,                                      # e.g. "10"
                # compact summary of all results, e.g. "food: Highly eligible; utility: Unlikely"
                "eligibility": "; ".join(f"{key}: {result.status}" for key, result in eligibility.items()),
                "location_count": len(locations),                            # e.g. 3
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


def _get_program_display_name(program_key: str, result: ProgramResult) -> str:
    """extract specific program names (snap/wic, etc.) from the eligibility result if available."""
    if program_key == "food" and result.passed:
        for passed_item in result.passed:
            if "qualifies for" in passed_item.lower():
                # extract program name from "Income qualifies for SNAP (165% limit)"
                # or "Income qualifies for SNAP (165% limit) and WIC (185% limit)"
                start_idx = passed_item.lower().find("qualifies for")
                if start_idx != -1:
                    start_idx += len("qualifies for")
                    end_idx = passed_item.find(":", start_idx)
                    if end_idx == -1:
                        end_idx = passed_item.find(".", start_idx)
                    if end_idx != -1:
                        programs_text = passed_item[start_idx:end_idx].strip()
                        return f"Food: {programs_text}"
    return PROGRAMS[program_key]["name"]


def build_draft_application(
    selected_programs: list[str],
    user_data: dict[str, object],
    eligibility: dict[str, ProgramResult],
    locations: list[dict[str, object]],
    radius: str,
) -> str:
    """build the complete html document for the printable draft application report.
    takes the programs the user picked, the form answers, the eligibility results,
    and the nearby offices list, then assembles them into a styled html page.
    returns the finished html string which the app opens in the browser."""
    # safely embed the applicant name into html so characters like < and & do not break the page
    applicant_name = html.escape(str(user_data.get("applicant_name", "")).strip() or "Applicant")
    # pull the state the user selected on the form
    state = str(user_data.get("state", ""))
    # format the monthly income as a dollar string like "$2,750"
    income_str = format_money(float(user_data["monthly_income"]))
    # the number of people in the household
    household = user_data["household_size"]
    # the zip code or city text the user typed
    location_input = user_data.get("location_input", "")
    # the age range option the user selected (child, adult, or senior)
    age_range = user_data.get("age_range", "")
    # the employment status option the user selected
    employment = user_data.get("employment_status", "")
    # convert each boolean checkbox value into a readable "yes" or "no" string for the html
    resident = "Yes" if user_data.get("resident") else "No"
    child_u13 = "Yes" if user_data.get("child_under_13") else "No"
    child_u5 = "Yes" if user_data.get("child_under_5") else "No"
    utility_hardship = "Yes" if user_data.get("utility_hardship") else "No"
    internet_need = "Yes" if user_data.get("internet_need") else "No"
    transport_need = "Yes" if user_data.get("transportation_need") else "No"

    # build the summary row showing each program name and its eligibility status badge
    summary_pills = "".join(
        f'<div style="display:flex;align-items:center;gap:12px;padding:12px 0;'
        f'border-bottom:1px solid #f1f5f9;">'
        f'<span style="font-weight:600;color:#1e293b;min-width:190px;">'
        f'{_get_program_display_name(k, eligibility[k])}</span>'
        f'{_html_badge(eligibility[k].status)}</div>'
        for k in selected_programs
    )

    # build the detailed section for each program one at a time
    program_sections = ""
    for k in selected_programs:
        # get the eligibility result object for this program
        result = eligibility[k]
        # get the program metadata like its name and description
        prog = PROGRAMS[k]
        # look up the badge colors for this status; fall back to neutral gray if not found
        bg, fg = _STATUS_BADGE.get(result.status, ("#e5e7eb", "#374151"))
        # get the longer description text for this program if available
        description = _PROGRAM_DESCRIPTIONS.get(k, prog["description"])
        # get the list of documents the user should bring for this program
        docs = _PROGRAM_DOCS.get(k, [])

        # build an html list item for each rule the user passed (shown in green with a checkmark)
        passed_html = "".join(
            f'<li style="margin-bottom:6px;color:#065f46;">&#10003;&nbsp;{t}</li>'
            for t in result.passed
        )
        # build an html list item for each rule the user missed (shown in amber with a warning icon)
        missed_html = "".join(
            f'<li style="margin-bottom:6px;color:#92400e;">&#9888;&nbsp;{t}</li>'
            for t in result.missed
        )
        # only include the rules sections in the html if there is at least one item to show
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
                Documents to bring
              </p>
              {_html_checklist(docs)}
            </div>
          </div>
        </div>
        """

    # build the nearby offices section of the html report
    if locations:
        # start with an empty string and append an html card for each office
        office_rows = ""
        # cap the list at 10 offices so the page does not become too long
        for item in locations[:10]:
            loc = item["location"]
            # build small blue pill chips showing which programs this office handles
            prog_tags = "".join(
                f'<span style="display:inline-block;padding:2px 10px;border-radius:999px;'
                f'background:#eff6ff;color:#1d4ed8;font-size:11px;font-weight:600;margin:2px;">'
                f'{PROGRAMS[p]["short_name"]}</span>'
                for p in item["programs"] if p in PROGRAMS
            )
            # append this office as a single html card row: name, address, distance, and program chips
            office_rows += f"""
            <div style="padding:16px 0;border-bottom:1px solid #f1f5f9;">
              <div style="font-weight:700;color:#1e293b;font-size:15px;">{loc['name']}</div>
              <div style="color:#64748b;margin:4px 0 8px;font-size:13px;">
                {loc['address']}&nbsp;&nbsp;
                <span style="color:#94a3b8;">({item['distance_text']})</span>
              </div>
              <div>{prog_tags}</div>
            </div>
            """
        # wrap all the office rows inside a dark header card container
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
        # no offices were found so just show a short italicized message
        offices_section = (
            '<p style="color:#64748b;font-style:italic;">No offices found within the selected radius.</p>'
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
          <td style="padding:9px 0;color:#64748b;border-bottom:1px solid #f1f5f9;">Child under 5 (WIC)</td>
          <td style="padding:9px 0;font-weight:600;border-bottom:1px solid #f1f5f9;">{child_u5}</td>
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
    by state, county, and funding year. Always verify requirements with the administering agency.
  </div>

</div>
</body>
</html>"""


def summarize_location_results(items: list[dict[str, object]]) -> str:
    """build a one sentence summary of the closest matching office.
    used in the status bar and copy summary feature.
    returns a fallback message if the list is empty."""
    # if no offices were found at all, say so and stop
    if not items:
        return "No matching offices found."
    # grab the first item which is always the closest office after sorting by distance
    top = items[0]
    location = top["location"]
    # join the short names of all programs this office handles into one comma separated string
    programs = ", ".join(PROGRAMS[key]["short_name"] for key in top["programs"])
    # build and return the final sentence
    return f"Closest match: {location['name']} ({top['distance_text']}) for {programs}."


def clamp(value: int, low: int, high: int) -> int:
    """keep value between low and high (inclusive).
    example: clamp(150, 9, 22) gives 22 and clamp(5, 9, 22) gives 9.
    used mainly to keep font sizes from going out of range in accessibility mode.
    """
    return max(low, min(high, value))


def safe_get_program_short_names(program_keys: list[str]) -> str:
    """turn a list of program keys into a comma-separated string of short names.
    skips any key that is not in the programs dict so unknown keys do not crash the app.
    example: ["food", "utility"] becomes "Food, Utilities"
    """
    return ", ".join(PROGRAMS[key]["short_name"] for key in program_keys if key in PROGRAMS)


def sanitize_location_text(text: str) -> str:
    """strip leading/trailing whitespace and collapse multiple spaces into one.
    example: "  San   Jose  " becomes "San Jose".
    used before displaying or saving location strings.
    """
    return " ".join(text.strip().split())


# entry point section
# python only runs the code below if this file is executed directly
# (for example: python BenefitBridge.py). if the file is imported by another
# script, this block is skipped, which is important for testing and packaging.
if __name__ == "__main__":
    # create the main application window (which calls __init__ and builds the ui)
    app = BenefitBridgeApp()
    # hand control to tk's event loop, this runs forever until the window is closed
    app.mainloop()

