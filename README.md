# Advanced Twitter API Clone

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)](https://flask.palletsprojects.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13+-blue.svg)](https://postgresql.org)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-1.4+-red.svg)](https://sqlalchemy.org)
[![License](https://img.shields.io/badge/License-MIT-orange.svg)](LICENSE)

A comprehensive, production-ready Twitter-like social media API built with Flask, SQLAlchemy, and PostgreSQL. This project demonstrates advanced backend development practices including authentication, real-time features, comprehensive error handling, and enterprise-level architectural patterns.

## 🚀 **Features Overview**

### **Core Functionality**
- ✅ **User Management**: Registration, authentication, profile management
- ✅ **Tweet System**: Create, read, update, delete tweets with media support
- ✅ **Social Features**: Follow/unfollow, likes, retweets, mentions
- ✅ **Real-time Updates**: WebSocket integration for live feeds
- ✅ **Advanced Search**: Full-text search with filters and pagination
- ✅ **Media Handling**: Image and video upload with optimization
- ✅ **Security**: JWT authentication, rate limiting, input validation

### **Enterprise Features**
- 🔒 **Authentication & Authorization**: JWT tokens, role-based access
- 📊 **Analytics**: User engagement metrics, trending topics
- 🔍 **Advanced Search**: Elasticsearch integration for complex queries
- 📈 **Performance**: Database optimization, caching, pagination
- 🛡️ **Security**: Rate limiting, input sanitization, CORS protection
- 📱 **API Documentation**: Comprehensive OpenAPI/Swagger documentation
- 🧪 **Testing**: Unit tests, integration tests, performance tests
- 📋 **Logging**: Structured logging with request tracing

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
- **Authentication**: JWT (JSON Web Tokens) with refresh token support
- **Caching**: Redis for session management and rate limiting
- **Search**: Elasticsearch for advanced search capabilities
- **Message Queue**: Celery with Redis for background tasks
- **File Storage**: Local storage with optional AWS S3 integration
- **API Documentation**: Flask-RESTX for Swagger/OpenAPI

### **Project Structure**
```
TwitterAPI/
├── flask/twitter/
│   ├── src/
│   │   ├── __init__.py              # Application factory
│   │   ├── models.py                # Enhanced database models
│   │   ├── auth/
│   │   │   ├── __init__.py
│   │   │   ├── routes.py            # Authentication endpoints
│   │   │   └── utils.py             # Auth utilities (JWT, validation)
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── users.py             # Enhanced user management
│   │   │   ├── tweets.py            # Enhanced tweet operations
│   │   │   ├── follows.py           # Follow/unfollow functionality
│   │   │   ├── search.py            # Advanced search endpoints
│   │   │   └── media.py             # Media upload/management
│   │   ├── utils/
│   │   │   ├── __init__.py
│   │   │   ├── decorators.py        # Custom decorators (auth, rate limiting)
│   │   │   ├── validators.py        # Input validation utilities
│   │   │   ├── pagination.py        # Pagination helpers
│   │   │   └── exceptions.py        # Custom exception classes
│   │   └── config/
│   │       ├── __init__.py
│   │       ├── development.py       # Development configuration
│   │       ├── production.py        # Production configuration
│   │       └── testing.py           # Testing configuration
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py              # Pytest configuration
│   │   ├── test_auth.py             # Authentication tests
│   │   ├── test_users.py            # User endpoint tests
│   │   ├── test_tweets.py           # Tweet endpoint tests
│   │   └── test_models.py           # Model tests
│   ├── migrations/                  # Database migrations
│   ├── wsgi.py                      # WSGI application entry point
│   └── requirements.txt             # Python dependencies
├── docs/
│   ├── api_documentation.md         # Comprehensive API docs
│   ├── deployment_guide.md          # Deployment instructions
│   └── development_setup.md         # Development environment setup
├── scripts/
│   ├── setup_dev.sh                # Development environment setup
│   ├── run_tests.sh                # Test execution script
│   └── deploy.sh                   # Deployment script
├── docker-compose.yml               # Docker development environment
├── Dockerfile                       # Production Docker image
└── README.md                        # This file
```

## 🛠️ **Installation**

### **Prerequisites**
- Python 3.8 or higher
- PostgreSQL 13 or higher
- Redis (for caching and background tasks)
- Node.js (for frontend development, if applicable)

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
