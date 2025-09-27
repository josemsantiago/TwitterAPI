"""
Notification management API endpoints
"""
from flask import Blueprint, jsonify, request
from sqlalchemy import desc
from ..models import Notification, db
from ..auth.utils import token_required, rate_limit, AuthManager
from datetime import datetime, timezone

bp = Blueprint('notifications', __name__, url_prefix='/api/notifications')


@bp.route('', methods=['GET'])
@token_required
@rate_limit(limit=200, window=3600)
def index():
    """Get user's notifications with pagination"""
    try:
        current_user = AuthManager.get_current_user()

        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 50)

        # Filters
        unread_only = request.args.get('unread', type=bool)
        notification_type = request.args.get('type', '').strip()

        # Build query
        query = current_user.notifications

        if unread_only:
            query = query.filter(Notification.is_read == False)

        if notification_type:
            query = query.filter(Notification.notification_type == notification_type)

        # Execute query
        notifications = query.order_by(desc(Notification.created_at)).paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        return jsonify({
            'notifications': [notification.serialize() for notification in notifications.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': notifications.total,
                'pages': notifications.pages,
                'has_next': notifications.has_next,
                'has_prev': notifications.has_prev
            },
            'unread_count': current_user.notifications.filter(Notification.is_read == False).count()
        }), 200

    except Exception as e:
        return jsonify({'error': 'Failed to fetch notifications', 'details': str(e)}), 500


@bp.route('/<int:id>/read', methods=['POST'])
@token_required
@rate_limit(limit=100, window=3600)
def mark_as_read(id: int):
    """Mark a specific notification as read"""
    try:
        current_user = AuthManager.get_current_user()
        notification = Notification.query.filter_by(
            id=id,
            user_id=current_user.id
        ).first()

        if not notification:
            return jsonify({'error': 'Notification not found'}), 404

        if not notification.is_read:
            notification.mark_as_read()
            db.session.commit()

        return jsonify({
            'message': 'Notification marked as read',
            'notification': notification.serialize()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to mark notification as read', 'details': str(e)}), 500


@bp.route('/read-all', methods=['POST'])
@token_required
@rate_limit(limit=20, window=3600)
def mark_all_as_read():
    """Mark all notifications as read for the current user"""
    try:
        current_user = AuthManager.get_current_user()

        # Update all unread notifications
        current_user.notifications.filter(
            Notification.is_read == False
        ).update({
            'is_read': True,
            'read_at': datetime.now(timezone.utc)
        })

        db.session.commit()

        return jsonify({'message': 'All notifications marked as read'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to mark all notifications as read', 'details': str(e)}), 500


@bp.route('/summary', methods=['GET'])
@token_required
@rate_limit(limit=100, window=3600)
def summary():
    """Get notification summary/counts by type"""
    try:
        current_user = AuthManager.get_current_user()

        # Get counts by notification type
        from sqlalchemy import func
        type_counts = db.session.query(
            Notification.notification_type,
            func.count(Notification.id).label('count'),
            func.count(Notification.id).filter(Notification.is_read == False).label('unread_count')
        ).filter(
            Notification.user_id == current_user.id
        ).group_by(
            Notification.notification_type
        ).all()

        total_unread = current_user.notifications.filter(Notification.is_read == False).count()

        summary_data = {
            'total_unread': total_unread,
            'by_type': {
                type_name: {
                    'total': count,
                    'unread': unread_count
                }
                for type_name, count, unread_count in type_counts
            }
        }

        return jsonify({'summary': summary_data}), 200

    except Exception as e:
        return jsonify({'error': 'Failed to get notification summary', 'details': str(e)}), 500