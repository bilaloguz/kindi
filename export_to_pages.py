#!/usr/bin/env python3
import json
import os
import sqlite3
from datetime import datetime, timezone

DB_PATH = os.path.join('crawler_data', 'turkish_syllables.db')
OUT_PATH = os.path.join('docs', 'data.json')


def dict_from_row(row):
    return {k: row[k] for k in row.keys()}


def main():
    if not os.path.exists(DB_PATH):
        raise SystemExit(f'Database not found: {DB_PATH}')

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    stats = {
        'pages': cur.execute('SELECT COUNT(*) FROM visited_urls').fetchone()[0],
        'words': cur.execute('SELECT COUNT(*) FROM words').fetchone()[0],
        'queue': cur.execute('SELECT COUNT(*) FROM url_queue').fetchone()[0],
        'syllables': {
            'unique': cur.execute('SELECT COUNT(*) FROM syllables').fetchone()[0],
            'total': cur.execute('SELECT COALESCE(SUM(frequency),0) FROM syllables').fetchone()[0],
        },
        'monographs': {
            'unique': cur.execute('SELECT COUNT(*) FROM monographs').fetchone()[0],
            'total': cur.execute('SELECT COALESCE(SUM(frequency),0) FROM monographs').fetchone()[0],
        },
        'digraphs': {
            'unique': cur.execute('SELECT COUNT(*) FROM digraphs').fetchone()[0],
            'total': cur.execute('SELECT COALESCE(SUM(frequency),0) FROM digraphs').fetchone()[0],
        },
        'trigraphs': {
            'unique': cur.execute('SELECT COUNT(*) FROM trigraphs').fetchone()[0],
            'total': cur.execute('SELECT COALESCE(SUM(frequency),0) FROM trigraphs').fetchone()[0],
        },
    }

    top_syllables = [dict_from_row(r) for r in cur.execute(
        'SELECT syllable, frequency, last_word FROM syllables ORDER BY frequency DESC LIMIT 20'
    ).fetchall()]
    top_monographs = [dict_from_row(r) for r in cur.execute(
        'SELECT monograph, frequency, last_word FROM monographs ORDER BY frequency DESC LIMIT 20'
    ).fetchall()]
    top_digraphs = [dict_from_row(r) for r in cur.execute(
        'SELECT digraph, frequency, last_word FROM digraphs ORDER BY frequency DESC LIMIT 20'
    ).fetchall()]
    top_trigraphs = [dict_from_row(r) for r in cur.execute(
        'SELECT trigraph, frequency, last_word FROM trigraphs ORDER BY frequency DESC LIMIT 20'
    ).fetchall()]
    random_words = [dict_from_row(r) for r in cur.execute(
        'SELECT word FROM words ORDER BY RANDOM() LIMIT 50'
    ).fetchall()]

    conn.close()

    payload = {
        'stats': stats,
        'top_syllables': top_syllables,
        'top_monographs': top_monographs,
        'top_digraphs': top_digraphs,
        'top_trigraphs': top_trigraphs,
        'random_words': random_words,
        'last_updated': datetime.now(timezone.utc).isoformat(),
    }

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False)

    print(f'Wrote {OUT_PATH}')


if __name__ == '__main__':
    main()


