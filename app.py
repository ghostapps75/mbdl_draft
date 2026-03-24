import os
import pandas as pd
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)
DATA_DIR = r"c:\AI Agent Folder\mbdl_draft"
LIVE_STATE_PATH = os.path.join(DATA_DIR, 'live_draft_state.csv')
BATTERS_PATH = os.path.join(DATA_DIR, 'Draft_Board_Master_Batters.csv')
PITCHERS_PATH = os.path.join(DATA_DIR, 'Draft_Board_Master_Pitchers.csv')

def initialize_data():
    if not os.path.exists(LIVE_STATE_PATH):
        print("live_draft_state.csv not found. Initializing from master files...")
        batters_df = pd.read_csv(BATTERS_PATH)
        batters_df['Type'] = 'B'
        
        pitchers_df = pd.read_csv(PITCHERS_PATH)
        pitchers_df['Type'] = 'P'
        
        # Concatenate and save
        df = pd.concat([batters_df, pitchers_df], ignore_index=True)
        # Ensure 'CBS Salary' and 'Dollars' cols exist and are numeric
        df['CBS Salary'] = pd.to_numeric(df['CBS Salary'], errors='coerce').fillna(0.0)
        df['Dollars'] = pd.to_numeric(df['Dollars'], errors='coerce').fillna(0.0)
        df.to_csv(LIVE_STATE_PATH, index=False)
        print("live_draft_state.csv generated successfully.")
        return df
    else:
        return pd.read_csv(LIVE_STATE_PATH)

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
    
    return {
        'total_kept_salaries': float(total_kept_salaries),
        'total_kept_value': float(total_kept_value),
        'inflation_multiplier': float(inflation_multiplier),
        'hot_balls': {
            'spent': float(hb_spent),
            'remaining': float(hb_remaining),
            'roster_size': int(hb_roster_size),
            'max_bid': float(hb_max_bid)
        }
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
    fa_df['Inflation_Value'] = fa_df['Dollars'] * mult
    
    # Replace NaN with None stringification to avoid JSON NaN error if there is any
    fa_df = fa_df.where(pd.notnull(fa_df), None)
    
    # Only return required columns to frontend to save bandwidth
    fa_cols = ['Player', 'Type', 'Dollars', 'Inflation_Value']
    fa_list = fa_df[fa_cols].to_dict(orient='records')
    
    # Hot Balls roster
    hb_df = df[df['Avail'] == 'Hot Balls']
    hb_list = hb_df[['Player', 'CBS Salary']].to_dict(orient='records')
    
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
