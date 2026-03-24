from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.user import User
from app.models.club import Club, Membership
from app.models.event import Event, EventAttendance
from app.models.announcement import Announcement
from datetime import datetime, timedelta
from sqlalchemy import func

bp = Blueprint('admin', __name__, url_prefix='/admin')

@bp.before_request
@login_required
def check_admin():
    if not current_user.is_admin:
        return render_template('errors/403.html'), 403

@bp.route('/')
def dashboard():
    return render_template('admin/dashboard.html')

@bp.route('/api/stats')
def api_stats():
    # Total counts
    total_users = User.query.count()
    total_clubs = Club.query.count()
    total_events = Event.query.count()
    total_announcements = Announcement.query.count()
    
    # Active users (last 30 days)
    month_ago = datetime.utcnow() - timedelta(days=30)
    active_users = User.query.filter(User.last_login >= month_ago).count()
    
    # New users (last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)
    new_users = User.query.filter(User.created_at >= week_ago).count()
    
    # Events this month
    events_this_month = Event.query.filter(
        Event.start_time >= month_ago
    ).count()
    
    # Membership stats
    total_memberships = Membership.query.filter_by(status='approved').count()
    pending_requests = Membership.query.filter_by(status='pending').count()
    
    # Attendance stats
    total_attendance = EventAttendance.query.filter_by(status='attended').count()
    
    # Clubs by category
    clubs_by_category = db.session.query(
        Club.category, func.count(Club.id)
    ).group_by(Club.category).all()
    
    return jsonify({
        'total_users': total_users,
        'total_clubs': total_clubs,
        'total_events': total_events,
        'total_announcements': total_announcements,
        'active_users': active_users,
        'new_users': new_users,
        'events_this_month': events_this_month,
        'total_memberships': total_memberships,
        'pending_requests': pending_requests,
        'total_attendance': total_attendance,
        'clubs_by_category': dict(clubs_by_category)
    })

@bp.route('/users')
def users_report():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)

@bp.route('/clubs')
def clubs_report():
    clubs = Club.query.all()
    club_stats = []
    
    for club in clubs:
        stats = {
            'club': club,
            'member_count': Membership.query.filter_by(club_id=club.id, status='approved').count(),
            'event_count': Event.query.filter_by(club_id=club.id).count(),
            'announcement_count': Announcement.query.filter_by(club_id=club.id).count()
        }
        club_stats.append(stats)
    
    return render_template('admin/clubs.html', club_stats=club_stats)

@bp.route('/engagement')
def engagement_report():
    # Get top clubs by engagement
    top_clubs = db.session.query(
        Club.id,
        Club.name,
        func.count(EventAttendance.id).label('attendance_count')
    ).join(Event, Club.id == Event.club_id
    ).join(EventAttendance, Event.id == EventAttendance.event_id
    ).filter(EventAttendance.status == 'attended'
    ).group_by(Club.id, Club.name
    ).order_by(func.count(EventAttendance.id).desc()
    ).limit(10).all()
    
    # Get top users by points
    from app.models.gamification import Contribution
    top_users = db.session.query(
        User.id,
        User.first_name,
        User.last_name,
        func.sum(Contribution.points).label('total_points')
    ).join(Contribution, User.id == Contribution.user_id
    ).group_by(User.id, User.first_name, User.last_name
    ).order_by(func.sum(Contribution.points).desc()
    ).limit(10).all()
    
    return render_template('admin/engagement.html',
                         top_clubs=top_clubs,
                         top_users=top_users)