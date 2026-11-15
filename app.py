"""Chicago Food Inspections dashboard.

Run locally:   streamlit run app.py
Data:          inspections.parquet (cleaned City of Chicago Food Inspections data)
"""
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Chicago Food Inspections", page_icon="🍽️", layout="wide")

DATA_PATH = Path(__file__).parent / "inspections.parquet"

# Colours: one fixed colour per entity, used the same way in every chart.
PASS, CONDITIONS, FAIL = "#2a78d6", "#1baf7a", "#eb6834"
NEUTRAL = "#9a988f"
RESULT_COLOURS = {"Pass": PASS, "Pass w/ Conditions": CONDITIONS, "Fail": FAIL}
INSPECTED = ["Pass", "Pass w/ Conditions", "Fail"]
NOT_INSPECTED = ["Out of Business", "No Entry", "Not Ready", "Business Not Located"]
RISK_ORDER = ["Risk 1 (High)", "Risk 2 (Medium)", "Risk 3 (Low)"]
MAP_STYLE = __import__("os").environ.get("MAP_STYLE", "carto-positron")
SEQ_BLUE = ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]


@st.cache_data(show_spinner="Loading inspections…")
def load_data() -> pd.DataFrame:
    df = pd.read_parquet(DATA_PATH)
    df["Results"] = df["Results"].astype(str)
    df["Facility Type"] = df["Facility Type"].astype(str)
    df["Risk"] = df["Risk"].astype(str)
    df["Zip"] = df["Zip"].astype(str)
    df["Inspection Type"] = df["Inspection Type"].astype(str)
    # Group the many inspection types into a few readable families.
    t = df["Inspection Type"].str.lower()
    df["Inspection Group"] = "Other"
    df.loc[t.str.contains("canvass"), "Inspection Group"] = "Routine (canvass)"
    df.loc[t.str.contains("license"), "Inspection Group"] = "License"
    df.loc[t.str.contains("complaint"), "Inspection Group"] = "Complaint"
    df.loc[t.str.contains(r"re-?insp"), "Inspection Group"] = "Re-inspection"
    return df


def style(fig: go.Figure, height: int = 360) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=8, b=8),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title=None),
        hoverlabel=dict(font_size=13),
        bargap=0.25,
    )
    fig.update_xaxes(showgrid=False, title=None)
    fig.update_yaxes(gridcolor="rgba(128,128,128,0.15)", zeroline=False)
    return fig


def pct(x: float) -> str:
    return "–" if pd.isna(x) else f"{x:.1%}"


df = load_data()

# ---------------------------------------------------------------- sidebar
st.sidebar.header("Filters")
min_y, max_y = int(df["Year"].min()), int(df["Year"].max())
years = st.sidebar.slider("Years", min_y, max_y, (min_y, max_y))
facilities = st.sidebar.multiselect(
    "Facility type",
    sorted(df["Facility Type"].unique()),
    placeholder="All facility types",
)
risks = st.sidebar.multiselect("Risk level", RISK_ORDER, placeholder="All risk levels")
groups = st.sidebar.multiselect(
    "Inspection type",
    sorted(df["Inspection Group"].unique()),
    placeholder="All inspection types",
)
include_visits = st.sidebar.toggle(
    "Count visits where no inspection took place",
    value=False,
    help="Out of Business, No Entry, Not Ready and Business Not Located visits. "
    "Off by default, so pass and fail rates only count real inspections.",
)
st.sidebar.caption(
    f"Data: City of Chicago Food Inspections, cleaned. {len(df):,} records, "
    f"{df['Inspection Date'].min():%b %Y} – {df['Inspection Date'].max():%b %Y}."
)

f = df[df["Year"].between(*years)]
if facilities:
    f = f[f["Facility Type"].isin(facilities)]
if risks:
    f = f[f["Risk"].isin(risks)]
if groups:
    f = f[f["Inspection Group"].isin(groups)]
rate_base = f if include_visits else f[f["Results"].isin(INSPECTED)]

