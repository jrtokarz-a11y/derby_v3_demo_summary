
from __future__ import annotations
from datetime import date, datetime
import os
import time

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from providers import get_provider
from database import init_db, save_odds_snapshot, load_previous_best_odds, load_alerts, save_bet, load_bets, load_snapshots
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
</style>
""", unsafe_allow_html=True)

st.title("Derby V3.1 - Demo + Smart Reddit Layer")
st.caption("Demo-only race model plus optional Reddit sentiment, public hype, fade risk, and sharp/public divergence.")

with st.sidebar:
    st.header("Demo mode")
    st.markdown("**Data source: Demo only**")
    track = st.text_input("Track", "Churchill Downs")
    race_date = st.date_input("Race date", value=date(2026, 5, 2))

    st.header("Smart Reddit")
    use_reddit = st.checkbox("Enable Reddit layer", value=False)
    subreddit_text = st.text_input("Subreddits", "horseracing,sportsbook,KentuckyDerby")
    reddit_limit = st.slider("Posts per subreddit", 25, 250, 75, 25)
    reddit_model_boost = st.slider("Reddit overlay influence", 0.0, 0.10, 0.03, 0.01)
    alert_sharp_low_hype = st.checkbox("Alert: sharp value + low hype", value=True)
    alert_public_traps = st.checkbox("Alert: public trap / fade risk", value=True)
    low_hype_threshold = st.slider("Low hype threshold %", 0, 60, 35, 5)

    st.header("Daily scan")
    auto_scan = st.checkbox("Auto-scan full card", False)
    scan_seconds = st.slider("Scan every seconds", 15, 300, 60, 15)
    manual_scan = st.button("Scan full card now")

    st.header("Bankroll")
    bankroll = st.number_input("Bankroll", min_value=0.0, value=100.0, step=10.0)
    unit = st.number_input("Exotic unit", min_value=0.10, value=1.0, step=.5)
    kelly_mult = st.slider("Kelly fraction", .05, 1.0, .25, .05)
    max_win_pct = st.slider("Max win bet % bankroll", .005, .10, .03, .005)

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

provider = get_provider("Demo")

try:
    races = provider.races(track, str(race_date))
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
            })
    return pd.DataFrame(rows)

if use_reddit and not has_reddit_credentials():
    st.warning("Reddit layer is ON, but Reddit credentials are missing. Add them in Streamlit Secrets or turn Reddit OFF.")

if auto_scan:
    now = time.time()
    if "last_scan" not in st.session_state:
        st.session_state.last_scan = 0
    if now - st.session_state.last_scan >= scan_seconds:
        st.session_state.last_scan = now
        st.session_state["daily_summary"] = build_daily_summary()
        st.rerun()

if manual_scan or "daily_summary" not in st.session_state:
    st.session_state["daily_summary"] = build_daily_summary()

summary_df = st.session_state["daily_summary"]

tabs = st.tabs(["Daily Summary", "Best Horses", "Sharp Alerts", "Reddit Signals", "Race Detail", "Alerts", "Odds History", "Bet Ledger / ROI"])

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

with tabs[1]:
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
            f"<div>{chip}</div>"
            f"<div><b>Pace:</b> {row['Pace']} | <b>Bias:</b> {row['Bias']}</div>"
            f"<div class='small-muted'>{row['Race']} - Post {row['Post']}</div>"
            f"</div>"
        )
        st.markdown(html, unsafe_allow_html=True)

with tabs[2]:
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

with tabs[3]:
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

with tabs[4]:
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
            f"<div class='{css_map.get(r['tier'], 'gray')}'>{r['runner']} - {r['confidence']} - EV {r['expected_value_pct']:.1f}% - Kelly {r['kelly_fraction_pct']:.1f}% - Reddit {r.get('reddit_signal','Off / none')} - {r.get('sharp_public_signal','Model only')}</div>",
            unsafe_allow_html=True,
        )

    board_cols = [
        "runner","tier","movement_flag","best_american_odds","market_fair_prob_pct","model_prob_pct",
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

with tabs[5]:
    st.subheader("Alert log")
    st.dataframe(load_alerts(200), use_container_width=True, hide_index=True)

with tabs[6]:
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

with tabs[7]:
    st.subheader("Bet ledger with CLV")
    race_names = {f"Race {r.number} {r.name}": r for r in races}
    race_label = st.selectbox("Race for bet", list(race_names), key="bet_race")
    br = race_names[race_label]
    bet_type = st.selectbox("Bet type", ["Win","Place","Show","Exacta Box","Trifecta Box","Pass"])
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

st.warning("Demo data is for testing only. Reddit is noisy and should be treated as a small sentiment overlay, not a primary betting signal.")
