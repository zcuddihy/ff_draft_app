# %%
import itertools
import numpy as np
import pandas as pd
import pickle
from scipy.stats import norm
import seaborn as sns

# ONLY SET UP FOR 1QB, 2RB, 2WR, 1TE, 1FLEX(RB,WR,TE) AS OF NOW
# HAVE NOT ATTEMPTED TWO FLEX POSITIONS, NOT SURE IF ITERTOOLS.PRODUCT WILL WORK


class Draft_Setup:

    def __init__(self, n_QB, n_RB, n_WR, n_TE, n_FLEX, flex_type, draft_picks, year):
        self.n_QB = n_QB
        self.n_RB = n_RB
        self.n_WR = n_WR
        self.n_TE = n_TE
        self.n_FLEX = n_FLEX
        # Either: Standard (RB, WR, TE), Super Flex (RB, WR, TE, QB), RB/WR or None
        self.flex_type = flex_type
        self.draft_picks = draft_picks
        self.year = year

    def initialize_player_data(self):
        '''

        Parameters
        ----------
        year : TYPE
            DESCRIPTION.

        Returns
        -------
        season_projections : Dataframe of all players with the following information:
            FPTS: Projected fantasy points for the season
            ADP Mean: Average draft position mean
            ADP Std: Average draft positition standard deviation
            WAR: Wins above replacement based on the projected fantasy points

        '''

        # Load the season projection data
        season_projections = pd.read_csv(
            './data/{year}/season_projections.csv'.format(year=self.year))

        # Load the linear regression models that define the wins above replacement
        # for each player based on their position
        WAR_file = open('./war_linear_models/PPR.pickle', 'rb')
        WAR_linear_models = pickle.load(WAR_file)

        def apply_WAR_model(points, position):
            '''

            Parameters
            ----------
            points : Projected fantasy points for the season to be input 
            into the linear regression model.
            position : Players position that will be used to look up the 
            linear regression model to calculate the WAR.

            Returns
            -------
            WAR : The players projected wins above replacement based on the 
            projected season fantasy points. 

            '''
            WAR = float(WAR_linear_models[position].predict([[points]]))
            return WAR

        # Apply the calculate_WAR function for each player to determine the predicted
        # wins above replacement.
        # Must be done iterating over rows (unless there's an easier options)
        season_projections['WAR'] = season_projections[['FPTS', 'Pos']].apply(
            lambda row: apply_WAR_model(*row), axis=1)

        return season_projections

    def position_combinations(self):
        '''


        Returns
        -------
        all_position_combinations :

        '''

        # Setup the list of starting positions and the number of starters (excluding K, and DST or IDP)
        positions = {
            'QB': self.n_QB,
            'RB': self.n_RB,
            'WR': self.n_WR,
            'TE': self.n_TE,
            'FLEX': self.n_FLEX
        }

        combined_positions = []
        for key, value in positions.items():
            for i in range(value):
                combined_positions.append(key)

        # Setup the list of flex positions based on the user input
        if self.flex_type == 'Standard':
            flex_positions = ['RB', 'WR', 'TE']
        elif self.flex_type == 'Super Flex':
            flex_positions = ['QB', 'RB', 'WR', 'TE']
        elif self.flex_type == 'RB/WR':
            flex_positions = ['RB', 'WR']
        elif self.flex_type == 'None':
            pass

        # Initial list of of draft combinations with the FLEX "position"
        initial_draft_combinations = (
            set(itertools.permutations(combined_positions)))

        # Skip all the extra steps if there are no FLEX "positions"
        if self.flex_type != 'None':
            '''
            Map the flex_positions list to every location where the FLEX "position" occurs
            Convert each non-Flex position to it's own list to properly use itertools.product in the next step
            Use itertools.product to get all lists from list containing flex players list

            EXAMPLE:
            Intial list: ['QB','WR','TE','FLEX','RB','RB','WR'] 
            List with flex replaced: ['QB','WR','TE',['RB','WR','TE'],'RB','RB','WR'] 
            Lists after itertools.product:
                    ['QB','WR','TE','RB','RB','RB','WR'] 
                    ['QB','WR','TE','WR','RB','RB','WR'] 
                    ['QB','WR','TE','TE','RB','RB','WR'] 
            '''
            modified_draft_combinations = [list(map(lambda x: [x] if x != 'FLEX' else flex_positions, i))
                                           for i in initial_draft_combinations]

            modified_draft_combinations = [list(itertools.product(*modified_draft_combinations[i]))
                                           for i in range(len(modified_draft_combinations))]

            # The modified_draft_combinations is a list of lists of lists
            # Reappend the list so it is a list of lists instead
            draft_combinations_combined = []
            for outside_list in modified_draft_combinations:
                for i in range(len(outside_list)):
                    draft_combinations_combined.append(outside_list[i])

            # Convert the list of lists into a dataframe
            all_position_combinations = pd.DataFrame(
                set(draft_combinations_combined))
        else:
            all_position_combinations = pd.DataFrame(
                (initial_draft_combinations))

        return all_position_combinations


