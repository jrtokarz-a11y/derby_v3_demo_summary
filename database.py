from __future__ import annotations
from pathlib import Path
import sqlite3
import pandas as pd

DB_PATH = Path("derby_v3.db")


def connect():
    return sqlite3.connect(DB_PATH)


def init_db():
    with connect() as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS odds_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            race_id TEXT NOT NULL,
            runner TEXT NOT NULL,
            book TEXT NOT NULL,
            american_odds INTEGER NOT NULL
        )
        """)
        con.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            race_id TEXT NOT NULL,
            runner TEXT,
            alert_type TEXT NOT NULL,
            message TEXT NOT NULL,
            tier TEXT
        )
        """)
        con.execute("""
        CREATE TABLE IF NOT EXISTS bets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            track TEXT,
            race_id TEXT,
            race_name TEXT,
            bet_type TEXT,
            horses TEXT,
            stake REAL,
            odds_taken INTEGER,
            closing_odds INTEGER,
            clv_points REAL,
            tier TEXT,
            result TEXT,
            payout REAL,
            profit REAL
        )
        """)
        con.execute("CREATE INDEX IF NOT EXISTS idx_snap_race_runner ON odds_snapshots(race_id, runner)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_alert_race ON alerts(race_id)")
        con.commit()


def save_odds_snapshot(ts: str, race_id: str, odds_rows):
    rows = [(ts, o.race_id, o.runner, o.book, int(o.american_odds)) for o in odds_rows]
    with connect() as con:
        con.executemany(
            "INSERT INTO odds_snapshots(ts, race_id, runner, book, american_odds) VALUES (?, ?, ?, ?, ?)",
            rows,
        )
        con.commit()


def load_latest_best_odds(race_id: str) -> pd.DataFrame:
    with connect() as con:
        df = pd.read_sql_query(
            """
            SELECT runner, MAX(american_odds) AS best_american_odds
            FROM odds_snapshots
            WHERE race_id = ?
            AND ts = (SELECT MAX(ts) FROM odds_snapshots WHERE race_id = ?)
            GROUP BY runner
            """,
            con,
            params=(race_id, race_id),
        )
    return df


def load_previous_best_odds(race_id: str) -> pd.DataFrame:
    with connect() as con:
        snaps = pd.read_sql_query(
            "SELECT DISTINCT ts FROM odds_snapshots WHERE race_id = ? ORDER BY ts DESC LIMIT 2",
            con,
            params=(race_id,),
        )
        if len(snaps) < 2:
            return pd.DataFrame()
        prev_ts = snaps.iloc[1]["ts"]
        df = pd.read_sql_query(
            """
            SELECT runner, MAX(american_odds) AS previous_best_odds
            FROM odds_snapshots
            WHERE race_id = ? AND ts = ?
            GROUP BY runner
            """,
            con,
            params=(race_id, prev_ts),
        )
    return df


def save_alert(ts: str, race_id: str, runner: str | None, alert_type: str, message: str, tier: str | None = None):
    with connect() as con:
        con.execute(
            "INSERT INTO alerts(ts, race_id, runner, alert_type, message, tier) VALUES (?, ?, ?, ?, ?, ?)",
            (ts, race_id, runner, alert_type, message, tier),
        )
        con.commit()


def load_alerts(limit: int = 100) -> pd.DataFrame:
    with connect() as con:
        return pd.read_sql_query("SELECT * FROM alerts ORDER BY id DESC LIMIT ?", con, params=(limit,))


def save_bet(row: dict):
    cols = list(row.keys())
    vals = [row[c] for c in cols]
    placeholders = ",".join(["?"] * len(cols))
    with connect() as con:
        con.execute(f"INSERT INTO bets({','.join(cols)}) VALUES ({placeholders})", vals)
        con.commit()


def load_bets() -> pd.DataFrame:
    with connect() as con:
        return pd.read_sql_query("SELECT * FROM bets ORDER BY id DESC", con)


def load_snapshots(race_id: str) -> pd.DataFrame:
    with connect() as con:
        return pd.read_sql_query("SELECT * FROM odds_snapshots WHERE race_id = ? ORDER BY ts", con, params=(race_id,))


def update_bet_result(bet_id: int, result: str, payout: float, closing_odds: int | None = None):
    with connect() as con:
        row = con.execute("SELECT odds_taken, stake FROM bets WHERE id = ?", (int(bet_id),)).fetchone()
        odds_taken = int(row[0]) if row else 0
        stake = float(row[1]) if row else 0.0
        closing_odds = int(closing_odds or 0)
        clv_points = closing_odds - odds_taken if closing_odds else 0
        profit = float(payout) - stake if result in ["Won", "Lost"] else 0.0
        con.execute(
            "UPDATE bets SET result = ?, payout = ?, closing_odds = ?, clv_points = ?, profit = ? WHERE id = ?",
            (result, float(payout), closing_odds, clv_points, profit, int(bet_id)),
        )
        con.commit()


def delete_bet(bet_id: int):
    with connect() as con:
        con.execute("DELETE FROM bets WHERE id = ?", (int(bet_id),))
        con.commit()
