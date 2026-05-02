
from __future__ import annotations

import re
import requests
import pandas as pd

from providers import Race, RunnerOdds

OFFICIAL_DERBY_STATUS = {"loaded": False, "message": "Not attempted yet"}

DERBY_URL = "https://www.kentuckyderby.com/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; DerbyResearchTool/1.0)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def fractional_to_american(value: str) -> int:
    value = str(value or "").strip()
    m = re.search(r"(\d+)\s*[/\-]\s*(\d+)", value)
    if m:
        return int((float(m.group(1)) / float(m.group(2))) * 100)
    try:
        f = float(value)
        if 1.01 <= f <= 100:
            return int((f - 1) * 100)
        return int(f)
    except Exception:
        return 1000


class OfficialDerbyLiveProvider:
    """
    Pulls the official KentuckyDerby.com Derby odds block when available.
    Intended for the Kentucky Derby race itself, not the full undercard.
    """

    def __init__(self):
        # Imported lazily to avoid circular import at module load time.
        from providers import OaksAwareDemoProvider
        self.fallback = OaksAwareDemoProvider()

    def _page_text(self) -> str:
        r = requests.get(DERBY_URL, headers=HEADERS, timeout=20)
        r.raise_for_status()
        return r.text

    def _parse_derby_rows(self):
        html = self._page_text()
        block = html

        # Try to narrow to the Derby odds section.
        for marker in ["2026 Kentucky Derby", "Kentucky Derby 152", "Horse Name"]:
            idx = block.find(marker)
            if idx != -1:
                block = block[idx: idx + 50000]
                break

        # Strip HTML tags while preserving order.
        text = re.sub(r"<[^>]+>", "\n", block)
        text = re.sub(r"&nbsp;|&#160;", " ", text)
        tokens = [t.strip() for t in re.split(r"\n+", text) if t.strip()]

        rows = []
        i = 0
        while i < len(tokens):
            # Common pattern: number, horse, jockey, trainer, odds
            if re.fullmatch(r"\d{1,2}", tokens[i]):
                num = int(tokens[i])
                if i + 4 < len(tokens):
                    horse = tokens[i + 1]
                    jockey = tokens[i + 2]
                    trainer = tokens[i + 3]
                    odds = tokens[i + 4]
                    if re.search(r"\d+\s*/\s*\d+", odds) and not re.search(r"Race|Horse|Jockey|Trainer|Odds", horse, re.I):
                        rows.append({
                            "number": num,
                            "horse": horse,
                            "jockey": jockey,
                            "trainer": trainer,
                            "odds": odds,
                            "american_odds": fractional_to_american(odds),
                        })
                        i += 5
                        continue
            i += 1

        # Deduplicate horses.
        seen = set()
        clean = []
        for row in rows:
            key = row["horse"].lower()
            if key not in seen:
                seen.add(key)
                clean.append(row)

        if not clean:
            raise RuntimeError("Could not parse official Derby odds block.")

        OFFICIAL_DERBY_STATUS.update({
            "loaded": True,
            "message": f"Loaded {len(clean)} horses from KentuckyDerby.com official odds block.",
        })
        return clean

    def races(self, track: str, race_date: str):
        try:
            self._parse_derby_rows()
            return [
                Race(
                    race_id="OFFICIAL-DERBY-R12",
                    number=12,
                    name="Kentucky Derby presented by Woodford Reserve",
                    track="Churchill Downs",
                    post_time="6:57 PM ET",
                    distance="1 1/4 miles",
                    surface="Dirt",
                    purse="$5,000,000",
                )
            ]
        except Exception as exc:
            OFFICIAL_DERBY_STATUS.update({
                "loaded": False,
                "message": f"Official Derby source failed; using fallback: {exc}",
            })
            return self.fallback.races(track, race_date)

    def odds(self, race_id: str):
        try:
            rows = self._parse_derby_rows()
            out = []
            for row in rows:
                base = int(row["american_odds"])
                out.append(RunnerOdds(race_id, row["horse"], "KentuckyDerby.com Official", base))
                out.append(RunnerOdds(race_id, row["horse"], "Official + small", int(base * 1.01)))
                out.append(RunnerOdds(race_id, row["horse"], "Official - small", max(100, int(base * 0.99))))
            return out
        except Exception as exc:
            OFFICIAL_DERBY_STATUS.update({
                "loaded": False,
                "message": f"Official Derby odds failed; using fallback odds: {exc}",
            })
            return self.fallback.odds(race_id)

    def factors(self, race_id: str):
        try:
            rows = self._parse_derby_rows()
            out = []
            for idx, row in enumerate(rows):
                out.append({
                    "race_id": race_id,
                    "runner": row["horse"],
                    "post_position": row["number"],
                    "speed_figure": 75 + ((idx * 5) % 20),
                    "jockey_rating": 75,
                    "trainer_rating": 75,
                    "track_condition_fit": 75,
                    "distance_fit": 75,
                    "pace_fit": 75,
                    "recent_form": 75,
                    "class_rating": 75,
                    "early_speed": 65 + ((idx * 9) % 30),
                    "late_speed": 65 + ((idx * 11) % 30),
                    "running_style": ["Early", "Stalker", "Closer"][idx % 3],
                    "scratched": False,
                })
            return pd.DataFrame(out)
        except Exception:
            return self.fallback.factors(race_id)
