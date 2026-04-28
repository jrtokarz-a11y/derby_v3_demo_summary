from __future__ import annotations
from itertools import permutations
import pandas as pd
import numpy as np


def american_to_decimal(odds: int) -> float:
    return 1 + odds / 100 if odds > 0 else 1 + 100 / abs(odds)


def american_to_implied_prob(odds: int) -> float:
    return 100 / (odds + 100) if odds > 0 else abs(odds) / (abs(odds) + 100)


def normalize(s: pd.Series) -> pd.Series:
    s = pd.to_numeric(s, errors="coerce")
    s = s.fillna(s.median() if len(s.dropna()) else 0)
    if s.max() == s.min():
        return pd.Series([.5] * len(s), index=s.index)
    return (s - s.min()) / (s.max() - s.min())


def devig(g: pd.DataFrame) -> pd.DataFrame:
    g = g.copy()
    total = g["implied_prob"].sum()
    g["fair_prob_market"] = g["implied_prob"] / total if total else 0
    return g


def race_shape(factors: pd.DataFrame) -> dict:
    if factors is None or factors.empty:
        return {"shape": "UNKNOWN", "bias": "Neutral", "speed_pressure": 0, "volatility": "UNKNOWN"}
    f = factors.copy()
    if "early_speed" not in f:
        f["early_speed"] = 50
    if "running_style" not in f:
        f["running_style"] = "Stalker"
    active = f[~f.get("scratched", False).astype(bool)] if "scratched" in f else f
    early_count = ((active["running_style"].astype(str).str.lower() == "early") | (pd.to_numeric(active["early_speed"], errors="coerce") >= 80)).sum()
    field = max(len(active), 1)
    pressure = early_count / field
    volatility = "HIGH" if field >= 10 else ("MEDIUM" if field >= 7 else "LOW")
    if pressure >= .45:
        return {"shape": "FAST", "bias": "Favors closers/stalkers", "speed_pressure": pressure, "volatility": volatility}
    if pressure <= .18:
        return {"shape": "SLOW", "bias": "Favors front-runners", "speed_pressure": pressure, "volatility": volatility}
    return {"shape": "MODERATE", "bias": "Balanced", "speed_pressure": pressure, "volatility": volatility}


def pace_score(df: pd.DataFrame, shape: dict) -> pd.Series:
    early = normalize(df.get("early_speed", pd.Series([50]*len(df))))
    late = normalize(df.get("late_speed", pd.Series([50]*len(df))))
    pace_fit = normalize(df.get("pace_fit", pd.Series([50]*len(df))))
    style = df.get("running_style", pd.Series(["Stalker"]*len(df))).astype(str).str.lower()
    score = pace_fit * .45 + early * .25 + late * .30
    if shape["shape"] == "FAST":
        score = score + np.where(style.str.contains("closer"), .10, 0) + np.where(style.str.contains("early"), -.06, 0)
    elif shape["shape"] == "SLOW":
        score = score + np.where(style.str.contains("early"), .09, 0) + np.where(style.str.contains("closer"), -.04, 0)
    return pd.Series(score, index=df.index).clip(lower=0, upper=1.2)


def post_score(post: pd.Series, field_size: int) -> pd.Series:
    p = pd.to_numeric(post, errors="coerce").fillna((field_size + 1) / 2)
    center = (field_size + 1) / 2
    maxd = max(center - 1, 1)
    return (1 - (abs(p - center) / maxd) * .22).clip(lower=.65, upper=1)


def movement(current: pd.DataFrame, previous: pd.DataFrame) -> pd.DataFrame:
    if previous is None or previous.empty:
        return pd.DataFrame({"runner": current["runner"], "odds_change_pct": 0, "movement_flag": "NEW"})
    cur = current[["runner","best_american_odds"]].copy()
    prev = previous[["runner","previous_best_odds"]].copy()
    m = cur.merge(prev, on="runner", how="left")
    m["odds_change_pct"] = (m["best_american_odds"] - m["previous_best_odds"]) / m["previous_best_odds"].abs()
    m["movement_flag"] = np.where(m["odds_change_pct"] <= -.10, "STEAM", np.where(m["odds_change_pct"] >= .10, "DRIFT", "STABLE"))
    m["movement_flag"] = m["movement_flag"].fillna("NEW")
    return m[["runner","odds_change_pct","movement_flag"]]


def tier(row: pd.Series) -> str:
    if bool(row.get("scratched", False)):
        return "GRAY"
    ev, k, p, pace = row["expected_value"], row["kelly_fraction"], row["model_prob"], row.get("pace_engine_score", .5)
    move = row.get("movement_flag", "")
    if ev >= .15 and k >= .035 and p >= .08 and pace >= .55 and move != "DRIFT":
        return "GREEN+"
    if ev >= .08 and k >= .02 and p >= .06:
        return "GREEN"
    if ev > 0:
        return "YELLOW"
    return "RED"