def positional_value_by_round(active_pick, draft_picks, undrafted_players):
    '''

    Parameters
    ----------
    active_pick : Integer of the active pick in the draft
    draft_picks : List of the managers draft picks
    undrafted_players : Dataframe of all undrafted players 

    Returns
    -------
    position_value_by_round : Dictionary of dictionaries
    The nested dictionary contains the positional values for each position per round. These
    values are the probabilistic wins above replacement for the position in the specific
    round. The outer dictionary key is the round number (e.g. 1, 2, 3, etc.).
    These values will be used to check all possible draft combinations to determine
    the most optimal player to draft.

    '''

    def grouped_probability(df, i):

        # Sort the WAR value descending in order to classify the order of "best" players
        df.sort_values(by='WAR', ascending=False)

        # Calculate the probability that each player is available at the specified draft pick
        df['p_Available'] = 1-norm(df.loc[:,'ADP Avg'], df.loc[:,'ADP Std']).cdf(i)

        # Calculate the probability that each player is NOT available at the specified draft pick
        df['p_Not Available'] = norm(df['ADP Avg'], df['ADP Std']).cdf(i)

        # Calculate the probability that this player is the best available player at their position
        # First, take the cumulative product of the p_Not Available for all players better than
        # the player in question. This is accomplished by shifting the values down 1 since
        # cumprod() also includes the the row we are analyzing.
        # Then multiply the player in questions p_Available by the cumulative product previously calculated.
        df['p_Best Available'] = (
            (df['p_Not Available'].cumprod()).shift(1))*df['p_Available']

        # Since the dataframes were shifted, the top player in each dataframe will have an nan value.
        # Replace the nan value with this players p_Available since they are the best available.
        df['p_Best Available'].fillna(df['p_Available'], inplace=True)

        # Determine the adjusted player WAR based on the p_Best Available
        # dWAR = dynamic Wins Above Replacement
        df['dWAR'] = df['WAR']*df['p_Best Available']

        return df

    position_value_by_round = {}
    round_counter = 1
    for i in draft_picks:

        # Only consider future rounds.
        if i > active_pick:

            undrafted_players = undrafted_players.groupby(
                by='Pos').apply(grouped_probability, i=i)
            positional_value = undrafted_players.groupby('Pos').sum()['dWAR']
            position_value_by_round[round_counter] = positional_value.to_dict()
        else:
            pass

        round_counter = round_counter+1

    return position_value_by_round


