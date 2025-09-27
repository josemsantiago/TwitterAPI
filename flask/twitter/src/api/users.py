"""
Enhanced user management API endpoints with authentication, pagination, and advanced features
"""
from flask import Blueprint, jsonify, abort, request, g
from sqlalchemy import or_, desc, func
from ..models import User, db, Tweet, Notification
from ..auth.utils import token_required, optional_auth, rate_limit, AuthManager
from datetime import datetime, timezone

bp = Blueprint('users', __name__, url_prefix='/api/users')


@bp.route('', methods=['GET'])
@token_required
@rate_limit(limit=100, window=3600)  # 100 requests per hour
def index():
    """Get paginated list of users with search and filtering"""
    try:
        # Pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)  # Max 100 per page

        # Search parameters
        search = request.args.get('search', '').strip()
        verified_only = request.args.get('verified', type=bool)
        sort_by = request.args.get('sort', 'created_at')  # created_at, followers, tweets

        # Build query
        query = User.query.filter(User.is_active == True)

        # Apply search filter
        if search:
            query = query.filter(
                or_(
                    User.username.ilike(f'%{search}%'),
                    User.display_name.ilike(f'%{search}%')
                )
            )

        # Apply verification filter
        if verified_only:
            query = query.filter(User.is_verified == True)

        # Apply sorting
        if sort_by == 'followers':
            query = query.order_by(desc(User.followers_count))
        elif sort_by == 'tweets':
            query = query.order_by(desc(User.tweet_count))
        else:
            query = query.order_by(desc(User.created_at))

        # Execute paginated query
        users = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        return jsonify({
            'users': [user.serialize() for user in users.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': users.total,
                'pages': users.pages,
                'has_next': users.has_next,
                'has_prev': users.has_prev
            }
        }), 200

    except Exception as e:
        return jsonify({'error': 'Failed to fetch users', 'details': str(e)}), 500


@bp.route('/<int:id>', methods=['GET'])
@optional_auth
@rate_limit(limit=200, window=3600)
def show(id: int):
    """Get user by ID with enhanced profile information"""
    try:
        user = User.query.filter_by(id=id, is_active=True).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        current_user = AuthManager.get_current_user()

        # Check if profile is private
        if user.is_private and (not current_user or not current_user.is_following(user)):
            return jsonify({'error': 'This profile is private'}), 403

        # Include relationship info if authenticated
        user_data = user.serialize()
        if current_user:
            user_data['relationship'] = {
                'is_following': current_user.is_following(user),
                'is_followed_by': user.is_following(current_user),
                'is_self': current_user.id == user.id
            }

        return jsonify({'user': user_data}), 200

    except Exception as e:
        return jsonify({'error': 'Failed to fetch user', 'details': str(e)}), 500


@bp.route('/<int:id>/tweets', methods=['GET'])
@optional_auth
@rate_limit(limit=150, window=3600)
def user_tweets(id: int):
    """Get user's tweets with pagination"""
    try:
        user = User.query.filter_by(id=id, is_active=True).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        current_user = AuthManager.get_current_user()

        # Check privacy settings
        if user.is_private and (not current_user or not current_user.is_following(user)):
            return jsonify({'error': 'This profile is private'}), 403

        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 50)

        # Get tweets
        tweets = Tweet.query.filter_by(
            user_id=id,
            is_deleted=False
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
        return jsonify({'error': 'Failed to fetch user tweets', 'details': str(e)}), 500


@bp.route('/<int:id>/followers', methods=['GET'])
@token_required
@rate_limit(limit=100, window=3600)
def followers(id: int):
    """Get user's followers"""
    try:
        user = User.query.filter_by(id=id, is_active=True).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        current_user = AuthManager.get_current_user()

        # Check privacy
        if user.is_private and not current_user.is_following(user) and current_user.id != user.id:
            return jsonify({'error': 'This profile is private'}), 403

        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 50)

        followers = user.followers.filter(User.is_active == True).paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        return jsonify({
            'followers': [follower.serialize() for follower in followers.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': followers.total,
                'pages': followers.pages,
                'has_next': followers.has_next,
                'has_prev': followers.has_prev
            }
        }), 200

    except Exception as e:
        return jsonify({'error': 'Failed to fetch followers', 'details': str(e)}), 500


@bp.route('/<int:id>/following', methods=['GET'])
@token_required
@rate_limit(limit=100, window=3600)
def following(id: int):
    """Get users that this user is following"""
    try:
        user = User.query.filter_by(id=id, is_active=True).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        current_user = AuthManager.get_current_user()

        # Check privacy
        if user.is_private and not current_user.is_following(user) and current_user.id != user.id:
            return jsonify({'error': 'This profile is private'}), 403

        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 50)

        following = user.following.filter(User.is_active == True).paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        return jsonify({
            'following': [followed.serialize() for followed in following.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': following.total,
                'pages': following.pages,
                'has_next': following.has_next,
                'has_prev': following.has_prev
            }
        }), 200

    except Exception as e:
        return jsonify({'error': 'Failed to fetch following', 'details': str(e)}), 500


