"""
live_load_data.py -- gathers the Chapter 3 live-load data.

Reads the vehicles the user ticked in the Loading tab, looks the loads up in
the IRC 6 module the analysis itself uses, and hands plain rows to
live_load_tables.py for rendering.

Design rules
* Only vehicles ticked in the UI appear, in the same order as the UI.
* Loads come from IRC6_2017 wherever it defines the vehicle, converted to kN
  by dividing by keyfile.kN (so the result is right whatever base unit the
  module uses).  Totals therefore match what the analysis applies
  (1 t = 9.81 kN), not the rounded 10 kN/t of the IRC tables.
* A value that cannot be obtained is None and is printed as "--".  The
  report never invents a number.
"""
from osdagbridge.core.reports.live_load_tables import VehicleRow, vehicle_table, footpath_table
from osdagbridge.core.utils.common import (
    KEY_BL_ECCENTRICITY,
    KEY_BL_IRC_70R_BOGIE,
    KEY_BL_IRC_70R_TRACKED,
    KEY_BL_IRC_70R_WHEELED,
    KEY_BL_IRC_AA_TRACKED,
    KEY_BL_IRC_AA_WHEELED,
    KEY_BL_IRC_CLASS_A,
    KEY_BL_IRC_CLASS_FATIGUE,
    KEY_BL_IRC_CLASS_SV,
    KEY_FOOTPATH,
    KEY_LL_CUSTOM_VEHICLES,
    KEY_LL_ECCENTRICITY,
    KEY_LL_FOOTPATH_PRESSURE_MODE,
    KEY_LL_FOOTPATH_PRESSURE_VALUE,
    KEY_LL_IRC_70R_BOGIE,
    KEY_LL_IRC_70R_TRACKED,
    KEY_LL_IRC_70R_WHEELED,
    KEY_LL_IRC_AA_TRACKED,
    KEY_LL_IRC_AA_WHEELED,
    KEY_LL_IRC_CLASS_A,
    KEY_LL_IRC_CLASS_FATIGUE,
    KEY_LL_IRC_CLASS_SV,
    KEY_SPAN,
    KEY_TS_FOOTPATH_WIDTH,
)

# IRC 6 Cl. 211.3: braking force acts 1.2 m above the road surface.
DEFAULT_ECCENTRICITY_M = 1.2
# IRC 6 Cl. 211.2: 20 % of the first train.  One-lane value; extra trains and
# lanes are not included (stated in the table note).
BRAKING_FRACTION = 0.20
# IRC 6 Cl. 204.1 Class AA loads in tonnes.  IRC6_2017 does not define Class
# AA, so these standard values are converted with the same g the module uses.
CLASS_AA_WHEELED_T = 40.0
CLASS_AA_TRACKED_T = 70.0

# (label, selection key, kind, braking-flag key, braking considered by default)
# Order follows the Loading tab.
_VEHICLES = [
    ("Class A",             KEY_LL_IRC_CLASS_A,     "A",       KEY_BL_IRC_CLASS_A,      True),
    ("Class AA (Wheeled)",  KEY_LL_IRC_AA_WHEELED,  "wheeled", KEY_BL_IRC_AA_WHEELED,   True),
    ("Class AA (Tracked)",  KEY_LL_IRC_AA_TRACKED,  "tracked", KEY_BL_IRC_AA_TRACKED,   True),
    ("Class 70R (Wheeled)", KEY_LL_IRC_70R_WHEELED, "wheeled", KEY_BL_IRC_70R_WHEELED,  True),
    ("Class 70R (Tracked)", KEY_LL_IRC_70R_TRACKED, "tracked", KEY_BL_IRC_70R_TRACKED,  True),
    ("Class 70R (Bogie)",   KEY_LL_IRC_70R_BOGIE,   "wheeled", KEY_BL_IRC_70R_BOGIE,    True),
    ("Class SV",            KEY_LL_IRC_CLASS_SV,    "sv",      KEY_BL_IRC_CLASS_SV,     False),
    ("Class Fatigue",       KEY_LL_IRC_CLASS_FATIGUE, "fatigue", KEY_BL_IRC_CLASS_FATIGUE, False),
]


def _truthy(v):
    if isinstance(v, str):
        return v.strip().lower() not in ("", "0", "false", "no", "none")
    return bool(v)


