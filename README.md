# Derby V4.2 Live Odds API Connector

Adds:
- Live Odds API data mode
- Streamlit Secrets support
- Generic API adapter
- Live provider status check
- Racecards endpoint support
- Odds endpoint support
- Graceful fallback to Demo if API fails

## Required secrets

In Streamlit Cloud > App settings > Secrets:

```toml
LIVE_ODDS_PROVIDER = "THERACINGAPI"
RACING_API_KEY = "your_key_here"
RACING_API_BASE_URL = "https://api.theracingapi.com/v1"
```

## Expected endpoints

The generic adapter expects:

```text
GET /racecards?track=Churchill Downs&date=YYYY-MM-DD
GET /odds?race_id=...
```

If your provider uses different endpoints or field names, update `live_odds_provider.py`.

## Important

This app does not place bets. Always verify entries, scratches, odds, and legality before wagering.
