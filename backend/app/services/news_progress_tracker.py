"""
Progress tracking service for news fetching operations
"""
import uuid
from datetime import datetime
from typing import Dict, Optional
from app.schemas.news_progress import NewsProgress, AssetProgress


class NewsProgressTracker:
    """In-memory progress tracker for news fetching sessions"""
    
    def __init__(self):
        self.sessions: Dict[str, NewsProgress] = {}
    
    def create_session(self, user_id: int, assets: list) -> str:
        """Create a new progress tracking session"""
        session_id = str(uuid.uuid4())
        
        asset_progress = [
            AssetProgress(
                asset_id=asset.id,
                asset_name=asset.name,
                asset_symbol=asset.symbol,
                status="pending"
            )
            for asset in assets
        ]
        
        progress = NewsProgress(
            session_id=session_id,
            user_id=user_id,
            total_assets=len(assets),
            processed_assets=0,
            alerts_created=0,
            status="running",
            assets=asset_progress,
            started_at=datetime.utcnow()
        )
        
        self.sessions[session_id] = progress
        return session_id
    
    def update_asset_status(
        self,
        session_id: str,
        asset_id: int,
        status: str,
        alert_created: bool = False,
        alert_message: Optional[str] = None,
        error_message: Optional[str] = None
    ):
        """Update the status of a specific asset"""
        if session_id not in self.sessions:
            return
        
        progress = self.sessions[session_id]
        
        for asset in progress.assets:
            if asset.asset_id == asset_id:
                asset.status = status
                asset.alert_created = alert_created
                asset.alert_message = alert_message
                asset.error_message = error_message
                asset.processed_at = datetime.utcnow()
                
                if status == "completed":
                    progress.processed_assets += 1
                    if alert_created:
                        progress.alerts_created += 1
                
                break
    
    def complete_session(self, session_id: str):
        """Mark a session as completed"""
        if session_id in self.sessions:
            self.sessions[session_id].status = "completed"
            self.sessions[session_id].completed_at = datetime.utcnow()
    
    def fail_session(self, session_id: str):
        """Mark a session as failed"""
        if session_id in self.sessions:
            self.sessions[session_id].status = "failed"
            self.sessions[session_id].completed_at = datetime.utcnow()
    
    def cancel_session(self, session_id: str):
        """Mark a session as cancelled"""
        if session_id in self.sessions:
            self.sessions[session_id].status = "cancelled"
            self.sessions[session_id].completed_at = datetime.utcnow()
    
    def is_cancelled(self, session_id: str) -> bool:
        """Check if a session has been cancelled"""
        if session_id in self.sessions:
            return self.sessions[session_id].status == "cancelled"
        return False
    
    def get_progress(self, session_id: str) -> Optional[NewsProgress]:
        """Get the current progress of a session"""
        return self.sessions.get(session_id)
    
    def get_user_sessions(self, user_id: int) -> list[NewsProgress]:
        """Get all sessions for a user"""
        return [
            progress for progress in self.sessions.values()
            if progress.user_id == user_id
        ]
    
    def cleanup_old_sessions(self, hours: int = 24):
        """Remove sessions older than specified hours"""
        cutoff = datetime.utcnow().timestamp() - (hours * 3600)
        to_remove = [
            session_id for session_id, progress in self.sessions.items()
            if progress.started_at.timestamp() < cutoff
        ]
        for session_id in to_remove:
            del self.sessions[session_id]


# Singleton instance
progress_tracker = NewsProgressTracker()

# Made with Bob
