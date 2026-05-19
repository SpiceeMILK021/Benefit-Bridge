from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus
import csv
import html
import json
import math
import os
import re
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import webbrowser

try:
    from zip_data import CITY_COORDS, ZIP_COORDS
except Exception:
    CITY_COORDS = {}
    ZIP_COORDS = {}


def resource_path(relative_path: str) -> str:
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


APP_DIR = Path(resource_path("."))
DRAFT_FILE = APP_DIR / "benefit_bridge_v4_draft.json"
HISTORY_FILE = APP_DIR / "benefit_bridge_v4_history.csv"
EXPORT_DIR = APP_DIR / "exports"

PROGRAMS = {
    "childcare": {"name": "Child-care subsidy", "short": "Child care"},
    "food": {"name": "Food assistance / SNAP-like program", "short": "Food"},
    "utility": {"name": "Utility bill help", "short": "Utilities"},
    "internet": {"name": "Internet subsidy", "short": "Internet"},
    "transportation": {"name": "Other: transportation vouchers", "short": "Transport"},
}

FPL_BASE_LIMITS = {1: 1330, 2: 1803, 3: 2276, 4: 2750, 5: 3223, 6: 3696, 7: 4170, 8: 4643}
FPL_200_LIMITS = {size: amount * 2 for size, amount in FPL_BASE_LIMITS.items()}
FPL_150_LIMITS = {size: amount * 1.5 for size, amount in FPL_BASE_LIMITS.items()}

STATE_LIMITS = {
    "California": {
        "childcare": {1: 4992, 2: 6232, 3: 7472, 4: 8712, 5: 9952, 6: 11192, 7: 12432, 8: 13672},
        "internet": FPL_200_LIMITS,
        "utility": {1: 3459, 2: 4523, 3: 5587, 4: 6651, 5: 7715, 6: 8779, 7: 8979, 8: 9178},
        "transportation": {1: 2200, 2: 2980, 3: 3760, 4: 4550, 5: 5330, 6: 6120, 7: 6900, 8: 7690},
    },
    "Texas": {
        "childcare": {1: 3801, 2: 4971, 3: 6141, 4: 7311, 5: 8481, 6: 9651, 7: 10821, 8: 11991},
        "internet": FPL_200_LIMITS,
        "utility": {1: 2918, 2: 3816, 3: 4714, 4: 5612, 5: 6510, 6: 7408, 7: 7576, 8: 7744},
        "transportation": {1: 2000, 2: 2700, 3: 3400, 4: 4100, 5: 4800, 6: 5500, 7: 6200, 8: 6900},
    },
    "New York": {
        "childcare": {1: 4706, 2: 6155, 3: 7604, 4: 9053, 5: 10502, 6: 11951, 7: 13400, 8: 14849},
        "internet": FPL_200_LIMITS,
        "utility": {1: 3563, 2: 4660, 3: 5756, 4: 6853, 5: 7949, 6: 9045, 7: 9251, 8: 9456},
        "transportation": {1: 2300, 2: 3100, 3: 3900, 4: 4700, 5: 5500, 6: 6300, 7: 7100, 8: 7900},
    },
}

SNAP_STATE_MULTIPLIERS = {"Texas": 1.65, "California": 2.0, "New York": 2.0}
EXTRA_PERSON_AMOUNT = 473
EMPLOYMENT_OPTIONS = ["Working", "In school or job training", "Working and in school", "Looking for work", "Not working or in school", "Retired"]
STATE_OPTIONS = list(STATE_LIMITS)
RADIUS_OPTIONS = ["5", "10", "25", "50", "100"]

PROGRAM_CHECKLISTS = {
    "childcare": ["Photo ID", "Proof of income", "Work, school, or training schedule", "Child proof of age"],
    "food": ["Photo ID", "Proof of household income", "Proof of address", "Utility bill if requested"],
    "utility": ["Past-due bill or shutoff notice", "Photo ID", "Proof of income", "Service address document"],
    "internet": ["Photo ID", "Proof of income or aid program participation", "Proof of address"],
    "transportation": ["Photo ID", "Proof of income", "Work, school, medical, or appointment letter"],
}