# ---------------------------------------------------------------- header + KPIs
st.title("Chicago Food Inspections")
st.caption(
    "How food businesses in Chicago perform in city health inspections. "
    "Use the filters on the left; every chart and number updates."
)

if rate_base.empty:
    st.warning("No inspections match these filters. Try widening them.")
    st.stop()

n = len(rate_base)
fail_rate = (rate_base["Results"] == "Fail").mean()
pass_rate = (rate_base["Results"] == "Pass").mean()
avg_viol = rate_base["Violation Count"].mean()
no_insp_share = f["Results"].isin(NOT_INSPECTED).mean()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Inspections", f"{n:,}", help="Records counted under the current filters.")
k2.metric("Pass rate", pct(pass_rate), help="Share of inspections with a clean Pass.")
k3.metric("Fail rate", pct(fail_rate), help="Share of inspections that failed.")
k4.metric(
    "Avg violations per inspection",
    "–" if pd.isna(avg_viol) else f"{avg_viol:.2f}",
    help="Inspections with no recorded violation details (NOT ASSESSED / UNKNOWN) are left out of this average.",
)
if not include_visits:
    st.caption(
        f"{no_insp_share:.1%} of visits in this selection found no business to inspect "
        "(out of business, no entry, not ready or not located) and are excluded from the rates."
    )

tab_trend, tab_type, tab_risk, tab_map, tab_zip, tab_data = st.tabs(
    ["Trends", "Business types", "Risk levels", "Map", "Zip codes", "Data"]
)

# ---------------------------------------------------------------- trends
with tab_trend:
    yearly = (
        rate_base.groupby("Year")
        .agg(inspections=("Inspection ID", "size"), fail_rate=("Results", lambda s: (s == "Fail").mean()))
        .reset_index()
    )
    partial = max_y in yearly["Year"].values
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Inspections per year")
        fig = px.bar(yearly, x="Year", y="inspections", color_discrete_sequence=[PASS])
        fig.update_traces(
            marker_cornerradius=4,
            hovertemplate="%{x}: %{y:,} inspections<extra></extra>",
        )
        fig.update_yaxes(title=None, tickformat=",")
        st.plotly_chart(style(fig), width="stretch")
    with c2:
        st.subheader("Fail rate per year")
        fig = px.line(yearly, x="Year", y="fail_rate", markers=True, color_discrete_sequence=[FAIL])
        fig.update_traces(
            line_width=2,
            marker_size=8,
            hovertemplate="%{x}: %{y:.1%} failed<extra></extra>",
        )
        fig.update_yaxes(title=None, tickformat=".0%", rangemode="tozero")
        st.plotly_chart(style(fig), width="stretch")
    if partial:
        st.caption(
            f"{max_y} is a partial year: the data ends on "
            f"{df['Inspection Date'].max():%d %B %Y}, so its inspection count is lower than a full year."
        )

    st.subheader("Results mix per year")
    mix = (
        rate_base[rate_base["Results"].isin(INSPECTED)]
        .groupby(["Year", "Results"]).size().reset_index(name="count")
    )
    mix["share"] = mix["count"] / mix.groupby("Year")["count"].transform("sum")
    fig = px.bar(
        mix, x="Year", y="share", color="Results",
        category_orders={"Results": INSPECTED}, color_discrete_map=RESULT_COLOURS,
        custom_data=["Results", "count"],
    )
    fig.update_traces(
        marker_line_width=1, marker_line_color="rgba(255,255,255,0.9)",
        hovertemplate="%{x} · %{customdata[0]}: %{y:.1%} (%{customdata[1]:,})<extra></extra>",
    )
    fig.update_layout(barmode="stack")
    fig.update_yaxes(title=None, tickformat=".0%")
    st.plotly_chart(style(fig, 380), width="stretch")

