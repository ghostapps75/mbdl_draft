import pandas as pd

def kill_phantoms(filename, sort_col):
    print(f"Scanning {filename} for duplicate phantom prospects...")
    df = pd.read_csv(filename)
    
    # Track starting rows
    starting_rows = len(df)
    
    # Sort so the REAL player (most HRs or Strikeouts) is at the very top
    df = df.sort_values(by=[sort_col, 'Dollars'], ascending=[False, False])
    
    # Drop any player that shares the exact same name, keeping only the best one
    df = df.drop_duplicates(subset=['Player'], keep='first')
    
    # Calculate how many ghosts we killed
    killed = starting_rows - len(df)
    
    # Save the pristine file
    df.to_csv(filename, index=False)
    print(f"Successfully eliminated {killed} phantom minor leaguers from {filename}!\n")

# Run it for both files (Sorting by Home Runs for batters, Strikeouts for pitchers)
kill_phantoms('Draft_Board_Master_Batters.csv', 'HR')
kill_phantoms('Draft_Board_Master_Pitchers.csv', 'K')