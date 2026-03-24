from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.club import Club, Membership
from app.models.user import User
from app.models.announcement import Announcement
from app.models.event import Event
from app.forms.club_forms import ClubCreateForm, MembershipRequestForm
from datetime import datetime
from sqlalchemy import or_

bp = Blueprint('clubs', __name__)

@bp.route('/')
@login_required
def list_clubs():
    # Get all clubs with member counts
    clubs = Club.query.filter_by(is_active=True).all()
    
    # Get user's memberships
    user_memberships = {m.club_id: m for m in Membership.query.filter_by(user_id=current_user.id).all()}
    
    # Get pending requests count for clubs user manages
    managed_clubs = [m.club_id for m in Membership.query.filter_by(
        user_id=current_user.id, role='leader').all()]
    
    pending_requests = {}
    for club_id in managed_clubs:
        pending_requests[club_id] = Membership.query.filter_by(
            club_id=club_id, status='pending').count()
    
    return render_template('club/list.html', 
                         clubs=clubs, 
                         user_memberships=user_memberships,
                         pending_requests=pending_requests)

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_club():
    form = ClubCreateForm()
    
    if form.validate_on_submit():
        club = Club(
            name=form.name.data,
            description=form.description.data,
            category=form.category.data,
            created_by=current_user.id,
            max_members=form.max_members.data
        )
        
        db.session.add(club)
        db.session.flush()  # Get club ID
        
        # Make creator the leader
        membership = Membership(
            user_id=current_user.id,
            club_id=club.id,
            role='leader',
            status='approved',
            joined_at=datetime.utcnow()
        )
        
        db.session.add(membership)
        db.session.commit()
        
        flash(f'Club "{club.name}" created successfully!', 'success')
        return redirect(url_for('clubs.view_club', club_id=club.id))
    
    return render_template('club/create.html', form=form)

@bp.route('/<int:club_id>')
@login_required
def view_club(club_id):
    club = Club.query.get_or_404(club_id)
    
    # Check membership status
    membership = Membership.query.filter_by(
        user_id=current_user.id, 
        club_id=club_id
    ).first()
    
    # Get members with their roles
    members = db.session.query(User, Membership).join(
        Membership, User.id == Membership.user_id
    ).filter(
        Membership.club_id == club_id,
        Membership.status == 'approved'
    ).all()
    
    # Get upcoming events
    events = Event.query.filter(
        Event.club_id == club_id,
        Event.start_time >= datetime.utcnow(),
        Event.is_active == True
    ).order_by(Event.start_time).limit(5).all()
    
    # Get recent announcements
    announcements = Announcement.query.filter_by(
        club_id=club_id, 
        is_active=True
    ).order_by(Announcement.created_at.desc()).limit(5).all()
    
    # Check if current user is leader
    is_leader = membership and membership.role == 'leader' if membership else False
    
    # Get pending requests (for leaders)
    pending_members = []
    if is_leader:
        pending = Membership.query.filter_by(
            club_id=club_id, 
            status='pending'
        ).all()
        pending_members = [(m, User.query.get(m.user_id)) for m in pending]
    
    return render_template('club/view.html',
                         club=club,
                         membership=membership,
                         members=members,
                         events=events,
                         announcements=announcements,
                         is_leader=is_leader,
                         pending_members=pending_members)

@bp.route('/<int:club_id>/join', methods=['POST'])
@login_required
def request_join(club_id):
    club = Club.query.get_or_404(club_id)
    
    # Check if already a member or pending
    existing = Membership.query.filter_by(
        user_id=current_user.id, 
        club_id=club_id
    ).first()
    
    if existing:
        if existing.status == 'pending':
            flash('You already have a pending request for this club.', 'info')
        elif existing.status == 'approved':
            flash('You are already a member of this club.', 'info')
        else:
            flash('Your previous request was rejected. Contact club leader.', 'warning')
        return redirect(url_for('clubs.view_club', club_id=club_id))
    
    # Check member limit
    if club.max_members:
        current_members = Membership.query.filter_by(
            club_id=club_id, 
            status='approved'
        ).count()
        if current_members >= club.max_members:
            flash('This club has reached its maximum member limit.', 'danger')
            return redirect(url_for('clubs.view_club', club_id=club_id))
    
    # Create membership request
    membership = Membership(
        user_id=current_user.id,
        club_id=club_id,
        status='pending'
    )
    
    db.session.add(membership)
    db.session.commit()
    
    # TODO: Send notification to club leaders
    flash('Your membership request has been sent to the club leaders.', 'success')
    return redirect(url_for('clubs.view_club', club_id=club_id))

