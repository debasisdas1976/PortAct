from pydantic import BaseModel, Field, model_validator
from typing import Optional, List
from datetime import date, datetime
from app.core.enums import SystematicPlanType, SystematicFrequency


class MFPlanCreate(BaseModel):
    plan_type: SystematicPlanType
    asset_id: int
    target_asset_id: Optional[int] = None  # required for STP
    amount: float = Field(..., gt=0)
    frequency: SystematicFrequency
    execution_day: Optional[int] = None
    start_date: date
    end_date: Optional[date] = None
    notes: Optional[str] = Field(None, max_length=500)

    @model_validator(mode="after")
    def validate_plan(self):
        # STP requires target_asset_id
        if self.plan_type == SystematicPlanType.STP and not self.target_asset_id:
            raise ValueError("target_asset_id is required for STP plans")
        if self.plan_type != SystematicPlanType.STP and self.target_asset_id:
            raise ValueError("target_asset_id is only valid for STP plans")
        # end_date must be after start_date
        if self.end_date and self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        # execution_day validation
        if self.frequency == SystematicFrequency.MONTHLY:
            if self.execution_day is None:
                raise ValueError("execution_day (1-28) is required for monthly frequency")
            if not (1 <= self.execution_day <= 28):
                raise ValueError("execution_day must be between 1 and 28 for monthly frequency")
        elif self.frequency == SystematicFrequency.WEEKLY:
            if self.execution_day is None:
                raise ValueError("execution_day (0=Mon..6=Sun) is required for weekly frequency")
            if not (0 <= self.execution_day <= 6):
                raise ValueError("execution_day must be between 0 (Mon) and 6 (Sun) for weekly frequency")
        return self


class MFPlanUpdate(BaseModel):
    amount: Optional[float] = Field(None, gt=0)
    frequency: Optional[SystematicFrequency] = None
    execution_day: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    notes: Optional[str] = Field(None, max_length=500)
    target_asset_id: Optional[int] = None


class MFPlanResponse(BaseModel):
    id: int
    plan_type: str
    asset_id: int
    asset_name: str
    target_asset_id: Optional[int] = None
    target_asset_name: Optional[str] = None
    amount: float
    frequency: str
    execution_day: Optional[int] = None
    start_date: date
    end_date: Optional[date] = None
    is_active: bool
    last_executed_date: Optional[date] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class MFPlanListResponse(BaseModel):
    plans: List[MFPlanResponse]
    total: int