def analyze(odds_rows, factors: pd.DataFrame, previous_best: pd.DataFrame, weights: dict, blend: dict) -> tuple[pd.DataFrame, dict]:
    odds = pd.DataFrame([o.__dict__ for o in odds_rows])
    if odds.empty:
        return pd.DataFrame(), race_shape(pd.DataFrame())
    odds["american_odds"] = pd.to_numeric(odds["american_odds"], errors="coerce").astype(int)
    odds["decimal_odds"] = odds["american_odds"].apply(american_to_decimal)
    odds["implied_prob"] = odds["american_odds"].apply(american_to_implied_prob)
    fair = pd.concat([devig(g) for _, g in odds.groupby("book")], ignore_index=True)

    r = fair.groupby("runner").agg(
        best_american_odds=("american_odds", "max"),
        best_decimal_odds=("decimal_odds", "max"),
        avg_american_odds=("american_odds", "mean"),
        market_fair_prob=("fair_prob_market", "mean"),
        books_seen=("book", "nunique"),
    ).reset_index()

    mov = movement(r, previous_best)
    r = r.merge(mov, on="runner", how="left")

    shape = race_shape(factors)
    if factors is not None and not factors.empty:
        f = factors.copy()
        if "race_id" in f.columns:
            f = f.drop(columns=["race_id"])
        r = r.merge(f, on="runner", how="left")
    r["scratched"] = r.get("scratched", False).fillna(False).astype(bool)

    for col in ["speed_figure","jockey_rating","trainer_rating","track_condition_fit","distance_fit","pace_fit","recent_form","class_rating","post_position","early_speed","late_speed"]:
        if col not in r:
            r[col] = np.nan
    if "running_style" not in r:
        r["running_style"] = "Stalker"

    active_n = int((~r["scratched"]).sum())
    r["pace_engine_score"] = pace_score(r, shape)
    components = (
        normalize(r["speed_figure"]) * weights["speed"] +
        r["pace_engine_score"] * weights["pace"] +
        normalize(r["recent_form"]) * weights["form"] +
        normalize(r["class_rating"]) * weights["class"] +
        normalize(r["jockey_rating"]) * weights["jockey"] +
        normalize(r["trainer_rating"]) * weights["trainer"] +
        normalize(r["track_condition_fit"]) * weights["track"] +
        normalize(r["distance_fit"]) * weights["distance"] +
        post_score(r["post_position"], active_n) * weights["post"]
    )
    r["factor_score"] = components / (sum(weights.values()) or 1)
    r.loc[r["scratched"], "factor_score"] = 0

    market = r["market_fair_prob"]
    factor_adj = r["factor_score"] / max(r["factor_score"].sum(), 1e-9)
    total_blend = blend["market"] + blend["factor"]
    r["model_prob_raw"] = (market*blend["market"] + factor_adj*blend["factor"]) / total_blend
    r.loc[r["scratched"], "model_prob_raw"] = 0
    r["model_prob"] = r["model_prob_raw"] / r["model_prob_raw"].sum() if r["model_prob_raw"].sum() else 0

    r["edge_prob"] = r["model_prob"] - r["market_fair_prob"]
    r["expected_value"] = r["model_prob"] * (r["best_decimal_odds"] - 1) - (1 - r["model_prob"])
    r["kelly_fraction"] = (r["expected_value"] / (r["best_decimal_odds"] - 1)).clip(lower=0)

    for col in ["market_fair_prob","model_prob","edge_prob","expected_value","kelly_fraction","odds_change_pct"]:
        r[col + "_pct"] = r[col] * 100

    r["tier"] = r.apply(tier, axis=1)
    r["confidence"] = r["tier"].map({
        "GREEN+": "GREEN+ - Aggressive value",
        "GREEN": "GREEN - Standard value",
        "YELLOW": "YELLOW - Support only",
        "RED": "RED - Avoid",
        "GRAY": "SCRATCHED",
    })
    order = {"GREEN+":0, "GREEN":1, "YELLOW":2, "RED":3, "GRAY":4}
    r["tier_order"] = r["tier"].map(order)
    r = r.sort_values(["tier_order","expected_value","model_prob"], ascending=[True,False,False]).reset_index(drop=True)
    return r, shape


def final_call(rankings: pd.DataFrame, shape: dict) -> str:
    active = rankings[~rankings["scratched"]]
    if shape.get("volatility") == "HIGH" and not active["tier"].isin(["GREEN+","GREEN"]).any():
        return "PASS - high volatility, no strong edge"
    if (active["tier"] == "GREEN+").any():
        return "BET WIN - GREEN+"
    if (active["tier"] == "GREEN").any():
        return "BET WIN SMALL - GREEN"
    if (active["tier"] == "YELLOW").sum() >= 3:
        return "SMALL EXACTA ONLY"
    return "PASS"


def exacta_legs(horses: list[str]) -> list[str]:
    return [f"{a} / {b}" for a, b in permutations(horses, 2)]


def trifecta_count(n: int) -> int:
    return n * max(n-1, 0) * max(n-2, 0)
