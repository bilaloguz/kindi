"""
Turkish Syllable Analysis System

1. Generate all possible Turkish syllables (V, VC, CV, CVC, CVCC)
2. Crawl Turkish websites to extract text
3. Syllabify words and count syllable frequencies
"""

from itertools import product
from collections import Counter
import requests
from bs4 import BeautifulSoup
import re
import time
import json
from urllib.parse import urljoin, urlparse
from datetime import datetime
import os
import sqlite3

# Turkish vowels (8 total)
VOWELS = ['a', 'e', 'ı', 'i', 'o', 'ö', 'u', 'ü']

# Turkish consonants (21 total)
CONSONANTS = ['b', 'c', 'ç', 'd', 'f', 'g', 'ğ', 'h', 'j', 'k', 'l', 'm', 'n', 'p', 'r', 's', 'ş', 't', 'v', 'y', 'z']


def generate_all_syllables():
    """
    Generate all possible Turkish syllables.
    
    Returns:
        List of all possible syllables
    """
    all_syllables = []
    
    # Pattern 1: V (vowel only)
    # Example: a, e, ı, i, o, ö, u, ü
    v_syllables = list(VOWELS)
    all_syllables.extend(v_syllables)
    
    # Pattern 2: VC (vowel + consonant)
    # Example: al, et, ın, is, ok, öp, ur, üş
    vc_syllables = [''.join(combo) for combo in product(VOWELS, CONSONANTS)]
    all_syllables.extend(vc_syllables)
    
    # Pattern 3: CV (consonant + vowel)
    # Example: ba, de, kı, mi, go, çö, su, tü
    cv_syllables = [''.join(combo) for combo in product(CONSONANTS, VOWELS)]
    all_syllables.extend(cv_syllables)
    
    # Pattern 4: CVC (consonant + vowel + consonant)
    # Example: bal, det, kın, mis, gol, çöp, sun, tüm
    cvc_syllables = [''.join(combo) for combo in product(CONSONANTS, VOWELS, CONSONANTS)]
    all_syllables.extend(cvc_syllables)
    
    # Pattern 5: CVCC (consonant + vowel + consonant + consonant)
    # Example: balk, dert, kırk, mist, sarf, türk
    cvcc_syllables = [''.join(combo) for combo in product(CONSONANTS, VOWELS, CONSONANTS, CONSONANTS)]
    all_syllables.extend(cvcc_syllables)
    
    return all_syllables


def syllabify_word(word, all_syllables_set):
    """
    Split a Turkish word into syllables using dynamic programming.
    
    Args:
        word: The word to syllabify (lowercase)
        all_syllables_set: Set of all valid syllables for fast lookup
    
    Returns:
        List of syllables if successful, None if word cannot be syllabified
    """
    word = word.lower()
    n = len(word)
    
    # dp[i] will store the list of syllables for word[0:i]
    dp = [None] * (n + 1)
    dp[0] = []  # Empty word has empty syllabification
    
    for i in range(1, n + 1):
        # Try all possible last syllables ending at position i
        for j in range(max(0, i - 4), i):  # Max syllable length is 4 (CVCC)
            syllable = word[j:i]
            if syllable in all_syllables_set and dp[j] is not None:
                dp[i] = dp[j] + [syllable]
                break  # Use the first valid solution (greedy)
    
    return dp[n]


