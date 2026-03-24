import os
import pandas as pd
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)
DATA_DIR = r"c:\AI Agent Folder\mbdl_draft"
LIVE_STATE_PATH = os.path.join(DATA_DIR, 'live_draft_state.csv')
BATTERS_PATH = os.path.join(DATA_DIR, 'Draft_Board_Master_Batters.csv')
PITCHERS_PATH = os.path.join(DATA_DIR, 'Draft_Board_Master_Pitchers.csv')

def initialize_data():
    if os.path.exists(LIVE_STATE_PATH):
        print("Removing existing live_draft_state.csv...")
        try:
            os.remove(LIVE_STATE_PATH)
        except OSError as e:
            print("Error removing file:", e)
            
    print("live_draft_state.csv not found or removed. Initializing from master files...")
    batters_df = pd.read_csv(BATTERS_PATH)
    batters_df['Type'] = 'B'
    
    pitchers_df = pd.read_csv(PITCHERS_PATH)
    pitchers_df['Type'] = 'P'
    
    # Concatenate and save
    df = pd.concat([batters_df, pitchers_df], ignore_index=True)
    # Ensure 'CBS Salary' and 'Dollars' cols exist and are numeric
    df['CBS Salary'] = pd.to_numeric(df['CBS Salary'], errors='coerce').fillna(0.0)
    df['Dollars'] = pd.to_numeric(df['Dollars'], errors='coerce').fillna(0.0)
    
    proj_cols = ['AVG', 'HR', 'R', 'RBI', 'SB', 'ERA', 'WHIP', 'K', 'QS', 'SHD', 'PA', 'IP']
    for col in proj_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
        else:
            df[col] = 0.0
            
    if 'POS' in df.columns:
        df['POS'] = df['POS'].fillna('UNK')
    else:
        df['POS'] = 'UNK'
        
    if 'MLB' in df.columns:
        df['MLB'] = df['MLB'].fillna('FA')
    else:
        df['MLB'] = 'FA'
        
    df.to_csv(LIVE_STATE_PATH, index=False)
    print("live_draft_state.csv generated successfully.")
    return df


def load_data():
    return pd.read_csv(LIVE_STATE_PATH)

def save_data(df):
    df.to_csv(LIVE_STATE_PATH, index=False)

