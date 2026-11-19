"""
report_charts.py -- matplotlib charts embedded in the design report.

Utilization-ratio charts for Section 5.5 (task item 4).  Material-quantity
charts for Chapter 7 are added to this module as well (task item 5).

* The Figure API is used directly, never pyplot, so charts can be made from the
  GUI's worker thread without touching a global matplotlib state.
* Appearance (size, dpi, colours, threshold line) comes from styles.CHART and
  styles.PALETTE.
* Every function returns None instead of raising when data is missing, and the
  LaTeX snippet is then simply empty, so a missing result can never stop
  report generation.
* UR numbers are taken with the same helpers the Executive Summary uses, so the
  chart and the summary cannot disagree.
"""
import os

from matplotlib.figure import Figure

from osdagbridge.core.reports import styles


# ─────────────────────────────────────────────────────────────────────────────
# Drawing
# ─────────────────────────────────────────────────────────────────────────────
def _save(fig, path):
    fig.savefig(path, dpi=styles.CHART["dpi"], bbox_inches="tight", format="png")
    return path.replace("\\", "/")


def ur_bar_chart(labels, values, path, title=None):
    """Bar chart of utilization ratios with a red dashed line at UR = 1.0.

    Bars at or below the threshold are drawn in the 'pass' colour, bars above
    it in the 'fail' colour.  A value of None keeps its place on the axis and
    is marked "N/A" (no result available), so every element the report covers
    is visible.  Returns the saved path, or None when there is no data at all.
    """
    labels, values = list(labels), list(values)
    if not labels or all(v is None for v in values):
        return None
    c = styles.CHART
    limit = c["ur_threshold"]
    real = [v for v in values if v is not None]

    fig = Figure(figsize=c["figsize"])
    ax = fig.subplots()
    xs = range(len(labels))
    colors = [(styles.hex_("pass_green") if v <= limit else styles.hex_("fail_red"))
              if v is not None else "none" for v in values]
    bars = ax.bar(xs, [v or 0 for v in values], width=c["bar_width"], color=colors, zorder=3)
    ax.set_xticks(list(xs))
    ax.set_xticklabels(labels)

    ax.axhline(limit, color=styles.hex_("fail_red"), linestyle=c["ur_threshold_style"],
               linewidth=1.4, zorder=4, label=c["ur_threshold_label"])
    top = max(max(real), limit)
    ax.set_ylim(0, top * 1.18)
    ax.set_ylabel("Utilization Ratio (Demand / Capacity)", fontsize=c["font_size"])
    ax.tick_params(labelsize=c["font_size"])
    ax.grid(axis="y", color=styles.hex_("grid"), linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for b, v in zip(bars, values):
        x = b.get_x() + b.get_width() / 2
        if v is None:
            ax.annotate("N/A", (x, 0), xytext=(0, 4), textcoords="offset points",
                        ha="center", va="bottom", fontsize=c["font_size"],
                        color="#777777", style="italic", zorder=5)
        elif 0.75 * limit <= v <= limit:
            # in the top quarter below the threshold line: label inside the bar so the
            # dashed line cannot touch the number (an outside label needs ~0.13 of headroom)
            ax.annotate(f"{v:.2f}", (x, v), xytext=(0, -3), textcoords="offset points",
                        ha="center", va="top", fontsize=c["font_size"],
                        fontweight="bold", color="white", zorder=5)
        else:
            ax.annotate(f"{v:.2f}", (x, v), xytext=(0, 3), textcoords="offset points",
                        ha="center", va="bottom", fontsize=c["font_size"],
                        fontweight="bold", zorder=5)
    ax.legend(loc="upper right", fontsize=c["font_size"], frameon=False)
    if title:
        ax.set_title(title, fontsize=c["title_size"], fontweight="bold")
    return _save(fig, path)


# ─────────────────────────────────────────────────────────────────────────────
# Data
# ─────────────────────────────────────────────────────────────────────────────
def collect_ur_data(output_dict):
    """DEPRECATED (use build_ur_figures, which matches Table 5.29 exactly).

    Return ({element: max UR}, {girder: max UR}) from the stored results.

    Mirrors executive_summary.executive_summary(): girder URs are the largest
    'dcr' of each girder's checks, the deck UR is the largest 'ur_*' entry,
    and cross bracing / end diaphragm use the largest member efficiency.
    """
    from osdagbridge.core.reports.executive_summary import _max_float, _max_member_efficiency

    design = (output_dict.get("design_results") or {})
    per_girder = design.get("per_girder") or {}
    deck = output_dict.get("deck_design_results") or {}

    girders = {}
    for g, gd in per_girder.items():
        if str(g).startswith("EB"):               # edge-beam pseudo girders
            continue
        m = _max_float([c.get("dcr") for c in (gd.get("checks") or [])])
        if m is not None:
            girders[str(g)] = m

    elements = {}
    if girders:
        elements["Steel Plate\nGirders"] = max(girders.values())
    m = _max_float([v for k, v in deck.items() if str(k).startswith("ur_")])
    if m is not None:
        elements["Concrete\nDeck Slab"] = m
    m = _max_member_efficiency(output_dict.get("crossbracing_design_results"))
    if m is not None:
        elements["Cross\nBracing"] = m
    m = _max_member_efficiency(output_dict.get("end_diaphragm_design_results"))
    if m is not None:
        elements["End\nDiaphragms"] = m
    return elements, girders


def make_ur_charts(output_dict, out_dir):
    """Write the Section 5.5 charts into out_dir; return {name: path}.

    A chart that cannot be drawn is simply left out of the result.
    """
    paths = {}
    try:
        os.makedirs(out_dir, exist_ok=True)
        elements, girders = collect_ur_data(output_dict)
        p = ur_bar_chart(list(elements), list(elements.values()),
                         os.path.join(out_dir, "ur_overall.png"))
        if p:
            paths["ur_overall"] = p
        if len(girders) > 1:        # one girder adds nothing beyond the overall chart
            p = ur_bar_chart(list(girders), list(girders.values()),
                             os.path.join(out_dir, "ur_girders.png"))
            if p:
                paths["ur_girders"] = p
    except Exception:
        # Never let a chart problem block the report.
        import logging
        logging.getLogger(__name__).exception("UR chart generation failed")
    return paths


# Table 5.29 row label prefix -> chart element (labels contain LaTeX dashes)
_ELEMENT_OF_ROW = [
    ("Girder", "Steel Plate\nGirders"),
    ("Transverse Shear (slab)", "Concrete\nDeck Slab"),
    ("Crack Width (slab)", "Concrete\nDeck Slab"),
    ("Deck", "Concrete\nDeck Slab"),
    ("Cross Bracing", "Cross\nBracing"),
    ("End Diaphragm", "End\nDiaphragms"),
]
ELEMENTS = ["Steel Plate\nGirders", "Concrete\nDeck Slab", "Cross\nBracing", "End\nDiaphragms"]


def parse_ur_cell(cell):
    """Number inside a formatted UR cell such as '0.94' or '\\textcolor{red}{1.85}'.
    Returns None for '---', 'N/A' and empty cells."""
    import re
    if not cell:
        return None
    m = re.search(r"\d+(?:\.\d+)?", str(cell))
    return float(m.group(0)) if m else None


def elements_from_log(ur_log):
    """{element: max UR or None} from Table 5.29's rows.

    ur_log is a list of (row label, UR cell text) recorded while the table is
    built, so the chart shows exactly the numbers the table prints.
    """
    out = {e: None for e in ELEMENTS}
    for label, cell in ur_log:
        label = str(label).strip()
        for prefix, element in _ELEMENT_OF_ROW:
            if label.startswith(prefix):
                v = parse_ur_cell(cell)
                if v is not None and (out[element] is None or v > out[element]):
                    out[element] = v
                break
    return out


def girder_urs(output_dict, input_dict=None):
    """{girder: max UR} for the girders the bridge actually has.

    The girder list comes from the inputs (the same list every report table
    uses); without inputs, every non edge-beam girder in the results is shown.
    """
    from osdagbridge.core.reports.report_utils import get_girder_entries
    from osdagbridge.core.reports.executive_summary import _max_float

    per_girder = ((output_dict or {}).get("design_results") or {}).get("per_girder") or {}
    allowed = None
    if input_dict:
        allowed = {str(lbl) for lbl, _ in get_girder_entries(input_dict) if lbl}
    out = {}
    for g, gd in per_girder.items():
        if str(g).startswith("EB") or (allowed and str(g) not in allowed):
            continue
        m = _max_float([c.get("dcr") for c in (gd.get("checks") or [])])
        if m is not None:
            out[str(g)] = m
    return out


def build_ur_figures(ur_log, output_dict, input_dict, chart_dir):
    """Draw the Section 5.5 charts into chart_dir and return their LaTeX.

    Never raises: any problem is logged and yields an empty string.
    """
    try:
        os.makedirs(chart_dir, exist_ok=True)
        paths = {}
        el = elements_from_log(ur_log)
        p = ur_bar_chart(list(el), list(el.values()), os.path.join(chart_dir, "ur_overall.png"))
        if p:
            paths["ur_overall"] = p
        gd = girder_urs(output_dict, input_dict)
        if len(gd) > 1:
            p = ur_bar_chart(list(gd), list(gd.values()), os.path.join(chart_dir, "ur_girders.png"))
            if p:
                paths["ur_girders"] = p
        return ur_figures_tex(paths)
    except Exception:
        import logging
        logging.getLogger(__name__).exception("UR chart generation failed")
        return ""


# ─────────────────────────────────────────────────────────────────────────────
# Material quantities (Chapter 7)
# ─────────────────────────────────────────────────────────────────────────────
def parse_quantity(v):
    """Float from a quantity string such as '32.89'; None for 'N.A.', '' or None."""
    try:
        return float(str(v).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def steel_quantities(q):
    """{element: steel weight in MT or None} from the Table 7.1 quantity strings.

    Cross bracing is the sum of its top chord, bottom chord and diagonal rows.
    End-diaphragm steel is not part of the quantity take-off (no key exists in
    calculate_material_quantities), so it is reported as None -> "N/A".
    """
    parts = [parse_quantity(q.get(k)) for k in
             ("bracing_top_wt_total", "bracing_bot_wt_total", "bracing_diag_wt_total")]
    bracing = sum(p for p in parts if p is not None) if any(p is not None for p in parts) else None
    return {
        "Girders": parse_quantity(q.get("steel_girders_wt_total")),
        "Cross\nBracing": bracing,
        "End\nDiaphragms": None,
    }


def _style_axes(ax):
    c = styles.CHART
    ax.tick_params(labelsize=c["font_size"])
    ax.grid(axis="y", color=styles.hex_("grid"), linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)


def quantity_bar_chart(labels, values, path, ylabel, color_key="steel_blue", fmt="{:.2f}"):
    """Simple bar chart; a value of None keeps its slot and is marked "N/A"."""
    labels, values = list(labels), list(values)
    real = [v for v in values if v is not None]
    if not labels or not real:
        return None
    c = styles.CHART
    fig = Figure(figsize=c["figsize"])
    ax = fig.subplots()
    xs = list(range(len(labels)))
    bars = ax.bar(xs, [v or 0 for v in values], width=c["bar_width"],
                  color=[styles.hex_(color_key) if v is not None else "none" for v in values], zorder=3)
    ax.set_xticks(xs)
    ax.set_xticklabels(labels)
    top = max(real) if max(real) > 0 else 1.0
    ax.set_ylim(0, top * 1.18)
    ax.set_ylabel(ylabel, fontsize=c["font_size"])
    _style_axes(ax)
    for b, v in zip(bars, values):
        x = b.get_x() + b.get_width() / 2
        if v is None:
            ax.annotate("N/A", (x, 0), xytext=(0, 4), textcoords="offset points", ha="center",
                        va="bottom", fontsize=c["font_size"], color="#777777", style="italic")
        else:
            ax.annotate(fmt.format(v), (x, v), xytext=(0, 3), textcoords="offset points",
                        ha="center", va="bottom", fontsize=c["font_size"], fontweight="bold")
    return _save(fig, path)


def concrete_rebar_chart(volume_m3, weight_mt, path):
    """Concrete volume (m3) and reinforcement weight (MT) as two side-by-side panels.

    The quantities have different units, so each gets its own panel and axis.
    A shared plot (or twin axes) would stretch both bars to the same height
    and suggest the two numbers are comparable.
    """
    if volume_m3 is None and weight_mt is None:
        return None
    c = styles.CHART
    fig = Figure(figsize=c["figsize"])
    axes = fig.subplots(1, 2)
    panels = (
        (axes[0], volume_m3, "concrete", "Concrete, deck slab", "Volume (m$^3$)", "{:.2f} m$^3$"),
        (axes[1], weight_mt, "rebar", "Reinforcement steel", "Weight (MT)", "{:.2f} MT"),
    )
    for ax, v, color_key, title, ylabel, txt in panels:
        ax.bar([0], [v or 0], width=0.5, color=styles.hex_(color_key) if v is not None else "none", zorder=3)
        ax.set_xlim(-0.6, 0.6)
        ax.set_xticks([])
        ax.set_ylim(0, (v or 1.0) * 1.25)
        ax.set_ylabel(ylabel, fontsize=c["font_size"])
        ax.set_title(title, fontsize=c["font_size"], fontweight="bold")
        _style_axes(ax)
        if v is None:
            ax.annotate("N/A", (0, 0), xytext=(0, 4), textcoords="offset points", ha="center",
                        va="bottom", fontsize=c["font_size"], color="#777777", style="italic")
        else:
            ax.annotate(txt.format(v), (0, v), xytext=(0, 3), textcoords="offset points",
                        ha="center", va="bottom", fontsize=c["font_size"], fontweight="bold")
    fig.tight_layout()
    return _save(fig, path)


def build_material_figures(quantities, chart_dir):
    """Draw the Chapter 7 charts into chart_dir and return their LaTeX.

    Numbers come from the same quantity strings Table 7.1 prints.  Never
    raises: a problem is logged and yields an empty string.
    """
    try:
        os.makedirs(chart_dir, exist_ok=True)
        parts = []
        steel = steel_quantities(quantities)
        p = quantity_bar_chart(list(steel), list(steel.values()),
                               os.path.join(chart_dir, "qty_steel.png"), "Structural steel weight (MT)")
        if p:
            parts.append(_figure_tex(
                p, r"Structural steel quantity by element (MT). Cross bracing is the sum of its "
                   r"top chord, bottom chord and diagonal members. End diaphragm steel is not "
                   r"included in the quantity take-off (N/A)."))
        p = concrete_rebar_chart(parse_quantity(quantities.get("concrete_deck_vol_total")),
                                 parse_quantity(quantities.get("rebar_deck_wt_total")),
                                 os.path.join(chart_dir, "qty_concrete_rebar.png"))
        if p:
            parts.append(_figure_tex(
                p, r"Deck slab concrete volume (m\textsuperscript{3}) and reinforcement steel weight (MT). "
                   r"The two panels use different units and scales."))
        return ("\n\\vspace{1em}\n" + "\n".join(parts)) if parts else ""
    except Exception:
        import logging
        logging.getLogger(__name__).exception("Material chart generation failed")
        return ""


# ─────────────────────────────────────────────────────────────────────────────
# LaTeX
# ─────────────────────────────────────────────────────────────────────────────
def _figure_tex(path, caption):
    return (r"\begin{figure}[H]" "\n"
            r"\centering" "\n"
            r"\includegraphics[width=" + styles.CHART["include_width"] + "]{" + path + "}\n"
            r"\caption{" + caption + "}\n"
            r"\end{figure}" "\n")


def ur_figures_tex(fig_paths):
    """LaTeX for the Section 5.5 charts; an empty string when none exist."""
    fig_paths = fig_paths or {}
    parts = []
    if fig_paths.get("ur_overall"):
        parts.append(_figure_tex(
            fig_paths["ur_overall"],
            r"Utilization ratio (UR = Demand / Capacity) of the primary elements. "
            r"The dashed red line marks UR = 1.0; bars above it fail the check."))
    if fig_paths.get("ur_girders"):
        parts.append(_figure_tex(
            fig_paths["ur_girders"],
            r"Governing utilization ratio of each plate girder."))
    if not parts:
        return ""
    return "\n\\vspace{1em}\n" + "\n".join(parts)