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

# --- FUTURISTIC ANIME AI COMMAND CENTER CSS ---
st.markdown("""
<style>
    /* ═══ FONTS ═══ */
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600;800&family=JetBrains+Mono:wght@400;700&display=swap');

    /* ═══ 1. GLOBAL THEME ═══ */
    .stApp {
        background-color: #05070D;
        background-image:
            radial-gradient(circle at top, #0B1220, #05070D 70%),
            repeating-linear-gradient(0deg, transparent, transparent 59px, rgba(56,189,248,0.03) 59px, rgba(56,189,248,0.03) 60px),
            repeating-linear-gradient(90deg, transparent, transparent 59px, rgba(56,189,248,0.03) 59px, rgba(56,189,248,0.03) 60px);
        background-size: 100% 100%, 60px 60px, 60px 60px;
        color: #e2e8f0;
        font-family: 'Inter', sans-serif;
    }

    /* Vignette */
    .stApp::before {
        content: "";
        position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
        background: radial-gradient(ellipse at 50% 30%, transparent 30%, rgba(5,7,13,0.7) 100%);
        pointer-events: none; z-index: 0;
    }

    /* ═══ 2. NEON SPINE & SIDEBAR ═══ */
    [data-testid="stSidebar"] {
        border-right: 2px solid transparent;
        border-image: linear-gradient(180deg, #38BDF8, #7C3AED, #38BDF8) 1;
        box-shadow: 3px 0 25px rgba(56,189,248,0.08), 3px 0 60px rgba(124,58,237,0.05);
        background: linear-gradient(180deg, rgba(5,7,13,0.97) 0%, rgba(11,18,32,0.97) 100%);
        backdrop-filter: blur(15px);
        z-index: 1000001 !important;
    }
    .main .block-container { padding-top: 2.5rem; padding-left: 3.5rem; }

    /* ═══ 3. TYPOGRAPHY ═══ */
    h1, h2, h3 {
        font-family: 'Space Grotesk', sans-serif !important;
        font-weight: 700; letter-spacing: -0.5px; color: #f8fafc;
    }
    .telemetry-text {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem; color: #64748b;
        letter-spacing: 2px; text-transform: uppercase;
        margin-bottom: 6px; display: flex; align-items: center; gap: 8px;
        animation: fadeIn 0.4s ease-out;
    }
    @keyframes fadeIn { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:translateY(0); } }

    .status-dot {
        height: 7px; width: 7px; background: #10b981; border-radius: 50%;
        display: inline-block; animation: pulseGlow 3s infinite ease-in-out;
    }
    @keyframes pulseGlow {
        0%,100% { box-shadow: 0 0 4px #10b981, 0 0 10px rgba(16,185,129,0.3); }
        50% { box-shadow: 0 0 8px #10b981, 0 0 20px rgba(16,185,129,0.6); }
    }

    /* ═══ 4. NARRATIVE PAYLOAD INPUT ═══ */
    .stTextArea textarea {
        background: linear-gradient(180deg, rgba(11,18,32,0.9) 0%, rgba(5,7,13,0.98) 100%);
        border: 1px solid rgba(56,189,248,0.12);
        color: #94a3b8; font-family: 'Inter', sans-serif;
        font-size: 1rem; line-height: 1.7; border-radius: 6px;
        box-shadow: inset 0 2px 30px rgba(0,0,0,0.7), 0 0 0 1px rgba(56,189,248,0.05);
        transition: all 0.4s cubic-bezier(0.4,0,0.2,1); padding: 22px;
        caret-color: #38BDF8;
    }
    .stTextArea textarea:focus {
        border-color: rgba(56,189,248,0.5);
        box-shadow: 0 0 30px rgba(56,189,248,0.12), 0 0 60px rgba(124,58,237,0.06),
                    inset 0 2px 30px rgba(0,0,0,0.7), 0 0 0 1px rgba(56,189,248,0.2);
        color: #f1f5f9; outline: none;
        background: linear-gradient(180deg, rgba(11,18,32,0.95) 0%, rgba(5,7,13,1) 100%);
    }
    .stTextArea:focus-within::after {
        content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
        background: linear-gradient(90deg, transparent, #38BDF8, #7C3AED, transparent);
        animation: scanline 2.5s linear infinite;
    }
    @keyframes scanline { 0% { transform: translateX(-100%); } 100% { transform: translateX(100%); } }

    /* ═══ 5. COMMAND BUTTON ═══ */
    .stButton > button {
        background: linear-gradient(135deg, #0EA5E9 0%, #7C3AED 100%);
        color: white; border: 1px solid rgba(255,255,255,0.1);
        padding: 20px 40px; font-family: 'JetBrains Mono', monospace;
        font-size: 1.05rem; font-weight: 700; letter-spacing: 2.5px;
        border-radius: 6px; width: 100%; text-transform: uppercase;
        box-shadow: 0 0 25px rgba(124,58,237,0.25), 0 0 60px rgba(14,165,233,0.1);
        transition: all 0.2s cubic-bezier(0.4,0,0.2,1);
        position: relative; overflow: hidden;
    }
    .stButton > button::before {
        content: ''; position: absolute; top: 0; left: -100%; width: 60%; height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.15), transparent);
        transform: skewX(-20deg); transition: 0.6s;
    }
    .stButton > button:hover {
        transform: scale(1.03) translateY(-1px);
        box-shadow: 0 0 50px rgba(124,58,237,0.45), 0 0 80px rgba(14,165,233,0.2);
        background: linear-gradient(135deg, #0EA5E9 0%, #8B5CF6 100%);
    }
    .stButton > button:hover::before { left: 150%; }
    .stButton > button:active {
        transform: scale(0.97);
        box-shadow: 0 0 15px rgba(124,58,237,0.7), 0 0 40px rgba(14,165,233,0.3);
    }

    /* ═══ 6. AI ORB ═══ */
    @keyframes orbIdle {
        0%,100% { box-shadow: 0 0 15px rgba(56,189,248,0.15), 0 0 40px rgba(56,189,248,0.08), inset 0 0 15px rgba(56,189,248,0.1); }
        50% { box-shadow: 0 0 25px rgba(56,189,248,0.3), 0 0 60px rgba(56,189,248,0.15), inset 0 0 25px rgba(56,189,248,0.2); }
    }
    @keyframes orbAnalyzing {
        0%,100% { box-shadow: 0 0 20px rgba(34,211,238,0.2), 0 0 50px rgba(34,211,238,0.1), inset 0 0 20px rgba(34,211,238,0.15); transform: rotate(0deg); }
        50% { box-shadow: 0 0 40px rgba(34,211,238,0.5), 0 0 80px rgba(34,211,238,0.2), inset 0 0 35px rgba(34,211,238,0.35); transform: rotate(180deg); }
    }
    @keyframes orbGreen {
        0%,100% { box-shadow: 0 0 20px rgba(52,211,153,0.2), 0 0 50px rgba(52,211,153,0.1), inset 0 0 20px rgba(52,211,153,0.15); }
        50% { box-shadow: 0 0 40px rgba(52,211,153,0.45), 0 0 70px rgba(52,211,153,0.2), inset 0 0 30px rgba(52,211,153,0.3); }
    }
    @keyframes orbWarning {
        0%,100% { box-shadow: 0 0 20px rgba(245,158,11,0.2), inset 0 0 20px rgba(245,158,11,0.15); }
        50% { box-shadow: 0 0 45px rgba(245,158,11,0.5), inset 0 0 35px rgba(245,158,11,0.35); }
    }
    @keyframes orbCritical {
        0%,100% { box-shadow: 0 0 20px rgba(244,63,94,0.2), inset 0 0 20px rgba(244,63,94,0.15); }
        50% { box-shadow: 0 0 50px rgba(244,63,94,0.55), inset 0 0 40px rgba(244,63,94,0.4); }
    }
    .ai-orb-container {
        position: relative; width: 70px; height: 70px;
        display: flex; justify-content: center; align-items: center;
        margin-left: auto;
    }
    .ai-orb {
        width: 50px; height: 50px; border-radius: 50%;
        background: radial-gradient(circle at 35% 35%, rgba(56,189,248,0.08), transparent 60%);
        border: 1.5px solid rgba(56,189,248,0.2);
        transition: all 1.5s ease; position: relative;
    }
    .ai-orb::before {
        content: ''; position: absolute; inset: 4px; border-radius: 50%;
        border: 1px solid rgba(255,255,255,0.06);
    }
    .ai-orb::after {
        content: ''; position: absolute; inset: 10px; border-radius: 50%;
        border: 1px dashed rgba(56,189,248,0.15);
    }
    .orb-stable { animation: orbGreen 7s infinite ease-in-out; border-color: rgba(52,211,153,0.35); }
    .orb-analyzing { animation: orbAnalyzing 3s infinite ease-in-out; border-color: rgba(34,211,238,0.4); }
    .orb-warning { animation: orbWarning 5s infinite ease-in-out; border-color: rgba(245,158,11,0.4); }
    .orb-critical { animation: orbCritical 4s infinite ease-in-out; border-color: rgba(244,63,94,0.4); }
    .orb-idle { animation: orbIdle 8s infinite ease-in-out; border-color: rgba(56,189,248,0.25); }

    /* ═══ 7. DECISION & INSIGHT CARDS ═══ */
    @keyframes slideUpFade {
        from { opacity: 0; transform: translateY(30px) scale(0.98); }
        to { opacity: 1; transform: translateY(0) scale(1); }
    }
    @keyframes glowPulse {
        0%,100% { opacity: 0.6; } 50% { opacity: 1; }
    }
    .decision-container {
        background: rgba(20,25,40,0.6);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px; padding: 55px 40px; text-align: center;
        backdrop-filter: blur(12px); margin-top: 20px;
        animation: slideUpFade 0.7s cubic-bezier(0.16,1,0.3,1) forwards;
        box-shadow: 0 25px 60px rgba(0,0,0,0.6);
        position: relative; overflow: hidden;
    }
    .decision-container::before {
        content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
        animation: glowPulse 3s infinite;
    }
    .decision-main {
        font-family: 'Space Grotesk', sans-serif !important;
        font-size: 4rem; font-weight: 700; letter-spacing: -1px;
        line-height: 1; margin-bottom: 15px; text-transform: uppercase;
    }
    .glow-green {
        color: #34d399; text-shadow: 0 0 40px rgba(52,211,153,0.4), 0 0 80px rgba(52,211,153,0.15);
        border-top: none;
    }
    .glow-green::before { background: linear-gradient(90deg, transparent, #34d399, transparent); }
    .glow-blue {
        color: #60a5fa; text-shadow: 0 0 40px rgba(96,165,250,0.4), 0 0 80px rgba(96,165,250,0.15);
        border-top: none;
    }
    .glow-blue::before { background: linear-gradient(90deg, transparent, #60a5fa, transparent); }
    .glow-amber {
        color: #fbbf24; text-shadow: 0 0 40px rgba(251,191,36,0.4), 0 0 80px rgba(251,191,36,0.15);
        border-top: none;
    }
    .glow-amber::before { background: linear-gradient(90deg, transparent, #fbbf24, transparent); }
    .glow-red {
        color: #f43f5e; text-shadow: 0 0 40px rgba(244,63,94,0.4), 0 0 80px rgba(244,63,94,0.15);
        border-top: none;
    }
    .glow-red::before { background: linear-gradient(90deg, transparent, #f43f5e, transparent); }

    .insight-box {
        background: rgba(20,25,40,0.6);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255,255,255,0.08); border-radius: 16px;
        padding: 25px; height: 100%;
        transition: all 0.3s cubic-bezier(0.4,0,0.2,1);
        animation: slideUpFade 0.8s cubic-bezier(0.16,1,0.3,1) both;
    }
    .insight-box:hover {
        transform: translateY(-3px);
        background: rgba(20,25,40,0.8);
        border-color: rgba(56,189,248,0.2);
        box-shadow: 0 12px 35px rgba(0,0,0,0.4), 0 0 20px rgba(56,189,248,0.05);
    }
    div[data-testid="column"]:nth-child(1) .insight-box { animation-delay: 0.1s; }
    div[data-testid="column"]:nth-child(2) .insight-box { animation-delay: 0.2s; }
    div[data-testid="column"]:nth-child(3) .insight-box { animation-delay: 0.3s; }

    /* ═══ 8. FLOATING GEOMETRY (Light Shards) ═══ */
    @keyframes floatShard1 { 0%,100% { transform: translate(0,0) rotate(0deg); } 50% { transform: translate(30px,-20px) rotate(15deg); } }
    @keyframes floatShard2 { 0%,100% { transform: translate(0,0) rotate(0deg); } 50% { transform: translate(-25px,30px) rotate(-10deg); } }
    @keyframes floatShard3 { 0%,100% { transform: translate(0,0) rotate(0deg); } 50% { transform: translate(15px,25px) rotate(8deg); } }

    /* ═══ 9. AVATAR (HOLOGRAPHIC) ═══ */
    .avatar-container {
        position: fixed; bottom: 20px; right: 25px; z-index: 999;
        display: flex; align-items: flex-end; gap: 10px; pointer-events: none;
    }
    .avatar-bubble {
        background: rgba(20,25,40,0.6);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(56,189,248,0.25);
        border-radius: 14px 14px 2px 14px; padding: 12px 16px;
        max-width: 220px; font-family: 'Inter', sans-serif;
        font-size: 0.8rem; color: #94a3b8; line-height: 1.5;
        box-shadow: 0 8px 30px rgba(0,0,0,0.5), 0 0 20px rgba(56,189,248,0.08);
        animation: slideUpFade 0.5s ease-out;
    }
    .avatar-img-wrap {
        width: 120px; height: 120px; position: relative; flex-shrink: 0;
        animation: avatarFloat 6s ease-in-out infinite;
        perspective: 500px;
        cursor: pointer; pointer-events: auto;
    }
    /* Hologram ground glow */
    .avatar-img-wrap::before {
        content: '';
        position: absolute; bottom: -8px; left: 10%; right: 10%; height: 14px;
        background: radial-gradient(ellipse, rgba(56,189,248,0.4), rgba(124,58,237,0.15), transparent);
        border-radius: 50%;
        filter: blur(6px);
        animation: avatarFloat 6s ease-in-out infinite reverse;
    }
    /* Hologram scanline overlay */
    .avatar-img-wrap::after {
        content: '';
        position: absolute; inset: 0; z-index: 2;
        background: repeating-linear-gradient(
            0deg,
            transparent,
            transparent 2px,
            rgba(56,189,248,0.04) 2px,
            rgba(56,189,248,0.04) 4px
        );
        border-radius: 8px;
        pointer-events: none;
        animation: holoFlicker 4s ease-in-out infinite;
    }
    .avatar-img-wrap img {
        width: 100%; height: 100%;
        object-fit: contain;
        filter: drop-shadow(0 0 15px rgba(56,189,248,0.35)) drop-shadow(0 0 30px rgba(124,58,237,0.2)) drop-shadow(0 4px 15px rgba(0,0,0,0.4));
        transition: transform 0.4s ease, filter 0.4s ease;
        position: relative; z-index: 1;
    }
    .avatar-img-wrap:hover img {
        transform: rotateY(12deg) rotateX(-5deg) scale(1.08);
        filter: drop-shadow(0 0 25px rgba(56,189,248,0.5)) drop-shadow(0 0 45px rgba(124,58,237,0.3)) drop-shadow(0 8px 25px rgba(0,0,0,0.5));
    }
    @keyframes avatarFloat {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-10px); }
    }
    @keyframes holoFlicker {
        0%, 100% { opacity: 0.7; }
        25% { opacity: 0.9; }
        50% { opacity: 0.6; }
        75% { opacity: 1; }
    }

    /* ═══ 10. ANALYSIS STAGES ═══ */
    .analysis-stage {
        display: flex; align-items: center; gap: 14px;
        padding: 12px 20px; margin: 6px 0; border-radius: 8px;
        background: rgba(11,18,32,0.6); border: 1px solid rgba(56,189,248,0.08);
        font-family: 'JetBrains Mono', monospace; font-size: 0.82rem;
        animation: slideUpFade 0.4s ease-out both;
    }
    .analysis-stage .stage-dot {
        width: 8px; height: 8px; border-radius: 50%;
        background: #38BDF8; box-shadow: 0 0 8px #38BDF8;
        animation: pulseGlow 1.5s infinite;
    }
    .analysis-stage.done .stage-dot { background: #34d399; box-shadow: 0 0 8px #34d399; animation: none; }
    .analysis-stage.done { color: #34d399; border-color: rgba(52,211,153,0.15); }

    /* ═══ 11. VIDEO PREVIEW ═══ */
    .preview-container {
        border: 1px solid rgba(255,255,255,0.08); border-radius: 16px;
        padding: 20px; margin-top: 20px; text-align: center;
        background: rgba(20,25,40,0.6);
        backdrop-filter: blur(12px);
        box-shadow: 0 0 30px rgba(56,189,248,0.06), 0 10px 40px rgba(0,0,0,0.4);
    }

    /* ═══ 12. FEEDBACK BUTTONS ═══ */
    .fb-option {
        display: inline-block; padding: 10px 24px; margin: 6px;
        border: 1px solid rgba(56,189,248,0.2); border-radius: 8px;
        font-family: 'JetBrains Mono', monospace; font-size: 0.85rem;
        color: #94a3b8; cursor: pointer;
        transition: all 0.25s ease;
        background: rgba(11,18,32,0.6);
    }
    .fb-option:hover {
        border-color: #38BDF8; color: #38BDF8;
        box-shadow: 0 0 15px rgba(56,189,248,0.15);
        transform: translateY(-2px);
    }

    /* ═══ 13. REDUCE MOTION ═══ */
    .reduce-motion .ai-orb, .reduce-motion .ai-orb::after,
    .reduce-motion .avatar-figure .av-ring,
    .reduce-motion .avatar-figure .av-eye { animation: none !important; }
    .reduce-motion .decision-container,
    .reduce-motion .insight-box,
    .reduce-motion .analysis-stage,
    .reduce-motion .avatar-bubble { animation: none !important; }
    .reduce-motion .stTextArea:focus-within::after { animation: none !important; display: none; }
    .reduce-motion .stButton > button::before { display: none; }
    .reduce-motion .geo-shard { display: none !important; }
    .reduce-motion #pt-particles { display: none !important; }
    .reduce-motion #pt-energy { display: none !important; }
    .reduce-motion .avatar-img-wrap::after { animation: none !important; }
    .reduce-motion .avatar-img-wrap { animation: none !important; }

    /* ═══ 14. UTILITY ═══ */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header[data-testid="stHeader"] { background: transparent !important; }

    /* Streamlit metric override — 3D Neon Cards */
    [data-testid="stMetric"] {
        background: linear-gradient(145deg, rgba(11,18,32,0.9) 0%, rgba(15,23,42,0.95) 100%) !important;
        border: 1px solid rgba(56,189,248,0.2) !important;
        border-radius: 12px !important;
        padding: 20px 16px !important;
        box-shadow:
            0 4px 15px rgba(0,0,0,0.4),
            0 8px 30px rgba(0,0,0,0.3),
            inset 0 1px 0 rgba(56,189,248,0.1),
            0 0 20px rgba(56,189,248,0.05) !important;
        transform: perspective(800px) translateZ(0px);
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    [data-testid="stMetric"]::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 2px;
        background: linear-gradient(90deg, #38BDF8, #7C3AED, #22D3EE);
        opacity: 0.8;
    }
    [data-testid="stMetric"]:hover {
        transform: perspective(800px) translateZ(8px) translateY(-2px);
        box-shadow:
            0 8px 25px rgba(0,0,0,0.5),
            0 12px 40px rgba(0,0,0,0.3),
            inset 0 1px 0 rgba(56,189,248,0.15),
            0 0 30px rgba(56,189,248,0.1) !important;
        border-color: rgba(56,189,248,0.35) !important;
    }
    [data-testid="stMetricValue"] {
        font-family: 'Space Grotesk', 'JetBrains Mono', monospace !important;
        font-size: 2.2rem !important;
        font-weight: 700 !important;
        color: #f1f5f9 !important;
        text-shadow: 0 0 10px rgba(56,189,248,0.3);
    }
    [data-testid="stMetricLabel"] {
        color: #94a3b8 !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.75rem !important;
        letter-spacing: 1.5px !important;
        text-transform: uppercase !important;
    }

    /* ═══ 15. WIDGET LABEL VISIBILITY FIXES ═══ */
    /* All Streamlit widget labels */
    .stSelectbox label, .stMultiSelect label, .stSlider label,
    .stRadio label, .stCheckbox label, .stTextInput label,
    .stTextArea label, .stNumberInput label, .stDateInput label,
    .stFileUploader label, .stColorPicker label,
    [data-testid="stWidgetLabel"], label, .stFormSubmitButton button {
        color: #94a3b8 !important;
    }

    /* Selectbox / Multiselect - input field */
    .stSelectbox [data-baseweb="select"],
    .stMultiSelect [data-baseweb="select"],
    .stSelectbox [data-baseweb="select"] > div,
    .stMultiSelect [data-baseweb="select"] > div {
        background: rgba(11,18,32,0.9) !important;
        background-color: rgba(11,18,32,0.9) !important;
        border-color: rgba(56,189,248,0.15) !important;
        color: #e2e8f0 !important;
    }
    .stSelectbox [data-baseweb="select"] div,
    .stMultiSelect [data-baseweb="select"] div {
        color: #e2e8f0 !important;
    }

    /* Selectbox / Multiselect - dropdown list container */
    [data-baseweb="popover"],
    [data-baseweb="popover"] > div,
    [data-baseweb="popover"] [role="listbox"],
    [data-baseweb="menu"],
    ul[role="listbox"] {
        background: #0B1220 !important;
        background-color: #0B1220 !important;
        border: 1px solid rgba(56,189,248,0.12) !important;
    }
    /* Dropdown options */
    [data-baseweb="popover"] [role="option"],
    [data-baseweb="menu"] [role="option"],
    ul[role="listbox"] li,
    [data-baseweb="popover"] li {
        color: #e2e8f0 !important;
        background: #0B1220 !important;
        background-color: #0B1220 !important;
    }
    [data-baseweb="popover"] [role="option"]:hover,
    [data-baseweb="menu"] [role="option"]:hover,
    ul[role="listbox"] li:hover,
    [data-baseweb="popover"] li:hover,
    [data-baseweb="popover"] [role="option"][aria-selected="true"],
    ul[role="listbox"] li[aria-selected="true"] {
        background: rgba(56,189,248,0.15) !important;
        background-color: rgba(56,189,248,0.15) !important;
        color: #38BDF8 !important;
    }
    /* Force BaseWeb internal divs */
    [data-baseweb="popover"] div[class],
    [data-baseweb="menu"] div[class] {
        background-color: #0B1220 !important;
    }

    /* Slider */
    .stSlider [data-baseweb="slider"] div {
        color: #e2e8f0 !important;
    }
    .stSlider p {
        color: #94a3b8 !important;
    }

    /* File uploader dark theme */
    [data-testid="stFileUploader"] {
        color: #94a3b8 !important;
    }
    [data-testid="stFileUploader"] section {
        background: rgba(11,18,32,0.6) !important;
        border-color: rgba(56,189,248,0.15) !important;
        border-radius: 8px !important;
    }
    [data-testid="stFileUploader"] section > div {
        color: #94a3b8 !important;
    }
    [data-testid="stFileUploader"] small {
        color: #64748b !important;
    }
    [data-testid="stFileUploaderDropzone"] {
        background: rgba(11,18,32,0.5) !important;
        border-color: rgba(56,189,248,0.12) !important;
        color: #94a3b8 !important;
    }
    [data-testid="stFileUploaderDropzone"] div,
    [data-testid="stFileUploaderDropzone"] span,
    [data-testid="stFileUploaderDropzone"] p,
    [data-testid="stFileUploaderDropzone"] small {
        color: #94a3b8 !important;
    }
    [data-testid="stFileUploaderDropzone"] svg {
        fill: #64748b !important;
    }

    /* Text area placeholder visibility */
    .stTextArea textarea::placeholder {
        color: #64748b !important;
        opacity: 1 !important;
    }

    /* Radio / toggle labels */
    .stRadio > div > label, .stRadio div[role="radiogroup"] label {
        color: #cbd5e1 !important;
    }
    [data-testid="stToggle"] label span {
        color: #94a3b8 !important;
    }

    /* Text input */
    .stTextInput input {
        background: rgba(11,18,32,0.7) !important;
        border-color: rgba(56,189,248,0.12) !important;
        color: #e2e8f0 !important;
    }
    .stTextInput input::placeholder {
        color: #64748b !important;
    }

    /* Expander */
    [data-testid="stExpander"] summary {
        color: #94a3b8 !important;
    }
    [data-testid="stExpander"] {
        border-color: rgba(56,189,248,0.1) !important;
    }

    /* Caption text */
    .stCaption, [data-testid="stCaptionContainer"] {
        color: #64748b !important;
    }

    /* Form submit button */
    .stFormSubmitButton button {
        background: linear-gradient(135deg, rgba(14,165,233,0.7) 0%, rgba(124,58,237,0.7) 100%) !important;
        color: white !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
    }

    /* Info/Warning/Error boxes */
    [data-testid="stAlert"] {
        background: rgba(11,18,32,0.6) !important;
        color: #e2e8f0 !important;
    }

    /* Dividers */
    hr {
        border-color: rgba(56,189,248,0.08) !important;
    }
</style>
""", unsafe_allow_html=True)

