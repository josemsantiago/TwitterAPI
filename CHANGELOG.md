# Changelog

All notable changes to the Twitter API Clone project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Add real-time notifications with WebSockets
- Implement direct messaging
- Add media upload for tweets
- Include trending topics
- Add user verification system

## [1.0.0] - Initial Release

### Added
- User authentication with JWT tokens
- User registration and login
- Tweet creation, reading, updating, deletion (CRUD)
- Like/unlike functionality
- Follow/unfollow users
- User feed generation
- Notification system
- Role-based access control
- Rate limiting
- PostgreSQL database integration
- RESTful API endpoints
- Docker containerization
- Database migrations with Alembic
- Comprehensive API documentation

### Security
- JWT authentication
- Password hashing with bcrypt
- Secure token management
- Environment variable configuration
- CORS support
- Input validation

### Infrastructure
- Flask web framework
- SQLAlchemy ORM
- PostgreSQL database
- Docker and Docker Compose
- Alembic migrations
- Redis integration (planned)

### API Endpoints
- Authentication (register, login, refresh)
- Users (CRUD, follow, followers, following)
- Tweets (CRUD, like, timeline)
- Feed (personalized, discover, trending)
- Notifications (list, mark as read)
