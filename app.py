
from __future__ import annotations
from datetime import date, datetime, timedelta
import os
import time
import re

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from providers import get_provider
from database import init_db, save_odds_snapshot, load_previous_best_odds, load_alerts, save_bet, load_bets, load_snapshots, update_bet_result, delete_bet
from model import analyze, final_call, exacta_legs, trifecta_count
from reddit_signals import RedditSignalProvider
from secrets_loader import load_streamlit_secrets_into_env

load_dotenv()
load_streamlit_secrets_into_env()
init_db()

st.set_page_config(page_title="Derby V3.1 Smart Reddit", page_icon="🏇", layout="wide")

st.markdown("""
<style>
.greenplus {background:#0b6b28;color:white;font-weight:1000;border-radius:10px;padding:8px 12px;margin:5px 0;}
.green {background:#d4edda;color:#155724;font-weight:900;border-radius:10px;padding:8px 12px;margin:5px 0;}
.yellow {background:#fff3cd;color:#856404;font-weight:900;border-radius:10px;padding:8px 12px;margin:5px 0;}
.red {background:#f8d7da;color:#721c24;font-weight:900;border-radius:10px;padding:8px 12px;margin:5px 0;}
.gray {background:#e2e3e5;color:#383d41;font-weight:900;border-radius:10px;padding:8px 12px;margin:5px 0;}
.call {font-size:24px;font-weight:1000;border:3px solid #111;padding:14px;border-radius:14px;background:#f6f6f6;}
.summary-card {border:1px solid #ddd;border-radius:12px;padding:12px;margin:8px 0;background:#fafafa;}
.big-horse {font-size:20px;font-weight:1000;}
.small-muted {color:#666;font-size:13px;}
.reddit-chip {display:inline-block;border-radius:999px;padding:3px 8px;background:#eef;margin:2px;font-size:12px;font-weight:800;}
.fade-chip {display:inline-block;border-radius:999px;padding:3px 8px;background:#f8d7da;color:#721c24;margin:2px;font-size:12px;font-weight:900;}
.sharp-chip {display:inline-block;border-radius:999px;padding:3px 8px;background:#d4edda;color:#155724;margin:2px;font-size:12px;font-weight:900;}
.sharp-alert {border:3px solid #0b6b28;background:#d4edda;color:#155724;border-radius:14px;padding:14px;margin:10px 0;font-weight:900;}
.trap-alert {border:3px solid #721c24;background:#f8d7da;color:#721c24;border-radius:14px;padding:14px;margin:10px 0;font-weight:900;}
.alert-title {font-size:20px;font-weight:1000;}
.play-card {border:3px solid #111;border-radius:16px;padding:16px;margin:12px 0;background:#ffffff;}
.play-a {border-color:#0b6b28;background:#e9f7ef;}
.play-b {border-color:#856404;background:#fff8dc;}
.play-pass {border-color:#721c24;background:#fdecea;}
.play-title {font-size:22px;font-weight:1000;}
.play-meta {font-size:14px;color:#333;margin-top:4px;}
.bet-amount {font-size:28px;font-weight:1000;color:#0b6b28;}

@keyframes fadeSlideUp {
  0% {opacity:0; transform:translateY(18px);}
  100% {opacity:1; transform:translateY(0);}
}
@keyframes pulseGreen {
  0% {box-shadow:0 0 0 0 rgba(11,107,40,.65);}
  70% {box-shadow:0 0 0 14px rgba(11,107,40,0);}
  100% {box-shadow:0 0 0 0 rgba(11,107,40,0);}
}
@keyframes pulseYellow {
  0% {box-shadow:0 0 0 0 rgba(133,100,4,.55);}
  70% {box-shadow:0 0 0 12px rgba(133,100,4,0);}
  100% {box-shadow:0 0 0 0 rgba(133,100,4,0);}
}
@keyframes shimmer {
  0% {background-position:-300px 0;}
  100% {background-position:300px 0;}
}
@keyframes glowText {
  0%,100% {text-shadow:0 0 0 rgba(11,107,40,0);}
  50% {text-shadow:0 0 10px rgba(11,107,40,.45);}
}

.greenplus, .green, .yellow, .red, .gray, .summary-card, .play-card, .sharp-alert, .trap-alert {
  animation: fadeSlideUp .45s ease-out both;
}
.greenplus {
  animation: fadeSlideUp .45s ease-out both, pulseGreen 2s infinite;
}
.play-a {
  animation: fadeSlideUp .45s ease-out both, pulseGreen 2.2s infinite;
}
.play-b {
  animation: fadeSlideUp .45s ease-out both, pulseYellow 2.8s infinite;
}
.play-card, .summary-card {
  transition: transform .18s ease, box-shadow .18s ease;
}
.play-card:hover, .summary-card:hover {
  transform: translateY(-3px) scale(1.01);
  box-shadow: 0 10px 24px rgba(0,0,0,.12);
}
.play-title, .big-horse {
  animation: glowText 2.6s ease-in-out infinite;
}
.bet-amount {
  background: linear-gradient(90deg, #0b6b28, #179447, #0b6b28);
  -webkit-background-clip: text;
  color: transparent;
  background-size: 300px 100%;
  animation: shimmer 2.4s linear infinite;
}
.animated-badge {
  display:inline-block;
  border-radius:999px;
  padding:4px 10px;
  background:#111;
  color:#fff;
  font-weight:900;
  animation: fadeSlideUp .4s ease-out both;
}
.steam-strong {display:inline-block;border-radius:999px;padding:4px 10px;background:#0b6b28;color:white;font-weight:1000;margin:2px;animation:pulseGreen 1.8s infinite;}
.steam {display:inline-block;border-radius:999px;padding:4px 10px;background:#d4edda;color:#155724;font-weight:900;margin:2px;}
.drift {display:inline-block;border-radius:999px;padding:4px 10px;background:#f8d7da;color:#721c24;font-weight:900;margin:2px;animation:pulseYellow 2s infinite;}
.stable {display:inline-block;border-radius:999px;padding:4px 10px;background:#e2e3e5;color:#383d41;font-weight:800;margin:2px;}
.steam-card {border:2px solid #ddd;border-radius:14px;padding:12px;margin:8px 0;background:#fff;}
.raceday-panel {border:3px solid #111;border-radius:16px;padding:14px;margin:10px 0;background:#f7f7f7;}
.raceday-live {border-color:#0b6b28;background:#e9f7ef;}
.raceday-alert {border-color:#721c24;background:#fdecea;color:#721c24;}
.countdown {font-size:22px;font-weight:1000;}
.roi-good {background:#d4edda;color:#155724;border-radius:12px;padding:10px;margin:6px 0;font-weight:900;}
.roi-bad {background:#f8d7da;color:#721c24;border-radius:12px;padding:10px;margin:6px 0;font-weight:900;}
.roi-neutral {background:#e2e3e5;color:#383d41;border-radius:12px;padding:10px;margin:6px 0;font-weight:900;}
.bankroll-card {border:3px solid #111;border-radius:16px;padding:14px;margin:10px 0;background:#fff;}
.bankroll-good {border-color:#0b6b28;background:#e9f7ef;color:#155724;}
.bankroll-warn {border-color:#856404;background:#fff8dc;color:#856404;}
.bankroll-bad {border-color:#721c24;background:#fdecea;color:#721c24;}
.size-pill {display:inline-block;border-radius:999px;padding:4px 10px;background:#111;color:#fff;font-weight:900;margin:2px;}
.ticket-card {border:3px solid #111;border-radius:16px;padding:14px;margin:10px 0;background:#fff;}
.ticket-win {border-color:#0b6b28;background:#e9f7ef;color:#155724;}
.ticket-exacta {border-color:#856404;background:#fff8dc;color:#856404;}
.ticket-trifecta {border-color:#3b3b98;background:#eef0ff;color:#1f2a7a;}
.ticket-pass {border-color:#721c24;background:#fdecea;color:#721c24;}
.ticket-title {font-size:22px;font-weight:1000;}
.ticket-lines {font-family:monospace;font-weight:800;margin-top:6px;}
.timing-card {border:3px solid #111;border-radius:16px;padding:14px;margin:10px 0;background:#fff;}
.timing-now {border-color:#0b6b28;background:#e9f7ef;color:#155724;}
.timing-soon {border-color:#856404;background:#fff8dc;color:#856404;}
.timing-wait {border-color:#3b3b98;background:#eef0ff;color:#1f2a7a;}
.timing-pass {border-color:#721c24;background:#fdecea;color:#721c24;}
.timing-title {font-size:22px;font-weight:1000;}
</style>
""", unsafe_allow_html=True)

st.title("Derby V4.1.1 - Timing Engine Fix")
st.markdown("<span class='animated-badge'>Odds timing engine mode</span>", unsafe_allow_html=True)
st.caption("Auto race-card mode using public entries + morning-line odds fallback, with auto recommender, Reddit overlay, sharp alerts, and steam logic.")

mode = "Demo"  # safe default

RACE_DAY_PRESETS = {
    "Oaks Day - Churchill Downs": {"track": "Churchill Downs", "date_offset": "friday"},
    "Derby Day - Churchill Downs": {"track": "Churchill Downs", "date_offset": "saturday"},
    "Today": {"track": "Churchill Downs", "date_offset": "today"},
    "Tomorrow": {"track": "Churchill Downs", "date_offset": "tomorrow"},
    "Custom": {"track": "Churchill Downs", "date_offset": "custom"},
}

