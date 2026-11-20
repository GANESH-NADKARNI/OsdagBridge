"""
live_load_tables.py -- Chapter 3 live-load tables.

Renders two separate tables (task item 3):

  Table 3.3  Live Loads -- Vehicles
             Vehicle | Total Load (kN) | Impact Factor | Braking Load
                                                        Considered? | Value (kN) | Eccentricity (m)
  Table 3.4  Live Loads -- Footpath

Rendering is kept apart from data gathering: these functions only take plain
values, so they can be tested without running a design.  Which vehicles
appear is decided by the caller from the Loading tab selection.
"""
from dataclasses import dataclass
from typing import List, Optional

from osdagbridge.core.reports.latex_tables import MAX_SHORT_ROWS, longtable, short_table
from osdagbridge.core.reports.report_utils import _tex

DASH = "--"


@dataclass
class VehicleRow:
    name: str                              # e.g. "Class 70R (Wheeled)"
    total_load_kn: Optional[float]         # None -> "--"
    impact_factor: Optional[float]         # None -> "--"
    braking_considered: bool
    braking_value_kn: Optional[float] = None
    eccentricity_m: Optional[float] = None


def _num(v, fmt):
    return DASH if v is None else format(v, fmt)


def vehicle_table(rows: List[VehicleRow], caption="Live Loads -- Vehicles") -> str:
    """Vehicle live-load table with a grouped 'Braking Load' header."""
    # Widths exclude cell padding (2 x 4pt per column, set below), so the
    # column sum is kept near 14.0cm to fit the 15.9cm text width.
    colspec = r"|L{2.8cm}|C{2.3cm}|C{1.8cm}|C{2.7cm}|C{1.9cm}|C{2.5cm}|"
    header = (
        r"\multirow{2}{*}{\textbf{Vehicle}} & "
        r"\multirow{2}{*}{\makecell{\textbf{Total Load}\\\textbf{(kN)}}} & "
        r"\multirow{2}{*}{\makecell{\textbf{Impact}\\\textbf{Factor}}} & "
        r"\multicolumn{3}{c|}{\textbf{Braking Load}} \\ \cline{4-6}" "\n"
        r" & & & \textbf{Considered?} & \makecell{\textbf{Value}\\\textbf{(kN)}} & "
        r"\makecell{\textbf{Eccentricity}\\\textbf{(m)}}"
    )
    if rows:
        body = ""
        for r in rows:
            body += (
                _tex(r.name) + " & "
                + _num(r.total_load_kn, ",.0f") + " & "
                + _num(r.impact_factor, ".3f") + " & "
                + ("Yes" if r.braking_considered else "No") + " & "
                + (_num(r.braking_value_kn, ",.2f") if r.braking_considered else DASH) + " & "
                + (_num(r.eccentricity_m, ".2f") if r.braking_considered else DASH)
                + " \\\\[\\rowgap]\n\\hline\n"
            )
    else:
        body = (r"\multicolumn{6}{|c|}{\textit{No vehicle selected in the Loading tab}}"
                " \\\\[\\rowgap]\n\\hline\n")
    note = (r"Note: Total loads follow the IRC 6 vehicle definitions used in the analysis "
            r"(1\,t = 9.81\,kN); Class AA uses the standard IRC 6 Cl.~204.1 loads. "
            r"Impact factor per IRC 6 Cl.~208.2 / 208.3 for the vehicle type. "
            r"Braking value = 20\,\% of the vehicle load (first train, one lane, IRC 6 Cl.~211.2), "
            r"acting at the eccentricity shown above the deck surface. "
            r"``--'': not applicable or not defined.")
    build = short_table if len(rows) <= MAX_SHORT_ROWS else longtable
    tbl = build(colspec, caption, header, body, note=note)
    return "\\begingroup\\setlength{\\tabcolsep}{\\tabcolsepTight}\n" + tbl + "\\endgroup\n"


def footpath_table(footpath_option: str, width_m: Optional[float],
                   mode: str, pressure_kn_m2: Optional[float],
                   caption="Live Loads -- Footpath") -> str:
    """Footpath live-load table; a one-line note when no footpath is provided."""
    if str(footpath_option).strip().lower() in ("", "none"):
        return (r"\noindent\textit{No footpath is provided; footpath live load "
                r"is not applicable.}\par\vspace{\gapNote}" "\n")
    colspec = r"|L{4.2cm}|C{2.8cm}|C{1.5cm}|L{3.4cm}|"
    header = (r"\textbf{Parameter} & \textbf{Value} & \textbf{Unit} & "
              r"\textbf{Source}")
    is_auto = str(mode).strip().lower() in ("automatic", "as per irc 6", "as per irc6")
    rows = [
        ("Footpath provision", _tex(footpath_option), DASH, "Basic Inputs"),
        ("Footpath width", _num(width_m, ".2f"), "m", "IRC 5 Cl. 104.3.6"),
        ("Pressure mode", _tex("As per IRC 6" if is_auto else "User-defined"), DASH,
         "Loading tab"),
        ("Footpath live load pressure", _num(pressure_kn_m2, ".2f"), r"kN/m\textsuperscript{2}",
         "IRC 6 Cl. 206.1" if is_auto else "User input"),
    ]
    body = "".join(f"{a} & {b} & {c} & {d} \\\\[\\rowgap]\n\\hline\n" for a, b, c, d in rows)
    return short_table(colspec, caption, header, body)