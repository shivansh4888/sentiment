from flask import Flask, render_template, request
import requests
import re
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from urllib.parse import urlparse, parse_qs

app = Flask(__name__)

# Replace with your actual YouTube API key

YOUTUBE_API_KEY = "AIzaSyDI11qFh5P05eQ-ExwE6AfRq2sBHBAY6qI"
analyzer = SentimentIntensityAnalyzer()

def extract_video_id(url):
    """
    Extracts video ID from a given YouTube URL.
    Supports various formats including short URLs and embedded links.
    """
    parsed_url = urlparse(url)
    
    if parsed_url.hostname in ["www.youtube.com", "youtube.com"]:
        return parse_qs(parsed_url.query).get("v", [None])[0]
    
    elif parsed_url.hostname in ["youtu.be"]:
        return parsed_url.path.lstrip("/")
    
    return None

def is_timestamp_comment(text):
    """
    Checks if a comment contains only timestamps or YouTube links.
    """
    timestamp_pattern = r'^(\d{1,2}:\d{2}(:\d{2})?(\s*[apAP][mM])?)$'  # Matches HH:MM, HH:MM:SS, with optional AM/PM
    youtube_timestamp_pattern = r'https?://www\.youtube\.com/watch\?v=[\w-]+&t=\d+s?'
    numeric_pattern = r'^(\d{1,4})$'  # Matches numbers like "123" which could be a timestamp reference
    embedded_timestamp_pattern = r'<a href="[^"]+">\d{1,2}:\d{2}(:\d{2})?</a>'  # Matches embedded timestamp links

    return (re.match(timestamp_pattern, text) or 
            re.search(youtube_timestamp_pattern, text) or 
            re.match(numeric_pattern, text) or 
            re.search(embedded_timestamp_pattern, text))

def get_youtube_comments(video_id):
    """
    Fetches YouTube comments for the given video ID.
    Filters out comments that are just timestamps or links.
    """
    url = "https://youtube.googleapis.com/youtube/v3/commentThreads"
    params = {
        "part": "snippet",
        "videoId": video_id,
        "maxResults": 100,
        "key": YOUTUBE_API_KEY
    }

    response = requests.get(url, params=params)
    
    if response.status_code != 200:
        return [], {"Positive": 0, "Neutral": 0, "Negative": 0}

    comments = []
    sentiment_counts = {"Positive": 0, "Neutral": 0, "Negative": 0}

    data = response.json()
    
    for item in data.get("items", []):
        comment_text = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"].strip()

        # Skip timestamp-only comments
        if is_timestamp_comment(comment_text):
            continue  

        sentiment = analyze_sentiment(comment_text)

        # Count sentiments
        sentiment_counts[sentiment] += 1

        comments.append({"text": comment_text, "sentiment": sentiment})

    return comments, sentiment_counts

def analyze_sentiment(text):
    """
    Performs sentiment analysis using VADER.
    """
    sentiment_score = analyzer.polarity_scores(text)["compound"]

    if sentiment_score >= 0.05:
        return "Positive"
    elif sentiment_score <= -0.05:
        return "Negative"
    return "Neutral"

@app.route("/", methods=["GET", "POST"])
def index():
    video_id = None
    results = []
    sentiments = {"Positive": 0, "Neutral": 0, "Negative": 0}

    if request.method == "POST":
        youtube_url = request.form.get("youtube_url")
        video_id = extract_video_id(youtube_url)

        if video_id:
            results, sentiments = get_youtube_comments(video_id)

    return render_template("index.html", results=results, sentiments=sentiments, video_id=video_id)

if __name__ == "__main__":
    app.run(debug=True)
