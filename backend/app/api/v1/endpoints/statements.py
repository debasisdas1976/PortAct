from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.dependencies import get_current_active_user
from app.models.user import User
from app.models.statement import Statement, StatementStatus, StatementType
from app.schemas.statement import (
    Statement as StatementSchema,
    StatementUploadResponse
)
from app.services.statement_processor import process_statement
import os
import shutil
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=List[StatementSchema])
async def get_statements(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all statements for the current user
    """
    statements = db.query(Statement).filter(
        Statement.user_id == current_user.id
    ).order_by(Statement.uploaded_at.desc()).all()
    
    return statements


@router.get("/{statement_id}", response_model=StatementSchema)
async def get_statement(
    statement_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific statement by ID
    """
    statement = db.query(Statement).filter(
        Statement.id == statement_id,
        Statement.user_id == current_user.id
    ).first()
    
    if not statement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Statement not found"
        )
    
    return statement


@router.post("/upload", response_model=StatementUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_statement(
    file: UploadFile = File(...),
    statement_type: StatementType = Form(...),
    institution_name: str = Form(None),
    password: str = Form(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Upload a financial statement for processing
    Optional password parameter for encrypted PDFs (e.g., NSDL CAS)
    """
    from app.core.config import settings
    
    # Validate file extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    allowed_extensions = settings.ALLOWED_EXTENSIONS.split(',')
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {settings.ALLOWED_EXTENSIONS}"
        )
    
    # Validate file size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning
    
    if file_size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE / 1024 / 1024}MB"
        )
    
    # Create upload directory if it doesn't exist
    upload_dir = os.path.join(settings.UPLOAD_DIR, str(current_user.id))
    os.makedirs(upload_dir, exist_ok=True)
    
    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(upload_dir, safe_filename)
    
    # Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        logger.error(f"Failed to save uploaded file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save the uploaded file. Please try again."
        )
    
    # Create statement record
    new_statement = Statement(
        user_id=current_user.id,
        filename=file.filename,
        file_path=file_path,
        file_size=file_size,
        file_type=file.content_type,
        statement_type=statement_type,
        institution_name=institution_name,
        password=password,
        status=StatementStatus.UPLOADED
    )
    
    db.add(new_statement)
    db.commit()
    db.refresh(new_statement)
    
    # Process statement asynchronously (in a real app, use Celery or similar)
    try:
        process_statement(new_statement.id, db)
    except Exception as e:
        logger.error(f"Error processing statement {new_statement.id}: {e}")
        new_statement.status = StatementStatus.FAILED
        new_statement.error_message = str(e)
        db.commit()
    
    return StatementUploadResponse(
        statement_id=new_statement.id,
        filename=file.filename,
        status=new_statement.status.value,
        message="Statement uploaded and processing started"
    )


@router.delete("/{statement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_statement(
    statement_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete a statement, its associated file, transactions, and assets
    
    This will:
    1. Delete all assets directly linked to this statement (via statement_id)
    2. Delete all transactions linked to this statement
    3. Delete the statement file from disk
    4. Delete the statement record
    
    Note: Assets are deleted based on their statement_id field, regardless of
    whether they have been reclassified or modified after import.
    """
    from app.models.asset import Asset
    from app.models.transaction import Transaction
    
    statement = db.query(Statement).filter(
        Statement.id == statement_id,
        Statement.user_id == current_user.id
    ).first()
    
    if not statement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Statement not found"
        )
    
    # Delete all assets that were created from this statement
    # This includes assets that may have been reclassified by the user
    assets_to_delete = db.query(Asset).filter(
        Asset.statement_id == statement_id
    ).all()
    
    for asset in assets_to_delete:
        db.delete(asset)
    
    # Delete all transactions linked to this statement
    # (cascade should handle this, but being explicit)
    transactions = db.query(Transaction).filter(
        Transaction.statement_id == statement_id
    ).all()
    
    for transaction in transactions:
        db.delete(transaction)
    
    # Delete file if it exists
    if os.path.exists(statement.file_path):
        try:
            os.remove(statement.file_path)
        except Exception:
            pass  # Continue even if file deletion fails
    
    # Delete the statement record
    db.delete(statement)
    db.commit()
    
    return None

# Made with Bob
