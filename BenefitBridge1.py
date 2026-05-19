from __future__ import annotations

from dataclasses import dataclass
import math
import tkinter as tk
from tkinter import messagebox, ttk


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

STATE_LIMITS = {
    "California": {
        "childcare": {1: 4992, 2: 6232, 3: 7472, 4: 8712, 5: 9952, 6: 11192, 7: 12432, 8: 13672},
        "food": FPL_200_LIMITS,
        "utility": {1: 3459, 2: 4523, 3: 5587, 4: 6651, 5: 7715, 6: 8779, 7: 8979, 8: 9178},
        "internet": FPL_200_LIMITS,
        "transportation": {1: 2200, 2: 2980, 3: 3760, 4: 4550, 5: 5330, 6: 6120, 7: 6900, 8: 7690},
    }
}

EMPLOYMENT_OPTIONS = [
    "Working",
    "In school or job training",
    "Working and in school",
    "Looking for work",
    "Not working or in school",
]

EXTRA_PERSON_AMOUNT = 473

APP_BG = "#0a0e14"
CARD_BG = "#121826"
CARD_BG_HOVER = "#171d2e"
BORDER = "#2a3447"
TEXT = "#e8eef9"
MUTED = "#94a3b8"
PRIMARY = "#3b82f6"
PRIMARY_HOVER = "#2563eb"
INPUT_BG = "#1a2233"


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
        household_size = int(user_data["household_size"])
        income = float(user_data["monthly_income"])
        limit = limit_for_household(limits[program_key], household_size)
        checks = [income_check(income, limit, f"Income is within the {PROGRAMS[program_key]['short_name']} limit")]

        if program_key == "childcare":
            checks.append(
                RuleCheck(
                    "Parent activity",
                    str(user_data.get("employment_status")) in {"Working", "In school or job training", "Working and in school"},
                    "Parent or caregiver is working, in school, or in job training.",
                    "Child-care programs usually require a parent to work, study, or train.",
                    close=str(user_data.get("employment_status")) == "Looking for work",
                )
            )
            checks.append(
                RuleCheck(
                    "Child age",
                    bool(user_data.get("child_under_13")),
                    "A child in the household is under age 13.",
                    "This child-care subsidy is focused on children under age 13.",
                    critical=True,
                )
            )
        elif program_key in {"food", "utility", "internet"}:
            checks.append(
                RuleCheck(
                    "Residency",
                    bool(user_data.get("resident")),
                    "Household meets the residency condition.",
                    "This program usually requires US residency or qualified non-citizen status.",
                    critical=True,
                )
            )
        elif program_key == "transportation":
            checks.append(
                RuleCheck(
                    "Transportation need",
                    bool(user_data.get("transportation_need")),
                    "Household reports a transportation need.",
                    "Voucher programs usually require a work, school, or medical transportation need.",
                )
            )

        results[program_key] = classify_program(program_key, checks)

    return results


def classify_program(program_key: str, checks: list[RuleCheck]) -> ProgramResult:
    passed = [check.pass_text for check in checks if check.passed]
    missed = [check.fail_text for check in checks if not check.passed]
    failures = [check for check in checks if not check.passed]

    if not failures:
        status = "Highly eligible"
    elif any(check.critical for check in failures):
        status = "Unlikely"
    elif len(failures) == 1 or all(check.close for check in failures):
        status = "Partially eligible"
    else:
        status = "Unlikely"

    program_name = PROGRAMS[program_key]["short_name"].lower()
    if status == "Highly eligible":
        explanation = f"You likely qualify for {program_name} because the current rules are met."
    elif status == "Partially eligible":
        explanation = f"You may qualify for {program_name}, but one detail needs review."
    else:
        explanation = f"You may not qualify for {program_name} based on this estimate."
    return ProgramResult(status, explanation, passed, missed)


class BenefitBridgeApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Benefit Bridge")
        self.geometry("820x620")
        self.minsize(720, 520)
        self.configure(bg=APP_BG)

        self.program_vars = {key: tk.BooleanVar(value=False) for key in PROGRAMS}
        self.income_var = tk.StringVar()
        self.household_var = tk.IntVar(value=3)
        self.employment_var = tk.StringVar(value=EMPLOYMENT_OPTIONS[0])
        self.resident_var = tk.BooleanVar(value=True)
        self.child_under_13_var = tk.BooleanVar(value=True)
        self.transportation_need_var = tk.BooleanVar(value=False)

        self._configure_styles()
        self._build_ui()

    def _configure_styles(self) -> None:
        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass
        self.style.configure("TFrame", background=APP_BG)
        self.style.configure("Card.TFrame", background=CARD_BG, relief="flat")
        self.style.configure("TLabel", background=APP_BG, foreground=TEXT, font=("Helvetica", 11))
        self.style.configure("Title.TLabel", background=APP_BG, foreground=TEXT, font=("Helvetica", 24, "bold"))
        self.style.configure("Section.TLabel", background=CARD_BG, foreground=TEXT, font=("Helvetica", 13, "bold"))
        self.style.configure("Card.TLabel", background=CARD_BG, foreground=TEXT, font=("Helvetica", 10))
        self.style.configure("Muted.TLabel", background=APP_BG, foreground=MUTED, font=("Helvetica", 10))
        self.style.configure("TCheckbutton", background=CARD_BG, foreground=TEXT, font=("Helvetica", 10))
        self.style.map("TCheckbutton", background=[("active", CARD_BG_HOVER)], foreground=[("active", TEXT)])
        self.style.configure("TButton", padding=(12, 8), font=("Helvetica", 10, "bold"))
        self.style.configure("Primary.TButton", background=PRIMARY, foreground="#f8fafc", borderwidth=0)
        self.style.map("Primary.TButton", background=[("active", PRIMARY_HOVER), ("pressed", PRIMARY_HOVER)])
        self.style.configure("TEntry", fieldbackground=INPUT_BG, foreground=TEXT, bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER)
        self.style.configure("TSpinbox", fieldbackground=INPUT_BG, foreground=TEXT, bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER)
        self.style.configure("TCombobox", fieldbackground=INPUT_BG, background=INPUT_BG, foreground=TEXT, arrowcolor=MUTED, bordercolor=BORDER)
        self.style.map("TCombobox", fieldbackground=[("readonly", INPUT_BG)], foreground=[("readonly", TEXT)])

    def _build_ui(self) -> None:
        main = ttk.Frame(self, padding=18)
        main.pack(fill="both", expand=True)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(2, weight=1)

        ttk.Label(main, text="Benefit Bridge", style="Title.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 4))
        ttk.Label(main, text="You're Closer Than You Think", style="Muted.TLabel").grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 12))

        form = ttk.Frame(main, style="Card.TFrame", padding=14)
        form.grid(row=2, column=0, sticky="ns", padx=(0, 18))

        ttk.Label(form, text="Programs", style="Section.TLabel").pack(anchor="w", pady=(0, 4))
        for key, program in PROGRAMS.items():
            ttk.Checkbutton(form, text=program["name"], variable=self.program_vars[key]).pack(anchor="w", pady=2)

        ttk.Label(form, text="Monthly income", style="Card.TLabel").pack(anchor="w", pady=(16, 2))
        ttk.Entry(form, textvariable=self.income_var, width=28).pack(anchor="w", fill="x")

        ttk.Label(form, text="Household size", style="Card.TLabel").pack(anchor="w", pady=(10, 2))
        ttk.Spinbox(form, from_=1, to=15, textvariable=self.household_var, width=8).pack(anchor="w")

        ttk.Label(form, text="Employment or school status", style="Card.TLabel").pack(anchor="w", pady=(10, 2))
        ttk.Combobox(form, textvariable=self.employment_var, values=EMPLOYMENT_OPTIONS, state="readonly", width=26).pack(anchor="w", fill="x")

        ttk.Checkbutton(form, text="US resident or qualified non-citizen", variable=self.resident_var).pack(anchor="w", pady=(14, 2))
        ttk.Checkbutton(form, text="A child in the household is under age 13", variable=self.child_under_13_var).pack(anchor="w", pady=2)
        ttk.Checkbutton(form, text="Need transportation for work, school, or medical appointments", variable=self.transportation_need_var).pack(anchor="w", pady=2)

        ttk.Button(form, text="Check Eligibility", command=self.run_check, style="Primary.TButton").pack(fill="x", pady=(16, 0))

        output_frame = ttk.Frame(main, style="Card.TFrame", padding=10)
        output_frame.grid(row=2, column=1, sticky="nsew")
        output_frame.rowconfigure(0, weight=1)
        output_frame.columnconfigure(0, weight=1)

        self.results_text = tk.Text(
            output_frame,
            wrap="word",
            padx=12,
            pady=12,
            bg=CARD_BG,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER,
            font=("Helvetica", 11),
        )
        self.results_text.grid(row=0, column=0, sticky="nsew")
        self.results_text.insert("1.0", "Choose programs, enter a household profile, then run the eligibility check.")
        self.results_text.config(state="disabled")

    def collect_user_data(self) -> dict[str, object]:
        income = parse_money(self.income_var.get())
        household_size = int(self.household_var.get())
        if household_size < 1:
            raise ValueError("Household size must be at least 1.")
        return {
            "monthly_income": income,
            "household_size": household_size,
            "state": "California",
            "employment_status": self.employment_var.get(),
            "resident": self.resident_var.get(),
            "child_under_13": self.child_under_13_var.get(),
            "transportation_need": self.transportation_need_var.get(),
        }

    def run_check(self) -> None:
        selected = [key for key, variable in self.program_vars.items() if variable.get()]
        if not selected:
            messagebox.showwarning("Choose programs", "Select at least one program.")
            return
        try:
            user_data = self.collect_user_data()
        except ValueError as exc:
            messagebox.showerror("Check form", str(exc))
            return
        self.show_results(compute_eligibility(selected, user_data))

    def show_results(self, eligibility: dict[str, ProgramResult]) -> None:
        lines: list[str] = []
        for key, result in eligibility.items():
            lines.append(f"{PROGRAMS[key]['name']}: {result.status}")
            lines.append(result.explanation)
            if result.passed:
                lines.append("Rules met:")
                lines.extend(f"- {item}" for item in result.passed)
            if result.missed:
                lines.append("Needs review:")
                lines.extend(f"- {item}" for item in result.missed)
            lines.append("")
        self.results_text.config(state="normal")
        self.results_text.delete("1.0", "end")
        self.results_text.insert("1.0", "\n".join(lines).strip())
        self.results_text.config(state="disabled")


if __name__ == "__main__":
    app = BenefitBridgeApp()
    app.mainloop()
