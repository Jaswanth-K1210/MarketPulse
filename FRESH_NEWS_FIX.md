# Fresh News Articles Fix

## Problem
The dashboard was showing static/old news articles instead of fresh data from the backend, even though the backend was successfully fetching 22+ new articles.

## Root Causes

1. **Articles only saved when alerts generated**: Articles were only saved to the database inside `pipeline.process_article()` when an alert was successfully created. When Gemini API limit was reached, processing failed and articles were never saved.

2. **No sorting by date**: The `get_all_articles()` method returned articles in insertion order (oldest first), not by publication date.

3. **No fallback for Gemini failures**: When Gemini API limit was reached, there was no way to fetch and save articles without processing.

## Solutions Implemented

### 1. Save Articles Immediately After Fetching
- **Location**: `app/api/routes.py` - `/fetch-and-analyze` endpoint
- **Change**: Articles are now saved to database immediately after fetching, BEFORE processing
- **Benefit**: Fresh articles are available in dashboard even if Gemini processing fails

```python
# CRITICAL: Save ALL articles to database immediately (before processing)
logger.info("💾 Saving articles to database...")
articles_saved = 0
for article in articles:
    try:
        database.save_article(article)
        articles_saved += 1
    except Exception as e:
        logger.warning(f"Failed to save article: {str(e)}")
```

### 2. Sort Articles by Most Recent First
- **Location**: `app/services/database.py` - `get_all_articles()` method
- **Change**: Articles are now sorted by `published_at` descending (most recent first)
- **Benefit**: Dashboard always shows the latest news first

```python
def get_all_articles(self, limit: int = 100) -> List[Article]:
    """Get all articles, sorted by most recent first"""
    articles = self._read_file(ARTICLES_DB)
    article_objects = [Article.from_dict(a) for a in articles]
    # Sort by published_at descending (most recent first)
    article_objects.sort(key=lambda x: x.published_at, reverse=True)
    return article_objects[:limit]
```

### 3. Added "Fetch News Only" Endpoint
- **Location**: `app/api/routes.py` - `/fetch-news` endpoint
- **Change**: New endpoint that fetches and saves articles WITHOUT processing
- **Benefit**: Can get fresh articles even when Gemini API limit is reached

### 4. Updated Background Task
- **Location**: `app/main.py` - `news_monitoring_task()`
- **Change**: Background task now saves articles immediately after fetching
- **Benefit**: Fresh articles available even if background processing fails

### 5. Frontend Improvements
- **Location**: `frontend/src/pages/Dashboard.jsx`
- **Changes**:
  - Always refresh articles after fetch-and-analyze
  - Added "Fetch News Only" button for when Gemini limit is reached
  - Better error handling and user feedback

## How to Use

### Normal Operation (Gemini Available)
1. Click "Fetch & Analyze News (10 articles)"
2. Articles are fetched, saved immediately, then processed
3. Dashboard refreshes to show fresh articles

### When Gemini Limit Reached
1. Click "Fetch News Only (No AI)" button
2. Articles are fetched and saved without processing
3. Dashboard shows fresh articles (no alerts generated)

### Automatic Background Updates
- Background task runs every 5 minutes
- Articles are saved immediately after fetching
- Processing happens in background (may fail if Gemini limit reached)
- Dashboard always has access to fresh articles

## Testing

1. **Test fresh articles**:
   ```bash
   # Backend fetches 22 articles
   python3 test_pipeline_live.py
   
   # Dashboard should show 10 most recent articles
   # Refresh dashboard to see new articles
   ```

2. **Test with Gemini limit**:
   - Click "Fetch News Only" button
   - Articles should appear in dashboard
   - No alerts generated (expected)

3. **Verify sorting**:
   - Check that newest articles appear first
   - Articles should be sorted by published_at descending

## Notes

- Duplicate prevention: `save_article()` checks for existing URLs, so it's safe to call multiple times
- Articles are saved even if processing fails
- Dashboard always shows most recent articles first
- Background task continues to work even if Gemini limit is reached

