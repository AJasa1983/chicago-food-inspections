"""Chicago Food Inspections dashboard.

Run locally:   streamlit run app.py
Data:          inspections.parquet (cleaned City of Chicago Food Inspections data)
"""
import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Chicago Food Inspections", page_icon="🍽️", layout="wide")

DATA_PATH = Path(__file__).parent / "inspections.parquet"
SOURCE_URL = "https://catalog.data.gov/dataset/food-inspections"
MAP_STYLE = os.environ.get("MAP_STYLE", "carto-positron")

# Colours (light theme). One fixed colour per entity, used the same way everywhere.
PASS, CONDITIONS, FAIL = "#2a78d6", "#1baf7a", "#eb6834"
INK, INK_2, INK_3 = "#1a2433", "#52514e", "#6b6a66"
YELLOW = "#eda100"
GOOD, BAD = "#1a7f37", "#cf222e"
RESULT_COLOURS = {"Pass": PASS, "Pass w/ Conditions": CONDITIONS, "Fail": FAIL}
INSPECTED = ["Pass", "Pass w/ Conditions", "Fail"]
NOT_INSPECTED = ["Out of Business", "No Entry", "Not Ready", "Business Not Located"]
RISK_ORDER = ["Risk 1 (High)", "Risk 2 (Medium)", "Risk 3 (Low)"]
SEQ_BLUE = ["#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]

# ---------------------------------------------------------------- styling
st.markdown(
    f"""
<style>
  .block-container {{ padding-top: 2.2rem; max-width: 1400px; }}

  .hero {{ display:flex; gap:1.4rem; align-items:flex-start; padding:1.6rem 1.8rem; border-radius:18px;
           background: linear-gradient(135deg, #1c5cab 0%, #2a78d6 55%, #3f8ee8 100%);
           box-shadow: 0 10px 30px rgba(42,120,214,0.25); margin-bottom:1.3rem; }}
  .hero-icon {{ font-size:2.6rem; line-height:1; padding:0.7rem; border-radius:16px;
                background: rgba(255,255,255,0.18); border:1px solid rgba(255,255,255,0.45); }}
  .hero h1 {{ font-size:2.1rem; margin:0 0 0.35rem 0; padding:0; color:#fff; font-weight:800; }}
  .hero p {{ color:rgba(255,255,255,0.92); font-size:1.02rem; margin:0 0 0.9rem 0; max-width:60rem; }}
  .chip {{ display:inline-block; font-size:0.8rem; padding:0.28rem 0.7rem; margin:0 0.4rem 0.4rem 0;
           border-radius:999px; border:1px solid rgba(255,255,255,0.5); color:#fff; background:rgba(255,255,255,0.14);
           text-decoration:none !important; }}
  .chip.warn {{ border-color:#ffd479; color:#3d2c00; background:#ffd479; font-weight:600; }}
  a.chip, a.chip:visited {{ color:#fff !important; }}

  .kpi {{ position:relative; padding:1rem 1.1rem 0.8rem; border-radius:16px; height:100%; min-height:178px;
          display:flex; flex-direction:column; background:#ffffff;
          border:1px solid rgba(20,40,80,0.10); border-top:4px solid var(--accent);
          box-shadow: 0 6px 22px color-mix(in srgb, var(--accent) 18%, transparent); }}
  .kpi-label {{ font-size:0.72rem; letter-spacing:0.08em; text-transform:uppercase; color:{INK_2}; font-weight:700;
                padding-right:1.6rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
  .kpi-icon {{ position:absolute; top:0.85rem; right:1rem; font-size:1.15rem; }}
  .kpi-value {{ font-size:clamp(1.25rem, 1.9vw, 2rem); font-weight:800; color:{INK}; margin:0.35rem 0 0.1rem;
                font-variant-numeric: tabular-nums; white-space:nowrap; }}
  .kpi-sub {{ font-size:0.8rem; color:{INK_3}; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
  .kpi-foot {{ margin-top:auto !important; display:flex; justify-content:space-between; align-items:center;
               gap:0.4rem; flex-wrap:wrap; padding-top:0.6rem; }}
  .kpi-foot svg {{ flex:1 1 60px; min-width:60px; max-width:110px; }}
  .pill {{ font-size:0.72rem; font-weight:700; padding:0.18rem 0.55rem; border-radius:999px; white-space:nowrap; }}
  .pill.good {{ color:{GOOD}; background:rgba(26,127,55,0.10); border:1px solid rgba(26,127,55,0.35); }}
  .pill.bad  {{ color:{BAD};  background:rgba(207,34,46,0.08); border:1px solid rgba(207,34,46,0.30); }}
  .pill.flat {{ color:{INK_2}; background:rgba(80,90,110,0.08); border:1px solid rgba(80,90,110,0.25); }}

  .section {{ display:flex; align-items:center; gap:0.8rem; margin:0.6rem 0 0.2rem; }}
  .section-num {{ font-size:0.85rem; font-weight:800; color:#fff; background:{PASS};
                  border-radius:8px; padding:0.25rem 0.55rem; }}
  .section-title {{ font-size:1.55rem; font-weight:800; color:{INK}; }}
  .section-sub {{ color:{INK_2}; margin:0 0 1rem 0; }}

  .insight {{ padding:1rem 1.15rem; border-radius:14px; height:100%;
              background: linear-gradient(160deg, color-mix(in srgb, var(--accent) 12%, #ffffff) 0%, #ffffff 75%);
              border:1px solid rgba(20,40,80,0.10); border-left:5px solid var(--accent);
              box-shadow: 0 4px 16px rgba(20,40,80,0.06); }}
  .insight-title {{ font-size:0.75rem; letter-spacing:0.1em; text-transform:uppercase; color:{INK_2}; font-weight:700; }}
  .insight-big {{ font-size:1.6rem; font-weight:800; color:{INK}; margin:0.25rem 0; }}
  .insight-text {{ color:{INK}; font-size:0.95rem; }}

  [data-testid="stTabs"] button p {{ font-size:0.98rem; font-weight:600; }}
</style>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------- data
@st.cache_data(show_spinner="Loading inspections…")
def load_data() -> pd.DataFrame:
    df = pd.read_parquet(DATA_PATH)
    for c in ["Results", "Facility Type", "Risk", "Zip", "Inspection Type"]:
        df[c] = df[c].astype(str)
    t = df["Inspection Type"].str.lower()
    df["Inspection Group"] = "Other"
    df.loc[t.str.contains("canvass"), "Inspection Group"] = "Routine (canvass)"
    df.loc[t.str.contains("license"), "Inspection Group"] = "License"
    df.loc[t.str.contains("complaint"), "Inspection Group"] = "Complaint"
    df.loc[t.str.contains(r"re-?insp"), "Inspection Group"] = "Re-inspection"
    return df


def fail_share(s: pd.Series) -> float:
    return (s == "Fail").mean()


def pass_share(s: pd.Series) -> float:
    return (s == "Pass").mean()


def cond_share(s: pd.Series) -> float:
    return (s == "Pass w/ Conditions").mean()


def style(fig: go.Figure, height: int = 360) -> go.Figure:
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=INK_2), height=height,
        margin=dict(l=8, r=8, t=8, b=8),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title=None, font=dict(color=INK)),
        hoverlabel=dict(font_size=13),
        bargap=0.25,
    )
    fig.update_xaxes(showgrid=False, title=None, linecolor="rgba(0,0,0,0.15)")
    fig.update_yaxes(gridcolor="rgba(0,0,0,0.07)", zeroline=False)
    return fig


def sparkline(values, colour: str) -> str:
    vals = [v for v in values if pd.notna(v)]
    if len(vals) < 2:
        return ""
    w, h, pad = 110, 30, 3
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1
    step = (w - 2 * pad) / (len(vals) - 1)
    pts = " ".join(f"{pad + i * step:.1f},{h - pad - (v - lo) / span * (h - 2 * pad):.1f}" for i, v in enumerate(vals))
    last_x, last_y = pts.split(" ")[-1].split(",")
    return (
        f'<svg height="{h}" viewBox="0 0 {w} {h}" preserveAspectRatio="none" aria-hidden="true">'
        f'<polyline points="{pts}" fill="none" stroke="{colour}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>'
        f'<circle cx="{last_x}" cy="{last_y}" r="3" fill="{colour}"/></svg>'
    )


def kpi_card(label, icon, value, sub, change, good_when_up, spark, accent):
    if change is None:
        pill = ""
    else:
        num, text = change
        cls = "flat" if text.lstrip("+-").startswith(("0%", "0.0 ", "0.00 ")) else ("good" if (num > 0) == good_when_up else "bad")
        pill = f'<span class="pill {cls}">{text}</span>'
    return f"""
<div class="kpi" style="--accent:{accent}">
  <div class="kpi-label">{label}</div><div class="kpi-icon">{icon}</div>
  <div class="kpi-value">{value}</div>
  <div class="kpi-sub">{sub}</div>
  <div class="kpi-foot">{pill}{spark}</div>
</div>"""


def section(num: int, title: str, sub: str) -> None:
    st.markdown(
        f'<div class="section"><span class="section-num">{num:02d}</span>'
        f'<span class="section-title">{title}</span></div><p class="section-sub">{sub}</p>',
        unsafe_allow_html=True,
    )


df = load_data()
min_y, max_y = int(df["Year"].min()), int(df["Year"].max())
last_date = df["Inspection Date"].max()

# ---------------------------------------------------------------- sidebar
DEFAULTS = {"years": (min_y, max_y), "fac": [], "risk": [], "grp": [], "visits": False, "excl_partial": False}
for k, v in DEFAULTS.items():
    st.session_state.setdefault(k, v)


def reset_filters():
    for k, v in DEFAULTS.items():
        st.session_state[k] = v


st.sidebar.markdown("### 🎛️ Filters")
st.sidebar.button("↺ Reset all filters", on_click=reset_filters, width="stretch")
st.sidebar.slider("Inspection years", min_y, max_y, key="years")
st.sidebar.checkbox(
    f"Exclude the incomplete {max_y}", key="excl_partial",
    help=f"The data ends on {last_date:%d %B %Y}, so {max_y} isn't a full year.",
)
st.sidebar.multiselect("Facility type", sorted(df["Facility Type"].unique()), key="fac",
                       placeholder="All facility types")
st.sidebar.multiselect("Risk level", RISK_ORDER, key="risk", placeholder="All risk levels")
st.sidebar.multiselect("Inspection type", sorted(df["Inspection Group"].unique()), key="grp",
                       placeholder="All inspection types")
st.sidebar.toggle(
    "Count visits where no inspection took place", key="visits",
    help="Out of Business, No Entry, Not Ready and Business Not Located visits. "
    "Off by default, so pass and fail rates only count real inspections.",
)
st.sidebar.caption(
    f"Source: City of Chicago Food Inspections via data.gov, cleaned. "
    f"{len(df):,} records, {df['Inspection Date'].min():%b %Y} – {last_date:%b %Y}."
)

ss = st.session_state
f = df[df["Year"].between(*ss.years)]
if ss.excl_partial:
    f = f[f["Year"] < max_y]
if ss.fac:
    f = f[f["Facility Type"].isin(ss.fac)]
if ss.risk:
    f = f[f["Risk"].isin(ss.risk)]
if ss.grp:
    f = f[f["Inspection Group"].isin(ss.grp)]
rate_base = f if ss.visits else f[f["Results"].isin(INSPECTED)]

# ---------------------------------------------------------------- hero
partial_chip = (
    f'<span class="chip warn">⏳ {max_y} is incomplete (data to {last_date:%d %b})</span>'
    if ss.years[1] == max_y and not ss.excl_partial else ""
)
st.markdown(
    f"""
<div class="hero">
  <div class="hero-icon">🍽️</div>
  <div>
    <h1>Chicago Food Inspections</h1>
    <p>Every city health inspection of Chicago's restaurants, shops, schools and care homes since 2010:
       who passes, who fails, what risk they carry and where the problems cluster.</p>
    <span class="chip">🏛️ Chicago Dept. of Public Health · data.gov</span>
    <span class="chip">📅 {ss.years[0]}–{ss.years[1]}</span>
    <span class="chip">🧹 {len(df):,} cleaned records</span>
    {partial_chip}
    <a class="chip" href="{SOURCE_URL}" target="_blank">↗ Original dataset</a>
  </div>
</div>""",
    unsafe_allow_html=True,
)

if rate_base.empty:
    st.warning("No inspections match these filters. Try widening them or press **Reset all filters**.")
    st.stop()

# ---------------------------------------------------------------- KPI cards
n = len(rate_base)
fail_rate = fail_share(rate_base["Results"])
pass_rate = pass_share(rate_base["Results"])
cond_rate = cond_share(rate_base["Results"])
avg_viol = rate_base["Violation Count"].mean()
no_insp_share = f["Results"].isin(NOT_INSPECTED).mean()

by_year = rate_base[rate_base["Year"] < max_y].groupby("Year").agg(
    n=("Results", "size"), pass_=("Results", pass_share), fail=("Results", fail_share),
    cond=("Results", cond_share), viol=("Violation Count", "mean"),
)


def yoy(col: str, kind: str):
    if len(by_year) < 2:
        return None
    cur, prev = by_year[col].iloc[-1], by_year[col].iloc[-2]
    y = by_year.index[-1]
    if kind == "pct_change":
        d = (cur - prev) / prev
        return d, f"{d:+.0%} vs prior year"
    if kind == "points":
        d = (cur - prev) * 100
        return d, f"{d:+.1f} pts vs prior year"
    d = cur - prev
    return d, f"{d:+.2f} vs prior year"


cards = [
    ("Inspections", "🔍", f"{n:,}", f"{rate_base['DBA Name'].nunique():,} businesses",
     yoy("n", "pct_change"), True, sparkline(by_year["n"], PASS), PASS),
    ("Pass rate", "✅", f"{pass_rate:.1%}", "clean pass",
     yoy("pass_", "points"), True, sparkline(by_year["pass_"], PASS), PASS),
    ("Conditional", "🛠️", f"{cond_rate:.1%}", "fixed on the spot",
     yoy("cond", "points"), False, sparkline(by_year["cond"], CONDITIONS), CONDITIONS),
    ("Fail rate", "⛔", f"{fail_rate:.1%}", "of inspections failed",
     yoy("fail", "points"), False, sparkline(by_year["fail"], FAIL), FAIL),
    ("Violations", "📋", "–" if pd.isna(avg_viol) else f"{avg_viol:.2f}", "avg per inspection",
     yoy("viol", "abs"), False, sparkline(by_year["viol"], YELLOW), YELLOW),
]
for col, c in zip(st.columns(5), cards):
    col.markdown(kpi_card(*c), unsafe_allow_html=True)
st.write("")

note = "Change pills compare the last two full years in your selection; mini lines show the yearly trend."
if not ss.visits:
    note += (f" {no_insp_share:.1%} of visits found no business to inspect "
             "(out of business, no entry, not ready or not located) and are left out of the rates.")
st.caption(note)

tabs = st.tabs(["🏠 Overview", "📈 Trends", "🏪 Business types", "⚠️ Risk levels",
                "🗺️ Map", "📍 Zip codes", "🗂️ Data"])

# ---------------------------------------------------------------- 01 overview
with tabs[0]:
    section(1, "🏠 Executive overview", "The four things to know about the inspections you've selected.")
    insights = []
    bt = rate_base.groupby("Facility Type")["Results"].agg(["size", fail_share])
    bt = bt[bt["size"] >= 200]
    if len(bt) >= 2:
        top = bt["fail_share"].idxmax()
        insights.append((FAIL, "🏪 Riskiest business type", top,
                         f"Fails <b>{bt.loc[top, 'fail_share']:.0%}</b> of inspections, against "
                         f"<b>{fail_rate:.0%}</b> overall."))
    yr = by_year["fail"]
    if len(yr) >= 2:
        change = (yr.iloc[-1] - yr.iloc[0]) * 100
        insights.append((GOOD if change < 0 else BAD, "📉 Long-term trend" if change < 0 else "📈 Long-term trend",
                         f"{change:+.1f} pts",
                         f"Fail rate went from <b>{yr.iloc[0]:.0%}</b> in {yr.index[0]} to "
                         f"<b>{yr.iloc[-1]:.0%}</b> in {yr.index[-1]}."))
    rk = rate_base.groupby("Risk")["Results"].agg(fail_share)
    if {"Risk 1 (High)", "Risk 3 (Low)"} <= set(rk.index):
        hi, lo = rk["Risk 1 (High)"], rk["Risk 3 (Low)"]
        if lo > hi:
            insights.append((YELLOW, "⚠️ Surprise finding", "Low risk ≠ safe",
                             f"Low-risk businesses fail <b>{lo:.0%}</b> of the time, more than high-risk ones "
                             f"(<b>{hi:.0%}</b>). Risk level reflects the food handled, not past performance."))
        else:
            insights.append((YELLOW, "⚠️ Risk level", f"{hi:.0%} vs {lo:.0%}",
                             "Fail rate for high-risk compared with low-risk businesses."))
    zp = rate_base.groupby("Zip")["Results"].agg(["size", fail_share])
    zp = zp[zp["size"] >= 300]
    if len(zp) >= 2:
        z = zp["fail_share"].idxmax()
        insights.append((PASS, "📍 Hotspot zip code", z,
                         f"Highest fail rate: <b>{zp.loc[z, 'fail_share']:.0%}</b> across "
                         f"{int(zp.loc[z, 'size']):,} inspections."))

    if insights:
        for col, (accent, title, big, text) in zip(st.columns(len(insights)), insights):
            col.markdown(
                f'<div class="insight" style="--accent:{accent}"><div class="insight-title">{title}</div>'
                f'<div class="insight-big">{big}</div><div class="insight-text">{text}</div></div>',
                unsafe_allow_html=True,
            )
    st.write("")
    st.markdown("##### Inspections each month")
    monthly = (rate_base.set_index("Inspection Date").resample("MS")["Results"]
               .agg(inspections="size", fail_rate=fail_share).reset_index())
    fig = px.area(monthly, x="Inspection Date", y="inspections", color_discrete_sequence=[PASS],
                  custom_data=["fail_rate"])
    fig.update_traces(line_width=2, fillcolor="rgba(42,120,214,0.14)",
                      hovertemplate="%{x|%B %Y}: %{y:,} inspections, %{customdata[0]:.1%} failed<extra></extra>")
    fig.update_yaxes(title=None, tickformat=",", rangemode="tozero")
    st.plotly_chart(style(fig, 300), width="stretch")
    st.caption("The dip in spring 2020 matches the COVID-19 lockdowns.")

# ---------------------------------------------------------------- 02 trends
with tabs[1]:
    section(2, "📈 Trends over time", "Is food safety in Chicago getting better or worse?")
    yearly = rate_base.groupby("Year").agg(inspections=("Results", "size"),
                                           fail_rate=("Results", fail_share)).reset_index()
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### Inspections per year")
        fig = px.bar(yearly, x="Year", y="inspections", color_discrete_sequence=[PASS])
        fig.update_traces(marker_cornerradius=4, hovertemplate="%{x}: %{y:,} inspections<extra></extra>")
        fig.update_yaxes(title=None, tickformat=",")
        st.plotly_chart(style(fig), width="stretch")
    with c2:
        st.markdown("##### Fail rate per year")
        fig = px.line(yearly, x="Year", y="fail_rate", markers=True, color_discrete_sequence=[FAIL])
        fig.update_traces(line_width=2, marker_size=8, hovertemplate="%{x}: %{y:.1%} failed<extra></extra>")
        fig.update_yaxes(title=None, tickformat=".0%", rangemode="tozero")
        st.plotly_chart(style(fig), width="stretch")
    if max_y in yearly["Year"].values:
        st.caption(f"{max_y} is a partial year (data ends {last_date:%d %B %Y}), so its count is lower.")

    st.markdown("##### Results mix per year")
    mix = rate_base[rate_base["Results"].isin(INSPECTED)].groupby(["Year", "Results"]).size().reset_index(name="count")
    mix["share"] = mix["count"] / mix.groupby("Year")["count"].transform("sum")
    fig = px.bar(mix, x="Year", y="share", color="Results", category_orders={"Results": INSPECTED},
                 color_discrete_map=RESULT_COLOURS, custom_data=["Results", "count"])
    fig.update_traces(marker_line_width=1, marker_line_color="#ffffff",
                      hovertemplate="%{x} · %{customdata[0]}: %{y:.1%} (%{customdata[1]:,})<extra></extra>")
    fig.update_layout(barmode="stack")
    fig.update_yaxes(title=None, tickformat=".0%")
    st.plotly_chart(style(fig, 380), width="stretch")

# ---------------------------------------------------------------- 03 business types
with tabs[2]:
    section(3, "🏪 Business types", "Which kinds of food business struggle most?")
    by_type = rate_base.groupby("Facility Type").agg(
        inspections=("Results", "size"), fail_rate=("Results", fail_share),
        avg_violations=("Violation Count", "mean")).reset_index()
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### Fail rate by facility type")
        d = by_type.sort_values("fail_rate")
        fig = px.bar(d, x="fail_rate", y="Facility Type", orientation="h",
                     color_discrete_sequence=[FAIL], custom_data=["inspections"])
        fig.update_traces(marker_cornerradius=4,
                          hovertemplate="%{y}: %{x:.1%} failed (%{customdata[0]:,} inspections)<extra></extra>")
        fig.add_vline(x=fail_rate, line_dash="dot", line_color=INK_3,
                      annotation_text=f"Overall {fail_rate:.1%}", annotation_position="bottom right",
                      annotation_font_color=INK_2)
        fig.update_xaxes(tickformat=".0%")
        fig.update_yaxes(title=None, gridcolor="rgba(0,0,0,0)")
        st.plotly_chart(style(fig, 440), width="stretch")
    with c2:
        st.markdown("##### Average violations by facility type")
        d = by_type.sort_values("avg_violations")
        fig = px.bar(d, x="avg_violations", y="Facility Type", orientation="h",
                     color_discrete_sequence=[PASS], custom_data=["inspections"])
        fig.update_traces(marker_cornerradius=4,
                          hovertemplate="%{y}: %{x:.2f} violations on average (%{customdata[0]:,} inspections)<extra></extra>")
        fig.update_yaxes(title=None, gridcolor="rgba(0,0,0,0)")
        st.plotly_chart(style(fig, 440), width="stretch")
    st.caption("'Other' groups more than 500 smaller facility types, so read it with care.")

# ---------------------------------------------------------------- 04 risk
with tabs[3]:
    section(4, "⚠️ Risk levels", "Do businesses the city rates as high-risk actually fail more often?")
    risk_mix = (rate_base[rate_base["Results"].isin(INSPECTED)]
                .groupby(["Risk", "Results"]).size().reset_index(name="count"))
    risk_mix["share"] = risk_mix["count"] / risk_mix.groupby("Risk")["count"].transform("sum")
    fig = px.bar(risk_mix, y="Risk", x="share", color="Results", orientation="h",
                 category_orders={"Results": INSPECTED, "Risk": RISK_ORDER},
                 color_discrete_map=RESULT_COLOURS, custom_data=["Results", "count"], text="share")
    fig.update_traces(texttemplate="%{x:.0%}", textposition="inside", insidetextanchor="middle",
                      textfont_color="#ffffff", marker_line_width=1, marker_line_color="#ffffff",
                      hovertemplate="%{y} · %{customdata[0]}: %{x:.1%} (%{customdata[1]:,})<extra></extra>")
    fig.update_layout(barmode="stack")
    fig.update_xaxes(tickformat=".0%")
    fig.update_yaxes(title=None, gridcolor="rgba(0,0,0,0)")
    st.plotly_chart(style(fig, 300), width="stretch")
    risk_table = (rate_base.groupby("Risk")
                  .agg(Inspections=("Results", "size"), **{"Fail rate": ("Results", fail_share)},
                       **{"Avg violations": ("Violation Count", "mean")})
                  .reindex(RISK_ORDER).dropna(how="all").reset_index())
    st.dataframe(risk_table, hide_index=True, width="stretch", column_config={
        "Inspections": st.column_config.NumberColumn(format="localized"),
        "Fail rate": st.column_config.NumberColumn(format="percent"),
        "Avg violations": st.column_config.NumberColumn(format="%.2f")})

# ---------------------------------------------------------------- 05 map
with tabs[4]:
    section(5, "🗺️ Map", "Where in the city do inspections, and failures, cluster?")
    show = st.radio("Show", ["Failed inspections", "All inspections"], horizontal=True)
    m = rate_base.dropna(subset=["Latitude", "Longitude"])
    if show == "Failed inspections":
        m = m[m["Results"] == "Fail"]
    if m.empty:
        st.info("No mapped inspections for this selection.")
    else:
        grid = (m.assign(lat=(m["Latitude"] / 0.01).round() * 0.01, lon=(m["Longitude"] / 0.01).round() * 0.01)
                .groupby(["lat", "lon"]).size().reset_index(name="count"))
        fig = px.scatter_map(grid, lat="lat", lon="lon", color="count", size="count", size_max=18,
                             color_continuous_scale=SEQ_BLUE, center=dict(lat=41.84, lon=-87.68),
                             zoom=9.4, map_style=MAP_STYLE, opacity=0.85)
        fig.update_traces(hovertemplate="%{marker.color:,} inspections in this area<extra></extra>")
        fig.update_layout(height=620, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)",
                          coloraxis_colorbar=dict(title="Inspections", thickness=12, len=0.5,
                                                  tickfont=dict(color=INK_2), title_font=dict(color=INK_2)))
        st.plotly_chart(fig, width="stretch")
        st.caption(f"Each circle is an area of about 1 km²; bigger, brighter circles have more "
                   f"{'failed ' if show == 'Failed inspections' else ''}inspections. "
                   f"{len(m):,} inspections shown; records without coordinates are left out.")

# ---------------------------------------------------------------- 06 zip codes
with tabs[5]:
    section(6, "📍 Zip codes", "Which neighbourhoods have the highest fail rates?")
    min_n = st.slider("Only zip codes with at least this many inspections", 50, 2000, 300, step=50)
    by_zip = rate_base.groupby("Zip").agg(Inspections=("Results", "size"),
                                          Fails=("Results", lambda s: (s == "Fail").sum()),
                                          **{"Avg violations": ("Violation Count", "mean")}).reset_index()
    by_zip = by_zip[by_zip["Inspections"] >= min_n]
    by_zip["Fail rate"] = by_zip["Fails"] / by_zip["Inspections"]
    by_zip = by_zip.sort_values("Fail rate", ascending=False)
    if by_zip.empty:
        st.info("No zip code has that many inspections in this selection. Lower the threshold.")
    else:
        top = by_zip.head(15).sort_values("Fail rate")
        fig = px.bar(top, x="Fail rate", y="Zip", orientation="h",
                     color_discrete_sequence=[FAIL], custom_data=["Inspections"])
        fig.update_traces(marker_cornerradius=4,
                          hovertemplate="Zip %{y}: %{x:.1%} failed (%{customdata[0]:,} inspections)<extra></extra>")
        fig.update_xaxes(tickformat=".0%")
        fig.update_yaxes(title=None, type="category", gridcolor="rgba(0,0,0,0)")
        st.plotly_chart(style(fig, 460), width="stretch")
        st.caption("Top 15 shown. The full ranking is in the table.")
        st.dataframe(by_zip, hide_index=True, width="stretch", column_config={
            "Inspections": st.column_config.NumberColumn(format="localized"),
            "Fails": st.column_config.NumberColumn(format="localized"),
            "Fail rate": st.column_config.NumberColumn(format="percent"),
            "Avg violations": st.column_config.NumberColumn(format="%.2f")})

# ---------------------------------------------------------------- 07 data
with tabs[6]:
    section(7, "🗂️ Dataset explorer", "Browse and download the records behind every chart.")
    cols = ["Inspection Date", "DBA Name", "Facility Type", "Risk", "Zip",
            "Inspection Type", "Results", "Violation Count"]
    out = f[cols].sort_values("Inspection Date", ascending=False)
    st.dataframe(out.head(5000), hide_index=True, width="stretch")
    st.caption(f"Showing the latest {min(len(out), 5000):,} of {len(out):,} matching records.")
    st.download_button("⬇️ Download filtered data (CSV)", out.to_csv(index=False).encode("utf-8"),
                       file_name="chicago_inspections_filtered.csv", mime="text/csv")
