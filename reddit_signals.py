
from __future__ import annotations
import os
import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


class RedditSignalProvider:
    def __init__(self):
        import praw
        self.reddit = praw.Reddit(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            user_agent=os.getenv("REDDIT_USER_AGENT"),
        )
        self.analyzer = SentimentIntensityAnalyzer()

    def fetch(self, runners: list[str], race_name: str, subreddits: list[str], limit: int = 75) -> pd.DataFrame:
        rows = []
        query = f'"{race_name}" OR "Churchill Downs" OR "Kentucky Derby"'
        for subreddit in subreddits:
            try:
                posts = self.reddit.subreddit(subreddit).search(query, sort="new", time_filter="week", limit=limit)
                for post in posts:
                    text = f"{post.title}\n{getattr(post, 'selftext', '')}"
                    sentiment = self.analyzer.polarity_scores(text)["compound"]
                    for runner in runners:
                        if runner.lower() in text.lower():
                            rows.append({
                                "runner": runner,
                                "subreddit": subreddit,
                                "post_id": post.id,
                                "post_score": getattr(post, "score", 0),
                                "sentiment": sentiment,
                            })
            except Exception:
                continue

        if not rows:
            return pd.DataFrame(columns=[
                "runner", "mentions", "avg_sentiment", "reddit_heat",
                "reddit_signal", "public_hype", "fade_risk"
            ])

        df = pd.DataFrame(rows)
        agg = df.groupby("runner").agg(
            mentions=("post_id", "count"),
            avg_sentiment=("sentiment", "mean"),
            total_upvotes=("post_score", "sum"),
        ).reset_index()

        agg["reddit_heat"] = (
            agg["mentions"] * 0.7
            + agg["avg_sentiment"].fillna(0) * 10
            + agg["total_upvotes"].clip(lower=0).pow(0.5) * 0.3
        )

        heat = agg["reddit_heat"]
        if heat.max() != heat.min():
            agg["public_hype"] = (heat - heat.min()) / (heat.max() - heat.min())
        else:
            agg["public_hype"] = 0.0

        def signal(row):
            if row["mentions"] >= 3 and row["avg_sentiment"] >= 0.20:
                return "Bullish"
            if row["mentions"] >= 3 and row["avg_sentiment"] <= -0.15:
                return "Bearish"
            if row["mentions"] >= 3:
                return "High chatter"
            return "Quiet"

        agg["reddit_signal"] = agg.apply(signal, axis=1)
        agg["fade_risk"] = ((agg["public_hype"] >= 0.75) & (agg["avg_sentiment"] >= 0.15)).astype(int)

        return agg[[
            "runner", "mentions", "avg_sentiment", "reddit_heat",
            "reddit_signal", "public_hype", "fade_risk"
        ]]
