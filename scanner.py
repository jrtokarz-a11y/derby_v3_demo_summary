from __future__ import annotations
from datetime import datetime
import pandas as pd

from database import save_odds_snapshot, load_previous_best_odds, save_alert
from model import analyze, final_call


def scan_card(provider, races, weights, blend) -> pd.DataFrame:
    rows = []
    ts = datetime.now().isoformat(timespec="seconds")
    for race in races:
        try:
            odds = provider.odds(race.race_id)
            factors = provider.factors(race.race_id)
            save_odds_snapshot(ts, race.race_id, odds)
            prev = load_previous_best_odds(race.race_id)
            rankings, shape = analyze(odds, factors, prev, weights, blend)
            call = final_call(rankings, shape)
            greens = rankings[rankings["tier"].isin(["GREEN+","GREEN"])]
            top = rankings.iloc[0] if len(rankings) else None
            if top is not None:
                rows.append({
                    "race_id": race.race_id,
                    "race": f"Race {race.number} {race.name}",
                    "post_time": race.post_time,
                    "shape": shape["shape"],
                    "volatility": shape["volatility"],
                    "final_call": call,
                    "top_horse": top["runner"],
                    "top_tier": top["tier"],
                    "top_ev_pct": top["expected_value_pct"],
                    "greens": len(greens),
                })
            for _, g in greens.iterrows():
                save_alert(ts, race.race_id, g["runner"], "VALUE", f'{g["tier"]} {g["runner"]} in {race.name}: EV {g["expected_value_pct"]:.1f}%', g["tier"])
        except Exception as exc:
            rows.append({
                "race_id": race.race_id,
                "race": f"Race {race.number} {race.name}",
                "post_time": race.post_time,
                "shape": "ERROR",
                "volatility": "ERROR",
                "final_call": str(exc),
                "top_horse": "",
                "top_tier": "",
                "top_ev_pct": 0,
                "greens": 0,
            })
    return pd.DataFrame(rows)
