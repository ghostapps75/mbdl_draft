import pandas as pd
import re

def match_name(name):
    # Standardize names for exact matching
    return re.sub(r'\s+jr\.?$|\s+ii$|\s+iii$', '', str(name).replace('\xa0', ' ').strip().lower())

def fix_dollars(master_file, fg_file):
    print(f"Fixing corrupted values in {master_file}...")
    
    # Load the files
    master_df = pd.read_csv(master_file)
    fg_df = pd.read_csv(fg_file)
    
    # Drop the corrupted Dollars column
    master_df = master_df.drop(columns=['Dollars', 'Match_Name'], errors='ignore')
    
    # Create exact match columns
    master_df['Match_Name'] = master_df['Player'].apply(match_name)
    fg_df['Match_Name'] = fg_df['NameASCII'].apply(match_name)
    
    # Merge ONLY exact matches
    merged = pd.merge(master_df, fg_df[['Match_Name', 'Dollars']], on='Match_Name', how='left')
    
    # Fill anyone who isn't an exact match with $0.00
    merged['Dollars'] = merged['Dollars'].fillna(0.0).round(2)
    merged = merged.drop(columns=['Match_Name'])
    
    # Save the cleaned file
    merged.to_csv(master_file, index=False)
    
    # Print the top 5 to verify Cy Youngs are back on top
    top = merged.sort_values(by='Dollars', ascending=False).head(5)
    print("--- NEW TOP 5 ---")
    print(top[['Player', 'Dollars']].to_string(index=False))
    print("-----------------\n")

fix_dollars('Draft_Board_Master_Pitchers.csv', 'fangraphs-auction-pitchers.csv')
fix_dollars('Draft_Board_Master_Batters.csv', 'fangraphs-auction-batters.csv')