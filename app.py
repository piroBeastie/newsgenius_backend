from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
load_dotenv()
import os
import google.generativeai as genai
import json
import requests
import datetime
import firebase_admin
from firebase_admin import credentials, firestore
import uuid
import logging
import xml.etree.ElementTree as ET
from urllib.parse import quote, urljoin, urlparse, parse_qs, unquote
import re
import time
import hashlib
import asyncio
import base64
from bs4 import BeautifulSoup

app = Flask(__name__)

# Enhanced CORS configuration to include production domains
CORS(app,
     origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:5173", 
              "http://127.0.0.1:5173", "https://newgenius-frontend.vercel.app"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization", "Accept", "Origin", "X-Requested-With"],
     supports_credentials=True
)


# Additional CORS handling for preflight requests with production domain
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = jsonify({'message': 'OK'})
        origin = request.headers.get('Origin', '')
        
        # Allow specific origins
        allowed_origins = ["http://localhost:3000", "http://localhost:3001", 
                          "http://localhost:5173", "http://127.0.0.1:5173", 
                          "https://newgenius-frontend.vercel.app"]
        
        if origin in allowed_origins:
            response.headers.add("Access-Control-Allow-Origin", origin)
        else:
            response.headers.add("Access-Control-Allow-Origin", "https://newgenius-frontend.vercel.app")
            
        response.headers.add('Access-Control-Allow-Headers', "Content-Type,Authorization,Accept,Origin,X-Requested-With")
        response.headers.add('Access-Control-Allow-Methods', "GET,POST,PUT,DELETE,OPTIONS")
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
service_account_key = json.loads(os.environ.get("FIREBASE_SERVICE_ACCOUNT_PATH"))

# --- Firebase Initialization ---
try:
    if not firebase_admin._apps:
        cred = credentials.Certificate(service_account_key)
        firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("Firebase initialized successfully.")
except Exception as e:
    print(f"Error initializing Firebase: {e}")

# --- Gemini Model Initialization ---
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('models/gemini-2.0-flash')

# --- Step 1: Use Gemini for Smart Keyword Generation ---
async def get_smart_keywords_with_gemini(user_prompt):
    """
    Use Gemini to generate intelligent search keywords for REAL news APIs
    """
    keyword_prompt = f"""
    You are a news search expert. Generate 6-8 precise search keywords that will help find REAL, current news articles about: "{user_prompt}"

    Rules:
    - Generate terms that actual news outlets use
    - Include both specific and broader terms
    - Focus on searchable, current terminology
    - Avoid generic words like "news", "latest", "breaking"

    Examples:
    For "gaming": ["video game industry", "gaming technology", "esports tournaments", "game development", "gaming market"]
    For "indian politics": ["India government", "Indian elections", "political parties India", "India parliament", "Indian policy"]

    Generate keywords for: "{user_prompt}"
    Return as JSON array.
    """
    
    try:
        response = model.generate_content(
            keyword_prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.2,
                max_output_tokens=200,
                response_mime_type="application/json"
            )
        )
        keywords = json.loads(response.text)
        logger.info(f"Generated keywords: {keywords}")
        return keywords[:8]
    except Exception as e:
        logger.error(f"Keyword generation failed: {e}")
        return [user_prompt, f"{user_prompt} news"]

# --- Step 2: Advanced Google News URL Decoding ---
def decode_google_news_url_advanced(encoded_url):
    """
    Advanced Google News URL decoding with multiple methods
    """
    try:
        logger.info(f"🔍 Advanced decoding: {encoded_url}")
        
        # Method 1: Extract article ID and try different decoding approaches
        if '/articles/' in encoded_url:
            article_id = encoded_url.split('/articles/')[-1].split('?')[0]
            
            # Try URL decoding first
            try:
                url_decoded = unquote(article_id)
                logger.info(f"URL decoded: {url_decoded}")
                
                # Look for URLs in the decoded string
                url_pattern = r'https?://[^\s<>"\']+[^\s<>"\'.,;!?]'
                urls = re.findall(url_pattern, url_decoded)
                for url in urls:
                    if 'google.com' not in url and len(url) > 20:
                        logger.info(f"✅ Found URL in decoded string: {url}")
                        return url
            except Exception as e:
                logger.debug(f"URL decoding failed: {e}")
            
            # Try base64 decoding with different padding
            for padding in ['', '=', '==', '===']:
                try:
                    padded_id = article_id + padding
                    decoded_bytes = base64.b64decode(padded_id)
                    decoded_str = decoded_bytes.decode('utf-8', errors='ignore')
                    
                    # Look for URLs in decoded content
                    url_pattern = r'https?://[^\s<>"\']+[^\s<>"\'.,;!?]'
                    urls = re.findall(url_pattern, decoded_str)
                    for url in urls:
                        if 'google.com' not in url and len(url) > 20:
                            logger.info(f"✅ Base64 decoded URL: {url}")
                            return url
                            
                except Exception as e:
                    continue
        
        return None
    except Exception as e:
        logger.error(f"Advanced URL decoding failed: {e}")
        return None

