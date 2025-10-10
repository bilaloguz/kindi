#!/bin/bash
# Auto-sync database to GitHub for Pages updates

cd /home/bilal/Desktop/dev/kriptoloji

# Check if database has changes
if git diff --quiet crawler_data/turkish_syllables.db; then
    echo "No database changes to sync"
    exit 0
fi

# Sync database and export data
echo "Syncing database changes..."
git add crawler_data/turkish_syllables.db
python3 export_to_pages.py
git add docs/data.json
git commit -m "data: auto-sync database and export [$(date +'%Y-%m-%d %H:%M')]"
git push

echo "Database synced to GitHub"