# ---------------------------------------------------------------- business types
with tab_type:
    by_type = (
        rate_base.groupby("Facility Type")
        .agg(
            inspections=("Inspection ID", "size"),
            fail_rate=("Results", lambda s: (s == "Fail").mean()),
            avg_violations=("Violation Count", "mean"),
        )
        .reset_index()
    )
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Fail rate by facility type")
        d = by_type.sort_values("fail_rate")
        fig = px.bar(d, x="fail_rate", y="Facility Type", orientation="h",
                     color_discrete_sequence=[FAIL], custom_data=["inspections"])
        fig.update_traces(
            marker_cornerradius=4,
            hovertemplate="%{y}: %{x:.1%} failed (%{customdata[0]:,} inspections)<extra></extra>",
        )
        fig.add_vline(x=fail_rate, line_dash="dot", line_color=NEUTRAL,
                      annotation_text=f"Overall {fail_rate:.1%}", annotation_position="bottom right",
                      annotation_font_color=NEUTRAL)
        fig.update_xaxes(tickformat=".0%")
        fig.update_yaxes(title=None, gridcolor="rgba(0,0,0,0)")
        st.plotly_chart(style(fig, 420), width="stretch")
    with c2:
        st.subheader("Average violations by facility type")
        d = by_type.sort_values("avg_violations")
        fig = px.bar(d, x="avg_violations", y="Facility Type", orientation="h",
                     color_discrete_sequence=[PASS], custom_data=["inspections"])
        fig.update_traces(
            marker_cornerradius=4,
            hovertemplate="%{y}: %{x:.2f} violations on average (%{customdata[0]:,} inspections)<extra></extra>",
        )
        fig.update_yaxes(title=None, gridcolor="rgba(0,0,0,0)")
        st.plotly_chart(style(fig, 420), width="stretch")
    st.caption("'Other' groups more than 500 smaller facility types, so read it with care.")

# ---------------------------------------------------------------- risk
with tab_risk:
    st.subheader("Do higher-risk businesses fail more often?")
    risk_mix = (
        rate_base[rate_base["Results"].isin(INSPECTED)]
        .groupby(["Risk", "Results"]).size().reset_index(name="count")
    )
    risk_mix["share"] = risk_mix["count"] / risk_mix.groupby("Risk")["count"].transform("sum")
    fig = px.bar(
        risk_mix, y="Risk", x="share", color="Results", orientation="h",
        category_orders={"Results": INSPECTED, "Risk": RISK_ORDER},
        color_discrete_map=RESULT_COLOURS, custom_data=["Results", "count"], text="share",
    )
    fig.update_traces(
        texttemplate="%{x:.0%}", textposition="inside", insidetextanchor="middle",
        marker_line_width=1, marker_line_color="rgba(255,255,255,0.9)",
        hovertemplate="%{y} · %{customdata[0]}: %{x:.1%} (%{customdata[1]:,})<extra></extra>",
    )
    fig.update_layout(barmode="stack")
    fig.update_xaxes(tickformat=".0%")
    fig.update_yaxes(title=None, gridcolor="rgba(0,0,0,0)")
    st.plotly_chart(style(fig, 300), width="stretch")

    risk_table = (
        rate_base.groupby("Risk")
        .agg(
            Inspections=("Inspection ID", "size"),
            **{"Fail rate": ("Results", lambda s: (s == "Fail").mean())},
            **{"Avg violations": ("Violation Count", "mean")},
        )
        .reindex(RISK_ORDER).dropna(how="all").reset_index()
    )
    st.dataframe(
        risk_table, hide_index=True, width="stretch",
        column_config={
            "Inspections": st.column_config.NumberColumn(format="localized"),
            "Fail rate": st.column_config.NumberColumn(format="percent"),
            "Avg violations": st.column_config.NumberColumn(format="%.2f"),
        },
    )

