import pandas as pd
import re
import difflib
import os
import warnings
warnings.filterwarnings('ignore')

def find_file(filename):
    search_dirs = ['.']
    for folder in search_dirs:
        filepath = os.path.join(folder, filename)
        if os.path.exists(filepath): return filepath
    print(f"CRITICAL WARNING: Could not find '{filename}' anywhere!")
    return filename

legend_df = pd.read_csv(find_file('player_projected_stats-2026.xlsx - Team Name Legend.csv'), header=None)
team_mapping = dict(zip(legend_df[0], legend_df[1]))
team_mapping['W'] = 'Free Agent'

def clean_name(name):
    name = str(name).replace('\xa0', ' ')
    return re.sub(r'\s+[A-Za-z0-9/,]+\s*•.*$', '', name).strip()

def match_name(name):
    return re.sub(r'\s+jr\.?$|\s+ii$|\s+iii$', '', str(name).replace('\xa0', ' ').strip().lower())

rosters = pd.read_csv(find_file('mbdl_full_league_rosters_2026.csv'))
for idx, row in rosters.iterrows():
    if pd.to_numeric(row['CBS Salary'], errors='coerce') == 0.0:
        try:
            rosters.at[idx, 'CBS Salary'] = float(row['Contract Status'])
            rosters.at[idx, 'Contract Status'] = 'Standard'
        except: pass
rosters['Player Name'] = rosters['Player Name'].str.strip().replace('Victor Scott II', 'Victor Scott')

def build_master(proj_name, fg_name, out_file, is_batter):
    df = pd.read_csv(find_file(proj_name))
    df['Player'] = df['Player'].apply(clean_name)
    df['Avail'] = df['Avail'].map(team_mapping).fillna(df['Avail'])
    
    merged = pd.merge(df, rosters[['Player Name', 'CBS Salary', 'Contract Status']], left_on='Player', right_on='Player Name', how='left')
    merged['CBS Salary'] = merged['CBS Salary'].fillna(0.0)
    merged['Contract Status'] = merged['Contract Status'].fillna('FA')
    merged = merged.drop(columns=['Player Name'])
    
    fg = pd.read_csv(find_file(fg_name))
    fg['Match_Name'] = fg['NameASCII'].apply(match_name)
    merged['Match_Name'] = merged['Player'].apply(match_name)
    
    if is_batter:
        fg_cols = ['Match_Name', 'Dollars', 'POS', 'Team', 'PA']
    else:
        fg_cols = ['Match_Name', 'Dollars', 'POS', 'Team', 'IP']
        
    final = pd.merge(merged, fg[fg_cols], on='Match_Name', how='left')
    final['Dollars'] = final['Dollars'].fillna(0.0).round(2)
    final['POS'] = final['POS'].fillna('UNK')
    final.rename(columns={'Team': 'MLB'}, inplace=True)
    
    missing_mask = final['Dollars'] == 0.0
    missing_players = final.loc[missing_mask, 'Player'].tolist()
    fg_names = fg['NameASCII'].astype(str).tolist()
    for p in missing_players:
        matches = difflib.get_close_matches(p, fg_names, n=1, cutoff=0.7)
        if matches:
            match_row = fg[fg['NameASCII'] == matches[0]].iloc[0]
            final.loc[final['Player'] == p, 'Dollars'] = match_row['Dollars']
            final.loc[final['Player'] == p, 'POS'] = match_row['POS']
            final.loc[final['Player'] == p, 'MLB'] = match_row['Team']
            if is_batter: final.loc[final['Player'] == p, 'PA'] = match_row['PA']
            else: final.loc[final['Player'] == p, 'IP'] = match_row['IP']
            
    final = final.drop(columns=['Match_Name'])
    final.to_csv(out_file, index=False)
    print(f"Successfully built: {out_file}")

# STRICT FILE NAMING ENFORCED HERE
build_master('player_projected_stats-2026.xlsx - Batters Projections.csv', 'fangraphs-auction-batters.csv', 'draftboard_master_batters.csv', True)
build_master('player_projected_stats-2026.xlsx - Pitchers Projections.csv', 'fangraphs-auction-pitchers.csv', 'draftboard_master_pitchers.csv', False)