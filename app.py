
from __future__ import annotations
from datetime import date, datetime
import time

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from providers import get_provider
from database import init_db, save_odds_snapshot, load_previous_best_odds, load_alerts, save_bet, load_bets, load_snapshots
from model import analyze, final_call, exacta_legs, trifecta_count

load_dotenv()
init_db()

st.set_page_config(page_title="Derby V3 Demo Summary", page_icon="🏇", layout="wide")

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
</style>
""", unsafe_allow_html=True)

st.title("Derby V3 - Demo Mode + Daily Summary")
st.caption("Phone-friendly best horses per race, daily card summary, pace engine, alerts, and ROI tracking.")

with st.sidebar:
    st.header("Demo mode")
    st.markdown("**Data source: Demo only**")
    track = st.text_input("Track", "Churchill Downs")
    race_date = st.date_input("Race date", value=date(2026, 5, 2))

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

def analyze_single_race(race):
    odds = provider.odds(race.race_id)
    factors = provider.factors(race.race_id)
    prev = load_previous_best_odds(race.race_id)
    rankings, shape = analyze(odds, factors, prev, weights, blend)
    call = final_call(rankings, shape)
    top = rankings.iloc[0] if len(rankings) else None
    greens = rankings[rankings["tier"].isin(["GREEN+", "GREEN"])]
    yellows = rankings[rankings["tier"] == "YELLOW"]
    active = rankings[~rankings["scratched"]]
    exacta = active.sort_values(["model_prob", "expected_value"], ascending=False).head(min(4, len(active)))
    return odds, factors, rankings, shape, call, top, greens, yellows, exacta

def build_daily_summary():
    rows = []
    ts = datetime.now().isoformat(timespec="seconds")
    for race in races:
        odds, factors, rankings, shape, call, top, greens, yellows, exacta = analyze_single_race(race)
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
            })
    return pd.DataFrame(rows)

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

tabs = st.tabs(["Daily Summary", "Best Horses", "Race Detail", "Alerts", "Odds History", "Bet Ledger / ROI"])

with tabs[0]:
    st.subheader("Daily card summary")
    green_races = summary_df[summary_df["Tier"].isin(["GREEN+", "GREEN"])]
    pass_races = summary_df[summary_df["Final Call"].str.contains("PASS", na=False)]

    a,b,c,d = st.columns(4)
    a.metric("Races", len(summary_df))
    b.metric("Playable races", len(green_races))
    c.metric("Pass races", len(pass_races))
    d.metric("Best EV", f"{summary_df['EV %'].max():.1f}%")

    if len(green_races):
        st.success(f"Top playable race: Race {int(green_races.iloc[0]['Race #'])} - {green_races.iloc[0]['Best Horse']} ({green_races.iloc[0]['Tier']})")
    else:
        st.warning("No GREEN/GREEN+ race found. Best move may be to pass or only play tiny exactas.")

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
    st.caption("Phone-friendly view: best horse, confidence tier, and suggested action for every race.")

    for _, row in summary_df.iterrows():
        tier = row["Tier"]
        css = {"GREEN+":"greenplus","GREEN":"green","YELLOW":"yellow","RED":"red"}.get(tier, "gray")
        html = (
            f"<div class='summary-card'>"
            f"<div class='{css}'>Race {int(row['Race #'])} - <span class='big-horse'>{row['Best Horse']}</span> - {tier}</div>"
            f"<div><b>Action:</b> {row['Best Play']}</div>"
            f"<div><b>Final Call:</b> {row['Final Call']}</div>"
            f"<div><b>EV:</b> {row['EV %']}% | <b>Kelly:</b> {row['Kelly %']}% | <b>Odds:</b> {row['Odds']}</div>"
            f"<div><b>Pace:</b> {row['Pace']} | <b>Bias:</b> {row['Bias']}</div>"
            f"<div class='small-muted'>{row['Race']} - Post {row['Post']}</div>"
            f"</div>"
        )
        st.markdown(html, unsafe_allow_html=True)

with tabs[2]:
    race_map = {f"Race {r.number} - {r.name} - {r.post_time}": r for r in races}
    selected = st.selectbox("Select race", list(race_map))
    race = race_map[selected]

    odds, factors, rankings, shape, call, top, greens, yellows, exacta = analyze_single_race(race)

    st.markdown(f"<div class='call'>FINAL CALL: {call}</div>", unsafe_allow_html=True)
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Pace shape", shape["shape"])
    c2.metric("Bias", shape["bias"])
    c3.metric("Volatility", shape["volatility"])
    c4.metric("Speed pressure", f"{shape['speed_pressure']:.0%}")

    css_map = {"GREEN+":"greenplus","GREEN":"green","YELLOW":"yellow","RED":"red","GRAY":"gray"}
    for _, r in rankings.iterrows():
        st.markdown(
            f"<div class='{css_map.get(r['tier'], 'gray')}'>{r['runner']} - {r['confidence']} - EV {r['expected_value_pct']:.1f}% - Kelly {r['kelly_fraction_pct']:.1f}% - {r['movement_flag']}</div>",
            unsafe_allow_html=True,
        )

    board_cols = ["runner","tier","movement_flag","best_american_odds","market_fair_prob_pct","model_prob_pct","edge_prob_pct","expected_value_pct","kelly_fraction_pct","pace_engine_score","factor_score","books_seen"]
    st.dataframe(rankings[board_cols], use_container_width=True, hide_index=True)

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

with tabs[3]:
    st.subheader("Alert log")
    st.dataframe(load_alerts(200), use_container_width=True, hide_index=True)

with tabs[4]:
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

with tabs[5]:
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

st.warning("Demo data is for testing only. This app does not place bets. Never wager money you cannot afford to lose.")
