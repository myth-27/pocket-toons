import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
from pathlib import Path

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="AI GREENLIGHT | COMMAND",
    layout="wide",
    page_icon="⚡",
    initial_sidebar_state="expanded"
)

# --- NEON CYBERPUNK THEME CSS ---
st.markdown("""
<style>
    /* 1. Global Theme */
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Inter:wght@400;600;800&display=swap');
    
    .stApp {
        background: radial-gradient(circle at top left, #0b0f1a, #05060a);
        color: #e0e0e0;
        font-family: 'Inter', sans-serif;
    }
    
    /* 2. Neon Spine */
    [data-testid="stSidebar"] {
        border-right: 2px solid #1e293b;
        background-color: #05060a;
    }
    .main .block-container {
        border-left: 3px solid transparent;
        border-image: linear-gradient(to bottom, #4f7dff, #7c5cff, rgba(0,0,0,0)) 1;
        padding-left: 3rem;
    }

    /* 3. Typography & Telemetry */
    h1, h2, h3 {
        font-family: 'Inter', sans-serif;
        letter-spacing: -0.5px;
        color: #f8fafc;
        text-shadow: 0 0 10px rgba(255,255,255,0.1);
    }
    .telemetry-text {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.8rem;
        color: #64748b;
        letter-spacing: 1px;
        text-transform: uppercase;
        margin-bottom: 5px;
        display: flex;
        align_items: center;
        gap: 10px;
    }
    .status-dot {
        height: 8px;
        width: 8px;
        background-color: #10b981;
        border-radius: 50%;
        box-shadow: 0 0 8px #10b981;
        display: inline-block;
    }
    
    /* 4. Narrative Payload (Input) */
    .stTextArea textarea {
        background: linear-gradient(180deg, #0f172a 0%, #020617 100%);
        border: 1px solid #1e293b;
        color: #94a3b8;
        border-radius: 8px;
        box-shadow: inset 0 2px 10px rgba(0,0,0,0.5);
        transition: all 0.3s ease;
    }
    .stTextArea textarea:focus {
        border-color: #4f7dff;
        box-shadow: 0 0 15px rgba(79, 125, 255, 0.3), inset 0 2px 10px rgba(0,0,0,0.5);
        color: #f1f5f9;
    }
    
    /* 5. Primary CTA (Glowing Button) */
    .stButton > button {
        background: linear-gradient(90deg, #2563eb, #7c3aed);
        color: white;
        border: none;
        padding: 18px 40px;
        font-size: 1.2rem;
        font-weight: 700;
        letter-spacing: 1px;
        border-radius: 6px;
        width: 100%;
        text-transform: uppercase;
        box-shadow: 0 0 20px rgba(124, 58, 237, 0.5);
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }
    .stButton > button:hover {
        transform: scale(1.02);
        box-shadow: 0 0 35px rgba(124, 58, 237, 0.8);
        letter-spacing: 2px;
    }
    
    /* 6. Decision Card */
    .decision-container {
        background: rgba(15, 23, 42, 0.8);
        border: 1px solid #334155;
        border-radius: 16px;
        padding: 40px;
        text-align: center;
        backdrop-filter: blur(10px);
        margin-top: 20px;
        animation: fadeIn 0.8s ease-out;
    }
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .decision-main {
        font-size: 4rem;
        font-weight: 900;
        letter-spacing: -2px;
        line-height: 1;
        margin-bottom: 10px;
        text-transform: uppercase;
        -webkit-background-clip: text;
        
    }
    .glow-green {
        color: #34d399;
        text-shadow: 0 0 40px rgba(52, 211, 153, 0.6);
        border-top: 4px solid #34d399;
    }
    .glow-blue {
        color: #60a5fa;
        text-shadow: 0 0 40px rgba(96, 165, 250, 0.6);
        border-top: 4px solid #60a5fa;
    }
    .glow-amber {
        color: #fbbf24;
        text-shadow: 0 0 40px rgba(251, 191, 36, 0.6);
        border-top: 4px solid #fbbf24;
    }
    .glow-red {
        color: #f87171;
        text-shadow: 0 0 40px rgba(248, 113, 113, 0.6);
        border-top: 4px solid #f87171;
    }
    
    /* 7. Insight Cards */
    .insight-box {
        background: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 20px;
        height: 100%;
        transition: transform 0.3s ease;
    }
    .insight-box:hover {
        transform: translateY(-5px);
        border-color: #334155;
    }
    
    /* Hide Streamlit Elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
</style>
""", unsafe_allow_html=True)

