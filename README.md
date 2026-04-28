# Derby V3.7.1 Mode Fix

Fixes:
- NameError on provider = get_provider(mode)
- Restores Data Source selector:
  - Auto Real Data
  - Demo
- Adds visible current data source indicator

Update GitHub by replacing:
- app.py
- providers.py
- real_scraper_provider.py
- requirements.txt
- README.md
- reddit_signals.py

Then reboot Streamlit.
