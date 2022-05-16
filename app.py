import streamlit as st
from apps import settings, draft, home, utils


def main():
    app = utils.MultiApp()

    st.markdown(
        """
    # Fantasy Football Draft Optimizer
    """
    )

    # Add all your application here
    app.add_app("Home", home.app)
    app.add_app("Settings", settings.app)
    app.add_app("Draft", draft.app)
    # The main app
    app.run()


if __name__ == "__main__":
    main()