# ---------------------------------------------------------------- map
with tab_map:
    st.subheader("Where do failed inspections happen?")
    show = st.radio("Show", ["Failed inspections", "All inspections"], horizontal=True)
    m = rate_base.dropna(subset=["Latitude", "Longitude"])
    if show == "Failed inspections":
        m = m[m["Results"] == "Fail"]
    if m.empty:
        st.info("No mapped inspections for this selection.")
    else:
        # Group points into ~1 km grid cells so dense areas stay readable.
        grid = (
            m.assign(lat=(m["Latitude"] / 0.01).round() * 0.01, lon=(m["Longitude"] / 0.01).round() * 0.01)
            .groupby(["lat", "lon"]).size().reset_index(name="count")
        )
        fig = px.scatter_map(
            grid, lat="lat", lon="lon", color="count", size="count", size_max=18,
            color_continuous_scale=SEQ_BLUE[1:], center=dict(lat=41.84, lon=-87.68),
            zoom=9.4, map_style=MAP_STYLE, opacity=0.8,
        )
        fig.update_traces(hovertemplate="%{marker.color:,} inspections in this area<extra></extra>")
        fig.update_layout(
            height=600, margin=dict(l=0, r=0, t=0, b=0),
            coloraxis_colorbar=dict(title="Inspections", thickness=12, len=0.5),
        )
        st.plotly_chart(fig, width="stretch")
        st.caption(
            f"Each circle is an area of about 1 km². Bigger, darker circles have more "
            f"{'failed ' if show == 'Failed inspections' else ''}inspections. "
            f"{len(m):,} inspections shown; records without coordinates are left out."
        )

# ---------------------------------------------------------------- zip codes
with tab_zip:
    st.subheader("Zip codes ranked by fail rate")
    min_n = st.slider("Only zip codes with at least this many inspections", 50, 2000, 300, step=50)
    by_zip = (
        rate_base.groupby("Zip")
        .agg(
            Inspections=("Inspection ID", "size"),
            Fails=("Results", lambda s: (s == "Fail").sum()),
            **{"Avg violations": ("Violation Count", "mean")},
        )
        .reset_index()
    )
    by_zip = by_zip[by_zip["Inspections"] >= min_n]
    by_zip["Fail rate"] = by_zip["Fails"] / by_zip["Inspections"]
    by_zip = by_zip.sort_values("Fail rate", ascending=False)
    if by_zip.empty:
        st.info("No zip code has that many inspections in this selection. Lower the threshold.")
    else:
        top = by_zip.head(15).sort_values("Fail rate")
        fig = px.bar(top, x="Fail rate", y="Zip", orientation="h",
                     color_discrete_sequence=[FAIL], custom_data=["Inspections"])
        fig.update_traces(
            marker_cornerradius=4,
            hovertemplate="Zip %{y}: %{x:.1%} failed (%{customdata[0]:,} inspections)<extra></extra>",
        )
        fig.update_xaxes(tickformat=".0%")
        fig.update_yaxes(title=None, type="category", gridcolor="rgba(0,0,0,0)")
        st.plotly_chart(style(fig, 460), width="stretch")
        st.caption("Top 15 shown. The full ranking is in the table.")
        st.dataframe(
            by_zip, hide_index=True, width="stretch",
            column_config={
                "Inspections": st.column_config.NumberColumn(format="localized"),
                "Fails": st.column_config.NumberColumn(format="localized"),
                "Fail rate": st.column_config.NumberColumn(format="percent"),
                "Avg violations": st.column_config.NumberColumn(format="%.2f"),
            },
        )

# ---------------------------------------------------------------- data
with tab_data:
    st.subheader("Filtered records")
    cols = ["Inspection Date", "DBA Name", "Facility Type", "Risk", "Zip",
            "Inspection Type", "Results", "Violation Count"]
    out = f[cols].sort_values("Inspection Date", ascending=False)
    st.dataframe(out.head(5000), hide_index=True, width="stretch")
    st.caption(f"Showing the latest {min(len(out), 5000):,} of {len(out):,} matching records.")
    st.download_button(
        "Download filtered data (CSV)",
        out.to_csv(index=False).encode("utf-8"),
        file_name="chicago_inspections_filtered.csv",
        mime="text/csv",
    )
