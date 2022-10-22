import re
import json
import datetime
from textwrap import dedent
from urllib.parse import quote
from collections import defaultdict

import numpy as np
import pandas as pd
import streamlit as st


F_PAPERS = "papers.json"
F_ROOMS = "rooms.json"
DAYS = {
    "Monday": datetime.date(2022, 10, 24),
    "Tuesday": datetime.date(2022, 10, 25),
    "Wednesday": datetime.date(2022, 10, 26),
}
DAYS_FILTER = {
    "Monday": True,
    "Tuesday": True,
    "Wednesday": True,
}
COLUMNS = [
    "room",
    "title",
    "abstract",
    "keywords",
    "📅",
]


# @st.experimental_memo
def load_data():
    return json.load(open(F_PAPERS)), json.load(open(F_ROOMS))


# @st.experimental_memo
def parse_datetimes(date: pd.Series, time: pd.Series):
    # date: pd.Series = pd.to_datetime(date)
    time = time.str.split("-", n=2, expand=True)
    ts_start = date.str.cat(time.iloc[:, 0], sep=" ")
    ts_end = date.str.cat(time.iloc[:, 1], sep=" ")
    ts_start, ts_end = pd.to_datetime(ts_start), pd.to_datetime(ts_end)

    return ts_start, ts_end


def table_to_html(dataframe: pd.DataFrame):
    # Table
    html = dedent("""
        <div>
        <style>
            .papers {
                width: 100%;
                border: none;
            }
            .papers td, .papers th {
                border: none;
                text-align: left;
            }
            .papers tr:hover {
                background-color: rgba(255, 255, 0, 20%);
            }
        </style>
        <table class='papers' style='border: none; width: 100%; padding: 2px;'>
    """)
    
    # Header
    html += dedent("""
        <thead>
        <tr style='font-weight: bold'>
    """)
    for c_idx, col in enumerate(dataframe.columns):
        if c_idx == 0:
            html += f"<th style='width: 64px'>{col.capitalize()}</th>"
        else:
            html += f"<th>{col.capitalize()}</th>"
    html += "</tr></thead>"

    # Content
    html += "<tbody>"
    for row in dataframe.iterrows():
        html += "<tr>"
        for col in row[1]:
            html += f"<td>{col}</td>"
        html += "</tr>"
    html += "</tbody>"

    # Table End
    html += "</table></div></br>"

    return html


def generate_tables(
    container: st.container,
    data: pd.DataFrame,
    date: datetime.date,
    highlight: list,
    time: datetime.time = None,
    range: datetime.timedelta = None,
    show_abstract: bool = False,
    show_keywords: bool = False,
):
    df = data[data["start"].dt.date == date]
    if time is not None:
        df = df[df["start"].dt.time >= time]
    if range is not None:
        now = datetime.datetime.combine(date, time)
        df = df[df["start"].dt.time < (now + range).time()]
    df.set_index("time", inplace=True)
    # df.sort_values(by="start", inplace=True)
    df.sort_index(inplace=True)
    for k in highlight:
        df["title"] = df["title"].map(
            lambda t: re.sub(f"({re.escape(k)})", r"<b>\1</b>", string=t, flags=re.IGNORECASE)
        )
        df["abstract"] = df["abstract"].map(
            lambda t: re.sub(f"({re.escape(k)})", r"<b>\1</b>", string=t, flags=re.IGNORECASE)
        )
        df["keywords"] = df["keywords"].map(
            lambda t: re.sub(f"({re.escape(k)})", r"<b>\1</b>", string=t, flags=re.IGNORECASE)
        )
    df["title"] = "<a href='" + df["link"] + "'>" + df["title"] + "</a>"
    
    if not show_abstract and "abstract" in COLUMNS:
        COLUMNS.remove("abstract")
    if not show_keywords and "keywords" in COLUMNS:
        COLUMNS.remove("keywords")


    if len(df):
        t_current = df["start"].values.astype(np.int64)
        # Round from nsecs to 10 minute blocks
        # t_current = df["start"].values.astype(np.int64) // 1000000000 // 600
        idx_ch = t_current[1:] - t_current[:-1]
        idx_ch = np.argwhere(idx_ch).squeeze() + 1

        # st.write(idx_ch)
        last_ch = 0
        for ch in list(idx_ch) + [len(df)]:
            ch = ch
            df_sec = df.iloc[last_ch:ch]
            if len(df_sec):
                # container.write(df_sec[COLUMNS].to_html(escape=False), unsafe_allow_html=True)
                df_sec_html = table_to_html(df_sec[COLUMNS])
                # df_sec_html = table_to_html(df_sec)
                container.subheader(f"{df['start'].iloc[last_ch].strftime('%a')} {df.index[last_ch]}")
                container.markdown(df_sec_html, unsafe_allow_html=True)
            last_ch = ch
        # container.write(df[COLUMNS].to_html(escape=False), unsafe_allow_html=True)