def get_draft_context():
    df = load_data()
    TOTAL_ECONOMY = 4160.0
    
    # Active players: not Free Agent and not Minors
    active_mask = (df['Avail'] != 'Free Agent') & (df['Avail'] != 'Minors')
    active_df = df[active_mask]
    
    total_kept_salaries = active_df['CBS Salary'].sum()
    total_kept_value = active_df['Dollars'].sum()
    
    remaining_economy = TOTAL_ECONOMY - total_kept_salaries
    remaining_value = TOTAL_ECONOMY - total_kept_value
    
    if remaining_value <= 0:
        inflation_multiplier = 1.0
    else:
        inflation_multiplier = max(1.0, remaining_economy / remaining_value)
        
    # Hot Balls specific
    hot_balls_df = df[df['Avail'] == 'Hot Balls']
    hb_spent = hot_balls_df['CBS Salary'].sum()
    hb_remaining = max(0.0, 260.0 - hb_spent)
    hb_roster_size = len(hot_balls_df)
    
    # Roster limit 23
    slots_left = max(1, 23 - hb_roster_size)
    hb_max_bid = max(0.0, hb_remaining - (slots_left - 1))
    
    # Calculate team stats
    team_stats = {}
    valid_teams = [t for t in df['Avail'].unique() if pd.notna(t) and t not in ['Free Agent', 'Minors']]
    
    for team in valid_teams:
        t_df = df[df['Avail'] == team]
        
        # Counting stats (fillna 0 and sum)
        def ssum(col):
            if col in t_df.columns:
                return float(pd.to_numeric(t_df[col], errors='coerce').fillna(0.0).sum())
            return 0.0
            
        hr = ssum('HR')
        r = ssum('R')
        rbi = ssum('RBI')
        sb = ssum('SB')
        k = ssum('K')
        qs = ssum('QS')
        shd = ssum('SHD')
        
        # Rate stats
        # Need to ensure PA and IP exist
        if 'PA' in t_df.columns and 'AVG' in t_df.columns:
            pa_series = pd.to_numeric(t_df['PA'], errors='coerce').fillna(0.0)
            avg_series = pd.to_numeric(t_df['AVG'], errors='coerce').fillna(0.0)
            sum_pa = pa_series.sum()
            avg = float((avg_series * pa_series).sum() / sum_pa) if sum_pa > 0 else 0.0
        else:
            avg = 0.0

        if 'IP' in t_df.columns:
            ip_series = pd.to_numeric(t_df['IP'], errors='coerce').fillna(0.0)
            sum_ip = ip_series.sum()
            if sum_ip > 0:
                era_series = pd.to_numeric(t_df['ERA'], errors='coerce').fillna(0.0) if 'ERA' in t_df.columns else pd.Series(0.0, index=ip_series.index)
                era = float((era_series * ip_series).sum() / sum_ip)
                whip_series = pd.to_numeric(t_df['WHIP'], errors='coerce').fillna(0.0) if 'WHIP' in t_df.columns else pd.Series(0.0, index=ip_series.index)
                whip = float((whip_series * ip_series).sum() / sum_ip)
            else:
                era, whip = 0.0, 0.0
        else:
            era, whip = 0.0, 0.0
            
        team_stats[team] = {
            'HR': hr, 'R': r, 'RBI': rbi, 'SB': sb,
            'K': k, 'QS': qs, 'SHD': shd,
            'AVG': avg, 'ERA': era, 'WHIP': whip
        }
        
    return {
        'total_kept_salaries': float(total_kept_salaries),
        'total_kept_value': float(total_kept_value),
        'inflation_multiplier': float(inflation_multiplier),
        'hot_balls': {
            'spent': float(hb_spent),
            'remaining': float(hb_remaining),
            'roster_size': int(hb_roster_size),
            'max_bid': float(hb_max_bid)
        },
        'team_stats': team_stats
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/state')
def api_state():
    df = load_data()
    context = get_draft_context()
    mult = context['inflation_multiplier']
    
    # Free agents
    fa_df = df[df['Avail'] == 'Free Agent'].copy()
    
    fa_list = []
    for _, row in fa_df.iterrows():
        calc_val = float(row.get('Dollars', 0.0)) * float(mult)
        fa_list.append({
            'Player': str(row.get('Player', '')),
            'Type': str(row.get('Type', '')),
            'POS': str(row.get('POS', 'UNK')),
            'MLB': str(row.get('MLB', 'FA')),
            'AVG': float(row.get('AVG', 0.0)),
            'HR': int(float(row.get('HR', 0.0))),
            'R': int(float(row.get('R', 0.0))),
            'RBI': int(float(row.get('RBI', 0.0))),
            'SB': int(float(row.get('SB', 0.0))),
            'ERA': float(row.get('ERA', 0.0)),
            'WHIP': float(row.get('WHIP', 0.0)),
            'K': int(float(row.get('K', 0.0))),
            'QS': int(float(row.get('QS', 0.0))),
            'SHD': int(float(row.get('SHD', 0.0))),
            'Dollars': float(row.get('Dollars', 0.0)),
            'Inflation_Value': calc_val
        })
    
    # Hot Balls roster
    hb_df = df[df['Avail'] == 'Hot Balls']
    hb_list = []
    for _, row in hb_df.iterrows():
        hb_list.append({
            'Player': str(row.get('Player', '')),
            'CBS Salary': float(row.get('CBS Salary', 0.0))
        })
    
    return jsonify({
        'free_agents': fa_list,
        'hot_balls_roster': hb_list,
        'context': context
    })

@app.route('/api/draft', methods=['POST'])
def api_draft():
    data = request.json
    player = data.get('player')
    team = data.get('team')
    price = float(data.get('price', 0.0))
    
    df = load_data()
    idx = df[df['Player'] == player].index
    if not idx.empty:
        df.loc[idx, 'Avail'] = team
        df.loc[idx, 'CBS Salary'] = price
        df.loc[idx, 'Contract Status'] = 'Standard'
        save_data(df)
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Player not found'}), 404

@app.route('/api/undo', methods=['POST'])
def api_undo():
    data = request.json
    player = data.get('player')
    
    df = load_data()
    idx = df[df['Player'] == player].index
    if not idx.empty:
        df.loc[idx, 'Avail'] = 'Free Agent'
        df.loc[idx, 'CBS Salary'] = 0.0
        df.loc[idx, 'Contract Status'] = 'FA'
        save_data(df)
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Player not found'}), 404

def _get_unique_teams():
    df = load_data()
    teams = df['Avail'].unique().tolist()
    # exclude free agent and minors
    return [t for t in teams if t not in ['Free Agent', 'Minors', None] and pd.notna(t)]

@app.route('/api/teams')
def api_teams():
    # Helper to populate teams if you want dynamic
    return jsonify({'teams': _get_unique_teams()})

if __name__ == '__main__':
    initialize_data()
    app.run(debug=True, port=5000)