async def resolve_google_news_with_session(google_news_url):
    """
    Use requests session with enhanced headers to resolve Google News URLs
    """
    try:
        # Enhanced headers to mimic real browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'DNT': '1',
            'Sec-GPC': '1'
        }
        
        # Try to follow redirects with session
        session = requests.Session()
        session.headers.update(headers)
        
        # Make request with longer timeout
        response = session.get(google_news_url, allow_redirects=True, timeout=15)
        
        # Check if we got redirected to actual news site
        if 'news.google.com' not in response.url and response.url != google_news_url:
            logger.info(f"✅ Session redirect resolved to: {response.url}")
            return response.url
        
        # Parse the Google News page for original article links
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for various link patterns in the page
            link_selectors = [
                'a[href*="http"]:contains("Read full article")',
                'a[href*="http"]:contains("View full coverage")',
                'a[href*="http"][data-url]',
                'a[href*="http"][class*="article"]',
                'a[href*="http"]'
            ]
            
            for selector in link_selectors:
                try:
                    links = soup.select(selector)
                    for link in links:
                        href = link.get('href') or link.get('data-url')
                        if href and 'news.google.com' not in href and 'http' in href and len(href) > 20:
                            logger.info(f"✅ Found original link in page: {href}")
                            return href
                except:
                    continue
        
        return None
    except Exception as e:
        logger.error(f"Session-based resolution failed: {e}")
        return None

# --- Step 3: NewsAPI for Real Images ---
async def fetch_real_news_with_newsapi(keywords):
    """
    Use NewsAPI.org which provides real images from news sources
    """
    try:
        newsapi_key = os.environ.get("NEWSAPI_KEY")  # Get from newsapi.org
        
        if newsapi_key == "YOUR_NEWSAPI_KEY":
            logger.info("NewsAPI key not configured, skipping NewsAPI")
            return []
        
        newsapi_url = "https://newsapi.org/v2/everything"
        
        # Use keywords to search
        query = " OR ".join(keywords[:3])
        
        params = {
            'apiKey': newsapi_key,
            'q': query,
            'language': 'en',
            'sortBy': 'publishedAt',
            'pageSize': 20
        }
        
        response = requests.get(newsapi_url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        real_articles = []
        if data.get('status') == 'ok' and data.get('articles'):
            for item in data['articles']:
                if item.get('title') and item.get('description'):
                    real_articles.append({
                        'title': item.get('title'),
                        'description': item.get('description'),
                        'url': item.get('url'),
                        'urlToImage': item.get('urlToImage'),  # Real image from news source
                        'publishedAt': item.get('publishedAt'),
                        'source': {'name': item.get('source', {}).get('name', 'NewsAPI')},
                        'content': item.get('content', item.get('description')),
                        'isReal': True,
                        'hasRealImage': bool(item.get('urlToImage'))
                    })
        
        logger.info(f"NewsAPI found {len(real_articles)} articles with real images")
        return real_articles
    except Exception as e:
        logger.error(f"NewsAPI failed: {e}")
        return []

# --- Step 4: Enhanced Real Image Extraction ---
async def extract_real_image_aggressive(url, title):
    """
    Aggressively extract real images with multiple resolution methods
    """
    try:
        # Try advanced URL decoding first
        decoded_url = decode_google_news_url_advanced(url)
        if decoded_url:
            actual_url = decoded_url
        else:
            # Try session-based resolution
            session_resolved = await resolve_google_news_with_session(url)
            if session_resolved:
                actual_url = session_resolved
            else:
                actual_url = url
        
        # Skip if still on Google News
        if 'news.google.com' in actual_url:
            logger.warning(f"⚠️ Still on Google News after all resolution attempts")
            return None
        
        logger.info(f"🖼️ Extracting from resolved URL: {actual_url}")
        
        # Enhanced headers for image extraction
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Referer': 'https://news.google.com/'
        }
        
        response = requests.get(actual_url, headers=headers, timeout=20, allow_redirects=True)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Priority 1: OpenGraph image
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            image_url = og_image['content']
            if is_real_news_image(image_url):
                absolute_url = urljoin(response.url, image_url)
                logger.info(f"✅ Found OG image: {absolute_url}")
                return absolute_url
        
        # Priority 2: Twitter card image
        twitter_image = soup.find('meta', attrs={'name': 'twitter:image'})
        if twitter_image and twitter_image.get('content'):
            image_url = twitter_image['content']
            if is_real_news_image(image_url):
                absolute_url = urljoin(response.url, image_url)
                logger.info(f"✅ Found Twitter image: {absolute_url}")
                return absolute_url
        
        logger.warning(f"⚠️ No real images found in resolved article")
        return None
        
    except Exception as e:
        logger.error(f"❌ Aggressive image extraction failed: {e}")
        return None

