
import os

routes_file = "/Users/apple/Documents/Projects/Marketpulse/MarketPulse/app/api/routes.py"

with open(routes_file, "r") as f:
    lines = f.readlines()

start_marker = "# Analyze each article with Gemini"
end_marker = "logger.info(f\"🎉 Alert generation complete! Created {alerts_generated} alerts\")"

start_idx = -1
end_idx = -1

for i, line in enumerate(lines):
    if start_marker in line:
        start_idx = i
    if end_marker in line and start_idx != -1:
        end_idx = i
        break

if start_idx != -1 and end_idx != -1:
    print(f"Found block: {start_idx} to {end_idx}")
    
    new_content = [
        "            # Analyze each article using the sophisticated 7-Stage Pipeline\n",
        "            from app.services.pipeline import Pipeline\n",
        "            from app.models.article import Article\n",
        "            from datetime import datetime\n",
        "            \n",
        "            pipeline = Pipeline()\n",
        "            alerts_generated = 0\n",
        "            \n",
        "            for article_data in articles[:5]:  # Limit to 5 most recent\n",
        "                try:\n",
        "                    # Convert to Article model\n",
        "                    article_obj = Article(\n",
        "                        title=article_data.get('title', 'Unknown'),\n",
        "                        url=article_data.get('url', 'http://unknown.com'),\n",
        "                        source=article_data.get('source', 'Unknown'),\n",
        "                        published_at=datetime.now(), # Default to now if missing\n",
        "                        content=article_data.get('content') or article_data.get('description', ''),\n",
        "                        companies_mentioned=[]\n",
        "                    )\n",
        "                    \n",
        "                    # Execute Pipeline (Validates -> Extracts Relations -> Infers Cascade -> Calculates Impact -> Saves Alert)\n",
        "                    logger.info(f\"🚀 Pipeline executing for: {article_obj.title[:50]}...\")\n",
        "                    alert = pipeline.process_article(article_obj)\n",
        "                    \n",
        "                    if alert:\n",
        "                        alerts_generated += 1\n",
        "                        logger.info(f\"✅ Generated alert: {alert.id}\")\n",
        "                    else:\n",
        "                        logger.info(f\"⏭️ No alert generated for article (Filtered/Low Confidence)\")\n",
        "                        \n",
        "                except Exception as e:\n",
        "                    logger.error(f\"Error processing article in pipeline: {e}\")\n",
        "                    continue\n",
        "            \n"
    ]
    
    # Replace
    new_lines = lines[:start_idx] + new_content + lines[end_idx:]
    
    with open(routes_file, "w") as f:
        f.writelines(new_lines)
    print("Successfully patched routes.py")

else:
    print("Could not find markers!")
