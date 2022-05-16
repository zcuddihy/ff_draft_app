import itertools
import pandas as pd
import numpy as np
import streamlit as st


class DraftSettings:
    def __init__(
        self,
        n_starters: dict,  # e.g. {QB: 1, RB: 2.....}
        flex_positions: list,
        scoring: str,
        draft_order: str,
        first_pick: int,
        n_teams: int,
        year: int,
    ):
        self.n_starters = n_starters
        self.flex_positions = flex_positions  # Standard (RB, WR, TE), Super Flex (RB, WR, TE, QB), RB/WR or None
        self.scoring = scoring  # PPR, Half-PPR, Standard
        self.draft_order = draft_order  # Snake or Custom
        self.first_pick = first_pick
        self.n_teams = n_teams
        self.year = year
        self.predictions = pd.read_csv(
            "./data/{year}/season_projections.csv".format(year=self.year)
        )
        self.players = list(self.predictions.Player)
        self.position_combinations = self.generate_position_combinations()

    def generate_position_combinations(self):
        """
        Returns
        -------
        all_position_combinations :

        """

        # Setup the list of starting positions and the number of starters (excluding K, and DST or IDP)
        positions = {
            "QB": self.n_starters["QB"],
            "RB": self.n_starters["RB"],
            "WR": self.n_starters["WR"],
            "TE": self.n_starters["TE"],
            "FLEX": self.n_starters["Flex"],
        }

        combined_positions = []
        for key, value in positions.items():
            for i in range(value):
                combined_positions.append(key)

        # Initial list of of draft combinations with the FLEX "position"
        initial_draft_combinations = set(itertools.permutations(combined_positions))

        # Skip all the extra steps if there are no FLEX "positions"
        if self.flex_positions != None:
            """
            Map the flex_positions list to every location where the FLEX "position" occurs
            Convert each non-Flex position to it's own list to properly use itertools.product in the next step
            Use itertools.product to get all lists from list containing flex players list

            EXAMPLE:
            Initial list: ['QB','WR','TE','FLEX','RB','RB','WR'] 
            List with flex replaced: ['QB','WR','TE',['RB','WR','TE'],'RB','RB','WR'] 
            Lists after itertools.product:
                    ['QB','WR','TE','RB','RB','RB','WR'] 
                    ['QB','WR','TE','WR','RB','RB','WR'] 
                    ['QB','WR','TE','TE','RB','RB','WR'] 
            """
            modified_draft_combinations = [
                list(map(lambda x: [x] if x != "FLEX" else self.flex_positions, i))
                for i in initial_draft_combinations
            ]

            modified_draft_combinations = [
                list(itertools.product(*modified_draft_combinations[i]))
                for i in range(len(modified_draft_combinations))
            ]

            # The modified_draft_combinations is a list of lists of lists
            # Reappend the list so it is a list of lists instead
            draft_combinations_combined = []
            for outside_list in modified_draft_combinations:
                for i in range(len(outside_list)):
                    draft_combinations_combined.append(outside_list[i])

            # Convert the list of lists into a dataframe
            all_position_combinations = pd.DataFrame(set(draft_combinations_combined))
        else:
            all_position_combinations = pd.DataFrame((initial_draft_combinations))

        # Adjust the column names to match the round numbers
        cols = np.arange(1, len(all_position_combinations.columns) + 1, 1)
        all_position_combinations.set_axis(cols, axis=1, inplace=True)

        return all_position_combinations


def app():

    col1, col2 = st.columns(2)

    with col1:
        st.header("Position Settings")
        # Collect the number of starters and flex type
        n_qb = st.number_input("QB", 0, 3, 1)
        n_rb = st.number_input("RB", 0, 8, 2)
        n_wr = st.number_input("WR", 0, 8, 2)
        n_te = st.number_input("TE", 0, 4, 1)
        n_flex = st.number_input("Flex", 0, 4, 0)
        n_k = st.number_input("K", 0, 4, 1)
        n_dst = st.number_input("DST", 0, 4, 1)
        flex_positions = st.multiselect(
            "Select the flex positions", ["QB", "RB", "WR", "TE"],
        )

    n_starters = {
        "QB": n_qb,
        "RB": n_rb,
        "WR": n_wr,
        "TE": n_te,
        "Flex": n_flex,
        "K": n_k,
        "DST": n_dst,
    }

    with col2:
        st.header("League Settings")
        n_teams = st.number_input("Number of Teams", 2, 24, 12)
        first_pick = st.number_input("Enter your First Pick", 2, 24)
        scoring = st.selectbox("Scoring", ("PPR", "Half-PPR", "Standard"),)
        draft_order = st.selectbox("Draft Order", ("Snake", "Custom"),)

    with st.form(key="Save Settings"):
        submit = st.form_submit_button("Save Settings")

    if submit:
        settings = DraftSettings(
            n_starters=n_starters,
            flex_positions=flex_positions,
            scoring=scoring,
            draft_order=draft_order,
            first_pick=first_pick,
            n_teams=n_teams,
            year=2021,
        )
        st.session_state.settings = settings

