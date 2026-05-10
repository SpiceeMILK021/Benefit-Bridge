

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
from zip_data import ZIP_COORDS, CITY_COORDS


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
FAVORITES_FILE = APP_DIR / "benefit_bridge_favorites.json"
EXPORT_DIR = APP_DIR / "exports"
BRAND_SLOGAN = "You're Closer Than You Think"

# Spanish translations keyed by English source text.
# Untranslated strings gracefully fall back to English.
SPANISH: dict[str, str] = {
    # Slogan / header
    "You're Closer Than You Think": "Estás más cerca de lo que crees",
    # Rail
    "Progress": "Progreso",
    "1. Choose subsidies": "1. Elegir subsidios",
    "2. Household profile": "2. Perfil del hogar",
    "3. Results & offices": "3. Resultados",
    "Sample rules only — always confirm with the office before applying.": "Solo reglas de muestra — confirme siempre con la oficina antes de solicitar.",
    # Nav buttons
    "Back": "Atrás",
    "Start over": "Comenzar de nuevo",
    "Save draft": "Guardar borrador",
    "Load draft": "Cargar borrador",
    "Continue": "Continuar",
    "Check Eligibility": "Verificar elegibilidad",
    "Draft Application": "Borrador de solicitud",
    # Step 0 — Program picker
    "Welcome": "Bienvenido",
    "Pick programs, answer one shared profile, then review eligibility, offices, and a printable packing list.": "Selecciona programas, responde un perfil y revisa elegibilidad, oficinas y lista de documentos.",
    "Smart reuse": "Reutilización inteligente",
    "One questionnaire powers every program you pick.": "Un cuestionario aplica a todos los programas que elijas.",
    "Office radar": "Radar de oficinas",
    "Distance-ranked sites — hundreds of demo ZIP codes statewide.": "Oficinas cercanas ordenadas por distancia.",
    "Audit trail": "Historial de auditoría",
    "CSV history + JSON export for handoff.": "Historial CSV + exportación JSON.",
    "Which type of subsidy?": "¿Qué tipo de subsidio?",
    "Choose one or more programs. Use Select all if you want a full scan.": "Elige uno o más programas.",
    "Select all": "Seleccionar todo",
    "Clear": "Limpiar",
    "Suggest common bundle": "Sugerir paquete común",
    # Program names and short names
    "Child-care subsidy": "Subsidio de cuidado infantil",
    "Child care": "Cuidado infantil",
    "Help paying for licensed care while a parent works or studies.": "Ayuda para pagar el cuidado mientras un padre trabaja o estudia.",
    "Food assistance / SNAP-like program": "Asistencia alimentaria / SNAP",
    "Food": "Alimentos",
    "Monthly grocery support for households under income limits.": "Apoyo mensual para víveres para hogares de bajos ingresos.",
    "Utility bill help": "Ayuda con servicios básicos",
    "Utilities": "Servicios",
    "Energy, water, or emergency bill support.": "Apoyo para facturas de energía, agua o emergencias.",
    "Internet subsidy": "Subsidio de internet",
    "Internet": "Internet",
    "Low-cost internet or digital access support.": "Apoyo para internet de bajo costo.",
    "Other: transportation vouchers": "Vales de transporte",
    "Transport": "Transporte",
    "Transit passes or rides for work, school, or medical needs.": "Pases de tránsito para trabajo, escuela o citas médicas.",
    # Estimator
    "Quick eligibility snapshot": "Resumen rápido de elegibilidad",
    "Typical income limits, family of 4": "Límites de ingresos para familia de 4",
    # Step 1 — Info screen
    "Household profile": "Perfil del hogar",
    "Answer once — every selected program reuses this profile. You can go back and edit before running the check.": "Responde una vez — cada programa seleccionado usa este perfil.",
    "Tip: enter any 5-digit ZIP from the expanded demo set (e.g. 95125, 94110, 90026, 92104, 95825, 93722, 92806) for distance math; cities still match by name.": "Consejo: ingresa un código postal de 5 dígitos para calcular distancias; las ciudades también funcionan por nombre.",
    "Basic personal info": "Información personal básica",
    "Name": "Nombre",
    "Enter the applicant's full name.": "Ingrese el nombre completo del solicitante.",
    "Income": "Ingresos",
    "Enter monthly income, or yearly income and choose Yearly.": "Ingrese ingreso mensual, o anual y elija 'Anual'.",
    "Household size": "Tamaño del hogar",
    "Everyone who shares income and expenses.": "Todos los que comparten ingresos y gastos.",
    "State": "Estado",
    "Choose the state for your location.": "Elija el estado de su ubicación.",
    "ZIP code": "Código postal",
    "Used to find nearby offices in the sample dataset.": "Para encontrar oficinas cercanas.",
    "Age range": "Rango de edad",
    "Employment or school status": "Empleo o situación escolar",
    "Program-specific details": "Detalles del programa",
    "US resident or qualified non-citizen": "Residente de EE.UU. o no ciudadano calificado",
    "Used by food, utility, and internet sample checks.": "Usado en verificaciones de alimentos, servicios e internet.",
    "Are you specifically looking for food with high nutritional value?": "¿Busca específicamente alimentos de alto valor nutricional?",
    "It is highly recommended that you select this.": "Se recomienda ampliamente seleccionar esto.",
    "A child in the household is under age 13": "Un menor en el hogar tiene menos de 13 años",
    "Used by the child-care subsidy check.": "Usado en la verificación de cuidado infantil.",
    "A child in the household is under age 5 (WIC)": "Un menor en el hogar tiene menos de 5 años (WIC)",
    "Used by the WIC food assistance check.": "Usado en la verificación WIC.",
    "Pregnant (WIC)": "Embarazada (WIC)",
    "Postpartum (within past 6 months, WIC)": "Postparto (últimos 6 meses, WIC)",
    "Breastfeeding (WIC)": "Lactando (WIC)",
    "Behind on utility bill or received a shutoff notice": "Atrasado en factura de servicios o recibió aviso de corte",
    "Used by utility bill help.": "Usado en ayuda con servicios.",
    "Need home internet for work, school, health, or benefits": "Necesita internet en casa para trabajo, escuela, salud o beneficios",
    "Used by internet subsidy.": "Usado en el subsidio de internet.",
    "Need transportation for work, school, or medical appointments": "Necesita transporte para trabajo, escuela o citas médicas",
    "Used by transportation vouchers.": "Usado en los vales de transporte.",
    "Selected programs": "Programas seleccionados",
    "None yet": "Ninguno todavía",
    # Step 2 — Results
    "Results workspace": "Espacio de resultados",
    "Estimates only — not a government decision. Use filters, what-if income, maps, and exports to prepare a real visit.": "Solo estimados — no es una decisión gubernamental. Use filtros, ingresos hipotéticos, mapas y exportaciones.",
    "Highly eligible": "Muy elegible",
    "Partially eligible": "Parcialmente elegible",
    "Unlikely": "No probable",
    "Not provided": "No proporcionado",
    "Search radius": "Radio de búsqueda",
    "Save CSV history": "Guardar historial CSV",
    "Copy summary": "Copiar resumen",
    "Print list": "Imprimir lista",
    "Edit profile": "Editar perfil",
    "What-if income (percent of the amount you entered — drag, then release to recalculate)": "Ingreso hipotético (porcentaje del monto ingresado — arrastra para recalcular)",
    "Office list": "Lista de oficinas",
    "Search": "Buscar",
    "Sort by": "Ordenar por",
    "Apply filter": "Aplicar filtro",
    "Copy all addresses": "Copiar todas las direcciones",
    "Show:": "Mostrar:",
    "Favorites only ★": "Solo favoritos ★",
    "Visit checklist (sample)": "Lista de documentos (ejemplo)",
    "Bring originals when possible. Offices may ask for different items.": "Lleve originales cuando sea posible.",
    "Eligibility detail": "Detalle de elegibilidad",
    "Nearby offices": "Oficinas cercanas",
    "No offices shown": "No hay oficinas",
    "Offices appear only for programs marked Highly eligible or Partially eligible. Increase income scenario or adjust answers, then update the list.": "Las oficinas solo aparecen para programas marcados como elegibles.",
    "No offices in radius": "Sin oficinas en el radio",
    "Try a larger radius or a sample city such as Sunnyvale, San Jose, Oakland, Los Angeles, San Diego, or Sacramento.": "Prueba un radio más grande o una ciudad como Los Ángeles, Sacramento o San José.",
    "No filter matches": "Sin coincidencias",
    "Clear the office search box or type part of a name, city, or street.": "Limpia el campo de búsqueda o escribe parte del nombre, ciudad o calle.",
    "Copy address": "Copiar dirección",
    "Open in Maps": "Ver en Mapas",
    "Directions": "Cómo llegar",
    "☆ Save": "☆ Guardar",
    "★ Saved": "★ Guardado",
    "Rules met": "Reglas cumplidas",
    "Needs review": "Necesita revisión",
    # What-changed
    "No change at {pct:.0f}% — all programs stay the same": "Sin cambios — todos los programas se mantienen igual",
    # Print list
    "No offices": "Sin oficinas",
    "No offices in current filter view.": "No hay oficinas en la vista actual.",
    "Office list opened in browser — use your browser's Print function": "Lista de oficinas abierta en el navegador — use la función Imprimir",
    # Misc
    "Ready": "Listo",
    "Step 1 of 3": "Paso 1 de 3",
    "Step 2 of 3": "Paso 2 de 3",
    "Step 3 of 3": "Paso 3 de 3",
}


# ===========================================================================
# PROGRAM DEFINITIONS
# ---------------------------------------------------------------------------
# The five assistance programs this app can screen for.
# This dict is the single source of truth for program names, descriptions,
# and display colors. Every other part of the code references this dict
# by key (e.g. "food", "childcare") rather than repeating the display text.
#
# Keys inside each program:
#   "name"        — Full title shown on the step 1 checkboxes and result cards.
#   "short_name"  — Short label used inside pills, lists, and compact spaces.
#   "description" — One-line plain-English description shown in tooltips/cards.
#   "color"       — Hex accent color for the colored swatch beside the checkbox.
# ===========================================================================
PROGRAMS = {
    # ── Child care ────────────────────────────────────────────────────────
    # Federal/state subsidy programs like CCDF that help working parents
    # pay for licensed daycare or after-school care.
    "childcare": {
        "name": "Child-care subsidy",
        "short_name": "Child care",
        "description": "Help paying for licensed care while a parent works or studies.",
        "color": "#14b8a6",   # teal
    },
    # ── Food ─────────────────────────────────────────────────────────────
    # Covers SNAP (food stamps) and WIC. Both are checked simultaneously
    # in food_eligibility() using state-specific income limits.
    "food": {
        "name": "Food assistance / SNAP-like program",
        "short_name": "Food",
        "description": "Monthly grocery support for households under income limits.",
        "color": "#3b82f6",   # blue
    },
    # ── Utility ──────────────────────────────────────────────────────────
    # Programs like LIHEAP that help households pay electric, gas, or water
    # bills — especially if they have a shutoff notice.
    "utility": {
        "name": "Utility bill help",
        "short_name": "Utilities",
        "description": "Energy, water, or emergency bill support.",
        "color": "#f97316",   # orange
    },
    # ── Internet ─────────────────────────────────────────────────────────
    # Programs like ACP (Affordable Connectivity Program) that subsidize
    # home internet for low-income households.
    "internet": {
        "name": "Internet subsidy",
        "short_name": "Internet",
        "description": "Low-cost internet or digital access support.",
        "color": "#8b5cf6",   # purple
    },
    # ── Transportation ────────────────────────────────────────────────────
    # State transit voucher programs — bus passes, rideshare credits, or
    # medical transport help for work, school, or appointments.
    "transportation": {
        "name": "Other: transportation vouchers",
        "short_name": "Transport",
        "description": "Transit passes or rides for work, school, or medical needs.",
        "color": "#f43f5e",   # rose/red
    },
}