def is_real_news_image(url):
    """Enhanced validation for real news images"""
    if not url or len(url) < 10:
        return False
    
    url_lower = url.lower()
    
    # Skip Google and other non-news images
    skip_patterns = [
        'google.com', 'gstatic.com', 'googleusercontent.com',
        'logo', 'icon', 'avatar', 'ad', 'banner', 'social', 'pixel',
        'tracking', 'button', 'badge', 'widget', 'placeholder',
        'facebook.com', 'twitter.com', 'instagram.com',
        'data:image', 'javascript:', 'mailto:', '#', '1x1',
        'transparent', 'favicon', 'sprite', 'blank', 'empty'
    ]
    
    if any(pattern in url_lower for pattern in skip_patterns):
        return False
    
    # Must have image indicators
    image_indicators = [
        '.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp',
        'images/', 'img/', 'photos/', 'media/', 'assets/',
        'cdn.', 'static.'
    ]
    
    has_image_indicator = any(indicator in url_lower for indicator in image_indicators)
    
    # Additional checks for news images
    news_indicators = [
        'wp-content', 'uploads', 'files', 'media',
        'images', 'photos', 'pictures'
    ]
    
    has_news_indicator = any(indicator in url_lower for indicator in news_indicators)
    
    return has_image_indicator or has_news_indicator

