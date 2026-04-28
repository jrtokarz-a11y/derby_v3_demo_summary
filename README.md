# Derby V4.1.1 Timing Engine Fix

Fixes:
- NameError / ordering issue where timing_board_df tried to use recommendations_df before it existed
- Adds safe defaults for recommendations, bet structures, bankroll variables, and timing board

Keeps:
- Timing Engine
- Bet Structure Engine
- Bankroll Engine
- ROI Dashboard
- Auto Real Data / Demo modes
