
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
import requests
import pandas as pd

from providers import Race, RunnerOdds, DemoProvider


class LiveOddsAPIProvider:
    """
    Generic live odds API adapter.

    Supported config through Streamlit Secrets or environment:
      LIVE_ODDS_PROVIDER = "THERACINGAPI" or "GENERIC"
      RACING_API_KEY = "..."
      RACING_API_BASE_URL = "https://api.theracingapi.com/v1"

    This adapter expects JSON endpoints:
      GET {base}/racecards?track=Churchill Downs&date=YYYY-MM-DD
      GET {base}/odds?race_id=<race_id>

    Many providers use different field names, so this tries common variants.
    If provider response shape differs, update normalize_races / normalize_odds.
    """

    def __init__(self):
        self.demo = DemoProvider()
        self.provider = (os.getenv("LIVE_ODDS_PROVIDER") or "THERACINGAPI").upper().strip()
        self.key = os.getenv("RACING_API_KEY") or os.getenv("LIVE_ODDS_API_KEY")
        self.base = (os.getenv("RACING_API_BASE_URL") or os.getenv("LIVE_ODDS_API_BASE_URL") or "").rstrip("/")
        self.timeout = int(os.getenv("LIVE_ODDS_TIMEOUT", "20"))

    def is_configured(self) -> bool:
        return bool(self.key and self.base)

    def headers(self) -> dict:
        # Different vendors expect different auth styles. We send common ones.
        return {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.key}",
            "X-API-Key": self.key or "",
            "x-api-key": self.key or "",
        }

    def get_json(self, path: str, params: dict | None = None):
        if not self.is_configured():
            raise RuntimeError("Live Odds API not configured. Set RACING_API_KEY and RACING_API_BASE_URL in Streamlit Secrets.")

        url = f"{self.base}/{path.lstrip('/')}"
        r = requests.get(url, params=params or {}, headers=self.headers(), timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def normalize_races(self, payload, track: str, race_date: str) -> list[Race]:
        data = payload
        if isinstance(data, dict):
            for key in ["races", "racecards", "cards", "events", "data", "results"]:
                if key in data and isinstance(data[key], list):
                    data = data[key]
                    break

        if not isinstance(data, list):
            raise RuntimeError("Racecard response was not a list.")

        races: list[Race] = []
        for i, item in enumerate(data, 1):
            if not isinstance(item, dict):
                continue

            race_num = item.get("race_number") or item.get("number") or item.get("raceNo") or item.get("race_num") or i
            race_id = item.get("race_id") or item.get("id") or item.get("event_id") or item.get("market_id") or f"{track}-{race_date}-R{race_num}"
            name = item.get("race_name") or item.get("name") or item.get("title") or f"Race {race_num}"
            post = item.get("post_time") or item.get("off_time") or item.get("start_time") or item.get("time") or ""
            surface = item.get("surface") or item.get("going") or item.get("track_surface") or ""
            distance = item.get("distance") or item.get("race_distance") or ""
            purse = item.get("purse") or item.get("prize") or item.get("prize_money") or ""

            try:
                race_num = int(race_num)
            except Exception:
                race_num = i

            races.append(Race(
                race_id=str(race_id),
                number=race_num,
                name=str(name),
                track=str(item.get("track") or item.get("course") or track),
                post_time=str(post),
                distance=str(distance),
                surface=str(surface),
                purse=str(purse),
            ))

        if not races:
            raise RuntimeError("No races found in API response.")
        return sorted(races, key=lambda r: r.number)

    def normalize_american_odds(self, value) -> int:
        if value is None:
            return 1000
        if isinstance(value, (int, float)):
            # If decimal odds look like 6.5, convert to American.
            if 1.01 <= float(value) <= 100:
                return int((float(value) - 1) * 100)
            return int(value)
        txt = str(value).strip()
        if txt.startswith("+") or txt.startswith("-"):
            try:
                return int(txt)
            except Exception:
                return 1000
        if "/" in txt or "-" in txt:
            import re
            m = re.search(r"(\d+)\s*[/\-]\s*(\d+)", txt)
            if m:
                num = float(m.group(1))
                den = float(m.group(2))
                return int((num / den) * 100)
        try:
            f = float(txt)
            if 1.01 <= f <= 100:
                return int((f - 1) * 100)
            return int(f)
        except Exception:
            return 1000

    def normalize_odds(self, payload, race_id: str) -> list[RunnerOdds]:
        data = payload
        if isinstance(data, dict):
            for key in ["runners", "odds", "markets", "selections", "data", "results"]:
                if key in data and isinstance(data[key], list):
                    data = data[key]
                    break

        if not isinstance(data, list):
            raise RuntimeError("Odds response was not a list.")

        rows: list[RunnerOdds] = []

        for item in data:
            if not isinstance(item, dict):
                continue

            # Case A: item is runner with nested prices.
            runner = item.get("runner") or item.get("horse") or item.get("horse_name") or item.get("name") or item.get("selection_name")
            prices = item.get("prices") or item.get("bookmakers") or item.get("books")

            if runner and isinstance(prices, list):
                for price in prices:
                    if not isinstance(price, dict):
                        continue
                    book = price.get("book") or price.get("bookmaker") or price.get("sportsbook") or price.get("source") or "Live API"
                    odds_val = (
                        price.get("american_odds")
                        or price.get("american")
                        or price.get("odds_american")
                        or price.get("price")
                        or price.get("decimal")
                        or price.get("fractional")
                        or price.get("odds")
                    )
                    rows.append(RunnerOdds(race_id, str(runner), str(book), self.normalize_american_odds(odds_val)))
                continue

            # Case B: item itself is a price row.
            book = item.get("book") or item.get("bookmaker") or item.get("sportsbook") or item.get("source") or "Live API"
            odds_val = (
                item.get("american_odds")
                or item.get("american")
                or item.get("odds_american")
                or item.get("price")
                or item.get("decimal")
                or item.get("fractional")
                or item.get("odds")
            )
            if runner and odds_val is not None:
                rows.append(RunnerOdds(race_id, str(runner), str(book), self.normalize_american_odds(odds_val)))

        if not rows:
            raise RuntimeError("No runner odds found in API response.")
        return rows

    def races(self, track: str, race_date: str) -> list[Race]:
        try:
            payload = self.get_json("racecards", {"track": track, "date": race_date})
            return self.normalize_races(payload, track, race_date)
        except Exception:
            # Fall back keeps app alive.
            return self.demo.races(track, race_date)

    def odds(self, race_id: str) -> list[RunnerOdds]:
        try:
            payload = self.get_json("odds", {"race_id": race_id})
            return self.normalize_odds(payload, race_id)
        except Exception:
            return self.demo.odds(race_id)

    def factors(self, race_id: str) -> pd.DataFrame:
        # Most odds APIs do not include speed figs. Use neutral/fallback factors.
        try:
            odds_rows = self.odds(race_id)
            runners = sorted({o.runner for o in odds_rows})
            rows = []
            for i, runner in enumerate(runners):
                rows.append({
                    "race_id": race_id,
                    "runner": runner,
                    "post_position": i + 1,
                    "speed_figure": 75,
                    "jockey_rating": 75,
                    "trainer_rating": 75,
                    "track_condition_fit": 75,
                    "distance_fit": 75,
                    "pace_fit": 75,
                    "recent_form": 75,
                    "class_rating": 75,
                    "early_speed": 65 + ((i * 9) % 30),
                    "late_speed": 65 + ((i * 11) % 30),
                    "running_style": ["Early", "Stalker", "Closer"][i % 3],
                    "scratched": False,
                })
            return pd.DataFrame(rows)
        except Exception:
            return self.demo.factors(race_id)