def _float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _total_load_kn(label, kind):
    """Total vehicle load in kN, or None when the module does not define it."""
    from osdagbridge.core.utils.codes.irc6_2017 import IRC6_2017
    from osdagbridge.core.utils.codes.keyfile import kN, g
    try:
        if label == "Class A":
            return sum(IRC6_2017.cl_204_1_ClassA_vehicle()["wheel_loads"]) / kN
        if label == "Class 70R (Wheeled)":
            return sum(IRC6_2017.cl_204_1_Class70R_vehicle_wheel()["wheel_loads"]) / kN
        if label == "Class 70R (Tracked)":
            v = IRC6_2017.cl_204_1_Class70R_vehicle_track()
            length = abs(v["x"][-1] - v["x"][0])          # m (module uses m = 1)
            return v["wheel_loads_udl"] * length * len(v["z"]) / kN
        if label == "Class SV":
            return IRC6_2017.cl_204_5_1_special_vehicle()["total_load_kN"]  # already kN
        if label == "Class Fatigue":
            return sum(IRC6_2017.cl_204_6_fatigue_load()["wheel_loads"]) / kN
        if label == "Class AA (Wheeled)":
            return CLASS_AA_WHEELED_T * g
        if label == "Class AA (Tracked)":
            return CLASS_AA_TRACKED_T * g
    except Exception:
        return None
    return None          # e.g. "Class 70R (Bogie)": not defined as a separate vehicle


def _impact_factor(kind, span):
    """Impact factor (1 + IM) per IRC 6 Cl. 208.2 / 208.3 for the vehicle type.

    The IRC6_2017.cl_208_3 helper cannot be used: it tests the constant list
    KEY_VEHICLE instead of the vehicle, so it always returns the tracked value.
    """
    if span is None or kind not in ("A", "wheeled", "tracked"):
        return None
    from osdagbridge.core.utils.codes.irc6_2017 import IRC6_2017
    try:
        if kind == "A":
            return round(1.0 + IRC6_2017.cl_208_2_impact_factor(span), 3)
        formula = 9.0 / (13.5 + min(span, 45.0))
        if span > 45.0:
            im = formula
        elif kind == "wheeled":
            im = 0.25 if span < 23.0 else formula
        else:  # tracked
            im = 0.25 if span < 5.0 else 0.10
        return round(1.0 + im, 3)
    except Exception:
        return None


def vehicle_rows(input_dict):
    """One VehicleRow per vehicle ticked in the Loading tab, in UI order."""
    span = _float(input_dict.get(KEY_SPAN))
    ecc = (_float(input_dict.get(KEY_LL_ECCENTRICITY))
           or _float(input_dict.get(KEY_BL_ECCENTRICITY))
           or DEFAULT_ECCENTRICITY_M)
    rows = []
    for label, sel_key, kind, bl_key, default_braking in _VEHICLES:
        if not _truthy(input_dict.get(sel_key)):
            continue
        flag = input_dict.get(bl_key)
        considered = default_braking if flag is None else _truthy(flag)
        total = _total_load_kn(label, kind)
        value = BRAKING_FRACTION * total if (considered and total is not None) else None
        rows.append(VehicleRow(label, total, _impact_factor(kind, span),
                               considered, value, ecc if considered else None))
    custom = input_dict.get(KEY_LL_CUSTOM_VEHICLES)
    if isinstance(custom, list):
        for c in custom:
            name = c.get("name") if isinstance(c, dict) else c
            if isinstance(name, str) and name.strip():
                rows.append(VehicleRow(name.strip(), None, None, False))
    return rows


def footpath_args(input_dict):
    """Arguments for footpath_table(): option, width, mode, pressure."""
    option = str(input_dict.get(KEY_FOOTPATH, "None") or "None")
    width = _float(input_dict.get(KEY_TS_FOOTPATH_WIDTH))
    mode = str(input_dict.get(KEY_LL_FOOTPATH_PRESSURE_MODE, "") or "")
    pressure = None
    if mode.strip().lower() in ("automatic", "as per irc 6", "as per irc6", ""):
        try:
            from osdagbridge.core.utils.codes.irc6_2017 import IRC6_2017
            pressure = float(IRC6_2017.cl_206_1_footway_load())
        except Exception:
            pressure = _float(input_dict.get(KEY_LL_FOOTPATH_PRESSURE_VALUE))
    else:
        pressure = _float(input_dict.get(KEY_LL_FOOTPATH_PRESSURE_VALUE))
    return option, width, mode, pressure


def live_load_block(input_dict):
    """Vehicle table + footpath table, ready to drop into Chapter 3."""
    return (vehicle_table(vehicle_rows(input_dict))
            + "\n\\vspace{1em}\n"
            + footpath_table(*footpath_args(input_dict)))