# Load Models
@st.cache_resource(ttl=1)
def load_models():
    from models.script_features import extract_script_features
    from models.genre_comparator import GenreComparator
    from models.decision_engine import DecisionEngine
    return extract_script_features, GenreComparator(), DecisionEngine()

extractor, comparator, engine = load_models()

# Load Genre Profiles
@st.cache_data(ttl=15)
def load_genre_data():
    try:
        df = pd.read_csv("data/processed/genre_profiles.csv")
        data = {}
        for _, row in df.iterrows():
            data[row['genre'].lower()] = row.to_dict()
        return data
    except:
        return {}

genre_data = load_genre_data()
genres = [g.capitalize() for g in genre_data.keys()] if genre_data else ["Action", "Fantasy", "Romance", "Drama"]

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("## 🧬 SYSTEM CONTROL")
    st.caption("AI COMMAND CENTER v2.1")
    
    st.divider()
    
    st.markdown("<div class='telemetry-text'>PARAMETER SETTINGS</div>", unsafe_allow_html=True)
    
    selected_genre_display = st.selectbox("Primary Genre Model", genres)
    selected_genre = selected_genre_display.lower() if selected_genre_display else "unknown"
    
    # Telemetry Panel
    if selected_genre in genre_data:
        prof = genre_data[selected_genre]
        count = prof.get('title_count', 0)
        conf = prof.get('confidence_level', 'Unknown')
        
        st.markdown(f"""
        <div style='background: #0f172a; padding: 15px; border-radius: 8px; border: 1px solid #1e293b; margin-top: 10px;'>
            <div class='telemetry-text'>MODEL TELEMETRY</div>
            <div style='color: #94a3b8; font-size: 0.9rem;'>
                TRAINING SET: <span style='color: #f8fafc;'>{count} TITLES</span><br>
                CONFIDENCE: <span style='color: #4f7dff;'>{conf}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Global System Stats
    total_titles = sum(d.get('title_count', 0) for d in genre_data.values())
    
    # Load Evaluation History for Script Count
    try:
        df_eval = pd.read_csv("data/processed/script_evaluation_history.csv")
        total_scripts = len(df_eval)
    except:
        total_scripts = 0
        
    st.markdown(f"""
    <div style='margin-top: 20px; padding-top: 20px; border-top: 1px solid #1e293b;'>
        <div class='telemetry-text'>SYSTEM CAPACITY</div>
        <div style='color: #64748b; font-size: 0.8rem;'>
            INDEXED TITLES: <span style='color: #e0e0e0;'>{total_titles}</span><br>
            EVALUATIONS RUN: <span style='color: #e0e0e0;'>{total_scripts}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    st.caption("SYSTEM STATUS: NOMINAL")

# --- MAIN INTERFACE ---

# 1. Header & Status
col_h1, col_h2 = st.columns([2, 1])
with col_h1:
    st.title("GREENLIGHT // COMMAND")
with col_h2:
    st.markdown("""
    <div style='text-align: right; padding-top: 20px;'>
        <div class='telemetry-text' style='justify-content: flex-end;'>
            <span class='status-dot'></span> AI ENGINE ONLINE
        </div>
        <div class='telemetry-text' style='justify-content: flex-end;'>
            LATENCY: 12ms
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# 2. Narrative Payload (Input)
st.markdown("<div class='telemetry-text'>🔹 DATA INGESTION PROTOCOL</div>", unsafe_allow_html=True)
st.markdown("### NARRATIVE PAYLOAD")

script_text = st.text_area(
    "SCRIPT_CONTENT",
    height=250,
    placeholder="> INITIATE UPLOAD OR PASTE TEXT SEQUENCE [500-3000 WORDS RECOMMENDED]",
    label_visibility="collapsed"
)

# Input Telemetry
col_stat_1, col_stat_2 = st.columns([1, 1])
word_count = len(script_text.split()) if script_text else 0

with col_stat_1:
    if 0 < word_count < 300:
        st.markdown(f"<div style='color: #f59e0b; font-family: monospace;'>⚠ LOW SIGNAL STRENGTH: {word_count} WORDS</div>", unsafe_allow_html=True)
    elif word_count > 0:
        st.markdown(f"<div style='color: #4f7dff; font-family: monospace;'>SIGNAL LOCKED: {word_count} WORDS</div>", unsafe_allow_html=True)

with col_stat_2:
    uploaded_file = st.file_uploader("UPLOAD_FILE", type=['txt', 'md'], label_visibility="collapsed")
    if uploaded_file:
        script_text = uploaded_file.read().decode("utf-8")
        st.markdown(f"<div style='text-align: right; color: #10b981; font-family: monospace;'>FILE BUFFER LOADED</div>", unsafe_allow_html=True)

# 3. Action Sequence
st.markdown("<br>", unsafe_allow_html=True)
col_act_1, col_act_2, col_act_3 = st.columns([1, 2, 1])

with col_act_2:
    evaluate_btn = st.button("RUN GREENLIGHT EVALUATION")
    st.markdown("<div style='text-align: center; color: #475569; font-size: 0.7rem; font-family: monospace; margin-top: 10px;'>ESTIMATED COMPUTE TIME: 3.2 SECONDS</div>", unsafe_allow_html=True)

# 4. Evaluation Sequence
if evaluate_btn and script_text:
    with st.spinner("PROCESSING NARRATIVE VECTORS..."):
        # Pipeline Execution
        features = extractor(script_text, selected_genre)
        comparison = comparator.compare(features, selected_genre)
        feedback = comparator.generate_feedback(comparison, features, selected_genre)
        
        # Get Genre Confidence
        prof = genre_data.get(selected_genre, {})
        genre_conf = prof.get('confidence_level', 'High')
        
        decision = engine.evaluate(feedback, features, genre_confidence=genre_conf)
        
        # Mapping
        d_label = decision['decision_label']
        conf_level = decision['confidence_level'].upper()
        explanation = decision['explanation_text']
        
        glow_class = "glow-red"
        if d_label == "GREENLIGHT": glow_class = "glow-green"
        elif d_label == "PILOT": glow_class = "glow-blue"
        elif d_label == "REWORK": glow_class = "glow-amber"
        
        # --- DECISION CARD ---
        st.markdown(f"""
        <div class="decision-container {glow_class}">
            <div class="telemetry-text" style="justify-content: center; margin-bottom: 20px;">EVALUATION COMPLETE</div>
            <div class="decision-main">{d_label}</div>
            <div style="font-family: 'JetBrains Mono'; color: #cbd5e1; font-size: 1.2rem; margin-bottom: 20px;">
                CONFIDENCE: <span style="color: white; font-weight: bold;">{conf_level}</span>
            </div>
            <div style="color: #94a3b8; font-size: 1.1rem; max-width: 800px; margin: 0 auto; line-height: 1.6;">
                {explanation}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # --- INSIGHT TRIAD ---
        c1, c2, c3 = st.columns(3)
        
        with c1:
            st.markdown(f"""
            <div class="insight-box">
                <div class="telemetry-text" style="color: #34d399;">✅ SIGNAL STRENGTHS</div>
                <ul style="list-style-type: none; padding: 0; color: #cbd5e1; font-size: 0.9rem;">
                    {''.join([f'<li style="margin-bottom: 8px;">+ {s}</li>' for s in feedback['strengths_vs_genre']] if feedback['strengths_vs_genre'] else '<li style="color: #64748b;">No distinctive peaks.</li>')}
                </ul>
            </div>
            """, unsafe_allow_html=True)
            
        with c2:
            st.markdown(f"""
            <div class="insight-box">
                <div class="telemetry-text" style="color: #f87171;">⚠️ RISK FACTORS</div>
                <ul style="list-style-type: none; padding: 0; color: #cbd5e1; font-size: 0.9rem;">
                     {''.join([f'<li style="margin-bottom: 8px;">! {w}</li>' for w in feedback['weaknesses_vs_genre']] + [f'<li style="margin-bottom: 8px;">? MISSING: {m}</li>' for m in feedback['missing_common_traits']] if (feedback['weaknesses_vs_genre'] or feedback['missing_common_traits']) else '<li style="color: #64748b;">nominal risk profile.</li>')}
                </ul>
            </div>
            """, unsafe_allow_html=True)
            
        with c3:
            rec_text = "INITIATE PILOT" if d_label == "GREENLIGHT" else "REQUEST REVISION" if d_label == "REWORK" else "ARCHIVE"
            st.markdown(f"""
            <div class="insight-box">
                <div class="telemetry-text" style="color: #60a5fa;">🚀 NEXT ACTION</div>
                <div style="font-size: 1.2rem; font-weight: 700; color: white; margin-bottom: 10px;">{rec_text}</div>
                <div style="color: #94a3b8; font-size: 0.9rem;">
                    {decision['improvement_suggestions'][0] if decision['improvement_suggestions'] else 'Proceed with standard protocols.'}
                </div>
            </div>
            """, unsafe_allow_html=True)

        # --- RAW DATA LINK ---
        with st.expander("VIEW RAW TELEMETRY"):
            st.json(features)

elif evaluate_btn and not script_text:
    st.error("❌ ERROR: NO NARRATIVE DATA DETECTED")
