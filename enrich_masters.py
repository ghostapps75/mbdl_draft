import pandas as pd
import re
import difflib
import warnings
warnings.filterwarnings('ignore')

def match_name(name):
    # Standardize names for matching (remove Jr, II, accents, etc)
    return re.sub(r'\s+jr\.?$|\s+ii$|\s+iii$', '', str(name).replace('\xa0', ' ').strip().lower())

def enrich_file(master_file, fg_file, is_batter):
    print(f"Enriching {master_file}...")
    
    # Load the files
    master_df = pd.read_csv(master_file)
    fg_df = pd.read_csv(fg_file)
    
    # NEW: Drop the columns if they already exist from a previous run
    cols_to_remove = ['POS', 'MLB', 'Team', 'PA', 'IP']
    master_df = master_df.drop(columns=[c for c in cols_to_remove if c in master_df.columns])
    
    # Create matching columns
    master_df['Match_Name'] = master_df['Player'].apply(match_name)
    fg_df['Match_Name'] = fg_df['NameASCII'].apply(match_name)
    
    # Decide which columns to grab from FanGraphs
    if is_batter:
        fg_cols = ['Match_Name', 'POS', 'Team', 'PA']
    else:
        fg_cols = ['Match_Name', 'POS', 'Team', 'IP']
        
    # Merge the data
    merged = pd.merge(master_df, fg_df[fg_cols], on='Match_Name', how='left')
    
    # Fuzzy Match for any players that didn't link up perfectly
    missing_mask = merged['POS'].isna()
    missing_players = merged.loc[missing_mask, 'Player'].tolist()
    fg_names = fg_df['NameASCII'].astype(str).tolist()
    
    for p in missing_players:
        matches = difflib.get_close_matches(p, fg_names, n=1, cutoff=0.7)
        if matches:
            match_row = fg_df[fg_df['NameASCII'] == matches[0]].iloc[0]
            merged.loc[merged['Player'] == p, 'POS'] = match_row['POS']
            merged.loc[merged['Player'] == p, 'Team'] = match_row['Team']
            if is_batter: 
                merged.loc[merged['Player'] == p, 'PA'] = match_row['PA']
            else: 
                merged.loc[merged['Player'] == p, 'IP'] = match_row['IP']
                
    # Clean up and rename 'Team' to 'MLB'
    merged.rename(columns={'Team': 'MLB'}, inplace=True)
    merged['POS'] = merged['POS'].fillna('UNK')
    merged['MLB'] = merged['MLB'].fillna('FA')
    if is_batter: merged['PA'] = merged['PA'].fillna(0.0)
    else: merged['IP'] = merged['IP'].fillna(0.0)
    
    merged = merged.drop(columns=['Match_Name'])
    
    # Overwrite the master file with the enriched data
    merged.to_csv(master_file, index=False)
    print(f"Success! {master_file} is now enriched.")

# Execute using exactly the 4 files you have in your folder
enrich_file('Draft_Board_Master_Batters.csv', 'fangraphs-auction-batters.csv', is_batter=True)
enrich_file('Draft_Board_Master_Pitchers.csv', 'fangraphs-auction-pitchers.csv', is_batter=False)