# ===========================================================================
# FEDERAL POVERTY LINE (FPL) TABLES
# ---------------------------------------------------------------------------
# The FPL is a number the US government publishes every year that defines
# what "poverty" means for a given household size. Programs use a multiple
# of it (like 130%, 185%, 200%) as their income cutoff.
#
# These are MONTHLY dollar amounts (annual FPL ÷ 12), rounded.
# Key: household size (number of people). Value: monthly income limit in $.
# ===========================================================================

# 100% FPL — the raw poverty line. Most programs use a multiple of this.
# Example: a family of 4 earning $2,750/month or less is at 100% FPL.
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

# 200% FPL — double the poverty line. Used for internet subsidies.
# Example: family of 4 limit becomes $5,500/month.
FPL_200_LIMITS = {size: amount * 2 for size, amount in FPL_BASE_LIMITS.items()}

# 150% FPL — one-and-a-half times the poverty line. Used as a floor for utility programs.
FPL_150_LIMITS = {size: amount * 1.5 for size, amount in FPL_BASE_LIMITS.items()}

# Alias so food eligibility code can reference the base as "FPL_100" for clarity.
FPL_100_LIMITS = FPL_BASE_LIMITS

# ---------------------------------------------------------------------------
# Alaska and Hawaii FPL tables
# ---------------------------------------------------------------------------
# The federal government publishes SEPARATE, HIGHER FPL numbers for Alaska
# and Hawaii because the cost of living there is significantly higher than
# the continental US. Alaska is ~25% higher; Hawaii is ~15% higher.
# These are the 100% FPL monthly values for those two states.
# The per-person "extra" amount is added for households larger than 8 people.
# ---------------------------------------------------------------------------

ALASKA_FPL_BASE = {1: 1662, 2: 2254, 3: 2846, 4: 3438, 5: 4030, 6: 4622, 7: 5214, 8: 5806}
ALASKA_FPL_EXTRA_PERSON = 592   # add this per person beyond 8

HAWAII_FPL_BASE = {1: 1528, 2: 2073, 3: 2618, 4: 3163, 5: 3708, 6: 4253, 7: 4798, 8: 5343}
HAWAII_FPL_EXTRA_PERSON = 545   # add this per person beyond 8

# ---------------------------------------------------------------------------
# SNAP Gross Income Test Multipliers by State (2026 BBCE Rules)
# ---------------------------------------------------------------------------
# SNAP (food stamps) has a federal gross income test at 130% FPL. However,
# most states have adopted "Broad-Based Categorical Eligibility" (BBCE),
# which lets them raise that ceiling. This dict maps each state to its
# actual multiplier. States NOT listed here use the 200% default (the most
# generous tier, used by big states like CA, NY, FL, etc.).
#
# Example: Texas uses 1.65, so a family of 4 can earn up to
#   $2,750 (100% FPL) × 1.65 = $4,537/month and still qualify for SNAP.
# ---------------------------------------------------------------------------
SNAP_STATE_MULTIPLIERS: dict[str, float] = {
    # 130% — strictest states; use the federal minimum with no BBCE expansion
    "Alabama": 1.30, "Arkansas": 1.30, "Georgia": 1.30, "Idaho": 1.30,
    "Indiana": 1.30, "Kansas": 1.30, "Mississippi": 1.30, "Missouri": 1.30,
    "Ohio": 1.30, "Oklahoma": 1.30, "South Carolina": 1.30, "South Dakota": 1.30,
    "Tennessee": 1.30, "Utah": 1.30, "Wyoming": 1.30,
    # 160%
    "Iowa": 1.60,
    # 165%
    "Illinois": 1.65, "Nebraska": 1.65, "Texas": 1.65,
    # 185%
    "Arizona": 1.85, "New Jersey": 1.85, "Rhode Island": 1.85, "Vermont": 1.85,
    # All other states (CA, NY, FL, WA, etc.) default to 2.00 — see food_eligibility()
}





# ---------------------------------------------------------------------------
# Extra-person amounts
# ---------------------------------------------------------------------------
# The FPL tables above only go up to 8 people. For households larger than 8,
# we extend the table by adding a fixed dollar amount for each extra person.
# These are the 100% FPL "per additional person" amounts, used as a base.
# Food uses this directly; internet doubles it (since it uses 200% FPL).
# ---------------------------------------------------------------------------
FPL_BASE_EXTRA_PERSON_AMOUNTS = {
    "food": 473,       # $473/month per person beyond 8, at 100% FPL
    "internet": 473,   # same base — will be doubled for 200% FPL below
}

# 200% versions of the above — used by internet subsidy calculations.
FPL_EXTRA_PERSON_AMOUNTS = {program: amount * 2 for program, amount in FPL_BASE_EXTRA_PERSON_AMOUNTS.items()}

# 150% version of the food extra-person amount — used by the utility floor calculation.
FPL_150_EXTRA_PERSON_AMOUNT = FPL_BASE_EXTRA_PERSON_AMOUNTS["food"] * 1.5

# ---------------------------------------------------------------------------
# State-specific extra-person increments (for childcare, utility, transportation)
# ---------------------------------------------------------------------------
# When a household has more than 8 people, we look up how much to add per
# extra person from this table. These are derived from real state program data:
#   - Childcare: from CCDF 2025 (difference between family-of-4 and family-of-3 limits)
#   - Utility: estimated from LIHEAP state data
#   - Transportation: estimated from state transit-assistance data
# Food and internet are NOT in this table — food uses SNAP logic, internet uses
# the federal 200% FPL amount above.
# ---------------------------------------------------------------------------
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

# ===========================================================================
# STATE INCOME LIMITS TABLE
# ---------------------------------------------------------------------------
# This is the main lookup table the app uses to decide if someone qualifies.
# For each state, it stores the monthly gross income limits for each program.
#
# How to read it: if a family of 4 in Alabama earns less than $4,500/month,
# they are under the childcare limit for Alabama.
#
# Sources:
#   - Childcare:      CCDF eligibility thresholds (2026)
#   - Utility:        LIHEAP — higher of 150% FPL or 60% State Median Income
#   - Internet:       200% FPL (federal, uniform across all states)
#   - Transportation: State transit-assistance program thresholds (estimated)
#   - Food:           NOT in this table — handled separately by food_eligibility()
#                     using SNAP_STATE_MULTIPLIERS and the FPL tables above.
# ===========================================================================
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

# ===========================================================================
# SECTION 3 — SERVICE LOCATIONS
# ---------------------------------------------------------------------------
# Loaded from locations.json — add new offices there without editing code.
# ===========================================================================
with open(resource_path("locations.json"), encoding="utf-8") as _lf:
    LOCATIONS: list[dict] = json.load(_lf)

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


class ModernCheckbox(tk.Frame):
    """A beautiful modern checkbox with rounded corners, smooth animations, and reactive hover effects."""
    
    def __init__(self, parent: tk.Widget, text: str = "", variable: tk.BooleanVar | None = None, 
                 command: callable | None = None, bg: str = CARD_BG, fg: str = TEXT) -> None:
        super().__init__(parent, bg=bg)
        
        self.variable = variable or tk.BooleanVar(value=False)
        self.command = command
        self.bg_color = bg
        self.fg_color = fg
        
        # Create checkbox container (clickable area)
        self.checkbox_frame = tk.Frame(self, bg=bg)
        self.checkbox_frame.pack(side="left", anchor="w")
        
        # Create the checkbox canvas
        self.checkbox_canvas = tk.Canvas(
            self.checkbox_frame,
            width=24, height=24,
            bg=bg,
            highlightthickness=0,
            bd=0,
            cursor="hand2"
        )
        self.checkbox_canvas.pack(pady=2)
        
        # Create label
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
        
        # Animation state
        self._hover = False
        self._animation_id = None
        
        # Bind events
        self.checkbox_canvas.bind("<Enter>", self._on_hover)
        self.checkbox_canvas.bind("<Leave>", self._on_leave)
        self.checkbox_canvas.bind("<Button-1>", self._on_click)
        if text:
            self.label.bind("<Enter>", self._on_hover)
            self.label.bind("<Leave>", self._on_leave)
            self.label.bind("<Button-1>", self._on_click)
        
        self.variable.trace("w", lambda *args: self._redraw())
        self._redraw()
    
    def _on_hover(self, _event=None):
        self._hover = True
        self._redraw()
    
    def _on_leave(self, _event=None):
        self._hover = False
        self._redraw()
    
    def _on_click(self, _event=None):
        self.variable.set(not self.variable.get())
        if self.command:
            self.command()
    
    def _redraw(self):
        self.checkbox_canvas.delete("all")
        
        is_checked = self.variable.get()
        size = 24
        
        # Outer rounded rect (border)
        border_color = "#4f46e5" if is_checked else ("#cbd5e1" if self._hover else "#d1d5db")
        bg_color = "#4f46e5" if is_checked else ("#f0f9ff" if self._hover else "white")
        
        # Draw rounded box (simplified as regular rect for better macOS support)
        self.checkbox_canvas.create_rectangle(
            2, 2, size-2, size-2,
            fill=bg_color,
            outline=border_color,
            width=2,
            tags="box"
        )
        
        # Add slight glow on hover
        if self._hover and not is_checked:
            self.checkbox_canvas.create_rectangle(
                1, 1, size-1, size-1,
                fill="",
                outline=border_color,
                width=1,
                tags="glow"
            )
        
        # Draw checkmark if checked
        if is_checked:
            # Draw a nice checkmark
            checkmark_color = "white"
            # Checkmark path: two lines forming an L shape
            self.checkbox_canvas.create_line(6, 12, 10, 16, fill=checkmark_color, width=2, tags="check")
            self.checkbox_canvas.create_line(10, 16, 18, 6, fill=checkmark_color, width=2, tags="check")


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