APP_BG = "#0a0e14"
HEADER_BG = "#0f141c"
CARD_BG = "#121826"
CARD_BG_HOVER = "#171d2e"
INPUT_BG = "#1a2233"
RAIL_BG = "#0d1118"
BORDER = "#2a3447"
TEXT = "#e8eef9"
SUBTEXT = "#c5d1e8"
MUTED = "#94a3b8"
PRIMARY = "#3b82f6"
PRIMARY_HOVER = "#2563eb"
ACCENT = "#38bdf8"
ACCENT_DIM = "#0ea5e9"
SUCCESS = "#34d399"
WARNING = "#fbbf24"

STATUS_COLORS = {
    "Highly eligible": "#bbf7d0",
    "Partially eligible": "#fde68a",
    "Unlikely": "#fecaca",
}


def load_locations() -> list[dict[str, object]]:
    path = Path(resource_path("locations.json"))
    if not path.exists():
        return []
    try:
        with path.open(encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


LOCATIONS = load_locations()


@dataclass
class RuleCheck:
    name: str
    passed: bool
    pass_text: str
    fail_text: str
    close: bool = False
    critical: bool = False


@dataclass
class ProgramResult:
    status: str
    explanation: str
    passed: list[str]
    missed: list[str]


def parse_money(value: str) -> float:
    cleaned = value.replace("$", "").replace(",", "").strip()
    if not cleaned:
        raise ValueError("Enter an income amount.")
    amount = float(cleaned)
    if not math.isfinite(amount) or amount < 0:
        raise ValueError("Income must be a positive number.")
    return amount


def format_money(value: float) -> str:
    return f"${value:,.0f}"


def limit_for_household(table: dict[int, int | float], household_size: int, extra_person_amount: int = EXTRA_PERSON_AMOUNT) -> int:
    if household_size in table:
        return int(table[household_size])
    largest_size = max(table)
    return int(table[largest_size] + (household_size - largest_size) * extra_person_amount)


def income_rule(income: float, limit: float, label: str) -> RuleCheck:
    return RuleCheck(
        "Income",
        income <= limit,
        f"{label}: {format_money(income)} monthly is at or below {format_money(limit)}.",
        f"Income is above the limit: {format_money(income)} monthly vs. {format_money(limit)}.",
        close=income <= limit * 1.15,
    )


def compute_eligibility(selected_programs: list[str], user: dict[str, object]) -> dict[str, ProgramResult]:
    state = str(user.get("state", "California"))
    limits = STATE_LIMITS.get(state, STATE_LIMITS["California"])
    results: dict[str, ProgramResult] = {}

    for program_key in selected_programs:
        if program_key == "food":
            results[program_key] = food_eligibility(user, state)
            continue

        if program_key == "utility":
            state_limit = limit_for_household(limits["utility"], int(user["household_size"]))
            fpl_floor = limit_for_household(FPL_150_LIMITS, int(user["household_size"]))
            limit = max(state_limit, fpl_floor)
        else:
            limit = limit_for_household(limits[program_key], int(user["household_size"]))

        checks = [income_rule(float(user["monthly_income"]), limit, f"Income is within the {PROGRAMS[program_key]['short']} limit")]

        if program_key == "childcare":
            checks.extend(
                [
                    RuleCheck("Child under 13", bool(user.get("child_under_13")), "A child in the household is under age 13.", "Child-care help usually focuses on children under age 13.", critical=True),
                    RuleCheck("Parent activity", str(user.get("employment_status")) in {"Working", "In school or job training", "Working and in school"}, "Parent or caregiver is working, in school, or in job training.", "Child-care programs usually require work, school, or training.", close=str(user.get("employment_status")) == "Looking for work"),
                ]
            )
        elif program_key == "utility":
            checks.extend(
                [
                    RuleCheck("Bill hardship", bool(user.get("utility_hardship")), "Household reports utility bill hardship.", "Utility bill help is often prioritized for shutoff notices or past-due bills."),
                    RuleCheck("Residency", bool(user.get("resident")), "Household meets the residency condition.", "Many utility programs require local residency or qualified status.", critical=True),
                ]
            )
        elif program_key == "internet":
            checks.extend(
                [
                    RuleCheck("Internet need", bool(user.get("internet_need")), "Household reports a need for home internet access.", "The internet subsidy expects a work, school, health, or benefits need."),
                    RuleCheck("Residency", bool(user.get("resident")), "Household meets the residency condition.", "Internet subsidies may require local residency or qualified status.", critical=True),
                ]
            )
        elif program_key == "transportation":
            active = str(user.get("employment_status")) in {"Working", "In school or job training", "Working and in school", "Looking for work"} or str(user.get("age_range")) == "Senior"
            checks.extend(
                [
                    RuleCheck("Transportation need", bool(user.get("transportation_need")), "Household reports a transportation need.", "Voucher programs usually require a work, school, or medical transportation need."),
                    RuleCheck("Activity", active, "Applicant has a work, school, job-search, or senior mobility reason.", "Transportation vouchers usually need a work, school, job-search, medical, or senior mobility reason.", close=str(user.get("employment_status")) == "Retired"),
                ]
            )

        results[program_key] = classify_result(program_key, checks)
    return results


def food_eligibility(user: dict[str, object], state: str) -> ProgramResult:
    household_size = int(user["household_size"])
    income = float(user["monthly_income"])
    fpl_100 = limit_for_household(FPL_BASE_LIMITS, household_size)
    snap_multiplier = SNAP_STATE_MULTIPLIERS.get(state, 2.0)
    snap_limit = fpl_100 * snap_multiplier
    wic_limit = fpl_100 * 1.85
    has_wic_path = bool(user.get("child_under_5") or user.get("pregnant") or user.get("postpartum") or user.get("breastfeeding"))

    if not user.get("resident"):
        return ProgramResult("Unlikely", "Food assistance often requires US residency or qualified non-citizen status.", [], ["Food assistance often requires US residency or qualified non-citizen status."])

    snap_ok = income <= snap_limit
    wic_ok = has_wic_path and income <= wic_limit
    if snap_ok or wic_ok:
        names = []
        if snap_ok:
            names.append(f"SNAP ({int(snap_multiplier * 100)}% limit)")
        if wic_ok:
            names.append("WIC (185% limit)")
        label = " and ".join(names)
        return ProgramResult("Highly eligible", f"Eligible for {label} based on this estimate.", [f"Income qualifies for {label}: {format_money(income)}/month.", "Household meets the residency condition."], [])

    close = income <= snap_limit * 1.15 or (has_wic_path and income <= wic_limit * 1.15)
    reason = f"Income is above the food assistance limit: {format_money(income)} vs. SNAP limit {format_money(snap_limit)}."
    return ProgramResult("Partially eligible" if close else "Unlikely", f"You may not qualify for food assistance because {reason}", ["Household meets the residency condition."], [reason])


def classify_result(program_key: str, checks: list[RuleCheck]) -> ProgramResult:
    passed = [check.pass_text for check in checks if check.passed]
    missed = [check.fail_text for check in checks if not check.passed]
    failures = [check for check in checks if not check.passed]
    if not failures:
        status = "Highly eligible"
    elif any(check.critical for check in failures):
        status = "Unlikely"
    elif len(failures) <= 2 and (len(failures) == 1 or all(check.close for check in failures)):
        status = "Partially eligible"
    else:
        status = "Unlikely"
    program_name = PROGRAMS[program_key]["short"].lower()
    if status == "Highly eligible":
        explanation = f"You likely qualify for {program_name} because the current rules are met."
    elif status == "Partially eligible":
        explanation = f"You may qualify for {program_name}, but one or two details need review."
    else:
        explanation = f"You may not qualify for {program_name} based on this estimate."
    return ProgramResult(status, explanation, passed, missed)


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


def resolve_user_coord(user_data: dict[str, object]) -> tuple[float, float] | None:
    zip_code = user_data.get("zip")
    if zip_code and str(zip_code) in ZIP_COORDS:
        return ZIP_COORDS[str(zip_code)]
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


def format_distance(distance: float | None, same_zip: bool = False) -> str:
    if same_zip:
        return "same ZIP"
    if distance is None:
        return "nearby"
    if distance < 0.2:
        return "same area"
    return f"{distance:.1f} mi"


def find_locations(user_data: dict[str, object], eligibility: dict[str, ProgramResult], radius_miles: float) -> list[dict[str, object]]:
    eligible_programs = {key for key, result in eligibility.items() if result.status in {"Highly eligible", "Partially eligible"}}
    user_coord = resolve_user_coord(user_data)
    user_zip = str(user_data.get("zip") or "")
    user_city = str(user_data.get("city") or "").lower()
    results = []

    for location in LOCATIONS:
        programs = [key for key in location.get("programs", []) if key in eligible_programs]
        if not programs:
            continue
        if user_data.get("healthy_food") and "food" in programs and location.get("healthy") is False:
            continue

        loc_zip = str(location.get("zip", ""))
        loc_city = str(location.get("city", "")).lower()
        loc_coord = ZIP_COORDS.get(loc_zip)
        distance = miles_between(user_coord, loc_coord) if user_coord and loc_coord else None
        same_zip = bool(user_zip and user_zip == loc_zip)
        same_city = bool(user_city and user_city == loc_city)

        if distance is not None:
            if distance > radius_miles:
                continue
        elif not (same_zip or same_city):
            continue

        results.append({"location": location, "programs": programs, "distance": distance, "distance_text": format_distance(distance, same_zip)})

    results.sort(key=lambda item: (9999 if item["distance"] is None else item["distance"], str(item["location"].get("name", "")).lower()))
    return results


def append_history(selected_programs: list[str], user_data: dict[str, object], eligibility: dict[str, ProgramResult], locations: list[dict[str, object]], radius: str) -> None:
    file_exists = HISTORY_FILE.exists()
    with HISTORY_FILE.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["timestamp", "programs", "income", "household_size", "location", "radius", "eligibility", "location_count"])
        if not file_exists:
            writer.writeheader()
        writer.writerow(
            {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "programs": "; ".join(selected_programs),
                "income": f"{float(user_data['monthly_income']):.2f}",
                "household_size": user_data["household_size"],
                "location": user_data["location_input"],
                "radius": radius,
                "eligibility": "; ".join(f"{key}: {result.status}" for key, result in eligibility.items()),
                "location_count": len(locations),
            }
        )