def main():
    keywords = list()
    papers, rooms = load_data()
    df_papers = pd.DataFrame(papers)
    n_all = len(df_papers)

    # Reformat dates
    date, time = df_papers["date"], df_papers["time"]
    df_papers["start"], df_papers["end"] = parse_datetimes(date, time)
    df_papers["time"] = df_papers["start"].map(lambda t: t.strftime("%H:%M"))
    # df_papers["duration"] = df_papers["end"] - df_papers["start"]$
    # df_papers["duration"] = df_papers["duration"].map(lambda t: str(t))

    # Reformat rooms
    df_papers["room"] = df_papers["id"].str.split(" ", expand=True).iloc[:, 1].str.split(".", expand=True).iloc[:, 0].map(rooms)  # noqa
    df_papers["room"] = df_papers["room"].map(lambda t: re.search(r"\((.*)\)", str(t))[1])
    df_papers["room"] = df_papers["room"].str.replace("Room ", "")

    # Split abstract / keywords
    df_abstract = df_papers["abstract"].str.split("Abstract: ", expand=True)
    df_papers["keywords"] = df_abstract.iloc[:, 0].str.split("Keywords: ", expand=True).iloc[:, 1]
    df_papers["abstract"] = df_abstract.iloc[:, 1]

    # GCal Links
    # https://www.google.com/calendar/render?action=TEMPLATE&text=PAPER&details=ABSTRACT&location=ROOM&dates=20221024T010000Z%2F20221024T012000Z
    df_papers["📅"] = (
        "<a href='https://www.google.com/calendar/render?action=TEMPLATE&text="
        + df_papers["title"].map(quote)
        + "&details="
        + df_papers["keywords"].map(quote)
        + "&location="
        + df_papers["room"].map(quote)
        + "&dates=" + df_papers["start"].dt.strftime("%Y%m%dT%H%M%S")
        + "%2F" + df_papers["end"].dt.strftime("%Y%m%dT%H%M%S")
        + "'>➕</a>"
    )
    df_papers["room"] = "<div style='white-space: nowrap'>" + df_papers["room"] + "</div>"

    tags = defaultdict(int)
    for kws in df_papers["keywords"].to_list():
        for kw in kws.split(", "):
            tags[kw.lower().strip()] += 1
    tags = sorted([(v, k) for k, v in tags.items()], key=lambda v: -v[0])

    # Create links
    df_papers["link"] = df_papers["title"].map(lambda t: f"https://scholar.google.com/scholar?q={t}")

    # SIDEBAR
    #########
    st.sidebar.title("Show / Hide")
    st.sidebar.subheader("Days")
    DAYS_FILTER["Monday"] = st.sidebar.checkbox("Monday, 24th Oct", DAYS_FILTER["Monday"])
    DAYS_FILTER["Tuesday"] = st.sidebar.checkbox("Tuesday, 25th Oct", DAYS_FILTER["Tuesday"])
    DAYS_FILTER["Wednesday"] = st.sidebar.checkbox("Wednesday, 26th Oct", DAYS_FILTER["Wednesday"])
    days_mask = [False] * len(df_papers)
    for d in DAYS:
        days_mask = days_mask | (DAYS_FILTER[d] & (df_papers["start"].dt.date == DAYS[d]))
    df_papers = df_papers[days_mask]

    st.sidebar.subheader("Columns")
    show_abstract = st.sidebar.checkbox("Show abstract", value=False)
    show_keywords = st.sidebar.checkbox("Show keywords", value=False)

    st.sidebar.subheader("Tags")
    cb_keywords = list()
    for t in tags:
        if st.sidebar.checkbox(f"{t[1]} ({t[0]})", value=False):
            cb_keywords.append(t)

    # Filter newline
    df_papers["title"] = df_papers["title"].map(lambda t: t.replace("\n", " "))
    df_papers["abstract"] = df_papers["abstract"].map(lambda t: str(t).replace("\n", " "))
    df_papers["keywords"] = df_papers["keywords"].map(lambda t: t.replace("\n", " "))

    # MAIN BODY
    ###########
    st.title("📅 IROS 2022 Paper Timetable")

    # Filter Keywords Input
    with st.expander("Filter"):
    # st.subheader("Filter")
        keywords = st.text_input("Custom Keywords", help="Seperate multiple keywords by a space.")  # noqa
        # keywords = keywords.replace(" ", "")
        keywords = [k for k in keywords.split(" ") if k != ""]
        selected_tags = (st.multiselect("Popular Tags", options=tags, default=cb_keywords, format_func=lambda v: f"{v[1]} ({v[0]})"))
        keywords.extend([v[1] for v in selected_tags])
        keywords.extend([v[1] for v in cb_keywords])
        for k in keywords:
            df_papers = df_papers[
                df_papers["title"].str.lower().str.contains(k) |
                df_papers["keywords"].str.lower().str.contains(k)
            ]
            # df_papers["title"] = df_papers["title"].map(lambda t: t.replace(k, f"<b>{k}</b>"))

    st.text(f"Showing {len(df_papers)} out of {n_all} papers")
    now = datetime.datetime.now()
    # now = datetime.datetime(2022, 10, 24, 11, 23)
    now = now - datetime.timedelta(minutes=now.minute % 10)
    
    # tabs = st.tabs([f"Now"] + list(DAYS.keys()))
    tabs = st.tabs(["All", "Live"])

    if len(df_papers):
        for d in DAYS:
            if DAYS_FILTER[d]:
                generate_tables(
                    container=tabs[0],
                    data=df_papers,
                    date=DAYS[d],
                    highlight=keywords,
                    show_abstract=show_abstract,
                    show_keywords=show_keywords,
                )

    generate_tables(
        container=tabs[1],
        data=df_papers,
        date=now.date(),
        time=now.time(),
        range=datetime.timedelta(hours=1),
        highlight=keywords,
        show_abstract=show_abstract,
        show_keywords=show_keywords
    )


if __name__ == "__main__":
    st.set_page_config(page_title="IROS Paper Timetable", layout="wide")
    main()