# --- ANIMATED BACKGROUND LAYERS ---
st.markdown("""
<!-- Layer 2: Anime Energy Aura -->
<canvas id="pt-energy" style="position:fixed;top:0;left:0;width:100vw;height:100vh;pointer-events:none;z-index:0;"></canvas>
<script>
(function(){
    const c=document.getElementById('pt-energy');
    if(!c)return;
    const ctx=c.getContext('2d');
    let W,H;
    function resize(){W=c.width=window.innerWidth;H=c.height=window.innerHeight;}
    resize(); window.addEventListener('resize',resize);
    const blobs=[];
    for(let i=0;i<6;i++){
        blobs.push({
            x:Math.random()*W, y:Math.random()*H,
            r:120+Math.random()*180,
            dx:(Math.random()-0.5)*0.15, dy:(Math.random()-0.5)*0.1,
            hue:Math.random()>0.5?'56,189,248':'124,58,237',
            phase:Math.random()*Math.PI*2
        });
    }
    let t=0;
    function draw(){
        ctx.clearRect(0,0,W,H);
        t+=0.003;
        for(const b of blobs){
            b.x+=b.dx; b.y+=b.dy;
            if(b.x<-b.r)b.x=W+b.r; if(b.x>W+b.r)b.x=-b.r;
            if(b.y<-b.r)b.y=H+b.r; if(b.y>H+b.r)b.y=-b.r;
            const osc=0.10+0.06*Math.sin(t+b.phase);
            const g=ctx.createRadialGradient(b.x,b.y,0,b.x,b.y,b.r);
            g.addColorStop(0,`rgba(${b.hue},${osc})`);
            g.addColorStop(1,'rgba(0,0,0,0)');
            ctx.fillStyle=g;
            ctx.fillRect(b.x-b.r,b.y-b.r,b.r*2,b.r*2);
        }
        requestAnimationFrame(draw);
    }
    draw();
})();
</script>

<!-- Layer 3: Floating Geometry (Light Shards + Triangles) -->
<div style="position:fixed;top:0;left:0;width:100vw;height:100vh;pointer-events:none;z-index:0;overflow:hidden;">
    <div class="geo-shard" style="position:absolute;top:15%;left:20%;width:60px;height:2px;background:linear-gradient(90deg,transparent,rgba(56,189,248,0.45),transparent);transform:rotate(25deg);animation:floatShard1 12s infinite ease-in-out;"></div>
    <div class="geo-shard" style="position:absolute;top:40%;right:15%;width:80px;height:2px;background:linear-gradient(90deg,transparent,rgba(124,58,237,0.35),transparent);transform:rotate(-15deg);animation:floatShard2 15s infinite ease-in-out;"></div>
    <div class="geo-shard" style="position:absolute;bottom:30%;left:35%;width:50px;height:2px;background:linear-gradient(90deg,transparent,rgba(34,211,238,0.3),transparent);transform:rotate(40deg);animation:floatShard3 18s infinite ease-in-out;"></div>
    <div class="geo-shard" style="position:absolute;top:60%;left:10%;width:0;height:0;border-left:12px solid transparent;border-right:12px solid transparent;border-bottom:20px solid rgba(56,189,248,0.12);animation:floatShard2 20s infinite ease-in-out;"></div>
    <div class="geo-shard" style="position:absolute;top:25%;right:25%;width:0;height:0;border-left:8px solid transparent;border-right:8px solid transparent;border-bottom:14px solid rgba(124,58,237,0.12);animation:floatShard1 16s infinite ease-in-out;"></div>
    <div class="geo-shard" style="position:absolute;bottom:20%;right:35%;width:40px;height:2px;background:linear-gradient(90deg,transparent,rgba(56,189,248,0.25),transparent);transform:rotate(-30deg);animation:floatShard3 14s infinite ease-in-out;"></div>
    <!-- Extra triangles -->
    <div class="geo-shard" style="position:absolute;top:10%;right:10%;width:0;height:0;border-left:10px solid transparent;border-right:10px solid transparent;border-bottom:16px solid rgba(34,211,238,0.1);animation:floatShard2 22s infinite ease-in-out;"></div>
    <div class="geo-shard" style="position:absolute;bottom:15%;left:15%;width:0;height:0;border-left:14px solid transparent;border-right:14px solid transparent;border-bottom:22px solid rgba(56,189,248,0.1);animation:floatShard1 25s infinite ease-in-out;"></div>
    <!-- Extra energy streaks -->
    <div class="geo-shard" style="position:absolute;top:70%;left:45%;width:90px;height:2px;background:linear-gradient(90deg,transparent,rgba(124,58,237,0.3),transparent);transform:rotate(18deg);animation:floatShard3 20s infinite ease-in-out;"></div>
    <div class="geo-shard" style="position:absolute;top:5%;left:55%;width:70px;height:2px;background:linear-gradient(90deg,transparent,rgba(34,211,238,0.25),transparent);transform:rotate(-12deg);animation:floatShard1 18s infinite ease-in-out;"></div>
</div>

<!-- Layer 4: Particle System (Enhanced) -->
<canvas id="pt-particles" style="position:fixed;top:0;left:0;width:100vw;height:100vh;pointer-events:none;z-index:0;"></canvas>
<script>
(function(){
    const c=document.getElementById('pt-particles');
    if(!c)return;
    const ctx=c.getContext('2d');
    let W,H;
    function resize(){W=c.width=window.innerWidth;H=c.height=window.innerHeight;}
    resize(); window.addEventListener('resize',resize);
    const N=120, ps=[];
    const hues=[
        [56,189,248],  // electric blue
        [124,58,237],  // violet
        [34,211,238]   // cyan
    ];
    for(let i=0;i<N;i++){
        const h=hues[Math.floor(Math.random()*hues.length)];
        ps.push({
            x:Math.random()*W, y:Math.random()*H,
            r:Math.random()*2.5+0.4,
            dx:(Math.random()-0.5)*0.25, dy:(Math.random()-0.5)*0.18,
            o:Math.random()*0.6+0.15,
            od:(Math.random()-0.5)*0.006,
            rgb:h
        });
    }
    function draw(){
        ctx.clearRect(0,0,W,H);
        ctx.shadowBlur=0; ctx.shadowColor='transparent';
        // Connection lines
        for(let i=0;i<N;i++){
            for(let j=i+1;j<N;j++){
                const dx=ps[i].x-ps[j].x, dy=ps[i].y-ps[j].y;
                const dist=Math.sqrt(dx*dx+dy*dy);
                if(dist<100){
                    const a=0.15*(1-dist/100);
                    ctx.strokeStyle=`rgba(56,189,248,${a})`;
                    ctx.lineWidth=0.5;
                    ctx.beginPath();
                    ctx.moveTo(ps[i].x,ps[i].y);
                    ctx.lineTo(ps[j].x,ps[j].y);
                    ctx.stroke();
                }
            }
        }
        // Particles
        for(const p of ps){
            p.x+=p.dx; p.y+=p.dy; p.o+=p.od;
            if(p.o>0.75||p.o<0.1)p.od*=-1;
            if(p.x<0)p.x=W; if(p.x>W)p.x=0;
            if(p.y<0)p.y=H; if(p.y>H)p.y=0;
            ctx.beginPath(); ctx.arc(p.x,p.y,p.r,0,Math.PI*2);
            const col=`rgba(${p.rgb[0]},${p.rgb[1]},${p.rgb[2]},${p.o})`;
            ctx.fillStyle=col;
            ctx.shadowBlur=15; ctx.shadowColor=col;
            ctx.fill();
        }
        requestAnimationFrame(draw);
    }
    draw();
})();
</script>
""", unsafe_allow_html=True)

