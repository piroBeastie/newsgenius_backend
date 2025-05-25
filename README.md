# NewsGenius Backend 🚀

**AI-Powered News Aggregation API**

[![Python](https://img.shields.io/badge/Python-3.9-blue)](https://python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.3-green)](https://flask.palletsprojects.com/)
[![Firebase](https://img.shields.io/badge/Firebase-Admin-orange)](https://firebase.google.com/)
[![Gemini AI](https://img.shields.io/badge/Gemini-AI-purple)](https://ai.google.dev/)

Intelligent backend API for NewsGenius that aggregates news from multiple sources, enhances content with AI, and prioritizes real images from authentic news sources.

## 🌟 Live API

**🔗 Backend URL**: `https://newsgenius-backend.onrender.com/`

## ☀️ FrontEnd Repo

**🔗 [newsgenius_frontend](https://github.com/piroBeastie/newsgenius_frontend)**

## ✨ Core Features

### 🤖 AI-Powered Intelligence
- **Smart Keyword Generation** - Gemini AI expands search terms for comprehensive coverage
- **Content Enhancement** - AI rewrites summaries for better engagement
- **Relevance Filtering** - AI scores and selects most relevant articles
- **Contextual Understanding** - AI analyzes content for better categorization

### 📰 Multi-Source Aggregation
- **NewsAPI Integration** - Professional news sources with authentic images
- **NewsData.io** - Alternative coverage and perspectives
- **Google News RSS** - Comprehensive global news coverage
- **Duplicate Removal** - Advanced URL-based deduplication system

### 🖼️ Real Image Priority System
- **Source Image Priority** - Prioritizes authentic news images
- **Aggressive Extraction** - OpenGraph and Twitter card image extraction
- **URL Decoding** - Advanced Google News URL resolution
- **Contextual Fallbacks** - Smart stock photo selection based on content

## 🏗️ Architecture

backend/
├── app.py # Main Flask application
├── requirements.txt # Python dependencies
├── .env.example # Environment variables template
└── functions/ # Core functionality
├── keyword_generation.py
├── news_fetching.py
├── image_extraction.py
├── ai_enhancement.py
└── data_processing.py


## 🚀 Quick Start

### Prerequisites
- **Python** (v3.9 or higher)
- **Firebase Account** with Firestore enabled
- **Google Cloud Account** (for Gemini AI)
- **News API Keys** (NewsAPI, NewsData.io)

### Installation

Clone the backend repository
git clone https://github.com/yourusername/newsgenius-backend.git
cd newsgenius-backend

Create virtual environment
python -m venv venv
source venv/bin/activate # On Windows: venv\Scripts\activate

Install dependencies
pip install -r requirements.txt

Create environment file
cp .env.example .env


### Environment Variables

AI Configuration
GEMINI_API_KEY=your_gemini_api_key

Database Configuration
FIREBASE_SERVICE_ACCOUNT_PATH={"type":"service_account",...}

News APIs
NEWSAPI_KEY=your_newsapi_key
NEWSDATA_API_KEY=your_newsdata_key
PEXELS_API_KEY=your_pexels_key

Server Configuration
PORT=8080
DEBUG=False


### Development

Start Flask development server
python app.py

Server runs on http://localhost:8080


## 📡 API Endpoints

### Categories Management

GET /api/user/{user_id}/categories
POST /api/user/{user_id}/categories
DELETE /api/user/{user_id}/categories/{category_id}


### News Operations

GET /api/user/{user_id}/categories/{category_id}/news
POST /api/user/{user_id}/categories/{category_id}/refresh_news


### Example Request/Response

Create Category
POST /api/user/123/categories
{
"prompt": "artificial intelligence"
}

Response
{
"message": "Category created with REAL news and real image priority",
"categoryId": "abc123",
"keywords": ["artificial intelligence", "machine learning", "AI technology"],
"fetchedNewsCount": 8
}


## 🛠️ Tech Stack

### Core Framework
- **🐍 Flask** - Lightweight Python web framework
- **⚡ asyncio** - Asynchronous programming for performance
- **🌐 Flask-CORS** - Cross-origin resource sharing

### AI & ML
- **🤖 Google Gemini AI** - Advanced text generation and analysis
- **📊 Content Analysis** - Intelligent keyword generation and filtering

### Data & Storage
- **🔥 Firebase Firestore** - Real-time NoSQL database
- **👤 Firebase Auth** - User authentication system
- **🗂️ Hierarchical Data** - User → Categories → News structure

### External APIs
- **📰 NewsAPI** - Professional news with authentic images
- **📊 NewsData.io** - Alternative news coverage
- **🗞️ Google News RSS** - Comprehensive news feed
- **📸 Pexels API** - High-quality stock photography

## 🎯 Core Functions

### Smart Keyword Generation

async def get_smart_keywords_with_gemini(user_prompt):
"""
AI generates 6-8 related keywords for comprehensive news search
Example: "Tesla" → ["electric vehicles", "Elon Musk", "automotive industry"]
"""


### Real Image Priority

async def get_real_image_priority(article):
"""
1. Use real images from news sources (highest priority)
2. Extract OpenGraph/Twitter images from articles
3. Fallback to contextual stock photos
4. Last resort: themed placeholders
"""


### AI Enhancement

async def enhance_real_article_with_gemini(article, user_context):
"""
AI rewrites summaries for better engagement while preserving facts
Personalizes content based on user interests
"""


## 🔄 Data Flow

graph TD
A[User Search] --> B[AI Keyword Generation]
B --> C[Multi-Source News Fetching]
C --> D[Duplicate Removal]
D --> E[AI Relevance Filtering]
E --> F[Real Image Extraction]
F --> G[AI Summary Enhancement]
G --> H[Firebase Storage]
H --> I[API Response]


## 🚀 Deployment

### Render Deployment

Ensure requirements.txt is current
pip freeze > requirements.txt

Deploy to Render
Build Command: pip install -r requirements.txt
Start Command: python app.py


### Environment Configuration
- Set all environment variables in Render dashboard
- Configure CORS origins for production frontend URL
- Set DEBUG=False for production

## 📊 Performance Metrics

- **⚡ Response Time**: < 30 seconds for news generation
- **🎯 Real Image Success**: 70-80% authentic news images
- **🤖 AI Processing**: 100% of articles enhanced
- **📰 Source Coverage**: 3 major news APIs
- **🔄 Deduplication**: Advanced URL-based system

### Development Guidelines
- Follow PEP 8 Python style guide
- Add comprehensive error handling
- Write meaningful commit messages
- Test all API endpoints thoroughly
- Document new functions with docstrings

**🚀 Backend powering the future of news consumption**

*Built with Flask, Gemini AI, and Firebase*
