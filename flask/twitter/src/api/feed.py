"""
Advanced feed and timeline API endpoints
"""
from flask import Blueprint, jsonify, request
from sqlalchemy import desc, func, or_
from ..models import Tweet, User, Hashtag, db
from ..auth.utils import token_required, rate_limit, AuthManager
from datetime import datetime, timezone, timedelta

bp = Blueprint('feed', __name__, url_prefix='/api/feed')


@bp.route('/home', methods=['GET'])
@token_required
@rate_limit(limit=200, window=3600)
def home_timeline():
    """Get personalized home timeline with algorithm"""
    try:
        current_user = AuthManager.get_current_user()

        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 50)

        # Get tweets from followed users + own tweets
        followed_user_ids = [user.id for user in current_user.following]
        followed_user_ids.append(current_user.id)

        # Algorithm: boost recent tweets and highly engaged tweets
        two_days_ago = datetime.now(timezone.utc) - timedelta(days=2)

        tweets = Tweet.query.filter(
            Tweet.user_id.in_(followed_user_ids),
            Tweet.is_deleted == False
        ).order_by(
            # Boost recent tweets
            desc(Tweet.created_at > two_days_ago),
            # Then by engagement (likes + retweets + replies)
            desc(Tweet.like_count + Tweet.retweet_count + Tweet.reply_count),
            # Finally by creation time
            desc(Tweet.created_at)
        ).paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        return jsonify({
            'tweets': [tweet.serialize() for tweet in tweets.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': tweets.total,
                'pages': tweets.pages,
                'has_next': tweets.has_next,
                'has_prev': tweets.has_prev
            }
        }), 200

    except Exception as e:
        return jsonify({'error': 'Failed to fetch home timeline', 'details': str(e)}), 500


@bp.route('/discover', methods=['GET'])
@token_required
@rate_limit(limit=100, window=3600)
def discover():
    """Get discover feed with trending and recommended content"""
    try:
        current_user = AuthManager.get_current_user()

        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 50)

        # Get trending tweets from last 24 hours from non-followed users
        twenty_four_hours_ago = datetime.now(timezone.utc) - timedelta(hours=24)
        followed_user_ids = [user.id for user in current_user.following]
        followed_user_ids.append(current_user.id)

        trending_tweets = Tweet.query.join(User).filter(
            Tweet.created_at >= twenty_four_hours_ago,
            Tweet.is_deleted == False,
            User.is_active == True,
            User.is_private == False,
            ~Tweet.user_id.in_(followed_user_ids)  # Not from followed users
        ).order_by(
            desc(Tweet.like_count + Tweet.retweet_count * 2 + Tweet.reply_count)  # Weight retweets more
        ).paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        return jsonify({
            'tweets': [tweet.serialize() for tweet in trending_tweets.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': trending_tweets.total,
                'pages': trending_tweets.pages,
                'has_next': trending_tweets.has_next,
                'has_prev': trending_tweets.has_prev
            }
        }), 200

    except Exception as e:
        return jsonify({'error': 'Failed to fetch discover feed', 'details': str(e)}), 500


@bp.route('/hashtag/<hashtag_name>', methods=['GET'])
@token_required
@rate_limit(limit=150, window=3600)
def hashtag_feed(hashtag_name: str):
    """Get tweets for a specific hashtag"""
    try:
        # Clean hashtag name
        hashtag_name = hashtag_name.lower().replace('#', '')

        # Find hashtag
        hashtag = Hashtag.query.filter_by(name=hashtag_name).first()
        if not hashtag:
            return jsonify({'error': 'Hashtag not found'}), 404

        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 50)

        # Get tweets with this hashtag
        tweets = Tweet.query.join(User).filter(
            Tweet.hashtags.any(Hashtag.name == hashtag_name),
            Tweet.is_deleted == False,
            User.is_active == True,
            User.is_private == False  # Only public tweets for hashtag feeds
        ).order_by(
            desc(Tweet.created_at)
        ).paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        return jsonify({
            'hashtag': hashtag.serialize(),
            'tweets': [tweet.serialize() for tweet in tweets.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': tweets.total,
                'pages': tweets.pages,
                'has_next': tweets.has_next,
                'has_prev': tweets.has_prev
            }
        }), 200

    except Exception as e:
        return jsonify({'error': 'Failed to fetch hashtag feed', 'details': str(e)}), 500


@bp.route('/trending-hashtags', methods=['GET'])
@token_required
@rate_limit(limit=50, window=3600)
def trending_hashtags():
    """Get trending hashtags with different time periods"""
    try:
        # Time period options
        period = request.args.get('period', '24h')  # 24h, 7d, 30d
        limit = min(request.args.get('limit', 20, type=int), 50)

        # Calculate time threshold
        if period == '7d':
            time_threshold = datetime.now(timezone.utc) - timedelta(days=7)
        elif period == '30d':
            time_threshold = datetime.now(timezone.utc) - timedelta(days=30)
        else:  # default to 24h
            time_threshold = datetime.now(timezone.utc) - timedelta(hours=24)

        # Get trending hashtags
        trending = db.session.query(
            Hashtag.name,
            func.count(Tweet.id).label('tweet_count')
        ).join(
            Tweet.hashtags
        ).join(
            User, Tweet.user_id == User.id
        ).filter(
            Tweet.created_at >= time_threshold,
            Tweet.is_deleted == False,
            User.is_active == True,
            User.is_private == False
        ).group_by(
            Hashtag.id, Hashtag.name
        ).order_by(
            desc('tweet_count')
        ).limit(limit).all()

        return jsonify({
            'period': period,
            'trending_hashtags': [
                {
                    'hashtag': f'#{name}',
                    'tweet_count': count
                }
                for name, count in trending
            ]
        }), 200

    except Exception as e:
        return jsonify({'error': 'Failed to get trending hashtags', 'details': str(e)}), 500


@bp.route('/mentions', methods=['GET'])
@token_required
@rate_limit(limit=100, window=3600)
def mentions():
    """Get tweets where the current user is mentioned"""
    try:
        current_user = AuthManager.get_current_user()

        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 50)

        # Get tweets mentioning the current user
        mentioned_tweets = Tweet.query.join(User).filter(
            Tweet.mentions.any(mentioned_user_id=current_user.id),
            Tweet.is_deleted == False,
            User.is_active == True
        ).order_by(
            desc(Tweet.created_at)
        ).paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        return jsonify({
            'tweets': [tweet.serialize() for tweet in mentioned_tweets.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': mentioned_tweets.total,
                'pages': mentioned_tweets.pages,
                'has_next': mentioned_tweets.has_next,
                'has_prev': mentioned_tweets.has_prev
            }
        }), 200

    except Exception as e:
        return jsonify({'error': 'Failed to fetch mentions', 'details': str(e)}), 500