class ContinuousCrawler:
    """
    Continuous web crawler with SQLite database storage.
    
    Database Schema:
    - syllables: syllable TEXT PRIMARY KEY, frequency INTEGER, last_word TEXT, last_url TEXT
    - monographs: monograph TEXT PRIMARY KEY, frequency INTEGER, last_word TEXT, last_url TEXT
    - digraphs: digraph TEXT PRIMARY KEY, frequency INTEGER, last_word TEXT, last_url TEXT
    - trigraphs: trigraph TEXT PRIMARY KEY, frequency INTEGER, last_word TEXT, last_url TEXT
    - words: word TEXT PRIMARY KEY (unique Turkish words)
    - visited_urls: url TEXT PRIMARY KEY, crawled_at TEXT
    - url_queue: id INTEGER PRIMARY KEY AUTOINCREMENT, url TEXT UNIQUE
    """
    
    def __init__(self, all_syllables_set, db_path='crawler_data/turkish_syllables.db'):
        self.all_syllables_set = all_syllables_set
        self.db_path = db_path
        
        # Create data directory
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Initialize database
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_database()
        
        self.stats = self._get_stats()
    
    def _init_database(self):
        """Create database tables if they don't exist."""
        cursor = self.conn.cursor()
        
        # Syllables table: tracks each syllable's frequency and last occurrence
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS syllables (
                syllable TEXT PRIMARY KEY,
                frequency INTEGER DEFAULT 0,
                last_word TEXT,
                last_url TEXT
            )
        ''')
        
        # Monographs table: single letters
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS monographs (
                monograph TEXT PRIMARY KEY,
                frequency INTEGER DEFAULT 0,
                last_word TEXT,
                last_url TEXT
            )
        ''')
        
        # Digraphs table: two-letter combinations
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS digraphs (
                digraph TEXT PRIMARY KEY,
                frequency INTEGER DEFAULT 0,
                last_word TEXT,
                last_url TEXT
            )
        ''')
        
        # Trigraphs table: three-letter combinations
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trigraphs (
                trigraph TEXT PRIMARY KEY,
                frequency INTEGER DEFAULT 0,
                last_word TEXT,
                last_url TEXT
            )
        ''')
        
        # Words table: all unique Turkish words encountered
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS words (
                word TEXT PRIMARY KEY
            )
        ''')
        
        # Visited URLs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS visited_urls (
                url TEXT PRIMARY KEY,
                crawled_at TEXT
            )
        ''')
        
        # URL queue table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS url_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE
            )
        ''')
        
        # Create indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_syllable_freq ON syllables(frequency DESC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_monograph_freq ON monographs(frequency DESC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_digraph_freq ON digraphs(frequency DESC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trigraph_freq ON trigraphs(frequency DESC)')
        
        self.conn.commit()
    
    def __del__(self):
        """Close database connection on cleanup."""
        if hasattr(self, 'conn'):
            self.conn.close()
    
    def _get_stats(self):
        """Get current statistics from database."""
        cursor = self.conn.cursor()
        
        syllable_count = cursor.execute('SELECT COUNT(*) FROM syllables').fetchone()[0]
        monograph_count = cursor.execute('SELECT COUNT(*) FROM monographs').fetchone()[0]
        digraph_count = cursor.execute('SELECT COUNT(*) FROM digraphs').fetchone()[0]
        trigraph_count = cursor.execute('SELECT COUNT(*) FROM trigraphs').fetchone()[0]
        word_count = cursor.execute('SELECT COUNT(*) FROM words').fetchone()[0]
        visited_count = cursor.execute('SELECT COUNT(*) FROM visited_urls').fetchone()[0]
        queue_count = cursor.execute('SELECT COUNT(*) FROM url_queue').fetchone()[0]
        total_syll_freq = cursor.execute('SELECT SUM(frequency) FROM syllables').fetchone()[0] or 0
        total_mono_freq = cursor.execute('SELECT SUM(frequency) FROM monographs').fetchone()[0] or 0
        total_di_freq = cursor.execute('SELECT SUM(frequency) FROM digraphs').fetchone()[0] or 0
        total_tri_freq = cursor.execute('SELECT SUM(frequency) FROM trigraphs').fetchone()[0] or 0
        
        return {
            'pages_crawled': visited_count,
            'syllables_found': syllable_count,
            'monographs_found': monograph_count,
            'digraphs_found': digraph_count,
            'trigraphs_found': trigraph_count,
            'words_found': word_count,
            'queue_size': queue_count,
            'total_syllable_occurrences': total_syll_freq,
            'total_monograph_occurrences': total_mono_freq,
            'total_digraph_occurrences': total_di_freq,
            'total_trigraph_occurrences': total_tri_freq
        }
    
    def _is_url_visited(self, url):
        """Check if URL has been visited."""
        cursor = self.conn.cursor()
        result = cursor.execute('SELECT 1 FROM visited_urls WHERE url = ?', (url,)).fetchone()
        return result is not None
    
    def _mark_url_visited(self, url):
        """Mark URL as visited."""
        cursor = self.conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO visited_urls (url, crawled_at) VALUES (?, ?)',
                      (url, datetime.now().isoformat()))
        self.conn.commit()
    
    def _add_urls_to_queue(self, urls):
        """Add URLs to queue."""
        cursor = self.conn.cursor()
        for url in urls:
            try:
                cursor.execute('INSERT OR IGNORE INTO url_queue (url) VALUES (?)', (url,))
            except:
                pass
        self.conn.commit()
    
    def _get_next_url(self):
        """Get next URL from queue and remove it."""
        cursor = self.conn.cursor()
        result = cursor.execute('SELECT id, url FROM url_queue ORDER BY id LIMIT 1').fetchone()
        if result:
            url_id, url = result['id'], result['url']
            cursor.execute('DELETE FROM url_queue WHERE id = ?', (url_id,))
            self.conn.commit()
            return url
        return None
    
    def _update_syllable(self, syllable, word, url):
        """Update syllable frequency and last occurrence."""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO syllables (syllable, frequency, last_word, last_url)
            VALUES (?, 1, ?, ?)
            ON CONFLICT(syllable) DO UPDATE SET
                frequency = frequency + 1,
                last_word = excluded.last_word,
                last_url = excluded.last_url
        ''', (syllable, word, url))
    
    def _update_monograph(self, monograph, word, url):
        """Update monograph frequency and last occurrence."""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO monographs (monograph, frequency, last_word, last_url)
            VALUES (?, 1, ?, ?)
            ON CONFLICT(monograph) DO UPDATE SET
                frequency = frequency + 1,
                last_word = excluded.last_word,
                last_url = excluded.last_url
        ''', (monograph, word, url))
    
    def _update_digraph(self, digraph, word, url):
        """Update digraph frequency and last occurrence."""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO digraphs (digraph, frequency, last_word, last_url)
            VALUES (?, 1, ?, ?)
            ON CONFLICT(digraph) DO UPDATE SET
                frequency = frequency + 1,
                last_word = excluded.last_word,
                last_url = excluded.last_url
        ''', (digraph, word, url))
    
    def _update_trigraph(self, trigraph, word, url):
        """Update trigraph frequency and last occurrence."""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO trigraphs (trigraph, frequency, last_word, last_url)
            VALUES (?, 1, ?, ?)
            ON CONFLICT(trigraph) DO UPDATE SET
                frequency = frequency + 1,
                last_word = excluded.last_word,
                last_url = excluded.last_url
        ''', (trigraph, word, url))
    
    def _extract_monographs(self, word):
        """Extract all single letters from a word."""
        return list(word)
    
    def _extract_digraphs(self, word):
        """Extract all two-letter combinations from a word."""
        digraphs = []
        for i in range(len(word) - 1):
            digraphs.append(word[i:i+2])
        return digraphs
    
    def _extract_trigraphs(self, word):
        """Extract all three-letter combinations from a word."""
        trigraphs = []
        for i in range(len(word) - 2):
            trigraphs.append(word[i:i+3])
        return trigraphs
    
    
    def is_turkish_domain(self, url):
        """Check if URL is likely Turkish content."""
        turkish_patterns = [
            '.tr/', '.tr?', '.tr#',  # Turkish TLD
            'tr.wikipedia.org',
            '/tr/', '/tr?',  # Turkish language path
            'turkish', 'turkiye', 'istanbul'
        ]
        url_lower = url.lower()
        return any(pattern in url_lower for pattern in turkish_patterns)
    
    def extract_links(self, soup, base_url):
        """Extract valid Turkish links from a page."""
        links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            # Make absolute URL
            absolute_url = urljoin(base_url, href)
            
            # Parse URL
            parsed = urlparse(absolute_url)
            
            # Filter: same domain or Turkish content
            base_domain = urlparse(base_url).netloc
            link_domain = parsed.netloc
            
            # Keep if same domain or Turkish-related
            if (link_domain == base_domain or self.is_turkish_domain(absolute_url)) and \
               parsed.scheme in ['http', 'https'] and \
               not self._is_url_visited(absolute_url):
                links.append(absolute_url)
        
        return links[:50]  # Limit to 50 new links per page
    
    def crawl_page(self, url):
        """
        Crawl a single page and extract text and links.
        
        Returns:
            (text, links) tuple
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract links before cleaning
            links = self.extract_links(soup, url)
            
            # Remove script and style elements
            for script in soup(['script', 'style', 'nav', 'footer', 'header']):
                script.decompose()
            
            # Get text with proper spacing between elements
            text = soup.get_text(separator=' ', strip=True)
            
            # Clean up extra whitespace
            text = ' '.join(text.split())
            
            return text, links
        except Exception as e:
            print(f"Error crawling {url}: {e}")
            return "", []
    
    def process_text(self, text, url):
        """Process text and update syllable/digraph frequencies and words in database."""
        # Extract words with original case to identify proper names
        words_with_case = extract_words(text, preserve_case=True)
        unique_words = set(words_with_case)
        
        cursor = self.conn.cursor()
        words_processed = 0
        
        for word in unique_words:
            # Skip proper names (capitalized words)
            if word and word[0].isupper():
                continue
            
            # Convert to lowercase for processing
            word_lower = word.lower()
            syllables = syllabify_word(word_lower, self.all_syllables_set)
            
            if syllables:
                # Successfully syllabified - it's Turkish!
                # Add word to words table
                cursor.execute('INSERT OR IGNORE INTO words (word) VALUES (?)', (word_lower,))
                
                # Update syllable frequencies
                for syllable in syllables:
                    self._update_syllable(syllable, word_lower, url)
                
                # Extract and update monographs (single letters)
                monographs = self._extract_monographs(word_lower)
                for monograph in monographs:
                    self._update_monograph(monograph, word_lower, url)
                
                # Extract and update digraphs (two-letter combinations)
                digraphs = self._extract_digraphs(word_lower)
                for digraph in digraphs:
                    self._update_digraph(digraph, word_lower, url)
                
                # Extract and update trigraphs (three-letter combinations)
                trigraphs = self._extract_trigraphs(word_lower)
                for trigraph in trigraphs:
                    self._update_trigraph(trigraph, word_lower, url)
                
                words_processed += 1
            # If syllabification fails, skip the word (it's not Turkish)
        
        self.conn.commit()
        return words_processed
    
    def crawl_continuous(self, seed_urls, max_pages=100, save_interval=10):
        """
        Crawl continuously starting from seed URLs.
        
        Args:
            seed_urls: List of initial URLs to start crawling
            max_pages: Maximum number of pages to crawl (0 = unlimited)
            save_interval: Commit to database every N pages
        """
        # Add seed URLs to queue
        self._add_urls_to_queue(seed_urls)
        
        # Refresh stats
        self.stats = self._get_stats()
        
        print(f"\n{'='*70}")
        print(f"CONTINUOUS CRAWLER STARTED")
        print(f"{'='*70}")
        print(f"Initial queue size: {self.stats['queue_size']}")
        print(f"Already visited: {self.stats['pages_crawled']}")
        print(f"Turkish words: {self.stats['words_found']}")
        print(f"Syllables: {self.stats['syllables_found']} ({self.stats['total_syllable_occurrences']}x)")
        print(f"Monographs: {self.stats['monographs_found']} ({self.stats['total_monograph_occurrences']}x)")
        print(f"Digraphs: {self.stats['digraphs_found']} ({self.stats['total_digraph_occurrences']}x)")
        print(f"Trigraphs: {self.stats['trigraphs_found']} ({self.stats['total_trigraph_occurrences']}x)")
        print(f"Max pages: {max_pages if max_pages > 0 else 'unlimited'}")
        print(f"Database: {self.db_path}")
        print(f"{'='*70}\n")
        
        pages_this_session = 0
        
        try:
            while True:
                # Check max pages limit
                if max_pages > 0 and pages_this_session >= max_pages:
                    print(f"\nReached max pages limit ({max_pages})")
                    break
                
                # Get next URL
                url = self._get_next_url()
                if not url:
                    print("\nNo more URLs in queue!")
                    break
                
                # Skip if already visited
                if self._is_url_visited(url):
                    continue
                
                # Crawl page
                pages_this_session += 1
                print(f"\n[{pages_this_session}] Crawling: {url[:80]}...")
                text, links = self.crawl_page(url)
                
                # Mark as visited
                self._mark_url_visited(url)
                
                # Process text
                if text:
                    words_added = self.process_text(text, url)
                    print(f"  ✓ Extracted {len(text)} chars, {words_added} Turkish words")
                
                # Add new links to queue
                if links:
                    self._add_urls_to_queue(links)
                    print(f"  ✓ Found {len(links)} new links")
                
                # Refresh stats and display
                if pages_this_session % save_interval == 0:
                    self.stats = self._get_stats()
                    print(f"  💾 Database committed!")
                
                self.stats = self._get_stats()
                print(f"  📊 Syl: {self.stats['syllables_found']} ({self.stats['total_syllable_occurrences']}x) | " +
                      f"1g: {self.stats['monographs_found']} | 2g: {self.stats['digraphs_found']} | 3g: {self.stats['trigraphs_found']} | " +
                      f"Words: {self.stats['words_found']}")
                
                # Be polite to servers
                time.sleep(1)
        
        except KeyboardInterrupt:
            print(f"\n\n⚠️  Interrupted by user")
        
        finally:
            # Final commit
            self.conn.commit()
            self._print_final_stats(pages_this_session)
    
    def _print_final_stats(self, pages_this_session):
        """Print final statistics from database."""
        cursor = self.conn.cursor()
        
        # Get top items for each n-graph type
        top_syllables = cursor.execute('SELECT syllable, frequency, last_word FROM syllables ORDER BY frequency DESC LIMIT 15').fetchall()
        top_monographs = cursor.execute('SELECT monograph, frequency, last_word FROM monographs ORDER BY frequency DESC LIMIT 15').fetchall()
        top_digraphs = cursor.execute('SELECT digraph, frequency, last_word FROM digraphs ORDER BY frequency DESC LIMIT 15').fetchall()
        top_trigraphs = cursor.execute('SELECT trigraph, frequency, last_word FROM trigraphs ORDER BY frequency DESC LIMIT 15').fetchall()
        
        print(f"\n{'='*70}")
        print(f"CRAWLING SESSION COMPLETED")
        print(f"{'='*70}")
        print(f"Pages this session: {pages_this_session} | Total: {self.stats['pages_crawled']}")
        print(f"Turkish words: {self.stats['words_found']}")
        print(f"Syllables: {self.stats['syllables_found']} ({self.stats['total_syllable_occurrences']}x)")
        print(f"Monographs (1-letter): {self.stats['monographs_found']} ({self.stats['total_monograph_occurrences']}x)")
        print(f"Digraphs (2-letter): {self.stats['digraphs_found']} ({self.stats['total_digraph_occurrences']}x)")
        print(f"Trigraphs (3-letter): {self.stats['trigraphs_found']} ({self.stats['total_trigraph_occurrences']}x)")
        print(f"Queue: {self.stats['queue_size']}")
        
        print(f"\n{'Top 15 SYLLABLES':<25} | {'Top 15 MONOGRAPHS':<25} | {'Top 15 DIGRAPHS':<25} | {'Top 15 TRIGRAPHS'}")
        print(f"{'-'*115}")
        for i in range(15):
            s = top_syllables[i] if i < len(top_syllables) else {'syllable': '', 'frequency': ''}
            m = top_monographs[i] if i < len(top_monographs) else {'monograph': '', 'frequency': ''}
            d = top_digraphs[i] if i < len(top_digraphs) else {'digraph': '', 'frequency': ''}
            t = top_trigraphs[i] if i < len(top_trigraphs) else {'trigraph': '', 'frequency': ''}
            print(f"{i+1:2}. {str(s['syllable']):<5} {str(s['frequency']):>6}x | " +
                  f"{str(m['monograph']):<5} {str(m['frequency']):>6}x | " +
                  f"{str(d['digraph']):<5} {str(d['frequency']):>6}x | " +
                  f"{str(t['trigraph']):<5} {str(t['frequency']):>6}x")
        
        print(f"{'='*70}")
        print(f"Database: {self.db_path}")
        print(f"{'='*70}\n")


def crawl_turkish_website(url, max_pages=1):
    """
    Crawl a Turkish website and extract text (legacy function).
    
    Args:
        url: The URL to crawl
        max_pages: Maximum number of pages to crawl
    
    Returns:
        Extracted text as a string
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script and style elements
        for script in soup(['script', 'style', 'nav', 'footer', 'header']):
            script.decompose()
        
        # Get text with proper spacing between elements
        text = soup.get_text(separator=' ', strip=True)
        
        # Clean up extra whitespace
        text = ' '.join(text.split())
        
        return text
    except Exception as e:
        print(f"Error crawling {url}: {e}")
        return ""


def extract_words(text, preserve_case=False):
    """
    Extract Turkish words from text.
    
    Args:
        text: Input text
        preserve_case: If True, keep original case; if False, convert to lowercase
    
    Returns:
        List of words
    """
    # Turkish letters pattern
    turkish_pattern = r'[a-zA-ZçÇğĞıİöÖşŞüÜ]+'
    words = re.findall(turkish_pattern, text)
    
    if preserve_case:
        return [word for word in words if len(word) > 1]
    else:
        return [word.lower() for word in words if len(word) > 1]


def analyze_syllables(words, all_syllables_set):
    """
    Analyze syllable frequencies from a list of words.
    
    Args:
        words: List of words to analyze
        all_syllables_set: Set of all valid syllables
    
    Returns:
        Counter object with syllable frequencies
    """
    syllable_counter = Counter()
    successful = 0
    failed = 0
    
    for word in words:
        syllables = syllabify_word(word, all_syllables_set)
        if syllables:
            syllable_counter.update(syllables)
            successful += 1
        else:
            failed += 1
    
    print(f"Successfully syllabified: {successful} words")
    print(f"Failed: {failed} words")
    
    return syllable_counter


def print_statistics(syllables_list):
    """Print statistics about generated syllables."""
    print("Turkish Syllable Generation")
    print("=" * 60)
    print(f"Vowels ({len(VOWELS)}): {', '.join(VOWELS)}")
    print(f"Consonants ({len(CONSONANTS)}): {', '.join(CONSONANTS)}")
    print("\n" + "=" * 60)
    
    # Calculate counts for each pattern
    v_count = len(VOWELS)
    vc_count = len(VOWELS) * len(CONSONANTS)
    cv_count = len(CONSONANTS) * len(VOWELS)
    cvc_count = len(CONSONANTS) * len(VOWELS) * len(CONSONANTS)
    cvcc_count = len(CONSONANTS) * len(VOWELS) * len(CONSONANTS) * len(CONSONANTS)
    
    print(f"V      pattern: {v_count:,} syllables")
    print(f"VC     pattern: {vc_count:,} syllables")
    print(f"CV     pattern: {cv_count:,} syllables")
    print(f"CVC    pattern: {cvc_count:,} syllables")
    print(f"CVCC   pattern: {cvcc_count:,} syllables")
    print("=" * 60)
    print(f"TOTAL: {len(syllables_list):,} possible Turkish syllables")
    print("=" * 60)


def crawl_and_analyze(urls, syllables_list):
    """
    Crawl Turkish websites and analyze syllable frequencies.
    
    Args:
        urls: List of URLs to crawl
        syllables_list: List of all possible syllables
    
    Returns:
        Counter object with syllable frequencies
    """
    print("\n" + "=" * 60)
    print("STEP 2: CRAWLING AND ANALYZING TURKISH TEXT")
    print("=" * 60)
    
    all_syllables_set = set(syllables_list)
    all_text = ""
    
    for url in urls:
        print(f"\nCrawling: {url}")
        text = crawl_turkish_website(url)
        all_text += " " + text
        print(f"Extracted {len(text)} characters")
        time.sleep(1)  # Be polite to servers
    
    print(f"\nTotal text length: {len(all_text)} characters")
    
    # Extract words
    words = extract_words(all_text)
    print(f"Extracted {len(words)} words")
    unique_words = list(set(words))
    print(f"Unique words: {len(unique_words)}")
    
    # Analyze syllables
    print("\nAnalyzing syllables...")
    syllable_freq = analyze_syllables(unique_words, all_syllables_set)
    
    print(f"\nFound {len(syllable_freq)} unique syllables in use")
    print(f"Out of {len(syllables_list)} possible syllables")
    print(f"Coverage: {len(syllable_freq)/len(syllables_list)*100:.2f}%")
    
    # Show top 20 most common syllables
    print("\nTop 20 most common syllables:")
    print("-" * 60)
    for syllable, count in syllable_freq.most_common(20):
        print(f"{syllable:6} : {count:5} times")
    
    return syllable_freq


def is_likely_turkish(word):
    """Check if a word is likely Turkish (contains Turkish-specific characters)."""
    turkish_specific = set('çğıöşüÇĞİÖŞÜ')
    # If word contains Turkish-specific chars, it's Turkish
    if any(c in turkish_specific for c in word):
        return True
    # If word is short and all lowercase, likely Turkish
    if len(word) <= 4 and word.islower():
        return True
    # Common Turkish suffixes
    turkish_suffixes = ['lar', 'ler', 'lık', 'lik', 'dır', 'dir', 'tir', 'tır', 
                        'miş', 'mış', 'muş', 'müş', 'de', 'da', 'te', 'ta',
                        'den', 'dan', 'ten', 'tan', 'ın', 'in', 'un', 'ün']
    if any(word.endswith(suffix) for suffix in turkish_suffixes):
        return True
    # Common English indicators (exclude)
    english_patterns = ['tion', 'ing', 'ness', 'ment', 'ful', 'less', 'ism', 'ist', 'phy', 'logy']
    if any(pattern in word for pattern in english_patterns):
        return False
    return True


def debug_single_page():
    """Debug mode: crawl one page and show all syllabifications (skip non-Turkish words)."""
    print("=" * 70)
    print("TURKISH SYLLABLE ANALYZER - DEBUG MODE (SINGLE PAGE)")
    print("=" * 70)
    
    # Step 1: Generate all possible syllables
    print("\nGenerating all possible Turkish syllables...")
    syllables = generate_all_syllables()
    syllables_set = set(syllables)
    print(f"✓ Generated {len(syllables):,} possible syllables\n")
    
    # Crawl one page
    url = "https://tr.wikipedia.org/wiki/Türkiye"
    print(f"Crawling: {url}\n")
    
    text = crawl_turkish_website(url)
    words = extract_words(text)
    all_unique = sorted(set(words))
    
    print(f"Found {len(all_unique)} unique words total")
    print(f"Syllabifying all words (skipping only non-Turkish)...\n")
    print("=" * 70)
    print(f"{'WORD':<25} | SYLLABIFICATION")
    print("=" * 70)
    
    successful = 0
    skipped = 0
    shown = 0
    
    for word in all_unique:
        result = syllabify_word(word, syllables_set)
        if result:
            if shown < 150:  # Show first 150 successfully syllabified words
                syllabification = '-'.join(result)
                print(f"{word:<25} | {syllabification}")
                shown += 1
            successful += 1
        else:
            skipped += 1
    
    print("=" * 70)
    print(f"\nTotal words analyzed: {len(all_unique)}")
    print(f"Turkish words (successfully syllabified): {successful}")
    print(f"Non-Turkish words (skipped): {skipped}")
    print(f"Success rate: {successful/len(all_unique)*100:.1f}%")


def main():
    """Main function with continuous crawler."""
    print("=" * 70)
    print("TURKISH SYLLABLE ANALYZER - CONTINUOUS CRAWLER")
    print("=" * 70)
    
    # Step 1: Generate all possible syllables
    print("\nSTEP 1: Generating all possible Turkish syllables...")
    syllables = generate_all_syllables()
    syllables_set = set(syllables)
    
    print(f"✓ Generated {len(syllables):,} possible syllables")
    print(f"  Patterns: V(8) + VC(168) + CV(168) + CVC(3,528) + CVCC(74,088)")
    
    # Test syllabification with some examples
    print("\nTesting syllabification with examples:")
    test_words = ["araba", "kitap", "merhaba", "türkiye", "bilgisayar", "istanbul"]
    for word in test_words:
        result = syllabify_word(word, syllables_set)
        if result:
            print(f"  {word:12} -> {'-'.join(result)}")
    
    # Step 2: Start continuous crawler
    print("\nSTEP 2: Starting continuous crawler...")
    
    # Seed URLs - Turkish Wikipedia
    seed_urls = [
        "https://tr.wikipedia.org/wiki/Türkiye",
        "https://tr.wikipedia.org/wiki/İstanbul",
        "https://tr.wikipedia.org/wiki/Ankara",
    ]
    
    # Create crawler instance
    crawler = ContinuousCrawler(syllables_set)
    
    # Start crawling (you can stop with Ctrl+C)
    crawler.crawl_continuous(
        seed_urls=seed_urls,
        max_pages=0,  # 0 = unlimited, crawl indefinitely
        save_interval=10  # Save every 10 pages
    )
    
    return syllables, crawler


if __name__ == "__main__":
    # Use debug mode to check syllabification (uncomment to test):
    # debug_single_page()
    
    # Continuous crawling mode:
    syllables, crawler = main()

