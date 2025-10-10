# Kindi - Türkçe Sıklık Analizi

Turkish syllable frequency analyzer with real-time web dashboard.

## Features

- **Turkish Syllabification**: Rule-based algorithm for 5 Turkish syllable patterns (V, VC, CV, CVC, CVCC)
- **Web Crawler**: Continuous crawler for Turkish websites
- **N-gram Analysis**: Tracks monographs, digraphs, trigraphs, and syllables
- **Real-time Dashboard**: Local Flask dashboard at http://localhost:5000
- **GitHub Pages**: Public dashboard at https://bilaloguz.github.io/kindi/

## Architecture

### Local Components
- `turkish_hyphenation.py` - Main crawler and syllabification engine
- `dashboard.py` - Local Flask dashboard
- `crawler_data/turkish_syllables.db` - SQLite database

### GitHub Pages Components
- `docs/index.html` - Static dashboard
- `docs/data.json` - Exported data snapshot
- `.github/workflows/update-pages.yml` - Auto-refresh workflow (every 15 min)

### Auto-Sync
- `sync_database.sh` - Syncs local database to GitHub
- Cron job runs every 15 minutes: `*/15 * * * *`
- GitHub Action exports data.json every 15 minutes

## Running Locally

```bash
# Start crawler (in one terminal)
python3 turkish_hyphenation.py

# Start dashboard (in another terminal)
python3 dashboard.py
```

Visit: http://localhost:5000

## Deployment

The GitHub Pages dashboard updates automatically:
1. Local cron job syncs `crawler_data/turkish_syllables.db` to GitHub every 15 min
2. GitHub Action runs `export_to_pages.py` every 15 min
3. Static dashboard polls `docs/data.json` every 5 seconds

Manual sync:
```bash
./sync_database.sh
```

## Data Flow

```
Local Crawler → SQLite DB → (cron) → GitHub Repo → (Action) → data.json → GitHub Pages
```

## Database Schema

- `syllables`: syllable, frequency, last_word, last_url
- `monographs`: monograph, frequency, last_word, last_url  
- `digraphs`: digraph, frequency, last_word, last_url
- `trigraphs`: trigraph, frequency, last_word, last_url
- `words`: word
- `visited_urls`: url, visited_at
- `url_queue`: url

## License

MIT