class CanvasScrollbar(tk.Canvas):
    """Modern canvas-based scrollbar with smooth rendering and robust thumb calculation."""
    
    def __init__(self, parent, command=None, width=10, bg="#222", thumb_color="#888"):
        super().__init__(parent, width=width, height=1, highlightthickness=0, bg=bg)
        
        self.command = command
        self.thumb_color = thumb_color
        self._start = 0
        self._end = 1
        self._dragging = False
        
        self.bind("<Button-1>", self._click)
        self.bind("<B1-Motion>", self._drag)
        self.bind("<ButtonRelease-1>", self._release)
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Enter>", lambda e: self.config(cursor="hand2"))
        self.bind("<Leave>", lambda e: self.config(cursor=""))
    
    def set(self, start, end):
        """Update scrollbar position."""
        self._start = max(0.0, min(1.0, float(start)))
        self._end = max(0.0, min(1.0, float(end)))
        self._draw()
    
    def _draw(self):
        """Render the scrollbar thumb."""
        self.delete("all")
        
        h = self.winfo_height()
        w = self.winfo_width()
        
        if h < 4 or w < 4:
            return  # Too small to draw
        
        # Calculate thumb position and size
        thumb_start = int(self._start * h)
        thumb_end = int(self._end * h)
        thumb_height = thumb_end - thumb_start
        
        # Minimum thumb size for usability
        min_thumb = max(16, int(h * 0.05))
        if thumb_height < min_thumb:
            thumb_height = min_thumb
            thumb_end = thumb_start + thumb_height
        
        # Clamp to canvas bounds
        thumb_start = max(0, min(thumb_start, h - thumb_height))
        thumb_end = min(h, thumb_start + thumb_height)
        
        radius = w // 2
        
        # Main body rectangle
        self.create_rectangle(
            2, thumb_start + radius,
            w - 2, thumb_end - radius,
            fill=self.thumb_color,
            outline=""
        )
        
        # Top rounded cap
        if thumb_start + 2 * radius <= thumb_end:
            self.create_oval(
                2, thumb_start,
                w - 2, thumb_start + 2 * radius,
                fill=self.thumb_color,
                outline=""
            )
        
        # Bottom rounded cap
        if thumb_end - 2 * radius >= thumb_start:
            self.create_oval(
                2, thumb_end - 2 * radius,
                w - 2, thumb_end,
                fill=self.thumb_color,
                outline=""
            )
    
    def _click(self, event):
        """Handle click on scrollbar."""
        self._dragging = True
        self._drag(event)
    
    def _drag(self, event):
        """Handle dragging the thumb."""
        if not self.command:
            return
        
        h = self.winfo_height()
        if h <= 0:
            return
        
        fraction = event.y / h
        fraction = max(0.0, min(1.0, fraction))
        
        self.command("moveto", fraction)
    
    def _release(self, _event):
        """Handle release of mouse."""
        self._dragging = False


class HorizontalCanvasScrollbar(tk.Canvas):
    """Modern horizontal canvas-based scrollbar with robust thumb calculation."""
    
    def __init__(self, parent, command=None, height=10, bg="#222", thumb_color="#888"):
        super().__init__(parent, height=height, width=1, highlightthickness=0, bg=bg)
        
        self.command = command
        self.thumb_color = thumb_color
        self._start = 0
        self._end = 1
        self._dragging = False
        
        self.bind("<Button-1>", self._click)
        self.bind("<B1-Motion>", self._drag)
        self.bind("<ButtonRelease-1>", self._release)
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Enter>", lambda e: self.config(cursor="hand2"))
        self.bind("<Leave>", lambda e: self.config(cursor=""))
    
    def set(self, start, end):
        """Update scrollbar position."""
        self._start = max(0.0, min(1.0, float(start)))
        self._end = max(0.0, min(1.0, float(end)))
        self._draw()
    
    def _draw(self):
        """Render the scrollbar thumb."""
        self.delete("all")
        
        h = self.winfo_height()
        w = self.winfo_width()
        
        if h < 4 or w < 4:
            return  # Too small to draw
        
        # Calculate thumb position and size
        thumb_start = int(self._start * w)
        thumb_end = int(self._end * w)
        thumb_width = thumb_end - thumb_start
        
        # Minimum thumb size for usability
        min_thumb = max(16, int(w * 0.05))
        if thumb_width < min_thumb:
            thumb_width = min_thumb
            thumb_end = thumb_start + thumb_width
        
        # Clamp to canvas bounds
        thumb_start = max(0, min(thumb_start, w - thumb_width))
        thumb_end = min(w, thumb_start + thumb_width)
        
        radius = h // 2
        
        # Main body rectangle
        self.create_rectangle(
            thumb_start + radius, 2,
            thumb_end - radius, h - 2,
            fill=self.thumb_color,
            outline=""
        )
        
        # Left rounded cap
        if thumb_start + 2 * radius <= thumb_end:
            self.create_oval(
                thumb_start, 2,
                thumb_start + 2 * radius, h - 2,
                fill=self.thumb_color,
                outline=""
            )
        
        # Right rounded cap
        if thumb_end - 2 * radius >= thumb_start:
            self.create_oval(
                thumb_end - 2 * radius, 2,
                thumb_end, h - 2,
                fill=self.thumb_color,
                outline=""
            )
    
    def _click(self, event):
        """Handle click on scrollbar."""
        self._dragging = True
        self._drag(event)
    
    def _drag(self, event):
        """Handle dragging the thumb."""
        if not self.command:
            return
        
        w = self.winfo_width()
        if w <= 0:
            return
        
        fraction = event.x / w
        fraction = max(0.0, min(1.0, fraction))
        
        self.command("moveto", fraction)
    
    def _release(self, _event):
        """Handle release of mouse."""
        self._dragging = False