def remaining_draft_value(active_pick, draft_picks, position_value_by_round, position_combinations):
    '''

    Parameters
    ----------
    active_pick : Integer of the active pick in the draft
    draft_picks : List of the managers draft picks
    position_value_by_round : Dictionary of dictionaries with values for each position in each remaining round
    undrafted_players : Dataframe of all undrafted players 

    Returns
    -------
    combined_position_value : Dictionary 
        Combining all positional values by round for the remaining draft combinations. Dictionary has
        a single value for each position. This is then added to all undrafted players WAR value in the main()
        function based on their position.

    '''

    round_counter = 1
    temp_df = pd.DataFrame()
    for i in draft_picks:
        # Only consider future rounds.
        if i > active_pick:
            temp_df[round_counter] = position_combinations.loc[:,
                                                               round_counter-1].map(position_value_by_round[round_counter])
        # If pick has already occured, drop that rounds column from the combinations
        else:
            pass
        round_counter = 1+round_counter

    position_combinations['Total'] = temp_df.sum(axis=1)
    position_combinations.sort_values(
        by='Total', ascending=False, inplace=True)

    current_round = draft_picks.index(active_pick)
    combined_position_value = position_combinations.groupby(
        position_combinations.iloc[:, current_round])['Total'].max()
    combined_position_value = combined_position_value.to_dict()
    return combined_position_value


def start_draft():
    draft_picks = [3, 22, 27, 46, 51, 70, 75]
    Draft = Draft_Setup(1, 2, 2, 1, 1, 'Standard', draft_picks, 2021)
    all_players = Draft.initialize_player_data()
    all_position_combinations = Draft.position_combinations()

    drafted_players = []
    my_team = []
    active_pick = 1
    remaining_draft_combinations = all_position_combinations.copy()
    for j in range(1, 76):
        undrafted_players = all_players[~all_players['Player'].isin(
            drafted_players)]

        if j in draft_picks:

            # Calculate the positional value by round
            position_value_by_round = positional_value_by_round(
                active_pick, draft_picks, undrafted_players)

            # Calculate combined value of all future rounds by position
            combined_position_value = remaining_draft_value(
                active_pick, draft_picks, position_value_by_round, remaining_draft_combinations)

            # Calculated the dynamic WAR for each player
            undrafted_players.loc[:,'dWAR'] = undrafted_players['Pos'].map(
                combined_position_value)+undrafted_players.loc[:,'WAR']
            undrafted_players.sort_values(
                by='dWAR', ascending=False, inplace=True)

            # Get the managers selection
            cols_to_display = ['Player', 'Team', 'Pos', 'FPTS']
            print(undrafted_players[cols_to_display].head(10))
            player_selected = int(input('Enter the player index : '))

            # Add the selected player to the drafted_players list and the my_team list
            drafted_players.append(
                undrafted_players.loc[player_selected, 'Player'])
            my_team.append(undrafted_players.loc[player_selected, 'Player'])

            # Drop all rows without the players position in the selected round from
            # the remaining_draft_combinations dataframe
            drafted_position = undrafted_players.loc[player_selected, 'Pos']
            column_lookup = draft_picks.index(j)

            # Remove all draft combinations that didn't include the position selected this round
            remaining_draft_combinations = remaining_draft_combinations[remaining_draft_combinations.iloc[:, column_lookup].isin([drafted_position])]
            print(remaining_draft_combinations.head(10))

            active_pick = active_pick+1
        else:
            undrafted_players.sort_values(
                by='ADP Avg', ascending=True, inplace=True)

            # Add the selected player to the drafted_players list
            # cols_to_display=['Player','Team','Pos','FPTS']
            # print(undrafted_players[cols_to_display].head(10))
            #player_selected=int(input('Enter the player index : '))
            undrafted_players.sort_values(
                by='ADP Avg', ascending=True, inplace=True)
            player_selected = undrafted_players.iloc[0, undrafted_players.columns.get_loc(
                'Player')]

            # Add the selected player to the drafted_players list
            # loc[player_selected,'Player'])
            drafted_players.append(player_selected)
            active_pick = active_pick+1


start_draft()



#%%

# Incorporate injury risk by position into the value check
# for example, take another RB even though they'll be on your bench or take a WR that will be in your starting lineup


# %%