# --- Step 5: Pexels API (Fallback Only) ---
async def get_relevant_image_from_pexels(title, description=""):
    """
    Get contextually relevant images from Pexels API (fallback only)
    """
    try:
        # Extract key terms for search
        text = f"{title} {description}".lower()
        
        # Determine search terms based on content
        search_terms = []
        
        if any(word in text for word in ['politics', 'government', 'election', 'parliament', 'minister', 'congress', 'modi', 'bjp']):
            search_terms = ['government building', 'politics', 'parliament', 'democracy']
        elif any(word in text for word in ['business', 'economy', 'market', 'finance', 'economic', 'company']):
            search_terms = ['business meeting', 'finance', 'corporate', 'economy']
        elif any(word in text for word in ['technology', 'tech', 'ai', 'digital', 'software']):
            search_terms = ['technology', 'computer', 'digital', 'innovation']
        elif any(word in text for word in ['gaming', 'game', 'esports', 'video game']):
            search_terms = ['gaming', 'esports', 'video games', 'technology']
        elif any(word in text for word in ['health', 'medical', 'healthcare', 'medicine']):
            search_terms = ['healthcare', 'medical', 'hospital', 'health']
        elif any(word in text for word in ['sports', 'football', 'cricket', 'basketball']):
            search_terms = ['sports', 'stadium', 'athletics', 'competition']
        else:
            search_terms = ['news', 'journalism', 'media', 'information']
        
        # Try each search term
        for search_term in search_terms:
            try:
                # Pexels API (get free API key from pexels.com)
                pexels_api_key = os.environ.get("PEXELS_API_KEY")  # Replace with actual key from pexels.com/api
                
                if pexels_api_key == "YOUR_PEXELS_API_KEY":
                    # Skip Pexels if no API key
                    continue
                
                pexels_url = "https://api.pexels.com/v1/search"
                params = {
                    'query': search_term,
                    'per_page': 10,
                    'orientation': 'landscape'
                }
                headers = {
                    'Authorization': pexels_api_key
                }
                
                response = requests.get(pexels_url, headers=headers, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    photos = data.get('photos', [])
                    if photos:
                        # Select based on article title hash for consistency
                        title_hash = hashlib.md5(title.encode()).hexdigest()
                        photo_index = int(title_hash, 16) % len(photos)
                        selected_photo = photos[photo_index]
                        image_url = selected_photo['src']['large']
                        
                        logger.info(f"✅ Found Pexels image for '{search_term}': {image_url}")
                        return image_url
            except Exception as e:
                logger.debug(f"Pexels search failed for '{search_term}': {e}")
                continue
        
        return None
    except Exception as e:
        logger.error(f"Pexels API failed: {e}")
        return None

def get_contextual_placeholder_image(title, description=""):
    """
    Generate contextual placeholder images (absolute last resort)
    """
    try:
        text = f"{title} {description}".lower()
        
        if any(word in text for word in ['politics', 'government', 'election', 'parliament', 'minister']):
            return "https://images.unsplash.com/photo-1529107386315-e1a2ed48a620?w=800&h=450&fit=crop&q=80"
        elif any(word in text for word in ['business', 'economy', 'market', 'finance']):
            return "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=800&h=450&fit=crop&q=80"
        elif any(word in text for word in ['technology', 'tech', 'ai', 'digital']):
            return "https://images.unsplash.com/photo-1518709268805-4e9042af2176?w=800&h=450&fit=crop&q=80"
        elif any(word in text for word in ['gaming', 'game', 'esports']):
            return "https://images.unsplash.com/photo-1552820728-8b83bb6b773f?w=800&h=450&fit=crop&q=80"
        elif any(word in text for word in ['health', 'medical', 'healthcare']):
            return "https://images.unsplash.com/photo-1559757148-5c350d0d3c56?w=800&h=450&fit=crop&q=80"
        elif any(word in text for word in ['sports', 'football', 'cricket']):
            return "https://images.unsplash.com/photo-1461896836934-ffe607ba8211?w=800&h=450&fit=crop&q=80"
        else:
            return "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800&h=450&fit=crop&q=80"
    
    except Exception as e:
        return "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800&h=450&fit=crop&q=80"

# --- Step 6: Real Image Priority Strategy ---
async def get_real_image_priority(article):
    """
    Prioritize real images from actual news sources over stock images
    """
    title = article.get('title', '')
    url = article.get('url', '')
    existing_image = article.get('urlToImage')
    
    logger.info(f"🎯 REAL IMAGE PRIORITY for: {title[:50]}...")
    
    # Strategy 1: Use NewsData.io/NewsAPI real image
    if existing_image and is_real_news_image(existing_image):
        try:
            response = requests.head(existing_image, timeout=5)
            if response.status_code == 200:
                logger.info(f"✅ Using real source image")
                return {
                    'imageUrl': existing_image,
                    'source': 'source-real',
                    'relevance': 'high'
                }
        except:
            pass
    
    # Strategy 2: Aggressive extraction from resolved source
    if url:
        try:
            real_image = await extract_real_image_aggressive(url, title)
            if real_image:
                logger.info(f"✅ Extracted real image from source")
                return {
                    'imageUrl': real_image,
                    'source': 'extracted-real',
                    'relevance': 'high'
                }
        except Exception as e:
            logger.error(f"Real extraction failed: {e}")
    
    # Strategy 3: Only use Pexels as last resort
    logger.warning(f"⚠️ No real images found, falling back to Pexels")
    try:
        pexels_image = await get_relevant_image_from_pexels(title, article.get('description', ''))
        if pexels_image:
            return {
                'imageUrl': pexels_image,
                'source': 'pexels-fallback',
                'relevance': 'low'
            }
    except Exception as e:
        logger.error(f"Pexels fallback failed: {e}")
    
    # Strategy 4: Contextual placeholder (absolute last resort)
    return {
        'imageUrl': get_contextual_placeholder_image(title, article.get('description', '')),
        'source': 'placeholder',
        'relevance': 'low'
    }

# --- Step 7: RSS Parsing Functions ---
def parse_google_news_rss(rss_content):
    """Parse Google News RSS content"""
    try:
        root = ET.fromstring(rss_content)
        articles = []
        
        for item in root.findall('.//item'):
            title_elem = item.find('title')
            description_elem = item.find('description')
            link_elem = item.find('link')
            pub_date_elem = item.find('pubDate')
            source_elem = item.find('source')
            
            if title_elem is not None and description_elem is not None:
                title = title_elem.text
                description = description_elem.text
                link = link_elem.text if link_elem is not None else ""
                pub_date = pub_date_elem.text if pub_date_elem is not None else ""
                source_name = source_elem.text if source_elem is not None else "Google News"
                
                articles.append({
                    'title': title,
                    'description': description,
                    'url': link,
                    'publishedAt': pub_date,
                    'source': {'name': source_name},
                    'content': description,
                    'isReal': True
                })
        
        return articles
    except ET.ParseError as e:
        logger.error(f"RSS parsing failed: {e}")
        return []

async def fetch_real_news_google_rss(keywords):
    """Fetch REAL news from Google News RSS"""
    try:
        search_query = quote(" ".join(keywords[:3]))
        rss_url = f"https://news.google.com/rss/search?q={search_query}&hl=en-US&gl=US&ceid=US:en"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(rss_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        real_articles = parse_google_news_rss(response.content)
        logger.info(f"Google News found {len(real_articles)} articles")
        return real_articles[:10]
        
    except Exception as e:
        logger.error(f"Google News failed: {e}")
        return []

async def fetch_real_news_newsdata(keywords):
    """Fetch REAL news from NewsData.io"""
    try:
        newsdata_url = "https://newsdata.io/api/1/latest"
        api_key = os.environ.get("NEWSDATA_API_KEY")
        
        search_queries = [
            keywords[0] if keywords else "",
            " OR ".join(keywords[:3])
        ]
        
        real_articles = []
        
        for query in search_queries:
            if not query:
                continue
                
            params = {
                'apikey': api_key,
                'language': 'en',
                'size': 10,
                'q': query
            }
            
            response = requests.get(newsdata_url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') == 'success' and data.get('results'):
                for item in data['results']:
                    if item.get('title') and item.get('description'):
                        real_articles.append({
                            'title': item.get('title'),
                            'description': item.get('description'),
                            'url': item.get('link'),
                            'urlToImage': item.get('image_url'),
                            'publishedAt': item.get('pubDate'),
                            'source': {'name': item.get('source_id', 'NewsData')},
                            'content': item.get('content', item.get('description')),
                            'isReal': True,
                            'hasRealImage': bool(item.get('image_url'))
                        })
        
        logger.info(f"NewsData.io found {len(real_articles)} REAL articles")
        return real_articles
    except Exception as e:
        logger.error(f"NewsData.io failed: {e}")
        return []

# --- Step 8: Article Enhancement and Filtering ---
async def enhance_real_article_with_gemini(article, user_context):
    """Use Gemini to enhance REAL articles while keeping them authentic"""
    enhancement_prompt = f"""
    You are a professional news editor. Enhance this REAL news article summary for someone interested in "{user_context}".

    REAL Article:
    Title: {article.get('title')}
    Original Summary: {article.get('description')}
    Source: {article.get('source', {}).get('name')}

    Instructions:
    1. Keep ALL original facts accurate - never add false information
    2. Make the summary more engaging and relevant to "{user_context}"
    3. Highlight aspects most important to the user's interests
    4. Add helpful context and implications
    5. Write in a professional, journalistic style
    6. Aim for 180-220 words

    Return only the enhanced summary text.
    """
    
    try:
        response = model.generate_content(
            enhancement_prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.3,
                max_output_tokens=350
            )
        )
        enhanced_text = response.text.strip()
        
        if len(enhanced_text) > 50 and enhanced_text != article.get('description', ''):
            return enhanced_text
        else:
            return article.get('description', 'Summary not available')
    except Exception as e:
        logger.error(f"Enhancement failed: {e}")
        return article.get('description', 'Summary not available')

async def filter_articles_with_gemini(articles, user_prompt):
    """Use Gemini to identify most relevant REAL articles"""
    if len(articles) <= 8:
        return articles
    
    filtering_prompt = f"""
    Analyze these REAL news articles for relevance to: "{user_prompt}"
    
    Rate each article 1-10:
    - 8-10: Highly relevant and valuable
    - 6-7: Moderately relevant
    - 4-5: Somewhat related
    - 1-3: Not relevant
    
    Return indices of articles scoring 6+ as JSON array.
    """
    
    try:
        relevant_indices = []
        batch_size = 8
        
        for i in range(0, len(articles), batch_size):
            batch = articles[i:i+batch_size]
            batch_text = ""
            
            for idx, article in enumerate(batch):
                title = article.get('title', '')[:100]
                desc = article.get('description', '')[:150]
                batch_text += f"Article {i+idx}: {title} - {desc}\n"
            
            response = model.generate_content(
                f"{filtering_prompt}\n\nArticles:\n{batch_text}\n\nRelevant indices:",
                generation_config=genai.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=100,
                    response_mime_type="application/json"
                )
            )
            
            batch_relevant = json.loads(response.text)
            relevant_indices.extend([i + idx for idx in batch_relevant if isinstance(idx, int)])
        
        filtered = [articles[idx] for idx in relevant_indices if idx < len(articles)]
        return filtered if filtered else articles[:8]
    except Exception as e:
        logger.error(f"Filtering failed: {e}")
        return articles[:8]

def remove_duplicates(articles):
    """Remove duplicate articles"""
    seen_urls = set()
    unique_articles = []
    
    for article in articles:
        url = article.get('url', '')
        if url not in seen_urls and len(article.get('title', '')) > 10:
            seen_urls.add(url)
            unique_articles.append(article)
    
    return unique_articles

# --- Step 9: Main News Fetching Function ---
async def fetch_and_store_category_news(user_id, category_id, keywords, original_prompt=""):
    """
    Fetch REAL news with priority on real images from actual sources
    """
    logger.info(f"🚀 REAL IMAGE PRIORITY FETCHING for: '{original_prompt}'")
    
    try:
        all_articles = []
        
        # Source 1: NewsAPI (provides real images) - highest priority
        newsapi_articles = await fetch_real_news_with_newsapi(keywords)
        all_articles.extend(newsapi_articles)
        
        # Source 2: NewsData.io
        newsdata_articles = await fetch_real_news_newsdata(keywords)
        all_articles.extend(newsdata_articles)
        
        # Source 3: Google News RSS (with aggressive resolution)
        google_articles = await fetch_real_news_google_rss(keywords)
        all_articles.extend(google_articles)
        
        if not all_articles:
            logger.warning("❌ No REAL articles found")
            return 0
        
        # Remove duplicates and filter
        unique_articles = remove_duplicates(all_articles)
        relevant_articles = await filter_articles_with_gemini(unique_articles, original_prompt)
        
        logger.info(f"📰 Processing {len(relevant_articles)} articles with REAL IMAGE PRIORITY")
        
        # Process each article with real image priority
        enhanced_articles = []
        real_image_count = 0
        
        for i, article in enumerate(relevant_articles[:8]):
            try:
                logger.info(f"🔄 Processing article {i+1}/{len(relevant_articles[:8])}")
                
                # Enhance summary
                enhanced_summary = await enhance_real_article_with_gemini(article, original_prompt)
                article['enhancedSummary'] = enhanced_summary
                
                # Real image priority extraction
                image_result = await get_real_image_priority(article)
                
                article['urlToImage'] = image_result['imageUrl']
                article['imageSource'] = image_result['source']
                article['imageRelevance'] = image_result['relevance']
                article['hasRealImage'] = image_result['source'] in ['source-real', 'extracted-real']
                
                if article['hasRealImage']:
                    real_image_count += 1
                
                enhanced_articles.append(article)
                
                logger.info(f"✅ Article {i+1} processed - Image: {image_result['source']} (Real: {article['hasRealImage']})")
                
                # Add delay
                await asyncio.sleep(0.3)
                
            except Exception as e:
                logger.error(f"❌ Article {i+1} processing failed: {e}")
                enhanced_articles.append(article)
        
        # Store articles
        fetched_count = 0
        news_items_ref = db.collection('users').document(user_id).collection('categories').document(category_id).collection('news_items')
        
        for article in enhanced_articles:
            news_item_data = {
                "mainTitle": article.get('title'),
                "mainSource": article.get('source', {}).get('name'),
                "mainUrl": article.get('url'),
                "imageUrl": article.get('urlToImage'),
                "publishedAt": firestore.SERVER_TIMESTAMP,
                "summaries": [{
                    "source": article.get('source', {}).get('name'),
                    "summary": article.get('enhancedSummary', article.get('description')),
                    "url": article.get('url')
                }],
                "keywords": keywords,
                "isRealNews": True,
                "hasRealImage": article.get('hasRealImage', False),
                "imageSource": article.get('imageSource', 'placeholder'),
                "imageRelevance": article.get('imageRelevance', 'low'),
                "enhancedByGemini": True,
                "originalDescription": article.get('description'),
                "articleId": str(uuid.uuid4())
            }
            
            news_items_ref.add(news_item_data)
            fetched_count += 1
        
        logger.info(f"🎉 Successfully stored {fetched_count} articles - {real_image_count} with REAL images")
        return fetched_count
        
    except Exception as e:
        logger.error(f"❌ Real image priority fetching failed: {e}")
        return 0

# --- Step 10: API Endpoints ---
@app.route('/')
def home():
    return "NewsGenius Backend - REAL News with Real Image Priority!"

@app.route('/api/user/<user_id>/categories', methods=['GET'])
def get_user_categories(user_id):
    try:
        categories_ref = db.collection('users').document(user_id).collection('categories')
        categories = []
        for doc in categories_ref.stream():
            category_data = doc.to_dict()
            categories.append({
                "id": doc.id,
                "prompt": category_data.get('prompt'),
                "keywords": category_data.get('keywords'),
                "createdAt": category_data.get('createdAt').isoformat() if category_data.get('createdAt') else None
            })
        return jsonify({"categories": categories})
    except Exception as e:
        logger.error(f"Error fetching categories: {e}")
        return jsonify({"error": "Failed to retrieve categories"}), 500

@app.route('/api/user/<user_id>/categories', methods=['POST'])
async def create_category_and_fetch_news(user_id):
    data = request.get_json()
    user_prompt = data.get('prompt', '')

    if not user_prompt:
        return jsonify({"error": "Prompt is required"}), 400

    try:
        keywords = await get_smart_keywords_with_gemini(user_prompt)
        logger.info(f"Generated keywords for '{user_prompt}': {keywords}")
        
        if not keywords:
            return jsonify({"error": "Could not generate keywords"}), 400

        categories_ref = db.collection('users').document(user_id).collection('categories')
        category_data = {
            "prompt": user_prompt,
            "keywords": keywords,
            "createdAt": firestore.SERVER_TIMESTAMP,
            "newsSource": "real-news-real-image-priority"
        }
        doc_ref = categories_ref.add(category_data)
        category_id = doc_ref[1].id

        fetched_news_count = await fetch_and_store_category_news(user_id, category_id, keywords, user_prompt)

        return jsonify({
            "message": "Category created with REAL news and real image priority",
            "categoryId": category_id,
            "prompt": user_prompt,
            "keywords": keywords,
            "fetchedNewsCount": fetched_news_count,
            "newsSource": "real-news-real-image-priority"
        })

    except Exception as e:
        logger.error(f"Error creating category: {e}")
        return jsonify({"error": f"Failed to create category: {e}"}), 500

@app.route('/api/user/<user_id>/categories/<category_id>/news', methods=['GET'])
def get_category_news(user_id, category_id):
    try:
        news_items_ref = db.collection('users').document(user_id).collection('categories').document(category_id).collection('news_items')
        news_items = []
        for doc in news_items_ref.order_by('publishedAt', direction=firestore.Query.DESCENDING).stream():
            news_data = doc.to_dict()
            news_items.append({
                "id": doc.id,
                "mainTitle": news_data.get('mainTitle'),
                "mainSource": news_data.get('mainSource'),
                "mainUrl": news_data.get('mainUrl'),
                "imageUrl": news_data.get('imageUrl'),
                "publishedAt": news_data.get('publishedAt').isoformat() if news_data.get('publishedAt') else None,
                "summaries": news_data.get('summaries', []),
                "isRealNews": news_data.get('isRealNews', True),
                "hasRealImage": news_data.get('hasRealImage', False),
                "imageSource": news_data.get('imageSource', 'placeholder'),
                "imageRelevance": news_data.get('imageRelevance', 'low'),
                "enhancedByGemini": news_data.get('enhancedByGemini', True)
            })
        return jsonify({"newsItems": news_items})
    except Exception as e:
        logger.error(f"Error fetching news: {e}")
        return jsonify({"error": "Failed to retrieve news"}), 500

@app.route('/api/user/<user_id>/categories/<category_id>/refresh_news', methods=['POST'])
async def refresh_category_news_endpoint(user_id, category_id):
    try:
        category_doc = db.collection('users').document(user_id).collection('categories').document(category_id).get()
        if not category_doc.exists:
            return jsonify({"error": "Category not found"}), 404

        category_data = category_doc.to_dict()
        keywords = category_data.get('keywords')
        original_prompt = category_data.get('prompt', '')
        
        if not keywords:
            return jsonify({"error": "No keywords found"}), 400

        # Clear existing news
        news_items_ref = db.collection('users').document(user_id).collection('categories').document(category_id).collection('news_items')
        docs = news_items_ref.stream()
        for doc in docs:
            doc.reference.delete()

        # Fetch fresh news with real image priority
        fetched_count = await fetch_and_store_category_news(user_id, category_id, keywords, original_prompt)
        return jsonify({"message": "REAL news with real image priority refreshed successfully", "fetchedNewsCount": fetched_count})
        
    except Exception as e:
        logger.error(f"Error refreshing news: {e}")
        return jsonify({"error": "Failed to refresh news"}), 500

# --- DELETE ENDPOINT (FIXED) ---
@app.route('/api/user/<user_id>/categories/<category_id>', methods=['DELETE', 'OPTIONS'])
def delete_category(user_id, category_id):
    # Handle preflight request
    if request.method == 'OPTIONS':
        response = jsonify({'message': 'OK'})
        origin = request.headers.get('Origin', '')
        
        # Allow specific origins
        allowed_origins = ["http://localhost:3000", "http://localhost:3001", 
                          "http://localhost:5173", "http://127.0.0.1:5173", 
                          "https://newgenius-frontend.vercel.app"]
        
        if origin in allowed_origins:
            response.headers.add("Access-Control-Allow-Origin", origin)
        else:
            response.headers.add("Access-Control-Allow-Origin", "https://newgenius-frontend.vercel.app")
            
        response.headers.add('Access-Control-Allow-Headers', "Content-Type,Authorization")
        response.headers.add('Access-Control-Allow-Methods', "DELETE,OPTIONS")
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response, 200
    
    try:
        logger.info(f"🗑️ DELETE request for category {category_id} by user {user_id}")
        
        # Delete the category document
        category_ref = db.collection('users').document(user_id).collection('categories').document(category_id)
        
        # Check if category exists
        category_doc = category_ref.get()
        if not category_doc.exists:
            logger.error(f"Category {category_id} not found")
            return jsonify({"error": "Category not found"}), 404
        
        # Delete all news items in this category first
        news_items_ref = category_ref.collection('news_items')
        docs = news_items_ref.stream()
        deleted_news_count = 0
        for doc in docs:
            doc.reference.delete()
            deleted_news_count += 1
        
        # Delete the category itself
        category_ref.delete()
        
        logger.info(f"✅ Successfully deleted category {category_id} and {deleted_news_count} news items for user {user_id}")
        
        # Update the CORS headers in the response
        response = jsonify({
            "message": "Category deleted successfully",
            "deletedNewsItems": deleted_news_count
        })
        
        # Add CORS headers to response
        origin = request.headers.get('Origin', '')
        allowed_origins = ["http://localhost:3000", "http://localhost:3001", 
                         "http://localhost:5173", "http://127.0.0.1:5173", 
                         "https://newgenius-frontend.vercel.app"]
        
        if origin in allowed_origins:
            response.headers.add("Access-Control-Allow-Origin", origin)
        else:
            response.headers.add("Access-Control-Allow-Origin", "https://newgenius-frontend.vercel.app")
            
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        
        return response, 200
    
    except Exception as e:
        logger.error(f"❌ Error deleting category {category_id}: {e}")
        error_response = jsonify({"error": f"Failed to delete category: {str(e)}"})
        error_response.headers.add("Access-Control-Allow-Origin", request.headers.get('Origin', '*'))
        return error_response, 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    mode = os.environ.get('DEBUG', 'False')
    app.run(host='0.0.0.0', port=port, debug=mode )