class HorizontalScrollableFrame(ttk.Frame):
    """Custom horizontally scrollable frame with smooth scrolling and keyboard support."""

    _active = None
    _wheel_bound = False

    def __init__(self, parent: ttk.Widget, background: str = APP_BG) -> None:
        super().__init__(parent)

        self._bg = background

        # Main scrolling canvas
        self.canvas = tk.Canvas(
            self,
            borderwidth=0,
            highlightthickness=0,
            background=background,
            xscrollincrement=20,
        )

        # Custom horizontal scrollbar
        self.scrollbar = HorizontalCanvasScrollbar(
            self,
            command=self._scroll_command,
            height=10,
            bg=background,
            thumb_color="#888"
        )

        # Inner frame (actual content container)
        self.inner = tk.Frame(self.canvas, background=background)

        self.window_id = self.canvas.create_window(
            (0, 0),
            window=self.inner,
            anchor="nw"
        )

        # Connect scrollbar <-> canvas
        self.canvas.configure(xscrollcommand=self._on_scroll)

        # Layout
        self.canvas.pack(side="top", fill="both", expand=True)
        self.scrollbar.pack(side="bottom", fill="x")

        # Resize + scroll region handling
        self.inner.bind("<Configure>", self._update_scroll_region)
        self.canvas.bind("<Configure>", self._resize_inner)

        # Mouse tracking
        self.bind("<Enter>", self._activate)
        self.canvas.bind("<Enter>", self._activate)
        self.inner.bind("<Enter>", self._activate)

        # Keyboard bindings for horizontal scrolling
        self.canvas.bind("<Left>", self._on_key_left)
        self.canvas.bind("<Right>", self._on_key_right)

        self.bind("<Destroy>", self._on_destroy)

    def _update_scroll_region(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _resize_inner(self, event):
        self.canvas.itemconfig(self.window_id, height=event.height)

    def _activate(self, _event):
        HorizontalScrollableFrame._active = self
        self.canvas.focus_set()

    def _on_destroy(self, event):
        if event.widget == self:
            if HorizontalScrollableFrame._active is self:
                HorizontalScrollableFrame._active = None

    def _on_scroll(self, start, end):
        """Update scrollbar when canvas scrolls."""
        self.scrollbar.set(start, end)

    def _scroll_command(self, *args):
        """Handle scrollbar commands."""
        self.canvas.xview(*args)

    # ============ Keyboard Support ============

    def _on_key_left(self, _event):
        self.canvas.xview_scroll(-3, "units")

    def _on_key_right(self, _event):
        self.canvas.xview_scroll(3, "units")


class ScrollableFrame(ttk.Frame):
    """Custom scrollable frame with canvas-based scrollbar, animated scrolling,
    and keyboard support with smooth acceleration."""

    _active = None
    _wheel_bound = False

    def __init__(self, parent: tk.Widget, background: str = APP_BG) -> None:
        super().__init__(parent)

        self._bg = background

        # Main scrolling canvas
        self.canvas = tk.Canvas(
            self,
            borderwidth=0,
            highlightthickness=0,
            background=background,
            highlightcolor=background,
            highlightbackground=background,
            yscrollincrement=20,
        )
        self.canvas.config(takefocus=True)  # Make canvas focusable

        # Custom scrollbar
        self.scrollbar = CanvasScrollbar(
            self,
            command=self._scroll_command,
            width=10,
            bg=background,
            thumb_color="#888"
        )

        # Inner frame (actual content container)
        self.inner = tk.Frame(self.canvas, background=background)

        self.window_id = self.canvas.create_window(
            (0, 0),
            window=self.inner,
            anchor="nw"
        )

        # Connect scrollbar <-> canvas
        self.canvas.configure(yscrollcommand=self._on_scroll)

        # Layout
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Resize + scroll region handling
        self.inner.bind("<Configure>", self._update_scroll_region)
        self.canvas.bind("<Configure>", self._resize_inner)

        # Mouse tracking
        self.bind("<Enter>", self._activate)
        self.canvas.bind("<Enter>", self._activate)
        self.inner.bind("<Enter>", self._activate)

        # Keyboard bindings on canvas
        self.canvas.bind("<KeyPress-Up>", self._on_key_up)
        self.canvas.bind("<KeyPress-Down>", self._on_key_down)
        self.canvas.bind("<KeyPress-Prior>", self._on_page_up)
        self.canvas.bind("<KeyPress-Next>", self._on_page_down)
        self.canvas.bind("<KeyPress-Home>", self._on_home)
        self.canvas.bind("<KeyPress-End>", self._on_end)
        
        # Also bind to frame level for better event capture
        self.bind("<KeyPress-Up>", self._on_key_up)
        self.bind("<KeyPress-Down>", self._on_key_down)
        self.bind("<KeyPress-Prior>", self._on_page_up)
        self.bind("<KeyPress-Next>", self._on_page_down)
        self.bind("<KeyPress-Home>", self._on_home)
        self.bind("<KeyPress-End>", self._on_end)

        self.bind("<Destroy>", self._on_destroy)

    def _update_scroll_region(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _resize_inner(self, event):
        self.canvas.itemconfig(self.window_id, width=event.width)

    def _activate(self, _event):
        ScrollableFrame._active = self
        # Focus canvas to receive keyboard events
        self.canvas.focus_set()

    def _on_destroy(self, event):
        if event.widget == self:
            if ScrollableFrame._active is self:
                ScrollableFrame._active = None

    def _on_scroll(self, start, end):
        """Update scrollbar when canvas scrolls."""
        self.scrollbar.set(start, end)

    def _scroll_command(self, *args):
        """Handle scrollbar commands."""
        self.canvas.yview(*args)

    # ============ Keyboard Support ============

    def _on_key_up(self, _event):
        self.canvas.yview_scroll(-3, "units")

    def _on_key_down(self, _event):
        self.canvas.yview_scroll(3, "units")

    def _on_page_up(self, _event):
        self.canvas.yview_scroll(-10, "units")

    def _on_page_down(self, _event):
        self.canvas.yview_scroll(10, "units")

    def _on_home(self, _event):
        """Home key - scroll to top."""
        self.canvas.yview_moveto(0)

    def _on_end(self, _event):
        """End key - scroll to bottom."""
        self.canvas.yview_moveto(1)

    # ============ Mousewheel Support with Smooth Acceleration ============

    @classmethod
    def hook_mousewheel(cls, root: tk.Misc) -> None:
        if cls._wheel_bound:
            return

        root.bind_all("<MouseWheel>", cls._on_mousewheel_all)
        root.bind_all("<Button-4>", cls._on_linux_up_all)
        root.bind_all("<Button-5>", cls._on_linux_down_all)

        cls._wheel_bound = True

    @classmethod
    def _scroll_target(cls, event):
        """Find the scrollable frame under the cursor."""
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

        return cls._active

    @classmethod
    def _on_mousewheel_all(cls, event):
        """Handle Windows/macOS mousewheel scrolling."""
        target = cls._scroll_target(event)
        if target:
            delta = getattr(event, "delta", 0)
            if delta == 0:
                return
            # delta=120 per mouse-wheel click; trackpad sends smaller values.
            # Scale so one click scrolls 3 units (60px with yscrollincrement=20).
            units = max(1, abs(delta) // 40) * (-1 if delta > 0 else 1)
            target.canvas.yview_scroll(units, "units")

    @classmethod
    def _on_linux_up_all(cls, event):
        target = cls._scroll_target(event)
        if target:
            target.canvas.yview_scroll(-3, "units")

    @classmethod
    def _on_linux_down_all(cls, event):
        target = cls._scroll_target(event)
        if target:
            target.canvas.yview_scroll(3, "units")


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
    """
    The baseline settings used the very first time the app runs (or if the
    settings file gets deleted). All keys here MUST match what load_settings()
    and the settings panel read/write.

      font_scale:     0 = normal size. Positive = bigger text for accessibility.
      reduce_motion:  if True, skip the animated button pulse effect.
      autosave_draft: if True, save the form to disk every time the user changes a field.
    """
    return {"font_scale": 0, "reduce_motion": False, "autosave_draft": True}


def load_settings() -> dict[str, object]:
    """
    Read saved settings from disk. Strategy:
      1. If the file doesn't exist → use defaults (first run).
      2. If the file exists but is corrupt → use defaults (graceful recovery).
      3. If the file exists and is valid → merge with defaults so any NEW keys
         added in a future version automatically get their default values.
    """
    if not SETTINGS_FILE.exists():
        return default_settings()   # first run — no file yet
    try:
        # Read the raw text and parse it as a JSON dictionary.
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        # Start from defaults so new/missing keys are always populated.
        base = default_settings()
        # Overwrite only the keys that exist in both the file AND the defaults dict.
        # This prevents stale/unknown keys from sneaking in.
        base.update({k: data[k] for k in base if k in data})
        return base
    except (json.JSONDecodeError, OSError):
        # File is corrupt, empty, or we don't have read permission — use defaults.
        return default_settings()


def save_settings(data: dict[str, object]) -> None:
    """Write the settings dictionary to disk as nicely-indented JSON.
    Silently ignores disk errors (full disk, read-only file system, etc.)
    because a failed settings save should never crash the app.
    """
    try:
        SETTINGS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError:
        pass   # disk error — just skip silently


def _loc_key(location: dict) -> str:
    """Stable string key that uniquely identifies a location for favorites."""
    return f"{location['name']}|{location['address']}"


def _maps_query(location: dict) -> str:
    """Build the most precise Maps query string possible for a location dict.

    Priority:
    1. Lat/lng coordinates — completely unambiguous, works for any address.
    2. Full address if the ZIP is already embedded in the address field.
    3. Street + city + state + ZIP appended so Maps can disambiguate.
    """
    if location.get("lat") and location.get("lng"):
        return f"{location['lat']},{location['lng']}"
    addr = str(location.get("address", ""))
    zip_code = str(location.get("zip", ""))
    if zip_code and zip_code in addr:
        return addr  # address field already includes ZIP — no disambiguation needed
    city = str(location.get("city", ""))
    state = str(location.get("state", ""))
    extras = ", ".join(p for p in [city, state, zip_code] if p)
    return f"{addr}, {extras}" if extras else addr


def open_location_in_maps(address: str) -> None:
    """Open the user's default browser with a Google Maps search for the address."""
    webbrowser.open(f"https://www.google.com/maps/search/?api=1&query={quote_plus(address)}")


def open_directions_in_maps(destination: str, origin: str = "") -> None:
    """Open Google Maps in directions mode. Origin is the user's location (ZIP or city);
    destination is the office. If origin is empty, Maps uses the device's current location."""
    url = f"https://www.google.com/maps/dir/?api=1&destination={quote_plus(destination)}"
    if origin:
        url += f"&origin={quote_plus(origin)}"
    webbrowser.open(url)


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
        self.residency_var = tk.BooleanVar(value=True)
        self.healthy_var = tk.BooleanVar(value=True)           # is a US resident?
        self.child_under_13_var = tk.BooleanVar(value=True)      # has young child?
        self.child_under_5_var = tk.BooleanVar(value=False)      # has child under 5 (WIC)?
        self.pregnant_var = tk.BooleanVar(value=False)           # pregnant (WIC)?
        self.postpartum_var = tk.BooleanVar(value=False)         # postpartum (WIC)?
        self.breastfeeding_var = tk.BooleanVar(value=False)      # breastfeeding (WIC)?
        self.utility_hardship_var = tk.BooleanVar(value=False)   # behind on utilities?
        self.internet_need_var = tk.BooleanVar(value=True)       # needs internet?
        self.transportation_need_var = tk.BooleanVar(value=False)  # needs transit?
        self.radius_var = tk.StringVar(value="10")               # search radius miles
        self._radius_dbl = tk.DoubleVar(value=10.0)              # numeric twin for the slider

        # Variables for the results page filters.
        self.office_search_var = tk.StringVar()                  # office search text
        self.office_sort_var = tk.StringVar(value="distance")    # sort by distance/name
        self.income_scenario_pct = tk.DoubleVar(value=100.0)     # "what-if" income slider
        self.prog_filter_vars: dict[str, tk.BooleanVar] = {k: tk.BooleanVar(value=True) for k in PROGRAMS}
        self.show_favorites_var = tk.BooleanVar(value=False)
        self._lang: str = "en"
        self.favorite_keys: set[str] = self._load_favorites()

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

    def _t(self, text: str) -> str:
        """Return the Spanish translation of `text` if the UI is in Spanish, otherwise English."""
        if self._lang == "es":
            return SPANISH.get(text, text)
        return text

    def _button(self, parent: tk.Widget, text: str, command, variant: str = "secondary") -> ModernButton:
        # Quick helper: make a ModernButton that matches its parent's background.
        return ModernButton(parent, text, command, variant, widget_background(parent))

    def _load_brand_logo(self) -> tk.PhotoImage | None:
        """Load the logo image and shrink it if it's too big. Returns None if no logo."""
        logo_path = resolve_brand_logo_path()
        if not logo_path:
            return None
        max_h = 70  # logical display height in points
        # Prefer PIL: smooth resize with no subsample GC hazard.
        if Image is not None and ImageTk is not None:
            try:
                pil_img = Image.open(str(logo_path))
                # Render at physical pixels so Retina/HiDPI displays stay crisp.
                # winfo_fpixels('1i') ≈ 144 on 2x Retina vs 72 on standard.
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
        # Fallback: pure Tkinter (PIL not installed).
        try:
            image = tk.PhotoImage(file=str(logo_path))
        except tk.TclError:
            return None
        if image.height() > max_h:
            ratio = max(1, math.ceil(image.height() / max_h))
            # Keep original alive — subsample result can be invalidated when
            # the source image is garbage-collected on some Tk builds.
            self._brand_logo_original = image
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
            logo_label = tk.Label(left_brand, image=self.brand_logo_image, bg=HEADER_BG)
            logo_label.pack(side="left", padx=(0, 14))

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
        self._lang_btn = self._button(tools, "ES", self._toggle_lang, "accent")
        self._lang_btn.pack(side="left", padx=3)

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
        self._nav_startover_btn = self._button(self.nav, "Start over", self.start_over, "ghost")
        self._nav_startover_btn.pack(side="left", padx=10)
        self._nav_savedraft_btn = self._button(self.nav, "Save draft", self.action_save_draft_now, "ghost")
        self._nav_savedraft_btn.pack(side="left", padx=4)
        self._nav_loaddraft_btn = self._button(self.nav, "Load draft", self.action_load_draft_now, "ghost")
        self._nav_loaddraft_btn.pack(side="left", padx=4)
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
                "healthy": self.healthy_var.get(),
                "child_under_13": self.child_under_13_var.get(),
                "child_under_5": self.child_under_5_var.get(),
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
        self.healthy_var.set(bool(data.get("healthy", True)))
        self.child_under_13_var.set(bool(data.get("child_under_13", True)))
        self.child_under_5_var.set(bool(data.get("child_under_5", False)))
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
            self.next_button.configure(text=self._t("Continue"))
        elif step == 1:
            self._build_info_screen()
            self.back_button.configure(state="normal")
            self.next_button.configure(text=self._t("Check Eligibility"))
        else:
            self._build_results_screen()
            self.back_button.configure(state="normal")
            self.next_button.configure(text=self._t("Draft Application"))
        # Schedule an autosave whenever a step shows up.
        self._schedule_draft_autosave()
        # Update the footer message.
        self._status(self._t(f"Step {step + 1} of 3"))

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
        ttk.Label(self._step_host, text=self._t("Welcome"), style="Title.TLabel").pack(anchor="w")
        tk.Label(
            self._step_host,
            text=self._t("Pick programs, answer one shared profile, then review eligibility, offices, and a printable packing list."),
            bg=APP_BG,
            fg=MUTED,
            font=(FONT_FAMILY, self._font_size(12)),
            wraplength=self._text_wrap(),
            justify="left",
        ).pack(anchor="w", pady=(6, 14))

        # === Three info "chip" cards across the top ===
        chips_container = HorizontalScrollableFrame(self._step_host, APP_BG)
        chips_container.pack(fill="x", pady=(0, 22))
        chips = chips_container.inner
        # Each chip's wrap width is about a third of the available area.
        chip_wrap = max(200, min(280, self._text_wrap() // 3))
        # Loop over the chip data and build one card per item.
        for label, sub in (
            ("Smart reuse", "One questionnaire powers every program you pick."),
            ("Office radar", "Distance-ranked sites — hundreds of demo ZIP codes statewide."),
            ("Audit trail", "CSV history + JSON export for handoff."),
        ):
            c = self._card(chips)
            c.pack(side="left", fill="both", expand=False, padx=(0, 14))
            cb = self._surface(c)  # the inner body of the rounded card
            # Bold title.
            tk.Label(cb, text=self._t(label), bg=CARD_BG, fg=TEXT, font=(FONT_FAMILY, self._font_size(13), "bold")).pack(anchor="w", padx=18, pady=(16, 6))
            # Description text.
            tk.Label(cb, text=self._t(sub), bg=CARD_BG, fg=MUTED, font=(FONT_FAMILY, self._font_size(11)), wraplength=chip_wrap, justify="left").pack(anchor="w", padx=18, pady=(0, 18))

        # === Main "pick subsidies" card ===
        card = self._card(self._step_host)
        card.pack(fill="x", expand=False)
        card_body = self._surface(card)

        # Card heading.
        tk.Label(card_body, text=self._t("Which type of subsidy?"), bg=CARD_BG, fg=TEXT, font=(FONT_FAMILY, self._font_size(20), "bold")).pack(anchor="w", padx=24, pady=(24, 8))
        # Subtitle / instruction.
        tk.Label(
            card_body,
            text=self._t("Choose one or more programs. Use Select all if you want a full scan."),
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
            ModernCheckbox(head, text=self._t(program["name"]), variable=self.program_vars[key], bg=CARD_BG_HOVER, fg=TEXT).pack(side="left", anchor="nw", pady=(2, 0))
            # The program's description below the checkbox row.
            tk.Label(
                inner,
                text=self._t(program["description"]),
                bg=CARD_BG_HOVER,
                fg=SUBTEXT,
                font=(FONT_FAMILY, self._font_size(11)),
                wraplength=row_wrap,
                justify="left",
            ).pack(anchor="w", padx=(22, 8), pady=(12, 0))

        # === Buttons at the bottom of the card ===
        actions = tk.Frame(card_body, bg=CARD_BG)
        actions.pack(fill="x", padx=22, pady=(22, 26))
        self._button(actions, self._t("Select all"), self.select_all_programs, "secondary").pack(side="left")
        self._button(actions, self._t("Clear"), self.clear_programs, "ghost").pack(side="left", padx=10)
        self._button(actions, self._t("Suggest common bundle"), self.suggest_program_bundle, "accent").pack(side="right")

        # === Eligibility estimator card ===
        est_card = self._card(self._step_host)
        est_card.pack(fill="x", pady=(18, 0))
        eb = self._surface(est_card)
        state = self.state_var.get()
        state_lims = STATE_LIMITS.get(state, STATE_LIMITS["California"])
        snap_mult = SNAP_STATE_MULTIPLIERS.get(state, 2.0)
        tk.Label(eb, text=self._t("Quick eligibility snapshot"), bg=CARD_BG, fg=TEXT, font=(FONT_FAMILY, self._font_size(15), "bold")).pack(anchor="w", padx=22, pady=(20, 4))
        tk.Label(eb, text=self._t("Typical income limits, family of 4") + f" · {state}", bg=CARD_BG, fg=MUTED, font=(FONT_FAMILY, self._font_size(11)), wraplength=self._text_wrap() - 48, justify="left").pack(anchor="w", padx=22, pady=(0, 14))
        est_rows = [
            ("childcare",       state_lims.get("childcare", {}).get(4, 0)),
            ("food",            snap_mult * FPL_100_LIMITS[4]),
            ("utility",         state_lims.get("utility", {}).get(4, 0)),
            ("internet",        FPL_200_LIMITS[4]),
            ("transportation",  state_lims.get("transportation", {}).get(4, 0)),
        ]
        for prog_key, limit in est_rows:
            prog = PROGRAMS[prog_key]
            row = tk.Frame(eb, bg=CARD_BG)
            row.pack(fill="x", padx=22, pady=3)
            swatch = tk.Frame(row, bg=prog["color"], width=10, height=18)
            swatch.pack(side="left", padx=(0, 10))
            swatch.pack_propagate(False)
            tk.Label(row, text=self._t(prog["short_name"]), bg=CARD_BG, fg=TEXT, font=(FONT_FAMILY, self._font_size(11)), width=14, anchor="w").pack(side="left")
            tk.Label(row, text=f"under ${limit:,.0f} / mo", bg=CARD_BG, fg=MUTED, font=(FONT_FAMILY, self._font_size(11))).pack(side="left")
        tk.Frame(eb, height=14, bg=CARD_BG).pack()

    def _build_info_screen(self) -> None:
        """Build step 2: the form for the household profile."""
        # === Title and intro paragraph ===
        ttk.Label(self._step_host, text=self._t("Household profile"), style="Title.TLabel").pack(anchor="w")
        tk.Label(
            self._step_host,
            text=self._t("Answer once — every selected program reuses this profile. You can go back and edit before running the check."),
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
            text=self._t("Tip: enter any 5-digit ZIP from the expanded demo set (e.g. 95125, 94110, 90026, 92104, 95825, 93722, 92806) for distance math; cities still match by name."),
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
        self._section_title(left, self._t("Basic personal info"))
        # Each _field_row builds a labeled row with a widget under it.
        # The lambda creates the actual input widget — done lazily so we
        # control which parent row it goes into.
        self._field_row(left, self._t("Name"), lambda row: self._entry(row, self.name_var), self._t("Enter the applicant's full name."))
        self._field_row(left, self._t("Income"), lambda row: self._income_field(row), self._t("Enter monthly income, or yearly income and choose Yearly."))
        self._field_row(left, self._t("Household size"), lambda row: self._spinbox(row, self.household_var, 1, 12), self._t("Everyone who shares income and expenses."))
        self._field_row(left, self._t("State"), lambda row: self._combo(row, self.state_var, STATE_OPTIONS), self._t("Choose the state for your location."))
        self._field_row(left, self._t("ZIP code"), lambda row: self._entry(row, self.location_var), self._t("Used to find nearby offices in the sample dataset."))
        self._field_row(left, self._t("Age range"), lambda row: self._combo(row, self.age_var, AGE_OPTIONS), "")
        # Employment goes in the right column (continuing the form there).
        self._field_row(right, self._t("Employment or school status"), lambda row: self._combo(row, self.employment_var, EMPLOYMENT_OPTIONS), "")

        # === Right column: program-specific yes/no questions ===
        self._section_title(right, self._t("Program-specific details"))
        self._check_row(right, self._t("US resident or qualified non-citizen"), self.residency_var, self._t("Used by food, utility, and internet sample checks."))
        self._check_row(right, self._t("Are you specifically looking for food with high nutritional value?"), self.healthy_var, self._t("It is highly recommended that you select this."))
        self._check_row(right, self._t("A child in the household is under age 13"), self.child_under_13_var, self._t("Used by the child-care subsidy check."))
        self._check_row(right, self._t("A child in the household is under age 5 (WIC)"), self.child_under_5_var, self._t("Used by the WIC food assistance check."))
        self._check_row(right, self._t("Pregnant (WIC)"), self.pregnant_var, self._t("Used by the WIC food assistance check."))
        self._check_row(right, self._t("Postpartum (within past 6 months, WIC)"), self.postpartum_var, self._t("Used by the WIC food assistance check."))
        self._check_row(right, self._t("Breastfeeding (WIC)"), self.breastfeeding_var, self._t("Used by the WIC food assistance check."))
        self._check_row(right, self._t("Behind on utility bill or received a shutoff notice"), self.utility_hardship_var, self._t("Used by utility bill help."))
        self._check_row(right, self._t("Need home internet for work, school, health, or benefits"), self.internet_need_var, self._t("Used by internet subsidy."))
        self._check_row(right, self._t("Need transportation for work, school, or medical appointments"), self.transportation_need_var, self._t("Used by transportation vouchers."))

        # === Bottom summary card: which programs are selected ===
        # Join the short names of selected programs with commas.
        selected_names = ", ".join(PROGRAMS[key]["short_name"] for key in self.selected_programs)
        summary = self._card(self._step_host)
        summary.pack(fill="x", pady=(18, 0))
        summary_body = self._surface(summary)
        tk.Label(summary_body, text=self._t("Selected programs"), bg=CARD_BG, fg=MUTED, font=(FONT_FAMILY, self._font_size(10), "bold")).pack(anchor="w", padx=18, pady=(14, 2))
        tk.Label(
            summary_body,
            # If nothing is selected yet, show "None yet" instead of an empty string.
            text=selected_names or self._t("None yet"),
            bg=CARD_BG,
            fg=TEXT,
            font=(FONT_FAMILY, self._font_size(12)),
            wraplength=self._text_wrap() - 36,
            justify="left",
        ).pack(anchor="w", padx=18, pady=(0, 14))

    def _build_results_screen(self) -> None:
        """Build step 3: the results workspace (digest stats, controls, list of offices)."""
        # === Title and intro paragraph ===
        ttk.Label(self._step_host, text=self._t("Results workspace"), style="Title.TLabel").pack(anchor="w")
        tk.Label(
            self._step_host,
            text=self._t("Estimates only — not a government decision. Use filters, what-if income, maps, and exports to prepare a real visit."),
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
            tk.Label(cell, text=self._t(title), bg=CARD_BG, fg=MUTED, font=(FONT_FAMILY, self._font_size(11)), wraplength=140, justify="left").pack(anchor="w")

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
            text=f"Location: {self.user_data.get('location_input', self._t('Not provided'))}",
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
        tk.Label(rad_frame, text=self._t("Search radius"), bg=CARD_BG, fg=MUTED, font=(FONT_FAMILY, self._font_size(11))).pack(side="left", padx=(0, 8))
        self._radius_lbl = tk.Label(rad_frame, text="10 mi", bg=CARD_BG, fg=ACCENT, font=(FONT_FAMILY, self._font_size(11), "bold"), width=6)
        self._radius_lbl.pack(side="left", padx=(0, 8))
        rad_slider = ttk.Scale(rad_frame, from_=5, to=100, variable=self._radius_dbl, orient="horizontal", length=160)
        rad_slider.pack(side="left", padx=(0, 16))

        def _rad_motion(_event=None):
            v = round(self._radius_dbl.get())
            self._radius_lbl.configure(text=f"{v} mi")

        def _rad_release(_event=None):
            v = round(self._radius_dbl.get())
            self._radius_lbl.configure(text=f"{v} mi")
            self.radius_var.set(str(v))
            self.refresh_locations()

        rad_slider.bind("<Motion>", _rad_motion)
        rad_slider.bind("<ButtonRelease-1>", _rad_release)
        # Other action buttons in the same row.
        self._button(row_btns, self._t("Save CSV history"), self.save_case_history, "ghost").pack(side="left", padx=6)
        self._button(row_btns, self._t("Copy summary"), self.copy_results_summary, "ghost").pack(side="left", padx=6)
        self._button(row_btns, self._t("Print list"), self.print_office_list, "ghost").pack(side="left", padx=6)
        self._button(row_btns, self._t("Edit profile"), lambda: self.show_step(1), "ghost").pack(side="right", padx=6)

        # Third row: the "what-if" income slider.
        mid = tk.Frame(controls_body, bg=CARD_BG)
        mid.pack(fill="x", padx=22, pady=(8, 18))
        tk.Label(
            mid,
            text=self._t("What-if income (percent of the amount you entered — drag, then release to recalculate)"),
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

        # "What changed" label — updated by apply_income_scenario.
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

        # Bottom row: office search + sort + filter buttons.
        bot = tk.Frame(controls_body, bg=CARD_BG)
        bot.pack(fill="x", padx=22, pady=(4, 22))
        tk.Label(bot, text=self._t("Office list"), bg=CARD_BG, fg=TEXT, font=(FONT_FAMILY, self._font_size(12), "bold")).pack(anchor="w", pady=(0, 10))
        row_f = tk.Frame(bot, bg=CARD_BG)
        row_f.pack(fill="x", pady=(0, 8))
        # Search box.
        tk.Label(row_f, text=self._t("Search"), bg=CARD_BG, fg=MUTED, font=(FONT_FAMILY, self._font_size(11))).pack(side="left")
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
        tk.Label(row_f, text=self._t("Sort by"), bg=CARD_BG, fg=MUTED, font=(FONT_FAMILY, self._font_size(11))).pack(side="left")
        ttk.Combobox(row_f, values=("distance", "name"), width=11, state="readonly", textvariable=self.office_sort_var).pack(side="left", padx=(10, 14))
        self._button(row_f, self._t("Apply filter"), self._office_filter_changed, "secondary").pack(side="left", padx=6)
        self._button(row_f, self._t("Copy all addresses"), self.copy_all_office_addresses, "ghost").pack(side="right", padx=6)

        # Program filter + favorites row.
        prog_row = tk.Frame(bot, bg=CARD_BG)
        prog_row.pack(fill="x", pady=(0, 4))
        tk.Label(prog_row, text=self._t("Show:"), bg=CARD_BG, fg=MUTED, font=(FONT_FAMILY, self._font_size(11))).pack(side="left", padx=(0, 8))
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
            text=self._t("Favorites only ★"),
            variable=self.show_favorites_var,
            command=self._office_filter_changed,
        ).pack(side="left")

        # === Document checklist card ===
        docs = self._card(self._step_host)
        docs.pack(fill="x", pady=(0, 18))
        db = self._surface(docs)
        tk.Label(db, text=self._t("Visit checklist (sample)"), bg=CARD_BG, fg=TEXT, font=(FONT_FAMILY, self._font_size(15), "bold")).pack(anchor="w", padx=22, pady=(20, 6))
        tk.Label(
            db,
            text=self._t("Bring originals when possible. Offices may ask for different items."),
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
        old_statuses = {k: self.eligibility[k].status for k in self.selected_programs}
        u = dict(self.user_data)
        u["monthly_income"] = self._baseline_monthly * (pct / 100.0)
        self.eligibility = compute_eligibility(self.selected_programs, u)
        # Build "what changed" message.
        changes = []
        for k in self.selected_programs:
            old = old_statuses.get(k, "")
            new = self.eligibility[k].status
            if old != new:
                short = PROGRAMS[k]["short_name"]
                arrow = "↑" if new == "Highly eligible" or (new == "Partially eligible" and old == "Unlikely") else "↓"
                changes.append(f"{short}: {new} {arrow}")
        if hasattr(self, "_scenario_change_lbl"):
            if changes:
                self._scenario_change_lbl.configure(
                    text=f"At {pct:.0f}%: " + "  •  ".join(changes),
                    fg=SUCCESS if any("↑" in c for c in changes) else WARNING,
                )
            else:
                self._scenario_change_lbl.configure(text=self._t(f"No change at {pct:.0f}% — all programs stay the same"), fg=MUTED)
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
        # Program filter — only apply if at least one program is unchecked.
        active_progs = {k for k, v in self.prog_filter_vars.items() if v.get()}
        if active_progs != set(PROGRAMS.keys()):
            items = [x for x in items if any(p in active_progs for p in x["programs"])]
        # Favorites filter.
        if self.show_favorites_var.get():
            items = [x for x in items if _loc_key(x["location"]) in self.favorite_keys]
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

    def print_office_list(self) -> None:
        if not self._location_view:
            messagebox.showwarning(self._t("No offices"), self._t("No offices in current filter view."))
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
        self._toast(self._t("Office list opened in browser — use your browser's Print function"))

    def _toggle_lang(self) -> None:
        """Swap the UI language between English and Spanish and rebuild the current step."""
        self._lang = "es" if self._lang == "en" else "en"
        # Update button label.
        self._lang_btn.configure(text="EN" if self._lang == "es" else "ES")
        # Update persistent shell widgets (rail + nav) that were built once.
        step_keys = ["1. Choose subsidies", "2. Household profile", "3. Results & offices"]
        for lbl, key in zip(self.step_labels, step_keys):
            lbl.configure(text=self._t(key))
        self.back_button.configure(text=self._t("Back"))
        self._nav_startover_btn.configure(text=self._t("Start over"))
        self._nav_savedraft_btn.configure(text=self._t("Save draft"))
        self._nav_loaddraft_btn.configure(text=self._t("Load draft"))
        hint_base = "Sample rules only — always confirm with the office before applying."
        self._rail_hint.configure(text=f"{self._t(BRAND_SLOGAN)}. {self._t(hint_base)}")
        # Rebuild the current step with the new language.
        self.show_step(self.current_step)

    def _render_eligibility_cards(self) -> None:
        self._clear(self.results_frame.inner)
        wl = self._pane_text_wrap()
        tk.Label(self.results_frame.inner, text=self._t("Eligibility detail"), bg=APP_BG, fg=TEXT, font=(FONT_FAMILY, self._font_size(17), "bold")).pack(anchor="w", pady=(0, 16))
        for program_key in self.selected_programs:
            program = PROGRAMS[program_key]
            result = self.eligibility[program_key]
            card = self._card(self.results_frame.inner)
            card.pack(fill="x", pady=(0, 18), padx=(0, 10))
            card_body = self._surface(card)
            # For food programs, extract which specific programs (SNAP/WIC) user qualifies for
            display_name = program["name"]
            if program_key == "food" and result.passed:
                # Extract program names from passed text (e.g., "Income qualifies for SNAP (165% limit) and WIC (185% limit)")
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
                self._mini_list(card_body, self._t("Rules met"), result.passed, SUCCESS)
            if result.missed:
                self._mini_list(card_body, self._t("Needs review"), result.missed, WARNING)

    def _render_location_cards(self) -> None:
        self._clear(self.locations_frame.inner)
        wl = self._pane_text_wrap()
        tk.Label(self.locations_frame.inner, text=self._t("Nearby offices"), bg=APP_BG, fg=TEXT, font=(FONT_FAMILY, self._font_size(17), "bold")).pack(anchor="w", pady=(0, 16))
        eligible_keys = self.programs_for_locations()
        if not eligible_keys:
            self._empty_card(
                self.locations_frame.inner,
                self._t("No offices shown"),
                self._t("Offices appear only for programs marked Highly eligible or Partially eligible. Increase income scenario or adjust answers, then update the list."),
            )
            return
        if not self.location_results:
            self._empty_card(
                self.locations_frame.inner,
                self._t("No offices in radius"),
                self._t("Try a larger radius or a sample city such as Sunnyvale, San Jose, Oakland, Los Angeles, San Diego, or Sacramento."),
            )
            return
        if not self._location_view:
            self._empty_card(self.locations_frame.inner, self._t("No filter matches"), self._t("Clear the office search box or type part of a name, city, or street."))
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
            origin = str(self.user_data.get("location_input", ""))
            self._button(actions, self._t("Copy address"), partial(copy_to_clipboard, self, addr), "secondary").pack(side="left", padx=(0, 6))
            self._button(actions, self._t("Open in Maps"), partial(open_location_in_maps, _maps_query(location)), "ghost").pack(side="left", padx=(0, 6))
            self._button(actions, self._t("Directions"), partial(open_directions_in_maps, _maps_query(location), origin), "ghost").pack(side="left")
            fav_key = _loc_key(location)
            star_label = self._t("★ Saved") if fav_key in self.favorite_keys else self._t("☆ Save")
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
        
        # Use custom modern checkbox instead of ttk.Checkbutton
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
            self.session_id,
        )
        Path(path).write_text(html, encoding="utf-8")
        webbrowser.open(Path(path).as_uri())
        messagebox.showinfo("Draft saved", f"Application draft saved and opened in your browser:\n{path}")

    def go_next(self) -> None:
        """
        The 'Next' button handler — the wizard's brain. What it does depends on
        which step the user is currently on:

          Step 0 (program selection):
            → Validate that at least one program checkbox is ticked.
            → If OK, advance to step 1.

          Step 1 (household profile):
            → Validate all form fields (income, household size, location, etc.).
            → If OK, run compute_eligibility() to get the pass/fail results.
            → Find nearby offices, then advance to step 2 (results screen).

          Step 2 (results):
            → The 'Next' button becomes 'Save application' — saves a printable PDF/report.
        """
        if self.current_step == 0:
            # Step 0 → 1: make sure at least one program is checked.
            if self.collect_programs():
                self.show_step(1)
        elif self.current_step == 1:
            # Step 1 → 2: validate the profile, then run the eligibility engine.
            if self.collect_user_data():
                # Remember the income the user entered so the "what-if" slider works correctly.
                self._baseline_monthly = float(self.user_data["monthly_income"])
                # Reset the scenario slider and search filters so results are clean.
                self.income_scenario_pct.set(100.0)
                self.office_search_var.set("")
                self.office_sort_var.set("distance")
                # THE CORE STEP: run all the eligibility checks and store results.
                self.eligibility = compute_eligibility(self.selected_programs, self.user_data)
                # Find offices near the user that can help with programs they qualify for.
                self.refresh_location_data()
                # Advance to the results screen.
                self.show_step(2)
        else:
            # Step 2: save the application to disk.
            self.save_draft_application()

    def go_back(self) -> None:
        """Go back one step. Does nothing if already on step 0 (the first step)."""
        if self.current_step > 0:
            self.show_step(self.current_step - 1)

    def start_over(self) -> None:
        """
        Reset ALL form fields and results back to their initial/default values.
        Asks the user to confirm first because this action clears all their work.
        """
        # Show a Yes/No dialog — bail out if they click No.
        if not messagebox.askyesno("Start over", "Clear this run and start again?"):
            return
        # Reset all program checkboxes to unchecked.
        for variable in self.program_vars.values():
            variable.set(False)
        # Reset every form field to its default value.
        self.income_var.set("")                          # clear income amount
        self.income_period_var.set("Monthly")            # default: monthly
        self.household_var.set(3)                        # default household size
        self.location_var.set("")                        # clear ZIP/city
        self.state_var.set("California")                 # default state
        self.age_var.set("Adult")                        # default age range
        self.employment_var.set(EMPLOYMENT_OPTIONS[0])   # first option = "Working"
        self.residency_var.set(True)
        self.healthy_var.set(True)                     # default: is a resident
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
        self.income_scenario_pct.set(100.0)              # reset what-if slider to 100%
        self._baseline_monthly = 0.0                     # reset the baseline income
        self._location_view = []                         # clear filtered location results
        self.selected_programs = []                      # clear selected programs list
        self.user_data = {}                              # clear the household profile dict
        self.eligibility = {}                            # clear all eligibility results
        self.location_results = []                       # clear the list of nearby offices
        # Go back to the first step.
        self.show_step(0)


def parse_money(value: str) -> float:
    """
    Convert what the user typed in the income field into a plain float.
    Handles common formats like "$2,750", "2750", "2,750.00".

    Strips the dollar sign and commas first, then converts to a float.
    Raises ValueError if the string is empty or not a valid finite number
    (e.g. "infinity" or "NaN" would pass float() but fail isfinite).
    """
    # Remove $ signs and commas so "2,750" becomes "2750" before converting.
    cleaned = value.replace("$", "").replace(",", "").strip()
    if not cleaned:
        raise ValueError("empty amount")   # user left the field blank
    amount = float(cleaned)
    if not math.isfinite(amount):
        raise ValueError("invalid amount")  # reject inf/-inf/NaN
    return amount


def extract_zip(location_input: str) -> str | None:
    """
    Pull a 5-digit ZIP code out of whatever the user typed in the location field.
    Works for inputs like "94085", "Sunnyvale, CA 94085", "ZIP: 94085", etc.

    Returns the ZIP as a string (e.g. "94085"), or None if no ZIP is found.
    """
    # Look for any sequence of exactly 5 digits surrounded by word boundaries.
    match = re.search(r"\b\d{5}\b", location_input)
    if match:
        return match.group(0)   # return the first 5-digit match
    # Fallback: if the whole input is just 5 digits (no spaces/punctuation), treat it as a ZIP.
    stripped = location_input.strip()
    return stripped if stripped.isdigit() and len(stripped) == 5 else None


def extract_city(location_input: str) -> str | None:
    """
    Try to extract a recognizable city name from the user's location input.
    Only used when there's no ZIP code in the input.

    Strategy:
      1. Strip everything that isn't a letter or space.
      2. Lowercase and collapse multiple spaces.
      3. Check if any known city name (from CITY_COORDS) appears as a whole word.
         We check longest city names first to avoid "san" matching before "san jose".
      4. If no known city matches, return the cleaned text as-is (best-effort).

    Returns None if the input had a ZIP (handled by extract_zip instead).
    """
    # If there's a ZIP in the input, we don't need a city — return None.
    if extract_zip(location_input):
        return None
    # Strip everything except letters and spaces, then lowercase.
    city = re.sub(r"[^A-Za-z ]", " ", location_input).strip().lower()
    # Collapse multiple spaces into one (e.g. "san  jose" → "san jose").
    city = " ".join(city.split())
    if not city:
        return None   # input had no letters at all (e.g. just numbers)
    # Check against known cities — longest names first to avoid partial matches.
    for known_city in sorted(CITY_COORDS, key=len, reverse=True):
        if re.search(rf"\b{re.escape(known_city)}\b", city):
            return known_city   # found a match — return the canonical city name
    # No known city found — return whatever the user typed, cleaned up.
    return city


def extra_person_amount(state: str, program_key: str) -> int:
    # Look up the per-extra-person dollar increment for this state + program.
    # First checks the state-specific table; if not found, falls back to the
    # federal FPL-based defaults (used for internet). Returns 0 if unknown.
    return STATE_EXTRA_PERSON_AMOUNTS.get(state, {}).get(program_key, FPL_EXTRA_PERSON_AMOUNTS.get(program_key, 0))


def utility_eligibility_limit(utility_limits: dict[int, int], household_size: int, state: str) -> float:
    # Utility programs use whichever limit is HIGHER — the state's own table
    # or 150% of the federal poverty line. This protects households in states
    # with a low state limit but a relatively high poverty line.
    state_limit = limit_for_household(utility_limits, household_size, extra_person_amount(state, "utility"))
    fpl_limit = limit_for_household(FPL_150_LIMITS, household_size, FPL_150_EXTRA_PERSON_AMOUNT)
    return max(state_limit, fpl_limit)


def compute_eligibility(selected_programs: list[str], user_data: dict[str, object]) -> dict[str, ProgramResult]:
    """
    Run every selected program's eligibility rules and return a result for each.

    Food is handled separately by food_eligibility() because it has dual-path
    logic (SNAP + WIC) and state-specific FPL tables. Every other program goes
    through the standard checks → classify_program() pipeline.
    """
    results: dict[str, ProgramResult] = {}
    state = str(user_data.get("state", "California"))
    # Load this state's income limit tables. Falls back to California if unknown.
    limits = STATE_LIMITS.get(state, STATE_LIMITS["California"])
    for program_key in selected_programs:
        if program_key == "childcare":
            checks = childcare_checks(user_data, limits["childcare"], state)
        elif program_key == "food":
            # Food gets its own function — skips the generic classify_program() step.
            results[program_key] = food_eligibility(user_data, state)
            continue
        elif program_key == "utility":
            checks = utility_checks(user_data, limits["utility"], state)
        elif program_key == "internet":
            checks = internet_checks(user_data, limits["internet"], state)
        else:
            checks = transportation_checks(user_data, limits["transportation"], state)
        # Turn the list of rule checks into a single pass/fail result with an explanation.
        results[program_key] = classify_program(program_key, checks)
    return results


def childcare_checks(user: dict[str, object], childcare_limits: dict[int, int], state: str) -> list[RuleCheck]:
    """
    Returns a list of rules to check for childcare subsidy eligibility.
    Three rules:
      1. Income must be under the state's childcare limit.
      2. The parent/guardian must be working, studying, or in training.
         (Looking for work is treated as "close" — not a hard fail.)
      3. There must be a child under 13 in the household. (Critical — no child = instant Unlikely.)
    """
    # Get the income limit for this specific household size in this state.
    limit = limit_for_household(childcare_limits, int(user["household_size"]), extra_person_amount(state, "childcare"))
    income = float(user["monthly_income"])
    # Check if the parent has a qualifying activity (work, school, or training).
    working_or_studying = user["employment_status"] in {"Working", "In school or job training", "Working and in school"}
    return [
        income_check(income, limit, "Income is within the sample child-care limit"),
        RuleCheck(
            "Parent activity",
            working_or_studying,
            "Parent or caregiver is working, in school, or in job training.",
            "Child-care programs usually require a parent to work, study, or train.",
            close=user["employment_status"] == "Looking for work",  # "close" = not fully passing but borderline
        ),
        RuleCheck(
            "Child age",
            bool(user["child_under_13"]),
            "A child in the household is under age 13.",
            "This sample child-care subsidy is focused on children under age 13.",
            critical=True,  # critical=True means failing this alone causes "Unlikely" status
        ),
    ]


def food_eligibility(user: dict[str, object], state: str) -> ProgramResult:
    """
    Checks eligibility for two food assistance programs simultaneously:

      SNAP (Supplemental Nutrition Assistance Program, a.k.a. food stamps):
        - Income limit = 100% FPL × state's BBCE multiplier (e.g. 1.65 for Texas)
        - Multiplier comes from SNAP_STATE_MULTIPLIERS; defaults to 2.00 for broad states

      WIC (Women, Infants, and Children):
        - Only checked if there's a child under 5 in the household
        - Income limit = 100% FPL × 1.85 (fixed nationally at 185%)

    Alaska and Hawaii get their own higher FPL base tables because the federal
    government publishes separate poverty thresholds for those two states.

    Returns a ProgramResult directly (skips the generic classify_program step)
    because the dual-path logic and custom explanations don't fit the standard
    RuleCheck model used by other programs.
    """
    # Pull the four things we need from the user's form data.
    household_size = int(user["household_size"])
    gross_income = float(user["monthly_income"])
    has_child_under_5 = bool(user.get("child_under_5", False))  # defaults False for old drafts
    resident = bool(user["resident"])

    # Step 1: Pick the right FPL base table for this state.
    # Alaska and Hawaii have higher FPL values published by HHS.
    # Everyone else uses the standard continental US FPL table.
    if state == "Alaska":
        base_fpl = ALASKA_FPL_BASE
        extra_person = ALASKA_FPL_EXTRA_PERSON
    elif state == "Hawaii":
        base_fpl = HAWAII_FPL_BASE
        extra_person = HAWAII_FPL_EXTRA_PERSON
    else:
        base_fpl = FPL_100_LIMITS
        extra_person = FPL_BASE_EXTRA_PERSON_AMOUNTS["food"]

    # Step 2: Look up the 100% FPL dollar amount for this household size.
    # If the household is bigger than 8, extend the table by adding extra_person per head.
    fpl_100 = limit_for_household(base_fpl, household_size, extra_person)

    # Step 3: Calculate the actual income limits for each program.
    snap_multiplier = SNAP_STATE_MULTIPLIERS.get(state, 2.00)  # 2.00 = 200% for broad states
    snap_limit = fpl_100 * snap_multiplier   # e.g. $2,750 × 1.65 = $4,537 for TX family of 4
    wic_limit = fpl_100 * 1.85              # e.g. $2,750 × 1.85 = $5,088 nationally
    snap_pct = int(snap_multiplier * 100)    # e.g. 1.65 → 165 (used in explanation text)

    # Step 4: Residency is a hard requirement for both programs. Fail immediately if not met.
    if not resident:
        return ProgramResult(
            status="Unlikely",
            explanation="You may not qualify for food assistance based on this estimate because food assistance often requires US residency or qualified non-citizen status.",
            passed=[],
            missed=["Food assistance often requires US residency or qualified non-citizen status."],
        )

    # Step 5: Check both program paths independently.
    snap_eligible = gross_income <= snap_limit
    # WIC requires: child under 5 OR pregnant OR postpartum OR breastfeeding
    has_wic_criterion = (
        has_child_under_5 or 
        user.get("pregnant", False) or 
        user.get("postpartum", False) or 
        user.get("breastfeeding", False)
    )
    wic_eligible = has_wic_criterion and gross_income <= wic_limit

    # Step 6: If they qualify for either (or both), return a Highly eligible result.
    if snap_eligible or wic_eligible:
        # Build a list like ["SNAP (165% limit)", "WIC (185% limit)"]
        programs_qualified = []
        if snap_eligible:
            programs_qualified.append(f"SNAP ({snap_pct}% limit)")
        if wic_eligible:
            programs_qualified.append("WIC (185% limit)")
        qual_str = " and ".join(programs_qualified)  # e.g. "SNAP (165% limit) and WIC (185% limit)"
        explanation = f"Eligible for {qual_str}."
        # If income is above 100% FPL but still under the SNAP ceiling, warn that the
        # actual SNAP benefit amount is calculated after deducting rent and childcare.
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

    # Step 7: Not eligible for either — check if they're "close" (within 15% of a limit).
    # "Close" triggers "Partially eligible" instead of "Unlikely".
    close = gross_income <= snap_limit * 1.15 or (has_wic_criterion and gross_income <= wic_limit * 1.15)
    # Build a human-readable explanation of why they didn't qualify.
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
    Three rules for utility bill assistance:
      1. Income must be under whichever is higher — the state limit or 150% FPL.
      2. Household must report a bill hardship (past-due bill or shutoff notice).
      3. Must be a US resident or qualified non-citizen. (Critical — instant Unlikely if not.)
    """
    household_size = int(user["household_size"])
    # Use the higher of state limit vs. 150% FPL — see utility_eligibility_limit().
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
    Three rules for internet subsidy eligibility:
      1. Income must be under 200% FPL (the same limit for all states).
      2. Household must have a qualifying reason for needing internet (work, school, health, benefits).
      3. Must be a US resident. (Critical — instant Unlikely if not.)
    """
    # Internet uses a federal uniform limit — same for all states (200% FPL).
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
    Three rules for transportation voucher eligibility:
      1. Income must be under the state's transportation limit.
      2. Household must report a transportation need (work, school, medical).
      3. Applicant must have an active reason — working, studying, job-seeking, or a senior.
         (Retired is treated as "close" — not a hard fail.)
    """
    limit = limit_for_household(transportation_limits, int(user["household_size"]), extra_person_amount(state, "transportation"))
    income = float(user["monthly_income"])
    # These statuses count as "actively needing" transportation assistance.
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
            close=user["employment_status"] == "Retired",  # retired is borderline — not a hard fail
        ),
    ]


def income_check(income: float, limit: float, label: str) -> RuleCheck:
    # Reusable helper that builds a standard income rule check.
    # "close" is True if the income is within 15% above the limit — used to
    # show "Partially eligible" instead of "Unlikely" when someone is nearly there.
    return RuleCheck(
        "Income",
        income <= limit,
        f"{label}: {format_money(income)} monthly is at or below {format_money(limit)}.",
        f"Income is above the sample limit: {format_money(income)} monthly vs. {format_money(limit)}.",
        close=income <= limit * 1.15,
    )


def classify_program(program_key: str, checks: list[RuleCheck]) -> ProgramResult:
    """
    Takes the list of rule checks for a program and decides the overall status:

      "Highly eligible"    — passed every single rule
      "Partially eligible" — failed 1–2 rules, but all failures are "close" (borderline)
                             OR only one rule was failed at all
      "Unlikely"           — failed a critical rule, OR failed too many rules to be borderline

    Then generates a plain-English explanation and bundles it all into a ProgramResult.
    """
    # Split checks into passed and failed lists.
    passed = [check.pass_text for check in checks if check.passed]
    missed = [check.fail_text for check in checks if not check.passed]
    failures = [check for check in checks if not check.passed]
    critical_failures = [check for check in failures if check.critical]   # instant disqualifiers
    close_failures = [check for check in failures if check.close]         # borderline failures

    if not failures:
        # Passed everything — best possible result.
        status = "Highly eligible"
    elif critical_failures:
        # Any critical failure (e.g. no child under 13 for childcare) = Unlikely, no exceptions.
        status = "Unlikely"
    elif len(failures) <= 2 and (len(close_failures) == len(failures) or len(failures) == 1):
        # Failed 1–2 rules, but all of them are borderline → worth showing a partial result.
        status = "Partially eligible"
    else:
        # Too many failures or non-borderline failures → not looking good.
        status = "Unlikely"

    explanation = plain_language_explanation(program_key, status, passed, missed)
    return ProgramResult(status=status, explanation=explanation, passed=passed, missed=missed)


def plain_language_explanation(program_key: str, status: str, passed: list[str], missed: list[str]) -> str:
    # Generates a single human-readable sentence summarizing the result.
    # Food has its own custom explanation built inside food_eligibility(),
    # so this function is only called for childcare, utility, internet, and transportation.
    program_name = PROGRAMS[program_key]["short_name"].lower()
    if status == "Highly eligible":
        return f"You likely qualify for {program_name} because the sample rules are all met."
    if status == "Partially eligible":
        return f"You may qualify for {program_name}, but one or two details need review. An office can confirm whether exceptions or alternate rules apply."
    # Unlikely — lead with the primary reason they didn't qualify.
    primary_reason = missed[0] if missed else "multiple sample rules were not met."
    return f"You may not qualify for {program_name} based on this estimate because {primary_reason}"


def limit_for_household(table: dict[int, int], household_size: int, extra_person_amount: int) -> int:
    """
    Looks up the income limit for a given household size from a table.
    The tables only go up to 8 people. If the household is larger,
    we extend the table by adding `extra_person_amount` for each person beyond 8.

    Example: table has 8-person limit of $4,643. A 10-person household
    would be: $4,643 + (2 × $473) = $5,589.
    """
    if household_size in table:
        return table[household_size]
    # Household is larger than the table — extend it.
    largest = max(table)
    return table[largest] + (household_size - largest) * extra_person_amount


def find_locations(user_data: dict[str, object], eligibility: dict[str, ProgramResult], radius_miles: float) -> list[dict[str, object]]:
    """
    Find offices from the LOCATIONS list that:
      1. Offer at least one program the user is eligible for (Highly or Partially)
      2. Are within radius_miles of the user's ZIP/city

    Returns a list of dicts sorted by distance (closest first).
    Each dict has: "location" (the raw LOCATIONS entry), "programs" (list of matching
    program keys), "distance" (miles as float or None), "distance_text" (readable string).
    """
    # Build a set of program keys the user qualifies for — only those are worth showing offices for.
    eligible_programs = {
        key
        for key, result in eligibility.items()
        if result.status in {"Highly eligible", "Partially eligible"}  # skip Unlikely results
    }

    # Try to get the user's (lat, lon) from their ZIP or city so we can measure distance.
    user_coord = resolve_user_coord(user_data)
    user_zip = user_data.get("zip")     # e.g. "94085"
    user_city = user_data.get("city")   # e.g. "sunnyvale"
    results = []

    for location in LOCATIONS:
        # Only keep offices that offer at least one program the user qualifies for.
        matching_programs = [key for key in location["programs"] if key in eligible_programs]
        if not matching_programs:
            continue   # this office can't help — skip it

        # If the user wants healthy food only, skip food locations that aren't marked healthy.
        if user_data.get("healthy") and "food" in matching_programs and not location.get("healthy"):
            continue

        # Get the office's (lat, lon) so we can measure how far it is.
        loc_coord = ZIP_COORDS.get(location["zip"])
        # Compute distance in miles if we have both coordinates; otherwise None.
        distance = miles_between(user_coord, loc_coord) if user_coord and loc_coord else None
        # These are used as a fallback when we don't have coordinates.
        same_zip = user_zip and user_zip == location["zip"]
        same_city = user_city and user_city == location["city"].lower()

        if distance is not None:
            # We have real coordinates — only include if within the chosen radius.
            if distance > radius_miles:
                continue   # too far away
        elif not (same_zip or same_city):
            # No coordinates — only include if the ZIP or city matches exactly.
            continue

        results.append(
            {
                "location": location,               # the full office entry from LOCATIONS
                "programs": matching_programs,      # which programs this office can help with
                "distance": distance,               # float miles, or None if unknown
                "distance_text": format_distance(distance, same_zip),  # e.g. "2.3 mi"
            }
        )

    # Sort by distance first (9999 pushes unknowns to the bottom), then alphabetically by name.
    results.sort(key=lambda item: (9999 if item["distance"] is None else item["distance"], item["location"]["name"].lower()))
    return results


def resolve_user_coord(user_data: dict[str, object]) -> tuple[float, float] | None:
    """
    Figure out the user's (latitude, longitude) from what they typed.
    First tries to match by ZIP code, then by city name.
    Returns None if neither is found in our coordinate tables.
    """
    user_zip = user_data.get("zip")
    if user_zip and user_zip in ZIP_COORDS:
        # Found their ZIP in our table — use that coordinate directly.
        return ZIP_COORDS[str(user_zip)]
    city = user_data.get("city")
    if city and str(city).lower() in CITY_COORDS:
        # Found their city — use the city's center coordinate.
        return CITY_COORDS[str(city).lower()]
    # Neither ZIP nor city matched — we can't place them on a map.
    return None


def miles_between(start: tuple[float, float] | None, end: tuple[float, float] | None) -> float | None:
    """
    Calculate the straight-line distance in miles between two (lat, lon) points
    using the Haversine formula. This is the standard way to get accurate
    distances on a sphere (the Earth) from coordinates.

    Returns None if either coordinate is missing.
    """
    if not start or not end:
        return None   # can't measure without both points
    # Convert degrees → radians because Python's math functions expect radians.
    lat1, lon1 = map(math.radians, start)
    lat2, lon2 = map(math.radians, end)
    # Haversine formula — calculates the great-circle distance between two points.
    dlat = lat2 - lat1   # difference in latitude
    dlon = lon2 - lon1   # difference in longitude
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return 3958.8 * c   # 3958.8 = Earth's radius in miles


def format_distance(distance: float | None, same_zip: bool | None = False) -> str:
    """
    Convert a raw mile distance into a human-friendly label for display.
    Used in the location cards (e.g. "2.3 mi", "same ZIP", "nearby").
    """
    if same_zip:
        return "same ZIP"       # user and office share a ZIP — very close
    if distance is None:
        return "nearby"         # no coords available — just say nearby
    if distance < 0.2:
        return "same area"      # under a quarter mile — basically next door
    return f"{distance:.1f} mi"  # e.g. "4.7 mi"


def format_money(value: float) -> str:
    """Format a dollar amount with a $ sign and thousands comma. No cents.
    Example: 1330.0 → "$1,330"   |   12750.5 → "$12,751"
    """
    return f"${value:,.0f}"


def append_case_history(
    path: Path,                                    # path to the CSV file on disk
    selected_programs: list[str],                  # which programs were checked
    user_data: dict[str, object],                  # the household's profile
    eligibility: dict[str, ProgramResult],         # the eligibility results
    locations: list[dict[str, object]],            # nearby offices found
    radius: str,                                   # search radius in miles (as a string)
) -> None:
    """
    Append one row to the case history CSV file.

    Each row is a snapshot of a single screening session — who was screened,
    which programs were checked, and what the results were. This lets staff
    review usage over time without storing any personally identifiable info.

    The CSV is created automatically if it doesn't exist yet.
    New rows are always appended (not overwritten) so history is never lost.
    """
    # Check if the file already exists so we know whether to write the header row.
    file_exists = path.exists()
    # Open in append mode ("a") so existing rows are never overwritten.
    with path.open("a", newline="", encoding="utf-8") as file:
        # DictWriter lets us write dicts as rows, using the fieldnames as column headers.
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "timestamp",          # when this screening happened
                "selected_programs",  # which programs the user checked
                "monthly_income",     # monthly gross income entered
                "household_size",     # number of people in the household
                "location",           # ZIP or city the user entered
                "age_range",          # age group of the applicant
                "employment_status",  # their employment situation
                "radius_miles",       # how wide the office search was
                "eligibility",        # results per program (e.g. "food: Highly eligible")
                "location_count",     # how many nearby offices were found
            ],
        )
        # Only write the header once — when the file is brand new.
        if not file_exists:
            writer.writeheader()
        # Write one row for this session.
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
                # Compact summary of all results — e.g. "food: Highly eligible; utility: Unlikely"
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
    """Extract specific program names (SNAP/WIC, etc.) from eligibility result if available."""
    if program_key == "food" and result.passed:
        for passed_item in result.passed:
            if "qualifies for" in passed_item.lower():
                # Extract program name from "Income qualifies for SNAP (165% limit)"
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
    child_u5 = "Yes" if user_data.get("child_under_5") else "No"
    utility_hardship = "Yes" if user_data.get("utility_hardship") else "No"
    internet_need = "Yes" if user_data.get("internet_need") else "No"
    transport_need = "Yes" if user_data.get("transportation_need") else "No"

    # ── summary pills row ─────────────────────────────────────────────────────
    summary_pills = "".join(
        f'<div style="display:flex;align-items:center;gap:12px;padding:12px 0;'
        f'border-bottom:1px solid #f1f5f9;">'
        f'<span style="font-weight:600;color:#1e293b;min-width:190px;">'
        f'{_get_program_display_name(k, eligibility[k])}</span>'
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
    """Keep `value` between `low` and `high` (inclusive).
    Example: clamp(150, 9, 22) → 22    |    clamp(5, 9, 22) → 9
    Used mainly to keep font sizes from going crazy in accessibility mode.
    """
    return max(low, min(high, value))


def safe_get_program_short_names(program_keys: list[str]) -> str:
    """Turn a list of program keys into a comma-separated string of short names.
    Skips any key that isn't in the PROGRAMS dict so unknown keys don't crash the app.
    Example: ["food", "utility"] → "Food, Utilities"
    """
    return ", ".join(PROGRAMS[key]["short_name"] for key in program_keys if key in PROGRAMS)


def sanitize_location_text(text: str) -> str:
    """Strip leading/trailing whitespace and collapse multiple spaces into one.
    Example: "  San   Jose  " → "San Jose"
    Used before displaying or saving location strings.
    """
    return " ".join(text.strip().split())


# ===========================================================================
# ENTRY POINT
# ---------------------------------------------------------------------------
# Python only runs the code below if this file is executed directly
# (e.g. `python BenefitBridge.py`). If the file is imported by another
# script, this block is skipped — important for testing and packaging.
# ===========================================================================
if __name__ == "__main__":
    # Create the main application window (which calls __init__ and builds the UI).
    app = BenefitBridgeApp()
    # Hand control to Tk's event loop — this runs forever until the window is closed.
    app.mainloop()