# --- AVATAR STATE ---
if 'avatar_state' not in st.session_state:
    st.session_state.avatar_state = 'idle'

AVATAR_MESSAGES = {
    'idle': "Ahoy! I'm Pocket Toons, your help assistant! Paste your script and let's set sail!",
    'waiting_for_script': 'Standing by for narrative payload, Captain!',
    'analyzing': 'Scanning emotional signals across the seven seas...',
    'decision_ready': "Analysis complete! Here's my recommendation, matey!",
    'preview_generation': 'Would you like me to generate a concept preview for ye?',
    'feedback': 'Did the preview match yer creative vision?'
}

def render_avatar(state='idle'):
    import base64, os
    msg = AVATAR_MESSAGES.get(state, AVATAR_MESSAGES['idle'])
    avatar_path = os.path.join(os.path.dirname(__file__), 'assets', 'avatar.png')
    try:
        with open(avatar_path, 'rb') as f:
            b64 = base64.b64encode(f.read()).decode()
        img_src = f'data:image/png;base64,{b64}'
    except:
        img_src = ''
    
    st.markdown(f"""
    <div class="avatar-container">
        <div class="avatar-bubble">{msg}</div>
        <div class="avatar-img-wrap">
            <img src="{img_src}" alt="AI Guide" />
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- REDUCE MOTION TOGGLE SUPPORT ---
if 'reduce_motion' not in st.session_state:
    st.session_state.reduce_motion = False

if st.session_state.reduce_motion:
    st.markdown("""<script>
    document.querySelector('.stApp').classList.add('reduce-motion');
    </script>""", unsafe_allow_html=True)


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
    st.markdown("""
    <div style='text-align:center; margin-bottom:8px;'>
        <div style='font-family:Space Grotesk,sans-serif; font-size:1.3rem; font-weight:700; color:#f8fafc; letter-spacing:2px;'>« POCKET TOONS »</div>
        <div style='font-family:JetBrains Mono,monospace; font-size:0.65rem; color:#475569; letter-spacing:3px; margin-top:4px;'>AI GREENLIGHT ENGINE v3.0</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    st.markdown("<div class='telemetry-text'>⬡ PARAMETER SETTINGS</div>", unsafe_allow_html=True)
    
    selected_genre_display = st.selectbox("Primary Genre Model", genres)
    selected_genre = selected_genre_display.lower() if selected_genre_display else "unknown"
    
    # Telemetry Panel
    if selected_genre in genre_data:
        prof = genre_data[selected_genre]
        count = prof.get('title_count', 0)
        conf = prof.get('confidence_level', 'Unknown')
        
        st.markdown(f"""
        <div style='background:linear-gradient(180deg,rgba(11,18,32,0.8),rgba(5,7,13,0.9)); padding:16px; border-radius:8px; border:1px solid rgba(56,189,248,0.1); margin-top:10px;'>
            <div class='telemetry-text'>⬡ MODEL TELEMETRY</div>
            <div style='font-family:JetBrains Mono,monospace; font-size:0.82rem; color:#94a3b8; line-height:2;'>
                TRAINING SET <span style='color:#38BDF8; font-weight:700;'>{count}</span> TITLES<br>
                CONFIDENCE <span style='color:#7C3AED; font-weight:700;'>{conf}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Global System Stats
    total_titles = sum(d.get('title_count', 0) for d in genre_data.values())
    
    try:
        df_eval = pd.read_csv("data/processed/script_evaluation_history.csv")
        total_scripts = len(df_eval)
    except:
        total_scripts = 0
        
    st.markdown(f"""
    <div style='margin-top:18px; padding-top:18px; border-top:1px solid rgba(56,189,248,0.08);'>
        <div class='telemetry-text'>⬡ SYSTEM CAPACITY</div>
        <div style='font-family:JetBrains Mono,monospace; font-size:0.82rem; color:#64748b; line-height:2;'>
            INDEXED TITLES <span style='color:#e0e0e0; font-weight:600;'>{total_titles}</span><br>
            EVALUATIONS RUN <span style='color:#e0e0e0; font-weight:600;'>{total_scripts}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    # Reduce Motion Toggle
    st.session_state.reduce_motion = st.toggle("⚡ Reduce Motion", value=st.session_state.reduce_motion)
    
    st.markdown("""<div style='text-align:center; margin-top:12px;'>
        <div class='telemetry-text' style='justify-content:center;'><span class='status-dot'></span> SYSTEM NOMINAL</div>
    </div>""", unsafe_allow_html=True)

# --- MAIN INTERFACE ---

# 1. Header & Status
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.markdown("""<div style='margin-bottom:-10px;'>
        <div class='telemetry-text' style='margin-bottom:8px;'>⬡ NARRATIVE INTELLIGENCE ENGINE</div>
    </div>""", unsafe_allow_html=True)
    st.title("GREENLIGHT // COMMAND")
with col_h2:
    orb_class = "orb-idle" if 'evaluating' not in st.session_state else st.session_state.get('orb_class', 'orb-idle')
    
    st.markdown(f"""
    <div style='display:flex; flex-direction:column; align-items:flex-end; gap:8px; padding-top:10px;'>
        <div class='ai-orb-container'>
            <div class='ai-orb {orb_class}'></div>
        </div>
        <div class='telemetry-text' style='justify-content:flex-end;'>
            <span class='status-dot'></span> AI NEURAL LINK ACTIVE
        </div>
        <div class='telemetry-text' style='justify-content:flex-end; color:#38BDF8;'>
            LATENCY: 12ms
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<hr style='border-color:rgba(56,189,248,0.08); margin:10px 0 20px;'>", unsafe_allow_html=True)

# 2. Narrative Payload (Input)
st.markdown("<div class='telemetry-text'>⬡ DATA INGESTION PROTOCOL</div>", unsafe_allow_html=True)
st.markdown("### NARRATIVE PAYLOAD")

if 'script_input' not in st.session_state:
    st.session_state.script_input = ""

script_text = st.text_area(
    "SCRIPT_CONTENT",
    height=250,
    placeholder="▶ INITIATE UPLOAD OR PASTE TEXT SEQUENCE [500-3000 WORDS RECOMMENDED]",
    label_visibility="collapsed",
    key="script_area"
)

# Input Telemetry
col_stat_1, col_stat_2 = st.columns([1, 1])
word_count = len(script_text.split()) if script_text else 0

with col_stat_1:
    if 0 < word_count < 300:
        st.markdown(f"<div style='color:#f59e0b; font-family:JetBrains Mono,monospace; font-size:0.82rem;'>⚠ LOW SIGNAL: {word_count} WORDS</div>", unsafe_allow_html=True)
    elif word_count > 0:
        st.markdown(f"<div style='color:#38BDF8; font-family:JetBrains Mono,monospace; font-size:0.82rem;'>⬡ SIGNAL LOCKED: {word_count} WORDS</div>", unsafe_allow_html=True)
        if st.session_state.avatar_state == 'idle':
            st.session_state.avatar_state = 'waiting_for_script'

with col_stat_2:
    uploaded_file = st.file_uploader("UPLOAD_FILE", type=['txt', 'md'], label_visibility="collapsed")
    if uploaded_file:
        script_text = uploaded_file.read().decode("utf-8")
        st.markdown("<div style='text-align:right; color:#10b981; font-family:JetBrains Mono,monospace; font-size:0.82rem;'>✓ FILE BUFFER LOADED</div>", unsafe_allow_html=True)

# 3. Action Sequence
st.markdown("<br>", unsafe_allow_html=True)
col_act_1, col_act_2, col_act_3 = st.columns([1, 2, 1])

with col_act_2:
    evaluate_btn = st.button("EXECUTE GREENLIGHT ANALYSIS")
    st.markdown("<div style='text-align:center; color:#475569; font-size:0.7rem; font-family:JetBrains Mono,monospace; margin-top:12px; letter-spacing:1px;'>NEURAL EVALUATION • MAY TAKE 15-30 SECONDS</div>", unsafe_allow_html=True)

# 4. Evaluation Sequence
if evaluate_btn and script_text:
    st.session_state.evaluation_triggered = True
    st.session_state.evaluating = True
    st.session_state.orb_class = "orb-analyzing"
    st.session_state.avatar_state = 'analyzing'
    st.session_state.eval_data = None
    if 'last_preview_path' in st.session_state:
        del st.session_state['last_preview_path']

if st.session_state.get('evaluation_triggered', False) and script_text:
    
    if st.session_state.get('eval_data') is None:
        import time, uuid, os, importlib
        import ml_scoring_pipeline_v2 as ml_scoring_pipeline
        importlib.reload(ml_scoring_pipeline)
        from ml_scoring_pipeline_v2 import score_new_script, update_index_after_evaluation

        with st.status("⚡ **EXECUTING GREENLIGHT ANALYSIS...**", expanded=True) as status:
            st.write("🔍 Scanning narrative signals...")
            
            tmp_name = f"temp_script_{uuid.uuid4().hex[:8]}.txt"
            with open(tmp_name, "w", encoding="utf-8") as f:
                f.write(script_text)
            
            st.write("🧠 Analyzing emotional intensity & genre intelligence...")
            
            result = score_new_script(tmp_name)
            
            st.write("📊 Synthesizing greenlight decision...")
            
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
        
            print(f"DEBUG IN STREAMLIT: result = {result}")
        
            if result:
                st.write("✅ Pipeline complete — mapping results...")
                
                # Map ML output to the legacy eval_data dictionary structure 
                # so the rest of the UI (Insight Triad, Feedback) doesn't break
                
                # Re-run legacy extractor briefly just for the raw JSON display below
                features_raw = extractor(script_text, selected_genre)
                print(f"DEBUG IN STREAMLIT: features_raw = {features_raw}")
                
                # Gemini Evaluation Feedback
                evaluation = result.get("evaluation", {})
                final_node = evaluation.get("final", {})
                dims_node = evaluation.get("dimension_scores", {})
                
                features = features_raw
                feedback = {
                    "strengths_vs_genre": [final_node.get("top_strength", "")] if final_node.get("top_strength") else evaluation.get("strengths", []),
                    "weaknesses_vs_genre": [final_node.get("critical_fix", "")] if final_node.get("critical_fix") else evaluation.get("weaknesses", []),
                    "missing_common_traits": []
                }
                decision = {
                    "decision_label": result.get("decision", "REWORK"),
                    "confidence_level": "High" if result.get("greenlight_score", 0) > 78 else "Medium" if result.get("greenlight_score", 0) > 60 else "Low",
                    "explanation_text": final_node.get("mobile_fit", evaluation.get("one_line_verdict", "N/A")),
                    "improvement_suggestions": [final_node.get("critical_fix", "")] if final_node.get("critical_fix") else evaluation.get("weaknesses", []),
                    "quality_bands": {
                        "Emotion": "HIGH" if dims_node.get("emotional_spike", {}).get("score", evaluation.get("emotional_depth", 0)) > 7 else "MEDIUM",
                        "Addiction": "HIGH" if dims_node.get("binge_pull", {}).get("score", evaluation.get("hook_strength", 0)) > 7 else "MEDIUM",
                        "Risk": "LOW" if result.get("decision", "") == "GREENLIGHT" else "HIGH"
                    },
                    "failed_gates": []
                }
                
                st.session_state.eval_data = {
                    'features': features,
                    'feedback': feedback,
                    'decision': decision,
                    'similarity_data': result.get('similarity_data', {}),
                    'blend_breakdown': result.get('blend_breakdown', {}),
                    'intrinsic_features': result.get('evaluation', {}).get('intrinsic_features', {}),
                    'gemini_scores': {k: v.get('score', 0) for k, v in result.get('evaluation', {}).get('dimension_scores', {}).items()},
                    'script_text': script_text,
                    'greenlight_score': result.get('greenlight_score', 0)
                }
                
                # Automatically add pseudo-label to index
                try:
                    update_index_after_evaluation(
                        script_text, 
                        result.get('evaluation', {}).get('title', f"Uploaded Script {uuid.uuid4().hex[:4]}"), 
                        st.session_state.eval_data['intrinsic_features'], 
                        st.session_state.eval_data['gemini_scores'], 
                        result['greenlight_score'], 
                        result['decision']
                    )
                except Exception as e:
                    print(f"Failed to auto-index script: {e}")
                
                status.update(label="✅ **ANALYSIS COMPLETE**", state="complete", expanded=False)
            else:
                status.update(label="❌ **ANALYSIS FAILED**", state="error", expanded=False)
                st.error("Failed to generate ML scoring predictions.")
                st.session_state.eval_data = None

    # Retrieve from state
    eval_data = st.session_state.get('eval_data')
    if eval_data is None:
        st.stop()
        
    features = eval_data['features']
    feedback = eval_data['feedback']
    decision = eval_data['decision']
    
    # Mapping
    d_label = decision['decision_label']
    conf_level = decision['confidence_level'].upper()
    explanation = decision['explanation_text']
    
    glow_class = "glow-red"
    new_orb_class = "orb-critical"
        
    if d_label == "GREENLIGHT": 
        glow_class = "glow-green"
        new_orb_class = "orb-stable"
    elif d_label == "PILOT": 
        glow_class = "glow-blue"
        new_orb_class = "orb-analyzing"
    elif d_label == "REWORK": 
        glow_class = "glow-amber"
        new_orb_class = "orb-warning"
        
    st.session_state.orb_class = new_orb_class
    st.session_state.avatar_state = 'decision_ready'
    
    # --- DECISION CARD ---
    st.markdown(f"""
    <div class="decision-container {glow_class}">
        <div class="telemetry-text" style="justify-content:center; margin-bottom:20px;">⬡ EVALUATION COMPLETE</div>
        <div class="decision-main">{d_label}</div>
        <div style="font-family:'JetBrains Mono',monospace; color:#cbd5e1; font-size:1.1rem; margin-bottom:20px; letter-spacing:1px;">
            CONFIDENCE: <span style="color:white; font-weight:700;">{conf_level}</span>
            &nbsp;•&nbsp;
            SCORE: <span style="color:white; font-weight:700;">{eval_data.get('greenlight_score', 0):.0f}</span>
        </div>
        <div style="color:#94a3b8; font-size:1.05rem; max-width:800px; margin:0 auto; line-height:1.7;">
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
        next_action_map = {
            "GREENLIGHT": "COMMISSION IMMEDIATELY",
            "PILOT": "PILOT 5 EPISODES",
            "DEFER": "REQUEST STRUCTURAL REWORK",
            "REWORK": "RETURN TO WRITER",
        }
        rec_text = next_action_map.get(d_label, "REVIEW REQUIRED")
        st.markdown(f"""
        <div class="insight-box">
            <div class="telemetry-text" style="color: #60a5fa;">🚀 NEXT ACTION</div>
            <div style="font-size: 1.2rem; font-weight: 700; color: white; margin-bottom: 10px;">{rec_text}</div>
            <div style="color: #94a3b8; font-size: 0.9rem;">
                {decision['improvement_suggestions'][0] if decision['improvement_suggestions'] else 'Proceed with standard protocols.'}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # --- SIMILARITY PANEL & SCORE BREAKDOWN ---
    st.markdown("<br><hr style='border-color:rgba(56,189,248,0.08);'>", unsafe_allow_html=True)
    st.markdown("<div class='telemetry-text'>⬡ HYBRID SIMILARITY ENGINE</div>", unsafe_allow_html=True)
    
    sim_data = eval_data.get('similarity_data', {})
    blend = eval_data.get('blend_breakdown', {})
    
    if sim_data.get('confidence') == 'LOW':
        st.warning("⚠️ Low Confidence — similar scripts had mixed outcomes. Human review recommended.")
        
    st.markdown("#### Score Breakdown")
    b1, b2, b3 = st.columns(3)
    with b1: st.metric("Similarity Contribution (50%)", f"+{blend.get('similarity_contribution', 0)}")
    with b2: st.metric("Gemini Contribution (35%)", f"+{blend.get('gemini_contribution', 0)}")
    with b3: st.metric("ML Calibration (15%)", f"+{blend.get('ml_contribution', 0)}")
    
    st.markdown("#### Top 3 Similar Scripts")
    matches = sim_data.get('matches', [])[:3]
    if matches:
        for m in matches:
            color = '#34d399' if m['decision'] == 'GREENLIGHT' else '#60a5fa' if m['decision'] == 'PILOT' else '#f59e0b' if m['decision'] == 'DEFER' else '#ef4444'
            st.markdown(f'''
            <div style="background: rgba(15, 23, 42, 0.4); padding: 15px; border-radius: 8px; margin-bottom: 10px; border-left: 4px solid {color};">
                <span style="font-weight: bold; color: white;">{m['title']}</span> <span style="color: #94a3b8;">({m['decision']})</span>
                <br>
                <span style="font-size: 0.8rem; color: #cbd5e1;">Hybrid Sim: {m['hybrid_similarity']*100:.1f}% | Source: {m['label_source']}</span>
            </div>
            ''', unsafe_allow_html=True)
    else:
        st.info("Cold Start: No similar scripts in memory index yet.")

    # --- RAW DATA LINK ---
    with st.expander("VIEW RAW TELEMETRY"):
        st.json(features)
        
    # --- HUMAN in the LOOP (HITL) ---
    st.markdown("<br><hr style='border-color:rgba(56,189,248,0.08);'>", unsafe_allow_html=True)
    st.markdown("<div class='telemetry-text'>⬡ HUMAN-IN-THE-LOOP ALIGNMENT</div>", unsafe_allow_html=True)
    
    bands = decision.get('quality_bands', {})
    failed_gates = decision.get('failed_gates', [])
    
    with st.container():
        st.markdown("""
        <div style="background: rgba(15, 23, 42, 0.4); border: 1px solid rgba(56, 189, 248, 0.2); padding: 25px; border-radius: 8px;">
            <h4 style="color: #f1f5f9; font-family: 'JetBrains Mono'; margin-top: 0;">OVERRIDE & CALIBRATE ENGINE</h4>
        """, unsafe_allow_html=True)
        
        st.caption("Review internal bands and record final human decision to calibrate future memory lookups.")
        
        cb1, cb2, cb3 = st.columns(3)
        with cb1: st.metric("Emotion Band", bands.get('Emotion', 'N/A'))
        with cb2: st.metric("Addiction Band", bands.get('Addiction', 'N/A'))
        with cb3: st.metric("Risk Band", bands.get('Risk', 'N/A'))
        
        if failed_gates:
            st.error(f"HARD GATES FAILED: {', '.join(failed_gates)}")
            
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Try to get previous submission status
        if 'feedback_submitted' not in st.session_state:
            st.session_state.feedback_submitted = False
            
        with st.form("hitl_form"):
            choices = ["GREENLIGHT", "PILOT", "DEFER", "REWORK"]
            default_idx = choices.index(d_label) if d_label in choices else 2
            
            human_decision = st.radio("Final Human Decision:", choices, index=default_idx, horizontal=True)
            human_notes = st.text_input("Disagreement Notes (Optional):", placeholder="Why did the AI score this incorrectly?")
            
            submit_fb = st.form_submit_button("SUBMIT TO MEMORY")
            
            if submit_fb:
                try:
                    from models.feedback_memory import FeedbackMemory
                    import uuid
                    tmp_id = f"script_{str(uuid.uuid4())[:6]}"
                    fm = FeedbackMemory()
                    fm.record_feedback(
                        script_id=tmp_id,
                        genre=selected_genre,
                        ai_decision=d_label,
                        human_decision=human_decision,
                        failed_gates=failed_gates,
                        emotion_band=bands.get('Emotion', 'N/A'),
                        addiction_band=bands.get('Addiction', 'N/A'),
                        risk_band=bands.get('Risk', 'N/A'),
                        notes=human_notes
                    )
                    # Also save to ML training data for model retraining
                    import json
                    training_file = Path("data/training_feedback.jsonl")
                    training_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    human_score_map = {"GREENLIGHT": 85.0, "PILOT": 70.0, "DEFER": 50.0, "REWORK": 25.0}
                    h_score = human_score_map.get(human_decision, 50.0)
                    
                    training_entry = {
                        "script_id": tmp_id,
                        "title": f"HITL Override {tmp_id}",
                        "ai_score": eval_data.get('greenlight_score', 50.0),
                        "human_score": h_score,
                        "human_decision": human_decision,
                        "features": eval_data.get('intrinsic_features', {}),
                        "gemini_scores": eval_data.get('gemini_scores', {}),
                        "label_source": "hitl_verified",
                        "label_confidence": 1.0,
                        "timestamp": datetime.now().isoformat()
                    }
                    with open(training_file, "a", encoding="utf-8") as tf:
                        tf.write(json.dumps(training_entry, default=str) + "\n")
                        
                    from models.embeddings_pipeline import add_to_index, embed_script
                    
                    # Ensure embedding and add directly to memory index
                    try:
                        add_to_index({
                            "script_id": tmp_id,
                            "title": f"HITL Override {tmp_id}",
                            "embedding": embed_script(eval_data.get('script_text', '')),
                            "intrinsic_features": eval_data.get('intrinsic_features', {}),
                            "gemini_scores": eval_data.get('gemini_scores', {}),
                            "greenlight_score": h_score,
                            "decision": human_decision,
                            "label_source": "hitl_verified",
                            "label_confidence": 1.0
                        })
                    except Exception as e:
                        st.error(f"Memory update failed: {e}")
                    
                    st.session_state.feedback_submitted = True
                except Exception as e:
                    st.error(f"Failed to record memory: {e}")
                    
        if st.session_state.feedback_submitted:
            st.success("Human alignment recorded. Feedback saved to ML training pipeline for future model improvements.")
            st.session_state.feedback_submitted = False # reset for next click

        st.markdown("</div>", unsafe_allow_html=True)
        
    # --- PHASE 4: CONCEPT PREVIEW ---
    st.markdown("<br><hr style='border-color:rgba(56,189,248,0.08);'>", unsafe_allow_html=True)
    st.markdown("<div class='telemetry-text'>⬡ CONCEPT PREVIEW</div>", unsafe_allow_html=True)
    
    st.caption("Generate a fully rendered 8-second animated video trailer based on the script's emotional intensity.")
    st.session_state.avatar_state = 'preview_generation'
    
    preview_btn = st.button("🎬 GENERATE CONCEPT PREVIEW")
    
    if preview_btn:
        with st.spinner("Rendering continuous animation..."):
            try:
                from models.preview_generator import generate_preview_brief
                from models.video_renderer import render_preview_video
                import uuid
                import os
                
                script_id = f"script_{str(uuid.uuid4())[:8]}"
                brief = generate_preview_brief(features, selected_genre, bands.get('Emotion', 'MEDIUM'))
                
                output_file = f"temp_preview_{script_id}.mp4"
                video_path = render_preview_video(brief, output_file)
                
                if video_path and os.path.exists(video_path):
                    st.session_state.last_preview_path = video_path
                    st.session_state.last_script_id = script_id
                    st.session_state.preview_feedback_submitted = False
                else:
                    st.error("Video unavailable for this script.")
            except Exception as e:
                st.error(f"Video generation failed: {e}")
                
    # If a preview exists in state, render it and the feedback form
    if 'last_preview_path' in st.session_state and os.path.exists(st.session_state.last_preview_path):
        st.markdown("""
        <div class="preview-container">
            <div class='telemetry-text' style="justify-content:center; color:#38BDF8; margin-bottom:10px;">⬡ AI GENERATED CONCEPT PREVIEW</div>
            <div style="font-size:0.7rem; color:#475569; font-family:'JetBrains Mono',monospace; letter-spacing:1px; margin-bottom:12px;">MOOD REFERENCE ONLY</div>
        """, unsafe_allow_html=True)
        
        st.video(st.session_state.last_preview_path, format="video/mp4", autoplay=True, loop=True, muted=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        # --- PREVIEW FEEDBACK --
        st.markdown("<br>", unsafe_allow_html=True)
        st.session_state.avatar_state = 'feedback'
        with st.form("preview_feedback_form"):
            st.markdown("#### Did this preview match your mental picture?")
            match_choice = st.radio("Alignment match:", ["Yes", "Partially", "No"], horizontal=True, label_visibility="collapsed")
            preview_notes = st.text_input("What felt off? (Optional):")
            submit_pv = st.form_submit_button("SUBMIT PREVIEW FEEDBACK")
            
            if submit_pv:
                try:
                    # Append to csv manually or via helper
                    fb_file = Path("data/feedback/preview_feedback.csv")
                    fb_file.parent.mkdir(parents=True, exist_ok=True)
                    if not fb_file.exists():
                        pd.DataFrame(columns=["script_id", "genre", "ai_decision", "preview_match", "notes", "timestamp"]).to_csv(fb_file, index=False)
                        
                    new_row = {
                        "script_id": st.session_state.last_script_id,
                        "genre": selected_genre,
                        "ai_decision": d_label,
                        "preview_match": match_choice,
                        "notes": preview_notes,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    df_pfb = pd.read_csv(fb_file)
                    df_pfb = pd.concat([df_pfb, pd.DataFrame([new_row])], ignore_index=True)
                    df_pfb.to_csv(fb_file, index=False)
                    st.session_state.preview_feedback_submitted = True
                except Exception as e:
                    st.error(f"Failed to record feedback: {e}")
                    
        if st.session_state.get('preview_feedback_submitted', False):
            st.success("Preview feedback recorded.")
            st.session_state.preview_feedback_submitted = False

elif evaluate_btn and not script_text:
    st.error("❌ ERROR: NO NARRATIVE DATA DETECTED")

# ─── ML PREDICTIONS LEADERBOARD ───
st.markdown("<br><hr style='border-color:rgba(56,189,248,0.08);'>", unsafe_allow_html=True)
st.markdown("<div class='telemetry-text'>⬡ ML PREDICTIONS LEADERBOARD</div>", unsafe_allow_html=True)
st.caption("Top-ranked titles from the trained ML Greenlight model — based on content signals, audience reactions, script evaluations, and ground truth validation.")

try:
    pred_path = Path("data/ml_dataset/ml_predictions.csv")
    if pred_path.exists():
        df_pred = pd.read_csv(pred_path)
        
        # Filters
        fc1, fc2 = st.columns(2)
        with fc1:
            filter_decision = st.multiselect("Filter by Decision:", 
                ["GREENLIGHT", "PILOT", "DEFER", "REWORK"], 
                default=["GREENLIGHT", "PILOT"])
        with fc2:
            top_n = st.slider("Show Top N:", 5, 50, 10)
        
        filtered = df_pred[df_pred["decision"].isin(filter_decision)].head(top_n)
        
        if not filtered.empty:
            # Color-coded table
            for idx, (_, row) in enumerate(filtered.iterrows(), 1):
                dec = row["decision"]
                score = row["greenlight_score"]
                color = "#34d399" if dec == "GREENLIGHT" else "#60a5fa" if dec == "PILOT" else "#f59e0b" if dec == "DEFER" else "#ef4444"
                mal = f"{row['anime_mal_score']:.1f}" if row.get('anime_mal_score', 0) > 0 else "N/A"
                scr = f"{row.get('script_overall', 0):.1f}" if row.get('script_overall', 0) > 0 else "—"
                
                st.markdown(f"""
                <div style="display: flex; align-items: center; padding: 10px 15px; margin: 4px 0;
                            background: rgba(15, 23, 42, 0.6); border-left: 3px solid {color};
                            border-radius: 4px; font-family: 'JetBrains Mono', monospace;">
                    <span style="color: #64748b; width: 35px; font-size: 0.8rem;">#{idx}</span>
                    <span style="color: #f1f5f9; flex: 1; font-weight: 600;">{row['content_id'].replace('_', ' ').title()}</span>
                    <span style="color: #94a3b8; width: 60px; text-align: right; font-size: 0.8rem;">{row.get('genre', '')}</span>
                    <span style="color: {color}; width: 55px; text-align: right; font-weight: 700;">{score:.0f}</span>
                    <span style="color: {color}; width: 90px; text-align: right; font-size: 0.8rem; font-weight: 600;">{dec}</span>
                    <span style="color: #94a3b8; width: 50px; text-align: right; font-size: 0.8rem;">MAL {mal}</span>
                    <span style="color: #94a3b8; width: 50px; text-align: right; font-size: 0.8rem;">SCR {scr}</span>
                </div>
                """, unsafe_allow_html=True)
            
            # Summary stats
            st.markdown("<br>", unsafe_allow_html=True)
            sc1, sc2, sc3, sc4 = st.columns(4)
            total = len(df_pred)
            with sc1: st.metric("🟢 GREENLIGHT", len(df_pred[df_pred['decision']=='GREENLIGHT']))
            with sc2: st.metric("🔵 PILOT", len(df_pred[df_pred['decision']=='PILOT']))
            with sc3: st.metric("🟡 DEFER", len(df_pred[df_pred['decision']=='DEFER']))
            with sc4: st.metric("🔴 REWORK", len(df_pred[df_pred['decision']=='REWORK']))
        else:
            st.info("No titles match the selected filters.")
    else:
        st.warning("ML predictions not yet generated. Run: `python ml_scoring_pipeline.py`")
except Exception as e:
    st.error(f"Failed to load predictions: {e}")

# ─── BATCH UPLOAD & RANK ───
st.markdown("<br><hr style='border-color:rgba(56,189,248,0.08);'>", unsafe_allow_html=True)
st.markdown("<div class='telemetry-text'>⬡ NEW IP UPLOAD & RANKING</div>", unsafe_allow_html=True)
st.caption("Upload new, unpublished scripts to evaluate their Greenlight potential. Since these lack real market data, the ML model simulates a top-tier launch so the final score is heavily driven by intrinsic script quality.")

uploaded_scripts = st.file_uploader(
    "Upload script files (.txt)", type=["txt", "md"],
    accept_multiple_files=True, key="batch_upload"
)

if uploaded_scripts and st.button("🚀 RANK ALL UPLOADED SCRIPTS"):
    with st.spinner("Evaluating scripts with Gemini AI..."):
        import json
        results = []
        for i, ufile in enumerate(uploaded_scripts):
            text = ufile.read().decode("utf-8").strip()
            if len(text) < 20:
                st.warning(f"{ufile.name}: Too short, skipping")
                continue
            
            st.text(f"  [{i+1}/{len(uploaded_scripts)}] Evaluating {ufile.name}...")
            try:
                # Save temp and score
                import uuid, os, importlib
                import ml_scoring_pipeline
                importlib.reload(ml_scoring_pipeline)
                from ml_scoring_pipeline import score_new_script
                
                tmp_name = f"temp_batch_{uuid.uuid4().hex[:8]}_{ufile.name}"
                with open(tmp_name, "w", encoding="utf-8") as f:
                    f.write(text)
                
                result = score_new_script(tmp_name)
                
                if os.path.exists(tmp_name):
                    os.unlink(tmp_name)
                
                if result:
                    result["filename"] = ufile.name
                    results.append(result)
            except Exception as e:
                st.error(f"Error scoring {ufile.name}: {e}")
        
        if results:
            results.sort(key=lambda x: x["greenlight_score"], reverse=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("### 🏆 RANKED RESULTS")
            
            for idx, r in enumerate(results, 1):
                dec = r["decision"]
                score = r["greenlight_score"]
                color = "#34d399" if dec == "GREENLIGHT" else "#60a5fa" if dec == "PILOT" else "#f59e0b" if dec == "DEFER" else "#ef4444"
                eval_data = r.get("evaluation", {})
                verdict = eval_data.get("one_line_verdict", "")
                
                st.markdown(f"""
                <div style="padding: 15px; margin: 8px 0; background: rgba(15, 23, 42, 0.6);
                            border-left: 4px solid {color}; border-radius: 6px;">
                    <div style="display: flex; align-items: center; margin-bottom: 8px;">
                        <span style="font-size: 1.5rem; font-weight: 800; color: {color}; margin-right: 15px;">#{idx}</span>
                        <span style="font-size: 1.1rem; font-weight: 600; color: #f1f5f9; flex: 1;">{r['filename']}</span>
                        <span style="font-size: 1.8rem; font-weight: 800; color: {color};">{score:.0f}</span>
                    </div>
                    <div style="color: #94a3b8; font-size: 0.85rem; font-family: 'JetBrains Mono';">
                        {dec} | Intrinsic Quality: {r.get('script_quality_score', 0):.2f}/1.0 | {verdict}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            # Show top 10 if more than 10
            if len(results) > 10:
                st.info(f"Showing all {len(results)} results. Top 10 recommended for greenlight review.")

# --- RENDER AVATAR ---
render_avatar(st.session_state.avatar_state)

