import streamlit as st

st.set_page_config(layout="wide")


def highlight_rows(row):
    value = row.loc["Pos"]
    if value == "QB":
        color = "#0077BB"  # Blue
    elif value == "RB":
        color = "#33BBEE"  # Cyan
    elif value == "WR":
        color = "#009988"  # Teal
    elif value == "TE":
        color = "#EE7733"  # Orange
    elif value == "K":
        color = "#CC3311"  # Red
    elif value == "DST":
        color = "#EE3377"  # Magenta
    return ["background-color: {}".format(color) for r in row]


def app():
    st.header("Drafting!")
    df = st.session_state.settings.predictions.sort_values(
        "FPTS", ascending=False
    ).style.apply(highlight_rows, axis=1)

    # CSS to inject contained in a string
    hide_dataframe_row_index = """
                <style>
                .row_heading.level0 {display:none}
                .blank {display:none}
                </style>
                """

    # Inject CSS with Markdown
    st.markdown(hide_dataframe_row_index, unsafe_allow_html=True)

    # display table
    st.dataframe(df, 750, 750)


app()
