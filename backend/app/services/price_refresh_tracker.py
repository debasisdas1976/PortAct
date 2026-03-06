"""
Progress tracking service for price refresh operations
"""
import uuid
from datetime import datetime
from typing import Dict, Optional
from app.schemas.price_refresh_progress import PriceRefreshProgress, AssetPriceProgress


class PriceRefreshTracker:
    """In-memory progress tracker for price refresh sessions"""

    def __init__(self):
        self.sessions: Dict[str, PriceRefreshProgress] = {}

    def create_session(self, user_id: int, assets: list) -> str:
        """Create a new progress tracking session"""
        session_id = str(uuid.uuid4())

        asset_progress = [
            AssetPriceProgress(
                asset_id=asset.id,
                asset_name=asset.name,
                asset_symbol=asset.symbol,
                asset_type=asset.asset_type.value if hasattr(asset.asset_type, 'value') else str(asset.asset_type),
                status="pending",
            )
            for asset in assets
        ]

        progress = PriceRefreshProgress(
            session_id=session_id,
            user_id=user_id,
            total_assets=len(assets),
            updated_assets=0,
            failed_assets=0,
            status="running",
            assets=asset_progress,
            started_at=datetime.utcnow(),
        )

        self.sessions[session_id] = progress
        return session_id

    def set_asset_processing(self, session_id: str, asset_id: int):
        """Mark an asset as currently being processed"""
        if session_id not in self.sessions:
            return
        for asset in self.sessions[session_id].assets:
            if asset.asset_id == asset_id:
                asset.status = "processing"
                break

    def update_asset_status(
        self,
        session_id: str,
        asset_id: int,
        status: str,
        error_message: Optional[str] = None,
    ):
        """Update the status of a specific asset"""
        if session_id not in self.sessions:
            return

        progress = self.sessions[session_id]

        for asset in progress.assets:
            if asset.asset_id == asset_id:
                asset.status = status
                asset.error_message = error_message
                asset.processed_at = datetime.utcnow()

                if status == "completed":
                    progress.updated_assets += 1
                elif status == "error":
                    progress.failed_assets += 1
                break

    def complete_session(self, session_id: str):
        """Mark a session as completed"""
        if session_id in self.sessions:
            self.sessions[session_id].status = "completed"
            self.sessions[session_id].completed_at = datetime.utcnow()

    def fail_session(self, session_id: str, error_detail: Optional[str] = None):
        """Mark a session as failed"""
        if session_id in self.sessions:
            self.sessions[session_id].status = "failed"
            self.sessions[session_id].completed_at = datetime.utcnow()
            if error_detail:
                self.sessions[session_id].error_detail = error_detail

    def get_progress(self, session_id: str) -> Optional[PriceRefreshProgress]:
        """Get the current progress of a session"""
        return self.sessions.get(session_id)

    def get_active_session(self, user_id: int) -> Optional[PriceRefreshProgress]:
        """Get the active (running) session for a user, if any"""
        for progress in self.sessions.values():
            if progress.user_id == user_id and progress.status == "running":
                return progress
        return None

    def cleanup_old_sessions(self, hours: int = 24):
        """Remove sessions older than specified hours"""
        cutoff = datetime.utcnow().timestamp() - (hours * 3600)
        to_remove = [
            sid for sid, p in self.sessions.items()
            if p.started_at.timestamp() < cutoff
        ]
        for sid in to_remove:
            del self.sessions[sid]


# Singleton instance
price_refresh_tracker = PriceRefreshTracker()
