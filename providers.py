from __future__ import annotations
import os
from dataclasses import dataclass
import pandas as pd
import requests


@dataclass
class Race:
    race_id: str
    number: int
    name: str
    track: str
    post_time: str
    distance: str
    surface: str
    purse: str


@dataclass
class RunnerOdds:
    race_id: str
    runner: str
    book: str
    american_odds: int


class DemoProvider:
    def races(self, track: str, race_date: str) -> list[Race]:
        return [
            Race("CD-2026-05-02-R1", 1, "Maiden Special Weight", track, "10:30 AM ET", "6 furlongs", "Dirt", "$120,000"),
            Race("CD-2026-05-02-R2", 2, "Allowance Optional Claiming", track, "11:05 AM ET", "1 mile", "Dirt", "$134,000"),
            Race("CD-2026-05-02-R3", 3, "Turf Sprint Stakes", track, "11:40 AM ET", "5.5 furlongs", "Turf", "$250,000"),
            Race("CD-2026-05-02-R4", 4, "Pat Day Mile", track, "12:15 PM ET", "1 mile", "Dirt", "$600,000"),
            Race("CD-2026-05-02-R5", 5, "Derby City Distaff", track, "1:00 PM ET", "7 furlongs", "Dirt", "$1,000,000"),
            Race("CD-2026-05-02-R6", 6, "American Turf", track, "1:45 PM ET", "1 1/16 miles", "Turf", "$600,000"),
            Race("CD-2026-05-02-R7", 7, "Churchill Downs Stakes", track, "2:30 PM ET", "7 furlongs", "Dirt", "$1,000,000"),
            Race("CD-2026-05-02-R8", 8, "Derby Undercard Stakes", track, "3:20 PM ET", "1 1/8 miles", "Dirt", "$750,000"),
            Race("CD-2026-05-02-R9", 9, "Turf Classic", track, "4:10 PM ET", "1 1/8 miles", "Turf", "$1,000,000"),
            Race("CD-2026-05-02-R10", 10, "Kentucky Derby", track, "6:57 PM ET", "1 1/4 miles", "Dirt", "$5,000,000"),
        ]

    def odds(self, race_id: str) -> list[RunnerOdds]:
        names = {
            "R1": ["Morning Bell", "Blue Courier", "Last Ledger", "River Agent", "Side Street"],
            "R2": ["High Allowance", "Copper Rail", "Unbridled Deal", "Fast Margin", "Office Hours"],
            "R3": ["Grass Burner", "Quick Turn", "Turf Signal", "Green Flash", "Short Sprint"],
            "R4": ["Mile Marker", "Patriot Run", "Long Division", "Prime Number", "Second Gear"],
            "R5": ["Distaff Queen", "Seven Across", "Lady Ledger", "Bold Notice", "Inside Voice"],
            "R6": ["American Trade", "Turf Theory", "Wide Trip", "Late Invoice", "Euro Signal"],
            "R7": ["Churchill Rocket", "Seven Furlong", "Main Track", "Bluegrass Bid", "Sprint Equity"],
            "R8": ["Undercard Hero", "Dirt Route", "Classic Prep", "Long Run", "Final Turn"],
            "R9": ["Turf Classic", "Outside Draw", "Firm Ground", "Green Mile", "Closing Kick"],
            "R10": ["Journalism", "Sandman", "Coal Battle", "Sovereignty", "Burnham Square", "Tappan Street", "Rodriguez", "East Avenue"],
        }
        key = race_id.split("-")[-1]
        runners = names.get(key, names["R10"])
        base = [350, 500, 650, 800, 1000, 1200, 1600, 2000]
        rows = []
        import time, random
        seed = int(time.time() // 30) % 7
        for i, runner in enumerate(runners):
            a = base[i % len(base)] + (seed - 3) * (20 + i * 5)
            a = max(100, int(a))
            rows += [
                RunnerOdds(race_id, runner, "MockBook A", a),
                RunnerOdds(race_id, runner, "MockBook B", int(a * (1.08 + (i % 3) * .04))),
                RunnerOdds(race_id, runner, "MockBook C", max(100, int(a * (0.90 + (i % 2) * .03)))),
            ]
        return rows

    def factors(self, race_id: str) -> pd.DataFrame:
        runners = sorted({o.runner for o in self.odds(race_id)})
        styles = ["Early", "Stalker", "Closer", "Early", "Closer", "Stalker", "Early", "Closer"]
        rows = []
        for i, runner in enumerate(runners):
            rows.append({
                "race_id": race_id,
                "runner": runner,
                "post_position": i + 1,
                "speed_figure": 82 + ((i * 7) % 20),
                "jockey_rating": 70 + ((i * 9) % 28),
                "trainer_rating": 68 + ((i * 11) % 29),
                "track_condition_fit": 60 + ((i * 13) % 38),
                "distance_fit": 62 + ((i * 5) % 36),
                "pace_fit": 65 + ((i * 8) % 31),
                "recent_form": 65 + ((i * 6) % 33),
                "class_rating": 70 + ((i * 4) % 25),
                "early_speed": 50 + ((i * 17) % 50),
                "late_speed": 50 + ((i * 19) % 50),
                "running_style": styles[i % len(styles)],
                "scratched": False,
            })
        return pd.DataFrame(rows)


class CsvProvider:
    def races(self, track: str, race_date: str) -> list[Race]:
        path = os.getenv("RACE_CARD_CSV")
        if not path:
            raise RuntimeError("RACE_CARD_CSV not set")
        df = pd.read_csv(path)
        return [Race(**row[["race_id", "number", "name", "track", "post_time", "distance", "surface", "purse"]].to_dict()) for _, row in df.iterrows()]

    def odds(self, race_id: str) -> list[RunnerOdds]:
        path = os.getenv("ODDS_CSV")
        if not path:
            raise RuntimeError("ODDS_CSV not set")
        df = pd.read_csv(path)
        df = df[df["race_id"].astype(str) == str(race_id)]
        return [RunnerOdds(str(r.race_id), str(r.runner), str(r.book), int(r.american_odds)) for r in df.itertuples()]

    def factors(self, race_id: str) -> pd.DataFrame:
        path = os.getenv("FACTORS_CSV")
        if not path:
            return pd.DataFrame()
        df = pd.read_csv(path)
        return df[df["race_id"].astype(str) == str(race_id)] if "race_id" in df else df


class LiveProvider:
    def __init__(self):
        self.key = os.getenv("RACING_API_KEY")
        self.base = (os.getenv("RACING_API_BASE_URL") or "").rstrip("/")
        if not self.key or not self.base:
            raise RuntimeError("Set RACING_API_KEY and RACING_API_BASE_URL")

    def headers(self):
        return {"Authorization": f"Bearer {self.key}", "X-API-Key": self.key, "Accept": "application/json"}

    def races(self, track: str, race_date: str) -> list[Race]:
        r = requests.get(f"{self.base}/racecards", params={"track": track, "date": race_date}, headers=self.headers(), timeout=20)
        r.raise_for_status()
        data = r.json()
        items = data.get("races") or data.get("racecards") or data.get("data") or data
        races = []
        for i, item in enumerate(items, 1):
            races.append(Race(
                race_id=str(item.get("race_id") or item.get("id") or f"{track}-{race_date}-R{i}"),
                number=int(item.get("race_number") or item.get("number") or i),
                name=str(item.get("race_name") or item.get("name") or f"Race {i}"),
                track=str(item.get("track") or item.get("course") or track),
                post_time=str(item.get("post_time") or item.get("off_time") or item.get("time") or ""),
                distance=str(item.get("distance") or ""),
                surface=str(item.get("surface") or item.get("going") or ""),
                purse=str(item.get("purse") or item.get("prize") or ""),
            ))
        return races

    def odds(self, race_id: str) -> list[RunnerOdds]:
        r = requests.get(f"{self.base}/odds", params={"race_id": race_id}, headers=self.headers(), timeout=20)
        r.raise_for_status()
        data = r.json()
        items = data.get("runners") or data.get("odds") or data.get("data") or data
        rows = []
        for item in items:
            runner = item.get("runner") or item.get("horse") or item.get("name")
            prices = item.get("prices") or (item.get("odds") if isinstance(item.get("odds"), list) else [item])
            for price in prices:
                book = price.get("book") or price.get("bookmaker") or "Live"
                american = price.get("american_odds") or price.get("american") or price.get("odds_american")
                if runner and american is not None:
                    rows.append(RunnerOdds(race_id, str(runner), str(book), int(float(american))))
        return rows

    def factors(self, race_id: str) -> pd.DataFrame:
        return pd.DataFrame()


from real_scraper_provider import EquibaseOption1Provider


from live_odds_provider import LiveOddsAPIProvider


from churchill_full_card_provider import ChurchillFullCardProvider
from official_derby_provider import OfficialDerbyLiveProvider


def get_provider(mode: str):
    if mode == "Churchill Full Card Today":
        return ChurchillFullCardProvider()
    if mode == "Official Derby Live":
        return OfficialDerbyLiveProvider()
    if mode == "Live Odds API":
        return LiveOddsAPIProvider()
    if mode == "Auto Real Data":
        return EquibaseOption1Provider()
    if mode == "CSV Import":
        return CsvProvider()
    if mode == "Live API":
        return LiveProvider()
    return DemoProvider()


class OaksAwareDemoProvider(DemoProvider):
    pass