def export_session_json(path: Path, selected_programs: list[str], user_data: dict[str, object], eligibility: dict[str, ProgramResult], locations: list[dict[str, object]], radius: str) -> None:
    payload = {
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "selected_programs": selected_programs,
        "user_data": user_data,
        "eligibility": {key: result.__dict__ for key, result in eligibility.items()},
        "locations": [
            {
                "name": item["location"].get("name"),
                "address": item["location"].get("address"),
                "programs": item["programs"],
                "distance_text": item["distance_text"],
            }
            for item in locations[:20]
        ],
        "radius_miles": radius,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def build_draft_application(selected_programs: list[str], user_data: dict[str, object], eligibility: dict[str, ProgramResult], locations: list[dict[str, object]], radius: str) -> str:
    applicant = html.escape(str(user_data.get("applicant_name") or "Applicant"))
    rows = []
    for key in selected_programs:
        result = eligibility[key]
        docs = "".join(f"<li>{html.escape(item)}</li>" for item in PROGRAM_CHECKLISTS.get(key, []))
        passed = "".join(f"<li>{html.escape(item)}</li>" for item in result.passed)
        missed = "".join(f"<li>{html.escape(item)}</li>" for item in result.missed)
        rows.append(
            f"<section><h2>{html.escape(PROGRAMS[key]['name'])}: {result.status}</h2>"
            f"<p>{html.escape(result.explanation)}</p><h3>Rules met</h3><ul>{passed}</ul>"
            f"<h3>Needs review</h3><ul>{missed}</ul><h3>Bring</h3><ul>{docs}</ul></section>"
        )
    office_rows = []
    for item in locations[:10]:
        loc = item["location"]
        office_rows.append(f"<li><strong>{html.escape(str(loc.get('name', 'Office')))}</strong><br>{html.escape(str(loc.get('address', '')))} ({item['distance_text']})</li>")
    offices = "<ul>" + "".join(office_rows) + "</ul>" if office_rows else "<p>No nearby offices found.</p>"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Benefit Bridge preparation aid</title>
  <style>
    body {{ font-family: Helvetica, Arial, sans-serif; max-width: 840px; margin: 40px auto; line-height: 1.5; color: #172033; }}
    header, section {{ border: 1px solid #d8dee9; border-radius: 10px; padding: 20px; margin-bottom: 18px; }}
    header {{ background: #0f172a; color: white; }}
    h1, h2, h3 {{ margin-top: 0; }}
  </style>
</head>
<body>
  <header>
    <h1>{applicant}'s preparation aid</h1>
    <p>Generated {datetime.now().strftime('%B %d, %Y at %I:%M %p')} for offices within {html.escape(radius)} miles.</p>
  </header>
  <section>
    <h2>Household profile</h2>
    <p>Income: {format_money(float(user_data['monthly_income']))}/month. Household size: {user_data['household_size']}. Location: {html.escape(str(user_data.get('location_input', '')))}.</p>
  </section>
  {''.join(rows)}
  <section><h2>Nearby offices</h2>{offices}</section>
</body>
</html>"""


class BenefitBridgeApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Benefit Bridge")
        self.geometry("1120x760")
        self.minsize(980, 640)
        self.configure(bg=APP_BG)

        self.selected_programs: list[str] = []
        self.user_data: dict[str, object] = {}
        self.eligibility: dict[str, ProgramResult] = {}
        self.location_results: list[dict[str, object]] = []

        self.program_vars = {key: tk.BooleanVar(value=key in {"food", "utility", "internet"}) for key in PROGRAMS}
        self.name_var = tk.StringVar()
        self.income_var = tk.StringVar(value="3200")
        self.income_period_var = tk.StringVar(value="Monthly")
        self.household_var = tk.IntVar(value=3)
        self.state_var = tk.StringVar(value="California")
        self.location_var = tk.StringVar(value="95110")
        self.age_var = tk.StringVar(value="Adult")
        self.employment_var = tk.StringVar(value=EMPLOYMENT_OPTIONS[0])
        self.resident_var = tk.BooleanVar(value=True)
        self.healthy_food_var = tk.BooleanVar(value=True)
        self.child_under_13_var = tk.BooleanVar(value=True)
        self.child_under_5_var = tk.BooleanVar(value=False)
        self.pregnant_var = tk.BooleanVar(value=False)
        self.postpartum_var = tk.BooleanVar(value=False)
        self.breastfeeding_var = tk.BooleanVar(value=False)
        self.utility_hardship_var = tk.BooleanVar(value=False)
        self.internet_need_var = tk.BooleanVar(value=True)
        self.transportation_need_var = tk.BooleanVar(value=False)
        self.radius_var = tk.StringVar(value="10")
        self.office_search_var = tk.StringVar()

        self._configure_styles()
        self._build()

    def _configure_styles(self) -> None:
        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass
        self.style.configure("TFrame", background=APP_BG)
        self.style.configure("Header.TFrame", background=HEADER_BG)
        self.style.configure("Card.TFrame", background=CARD_BG)
        self.style.configure("TLabel", background=APP_BG, foreground=TEXT, font=("Helvetica", 11))
        self.style.configure("HeaderTitle.TLabel", background=HEADER_BG, foreground=TEXT, font=("Helvetica", 26, "bold"))
        self.style.configure("HeaderSub.TLabel", background=HEADER_BG, foreground=MUTED, font=("Helvetica", 10))
        self.style.configure("Card.TLabel", background=CARD_BG, foreground=SUBTEXT, font=("Helvetica", 10))
        self.style.configure("CardTitle.TLabel", background=CARD_BG, foreground=TEXT, font=("Helvetica", 11, "bold"))
        self.style.configure("Accent.TLabel", background=CARD_BG, foreground=ACCENT, font=("Helvetica", 10, "bold"))
        self.style.configure("TCheckbutton", background=CARD_BG, foreground=TEXT, font=("Helvetica", 10))
        self.style.map("TCheckbutton", background=[("active", CARD_BG_HOVER)], foreground=[("active", TEXT)])
        self.style.configure("TLabelframe", background=CARD_BG, foreground=TEXT, bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER, relief="solid")
        self.style.configure("TLabelframe.Label", background=CARD_BG, foreground=TEXT, font=("Helvetica", 11, "bold"))
        self.style.configure("TButton", padding=(12, 8), font=("Helvetica", 10, "bold"))
        self.style.configure("Primary.TButton", background=PRIMARY, foreground="#f8fafc", borderwidth=0)
        self.style.map("Primary.TButton", background=[("active", PRIMARY_HOVER), ("pressed", PRIMARY_HOVER)])
        self.style.configure("Accent.TButton", background="#0c4a6e", foreground=ACCENT, borderwidth=0)
        self.style.map("Accent.TButton", background=[("active", "#075985"), ("pressed", "#075985")])
        self.style.configure("TEntry", fieldbackground=INPUT_BG, foreground=TEXT, bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER)
        self.style.configure("TSpinbox", fieldbackground=INPUT_BG, foreground=TEXT, bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER)
        self.style.configure("TCombobox", fieldbackground=INPUT_BG, background=INPUT_BG, foreground=TEXT, arrowcolor=MUTED, bordercolor=BORDER)
        self.style.map("TCombobox", fieldbackground=[("readonly", INPUT_BG)], foreground=[("readonly", TEXT)])

    def _build(self) -> None:
        root = ttk.Frame(self, padding=16)
        root.pack(fill="both", expand=True)
        root.columnconfigure(0, weight=0)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(1, weight=1)

        header = ttk.Frame(root, style="Header.TFrame", padding=(16, 12))
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        title_stack = ttk.Frame(header, style="Header.TFrame")
        title_stack.pack(side="left")
        ttk.Label(title_stack, text="Benefit Bridge", style="HeaderTitle.TLabel").pack(anchor="w")
        ttk.Label(title_stack, text="You're Closer Than You Think", style="HeaderSub.TLabel").pack(anchor="w")
        ttk.Button(header, text="Load draft", command=self.load_draft).pack(side="right")
        ttk.Button(header, text="Save draft", command=self.save_draft).pack(side="right", padx=(0, 8))
        ttk.Button(header, text="Export JSON", command=self.export_json, style="Accent.TButton").pack(side="right", padx=(0, 8))
        ttk.Button(header, text="Print aid", command=self.open_printable, style="Accent.TButton").pack(side="right", padx=(0, 8))

        form = ttk.LabelFrame(root, text="Profile and programs", padding=12)
        form.grid(row=1, column=0, sticky="ns", padx=(0, 12))

        ttk.Label(form, text="Programs", style="CardTitle.TLabel").pack(anchor="w")
        for key, info in PROGRAMS.items():
            ttk.Checkbutton(form, text=info["name"], variable=self.program_vars[key]).pack(anchor="w", pady=1)

        fields = [
            ("Name", ttk.Entry(form, textvariable=self.name_var, width=28)),
            ("Income", ttk.Entry(form, textvariable=self.income_var, width=28)),
            ("Income period", ttk.Combobox(form, textvariable=self.income_period_var, values=["Monthly", "Yearly"], state="readonly", width=25)),
            ("Household size", ttk.Spinbox(form, from_=1, to=15, textvariable=self.household_var, width=8)),
            ("State", ttk.Combobox(form, textvariable=self.state_var, values=STATE_OPTIONS, state="readonly", width=25)),
            ("ZIP or city", ttk.Entry(form, textvariable=self.location_var, width=28)),
            ("Age range", ttk.Combobox(form, textvariable=self.age_var, values=["Child", "Adult", "Senior"], state="readonly", width=25)),
            ("Employment", ttk.Combobox(form, textvariable=self.employment_var, values=EMPLOYMENT_OPTIONS, state="readonly", width=25)),
            ("Radius", ttk.Combobox(form, textvariable=self.radius_var, values=RADIUS_OPTIONS, state="readonly", width=8)),
        ]
        for label, widget in fields:
            ttk.Label(form, text=label, style="Card.TLabel").pack(anchor="w", pady=(8, 2))
            widget.pack(anchor="w", fill="x")

        for label, variable in [
            ("US resident or qualified non-citizen", self.resident_var),
            ("Nutrition-focused food need", self.healthy_food_var),
            ("Child under age 13", self.child_under_13_var),
            ("Child under age 5", self.child_under_5_var),
            ("Pregnant", self.pregnant_var),
            ("Postpartum", self.postpartum_var),
            ("Breastfeeding", self.breastfeeding_var),
            ("Behind on utility bill", self.utility_hardship_var),
            ("Need home internet", self.internet_need_var),
            ("Need transportation", self.transportation_need_var),
        ]:
            ttk.Checkbutton(form, text=label, variable=variable).pack(anchor="w", pady=1)

        ttk.Button(form, text="Check eligibility", command=self.run_check, style="Primary.TButton").pack(fill="x", pady=(14, 0))
        ttk.Button(form, text="Save CSV history", command=self.save_history).pack(fill="x", pady=(6, 0))

        main = ttk.Frame(root)
        main.grid(row=1, column=1, sticky="nsew")
        main.rowconfigure(0, weight=2)
        main.rowconfigure(1, weight=1)
        main.columnconfigure(0, weight=1)

        results_box = ttk.LabelFrame(main, text="Eligibility detail", padding=10)
        results_box.grid(row=0, column=0, sticky="nsew")
        results_box.rowconfigure(0, weight=1)
        results_box.columnconfigure(0, weight=1)
        self.results_text = tk.Text(
            results_box,
            wrap="word",
            padx=14,
            pady=14,
            bg=CARD_BG,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER,
            font=("Helvetica", 11),
        )
        self.results_text.grid(row=0, column=0, sticky="nsew")
        self.results_text.insert("1.0", "Run a check to see eligibility results.")
        self.results_text.config(state="disabled")

        office_box = ttk.LabelFrame(main, text="Nearby offices", padding=10)
        office_box.grid(row=1, column=0, sticky="nsew", pady=(12, 0))
        office_box.rowconfigure(1, weight=1)
        office_box.columnconfigure(0, weight=1)
        search_row = ttk.Frame(office_box)
        search_row.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(search_row, text="Search", style="Card.TLabel").pack(side="left")
        search_entry = ttk.Entry(search_row, textvariable=self.office_search_var)
        search_entry.pack(side="left", fill="x", expand=True, padx=(8, 8))
        ttk.Button(search_row, text="Apply", command=self.refresh_office_list, style="Accent.TButton").pack(side="left")
        self.office_list = tk.Listbox(office_box, height=8)
        self.office_list.configure(
            bg=CARD_BG,
            fg=TEXT,
            selectbackground="#0c4a6e",
            selectforeground="#f8fafc",
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER,
            activestyle="none",
            font=("Helvetica", 11),
        )
        self.office_list.grid(row=1, column=0, sticky="nsew")
        self.office_list.bind("<Double-Button-1>", self.open_selected_office)

    def collect_user_data(self) -> dict[str, object]:
        income = parse_money(self.income_var.get())
        if self.income_period_var.get() == "Yearly":
            income = income / 12
        household_size = int(self.household_var.get())
        if household_size < 1:
            raise ValueError("Household size must be at least 1.")
        location_input = self.location_var.get().strip()
        return {
            "applicant_name": self.name_var.get().strip(),
            "monthly_income": income,
            "household_size": household_size,
            "state": self.state_var.get(),
            "location_input": location_input,
            "zip": extract_zip(location_input),
            "city": extract_city(location_input),
            "age_range": self.age_var.get(),
            "employment_status": self.employment_var.get(),
            "resident": self.resident_var.get(),
            "healthy_food": self.healthy_food_var.get(),
            "child_under_13": self.child_under_13_var.get(),
            "child_under_5": self.child_under_5_var.get(),
            "pregnant": self.pregnant_var.get(),
            "postpartum": self.postpartum_var.get(),
            "breastfeeding": self.breastfeeding_var.get(),
            "utility_hardship": self.utility_hardship_var.get(),
            "internet_need": self.internet_need_var.get(),
            "transportation_need": self.transportation_need_var.get(),
        }

    def run_check(self) -> None:
        self.selected_programs = [key for key, var in self.program_vars.items() if var.get()]
        if not self.selected_programs:
            messagebox.showwarning("Choose programs", "Select at least one program.")
            return
        try:
            self.user_data = self.collect_user_data()
            radius = float(self.radius_var.get())
        except ValueError as exc:
            messagebox.showerror("Check form", str(exc))
            return
        self.eligibility = compute_eligibility(self.selected_programs, self.user_data)
        self.location_results = find_locations(self.user_data, self.eligibility, radius)
        self.show_results()
        self.refresh_office_list()

    def show_results(self) -> None:
        lines: list[str] = []
        for key in self.selected_programs:
            result = self.eligibility[key]
            lines.append(f"{PROGRAMS[key]['name']}: {result.status}")
            lines.append(result.explanation)
            if result.passed:
                lines.append("Rules met:")
                lines.extend(f"- {item}" for item in result.passed)
            if result.missed:
                lines.append("Needs review:")
                lines.extend(f"- {item}" for item in result.missed)
            docs = ", ".join(PROGRAM_CHECKLISTS.get(key, []))
            lines.append(f"Bring: {docs}")
            lines.append("")
        self.results_text.config(state="normal")
        self.results_text.delete("1.0", "end")
        self.results_text.insert("1.0", "\n".join(lines).strip() or "No results yet.")
        self.results_text.config(state="disabled")

    def refresh_office_list(self) -> None:
        self.office_list.delete(0, "end")
        query = self.office_search_var.get().strip().lower()
        for item in self.location_results:
            loc = item["location"]
            haystack = " ".join(str(loc.get(part, "")) for part in ("name", "address", "city", "zip")).lower()
            if query and query not in haystack:
                continue
            program_names = ", ".join(PROGRAMS[key]["short"] for key in item["programs"])
            self.office_list.insert("end", f"{loc.get('name')} - {item['distance_text']} - {program_names}")

    def open_selected_office(self, _event=None) -> None:
        index = self.office_list.curselection()
        if not index:
            return
        text = self.office_list.get(index[0])
        for item in self.location_results:
            loc = item["location"]
            if str(loc.get("name")) in text:
                query = quote_plus(str(loc.get("address", "")))
                webbrowser.open(f"https://www.google.com/maps/search/?api=1&query={query}")
                return

    def save_history(self) -> None:
        if not self.eligibility:
            self.run_check()
            if not self.eligibility:
                return
        append_history(self.selected_programs, self.user_data, self.eligibility, self.location_results, self.radius_var.get())
        messagebox.showinfo("Saved", f"History saved to {HISTORY_FILE.name}.")

    def save_draft(self) -> None:
        payload = {
            "programs": {key: var.get() for key, var in self.program_vars.items()},
            "fields": {
                "name": self.name_var.get(),
                "income": self.income_var.get(),
                "income_period": self.income_period_var.get(),
                "household": self.household_var.get(),
                "state": self.state_var.get(),
                "location": self.location_var.get(),
                "age": self.age_var.get(),
                "employment": self.employment_var.get(),
                "resident": self.resident_var.get(),
                "healthy_food": self.healthy_food_var.get(),
                "child_under_13": self.child_under_13_var.get(),
                "child_under_5": self.child_under_5_var.get(),
                "pregnant": self.pregnant_var.get(),
                "postpartum": self.postpartum_var.get(),
                "breastfeeding": self.breastfeeding_var.get(),
                "utility_hardship": self.utility_hardship_var.get(),
                "internet_need": self.internet_need_var.get(),
                "transportation_need": self.transportation_need_var.get(),
                "radius": self.radius_var.get(),
            },
        }
        DRAFT_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        messagebox.showinfo("Draft saved", f"Draft saved to {DRAFT_FILE.name}.")

    def load_draft(self) -> None:
        if not DRAFT_FILE.exists():
            messagebox.showinfo("No draft", "No saved draft was found.")
            return
        payload = json.loads(DRAFT_FILE.read_text(encoding="utf-8"))
        for key, value in payload.get("programs", {}).items():
            if key in self.program_vars:
                self.program_vars[key].set(bool(value))
        fields = payload.get("fields", {})
        self.name_var.set(fields.get("name", ""))
        self.income_var.set(fields.get("income", ""))
        self.income_period_var.set(fields.get("income_period", "Monthly"))
        self.household_var.set(int(fields.get("household", 3)))
        self.state_var.set(fields.get("state", "California"))
        self.location_var.set(fields.get("location", ""))
        self.age_var.set(fields.get("age", "Adult"))
        self.employment_var.set(fields.get("employment", EMPLOYMENT_OPTIONS[0]))
        self.resident_var.set(bool(fields.get("resident", True)))
        self.healthy_food_var.set(bool(fields.get("healthy_food", True)))
        self.child_under_13_var.set(bool(fields.get("child_under_13", True)))
        self.child_under_5_var.set(bool(fields.get("child_under_5", False)))
        self.pregnant_var.set(bool(fields.get("pregnant", False)))
        self.postpartum_var.set(bool(fields.get("postpartum", False)))
        self.breastfeeding_var.set(bool(fields.get("breastfeeding", False)))
        self.utility_hardship_var.set(bool(fields.get("utility_hardship", False)))
        self.internet_need_var.set(bool(fields.get("internet_need", True)))
        self.transportation_need_var.set(bool(fields.get("transportation_need", False)))
        self.radius_var.set(fields.get("radius", "10"))

    def export_json(self) -> None:
        if not self.eligibility:
            self.run_check()
            if not self.eligibility:
                return
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        path = filedialog.asksaveasfilename(
            title="Export session",
            initialdir=str(EXPORT_DIR),
            initialfile=f"benefit_bridge_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
        )
        if not path:
            return
        export_session_json(Path(path), self.selected_programs, self.user_data, self.eligibility, self.location_results, self.radius_var.get())
        messagebox.showinfo("Exported", "Session exported.")

    def open_printable(self) -> None:
        if not self.eligibility:
            self.run_check()
            if not self.eligibility:
                return
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        path = EXPORT_DIR / f"benefit_bridge_print_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        html_text = build_draft_application(self.selected_programs, self.user_data, self.eligibility, self.location_results, self.radius_var.get())
        path.write_text(html_text, encoding="utf-8")
        webbrowser.open(path.as_uri())


if __name__ == "__main__":
    app = BenefitBridgeApp()
    app.mainloop()