@bp.route('/<int:club_id>/members/<int:user_id>/approve', methods=['POST'])
@login_required
def approve_member(club_id, user_id):
    # Check if current user is leader
    membership = Membership.query.filter_by(
        user_id=current_user.id,
        club_id=club_id,
        role='leader',
        status='approved'
    ).first()
    
    if not membership:
        flash('You do not have permission to approve members.', 'danger')
        return redirect(url_for('clubs.view_club', club_id=club_id))
    
    # Find the pending membership
    pending = Membership.query.filter_by(
        user_id=user_id,
        club_id=club_id,
        status='pending'
    ).first_or_404()
    
    pending.status = 'approved'
    pending.joined_at = datetime.utcnow()
    
    db.session.commit()
    
    # TODO: Send notification to approved user
    flash('Member approved successfully!', 'success')
    return redirect(url_for('clubs.view_club', club_id=club_id))

@bp.route('/<int:club_id>/members/<int:user_id>/reject', methods=['POST'])
@login_required
def reject_member(club_id, user_id):
    # Check if current user is leader
    membership = Membership.query.filter_by(
        user_id=current_user.id,
        club_id=club_id,
        role='leader',
        status='approved'
    ).first()
    
    if not membership:
        flash('You do not have permission to reject members.', 'danger')
        return redirect(url_for('clubs.view_club', club_id=club_id))
    
    # Find the pending membership
    pending = Membership.query.filter_by(
        user_id=user_id,
        club_id=club_id,
        status='pending'
    ).first_or_404()
    
    db.session.delete(pending)
    db.session.commit()
    
    # TODO: Send notification to rejected user
    flash('Member request rejected.', 'success')
    return redirect(url_for('clubs.view_club', club_id=club_id))

@bp.route('/<int:club_id>/members/<int:user_id>/remove', methods=['POST'])
@login_required
def remove_member(club_id, user_id):
    # Check if current user is leader
    membership = Membership.query.filter_by(
        user_id=current_user.id,
        club_id=club_id,
        role='leader',
        status='approved'
    ).first()
    
    if not membership:
        flash('You do not have permission to remove members.', 'danger')
        return redirect(url_for('clubs.view_club', club_id=club_id))
    
    # Cannot remove self if last leader
    if user_id == current_user.id:
        leader_count = Membership.query.filter_by(
            club_id=club_id,
            role='leader',
            status='approved'
        ).count()
        
        if leader_count <= 1:
            flash('Cannot remove the last leader. Transfer leadership first.', 'danger')
            return redirect(url_for('clubs.view_club', club_id=club_id))
    
    # Find member to remove
    member = Membership.query.filter_by(
        user_id=user_id,
        club_id=club_id,
        status='approved'
    ).first_or_404()
    
    db.session.delete(member)
    db.session.commit()
    
    flash('Member removed from club.', 'success')
    return redirect(url_for('clubs.view_club', club_id=club_id))

@bp.route('/<int:club_id>/announcements/create', methods=['POST'])
@login_required
def create_announcement(club_id):
    # Check if user is leader
    membership = Membership.query.filter_by(
        user_id=current_user.id,
        club_id=club_id,
        role='leader',
        status='approved'
    ).first()
    
    if not membership:
        flash('Only club leaders can create announcements.', 'danger')
        return redirect(url_for('clubs.view_club', club_id=club_id))
    
    title = request.form.get('title')
    content = request.form.get('content')
    priority = request.form.get('priority', 'normal')
    
    if not title or not content:
        flash('Title and content are required.', 'danger')
        return redirect(url_for('clubs.view_club', club_id=club_id))
    
    announcement = Announcement(
        club_id=club_id,
        author_id=current_user.id,
        title=title,
        content=content,
        priority=priority
    )
    
    db.session.add(announcement)
    db.session.commit()
    
    flash('Announcement posted successfully!', 'success')
    return redirect(url_for('clubs.view_club', club_id=club_id))