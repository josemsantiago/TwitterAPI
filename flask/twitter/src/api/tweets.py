"""
Enhanced tweet management API endpoints with advanced features
"""
from flask import Blueprint, jsonify, abort, request, g
from sqlalchemy import or_, desc, func, text
from ..models import Tweet, User, Hashtag, Mention, Notification, db
from ..auth.utils import token_required, optional_auth, rate_limit, AuthManager
from datetime import datetime, timezone, timedelta
import re

bp = Blueprint('tweets', __name__, url_prefix='/api/tweets')


@bp.route('', methods=['GET'])
@token_required
@rate_limit(limit=200, window=3600)
def index():
    """Get timeline with tweets from followed users"""
    try:
        current_user = AuthManager.get_current_user()

        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 50)

        # Get timeline: tweets from followed users + own tweets
        followed_user_ids = [user.id for user in current_user.following]
        followed_user_ids.append(current_user.id)

        tweets = Tweet.query.filter(
            Tweet.user_id.in_(followed_user_ids),
            Tweet.is_deleted == False
        ).order_by(desc(Tweet.created_at)).paginate(
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
        return jsonify({'error': 'Failed to fetch timeline', 'details': str(e)}), 500


@bp.route('/public', methods=['GET'])
@optional_auth
@rate_limit(limit=100, window=3600)
def public_timeline():
    """Get public timeline of recent tweets"""
    try:
        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 50)

        # Get public tweets from non-private users
        tweets = Tweet.query.join(User).filter(
            Tweet.is_deleted == False,
            User.is_private == False,
            User.is_active == True
        ).order_by(desc(Tweet.created_at)).paginate(
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
        return jsonify({'error': 'Failed to fetch public timeline', 'details': str(e)}), 500


@bp.route('/<int:id>', methods=['GET'])
@optional_auth
@rate_limit(limit=300, window=3600)
def show(id: int):
    """Get specific tweet by ID"""
    try:
        tweet = Tweet.query.filter_by(id=id, is_deleted=False).first()
        if not tweet:
            return jsonify({'error': 'Tweet not found'}), 404

        current_user = AuthManager.get_current_user()

        # Check if user can view this tweet
        if tweet.user.is_private and (not current_user or not current_user.is_following(tweet.user)):
            return jsonify({'error': 'This tweet is from a private account'}), 403

        # Include interaction info if authenticated
        tweet_data = tweet.serialize()
        if current_user:
            tweet_data['interactions'] = {
                'is_liked': tweet.is_liked_by(current_user),
                'can_edit': current_user.id == tweet.user_id,
                'can_delete': current_user.id == tweet.user_id
            }

        return jsonify({'tweet': tweet_data}), 200

    except Exception as e:
        return jsonify({'error': 'Failed to fetch tweet', 'details': str(e)}), 500


@bp.route('', methods=['POST'])
@token_required
@rate_limit(limit=100, window=3600)  # 100 tweets per hour
def create():
    """Create a new tweet"""
    try:
        current_user = AuthManager.get_current_user()
        data = request.get_json()

        if not data or 'content' not in data:
            return jsonify({'error': 'Tweet content is required'}), 400

        content = data['content'].strip()

        if not content:
            return jsonify({'error': 'Tweet content cannot be empty'}), 400

        if len(content) > 2800:  # Increased from Twitter's 280 for multimedia support
            return jsonify({'error': 'Tweet content is too long (max 2800 characters)'}), 400

        # Optional parameters
        reply_to_id = data.get('reply_to_id')
        retweet_of_id = data.get('retweet_of_id')
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        place_name = data.get('place_name')

        # Validate reply_to_id if provided
        if reply_to_id:
            reply_to_tweet = Tweet.query.filter_by(id=reply_to_id, is_deleted=False).first()
            if not reply_to_tweet:
                return jsonify({'error': 'Original tweet not found'}), 404

        # Validate retweet_of_id if provided
        if retweet_of_id:
            original_tweet = Tweet.query.filter_by(id=retweet_of_id, is_deleted=False).first()
            if not original_tweet:
                return jsonify({'error': 'Original tweet not found'}), 404

        # Create tweet
        tweet = Tweet(
            content=content,
            user_id=current_user.id,
            reply_to_id=reply_to_id,
            retweet_of_id=retweet_of_id
        )

        # Add location if provided
        if latitude and longitude:
            tweet.latitude = float(latitude)
            tweet.longitude = float(longitude)
            tweet.place_name = place_name

        db.session.add(tweet)
        db.session.flush()  # Get tweet ID

        # Process hashtags
        hashtags = re.findall(r'#(\w+)', content)
        for hashtag_name in hashtags:
            hashtag = Hashtag.query.filter_by(name=hashtag_name.lower()).first()
            if not hashtag:
                hashtag = Hashtag(name=hashtag_name.lower())
                db.session.add(hashtag)
            hashtag.tweet_count += 1
            tweet.hashtags.append(hashtag)

        # Process mentions
        mentions = re.findall(r'@(\w+)', content)
        for mention_username in mentions:
            mentioned_user = User.query.filter_by(username=mention_username, is_active=True).first()
            if mentioned_user:
                mention = Mention(tweet_id=tweet.id, mentioned_user_id=mentioned_user.id)
                db.session.add(mention)

                # Create notification for mention
                notification = Notification(
                    user_id=mentioned_user.id,
                    notification_type='mention',
                    title='You were mentioned',
                    message=f'@{current_user.username} mentioned you in a tweet',
                    related_user_id=current_user.id,
                    related_tweet_id=tweet.id
                )
                db.session.add(notification)

        # Update user tweet count
        current_user.tweet_count += 1

        # Handle reply notifications
        if reply_to_id and reply_to_tweet.user_id != current_user.id:
            notification = Notification(
                user_id=reply_to_tweet.user_id,
                notification_type='reply',
                title='New Reply',
                message=f'@{current_user.username} replied to your tweet',
                related_user_id=current_user.id,
                related_tweet_id=tweet.id
            )
            db.session.add(notification)
            reply_to_tweet.reply_count += 1

        # Handle retweet notifications and count
        if retweet_of_id and original_tweet.user_id != current_user.id:
            notification = Notification(
                user_id=original_tweet.user_id,
                notification_type='retweet',
                title='Your tweet was retweeted',
                message=f'@{current_user.username} retweeted your tweet',
                related_user_id=current_user.id,
                related_tweet_id=tweet.id
            )
            db.session.add(notification)
            original_tweet.retweet_count += 1

        db.session.commit()

        return jsonify({
            'message': 'Tweet created successfully',
            'tweet': tweet.serialize()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create tweet', 'details': str(e)}), 500


@bp.route('/<int:id>', methods=['PUT'])
@token_required
@rate_limit(limit=50, window=3600)
def update(id: int):
    """Update a tweet (within edit window)"""
    try:
        current_user = AuthManager.get_current_user()
        tweet = Tweet.query.filter_by(id=id, is_deleted=False).first()

        if not tweet:
            return jsonify({'error': 'Tweet not found'}), 404

        if tweet.user_id != current_user.id:
            return jsonify({'error': 'You can only edit your own tweets'}), 403

        # Check if tweet is within edit window (5 minutes)
        edit_window = timedelta(minutes=5)
        if datetime.now(timezone.utc) - tweet.created_at > edit_window:
            return jsonify({'error': 'Tweet edit window has expired'}), 400

        data = request.get_json()
        if not data or 'content' not in data:
            return jsonify({'error': 'Tweet content is required'}), 400

        content = data['content'].strip()
        if not content:
            return jsonify({'error': 'Tweet content cannot be empty'}), 400

        if len(content) > 2800:
            return jsonify({'error': 'Tweet content is too long (max 2800 characters)'}), 400

        # Update content and timestamp
        tweet.content = content
        tweet.updated_at = datetime.now(timezone.utc)

        # Re-process hashtags (remove old, add new)
        tweet.hashtags.clear()
        hashtags = re.findall(r'#(\w+)', content)
        for hashtag_name in hashtags:
            hashtag = Hashtag.query.filter_by(name=hashtag_name.lower()).first()
            if not hashtag:
                hashtag = Hashtag(name=hashtag_name.lower())
                db.session.add(hashtag)
            hashtag.tweet_count += 1
            tweet.hashtags.append(hashtag)

        db.session.commit()

        return jsonify({
            'message': 'Tweet updated successfully',
            'tweet': tweet.serialize()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update tweet', 'details': str(e)}), 500


@bp.route('/<int:id>', methods=['DELETE'])
@token_required
@rate_limit(limit=100, window=3600)
def delete(id: int):
    """Delete a tweet (soft delete)"""
    try:
        current_user = AuthManager.get_current_user()
        tweet = Tweet.query.filter_by(id=id, is_deleted=False).first()

        if not tweet:
            return jsonify({'error': 'Tweet not found'}), 404

        if tweet.user_id != current_user.id:
            return jsonify({'error': 'You can only delete your own tweets'}), 403

        # Soft delete
        tweet.is_deleted = True
        tweet.updated_at = datetime.now(timezone.utc)

        # Update user tweet count
        current_user.tweet_count -= 1

        # Update hashtag counts
        for hashtag in tweet.hashtags:
            hashtag.tweet_count -= 1

        db.session.commit()

        return jsonify({'message': 'Tweet deleted successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete tweet', 'details': str(e)}), 500


@bp.route('/<int:id>/like', methods=['POST'])
@token_required
@rate_limit(limit=200, window=3600)
def toggle_like(id: int):
    """Like or unlike a tweet"""
    try:
        current_user = AuthManager.get_current_user()
        tweet = Tweet.query.filter_by(id=id, is_deleted=False).first()

        if not tweet:
            return jsonify({'error': 'Tweet not found'}), 404

        # Check if user can view this tweet
        if tweet.user.is_private and not current_user.is_following(tweet.user):
            return jsonify({'error': 'Cannot like tweet from private account'}), 403

        if tweet.is_liked_by(current_user):
            # Unlike
            success = tweet.unlike(current_user)
            if success:
                db.session.commit()
                return jsonify({
                    'message': 'Tweet unliked',
                    'liked': False,
                    'like_count': tweet.like_count
                }), 200
        else:
            # Like
            success = tweet.like(current_user)
            if success:
                # Create notification if not own tweet
                if tweet.user_id != current_user.id:
                    notification = Notification(
                        user_id=tweet.user_id,
                        notification_type='like',
                        title='Your tweet was liked',
                        message=f'@{current_user.username} liked your tweet',
                        related_user_id=current_user.id,
                        related_tweet_id=tweet.id
                    )
                    db.session.add(notification)

                db.session.commit()
                return jsonify({
                    'message': 'Tweet liked',
                    'liked': True,
                    'like_count': tweet.like_count
                }), 200

        return jsonify({'error': 'Like action failed'}), 400

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Like action failed', 'details': str(e)}), 500


@bp.route('/<int:id>/liking_users', methods=['GET'])
@token_required
@rate_limit(limit=100, window=3600)
def liking_users(id: int):
    """Get users who liked a tweet"""
    try:
        tweet = Tweet.query.filter_by(id=id, is_deleted=False).first()
        if not tweet:
            return jsonify({'error': 'Tweet not found'}), 404

        current_user = AuthManager.get_current_user()

        # Check privacy
        if tweet.user.is_private and not current_user.is_following(tweet.user):
            return jsonify({'error': 'Cannot view likes for private account tweet'}), 403

        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 50)

        liking_users = tweet.liking_users.filter(User.is_active == True).paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        return jsonify({
            'users': [user.serialize() for user in liking_users.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': liking_users.total,
                'pages': liking_users.pages,
                'has_next': liking_users.has_next,
                'has_prev': liking_users.has_prev
            }
        }), 200

    except Exception as e:
        return jsonify({'error': 'Failed to fetch liking users', 'details': str(e)}), 500


@bp.route('/<int:id>/replies', methods=['GET'])
@optional_auth
@rate_limit(limit=200, window=3600)
def replies(id: int):
    """Get replies to a tweet"""
    try:
        tweet = Tweet.query.filter_by(id=id, is_deleted=False).first()
        if not tweet:
            return jsonify({'error': 'Tweet not found'}), 404

        current_user = AuthManager.get_current_user()

        # Check privacy
        if tweet.user.is_private and (not current_user or not current_user.is_following(tweet.user)):
            return jsonify({'error': 'Cannot view replies for private account tweet'}), 403

        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 50)

        replies = Tweet.query.join(User).filter(
            Tweet.reply_to_id == id,
            Tweet.is_deleted == False,
            User.is_active == True
        ).order_by(desc(Tweet.created_at)).paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        return jsonify({
            'replies': [reply.serialize() for reply in replies.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': replies.total,
                'pages': replies.pages,
                'has_next': replies.has_next,
                'has_prev': replies.has_prev
            }
        }), 200

    except Exception as e:
        return jsonify({'error': 'Failed to fetch replies', 'details': str(e)}), 500


@bp.route('/search', methods=['GET'])
@token_required
@rate_limit(limit=100, window=3600)
def search_tweets():
    """Search tweets with advanced filters"""
    try:
        query_text = request.args.get('q', '').strip()
        if not query_text:
            return jsonify({'error': 'Search query is required'}), 400

        current_user = AuthManager.get_current_user()

        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 50)

        # Filters
        from_user = request.args.get('from_user', '').strip()
        hashtag = request.args.get('hashtag', '').strip()
        since_date = request.args.get('since')
        until_date = request.args.get('until')

        # Build search query
        search_query = Tweet.query.join(User).filter(
            Tweet.is_deleted == False,
            User.is_active == True,
            or_(
                User.is_private == False,
                User.followers.any(id=current_user.id)  # User follows private account
            ),
            Tweet.content.ilike(f'%{query_text}%')
        )

        # Apply filters
        if from_user:
            search_query = search_query.filter(User.username.ilike(f'%{from_user}%'))

        if hashtag:
            search_query = search_query.filter(
                Tweet.hashtags.any(Hashtag.name.ilike(f'%{hashtag.replace("#", "")}%'))
            )

        if since_date:
            try:
                since_dt = datetime.fromisoformat(since_date.replace('Z', '+00:00'))
                search_query = search_query.filter(Tweet.created_at >= since_dt)
            except ValueError:
                return jsonify({'error': 'Invalid since date format'}), 400

        if until_date:
            try:
                until_dt = datetime.fromisoformat(until_date.replace('Z', '+00:00'))
                search_query = search_query.filter(Tweet.created_at <= until_dt)
            except ValueError:
                return jsonify({'error': 'Invalid until date format'}), 400

        # Execute search
        results = search_query.order_by(desc(Tweet.created_at)).paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        return jsonify({
            'tweets': [tweet.serialize() for tweet in results.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': results.total,
                'pages': results.pages,
                'has_next': results.has_next,
                'has_prev': results.has_prev
            },
            'query': query_text
        }), 200

    except Exception as e:
        return jsonify({'error': 'Search failed', 'details': str(e)}), 500


@bp.route('/trending', methods=['GET'])
@token_required
@rate_limit(limit=50, window=3600)
def trending():
    """Get trending hashtags and topics"""
    try:
        # Get trending hashtags from the last 24 hours
        twenty_four_hours_ago = datetime.now(timezone.utc) - timedelta(hours=24)

        trending_hashtags = db.session.query(
            Hashtag.name,
            func.count(Tweet.id).label('tweet_count')
        ).join(
            Tweet.hashtags
        ).filter(
            Tweet.created_at >= twenty_four_hours_ago,
            Tweet.is_deleted == False
        ).group_by(
            Hashtag.id
        ).order_by(
            desc('tweet_count')
        ).limit(20).all()

        return jsonify({
            'trending_hashtags': [
                {
                    'hashtag': f'#{hashtag}',
                    'tweet_count': count
                }
                for hashtag, count in trending_hashtags
            ]
        }), 200

    except Exception as e:
        return jsonify({'error': 'Failed to get trending topics', 'details': str(e)}), 500