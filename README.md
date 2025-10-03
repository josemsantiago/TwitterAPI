# Twitter API Clone - Partial Implementation

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)](https://flask.palletsprojects.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13+-blue.svg)](https://postgresql.org)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-1.4+-red.svg)](https://sqlalchemy.org)
[![Status](https://img.shields.io/badge/Status-Partial_Implementation-orange.svg)](#implementation-status)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A Twitter-like social media API built with Flask, SQLAlchemy, and PostgreSQL. This is a learning project demonstrating backend development concepts including authentication, RESTful API design, and database relationships. **Note:** This is a partial implementation with basic functionality - many advanced features are planned but not yet implemented.

## 📸 Screenshots

> **Note:** API endpoint screenshots and Postman collection examples will be added soon. Run the Flask server and test endpoints using the API documentation below.

## 📊 **Implementation Status**

### **✅ Implemented Features** (~40% complete)
- **User Management**: Basic registration, authentication (JWT), profile viewing
- **Tweet System**: Create tweets, view tweets, delete tweets
- **Social Features**: Follow/unfollow users, view followers/following
- **Feed**: Basic timeline feed showing tweets from followed users
- **Notifications**: Simple notification system for interactions
- **Authentication**: JWT-based authentication with login/register endpoints
- **Database**: PostgreSQL with SQLAlchemy ORM, basic relationship models

**API Endpoints Implemented:** ~40 endpoints across 6 route files

### **🚧 Planned but Not Implemented**
- ❌ Real-time updates (WebSocket/SSE)
- ❌ Advanced search (Elasticsearch)
- ❌ Media handling (image/video uploads)
- ❌ Retweets and quote tweets
- ❌ Mentions and hashtags
- ❌ Direct messaging
- ❌ User blocking/muting
- ❌ Tweet threads
- ❌ Advanced analytics
- ❌ Rate limiting
- ❌ Caching layer (Redis)
- ❌ Background task processing (Celery)
- ❌ Comprehensive test suite
- ❌ API documentation (Swagger/OpenAPI)
- ❌ Production deployment configuration

## 📋 **Table of Contents**

- [Architecture](#architecture)
- [Installation](#installation)
- [API Endpoints](#api-endpoints)
- [Database Schema](#database-schema)
- [Authentication](#authentication)
- [Features](#features)
- [Testing](#testing)
- [Deployment](#deployment)
- [Contributing](#contributing)

## 🏗️ **Architecture**

### **Technology Stack**
- **Backend Framework**: Flask 2.0+ with Blueprint architecture
- **Database**: PostgreSQL 13+ with SQLAlchemy ORM
- **Authentication**: JWT (JSON Web Tokens) - basic implementation
- **Caching**: ❌ Not implemented (Redis planned)
- **Search**: ❌ Not implemented (Elasticsearch planned)
- **Message Queue**: ❌ Not implemented (Celery planned)
- **File Storage**: ❌ Not implemented
- **API Documentation**: ❌ Not implemented (Swagger/OpenAPI planned)

### **Actual Project Structure**
```
TwitterAPI/
├── flask/twitter/
│   ├── src/
│   │   ├── __init__.py              # Application factory
│   │   ├── models.py                # Database models (User, Tweet, Follow, etc.)
│   │   ├── auth/
│   │   │   ├── __init__.py
│   │   │   ├── routes.py            # Login/register endpoints (8 routes)
│   │   │   └── utils.py             # JWT utilities
│   │   └── api/
│   │       ├── __init__.py
│   │       ├── users.py             # User endpoints (10 routes)
│   │       ├── tweets.py            # Tweet endpoints (11 routes)
│   │       ├── feed.py              # Timeline feed (5 routes)
│   │       └── notifications.py     # Notifications (4 routes)
│   ├── migrations/                  # ❌ Not set up
│   ├── wsgi.py                      # Basic Flask runner
│   └── requirements.txt             # Python dependencies
├── psycopg2/                        # Practice files (removed)
├── sqlalchemy/                      # Practice files (removed)
└── README.md                        # This file
```

**Note:** Many directories/files mentioned in the original README don't exist - this structure reflects what's actually implemented.

## 🛠️ **Installation**

### **Prerequisites**
- Python 3.8 or higher
- PostgreSQL 13 or higher (for full functionality)
- ~~Redis~~ (not yet implemented)
- ~~Node.js~~ (no frontend included)

### **Quick Start**

1. **Clone the repository**
```bash
git clone https://github.com/josemsantiago/TwitterAPI.git
cd TwitterAPI
```

2. **Set up virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up PostgreSQL database**
```bash
psql -U postgres
CREATE DATABASE twitter;
\q
```

5. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

6. **Run database migrations**
```bash
cd flask/twitter
flask db upgrade
```

7. **Start the development server**
```bash
python wsgi.py
```

The API will be available at `http://localhost:5000`

### **Docker Setup (Recommended)**

```bash
docker-compose up -d
```

This will start all required services (PostgreSQL, Redis, Flask app) in containers.

## 🔐 **Authentication**

The API uses JWT (JSON Web Tokens) for authentication:

1. **Register**: `POST /auth/register`
2. **Login**: `POST /auth/login` (returns access and refresh tokens)
3. **Refresh**: `POST /auth/refresh` (get new access token)
4. **Logout**: `POST /auth/logout`

**Token Usage**:
```bash
curl -H "Authorization: Bearer <access_token>" http://localhost:5000/api/tweets
```

## 📚 **API Endpoints**

### **Authentication**
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/auth/register` | User registration | No |
| POST | `/auth/login` | User login | No |
| POST | `/auth/refresh` | Refresh access token | Yes |
| POST | `/auth/logout` | User logout | Yes |
| GET | `/auth/me` | Get current user | Yes |

### **Users**
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/users` | List users (paginated) | Yes |
| GET | `/api/users/{id}` | Get user by ID | Yes |
| PUT | `/api/users/{id}` | Update user profile | Yes (own profile) |
| DELETE | `/api/users/{id}` | Delete user account | Yes (own profile) |
| GET | `/api/users/{id}/tweets` | Get user's tweets | Yes |
| GET | `/api/users/{id}/followers` | Get user's followers | Yes |
| GET | `/api/users/{id}/following` | Get users being followed | Yes |

### **Tweets**
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/tweets` | Get timeline (paginated) | Yes |
| POST | `/api/tweets` | Create new tweet | Yes |
| GET | `/api/tweets/{id}` | Get specific tweet | Yes |
| PUT | `/api/tweets/{id}` | Update tweet | Yes (owner only) |
| DELETE | `/api/tweets/{id}` | Delete tweet | Yes (owner only) |
| POST | `/api/tweets/{id}/like` | Like/unlike tweet | Yes |
| POST | `/api/tweets/{id}/retweet` | Retweet | Yes |
| GET | `/api/tweets/{id}/replies` | Get tweet replies | Yes |

### **Social Features**
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/users/{id}/follow` | Follow/unfollow user | Yes |
| GET | `/api/feed` | Get personalized feed | Yes |
| GET | `/api/trending` | Get trending topics | Yes |
| GET | `/api/notifications` | Get user notifications | Yes |

### **Search**
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/search/tweets` | Search tweets | Yes |
| GET | `/api/search/users` | Search users | Yes |
| GET | `/api/search/hashtags` | Search hashtags | Yes |

### **Media**
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/media/upload` | Upload media file | Yes |
| GET | `/api/media/{id}` | Get media file | Yes |
| DELETE | `/api/media/{id}` | Delete media file | Yes (owner only) |

## 💾 **Database Schema**

### **Enhanced Models**
- **User**: Extended with profile information, verification status
- **Tweet**: Enhanced with media support, retweet functionality
- **Follow**: User relationships (followers/following)
- **Like**: Tweet likes with timestamps
- **Retweet**: Retweet functionality
- **Hashtag**: Hashtag tracking and trending
- **Mention**: User mentions in tweets
- **Media**: File attachments (images, videos)
- **Notification**: User notifications system

## 🧪 **Testing**

Run the comprehensive test suite:

```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=src

# Run specific test file
python -m pytest tests/test_tweets.py

# Run with verbose output
python -m pytest -v
```

## 🚀 **Performance Features**

- **Database Optimization**: Proper indexing, query optimization
- **Caching**: Redis integration for frequent queries
- **Pagination**: Efficient pagination for large datasets
- **Rate Limiting**: API rate limiting to prevent abuse
- **Background Tasks**: Celery for heavy operations
- **Connection Pooling**: Optimized database connections

## 🔒 **Security Features**

- **Input Validation**: Comprehensive input sanitization
- **SQL Injection Protection**: Parameterized queries via SQLAlchemy
- **XSS Protection**: Output escaping and Content Security Policy
- **CORS Configuration**: Proper cross-origin request handling
- **Rate Limiting**: Request rate limiting per user/IP
- **Password Security**: Bcrypt hashing with salt
- **JWT Security**: Secure token generation and validation

## 📊 **Monitoring & Analytics**

- **Structured Logging**: JSON-formatted logs with request tracing
- **Performance Metrics**: Response time and throughput monitoring
- **Error Tracking**: Comprehensive error logging and notifications
- **User Analytics**: Engagement metrics and usage statistics

## 🐳 **Deployment**

### **Production Deployment**

1. **Using Docker**:
```bash
docker build -t twitter-api .
docker run -p 5000:5000 twitter-api
```

2. **Manual Deployment**:
```bash
gunicorn --bind 0.0.0.0:5000 wsgi:app
```

3. **Environment Variables**:
```bash
export FLASK_ENV=production
export SECRET_KEY=your-secret-key
export DATABASE_URL=postgresql://user:pass@localhost/twitter
export REDIS_URL=redis://localhost:6379/0
```

## 📸 Screenshots

> **Note:** Screenshots will be added soon. To test the API endpoints, use tools like Postman or curl after starting the development server at http://localhost:5000.

## 🤝 **Contributing**

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### **Development Guidelines**

- Follow PEP 8 style guidelines
- Write comprehensive tests for new features
- Update documentation for API changes
- Use type hints where applicable
- Follow conventional commit messages

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 **Acknowledgments**

- Flask and SQLAlchemy communities
- PostgreSQL development team
- Contributors and testers

---

*A comprehensive, production-ready social media API showcasing modern Python web development practices.*
