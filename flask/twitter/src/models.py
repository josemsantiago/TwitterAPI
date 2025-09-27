from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
import secrets
import hashlib
from typing import Optional

db = SQLAlchemy()

# Association table for user follows
follows_table = db.Table(
    'follows',
    db.Column('follower_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('followed_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('created_at', db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
)

# Association table for tweet likes
likes_table = db.Table(
    'likes',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('tweet_id', db.Integer, db.ForeignKey('tweets.id'), primary_key=True),
    db.Column('created_at', db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
)

# Association table for tweet hashtags
tweet_hashtags_table = db.Table(
    'tweet_hashtags',
    db.Column('tweet_id', db.Integer, db.ForeignKey('tweets.id'), primary_key=True),
    db.Column('hashtag_id', db.Integer, db.ForeignKey('hashtags.id'), primary_key=True)
)


class User(db.Model):
    __tablename__ = 'users'

    # Basic Information
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    # Profile Information
    display_name = db.Column(db.String(100), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    location = db.Column(db.String(100), nullable=True)
    website = db.Column(db.String(200), nullable=True)
    profile_image_url = db.Column(db.String(255), nullable=True)
    banner_image_url = db.Column(db.String(255), nullable=True)

    # Account Status
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_private = db.Column(db.Boolean, default=False, nullable=False)

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                          onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)

    # Statistics (denormalized for performance)
    tweet_count = db.Column(db.Integer, default=0, nullable=False)
    followers_count = db.Column(db.Integer, default=0, nullable=False)
    following_count = db.Column(db.Integer, default=0, nullable=False)
    likes_count = db.Column(db.Integer, default=0, nullable=False)

    # Relationships
    tweets = db.relationship('Tweet', backref='user', cascade='all,delete-orphan', lazy='dynamic')

    # Following/Followers relationships
    following = db.relationship(
        'User', secondary=follows_table,
        primaryjoin=id == follows_table.c.follower_id,
        secondaryjoin=id == follows_table.c.followed_id,
        backref='followers', lazy='dynamic'
    )

    # Notifications
    notifications = db.relationship('Notification', backref='user', cascade='all,delete-orphan', lazy='dynamic')

    def __init__(self, username: str, email: str, password: str, display_name: str = None):
        self.username = username
        self.email = email
        self.set_password(password)
        self.display_name = display_name or username

    def set_password(self, password: str) -> None:
        """Set password hash using Werkzeug's secure method"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Check if provided password matches the hash"""
        return check_password_hash(self.password_hash, password)

    def follow(self, user) -> bool:
        """Follow another user"""
        if not self.is_following(user) and user.id != self.id:
            self.following.append(user)
            self.following_count += 1
            user.followers_count += 1
            return True
        return False

    def unfollow(self, user) -> bool:
        """Unfollow a user"""
        if self.is_following(user):
            self.following.remove(user)
            self.following_count -= 1
            user.followers_count -= 1
            return True
        return False

    def is_following(self, user) -> bool:
        """Check if following a user"""
        return self.following.filter(follows_table.c.followed_id == user.id).count() > 0

    def get_followed_tweets(self):
        """Get tweets from followed users"""
        followed_users = self.following.subquery()
        return Tweet.query.join(
            followed_users, Tweet.user_id == followed_users.c.followed_id
        ).order_by(Tweet.created_at.desc())

    def serialize(self, include_private: bool = False):
        """Serialize user data for API responses"""
        data = {
            'id': self.id,
            'username': self.username,
            'display_name': self.display_name,
            'bio': self.bio,
            'location': self.location,
            'website': self.website,
            'profile_image_url': self.profile_image_url,
            'banner_image_url': self.banner_image_url,
            'is_verified': self.is_verified,
            'is_private': self.is_private,
            'created_at': self.created_at.isoformat(),
            'tweet_count': self.tweet_count,
            'followers_count': self.followers_count,
            'following_count': self.following_count,
            'likes_count': self.likes_count
        }

        if include_private:
            data.update({
                'email': self.email,
                'is_active': self.is_active,
                'last_login': self.last_login.isoformat() if self.last_login else None,
                'updated_at': self.updated_at.isoformat()
            })

        return data

    def __repr__(self):
        return f'<User {self.username}>'


class Tweet(db.Model):
    __tablename__ = 'tweets'

    # Basic Information
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    content = db.Column(db.Text, nullable=False)  # Changed to Text for longer content
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                          onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    reply_to_id = db.Column(db.Integer, db.ForeignKey('tweets.id'), nullable=True, index=True)
    retweet_of_id = db.Column(db.Integer, db.ForeignKey('tweets.id'), nullable=True, index=True)

    # Tweet Type and Status
    tweet_type = db.Column(db.String(20), default='tweet', nullable=False)  # tweet, reply, retweet
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)

    # Statistics (denormalized for performance)
    like_count = db.Column(db.Integer, default=0, nullable=False)
    retweet_count = db.Column(db.Integer, default=0, nullable=False)
    reply_count = db.Column(db.Integer, default=0, nullable=False)

    # Geographic Information
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    place_name = db.Column(db.String(100), nullable=True)

    # Relationships
    liking_users = db.relationship(
        'User', secondary=likes_table,
        lazy='dynamic',
        backref=db.backref('liked_tweets', lazy='dynamic')
    )

    # Self-referential relationships for replies and retweets
    replies = db.relationship(
        'Tweet', backref=db.backref('reply_to', remote_side=[id]),
        cascade='all,delete-orphan', lazy='dynamic'
    )

    retweets = db.relationship(
        'Tweet', backref=db.backref('original_tweet', remote_side=[id]),
        cascade='all,delete-orphan', lazy='dynamic',
        foreign_keys=[retweet_of_id]
    )

    # Media attachments
    media_attachments = db.relationship('Media', backref='tweet', cascade='all,delete-orphan', lazy='dynamic')

    # Hashtags
    hashtags = db.relationship(
        'Hashtag', secondary=tweet_hashtags_table,
        lazy='dynamic', backref=db.backref('tweets', lazy='dynamic')
    )

    # Mentions
    mentions = db.relationship('Mention', backref='tweet', cascade='all,delete-orphan', lazy='dynamic')

    def __init__(self, content: str, user_id: int, reply_to_id: int = None, retweet_of_id: int = None):
        self.content = content
        self.user_id = user_id
        self.reply_to_id = reply_to_id
        self.retweet_of_id = retweet_of_id

        # Set tweet type based on parameters
        if reply_to_id:
            self.tweet_type = 'reply'
        elif retweet_of_id:
            self.tweet_type = 'retweet'
        else:
            self.tweet_type = 'tweet'

    def like(self, user) -> bool:
        """Like this tweet"""
        if not self.is_liked_by(user):
            self.liking_users.append(user)
            self.like_count += 1
            user.likes_count += 1
            return True
        return False

    def unlike(self, user) -> bool:
        """Unlike this tweet"""
        if self.is_liked_by(user):
            self.liking_users.remove(user)
            self.like_count -= 1
            user.likes_count -= 1
            return True
        return False

    def is_liked_by(self, user) -> bool:
        """Check if tweet is liked by user"""
        return self.liking_users.filter(likes_table.c.user_id == user.id).count() > 0

    def get_hashtags_from_content(self) -> list:
        """Extract hashtags from tweet content"""
        import re
        return re.findall(r'#(\w+)', self.content)

    def get_mentions_from_content(self) -> list:
        """Extract mentions from tweet content"""
        import re
        return re.findall(r'@(\w+)', self.content)

    def serialize(self, include_user: bool = True, include_stats: bool = True):
        """Serialize tweet data for API responses"""
        data = {
            'id': self.id,
            'content': self.content,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'tweet_type': self.tweet_type,
            'reply_to_id': self.reply_to_id,
            'retweet_of_id': self.retweet_of_id
        }

        if include_user:
            data['user'] = self.user.serialize()
        else:
            data['user_id'] = self.user_id

        if include_stats:
            data.update({
                'like_count': self.like_count,
                'retweet_count': self.retweet_count,
                'reply_count': self.reply_count
            })

        # Include geographic information if available
        if self.latitude and self.longitude:
            data['location'] = {
                'latitude': self.latitude,
                'longitude': self.longitude,
                'place_name': self.place_name
            }

        # Include media attachments
        if self.media_attachments.count() > 0:
            data['media'] = [media.serialize() for media in self.media_attachments]

        # Include hashtags
        if self.hashtags.count() > 0:
            data['hashtags'] = [hashtag.serialize() for hashtag in self.hashtags]

        return data

    def __repr__(self):
        return f'<Tweet {self.id}: {self.content[:50]}...>'


class Hashtag(db.Model):
    __tablename__ = 'hashtags'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Statistics
    tweet_count = db.Column(db.Integer, default=0, nullable=False)

    def __init__(self, name: str):
        self.name = name.lower().replace('#', '')  # Store without # and in lowercase

    def serialize(self):
        return {
            'id': self.id,
            'name': f'#{self.name}',
            'tweet_count': self.tweet_count,
            'created_at': self.created_at.isoformat()
        }

    def __repr__(self):
        return f'<Hashtag #{self.name}>'


class Mention(db.Model):
    __tablename__ = 'mentions'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tweet_id = db.Column(db.Integer, db.ForeignKey('tweets.id'), nullable=False)
    mentioned_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    mentioned_user = db.relationship('User', backref='mentions_received')

    def __init__(self, tweet_id: int, mentioned_user_id: int):
        self.tweet_id = tweet_id
        self.mentioned_user_id = mentioned_user_id

    def serialize(self):
        return {
            'id': self.id,
            'tweet_id': self.tweet_id,
            'mentioned_user': self.mentioned_user.serialize(),
            'created_at': self.created_at.isoformat()
        }


class Media(db.Model):
    __tablename__ = 'media'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tweet_id = db.Column(db.Integer, db.ForeignKey('tweets.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # File Information
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    mime_type = db.Column(db.String(100), nullable=False)

    # Media Type
    media_type = db.Column(db.String(20), nullable=False)  # image, video, gif

    # Image/Video Properties
    width = db.Column(db.Integer, nullable=True)
    height = db.Column(db.Integer, nullable=True)
    duration = db.Column(db.Float, nullable=True)  # For videos, in seconds

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    uploader = db.relationship('User', backref='uploaded_media')

    def __init__(self, tweet_id: int, user_id: int, filename: str, original_filename: str,
                 file_path: str, file_size: int, mime_type: str, media_type: str):
        self.tweet_id = tweet_id
        self.user_id = user_id
        self.filename = filename
        self.original_filename = original_filename
        self.file_path = file_path
        self.file_size = file_size
        self.mime_type = mime_type
        self.media_type = media_type

    def serialize(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'file_size': self.file_size,
            'mime_type': self.mime_type,
            'media_type': self.media_type,
            'width': self.width,
            'height': self.height,
            'duration': self.duration,
            'created_at': self.created_at.isoformat(),
            'url': f'/api/media/{self.id}'  # API endpoint for media access
        }


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Notification Content
    notification_type = db.Column(db.String(50), nullable=False)  # like, retweet, follow, mention, reply
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)

    # Related Objects
    related_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    related_tweet_id = db.Column(db.Integer, db.ForeignKey('tweets.id'), nullable=True)

    # Status
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    read_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    related_user = db.relationship('User', foreign_keys=[related_user_id], backref='triggered_notifications')
    related_tweet = db.relationship('Tweet', foreign_keys=[related_tweet_id])

    def __init__(self, user_id: int, notification_type: str, title: str, message: str,
                 related_user_id: int = None, related_tweet_id: int = None):
        self.user_id = user_id
        self.notification_type = notification_type
        self.title = title
        self.message = message
        self.related_user_id = related_user_id
        self.related_tweet_id = related_tweet_id

    def mark_as_read(self):
        """Mark notification as read"""
        self.is_read = True
        self.read_at = datetime.now(timezone.utc)

    def serialize(self):
        data = {
            'id': self.id,
            'notification_type': self.notification_type,
            'title': self.title,
            'message': self.message,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat(),
            'read_at': self.read_at.isoformat() if self.read_at else None
        }

        if self.related_user:
            data['related_user'] = self.related_user.serialize()

        if self.related_tweet:
            data['related_tweet'] = self.related_tweet.serialize(include_user=False, include_stats=False)

        return data