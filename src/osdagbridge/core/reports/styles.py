"""
styles.py -- single source of truth for OsdagBridge report styling.

Every layout rule and visual attribute used by the report generator lives
here: page geometry, fonts, colour palette, table spacing, header/footer
text, and chart appearance.  Chapter files must import from this module
instead of hard-coding values, so a global restyle is a one-file change.

Sections
--------
1. PALETTE      colours (hex, no '#') shared by LaTeX and matplotlib
2. DOCUMENT     document class, font size, line spacing, page geometry
3. TABLE        row/cell padding, rules, longtable spacing, break rules
4. HEADER/FOOTER text shown in running header and footer
5. CHARTS       matplotlib appearance for generated figures
6. build_preamble()   assembles the LaTeX preamble from the values above
"""

# ═════════════════════════════════════════════════════════════════════════════
# 1. PALETTE  (hex without '#')
# ═════════════════════════════════════════════════════════════════════════════
PALETTE = {
    "osdag_green": "91B014",   # headers/footers rules, accents
    "fail_red":    "D62728",   # failing checks, UR threshold line
    "pass_green":  "2CA02C",   # passing bars
    "steel_blue":  "1F77B4",   # neutral bars (quantities)
    "concrete":    "7F7F7F",
    "rebar":       "FF7F0E",
    "grid":        "CCCCCC",
}


def hex_(name):
    """'#RRGGBB' form of a palette colour (for matplotlib)."""
    return "#" + PALETTE[name]


# ═════════════════════════════════════════════════════════════════════════════
# 2. DOCUMENT
# ═════════════════════════════════════════════════════════════════════════════
DOCUMENT = {
    "class":        "report",
    "font_size":    "12pt",
    "paper":        "a4paper",
    "margin":       "1in",
    "line_stretch": "1.15",
    # extra geometry() options.  footskip 44pt (default 30pt) moves the footer down so the
    # "* Software default value" note, which is drawn upward from the footer rule, no
    # longer touches the last line of body text.  The text area is unchanged.
    "geometry_extra": {"footskip": "44pt"},
}

# ═════════════════════════════════════════════════════════════════════════════
# 3. TABLE
# ═════════════════════════════════════════════════════════════════════════════
TABLE = {
    "tabcolsep":      "6pt",     # horizontal cell padding
    "arraystretch":   "1.12",    # row-height multiplier
    "extrarowheight": "0.6pt",   # small extra row height
    "rule_width":     "0.5pt",   # \arrayrulewidth
    "lt_pre":         "0pt",     # \LTpre   (space above a longtable)
    "lt_post":        "6pt",     # \LTpost  (space below a longtable)
    "row_gap":        "6pt",     # vertical gap appended to every row: \\[6pt]
    # If fewer than this many baselines remain on the page, start the
    # table on a new page instead of orphaning its caption/first row.
    "needspace_lines": 5,
    # \needspace before a longtable breaks it: the page break it forces is not
    # yet visible to longtable, which then prints a stray "(continued)" head at
    # the top of the new page.  Keep this False; longtable paginates itself.
    "needspace_longtable": False,
    # Lines that must fit after a \section heading, else it moves to the next page.
    "heading_needspace_lines": 10,
    # Repeat column headers on every page of a multi-page table.
    "repeat_header":  True,
}

# ═════════════════════════════════════════════════════════════════════════════
# 4. HEADER / FOOTER
# ═════════════════════════════════════════════════════════════════════════════
HEADER_FOOTER = {
    "footer_left":   r"Osdag $|$ FOSSEE $|$ Indian Institute of Technology Bombay",
    "footer_right":  r"Page \thepage\ of \pageref{LastPage}",
    "rule_width":    "1pt",
    "default_note":  r"* Software default value",
}

# ═════════════════════════════════════════════════════════════════════════════
# 5. CHARTS (matplotlib)
# ═════════════════════════════════════════════════════════════════════════════
CHART = {
    "dpi":              200,
    "figsize":          (6.4, 3.4),     # inches; fits text width at 0.9\textwidth
    "font_size":        9,
    "title_size":       10,
    "bar_width":        0.6,
    "ur_threshold":     1.0,
    "ur_threshold_style": "--",         # dashed
    "ur_threshold_label": "UR = 1.0",
    "include_width":    r"0.85\textwidth",
}


