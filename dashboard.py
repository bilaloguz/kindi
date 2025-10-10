"""
Turkish Syllable Crawler - Real-time Dashboard
"""

from flask import Flask, render_template, jsonify
import sqlite3
import os

app = Flask(__name__)
DB_PATH = 'crawler_data/turkish_syllables.db'


def get_db_connection():
    """Get database connection."""
    if not os.path.exists(DB_PATH):
        return None
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('dashboard.html')


@app.route('/api/stats')
def get_stats():
    """API endpoint for real-time statistics."""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database not found'})
    
    cursor = conn.cursor()
    
    # Get overall stats
    stats = {
        'pages': cursor.execute('SELECT COUNT(*) FROM visited_urls').fetchone()[0],
        'words': cursor.execute('SELECT COUNT(*) FROM words').fetchone()[0],
        'queue': cursor.execute('SELECT COUNT(*) FROM url_queue').fetchone()[0],
        'syllables': {
            'unique': cursor.execute('SELECT COUNT(*) FROM syllables').fetchone()[0],
            'total': cursor.execute('SELECT SUM(frequency) FROM syllables').fetchone()[0] or 0
        },
        'monographs': {
            'unique': cursor.execute('SELECT COUNT(*) FROM monographs').fetchone()[0],
            'total': cursor.execute('SELECT SUM(frequency) FROM monographs').fetchone()[0] or 0
        },
        'digraphs': {
            'unique': cursor.execute('SELECT COUNT(*) FROM digraphs').fetchone()[0],
            'total': cursor.execute('SELECT SUM(frequency) FROM digraphs').fetchone()[0] or 0
        },
        'trigraphs': {
            'unique': cursor.execute('SELECT COUNT(*) FROM trigraphs').fetchone()[0],
            'total': cursor.execute('SELECT SUM(frequency) FROM trigraphs').fetchone()[0] or 0
        }
    }
    
    # Get top items for each category
    top_syllables = [dict(row) for row in cursor.execute(
        'SELECT syllable, frequency, last_word FROM syllables ORDER BY frequency DESC LIMIT 20'
    ).fetchall()]
    
    top_monographs = [dict(row) for row in cursor.execute(
        'SELECT monograph, frequency, last_word FROM monographs ORDER BY frequency DESC LIMIT 20'
    ).fetchall()]
    
    top_digraphs = [dict(row) for row in cursor.execute(
        'SELECT digraph, frequency, last_word FROM digraphs ORDER BY frequency DESC LIMIT 20'
    ).fetchall()]
    
    top_trigraphs = [dict(row) for row in cursor.execute(
        'SELECT trigraph, frequency, last_word FROM trigraphs ORDER BY frequency DESC LIMIT 20'
    ).fetchall()]
    
    # Get some random words
    random_words = [dict(row) for row in cursor.execute(
        'SELECT word FROM words ORDER BY RANDOM() LIMIT 50'
    ).fetchall()]
    
    conn.close()
    
    return jsonify({
        'stats': stats,
        'top_syllables': top_syllables,
        'top_monographs': top_monographs,
        'top_digraphs': top_digraphs,
        'top_trigraphs': top_trigraphs,
        'random_words': random_words
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)

