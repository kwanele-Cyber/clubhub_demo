from app.extensions import db
from datetime import datetime

class Club(db.Model):
    __tablename__ = 'clubs'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    is_active = db.Column(db.Boolean, default=True)
    logo_url = db.Column(db.String(200))
    banner_url = db.Column(db.String(200))
    
    # Relationships
    memberships = db.relationship('Membership', back_populates='club', cascade='all, delete-orphan')
    events = db.relationship('Event', back_populates='club', cascade='all, delete-orphan')
    announcements = db.relationship('Announcement', back_populates='club', cascade='all, delete-orphan')

class Membership(db.Model):
    __tablename__ = 'memberships'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    club_id = db.Column(db.Integer, db.ForeignKey('clubs.id'), nullable=False)
    role = db.Column(db.String(20), default='member')  # 'leader', 'officer', 'member'
    status = db.Column(db.String(20), default='pending')  # 'pending', 'approved', 'rejected'
    joined_at = db.Column(db.DateTime)
    requested_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='memberships')
    club = db.relationship('Club', back_populates='memberships')
    
    __table_args__ = (db.UniqueConstraint('user_id', 'club_id', name='unique_membership'),)