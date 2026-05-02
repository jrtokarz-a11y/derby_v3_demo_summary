# Derby V4.4.2 Zero Odds Fix

Fixes:
- ZeroDivisionError when a public race-card source returns odds as 0 or blank.
- Invalid/missing odds now default safely to +1000 instead of crashing.
- Keeps Churchill Full Card Today mode.

Upload/replace all files in this package, reboot Streamlit, then Clear cache / refresh columns.
