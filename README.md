# Derby Final Clean Version

This is the clean final package.

Includes:
- Track dropdowns
- Race day presets
- Oaks Day fallback card
- Derby Day fallback card
- REAL DATA LOADED / FALLBACK DATA ACTIVE status
- Live Odds API connector
- Auto Real Data mode
- Timing Engine
- Steam detection
- Bet Structure Engine
- Bankroll Engine
- Bet Ledger
- ROI Dashboard
- Reddit sentiment overlay

## Important

If the app cannot pull real entries or live API data, it will clearly show:

FALLBACK DATA ACTIVE

That means it is using fallback race data, not real live race data.

## Streamlit Secrets for Live Odds API

```toml
LIVE_ODDS_PROVIDER = "THERACINGAPI"
RACING_API_KEY = "your_key_here"
RACING_API_BASE_URL = "https://api.theracingapi.com/v1"

REDDIT_CLIENT_ID = ""
REDDIT_CLIENT_SECRET = ""
REDDIT_USER_AGENT = "derby-app"
```
