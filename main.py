import re
import json
import datetime
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
    "Monday": False,
    "Tuesday": False,
    "Wednesday": False,
}
COLUMNS = [
    "room",
    "title",
    "abstract",
    "keywords"
]


@st.experimental_memo
def load_data():
    return json.load(open(F_PAPERS)), json.load(open(F_ROOMS))


@st.experimental_memo
def parse_datetimes(date: pd.Series, time: pd.Series):
    # date: pd.Series = pd.to_datetime(date)
    time = time.str.split("-", n=2, expand=True)
    ts_start = date.str.cat(time.iloc[:, 0], sep=" ")
    ts_end = date.str.cat(time.iloc[:, 1], sep=" ")
    ts_start, ts_end = pd.to_datetime(ts_start), pd.to_datetime(ts_end)

    return ts_start, ts_end


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

    # Split abstract / keywords
    df_abstract = df_papers["abstract"].str.split("Abstract: ", expand=True)
    df_papers["keywords"] = df_abstract.iloc[:, 0].str.split("Keywords: ", expand=True).iloc[:, 1]
    df_papers["abstract"] = df_abstract.iloc[:, 1]

    # Create links
    df_papers["link"] = df_papers["title"].map(lambda t: f"https://scholar.google.com/scholar?q={t}")

    # SIDEBAR
    #########
    st.sidebar.title("Filters")

    # Filter Keywords Input
    st.sidebar.subheader("Keywords")
    keywords = st.sidebar.text_input("Filter Keywords", help="Seperate multiple keywords by a space.")  # noqa
    # keywords = keywords.replace(" ", "")
    keywords = [k for k in keywords.split(" ") if k != ""]
    # keywords = st.sidebar.multiselect("Keywords", options=keywords, default=keywords)
    for k in keywords:
        df_papers = df_papers[
            df_papers["title"].str.lower().str.contains(k) |
            df_papers["keywords"].str.lower().str.contains(k)
        ]
        # df_papers["title"] = df_papers["title"].map(lambda t: t.replace(k, f"<b>{k}</b>"))

    st.sidebar.subheader("Days")
    DAYS_FILTER["Monday"] = st.sidebar.checkbox("Monday, 24th Oct", DAYS_FILTER["Monday"])
    DAYS_FILTER["Tuesday"] = st.sidebar.checkbox("Tuesday, 25th Oct", DAYS_FILTER["Tuesday"])
    DAYS_FILTER["Wednesday"] = st.sidebar.checkbox("Wednesday, 26th Oct", DAYS_FILTER["Wednesday"])
    days_mask = [False] * len(df_papers)
    for d in DAYS:
        days_mask = days_mask | (DAYS_FILTER[d] & (df_papers["start"].dt.date == DAYS[d]))
    df_papers = df_papers[days_mask]

    st.sidebar.subheader("Abstract")
    show_abstract = st.sidebar.checkbox("Show abstract", value=False)

    # Filter newline
    df_papers["title"] = df_papers["title"].map(lambda t: t.replace("\n", " "))
    df_papers["abstract"] = df_papers["abstract"].map(lambda t: str(t).replace("\n", " "))
    df_papers["keywords"] = df_papers["keywords"].map(lambda t: t.replace("\n", " "))

    # MAIN BODY
    ###########
    st.title("IROS 2022 Paper Timetable")
    st.text(f"Showing {len(df_papers)} out of {n_all} papers")
    if len(df_papers):
        for d in DAYS:
            if DAYS_FILTER[d]:
                st.subheader(d)
                df_day = df_papers[df_papers["start"].dt.date == DAYS[d]]
                df_day.set_index("time", inplace=True)
                df_day.sort_index(inplace=True)
                for k in keywords:
                    df_day["title"] = df_day["title"].map(
                        lambda t: re.sub(f"({re.escape(k)})", r"<b>\1</b>", string=t, flags=re.IGNORECASE)
                    )
                    df_day["abstract"] = df_day["abstract"].map(
                        lambda t: re.sub(f"({re.escape(k)})", r"<b>\1</b>", string=t, flags=re.IGNORECASE)
                    )
                    df_day["keywords"] = df_day["keywords"].map(
                        lambda t: re.sub(f"({re.escape(k)})", r"<b>\1</b>", string=t, flags=re.IGNORECASE)
                    )
                df_day["title"] = "<a href='" + df_day["link"] + "'>" + df_day["title"] + "</a>"
                if not show_abstract and "abstract" in COLUMNS:
                    COLUMNS.remove("abstract")
                # st.table(df_day[COLUMNS])
                st.write(df_day[COLUMNS].to_html(escape=False), unsafe_allow_html=True)


if __name__ == "__main__":
    st.set_page_config(page_title="IROS Paper Timetable", layout="wide")
    main()