# ═════════════════════════════════════════════════════════════════════════════
# 6. PREAMBLE
# ═════════════════════════════════════════════════════════════════════════════
def _geometry_options():
    opts = [DOCUMENT["paper"], "margin=" + DOCUMENT["margin"]]
    opts += [f"{k}={v}" for k, v in DOCUMENT["geometry_extra"].items()]
    return ", ".join(opts)


def _packages():
    return r"""
\usepackage[""" + _geometry_options() + r"""]{geometry}
\usepackage{graphicx}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{booktabs}
\usepackage{array}
\usepackage{tabularx}
\usepackage{float}
\usepackage{fancyhdr}
\usepackage[hidelinks]{hyperref}
\usepackage{xcolor}
\usepackage{setspace}
\usepackage{enumitem}
\usepackage{caption}

\captionsetup{
    labelfont=bf,
    justification=raggedright,
    singlelinecheck=false,
    format=plain
}
\usepackage{subcaption}
\usepackage{multirow}
\usepackage{colortbl}
\usepackage{longtable}
\setlength{\LTleft}{\fill}
\setlength{\LTright}{\fill}
\usepackage{titlesec}
\usepackage{titletoc}
\usepackage{lastpage}
\usepackage{makecell}
\usepackage{etoolbox}
\usepackage{needspace}
"""


def _table_layout():
    t = TABLE
    return r"""
\numberwithin{table}{chapter}
\numberwithin{figure}{chapter}
% Table layout and spacing (see styles.TABLE)
\setlength{\tabcolsep}{""" + t["tabcolsep"] + r"""}
\renewcommand{\arraystretch}{""" + t["arraystretch"] + r"""}
\setlength{\LTpre}{""" + t["lt_pre"] + r"""}
\setlength{\LTpost}{""" + t["lt_post"] + r"""}
\setlength{\arrayrulewidth}{""" + t["rule_width"] + r"""}
\setlength{\extrarowheight}{""" + t["extrarowheight"] + r"""}

% \keepneed{len}: if less than len remains on the page, end the page NOW.
% (needspace uses \break, which is applied lazily; a longtable that starts right
%  after it then measures the old page and prints a stray "(continued)" head.
%  \clearpage ships the page out immediately, so the table sees a fresh page.)
\makeatletter
\newcommand{\keepneed}[1]{\par\penalty-100\begingroup
  \@tempdima=#1\relax \@tempdimb=\pagegoal \advance\@tempdimb-\pagetotal
  \ifdim\@tempdima>\@tempdimb \clearpage \fi\endgroup}
\makeatother

% Keep a section heading together with the content that follows it, so a heading
% is never left alone at the bottom of a page (0 disables).
""" + (r"""\makeatletter
\pretocmd{\section}{\keepneed{""" + str(t["heading_needspace_lines"]) + r"""\baselineskip}}{}{}
\pretocmd{\subsection}{\keepneed{""" + str(t["heading_needspace_lines"] - 2) + r"""\baselineskip}}{}{}
\makeatother
""" if t["heading_needspace_lines"] else "") + r"""
% Do not start a floating table in the last few lines of a page.
\BeforeBeginEnvironment{table}{\needspace{""" + str(t["needspace_lines"]) + r"""\baselineskip}}
""" + (r"""\BeforeBeginEnvironment{longtable}{\needspace{""" + str(t["needspace_lines"]) + r"""\baselineskip}}
""" if t["needspace_longtable"] else "")


def _colors():
    return "\n".join(
        r"\definecolor{" + _latex_name(k) + r"}{HTML}{" + v + r"}"
        for k, v in PALETTE.items()
    ) + "\n"


def _latex_name(key):
    # 'osdag_green' -> 'osdagGreen'
    head, *rest = key.split("_")
    return head + "".join(w.capitalize() for w in rest)


