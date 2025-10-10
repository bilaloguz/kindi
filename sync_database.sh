#!/bin/bash
# Auto-sync database to GitHub for Pages updates

cd /home/bilal/Desktop/dev/kriptoloji

# Always sync database (crawler updates don't show in git diff for binary SQLite files)
echo "Syncing database..."
git add crawler_data/turkish_syllables.db
python3 export_to_pages.py
git add docs/data.json

# Only commit and push if there are actual changes
if git diff --staged --quiet; then
    echo "No changes to sync"
    exit 0
fi

git commit -m "data: auto-sync database and export [$(date +'%Y-%m-%d %H:%M')]"
git push

echo "Database synced to GitHub"