@bp.route('/<int:id>/follow', methods=['POST'])
@token_required
@rate_limit(limit=50, window=3600)
def follow_user(id: int):
    """Follow or unfollow a user"""
    try:
        current_user = AuthManager.get_current_user()

        if current_user.id == id:
            return jsonify({'error': 'Cannot follow yourself'}), 400

        target_user = User.query.filter_by(id=id, is_active=True).first()
        if not target_user:
            return jsonify({'error': 'User not found'}), 404

        if current_user.is_following(target_user):
            # Unfollow
            success = current_user.unfollow(target_user)
            if success:
                db.session.commit()
                return jsonify({
                    'message': f'Unfollowed @{target_user.username}',
                    'following': False
                }), 200
        else:
            # Follow
            success = current_user.follow(target_user)
            if success:
                # Create notification
                notification = Notification(
                    user_id=target_user.id,
                    notification_type='follow',
                    title='New Follower',
                    message=f'@{current_user.username} started following you',
                    related_user_id=current_user.id
                )
                db.session.add(notification)
                db.session.commit()

                return jsonify({
                    'message': f'Now following @{target_user.username}',
                    'following': True
                }), 200

        return jsonify({'error': 'Follow action failed'}), 400

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Follow action failed', 'details': str(e)}), 500


@bp.route('/<int:id>/liked_tweets', methods=['GET'])
@token_required
@rate_limit(limit=100, window=3600)
def liked_tweets(id: int):
    """Get tweets liked by a user"""
    try:
        user = User.query.filter_by(id=id, is_active=True).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        current_user = AuthManager.get_current_user()

        # Check privacy
        if user.is_private and not current_user.is_following(user) and current_user.id != user.id:
            return jsonify({'error': 'This profile is private'}), 403

        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 50)

        liked_tweets = user.liked_tweets.filter(
            Tweet.is_deleted == False
        ).order_by(desc(Tweet.created_at)).paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        return jsonify({
            'liked_tweets': [tweet.serialize() for tweet in liked_tweets.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': liked_tweets.total,
                'pages': liked_tweets.pages,
                'has_next': liked_tweets.has_next,
                'has_prev': liked_tweets.has_prev
            }
        }), 200

    except Exception as e:
        return jsonify({'error': 'Failed to fetch liked tweets', 'details': str(e)}), 500


@bp.route('/suggestions', methods=['GET'])
@token_required
@rate_limit(limit=50, window=3600)
def follow_suggestions():
    """Get user follow suggestions based on mutual follows"""
    try:
        current_user = AuthManager.get_current_user()
        limit = min(request.args.get('limit', 10, type=int), 20)

        # Get users with most mutual followers
        suggestions = db.session.query(User).join(
            User.followers
        ).filter(
            User.id != current_user.id,
            User.is_active == True,
            ~User.followers.any(id=current_user.id)  # Not already following
        ).group_by(User.id).order_by(
            desc(func.count())  # Order by follower count
        ).limit(limit).all()

        return jsonify({
            'suggestions': [user.serialize() for user in suggestions]
        }), 200

    except Exception as e:
        return jsonify({'error': 'Failed to get suggestions', 'details': str(e)}), 500


@bp.route('/search', methods=['GET'])
@token_required
@rate_limit(limit=100, window=3600)
def search_users():
    """Advanced user search with filters"""
    try:
        query_text = request.args.get('q', '').strip()
        if not query_text:
            return jsonify({'error': 'Search query is required'}), 400

        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 50)

        # Filters
        verified_only = request.args.get('verified', type=bool)
        min_followers = request.args.get('min_followers', 0, type=int)

        # Build search query
        search_query = User.query.filter(
            User.is_active == True,
            or_(
                User.username.ilike(f'%{query_text}%'),
                User.display_name.ilike(f'%{query_text}%'),
                User.bio.ilike(f'%{query_text}%')
            )
        )

        # Apply filters
        if verified_only:
            search_query = search_query.filter(User.is_verified == True)

        if min_followers > 0:
            search_query = search_query.filter(User.followers_count >= min_followers)

        # Execute search
        results = search_query.order_by(
            desc(User.followers_count)
        ).paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        return jsonify({
            'users': [user.serialize() for user in results.items],
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


@bp.route('/<int:id>/analytics', methods=['GET'])
@token_required
def user_analytics(id: int):
    """Get user analytics (only for the user themselves)"""
    try:
        current_user = AuthManager.get_current_user()

        if current_user.id != id:
            return jsonify({'error': 'Access denied'}), 403

        # Calculate analytics
        total_tweets = current_user.tweets.filter_by(is_deleted=False).count()
        total_likes_received = db.session.query(func.sum(Tweet.like_count)).filter(
            Tweet.user_id == current_user.id,
            Tweet.is_deleted == False
        ).scalar() or 0

        total_retweets_received = db.session.query(func.sum(Tweet.retweet_count)).filter(
            Tweet.user_id == current_user.id,
            Tweet.is_deleted == False
        ).scalar() or 0

        # Recent activity (last 30 days)
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        recent_tweets = current_user.tweets.filter(
            Tweet.created_at >= thirty_days_ago,
            Tweet.is_deleted == False
        ).count()

        return jsonify({
            'analytics': {
                'total_tweets': total_tweets,
                'total_likes_received': total_likes_received,
                'total_retweets_received': total_retweets_received,
                'followers_count': current_user.followers_count,
                'following_count': current_user.following_count,
                'recent_tweets_30d': recent_tweets,
                'account_age_days': (datetime.now(timezone.utc) - current_user.created_at).days
            }
        }), 200

    except Exception as e:
        return jsonify({'error': 'Failed to get analytics', 'details': str(e)}), 500