TRACK_OPTIONS = [
    "Churchill Downs",
    "Keeneland",
    "Saratoga",
    "Belmont at the Big A",
    "Gulfstream Park",
    "Santa Anita",
    "Del Mar",
    "Oaklawn Park",
    "Fair Grounds",
    "Tampa Bay Downs",
    "Custom"
]

def next_weekday(target_weekday: int):
    today = date.today()
    days_ahead = target_weekday - today.weekday()
    if days_ahead < 0:
        days_ahead += 7
    return today + timedelta(days=days_ahead)

def preset_date(offset: str):
    if offset == "today":
        return date.today()
    if offset == "tomorrow":
        return date.today() + timedelta(days=1)
    if offset == "friday":
        return next_weekday(4)
    if offset == "saturday":
        return next_weekday(5)
    return date.today()


with st.sidebar:
    animations_on = st.checkbox("Enable animations", value=True)
    if not animations_on:
        st.markdown("""
        <style>
        *, *::before, *::after {
          animation: none !important;
          transition: none !important;
        }
        </style>
        """, unsafe_allow_html=True)

    st.header("Data mode")
    mode = st.radio("Data source", ["Auto Real Data", "Demo"], index=0)
    if mode == "Auto Real Data":
        st.caption("Uses public Equibase-style entries when available; falls back to Demo if parsing fails.")
    else:
        st.caption("Demo mode uses simulated race card and odds.")
    st.header("Track / Race Day")
    race_day_preset = st.selectbox("Race day preset", list(RACE_DAY_PRESETS.keys()), index=0)

    track_choice = st.selectbox("Track", TRACK_OPTIONS, index=0)
    if track_choice == "Custom":
        track = st.text_input("Custom track name", "Churchill Downs")
    else:
        track = track_choice

    preset = RACE_DAY_PRESETS[race_day_preset]
    default_date = preset_date(preset["date_offset"])

    if race_day_preset == "Custom":
        race_date = st.date_input("Race date", value=date.today())
    else:
        race_date = st.date_input("Race date", value=default_date)

    st.caption(f"Selected: {track} on {race_date}")

    st.header("Smart Reddit")
    use_reddit = st.checkbox("Enable Reddit layer", value=False)
    subreddit_text = st.text_input("Subreddits", "horseracing,sportsbook,KentuckyDerby")
    reddit_limit = st.slider("Posts per subreddit", 25, 250, 75, 25)
    reddit_model_boost = st.slider("Reddit overlay influence", 0.0, 0.10, 0.03, 0.01)
    alert_sharp_low_hype = st.checkbox("Alert: sharp value + low hype", value=True)
    alert_public_traps = st.checkbox("Alert: public trap / fade risk", value=True)
    low_hype_threshold = st.slider("Low hype threshold %", 0, 60, 35, 5)

    st.header("Steam Engine")
    strong_steam_threshold = st.slider("Strong steam threshold %", 5, 50, 20, 5)
    steam_threshold = st.slider("Steam threshold %", 3, 30, 10, 1)
    drift_threshold = st.slider("Drift threshold %", 3, 40, 15, 1)
    steam_boost = st.slider("Steam score boost", 0, 20, 8, 1)
    drift_penalty = st.slider("Drift score penalty", 0, 25, 10, 1)

    st.header("Race Day Auto Mode")
    auto_scan = st.checkbox("Auto-scan full card", True)
    scan_seconds = st.slider("Scan every seconds", 15, 300, 60, 15)
    auto_rerun = st.checkbox("Auto-refresh browser", True)
    manual_scan = st.button("Scan full card now")
    if st.button("Clear cache / refresh columns"):
        st.cache_data.clear()
        for key in ["daily_summary", "last_scan", "last_scan_time", "last_a_play_count", "auto_alerts"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

    st.header("Odds Timing Engine")
    prime_window_start = st.slider("Prime bet window starts: minutes to post", 1, 30, 10, 1)
    prime_window_end = st.slider("Prime bet window ends: minutes to post", 0, 10, 2, 1)
    watch_window_start = st.slider("Watch window starts: minutes to post", 5, 60, 25, 5)
    stale_odds_minutes = st.slider("Stale odds warning after minutes", 2, 30, 8, 1)
    require_prime_window_for_a = st.checkbox("Require prime window for full A-play size", True)


    st.header("Bankroll")
    bankroll = st.number_input("Bankroll", min_value=0.0, value=100.0, step=10.0)
    unit = st.number_input("Exotic unit", min_value=0.10, value=1.0, step=.5)
    kelly_mult = st.slider("Kelly fraction", .05, 1.0, .25, .05)
    max_win_pct = st.slider("Max win bet % bankroll", .005, .10, .03, .005)
    st.header("Bankroll Engine")
    starting_bankroll = st.number_input("Starting bankroll tracking ($)", min_value=0.0, value=bankroll, step=10.0)
    daily_stop_loss_pct = st.slider("Daily stop-loss %", 1, 30, 10, 1)
    max_race_exposure_pct = st.slider("Max exposure per race %", 1, 15, 4, 1)
    max_daily_exposure_pct = st.slider("Max total daily exposure %", 1, 30, 10, 1)
    a_play_multiplier = st.slider("A-play size multiplier", 0.25, 2.0, 1.0, 0.25)
    b_play_multiplier = st.slider("B-play size multiplier", 0.10, 1.0, 0.5, 0.10)
    c_play_multiplier = st.slider("C-play size multiplier", 0.05, 0.5, 0.2, 0.05)

    st.header("Bet Structure Engine")
    exacta_unit = st.number_input("Exacta unit ($)", min_value=0.10, value=1.00, step=0.50)
    trifecta_unit = st.number_input("Trifecta unit ($)", min_value=0.10, value=0.50, step=0.50)
    max_exacta_horses = st.slider("Max exacta horses", 2, 5, 4, 1)
    max_trifecta_horses = st.slider("Max trifecta horses", 3, 6, 5, 1)
    min_win_edge_gap = st.slider("Win edge gap threshold %", 1, 20, 6, 1)
    enable_place_show = st.checkbox("Allow Place/Show recommendations", True)
    enable_trifecta = st.checkbox("Allow Trifecta recommendations", True)
    max_daily_bets = st.slider("Max recommended bets/day", 1, 6, 3, 1)
    min_a_ev = st.slider("A-play min EV %", 5, 30, 10, 1)
    min_b_ev = st.slider("B-play min EV %", 1, 20, 6, 1)
    max_total_daily_risk_pct = st.slider("Max total daily risk % bankroll", 1, 25, 8, 1)

    st.header("Race Day Alerts")
    alert_a_play = st.checkbox("Alert on A play", True)
    alert_strong_steam = st.checkbox("Alert on strong steam", True)
    alert_green_steam = st.checkbox("Alert on GREEN + steam", True)

    st.header("Model weights")
    weights = {
        "speed": st.slider("Speed", 0.0, 5.0, 2.4, .1),
        "pace": st.slider("Pace", 0.0, 5.0, 2.0, .1),
        "form": st.slider("Form", 0.0, 5.0, 1.5, .1),
        "class": st.slider("Class", 0.0, 5.0, 1.3, .1),
        "jockey": st.slider("Jockey", 0.0, 5.0, 1.0, .1),
        "trainer": st.slider("Trainer", 0.0, 5.0, 1.0, .1),
        "track": st.slider("Track fit", 0.0, 5.0, 1.0, .1),
        "distance": st.slider("Distance", 0.0, 5.0, 1.1, .1),
        "post": st.slider("Post", 0.0, 5.0, .6, .1),
    }
    blend = {
        "market": st.slider("Market blend", .1, .9, .58, .01),
        "factor": st.slider("Factor blend", .1, .9, .42, .01),
    }

provider = get_provider(mode if "mode" in globals() else "Demo")

st.info(f"Current data source: {mode}")

try:
    races = provider.races(track, str(race_date))
    if mode == "Auto Real Data":
        st.info("Auto Real Data is ON. If entries cannot be parsed from the public source, the app automatically falls back to demo data.")
except Exception as exc:
    st.error(f"Data load failed: {exc}")
    st.stop()

@st.cache_data(ttl=600, show_spinner=False)
def load_reddit_cached(runners, race_name, subreddits, limit):
    return RedditSignalProvider().fetch(list(runners), race_name, list(subreddits), limit)

def has_reddit_credentials():
    return bool(os.getenv("REDDIT_CLIENT_ID") and os.getenv("REDDIT_CLIENT_SECRET") and os.getenv("REDDIT_USER_AGENT"))

def apply_reddit_overlay(rankings: pd.DataFrame, reddit_df: pd.DataFrame | None) -> pd.DataFrame:
    r = rankings.copy()
    if reddit_df is None or reddit_df.empty:
        r["mentions"] = 0
        r["avg_sentiment"] = 0.0
        r["reddit_signal"] = "Off / none"
        r["public_hype"] = 0.0
        r["fade_risk"] = 0
        r["sharp_public_signal"] = "Model only"
        return r

    r = r.merge(reddit_df, on="runner", how="left")
    r[["mentions", "avg_sentiment", "reddit_heat", "public_hype", "fade_risk"]] = r[
        ["mentions", "avg_sentiment", "reddit_heat", "public_hype", "fade_risk"]
    ].fillna(0)
    r["reddit_signal"] = r["reddit_signal"].fillna("Quiet")

    # Smart use: don't let Reddit dominate. Small nudge only.
    hype = r["public_hype"].astype(float)
    if hype.sum() > 0 and reddit_model_boost > 0:
        reddit_adj = hype / hype.sum()
        r["model_prob"] = (r["model_prob"] * (1 - reddit_model_boost)) + (reddit_adj * reddit_model_boost)
        total = r["model_prob"].sum()
        if total:
            r["model_prob"] = r["model_prob"] / total
        r["edge_prob"] = r["model_prob"] - r["market_fair_prob"]
        r["expected_value"] = r["model_prob"] * (r["best_decimal_odds"] - 1) - (1 - r["model_prob"])
        r["kelly_fraction"] = (r["expected_value"] / (r["best_decimal_odds"] - 1)).clip(lower=0)
        for col in ["model_prob","edge_prob","expected_value","kelly_fraction"]:
            r[col + "_pct"] = r[col] * 100

    def divergence(row):
        if row["tier"] in ["GREEN+", "GREEN"] and row["public_hype"] < 0.35:
            return "Sharp value / low public buzz"
        if row["tier"] in ["RED", "YELLOW"] and row["public_hype"] >= 0.75:
            return "Public trap / fade risk"
        if row["tier"] in ["GREEN+", "GREEN"] and row["public_hype"] >= 0.65:
            return "Model + public aligned"
        return "Neutral"

    r["sharp_public_signal"] = r.apply(divergence, axis=1)
    return r

def analyze_single_race(race):
    odds = provider.odds(race.race_id)
    factors = provider.factors(race.race_id)
    prev = load_previous_best_odds(race.race_id)
    rankings, shape = analyze(odds, factors, prev, weights, blend)

    reddit_df = None
    if use_reddit:
        if not has_reddit_credentials():
            # handled in UI
            reddit_df = None
        else:
            runners = tuple(rankings["runner"].tolist())
            subs = tuple(x.strip() for x in subreddit_text.split(",") if x.strip())
            reddit_df = load_reddit_cached(runners, race.name, subs, reddit_limit)

    rankings = apply_reddit_overlay(rankings, reddit_df)

    call = final_call(rankings, shape)
    top = rankings.iloc[0] if len(rankings) else None
    greens = rankings[rankings["tier"].isin(["GREEN+", "GREEN"])]
    yellows = rankings[rankings["tier"] == "YELLOW"]
    active = rankings[~rankings["scratched"]]
    exacta = active.sort_values(["model_prob", "expected_value"], ascending=False).head(min(4, len(active)))
    return odds, factors, rankings, shape, call, top, greens, yellows, exacta, reddit_df

def build_daily_summary():
    rows = []
    ts = datetime.now().isoformat(timespec="seconds")
    for race in races:
        odds, factors, rankings, shape, call, top, greens, yellows, exacta, reddit_df = analyze_single_race(race)
        save_odds_snapshot(ts, race.race_id, odds)
        best_play = "PASS"
        if top is not None:
            if top["tier"] in ["GREEN+", "GREEN"]:
                best_play = f"WIN: {top['runner']}"
            elif len(yellows) >= 3:
                best_play = "SMALL EXACTA"

            rows.append({
                "Race #": race.number,
                "Race": race.name,
                "Post": race.post_time,
                "Best Horse": top["runner"],
                "Tier": top["tier"],
                "Final Call": call,
                "Best Play": best_play,
                "EV %": round(float(top["expected_value_pct"]), 1),
                "Kelly %": round(float(top["kelly_fraction_pct"]), 1),
                "Model %": round(float(top["model_prob_pct"]), 1),
                "Odds": int(top["best_american_odds"]),
                "Pace": shape["shape"],
                "Bias": shape["bias"],
                "Volatility": shape["volatility"],
                "Green Count": len(greens),
                "Reddit": top.get("reddit_signal", "Off / none"),
                "Mentions": int(top.get("mentions", 0)),
                "Public Hype": round(float(top.get("public_hype", 0)) * 100, 0),
                "Sharp/Public": top.get("sharp_public_signal", "Model only"),
                "Sharp Low-Hype Alert": int(top.get("sharp_public_signal", "") == "Sharp value / low public buzz" and float(top.get("public_hype", 0)) * 100 <= low_hype_threshold),
                "Public Trap Alert": int("trap" in str(top.get("sharp_public_signal", "")).lower()),
                "Odds Move Raw": float(top.get("odds_change_pct", 0)),
            })
    return pd.DataFrame(rows)



def classify_steam_from_move(move_pct: float) -> tuple[str, str]:
    """
    Uses odds_change_pct where negative means odds shortened (steam)
    and positive means odds drifted.
    """
    try:
        move_pct = float(move_pct)
    except Exception:
        move_pct = 0.0

    if move_pct <= -(strong_steam_threshold / 100):
        return "STRONG STEAM", "steam-strong"
    if move_pct <= -(steam_threshold / 100):
        return "STEAM", "steam"
    if move_pct >= (drift_threshold / 100):
        return "DRIFT", "drift"
    return "STABLE", "stable"


def enrich_summary_with_steam(summary_df: pd.DataFrame) -> pd.DataFrame:
    df = summary_df.copy()

    # Defensive defaults so old cached summaries or partial scans never crash.
    if df.empty:
        for col, default in {
            "Odds Move Raw": 0.0,
            "Steam Signal": "STABLE",
            "Steam CSS": "stable",
            "Odds Move %": 0.0,
        }.items():
            df[col] = default
        return df

    if "Odds Move Raw" not in df.columns:
        df["Odds Move Raw"] = 0.0

    df["Odds Move Raw"] = pd.to_numeric(df["Odds Move Raw"], errors="coerce").fillna(0.0)

    labels = df["Odds Move Raw"].apply(classify_steam_from_move)
    df["Steam Signal"] = labels.apply(lambda x: x[0])
    df["Steam CSS"] = labels.apply(lambda x: x[1])
    df["Odds Move %"] = (df["Odds Move Raw"].astype(float) * 100).round(1)

    return df



def build_raceday_alerts(summary_df: pd.DataFrame, recommendations_df: pd.DataFrame) -> list[str]:
    alerts = []

    if recommendations_df is not None and not recommendations_df.empty and alert_a_play:
        a_plays = recommendations_df[recommendations_df.get("Play Grade", "") == "A"]
        for _, row in a_plays.iterrows():
            alerts.append(f"A PLAY: Race {int(row['Race #'])} - {row['Best Horse']} - {row.get('Bet Type', 'WIN')} - Suggested ${row.get('Suggested Bet $', 0):.2f}")

    if "Steam Signal" in summary_df.columns and alert_strong_steam:
        strong = summary_df[summary_df["Steam Signal"] == "STRONG STEAM"]
        for _, row in strong.iterrows():
            alerts.append(f"STRONG STEAM: Race {int(row['Race #'])} - {row['Best Horse']} - Move {row.get('Odds Move %', 0)}%")

    if "Steam Signal" in summary_df.columns and alert_green_steam:
        green_steam = summary_df[
            summary_df["Tier"].isin(["GREEN+", "GREEN"]) &
            summary_df["Steam Signal"].isin(["STRONG STEAM", "STEAM"])
        ]
        for _, row in green_steam.iterrows():
            alerts.append(f"GREEN + STEAM: Race {int(row['Race #'])} - {row['Best Horse']} - {row['Tier']} - {row['Steam Signal']}")

    return alerts


def build_auto_recommendations(summary_df: pd.DataFrame) -> pd.DataFrame:
    if summary_df.empty:
        return pd.DataFrame()

    plays = summary_df.copy()
    plays["Recommendation"] = "PASS"
    plays["Play Grade"] = "PASS"
    plays["Bet Type"] = "PASS"
    plays["Reason"] = "No qualifying edge"
    plays["Raw Score"] = 0.0

    for idx, row in plays.iterrows():
        tier = row["Tier"]
        ev = float(row["EV %"])
        kelly = float(row["Kelly %"])
        sharp_alert = int(row.get("Sharp Low-Hype Alert", 0))
        trap = int(row.get("Public Trap Alert", 0))
        hype = float(row.get("Public Hype", 0))
        volatility = str(row.get("Volatility", ""))
        steam_signal = str(row.get("Steam Signal", "STABLE"))

        score = ev + kelly * 0.5
        if tier == "GREEN+":
            score += 12
        elif tier == "GREEN":
            score += 7
        elif tier == "YELLOW":
            score += 1

        if sharp_alert:
            score += 10
        if steam_signal in ["STRONG STEAM", "STEAM"] and tier in ["GREEN+", "GREEN"]:
            score += steam_boost
        if steam_signal == "STRONG STEAM" and sharp_alert:
            score += 4
        if steam_signal == "DRIFT":
            score -= drift_penalty
        if trap:
            score -= 12
        if volatility == "HIGH":
            score -= 4
        if hype >= 75 and tier not in ["GREEN+", "GREEN"]:
            score -= 6

        grade = "PASS"
        rec = "PASS"
        bet_type = "PASS"
        reason = "No qualifying edge"

        if tier == "GREEN+" and ev >= min_a_ev and sharp_alert and not trap and steam_signal != "DRIFT":
            grade = "A"
            rec = "BET"
            bet_type = "WIN"
            reason = "GREEN+ with sharp low-hype alert; steam check passed"
        elif tier in ["GREEN+", "GREEN"] and ev >= min_b_ev and not trap and steam_signal != "DRIFT":
            grade = "B"
            rec = "BET SMALL"
            bet_type = "WIN"
            reason = "GREEN-tier value without trap signal; no drift"
        elif tier == "YELLOW" and ev >= min_b_ev and sharp_alert and not trap:
            grade = "C"
            rec = "TINY EXACTA ONLY"
            bet_type = "EXACTA"
            reason = "Small edge with sharp/public divergence"

        if volatility == "HIGH" and grade not in ["A"]:
            grade = "PASS"
            rec = "PASS"
            bet_type = "PASS"
            reason = "High volatility filter"

        plays.at[idx, "Raw Score"] = score
        plays.at[idx, "Play Grade"] = grade
        plays.at[idx, "Recommendation"] = rec
        plays.at[idx, "Bet Type"] = bet_type
        plays.at[idx, "Reason"] = reason

    plays = plays.sort_values("Raw Score", ascending=False).reset_index(drop=True)

    eligible = plays[plays["Recommendation"] != "PASS"].head(max_daily_bets).copy()
    if eligible.empty:
        plays["Suggested Bet $"] = 0.0
        return plays

    daily_cap = bankroll * (max_total_daily_risk_pct / 100)
    suggested = []
    for _, row in eligible.iterrows():
        kelly_frac = max(float(row["Kelly %"]) / 100, 0)
        if row["Play Grade"] == "A":
            amt = bankroll * kelly_frac * kelly_mult
        elif row["Play Grade"] == "B":
            amt = bankroll * kelly_frac * kelly_mult * 0.5
        else:
            amt = unit

        amt = min(amt, bankroll * max_win_pct)
        suggested.append(max(round(amt, 2), 0))

    total_suggested = sum(suggested)
    if total_suggested > daily_cap and total_suggested > 0:
        scale = daily_cap / total_suggested
        suggested = [round(x * scale, 2) for x in suggested]

    plays["Suggested Bet $"] = 0.0
    for pos, idx in enumerate(eligible.index):
        plays.at[idx, "Suggested Bet $"] = suggested[pos]

    return plays

if use_reddit and not has_reddit_credentials():
    st.warning("Reddit layer is ON, but Reddit credentials are missing. Add them in Streamlit Secrets or turn Reddit OFF.")

# V3.6 race-day scanning loop
now = time.time()
if "last_scan" not in st.session_state:
    st.session_state.last_scan = 0
if "last_scan_time" not in st.session_state:
    st.session_state.last_scan_time = "Never"

should_scan = manual_scan or "daily_summary" not in st.session_state

if auto_scan and (now - st.session_state.last_scan >= scan_seconds):
    should_scan = True

if should_scan:
    st.session_state.last_scan = now
    st.session_state.last_scan_time = datetime.now().strftime("%H:%M:%S")
    st.session_state["daily_summary"] = build_daily_summary()

if auto_scan and auto_rerun:
    seconds_left = max(0, int(scan_seconds - (time.time() - st.session_state.last_scan)))
else:
    seconds_left = None

summary_df = st.session_state["daily_summary"]


def american_profit(stake: float, odds: int) -> float:
    stake = float(stake)
    odds = int(odds)
    if odds > 0:
        return stake * odds / 100
    if odds < 0:
        return stake * 100 / abs(odds)
    return 0.0


def suggested_payout(stake: float, odds: int, result: str) -> float:
    if result == "Won":
        return round(float(stake) + american_profit(stake, odds), 2)
    if result == "Lost":
        return 0.0
    return 0.0


def performance_summary(bets: pd.DataFrame) -> dict:
    if bets.empty:
        return {"bets": 0, "settled": 0, "stake": 0.0, "profit": 0.0, "roi": 0.0, "win_rate": 0.0, "avg_clv": 0.0}

    settled = bets[bets["result"].isin(["Won", "Lost"])].copy()
    stake = float(settled["stake"].sum()) if not settled.empty else 0.0
    profit = float(settled["profit"].sum()) if not settled.empty else 0.0
    roi = profit / stake * 100 if stake else 0.0
    win_rate = settled["result"].eq("Won").mean() * 100 if len(settled) else 0.0
    avg_clv = float(settled["clv_points"].mean()) if "clv_points" in settled.columns and len(settled) else 0.0
    return {"bets": len(bets), "settled": len(settled), "stake": stake, "profit": profit, "roi": roi, "win_rate": win_rate, "avg_clv": avg_clv}



def current_bankroll_from_bets(starting_bankroll_value: float, bets: pd.DataFrame) -> float:
    if bets.empty:
        return float(starting_bankroll_value)
    settled = bets[bets["result"].isin(["Won", "Lost"])].copy()
    profit = float(settled["profit"].sum()) if not settled.empty else 0.0
    return float(starting_bankroll_value) + profit


def bankroll_health(starting_bankroll_value: float, current_bankroll_value: float) -> tuple[str, str]:
    stop_loss = globals().get("daily_stop_loss_pct", 10)
    if starting_bankroll_value <= 0:
        return "Neutral", "bankroll-warn"
    change_pct = (current_bankroll_value - starting_bankroll_value) / starting_bankroll_value * 100
    if change_pct >= 5:
        return f"Healthy (+{change_pct:.1f}%)", "bankroll-good"
    if change_pct <= -stop_loss:
        return f"Stop-loss zone ({change_pct:.1f}%)", "bankroll-bad"
    if change_pct < 0:
        return f"Caution ({change_pct:.1f}%)", "bankroll-warn"
    return f"Stable (+{change_pct:.1f}%)", "bankroll-good"


def recommended_bet_size(play_grade: str, kelly_pct: float, current_bankroll_value: float) -> float:
    kelly_fraction = max(float(kelly_pct) / 100, 0.0)
    if play_grade == "A":
        mult = a_play_multiplier
    elif play_grade == "B":
        mult = b_play_multiplier
    elif play_grade == "C":
        mult = c_play_multiplier
    else:
        return 0.0

    raw = current_bankroll_value * kelly_fraction * kelly_mult * mult
    race_cap = current_bankroll_value * (max_race_exposure_pct / 100)
    win_cap = current_bankroll_value * max_win_pct
    return round(max(min(raw, race_cap, win_cap), 0.0), 2)


def apply_bankroll_engine(recommendations_df: pd.DataFrame, current_bankroll_value: float) -> pd.DataFrame:
    if recommendations_df.empty:
        return recommendations_df

    df = recommendations_df.copy()
    if "Play Grade" not in df.columns:
        df["Play Grade"] = "PASS"
    if "Kelly %" not in df.columns:
        df["Kelly %"] = 0.0

    df["Bankroll Bet $"] = df.apply(
        lambda row: recommended_bet_size(row.get("Play Grade", "PASS"), row.get("Kelly %", 0.0), current_bankroll_value),
        axis=1,
    )

    # Enforce daily total exposure cap by scaling down recommended bets.
    daily_cap = current_bankroll_value * (max_daily_exposure_pct / 100)
    total = float(df["Bankroll Bet $"].sum())
    if total > daily_cap and total > 0:
        scale = daily_cap / total
        df["Bankroll Bet $"] = (df["Bankroll Bet $"] * scale).round(2)

    df["Sizing Note"] = df.apply(
        lambda row: "PASS" if row["Bankroll Bet $"] <= 0 else f"{row['Play Grade']}-play sized with caps",
        axis=1,
    )

    return df

def grouped_roi(bets: pd.DataFrame, group_col: str) -> pd.DataFrame:
    if bets.empty or group_col not in bets.columns:
        return pd.DataFrame()
    settled = bets[bets["result"].isin(["Won", "Lost"])].copy()
    if settled.empty:
        return pd.DataFrame()
    out = settled.groupby(group_col, dropna=False).agg(
        bets=("id", "count"),
        stake=("stake", "sum"),
        profit=("profit", "sum"),
        avg_clv=("clv_points", "mean"),
    ).reset_index()
    out["roi_pct"] = (out["profit"] / out["stake"] * 100).round(1)
    out["stake"] = out["stake"].round(2)
    out["profit"] = out["profit"].round(2)
    out["avg_clv"] = out["avg_clv"].round(1)
    return out.sort_values("profit", ascending=False)



def exacta_box_cost(n: int, unit: float) -> float:
    return n * max(n - 1, 0) * float(unit)


def trifecta_box_cost(n: int, unit: float) -> float:
    return n * max(n - 1, 0) * max(n - 2, 0) * float(unit)


def top_contenders_for_race(race_obj, max_rows: int = 6) -> pd.DataFrame:
    try:
        _odds, _factors, rankings, _shape, _call, _top, _greens, _yellows, _exacta = analyze_single_race(race_obj)
        cols = [
            "runner", "tier", "model_prob_pct", "expected_value_pct", "kelly_fraction_pct",
            "best_american_odds", "pace_engine_score", "factor_score"
        ]
        available = [c for c in cols if c in rankings.columns]
        return rankings[available].head(max_rows).copy()
    except Exception:
        return pd.DataFrame()


def build_ticket_lines(ticket_type: str, horses: list[str], key_horse: str | None = None) -> list[str]:
    if ticket_type == "WIN":
        return [f"WIN: {horses[0]}"]
    if ticket_type == "PLACE":
        return [f"PLACE: {horses[0]}"]
    if ticket_type == "SHOW":
        return [f"SHOW: {horses[0]}"]
    if ticket_type == "EXACTA BOX":
        return [f"EXACTA BOX: {', '.join(horses)}"]
    if ticket_type == "EXACTA KEY":
        underneath = [h for h in horses if h != key_horse]
        return [f"EXACTA KEY: {key_horse} over {', '.join(underneath)}"]
    if ticket_type == "TRIFECTA BOX":
        return [f"TRIFECTA BOX: {', '.join(horses)}"]
    if ticket_type == "TRIFECTA KEY":
        underneath = [h for h in horses if h != key_horse]
        return [f"TRIFECTA KEY: {key_horse} over/with {', '.join(underneath)}"]
    return ["PASS"]


def choose_bet_structure(row: pd.Series, contenders: pd.DataFrame, current_bankroll_value: float) -> dict:
    tier = str(row.get("Tier", "RED"))
    ev = float(row.get("EV %", 0))
    kelly = float(row.get("Kelly %", 0))
    grade = str(row.get("Play Grade", "PASS"))
    recommendation = str(row.get("Recommendation", "PASS"))
    race_num = int(row.get("Race #", 0))
    top_horse = str(row.get("Best Horse", ""))

    if recommendation == "PASS" or grade == "PASS" or contenders.empty:
        return {
            "Race #": race_num,
            "Race": row.get("Race", ""),
            "Post": row.get("Post", ""),
            "Ticket Type": "PASS",
            "Ticket Grade": "PASS",
            "Horses": "",
            "Key Horse": "",
            "Ticket Cost": 0.0,
            "Recommended Stake": 0.0,
            "Reason": "No qualifying edge.",
            "Ticket Lines": "PASS",
        }

    c = contenders.copy()
    c["model_prob_pct"] = pd.to_numeric(c.get("model_prob_pct", 0), errors="coerce").fillna(0)
    c["expected_value_pct"] = pd.to_numeric(c.get("expected_value_pct", 0), errors="coerce").fillna(0)
    c = c.sort_values(["model_prob_pct", "expected_value_pct"], ascending=False).reset_index(drop=True)

    horses = c["runner"].astype(str).tolist()
    top_prob = float(c.iloc[0]["model_prob_pct"])
    second_prob = float(c.iloc[1]["model_prob_pct"]) if len(c) > 1 else 0.0
    edge_gap = top_prob - second_prob

    race_cap = current_bankroll_value * (max_race_exposure_pct / 100)
    daily_cap = current_bankroll_value * (max_daily_exposure_pct / 100)

    base_win_size = recommended_bet_size(grade, kelly, current_bankroll_value)

    # 1. Clear standout = win, sometimes place/show fallback.
    if grade in ["A", "B"] and edge_gap >= min_win_edge_gap and ev >= min_b_ev:
        ticket_type = "WIN"
        stake = max(base_win_size, 0.0)
        if enable_place_show and grade == "B" and ev < min_a_ev:
            ticket_type = "PLACE"
            stake = round(base_win_size * 0.75, 2)
        lines = build_ticket_lines(ticket_type, [top_horse])
        return {
            "Race #": race_num,
            "Race": row.get("Race", ""),
            "Post": row.get("Post", ""),
            "Ticket Type": ticket_type,
            "Ticket Grade": grade,
            "Horses": top_horse,
            "Key Horse": top_horse,
            "Ticket Cost": stake,
            "Recommended Stake": stake,
            "Reason": f"Top horse has clear probability gap ({edge_gap:.1f} pts).",
            "Ticket Lines": " | ".join(lines),
        }

    # 2. Clustered top contenders = exacta box or exacta key.
    exacta_n = min(max_exacta_horses, max(2, min(len(horses), 4)))
    exacta_horses = horses[:exacta_n]
    exacta_cost = exacta_box_cost(len(exacta_horses), exacta_unit)

    if grade in ["A", "B"] and exacta_cost <= race_cap:
        if edge_gap >= (min_win_edge_gap / 2):
            ticket_type = "EXACTA KEY"
            # Key top over next contenders: cheaper than box
            key_horse = top_horse
            ticket_cost = max(len(exacta_horses) - 1, 0) * exacta_unit
            reason = "Top horse has some edge, but exacta offers better structure than pure win."
        else:
            ticket_type = "EXACTA BOX"
            key_horse = ""
            ticket_cost = exacta_cost
            reason = "Top contenders are clustered; box protects order uncertainty."
        lines = build_ticket_lines(ticket_type, exacta_horses, key_horse or None)
        return {
            "Race #": race_num,
            "Race": row.get("Race", ""),
            "Post": row.get("Post", ""),
            "Ticket Type": ticket_type,
            "Ticket Grade": grade,
            "Horses": ", ".join(exacta_horses),
            "Key Horse": key_horse,
            "Ticket Cost": round(ticket_cost, 2),
            "Recommended Stake": round(ticket_cost, 2),
            "Reason": reason,
            "Ticket Lines": " | ".join(lines),
        }

    # 3. C-grade or chaotic/clustered race = tiny trifecta if enabled and affordable.
    if enable_trifecta and len(horses) >= 3:
        tri_n = min(max_trifecta_horses, len(horses), 5)
        tri_horses = horses[:tri_n]
        tri_cost = trifecta_box_cost(len(tri_horses), trifecta_unit)
        tri_key_cost = max(len(tri_horses) - 1, 0) * max(len(tri_horses) - 2, 0) * trifecta_unit
        if grade in ["A", "B", "C"] and tri_key_cost <= race_cap * 0.75:
            ticket_type = "TRIFECTA KEY"
            key_horse = top_horse
            lines = build_ticket_lines(ticket_type, tri_horses, key_horse)
            return {
                "Race #": race_num,
                "Race": row.get("Race", ""),
                "Post": row.get("Post", ""),
                "Ticket Type": ticket_type,
                "Ticket Grade": grade,
                "Horses": ", ".join(tri_horses),
                "Key Horse": key_horse,
                "Ticket Cost": round(tri_key_cost, 2),
                "Recommended Stake": round(tri_key_cost, 2),
                "Reason": "Clustered contenders; tiny trifecta key offers upside with controlled cost.",
                "Ticket Lines": " | ".join(lines),
            }
        if grade == "C" and tri_cost <= race_cap * 0.5:
            ticket_type = "TRIFECTA BOX"
            lines = build_ticket_lines(ticket_type, tri_horses)
            return {
                "Race #": race_num,
                "Race": row.get("Race", ""),
                "Post": row.get("Post", ""),
                "Ticket Type": ticket_type,
                "Ticket Grade": grade,
                "Horses": ", ".join(tri_horses),
                "Key Horse": "",
                "Ticket Cost": round(tri_cost, 2),
                "Recommended Stake": round(tri_cost, 2),
                "Reason": "Small speculative structure only; no standout winner.",
                "Ticket Lines": " | ".join(lines),
            }

    # 4. If exotics are too expensive, downgrade to show/place or pass.
    if enable_place_show and grade in ["A", "B"] and base_win_size > 0:
        ticket_type = "SHOW" if grade == "B" else "PLACE"
        stake = round(min(base_win_size * 0.5, race_cap), 2)
        lines = build_ticket_lines(ticket_type, [top_horse])
        return {
            "Race #": race_num,
            "Race": row.get("Race", ""),
            "Post": row.get("Post", ""),
            "Ticket Type": ticket_type,
            "Ticket Grade": grade,
            "Horses": top_horse,
            "Key Horse": top_horse,
            "Ticket Cost": stake,
            "Recommended Stake": stake,
            "Reason": "Exotic structure exceeded risk cap; downgraded to conservative straight wager.",
            "Ticket Lines": " | ".join(lines),
        }

    return {
        "Race #": race_num,
        "Race": row.get("Race", ""),
        "Post": row.get("Post", ""),
        "Ticket Type": "PASS",
        "Ticket Grade": "PASS",
        "Horses": "",
        "Key Horse": "",
        "Ticket Cost": 0.0,
        "Recommended Stake": 0.0,
        "Reason": "No affordable structure under bankroll caps.",
        "Ticket Lines": "PASS",
    }


def build_bet_structure_board(recommendations_df: pd.DataFrame, current_bankroll_value: float) -> pd.DataFrame:
    if recommendations_df.empty:
        return pd.DataFrame()

    tickets = []
    race_lookup = {r.number: r for r in races}

    # Only build structures for top recommendation board, but include PASS rows for context.
    for _, row in recommendations_df.iterrows():
        race_num = int(row.get("Race #", 0))
        race_obj = race_lookup.get(race_num)
        if race_obj is None:
            continue
        contenders = top_contenders_for_race(race_obj)
        tickets.append(choose_bet_structure(row, contenders, current_bankroll_value))

    out = pd.DataFrame(tickets)
    if out.empty:
        return out

    # Enforce total daily exposure cap across suggested tickets.
    daily_cap = current_bankroll_value * (max_daily_exposure_pct / 100)
    total = out["Recommended Stake"].sum()
    if total > daily_cap and total > 0:
        scale = daily_cap / total
        out["Recommended Stake"] = (out["Recommended Stake"] * scale).round(2)
        out["Ticket Cost"] = out["Recommended Stake"]
        out["Reason"] = out["Reason"] + " Daily exposure cap scaled stake."

    return out


# Safe defaults for bankroll display. This prevents NameError if a prior calculation branch fails.
if "all_bets_for_bankroll" not in globals():
    all_bets_for_bankroll = load_bets()
if "current_bankroll_value" not in globals():
    current_bankroll_value = current_bankroll_from_bets(globals().get("starting_bankroll", globals().get("bankroll", 100.0)), all_bets_for_bankroll)
if "bankroll_status" not in globals() or "bankroll_css" not in globals():
    bankroll_status, bankroll_css = bankroll_health(globals().get("starting_bankroll", globals().get("bankroll", 100.0)), current_bankroll_value)
if "recommendations_df" in globals() and "apply_bankroll_engine" in globals():
    recommendations_df = apply_bankroll_engine(recommendations_df, current_bankroll_value)
if "bet_structure_df" not in globals() and "build_bet_structure_board" in globals() and "recommendations_df" in globals():
    bet_structure_df = build_bet_structure_board(recommendations_df, current_bankroll_value)
if "recommendations_df" not in globals():
    try:
        recommendations_df = build_auto_recommendations(summary_df)
    except Exception:
        recommendations_df = pd.DataFrame()

if "all_bets_for_bankroll" not in globals():
    all_bets_for_bankroll = load_bets()

if "current_bankroll_value" not in globals():
    current_bankroll_value = current_bankroll_from_bets(globals().get("starting_bankroll", globals().get("bankroll", 100.0)), all_bets_for_bankroll)

try:
    recommendations_df = apply_bankroll_engine(recommendations_df, current_bankroll_value)
except Exception:
    pass

if "bet_structure_df" not in globals():
    try:
        bet_structure_df = build_bet_structure_board(recommendations_df, current_bankroll_value)
    except Exception:
        bet_structure_df = pd.DataFrame()

try:
    timing_board_df = build_timing_board(summary_df, recommendations_df)
except Exception:
    timing_board_df = pd.DataFrame()

st.markdown(
    f"<div class='bankroll-card {bankroll_css}'>"
    f"<b>Bankroll Engine:</b> {bankroll_status}<br>"
    f"Starting bankroll: ${globals().get('starting_bankroll', globals().get('bankroll', 100.0)):.2f} | Current bankroll: ${current_bankroll_value:.2f}<br>"
    f"Daily exposure cap: {globals().get('max_daily_exposure_pct', 10)}% | Race cap: {globals().get('max_race_exposure_pct', 4)}% | Stop-loss: {globals().get('daily_stop_loss_pct', 10)}%"
    f"</div>",
    unsafe_allow_html=True,
)


def parse_post_time_minutes(post_time: str) -> int | None:
    """
    Convert post time like '6:57 PM ET' into minutes from now.
    Uses today's selected race_date and local app timezone. This is a practical approximation for race-day timing.
    """
    try:
        txt = str(post_time or "").strip()
        if not txt:
            return None
        m = re.search(r"(\d{1,2}):(\d{2})\s*([AP]M)", txt, re.I)
        if not m:
            return None
        hour = int(m.group(1))
        minute = int(m.group(2))
        ampm = m.group(3).upper()
        if ampm == "PM" and hour != 12:
            hour += 12
        if ampm == "AM" and hour == 12:
            hour = 0
        target = datetime.combine(race_date, datetime.min.time()).replace(hour=hour, minute=minute)
        delta = target - datetime.now()
        return int(delta.total_seconds() // 60)
    except Exception:
        return None


def latest_snapshot_age_minutes() -> float | None:
    try:
        last_scan = st.session_state.get("last_scan", 0)
        if not last_scan:
            return None
        return max((time.time() - float(last_scan)) / 60, 0)
    except Exception:
        return None


def timing_action(minutes_to_post, steam_signal: str, tier: str, recommendation: str) -> tuple[str, str, str]:
    """
    Returns: action, css class, reason
    """
    if minutes_to_post is None:
        if recommendation == "PASS":
            return "PASS", "timing-pass", "No post time available and no bet signal."
        return "WATCH", "timing-wait", "No post time available; watch but do not rush."

    if minutes_to_post < 0:
        return "CLOSED / POSTED", "timing-pass", "Race appears to be past post time."
    if recommendation == "PASS":
        return "PASS", "timing-pass", "No qualifying edge."
    if minutes_to_post > watch_window_start:
        return "WAIT", "timing-wait", f"Too early. Start serious watch inside {watch_window_start} minutes."
    if prime_window_end <= minutes_to_post <= prime_window_start:
        if steam_signal in ["STRONG STEAM", "STEAM"] and tier in ["GREEN+", "GREEN"]:
            return "BET NOW", "timing-now", "Prime window plus steam confirmation."
        if tier in ["GREEN+", "GREEN"]:
            return "BET / CONFIRM ODDS", "timing-now", "Prime window and qualifying model signal."
        return "SMALL ONLY", "timing-soon", "Prime window but signal is not elite."
    if minutes_to_post < prime_window_end:
        return "LAST CALL", "timing-soon", "Very late. Bet only if odds are still acceptable."
    return "WATCH", "timing-wait", "Approaching prime betting window."


def build_timing_board(summary_df: pd.DataFrame, recommendations_df: pd.DataFrame) -> pd.DataFrame:
    if summary_df is None or summary_df.empty:
        return pd.DataFrame()

    if recommendations_df is None:
        recommendations_df = pd.DataFrame()

    rec_cols = ["Race #", "Recommendation", "Play Grade", "Bet Type", "Bankroll Bet $", "Suggested Bet $"]
    rec = recommendations_df[[c for c in rec_cols if c in recommendations_df.columns]].copy() if not recommendations_df.empty else pd.DataFrame()

    df = summary_df.copy()
    if not rec.empty and "Race #" in rec.columns:
        df = df.merge(rec, on="Race #", how="left", suffixes=("", "_rec"))

    for col, default in {
        "Recommendation": "PASS",
        "Play Grade": "PASS",
        "Bet Type": "PASS",
        "Bankroll Bet $": 0.0,
        "Suggested Bet $": 0.0,
        "Steam Signal": "STABLE",
    }.items():
        if col not in df.columns:
            df[col] = default

    df["Minutes To Post"] = df["Post"].apply(parse_post_time_minutes)
    df["Odds Snapshot Age Min"] = latest_snapshot_age_minutes()
    df["Odds Freshness"] = df["Odds Snapshot Age Min"].apply(
        lambda x: "UNKNOWN" if x is None else ("STALE" if x > stale_odds_minutes else "FRESH")
    )

    actions = df.apply(
        lambda row: timing_action(
            row.get("Minutes To Post"),
            str(row.get("Steam Signal", "STABLE")),
            str(row.get("Tier", "")),
            str(row.get("Recommendation", "PASS")),
        ),
        axis=1,
    )
    df["Timing Action"] = actions.apply(lambda x: x[0])
    df["Timing CSS"] = actions.apply(lambda x: x[1])
    df["Timing Reason"] = actions.apply(lambda x: x[2])

    # Timing score favors current actionable races, steam, A/B grades, and fresh data.
    def score(row):
        s = 0
        if row["Timing Action"] == "BET NOW":
            s += 100
        elif row["Timing Action"] == "BET / CONFIRM ODDS":
            s += 85
        elif row["Timing Action"] == "LAST CALL":
            s += 70
        elif row["Timing Action"] == "WATCH":
            s += 45
        if row.get("Steam Signal") == "STRONG STEAM":
            s += 15
        elif row.get("Steam Signal") == "STEAM":
            s += 8
        if row.get("Play Grade") == "A":
            s += 12
        elif row.get("Play Grade") == "B":
            s += 6
        if row.get("Odds Freshness") == "STALE":
            s -= 20
        return s

    df["Timing Score"] = df.apply(score, axis=1)
    return df.sort_values(["Timing Score", "Race #"], ascending=[False, True]).reset_index(drop=True)


# Final safety defaults before tabs render.
if "recommendations_df" not in globals():
    try:
        recommendations_df = build_auto_recommendations(summary_df)
    except Exception:
        recommendations_df = pd.DataFrame()

if "all_bets_for_bankroll" not in globals():
    all_bets_for_bankroll = load_bets()

if "current_bankroll_value" not in globals():
    current_bankroll_value = current_bankroll_from_bets(globals().get("starting_bankroll", globals().get("bankroll", 100.0)), all_bets_for_bankroll)

if "bankroll_status" not in globals() or "bankroll_css" not in globals():
    bankroll_status, bankroll_css = bankroll_health(globals().get("starting_bankroll", globals().get("bankroll", 100.0)), current_bankroll_value)

if "bet_structure_df" not in globals():
    try:
        bet_structure_df = build_bet_structure_board(recommendations_df, current_bankroll_value)
    except Exception:
        bet_structure_df = pd.DataFrame()

if "timing_board_df" not in globals():
    try:
        timing_board_df = build_timing_board(summary_df, recommendations_df)
    except Exception:
        timing_board_df = pd.DataFrame()


tabs = st.tabs(["Race Day Alerts", "Today's Plays", "Timing Engine", "Bet Structures", "Daily Summary", "Steam Board", "Best Horses", "Sharp Alerts", "Reddit Signals", "Race Detail", "Alerts", "Odds History", "Bet Ledger", "ROI Dashboard", "Bankroll Dashboard"])

with tabs[0]:
    st.subheader("Daily card summary")
    green_races = summary_df[summary_df["Tier"].isin(["GREEN+", "GREEN"])]
    pass_races = summary_df[summary_df["Final Call"].str.contains("PASS", na=False)]

    a,b,c,d = st.columns(4)
    a.metric("Races", len(summary_df))
    b.metric("Playable races", len(green_races))
    c.metric("Pass races", len(pass_races))
    d.metric("Best EV", f"{summary_df['EV %'].max():.1f}%")

    if use_reddit and "Public Hype" in summary_df:
        most_hyped = summary_df.sort_values("Public Hype", ascending=False).head(1)
        if len(most_hyped):
            st.info(f"Most public-hyped top pick: Race {int(most_hyped.iloc[0]['Race #'])} - {most_hyped.iloc[0]['Best Horse']} ({most_hyped.iloc[0]['Public Hype']:.0f}% hype)")

    if len(green_races):
        st.success(f"Top playable race: Race {int(green_races.iloc[0]['Race #'])} - {green_races.iloc[0]['Best Horse']} ({green_races.iloc[0]['Tier']})")
    else:
        st.warning("No GREEN/GREEN+ race found. Best move may be to pass or only play tiny exactas.")

    if alert_sharp_low_hype and "Sharp Low-Hype Alert" in summary_df.columns:
        sharp_alerts = summary_df[summary_df["Sharp Low-Hype Alert"] == 1]
        if len(sharp_alerts):
            st.markdown("### Sharp value + low hype alerts")
            for _, arow in sharp_alerts.iterrows():
                st.markdown(
                    f"<div class='sharp-alert'><div class='alert-title'>ACTIONABLE ALERT</div>"
                    f"Race {int(arow['Race #'])}: {arow['Best Horse']} - {arow['Tier']}<br>"
                    f"EV {arow['EV %']}% | Hype {arow.get('Public Hype', 0)}% | Odds {arow['Odds']}<br>"
                    f"{arow['Sharp/Public']}</div>",
                    unsafe_allow_html=True,
                )

    if alert_public_traps and "Public Trap Alert" in summary_df.columns:
        trap_alerts = summary_df[summary_df["Public Trap Alert"] == 1]
        if len(trap_alerts):
            st.markdown("### Public trap / fade-risk alerts")
            for _, trow in trap_alerts.iterrows():
                st.markdown(
                    f"<div class='trap-alert'><div class='alert-title'>FADE-RISK ALERT</div>"
                    f"Race {int(trow['Race #'])}: {trow['Best Horse']}<br>"
                    f"Hype {trow.get('Public Hype', 0)}% | Tier {trow['Tier']}<br>"
                    f"{trow['Sharp/Public']}</div>",
                    unsafe_allow_html=True,
                )

    def style_summary(row):
        tier = row["Tier"]
        if tier == "GREEN+":
            return ["background-color:#0b6b28;color:white;font-weight:bold"] * len(row)
        if tier == "GREEN":
            return ["background-color:#d4edda;color:#155724;font-weight:bold"] * len(row)
        if tier == "YELLOW":
            return ["background-color:#fff3cd;color:#856404;font-weight:bold"] * len(row)
        return ["background-color:#f8d7da;color:#721c24;font-weight:bold"] * len(row)

    st.dataframe(summary_df.style.apply(style_summary, axis=1), use_container_width=True, hide_index=True)
    st.download_button("Download daily summary CSV", summary_df.to_csv(index=False).encode("utf-8"), "daily_summary.csv", "text/csv")

with tabs[5]:
    st.subheader("Steam / odds movement board")
    st.caption("Negative odds move = odds shortened = steam. Positive odds move = drift.")
    steam_counts = summary_df["Steam Signal"].value_counts() if "Steam Signal" in summary_df.columns else pd.Series(dtype=int)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Strong steam", int(steam_counts.get("STRONG STEAM", 0)))
    c2.metric("Steam", int(steam_counts.get("STEAM", 0)))
    c3.metric("Drift", int(steam_counts.get("DRIFT", 0)))
    c4.metric("Stable", int(steam_counts.get("STABLE", 0)))

    if "Odds Move %" not in summary_df.columns:
        summary_df = enrich_summary_with_steam(summary_df)

    for _, row in summary_df.sort_values("Odds Move %").iterrows():
        css = row.get("Steam CSS", "stable")
        st.markdown(
            f"<div class='steam-card'><span class='{css}'>{row.get('Steam Signal','STABLE')} {row.get('Odds Move %',0)}%</span> "
            f"<b>Race {int(row['Race #'])}: {row['Best Horse']}</b> - {row['Tier']} - EV {row['EV %']}% - Odds {row['Odds']}<br>"
            f"<span class='small-muted'>{row['Race']} - {row['Best Play']}</span></div>",
            unsafe_allow_html=True,
        )

    steam_cols = ["Race #", "Race", "Best Horse", "Tier", "Best Play", "EV %", "Odds", "Steam Signal", "Odds Move %", "Sharp/Public", "Public Hype"]
    st.dataframe(summary_df[[c for c in steam_cols if c in summary_df.columns]], use_container_width=True, hide_index=True)

with tabs[6]:
    st.subheader("Locked-in best horses per race")
    st.caption("Phone-friendly view: best horse, confidence tier, suggested action, and Reddit overlay.")

    for _, row in summary_df.iterrows():
        tier = row["Tier"]
        css = {"GREEN+":"greenplus","GREEN":"green","YELLOW":"yellow","RED":"red"}.get(tier, "gray")
        signal = row.get("Sharp/Public", "Model only")
        if "Sharp value" in signal:
            chip = f"<span class='sharp-chip'>{signal}</span>"
        elif "trap" in signal:
            chip = f"<span class='fade-chip'>{signal}</span>"
        else:
            chip = f"<span class='reddit-chip'>{signal}</span>"
        html = (
            f"<div class='summary-card'>"
            f"<div class='{css}'>Race {int(row['Race #'])} - <span class='big-horse'>{row['Best Horse']}</span> - {tier}</div>"
            f"<div><b>Action:</b> {row['Best Play']}</div>"
            f"<div><b>Final Call:</b> {row['Final Call']}</div>"
            f"<div><b>EV:</b> {row['EV %']}% | <b>Kelly:</b> {row['Kelly %']}% | <b>Odds:</b> {row['Odds']}</div>"
            f"<div><b>Reddit:</b> {row.get('Reddit','Off / none')} | <b>Mentions:</b> {row.get('Mentions',0)} | <b>Hype:</b> {row.get('Public Hype',0)}%</div>"
            f"<div><b>Steam:</b> <span class='{row.get('Steam CSS','stable')}'>{row.get('Steam Signal','STABLE')} ({row.get('Odds Move %',0)}%)</span></div>"
            f"<div>{chip}</div>"
            f"<div><b>Pace:</b> {row['Pace']} | <b>Bias:</b> {row['Bias']}</div>"
            f"<div class='small-muted'>{row['Race']} - Post {row['Post']}</div>"
            f"</div>"
        )
        st.markdown(html, unsafe_allow_html=True)

with tabs[7]:
    st.subheader("Sharp value alert board")
    if "Sharp Low-Hype Alert" not in summary_df.columns:
        st.info("Run a scan first.")
    else:
        sharp_alerts = summary_df[summary_df["Sharp Low-Hype Alert"] == 1]
        trap_alerts = summary_df[summary_df["Public Trap Alert"] == 1]
        c1, c2 = st.columns(2)
        c1.metric("Sharp low-hype alerts", len(sharp_alerts))
        c2.metric("Public trap alerts", len(trap_alerts))
        if len(sharp_alerts):
            st.markdown("### Best actionable alerts")
            st.dataframe(sharp_alerts[["Race #", "Best Horse", "Tier", "Best Play", "EV %", "Kelly %", "Odds", "Public Hype", "Sharp/Public"]], use_container_width=True, hide_index=True)
        if len(trap_alerts):
            st.markdown("### Fade-risk alerts")
            st.dataframe(trap_alerts[["Race #", "Best Horse", "Tier", "EV %", "Odds", "Public Hype", "Sharp/Public"]], use_container_width=True, hide_index=True)
        if not len(sharp_alerts) and not len(trap_alerts):
            st.info("No sharp/public alerts found yet. Try enabling Reddit or lowering the low-hype threshold.")

with tabs[8]:
    st.subheader("Reddit signal board")
    if not use_reddit:
        st.info("Turn on 'Enable Reddit layer' in the sidebar.")
    elif not has_reddit_credentials():
        st.warning("Reddit credentials missing. Add REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, and REDDIT_USER_AGENT in Streamlit Secrets.")
    else:
        st.dataframe(summary_df[["Race #", "Best Horse", "Tier", "Reddit", "Mentions", "Public Hype", "Sharp/Public"]], use_container_width=True, hide_index=True)
        traps = summary_df[summary_df["Sharp/Public"].str.contains("trap", case=False, na=False)]
        sharp = summary_df[summary_df["Sharp/Public"].str.contains("Sharp value", case=False, na=False)]
        c1,c2 = st.columns(2)
        c1.metric("Sharp low-buzz spots", len(sharp))
        c2.metric("Public trap risks", len(traps))

with tabs[9]:
    race_map = {f"Race {r.number} - {r.name} - {r.post_time}": r for r in races}
    selected = st.selectbox("Select race", list(race_map))
    race = race_map[selected]

    odds, factors, rankings, shape, call, top, greens, yellows, exacta, reddit_df = analyze_single_race(race)

    st.markdown(f"<div class='call'>FINAL CALL: {call}</div>", unsafe_allow_html=True)
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Pace shape", shape["shape"])
    c2.metric("Bias", shape["bias"])
    c3.metric("Volatility", shape["volatility"])
    c4.metric("Speed pressure", f"{shape['speed_pressure']:.0%}")

    css_map = {"GREEN+":"greenplus","GREEN":"green","YELLOW":"yellow","RED":"red","GRAY":"gray"}
    for _, r in rankings.iterrows():
        st.markdown(
            f"<div class='{css_map.get(r['tier'], 'gray')}'>{r['runner']} - {r['confidence']} - EV {r['expected_value_pct']:.1f}% - Kelly {r['kelly_fraction_pct']:.1f}% - Move {r.get('movement_flag','STABLE')} {r.get('odds_change_pct_pct',0):.1f}% - Reddit {r.get('reddit_signal','Off / none')} - {r.get('sharp_public_signal','Model only')}</div>",
            unsafe_allow_html=True,
        )

    board_cols = [
        "runner","tier","movement_flag","odds_change_pct_pct","best_american_odds","market_fair_prob_pct","model_prob_pct",
        "edge_prob_pct","expected_value_pct","kelly_fraction_pct","pace_engine_score","factor_score",
        "mentions","avg_sentiment","public_hype","reddit_signal","sharp_public_signal","books_seen"
    ]
    available = [c for c in board_cols if c in rankings.columns]
    st.dataframe(rankings[available], use_container_width=True, hide_index=True)

    active = rankings[~rankings["scratched"]]
    win = active[active["tier"].isin(["GREEN+", "GREEN"])].head(3).copy()
    if win.empty:
        win = active.head(1).copy()
    win["capped_bet"] = (win["kelly_fraction"] * bankroll * kelly_mult).clip(upper=bankroll * max_win_pct).round(2)

    exacta_horses = exacta["runner"].tolist()
    trifecta = active.sort_values(["model_prob", "expected_value"], ascending=False).head(min(5, len(active)))
    trifecta_horses = trifecta["runner"].tolist()

    x,y,z = st.columns(3)
    with x:
        st.markdown("### Win candidates")
        st.dataframe(win[["runner","tier","best_american_odds","expected_value_pct","capped_bet"]], use_container_width=True, hide_index=True)
    with y:
        st.markdown("### Exacta box")
        st.write(", ".join(exacta_horses))
        st.metric("Cost", f"${len(exacta_horses)*max(len(exacta_horses)-1,0)*unit:.2f}")
        with st.expander("Legs"):
            st.write(exacta_legs(exacta_horses))
    with z:
        st.markdown("### Trifecta box")
        st.write(", ".join(trifecta_horses))
        st.metric("Combos", trifecta_count(len(trifecta_horses)))

with tabs[10]:
    st.subheader("Alert log")
    st.dataframe(load_alerts(200), use_container_width=True, hide_index=True)

with tabs[11]:
    st.subheader("Odds history")
    race_map2 = {f"Race {r.number} - {r.name}": r for r in races}
    r2 = st.selectbox("Odds history race", list(race_map2), key="hist_race")
    hist_race = race_map2[r2]
    snaps = load_snapshots(hist_race.race_id)
    if snaps.empty:
        st.info("No snapshots yet. Scan the card first.")
    else:
        st.dataframe(snaps, use_container_width=True, hide_index=True)
        best = snaps.groupby(["ts","runner"])["american_odds"].max().reset_index()
        pivot = best.pivot(index="ts", columns="runner", values="american_odds")
        st.line_chart(pivot)

with tabs[10]:
    st.subheader("Bet ledger with CLV")
    race_names = {f"Race {r.number} {r.name}": r for r in races}
    race_label = st.selectbox("Race for bet", list(race_names), key="bet_race")
    br = race_names[race_label]
    bet_type = st.selectbox("Bet type", ["Win","Place","Show","Exacta Box","Exacta Key","Trifecta Box","Trifecta Key","Pass"])
    horses = st.text_input("Horse(s)")
    stake = st.number_input("Stake", min_value=0.0, value=1.0, step=1.0)
    odds_taken = st.number_input("Odds taken American", value=0, step=10)
    closing_odds = st.number_input("Closing odds American", value=0, step=10)
    tier = st.selectbox("Tier", ["GREEN+","GREEN","YELLOW","RED","Manual"])
    result = st.selectbox("Result", ["Planned","Pending","Won","Lost"])
    payout = st.number_input("Payout", min_value=0.0, value=0.0, step=1.0)

    if st.button("Save bet"):
        save_bet({
            "date": str(race_date),
            "track": br.track,
            "race_id": br.race_id,
            "race_name": br.name,
            "bet_type": bet_type,
            "horses": horses,
            "stake": stake,
            "odds_taken": int(odds_taken),
            "closing_odds": int(closing_odds),
            "clv_points": int(closing_odds) - int(odds_taken) if closing_odds else 0,
            "tier": tier,
            "result": result,
            "payout": payout,
            "profit": payout - stake if result in ["Won","Lost"] else 0,
        })
        st.success("Bet saved.")

    bets = load_bets()
    if bets.empty:
        st.info("No bets yet.")
    else:
        st.dataframe(bets, use_container_width=True, hide_index=True)
        settled = bets[bets["result"].isin(["Won","Lost"])]
        total = settled["stake"].sum()
        profit = settled["profit"].sum()
        roi = profit / total * 100 if total else 0
        a,b,c = st.columns(3)
        a.metric("Settled stake", f"${total:.2f}")
        b.metric("Profit", f"${profit:.2f}")
        c.metric("ROI", f"{roi:.1f}%")
        if not settled.empty:
            tier_df = settled.groupby("tier").agg(bets=("id","count"), stake=("stake","sum"), profit=("profit","sum"), avg_clv=("clv_points","mean")).reset_index()
            tier_df["roi_pct"] = tier_df["profit"] / tier_df["stake"] * 100
            st.markdown("### ROI by tier")
            st.dataframe(tier_df, use_container_width=True, hide_index=True)

if mode == "Auto Real Data":
    st.warning("Auto Real Data uses public entries and morning-line odds when available. These are not guaranteed live tote odds. Verify final entries, scratches, and odds before betting.")
else:
    st.warning("Demo data is for testing only. Reddit is noisy and should be treated as a small sentiment overlay, not a primary betting signal.")


# Auto-rerun heartbeat for race-day mode.
if auto_scan and auto_rerun:
    time.sleep(1)
    if time.time() - st.session_state.last_scan >= scan_seconds:
        st.rerun()


with tabs[14]:
    st.subheader("Bankroll Dashboard")
    bets = load_bets()
    current_bankroll_value = current_bankroll_from_bets(starting_bankroll, bets)
    bankroll_status, bankroll_css = bankroll_health(globals().get("starting_bankroll", globals().get("bankroll", 100.0)), current_bankroll_value)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Starting bankroll", f"${starting_bankroll:.2f}")
    c2.metric("Current bankroll", f"${current_bankroll_value:.2f}")
    c3.metric("Net change", f"${current_bankroll_value - starting_bankroll:.2f}")
    c4.metric("Status", bankroll_status)

    stop_loss_amount = starting_bankroll * (daily_stop_loss_pct / 100)
    daily_cap = current_bankroll_value * (max_daily_exposure_pct / 100)
    race_cap = current_bankroll_value * (max_race_exposure_pct / 100)

    st.markdown("### Risk limits")
    r1, r2, r3 = st.columns(3)
    r1.metric("Daily stop-loss", f"${stop_loss_amount:.2f}")
    r2.metric("Max daily exposure", f"${daily_cap:.2f}")
    r3.metric("Max race exposure", f"${race_cap:.2f}")

    st.markdown("### Recommended sizing by play grade")
    sizing_rows = pd.DataFrame([
        {"Play Grade": "A", "Multiplier": a_play_multiplier, "Use Case": "Best edge / strongest confirmation"},
        {"Play Grade": "B", "Multiplier": b_play_multiplier, "Use Case": "Good edge / smaller position"},
        {"Play Grade": "C", "Multiplier": c_play_multiplier, "Use Case": "Tiny action only / exotic support"},
        {"Play Grade": "PASS", "Multiplier": 0.0, "Use Case": "No bet"},
    ])
    st.dataframe(sizing_rows, use_container_width=True, hide_index=True)

    st.markdown("### Bankroll-sized recommendations")
    if "recommendations_df" in globals() and not recommendations_df.empty:
        cols = ["Race #", "Race", "Best Horse", "Play Grade", "Recommendation", "Bet Type", "EV %", "Kelly %", "Bankroll Bet $", "Sizing Note"]
        st.dataframe(recommendations_df[[c for c in cols if c in recommendations_df.columns]], use_container_width=True, hide_index=True)
    else:
        st.info("No recommendations available yet.")

    st.markdown("### Bankroll history proxy")
    if bets.empty:
        st.info("No bet history yet.")
    else:
        settled = bets[bets["result"].isin(["Won", "Lost"])].copy()
        if settled.empty:
            st.info("No settled bets yet.")
        else:
            settled = settled.sort_values("id")
            settled["running_profit"] = settled["profit"].cumsum()
            settled["estimated_bankroll"] = starting_bankroll + settled["running_profit"]
            chart_df = settled.set_index("id")[["estimated_bankroll"]]
            st.line_chart(chart_df)
            st.dataframe(settled[["id", "date", "race_name", "horses", "tier", "stake", "result", "profit", "estimated_bankroll"]], use_container_width=True, hide_index=True)
