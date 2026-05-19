from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import csv
import json
import math
import os
import sys
import tkinter as tk
from tkinter import messagebox, ttk


def resource_path(relative_path: str) -> str:
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


APP_DIR = Path(resource_path("."))
CASE_HISTORY_FILE = APP_DIR / "benefit_bridge_v3_case_history.csv"
DRAFT_FILE = APP_DIR / "benefit_bridge_v3_draft.json"

PROGRAMS = {
    "childcare": {
        "name": "Child-care subsidy",
        "short_name": "Child care",
        "description": "Help paying for licensed care while a parent works or studies.",
    },
    "food": {
        "name": "Food assistance / SNAP-like program",
        "short_name": "Food",
        "description": "Monthly grocery support for households under income limits.",
    },
    "utility": {
        "name": "Utility bill help",
        "short_name": "Utilities",
        "description": "Energy, water, or emergency bill support.",
    },
    "internet": {
        "name": "Internet subsidy",
        "short_name": "Internet",
        "description": "Low-cost internet or digital access support.",
    },
    "transportation": {
        "name": "Other: transportation vouchers",
        "short_name": "Transport",
        "description": "Transit passes or rides for work, school, or medical needs.",
    },
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

SNAP_STATE_MULTIPLIERS = {"California": 2.0, "Texas": 1.65, "New York": 2.0}
EXTRA_PERSON_AMOUNT = 473
EMPLOYMENT_OPTIONS = ["Working", "In school or job training", "Working and in school", "Looking for work", "Not working or in school", "Retired"]
AGE_OPTIONS = ["Child", "Adult", "Senior"]
STATE_OPTIONS = list(STATE_LIMITS)

PROGRAM_CHECKLISTS = {
    "childcare": ["Photo ID for parent or guardian", "Proof of income", "Proof of work, school, or training schedule", "Child birth certificate or school enrollment"],
    "food": ["Photo ID for applicant", "Proof of household income", "Rent or mortgage statement if requested", "Utility bill showing address"],
    "utility": ["Past-due bill or shutoff notice", "Photo ID", "Proof of income", "Lease or document showing service address"],
    "internet": ["Photo ID", "Proof of income or participation in another aid program", "Statement of need"],
    "transportation": ["Photo ID", "Appointment letter, employer letter, or class schedule", "Proof of income"],
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
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


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


def limit_for_household(table: dict[int, int | float], household_size: int) -> int:
    if household_size in table:
        return int(table[household_size])
    largest = max(table)
    return int(table[largest] + (household_size - largest) * EXTRA_PERSON_AMOUNT)


def income_check(income: float, limit: float, label: str) -> RuleCheck:
    return RuleCheck(
        "Income",
        income <= limit,
        f"{label}: {format_money(income)} monthly is at or below {format_money(limit)}.",
        f"Income is above the limit: {format_money(income)} monthly vs. {format_money(limit)}.",
        close=income <= limit * 1.15,
    )


def compute_eligibility(selected_programs: list[str], user_data: dict[str, object]) -> dict[str, ProgramResult]:
    state = str(user_data.get("state", "California"))
    limits = STATE_LIMITS.get(state, STATE_LIMITS["California"])
    results: dict[str, ProgramResult] = {}

    for program_key in selected_programs:
        if program_key == "food":
            results[program_key] = food_eligibility(user_data, state)
            continue
        if program_key == "utility":
            state_limit = limit_for_household(limits["utility"], int(user_data["household_size"]))
            fpl_floor = limit_for_household(FPL_150_LIMITS, int(user_data["household_size"]))
            limit = max(state_limit, fpl_floor)
        else:
            limit = limit_for_household(limits[program_key], int(user_data["household_size"]))
        checks = [income_check(float(user_data["monthly_income"]), limit, f"Income is within the {PROGRAMS[program_key]['short_name']} limit")]

        if program_key == "childcare":
            checks.extend(
                [
                    RuleCheck("Parent activity", str(user_data.get("employment_status")) in {"Working", "In school or job training", "Working and in school"}, "Parent or caregiver is working, in school, or in job training.", "Child-care programs usually require a parent to work, study, or train.", close=str(user_data.get("employment_status")) == "Looking for work"),
                    RuleCheck("Child age", bool(user_data.get("child_under_13")), "A child in the household is under age 13.", "This child-care subsidy is focused on children under age 13.", critical=True),
                ]
            )
        elif program_key == "utility":
            checks.extend(
                [
                    RuleCheck("Bill hardship", bool(user_data.get("utility_hardship")), "Household reports utility bill hardship.", "Utility bill help is often prioritized for shutoff notices or past-due bills."),
                    RuleCheck("Residency", bool(user_data.get("resident")), "Household meets the residency condition.", "Many utility programs require local residency or qualified status.", critical=True),
                ]
            )
        elif program_key == "internet":
            checks.extend(
                [
                    RuleCheck("Internet need", bool(user_data.get("internet_need")), "Household reports a need for home internet access.", "The internet subsidy expects a work, school, health, or benefits need."),
                    RuleCheck("Residency", bool(user_data.get("resident")), "Household meets the residency condition.", "Internet subsidies may require local residency or qualified status.", critical=True),
                ]
            )
        elif program_key == "transportation":
            active = str(user_data.get("employment_status")) in {"Working", "In school or job training", "Working and in school", "Looking for work"} or str(user_data.get("age_range")) == "Senior"
            checks.extend(
                [
                    RuleCheck("Transportation need", bool(user_data.get("transportation_need")), "Household reports a transportation need.", "Voucher programs usually require a work, school, or medical transportation need."),
                    RuleCheck("Activity", active, "Applicant has a work, school, job-search, or senior mobility reason.", "Transportation vouchers usually need a work, school, job-search, medical, or senior mobility reason.", close=str(user_data.get("employment_status")) == "Retired"),
                ]
            )
        results[program_key] = classify_program(program_key, checks)
    return results


def food_eligibility(user_data: dict[str, object], state: str) -> ProgramResult:
    household_size = int(user_data["household_size"])
    income = float(user_data["monthly_income"])
    fpl_100 = limit_for_household(FPL_BASE_LIMITS, household_size)
    snap_multiplier = SNAP_STATE_MULTIPLIERS.get(state, 2.0)
    snap_limit = fpl_100 * snap_multiplier
    wic_limit = fpl_100 * 1.85
    has_wic_path = bool(user_data.get("child_under_5") or user_data.get("pregnant") or user_data.get("postpartum") or user_data.get("breastfeeding"))

    if not user_data.get("resident"):
        return ProgramResult("Unlikely", "Food assistance often requires US residency or qualified non-citizen status.", [], ["Food assistance often requires US residency or qualified non-citizen status."])

    snap_ok = income <= snap_limit
    wic_ok = has_wic_path and income <= wic_limit
    if snap_ok or wic_ok:
        programs = []
        if snap_ok:
            programs.append(f"SNAP ({int(snap_multiplier * 100)}% limit)")
        if wic_ok:
            programs.append("WIC (185% limit)")
        label = " and ".join(programs)
        return ProgramResult("Highly eligible", f"Eligible for {label}.", [f"Income qualifies for {label}: {format_money(income)}/month.", "Household meets the residency condition."], [])

    close = income <= snap_limit * 1.15 or (has_wic_path and income <= wic_limit * 1.15)
    reason = f"Income is above the food assistance limit: {format_money(income)} monthly vs. {format_money(snap_limit)}."
    return ProgramResult("Partially eligible" if close else "Unlikely", f"You may not qualify for food assistance because {reason}", ["Household meets the residency condition."], [reason])


def classify_program(program_key: str, checks: list[RuleCheck]) -> ProgramResult:
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

    program_name = PROGRAMS[program_key]["short_name"].lower()
    if status == "Highly eligible":
        explanation = f"You likely qualify for {program_name} because the current rules are met."
    elif status == "Partially eligible":
        explanation = f"You may qualify for {program_name}, but one or two details need review."
    else:
        explanation = f"You may not qualify for {program_name} based on this estimate."
    return ProgramResult(status, explanation, passed, missed)


def find_locations(user_data: dict[str, object], eligibility: dict[str, ProgramResult]) -> list[dict[str, object]]:
    location_input = str(user_data.get("location_input", "")).strip().lower()
    if not location_input:
        return []
    eligible_programs = {key for key, result in eligibility.items() if result.status in {"Highly eligible", "Partially eligible"}}
    results: list[dict[str, object]] = []

    for location in LOCATIONS:
        matching_programs = [key for key in location.get("programs", []) if key in eligible_programs]
        if not matching_programs:
            continue
        city = str(location.get("city", "")).lower()
        zip_code = str(location.get("zip", "")).lower()
        address = str(location.get("address", "")).lower()
        if city and city in location_input or zip_code and zip_code in location_input or location_input in address:
            results.append({"location": location, "programs": matching_programs, "distance_text": "nearby"})

    results.sort(key=lambda item: str(item["location"].get("name", "")).lower())
    return results


def append_case_history(selected_programs: list[str], user_data: dict[str, object], eligibility: dict[str, ProgramResult], locations: list[dict[str, object]]) -> None:
    file_exists = CASE_HISTORY_FILE.exists()
    with CASE_HISTORY_FILE.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["timestamp", "selected_programs", "monthly_income", "household_size", "location", "eligibility", "location_count"],
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
                "eligibility": "; ".join(f"{key}: {result.status}" for key, result in eligibility.items()),
                "location_count": len(locations),
            }
        )


class BenefitBridgeApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Benefit Bridge")
        self.geometry("1040x740")
        self.minsize(900, 620)
        self.configure(bg=APP_BG)

        self.selected_programs: list[str] = []
        self.user_data: dict[str, object] = {}
        self.eligibility: dict[str, ProgramResult] = {}
        self.location_results: list[dict[str, object]] = []
        self.current_step = 0

        self.program_vars = {key: tk.BooleanVar(value=False) for key in PROGRAMS}
        self.name_var = tk.StringVar()
        self.income_var = tk.StringVar()
        self.income_period_var = tk.StringVar(value="Monthly")
        self.household_var = tk.IntVar(value=3)
        self.state_var = tk.StringVar(value="California")
        self.location_var = tk.StringVar()
        self.age_var = tk.StringVar(value="Adult")
        self.employment_var = tk.StringVar(value=EMPLOYMENT_OPTIONS[0])
        self.resident_var = tk.BooleanVar(value=True)
        self.child_under_13_var = tk.BooleanVar(value=True)
        self.child_under_5_var = tk.BooleanVar(value=False)
        self.pregnant_var = tk.BooleanVar(value=False)
        self.postpartum_var = tk.BooleanVar(value=False)
        self.breastfeeding_var = tk.BooleanVar(value=False)
        self.utility_hardship_var = tk.BooleanVar(value=False)
        self.internet_need_var = tk.BooleanVar(value=True)
        self.transportation_need_var = tk.BooleanVar(value=False)

        self._configure_styles()
        self._build_shell()
        self.show_step(0)

    def _configure_styles(self) -> None:
        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass
        self.style.configure("TFrame", background=APP_BG)
        self.style.configure("Header.TFrame", background=HEADER_BG)
        self.style.configure("Footer.TFrame", background=HEADER_BG)
        self.style.configure("Rail.TFrame", background=RAIL_BG)
        self.style.configure("Card.TFrame", background=CARD_BG)
        self.style.configure("TLabel", background=APP_BG, foreground=TEXT, font=("Helvetica", 11))
        self.style.configure("HeaderTitle.TLabel", background=HEADER_BG, foreground=TEXT, font=("Helvetica", 24, "bold"))
        self.style.configure("Step.TLabel", background=HEADER_BG, foreground=ACCENT, font=("Helvetica", 10, "bold"))
        self.style.configure("Heading.TLabel", background=APP_BG, foreground=TEXT, font=("Helvetica", 18, "bold"))
        self.style.configure("Muted.TLabel", background=APP_BG, foreground=MUTED, font=("Helvetica", 10))
        self.style.configure("Card.TLabel", background=CARD_BG, foreground=SUBTEXT, font=("Helvetica", 10))
        self.style.configure("CardTitle.TLabel", background=CARD_BG, foreground=TEXT, font=("Helvetica", 11, "bold"))
        self.style.configure("Status.TLabel", background=CARD_BG, foreground=ACCENT, font=("Helvetica", 10, "bold"))
        self.style.configure("TCheckbutton", background=CARD_BG, foreground=TEXT, font=("Helvetica", 10))
        self.style.map("TCheckbutton", background=[("active", CARD_BG_HOVER)], foreground=[("active", TEXT)])
        self.style.configure("TLabelframe", background=CARD_BG, foreground=TEXT, bordercolor=BORDER, relief="solid")
        self.style.configure("TLabelframe.Label", background=CARD_BG, foreground=TEXT, font=("Helvetica", 11, "bold"))
        self.style.configure("TButton", padding=(12, 8), font=("Helvetica", 10, "bold"))
        self.style.configure("Primary.TButton", background=PRIMARY, foreground="#f8fafc", borderwidth=0)
        self.style.map("Primary.TButton", background=[("active", PRIMARY_HOVER), ("pressed", PRIMARY_HOVER)])
        self.style.configure("TEntry", fieldbackground=INPUT_BG, foreground=TEXT, bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER)
        self.style.configure("TSpinbox", fieldbackground=INPUT_BG, foreground=TEXT, bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER)
        self.style.configure("TCombobox", fieldbackground=INPUT_BG, background=INPUT_BG, foreground=TEXT, arrowcolor=MUTED, bordercolor=BORDER)
        self.style.map("TCombobox", fieldbackground=[("readonly", INPUT_BG)], foreground=[("readonly", TEXT)])

    def _build_shell(self) -> None:
        self.root_frame = ttk.Frame(self, padding=18)
        self.root_frame.pack(fill="both", expand=True)
        self.root_frame.rowconfigure(1, weight=1)
        self.root_frame.columnconfigure(0, weight=1)

        header = ttk.Frame(self.root_frame, style="Header.TFrame", padding=(16, 12))
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        ttk.Label(header, text="Benefit Bridge", style="HeaderTitle.TLabel").pack(side="left")
        self.step_label = ttk.Label(header, text="", style="Step.TLabel")
        self.step_label.pack(side="right")

        self.content = ttk.Frame(self.root_frame)
        self.content.grid(row=1, column=0, sticky="nsew")

        footer = ttk.Frame(self.root_frame, style="Footer.TFrame", padding=(12, 10))
        footer.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        ttk.Button(footer, text="Save draft", command=self.save_draft).pack(side="left")
        ttk.Button(footer, text="Load draft", command=self.load_draft).pack(side="left", padx=(8, 0))
        self.back_button = ttk.Button(footer, text="Back", command=self.go_back)
        self.back_button.pack(side="right")
        self.next_button = ttk.Button(footer, text="Continue", command=self.go_next, style="Primary.TButton")
        self.next_button.pack(side="right", padx=(0, 8))

    def show_step(self, step: int) -> None:
        self.current_step = step
        for child in self.content.winfo_children():
            child.destroy()
        self.step_label.config(text=f"Step {step + 1} of 3")
        self.back_button.config(state="normal" if step > 0 else "disabled")
        self.next_button.config(text="Save CSV history" if step == 2 else "Continue")
        if step == 0:
            self._show_program_step()
        elif step == 1:
            self._show_profile_step()
        else:
            self._show_results_step()

    def _show_program_step(self) -> None:
        ttk.Label(self.content, text="Which type of subsidy?", style="Heading.TLabel").pack(anchor="w", pady=(0, 8))
        ttk.Label(self.content, text="Choose one or more programs.", style="Muted.TLabel").pack(anchor="w", pady=(0, 10))
        for key, program in PROGRAMS.items():
            row = ttk.Frame(self.content, style="Card.TFrame", padding=12)
            row.pack(fill="x", pady=3)
            ttk.Checkbutton(row, text=program["name"], variable=self.program_vars[key]).pack(anchor="w")
            ttk.Label(row, text=program["description"], style="Card.TLabel", wraplength=760).pack(anchor="w", padx=(22, 0))

    def _show_profile_step(self) -> None:
        ttk.Label(self.content, text="Household profile", style="Heading.TLabel").pack(anchor="w", pady=(0, 12))
        form = ttk.Frame(self.content, style="Card.TFrame", padding=16)
        form.pack(fill="both", expand=True)
        form.columnconfigure(1, weight=1)
        fields = [
            ("Name", ttk.Entry(form, textvariable=self.name_var)),
            ("Income", ttk.Entry(form, textvariable=self.income_var)),
            ("Income period", ttk.Combobox(form, textvariable=self.income_period_var, values=["Monthly", "Yearly"], state="readonly")),
            ("Household size", ttk.Spinbox(form, from_=1, to=15, textvariable=self.household_var)),
            ("State", ttk.Combobox(form, textvariable=self.state_var, values=STATE_OPTIONS, state="readonly")),
            ("ZIP code or city", ttk.Entry(form, textvariable=self.location_var)),
            ("Age range", ttk.Combobox(form, textvariable=self.age_var, values=AGE_OPTIONS, state="readonly")),
            ("Employment or school status", ttk.Combobox(form, textvariable=self.employment_var, values=EMPLOYMENT_OPTIONS, state="readonly")),
        ]
        for row, (label, widget) in enumerate(fields, start=1):
            ttk.Label(form, text=label, style="Card.TLabel").grid(row=row, column=0, sticky="w", pady=5, padx=(0, 12))
            widget.grid(row=row, column=1, sticky="ew", pady=5)

        checks = ttk.LabelFrame(form, text="Program-specific details", padding=10)
        checks.grid(row=len(fields) + 1, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        for label, variable in [
            ("US resident or qualified non-citizen", self.resident_var),
            ("A child in the household is under age 13", self.child_under_13_var),
            ("A child in the household is under age 5", self.child_under_5_var),
            ("Pregnant", self.pregnant_var),
            ("Postpartum", self.postpartum_var),
            ("Breastfeeding", self.breastfeeding_var),
            ("Behind on utility bill or received a shutoff notice", self.utility_hardship_var),
            ("Need home internet for work, school, health, or benefits", self.internet_need_var),
            ("Need transportation for work, school, or medical appointments", self.transportation_need_var),
        ]:
            ttk.Checkbutton(checks, text=label, variable=variable).pack(anchor="w", pady=2)

    def _show_results_step(self) -> None:
        frame = ttk.Frame(self.content)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=2)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(0, weight=1)

        result_box = tk.Text(
            frame,
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
        result_box.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        result_box.insert("1.0", self._result_text())
        result_box.config(state="disabled")

        office_frame = ttk.LabelFrame(frame, text="Nearby offices", padding=10)
        office_frame.grid(row=0, column=1, sticky="nsew")
        if not self.location_results:
            ttk.Label(office_frame, text="No matching offices found.", style="Card.TLabel").pack(anchor="w")
        for item in self.location_results[:12]:
            location = item["location"]
            programs = ", ".join(PROGRAMS[key]["short_name"] for key in item["programs"])
            office_card = ttk.Frame(office_frame, style="Card.TFrame", padding=8)
            office_card.pack(fill="x", pady=(0, 8))
            ttk.Label(office_card, text=str(location.get("name", "Office")), style="CardTitle.TLabel").pack(anchor="w", pady=(0, 2))
            ttk.Label(office_card, text=str(location.get("address", "")), style="Card.TLabel", wraplength=300).pack(anchor="w")
            ttk.Label(office_card, text=programs, style="Status.TLabel").pack(anchor="w", pady=(4, 0))

    def _result_text(self) -> str:
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
            lines.append("Visit checklist:")
            lines.extend(f"- {item}" for item in PROGRAM_CHECKLISTS.get(key, []))
            lines.append("")
        return "\n".join(lines).strip()

    def go_next(self) -> None:
        if self.current_step == 0:
            self.selected_programs = [key for key, variable in self.program_vars.items() if variable.get()]
            if not self.selected_programs:
                messagebox.showwarning("Choose programs", "Select at least one program.")
                return
            self.show_step(1)
        elif self.current_step == 1:
            try:
                self.user_data = self.collect_user_data()
            except ValueError as exc:
                messagebox.showerror("Check form", str(exc))
                return
            self.eligibility = compute_eligibility(self.selected_programs, self.user_data)
            self.location_results = find_locations(self.user_data, self.eligibility)
            self.show_step(2)
        else:
            append_case_history(self.selected_programs, self.user_data, self.eligibility, self.location_results)
            messagebox.showinfo("Saved", f"History saved to {CASE_HISTORY_FILE.name}.")

    def go_back(self) -> None:
        if self.current_step > 0:
            self.show_step(self.current_step - 1)

    def collect_user_data(self) -> dict[str, object]:
        income = parse_money(self.income_var.get())
        if self.income_period_var.get() == "Yearly":
            income = income / 12
        household_size = int(self.household_var.get())
        if household_size < 1:
            raise ValueError("Household size must be at least 1.")
        return {
            "applicant_name": self.name_var.get().strip(),
            "monthly_income": income,
            "household_size": household_size,
            "state": self.state_var.get(),
            "location_input": self.location_var.get().strip(),
            "age_range": self.age_var.get(),
            "employment_status": self.employment_var.get(),
            "resident": self.resident_var.get(),
            "child_under_13": self.child_under_13_var.get(),
            "child_under_5": self.child_under_5_var.get(),
            "pregnant": self.pregnant_var.get(),
            "postpartum": self.postpartum_var.get(),
            "breastfeeding": self.breastfeeding_var.get(),
            "utility_hardship": self.utility_hardship_var.get(),
            "internet_need": self.internet_need_var.get(),
            "transportation_need": self.transportation_need_var.get(),
        }

    def save_draft(self) -> None:
        payload = {
            "programs": {key: variable.get() for key, variable in self.program_vars.items()},
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
                "child_under_13": self.child_under_13_var.get(),
                "child_under_5": self.child_under_5_var.get(),
                "pregnant": self.pregnant_var.get(),
                "postpartum": self.postpartum_var.get(),
                "breastfeeding": self.breastfeeding_var.get(),
                "utility_hardship": self.utility_hardship_var.get(),
                "internet_need": self.internet_need_var.get(),
                "transportation_need": self.transportation_need_var.get(),
            },
        }
        DRAFT_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        messagebox.showinfo("Draft saved", f"Draft saved to {DRAFT_FILE.name}.")

    def load_draft(self) -> None:
        if not DRAFT_FILE.exists():
            messagebox.showinfo("No draft", "No saved draft was found.")
            return
        try:
            payload = json.loads(DRAFT_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            messagebox.showerror("Draft error", "The saved draft could not be read.")
            return
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
        self.child_under_13_var.set(bool(fields.get("child_under_13", True)))
        self.child_under_5_var.set(bool(fields.get("child_under_5", False)))
        self.pregnant_var.set(bool(fields.get("pregnant", False)))
        self.postpartum_var.set(bool(fields.get("postpartum", False)))
        self.breastfeeding_var.set(bool(fields.get("breastfeeding", False)))
        self.utility_hardship_var.set(bool(fields.get("utility_hardship", False)))
        self.internet_need_var.set(bool(fields.get("internet_need", True)))
        self.transportation_need_var.set(bool(fields.get("transportation_need", False)))
        self.show_step(0)


if __name__ == "__main__":
    app = BenefitBridgeApp()
    app.mainloop()