def _header_footer(header_left, header_right):
    hf = HEADER_FOOTER
    rule = hf["rule_width"]

    def style(name, with_head, with_note):
        s = r"\fancypagestyle{" + name + r"}{" + "\n  \\fancyhf{}\n"
        if with_head:
            s += (r"  \fancyhead[L]{" + header_left + "}\n"
                  r"  \fancyhead[R]{" + header_right + "}\n")
        else:
            s += "  \\renewcommand{\\headrulewidth}{0pt}\n"
        s += (r"  \fancyfoot[L]{" + hf["footer_left"] + "}\n"
              r"  \fancyfoot[R]{" + hf["footer_right"] + "}\n")
        if with_head:
            s += (r"  \renewcommand{\headrule}{\color{osdagGreen}\hrule width\headwidth height "
                  + rule + r" \vspace{2pt}}" + "\n")
        if with_note:
            s += (r"""  \renewcommand{\footrule}{%
    \ifbool{hasSDonPage}{%
      \vspace{-20pt}%
      \hbox to \headwidth{\textcolor{black}{\footnotesize\textit{""" + hf["default_note"] + r"""}}\hfil}%
      \vspace{4pt}%
    }{%
      \vspace{-8pt}%
    }%
    \color{osdagGreen}\hrule width\headwidth height """ + rule + r""" \vspace{6pt}%
  }
""")
        else:
            s += (r"  \renewcommand{\footrule}{\vspace{-8pt}\color{osdagGreen}"
                  r"\hrule width\headwidth height " + rule + r" \vspace{6pt}}" + "\n")
        return s + "}\n"

    return (r"\newbool{hasSDonPage}" + "\n" + r"\boolfalse{hasSDonPage}" + "\n"
            + style("main", True, True)
            + style("plain", True, True)
            + style("firstpage", False, False)
            + r"\pagestyle{main}" + "\n"
            + r"\setstretch{" + DOCUMENT["line_stretch"] + "}\n")


_COMMANDS = r"""
% Custom Commands
\newcommand{\placeholder}[1]{\textit{\textless #1\textgreater}}
\newcommand{\todo}[1]{\colorbox{yellow}{TODO: #1}}
\newcolumntype{L}[1]{>{\raggedright\arraybackslash}p{#1}}
\newcolumntype{C}[1]{>{\centering\arraybackslash}p{#1}}
\newcolumntype{R}[1]{>{\raggedleft\arraybackslash}p{#1}}

% \kcline: same as \cline but forbids a page break after the rule.
% Used inside keep-together row groups (see latex_tables.keep_rows_together):
% a plain \cline leaves a legal break point that \\* cannot reach.
\makeatletter
\def\kcline#1{\@kcline#1\@nil}
\def\@kcline#1-#2\@nil{\omit
  \@multicnt#1%
  \advance\@multispan\m@ne
  \ifnum\@multicnt=\@ne\@firstofone{&\omit}\fi
  \@multicnt#2%
  \advance\@multicnt-#1%
  \advance\@multispan\@ne
  \leaders\hrule\@height\arrayrulewidth\hfill
  \cr
  \noalign{\penalty\@M\vskip-\arrayrulewidth}}
\makeatother

% Software-default asterisk
\newcommand{\sdstar}{\textsuperscript{*}}
\newcommand{\markSD}{\global\booltrue{hasSDonPage}}
\renewcommand{\sdstar}{\textsuperscript{*}\markSD{}}
\AddToHook{shipout/before}{\global\boolfalse{hasSDonPage}}
"""


def build_preamble(project_name, job_number, report_date, report_version):
    """Return the complete LaTeX preamble ending in \\begin{document}.

    Arguments must already be LaTeX-escaped (use report_utils._tex).
    """
    header_left = project_name + r" $|$ " + job_number
    header_right = report_date + r" $|$ " + report_version
    return (
        "\n\\documentclass[" + DOCUMENT["font_size"] + "," + DOCUMENT["paper"] + "]{"
        + DOCUMENT["class"] + "}\n"
        + _packages()
        + _table_layout()
        + "\n" + _colors()
        + _header_footer(header_left, header_right)
        + _COMMANDS
        + r"""
\title{\Large\textbf{OsdagBridge} \\ \normalsize Open Source Software for Steel Girder Bridge Design \\ \vspace{2cm} \large Design Report}
\author{}
\date{}

\begin{document}
"""
    )