"""
API endpoints for mutual fund holdings
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from difflib import SequenceMatcher
from app.core.database import get_db
from app.api.dependencies import get_current_active_user
from app.models.user import User
from app.models.asset import Asset, AssetType
from app.models.mutual_fund_holding import MutualFundHolding
from app.schemas.mutual_fund_holding import (
    MutualFundHolding as MutualFundHoldingSchema,
    MutualFundWithHoldings,
    HoldingsDashboardResponse,
    HoldingsDashboardStock,
    FundMappingPreview,
    UploadPreviewResponse,
    ConfirmImportRequest
)
from app.services.mutual_fund_holdings_service import MutualFundHoldingsService
from app.services.mutual_fund_holdings_csv_parser import MutualFundHoldingsCSVParser
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/{asset_id}/fetch", status_code=status.HTTP_200_OK)
async def fetch_mutual_fund_holdings(
    asset_id: int,
    force_refresh: bool = Query(False, description="Force refresh even if holdings exist"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Fetch and store holdings for a mutual fund
    """
    # Get the asset
    asset = db.query(Asset).filter(
        Asset.id == asset_id,
        Asset.user_id == current_user.id
    ).first()
    
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found"
        )
    
    # Verify it's a mutual fund
    if asset.asset_type not in [AssetType.EQUITY_MUTUAL_FUND, AssetType.DEBT_MUTUAL_FUND]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Asset is not a mutual fund"
        )
    
    # Fetch holdings
    success, message = MutualFundHoldingsService.update_fund_holdings(
        db, asset, current_user.id, force_refresh
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    # Get updated holdings count
    holdings_count = db.query(MutualFundHolding).filter(
        MutualFundHolding.asset_id == asset_id
    ).count()
    
    return {
        "success": True,
        "message": message,
        "holdings_count": holdings_count
    }


@router.post("/{asset_id}/upload-csv", status_code=status.HTTP_200_OK)
async def upload_holdings_csv(
    asset_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Upload CSV or Excel file containing mutual fund portfolio holdings
    
    Supported formats:
    - CSV (.csv)
    - Excel (.xlsx, .xls)
    
    CSV Format:
    Stock Name, Symbol, ISIN, Holding %, Sector, Industry, Market Cap
    
    Minimum required columns: Stock Name, Holding %
    """
    # Get the asset
    asset = db.query(Asset).filter(
        Asset.id == asset_id,
        Asset.user_id == current_user.id
    ).first()
    
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found"
        )
    
    # Verify it's an equity mutual fund
    if asset.asset_type != AssetType.EQUITY_MUTUAL_FUND:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Holdings tracking is only available for Equity Mutual Funds"
        )
    
    # Check file type
    filename = file.filename.lower()
    is_csv = filename.endswith('.csv')
    is_excel = filename.endswith(('.xlsx', '.xls'))
    
    if not (is_csv or is_excel):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a CSV (.csv) or Excel (.xlsx, .xls) file"
        )
    
    try:
        # Read file content
        content = await file.read()
        
        # Parse based on file type
        if is_csv:
            # Parse CSV
            holdings_data = MutualFundHoldingsCSVParser.parse_csv(content)
            
            # Validate holdings
            is_valid, message = MutualFundHoldingsCSVParser.validate_holdings(holdings_data)
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=message
                )
            
            # Convert to standard format
            holdings_data = [
                {
                    'name': h['stock_name'],
                    'isin': h.get('isin', ''),
                    'industry': h.get('industry', ''),
                    'percentage': h['holding_percentage'],
                    'stock_symbol': h.get('stock_symbol'),
                    'sector': h.get('sector'),
                    'market_cap': h.get('market_cap')
                }
                for h in holdings_data
            ]
        else:
            # Parse Excel
            import tempfile
            import os
            from app.services.generic_portfolio_parser import parse_portfolio
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp_file:
                tmp_file.write(content)
                tmp_path = tmp_file.name
            
            try:
                # Parse Excel
                holdings_data = parse_portfolio(tmp_path)
                
                if not holdings_data:
                    raise ValueError("No equity holdings found in Excel file")
                
            finally:
                # Clean up temp file
                try:
                    os.unlink(tmp_path)
                except:
                    pass
        
        # Delete existing holdings
        db.query(MutualFundHolding).filter(
            MutualFundHolding.asset_id == asset_id
        ).delete()
        
        # Create new holdings
        created_count = 0
        for holding_data in holdings_data:
            holding = MutualFundHolding(
                asset_id=asset_id,
                user_id=current_user.id,
                stock_name=holding_data['name'],
                stock_symbol=holding_data.get('stock_symbol'),
                isin=holding_data.get('isin'),
                holding_percentage=holding_data['percentage'],
                sector=holding_data.get('sector'),
                industry=holding_data.get('industry'),
                market_cap=holding_data.get('market_cap'),
                data_source='file_upload'
            )
            
            # Calculate holding value based on user's MF units
            if asset.quantity and asset.current_price:
                holding.calculate_holding_value(asset.quantity, asset.current_price)
            
            db.add(holding)
            created_count += 1
        
        db.commit()
        
        file_type = "CSV" if is_csv else "Excel"
        return {
            "success": True,
            "message": f"Successfully uploaded {created_count} holdings from {file_type}",
            "holdings_count": created_count
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process the uploaded file. Please ensure it is a valid portfolio file."
        )


@router.post("/{asset_id}/download-from-url", status_code=status.HTTP_200_OK)
async def download_and_parse_from_url(
    asset_id: int,
    url: str = Query(..., description="URL of the portfolio Excel file"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Download portfolio Excel file from URL and parse holdings
    
    Supports:
    - Direct Excel file URLs (.xls, .xlsx)
    - PPFAS portfolio URLs
    - Other AMC portfolio URLs
    
    The parser will automatically detect the format and extract equity holdings.
    """
    # Get the asset
    asset = db.query(Asset).filter(
        Asset.id == asset_id,
        Asset.user_id == current_user.id
    ).first()
    
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found"
        )
    
    # Verify it's an equity mutual fund
    if asset.asset_type != AssetType.EQUITY_MUTUAL_FUND:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Holdings tracking is only available for Equity Mutual Funds"
        )
    
    try:
        # Import services
        from app.services.portfolio_downloader import download_portfolio
        from app.services.generic_portfolio_parser import parse_portfolio
        import os
        
        logger.info(f"Downloading portfolio from URL: {url}")
        
        # Download the file
        file_path = download_portfolio(url)
        
        logger.info(f"Downloaded to: {file_path}")
        
        # Parse the file
        holdings_data = parse_portfolio(file_path)
        
        # Clean up downloaded file
        try:
            os.unlink(file_path)
        except:
            pass
        
        if not holdings_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No equity holdings found in the portfolio file"
            )
        
        logger.info(f"Parsed {len(holdings_data)} holdings")
        
        # Delete existing holdings
        db.query(MutualFundHolding).filter(
            MutualFundHolding.asset_id == asset_id
        ).delete()
        
        # Create new holdings
        created_count = 0
        for holding_data in holdings_data:
            holding = MutualFundHolding(
                asset_id=asset_id,
                user_id=current_user.id,
                stock_name=holding_data['name'],
                stock_symbol=holding_data.get('stock_symbol'),
                isin=holding_data.get('isin'),
                holding_percentage=holding_data['percentage'],
                sector=holding_data.get('sector'),
                industry=holding_data.get('industry'),
                market_cap=holding_data.get('market_cap'),
                data_source='url_download'
            )
            
            # Calculate holding value based on user's MF units
            if asset.quantity and asset.current_price:
                holding.calculate_holding_value(asset.quantity, asset.current_price)
            
            db.add(holding)
            created_count += 1
        
        db.commit()
        
        # Separate domestic and foreign for response
        domestic_count = sum(1 for h in holdings_data if not h.get('is_foreign', False))
        foreign_count = sum(1 for h in holdings_data if h.get('is_foreign', False))
        
        return {
            "success": True,
            "message": f"Successfully downloaded and parsed portfolio from URL",
            "holdings_count": created_count,
            "domestic_count": domestic_count,
            "foreign_count": foreign_count,
            "url": url
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading/parsing from URL: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not download or process the portfolio. Please try again."
        )


@router.post("/auto-update-all", status_code=status.HTTP_200_OK)
async def auto_update_all_holdings(
    force_refresh: bool = Query(False, description="Force refresh even if holdings exist"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Automatically update holdings for all equity mutual funds in the user's portfolio
    
    This endpoint will:
    1. Find all equity mutual funds in the user's portfolio
    2. Use AMFI scraper to find AMC portfolio disclosure URLs
    3. Download and parse the latest portfolio Excel files
    4. Update holdings for each fund
    
    Returns a summary of successful and failed updates.
    """
    try:
        from app.services.amfi_scraper import get_amfi_scraper
        from app.services.portfolio_downloader import download_portfolio
        from app.services.generic_portfolio_parser import parse_portfolio
        import os
        
        logger.info(f"Starting auto-update for all equity mutual funds for user {current_user.id}")
        
        # Get all equity mutual funds for this user
        equity_funds = db.query(Asset).filter(
            Asset.user_id == current_user.id,
            Asset.asset_type == AssetType.EQUITY_MUTUAL_FUND
        ).all()
        
        if not equity_funds:
            return {
                "success": True,
                "message": "No equity mutual funds found in portfolio",
                "total_funds": 0,
                "successful_updates": 0,
                "failed_updates": 0,
                "results": []
            }
        
        logger.info(f"Found {len(equity_funds)} equity mutual funds")
        
        # Initialize AMFI scraper
        scraper = get_amfi_scraper()
        
        results = []
        successful_updates = 0
        failed_updates = 0
        
        for asset in equity_funds:
            fund_result = {
                "asset_id": asset.id,
                "fund_name": asset.name,
                "success": False,
                "message": "",
                "holdings_count": 0
            }
            
            try:
                # Check if we should skip (already has holdings and not force refresh)
                if not force_refresh:
                    existing_holdings = db.query(MutualFundHolding).filter(
                        MutualFundHolding.asset_id == asset.id
                    ).count()
                    
                    if existing_holdings > 0:
                        fund_result["success"] = True
                        fund_result["message"] = f"Skipped - already has {existing_holdings} holdings (use force_refresh=true to update)"
                        fund_result["holdings_count"] = existing_holdings
                        results.append(fund_result)
                        successful_updates += 1
                        continue
                
                # Step 1: Check if asset already has AMC URL in details
                amc_url = None
                if asset.details and isinstance(asset.details, dict):
                    amc_url = asset.details.get('amc_portfolio_url')
                
                # Step 2: If no URL, try to find it using AMFI scraper
                if not amc_url:
                    logger.info(f"Finding AMC URL for: {asset.name}")
                    amc_url = scraper.get_amc_url_for_fund(asset.name)
                    
                    if amc_url:
                        # Store the URL in asset details for future use
                        if not asset.details:
                            asset.details = {}
                        asset.details['amc_portfolio_url'] = amc_url
                        db.commit()
                        logger.info(f"Stored AMC URL for {asset.name}: {amc_url}")
                
                if not amc_url:
                    fund_result["message"] = "Could not find AMC portfolio disclosure URL"
                    results.append(fund_result)
                    failed_updates += 1
                    logger.warning(f"No AMC URL found for: {asset.name}")
                    continue
                
                # Step 3: Try to find direct Excel URL from the AMC page
                logger.info(f"Searching for Excel file at: {amc_url}")
                excel_url = scraper.find_latest_excel_url(amc_url)
                
                if not excel_url:
                    # If no direct Excel URL found, try using the AMC page URL itself
                    excel_url = amc_url
                
                logger.info(f"Downloading portfolio from: {excel_url}")
                
                # Step 4: Download the portfolio file
                file_path = download_portfolio(excel_url)
                
                # Step 5: Parse the file
                holdings_data = parse_portfolio(file_path)
                
                # Clean up downloaded file
                try:
                    os.unlink(file_path)
                except:
                    pass
                
                if not holdings_data:
                    fund_result["message"] = "No equity holdings found in portfolio file"
                    results.append(fund_result)
                    failed_updates += 1
                    continue
                
                logger.info(f"Parsed {len(holdings_data)} holdings for {asset.name}")
                
                # Step 6: Delete existing holdings
                db.query(MutualFundHolding).filter(
                    MutualFundHolding.asset_id == asset.id
                ).delete()
                
                # Step 7: Create new holdings
                created_count = 0
                for holding_data in holdings_data:
                    holding = MutualFundHolding(
                        asset_id=asset.id,
                        user_id=current_user.id,
                        stock_name=holding_data['name'],
                        stock_symbol=holding_data.get('stock_symbol'),
                        isin=holding_data.get('isin'),
                        holding_percentage=holding_data['percentage'],
                        sector=holding_data.get('sector'),
                        industry=holding_data.get('industry'),
                        market_cap=holding_data.get('market_cap'),
                        data_source='auto_update'
                    )
                    
                    # Calculate holding value based on user's MF units
                    if asset.quantity and asset.current_price:
                        holding.calculate_holding_value(asset.quantity, asset.current_price)
                    
                    db.add(holding)
                    created_count += 1
                
                db.commit()
                
                fund_result["success"] = True
                fund_result["message"] = f"Successfully updated {created_count} holdings"
                fund_result["holdings_count"] = created_count
                fund_result["source_url"] = excel_url
                results.append(fund_result)
                successful_updates += 1
                
                logger.info(f"Successfully updated holdings for {asset.name}")
                
            except Exception as e:
                logger.error(f"Error updating holdings for {asset.name}: {str(e)}")
                fund_result["message"] = f"Error: {str(e)}"
                results.append(fund_result)
                failed_updates += 1
                db.rollback()
        
        return {
            "success": True,
            "message": f"Auto-update completed: {successful_updates} successful, {failed_updates} failed",
            "total_funds": len(equity_funds),
            "successful_updates": successful_updates,
            "failed_updates": failed_updates,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error in auto-update-all: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Holdings auto-update failed. Please try again later."
        )


@router.post("/import-from-consolidated-file", status_code=status.HTTP_200_OK)
async def import_from_consolidated_file(
    file_path: str = Query(default="../statements/mfs/MF-Holdings.xlsx", description="Path to consolidated Excel file"),
    similarity_threshold: float = Query(default=0.6, description="Minimum similarity score for fund matching (0-1)"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Import holdings from a consolidated Excel file with multiple tabs
    
    Each tab should contain holdings for one mutual fund.
    The system will:
    1. Parse all tabs in the Excel file
    2. Extract fund names from each tab
    3. Match fund names to assets in your portfolio
    4. Import holdings for matched funds
    
    Returns a summary of successful and failed imports.
    """
    try:
        from app.services.consolidated_mf_parser import ConsolidatedMFParser, match_fund_to_asset
        import os
        
        # Resolve file path relative to backend directory
        if not os.path.isabs(file_path):
            file_path = os.path.join(os.path.dirname(__file__), '../../../../', file_path)
            file_path = os.path.abspath(file_path)
        
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {file_path}"
            )
        
        logger.info(f"Importing from consolidated file: {file_path}")
        
        # Parse the consolidated file
        parser = ConsolidatedMFParser(file_path)
        all_funds = parser.parse_all_funds()
        
        if not all_funds:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No funds found in the Excel file"
            )
        
        logger.info(f"Parsed {len(all_funds)} funds from file")
        
        # Get all equity mutual funds for this user
        equity_funds = db.query(Asset).filter(
            Asset.user_id == current_user.id,
            Asset.asset_type == AssetType.EQUITY_MUTUAL_FUND
        ).all()
        
        if not equity_funds:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No equity mutual funds found in your portfolio"
            )
        
        # Get asset names for matching
        asset_names = [fund.name for fund in equity_funds]
        asset_map = {fund.name: fund for fund in equity_funds}
        
        results = []
        successful_imports = 0
        failed_imports = 0
        
        # Match and import each fund
        for fund_name_from_excel, holdings in all_funds.items():
            result = {
                "fund_name_from_excel": fund_name_from_excel,
                "matched_asset": None,
                "similarity_score": 0.0,
                "success": False,
                "message": "",
                "holdings_count": 0
            }
            
            try:
                # Match fund name to asset
                matched_asset_name, similarity_score = match_fund_to_asset(
                    fund_name_from_excel,
                    asset_names
                )
                
                result["matched_asset"] = matched_asset_name
                result["similarity_score"] = round(similarity_score, 2)
                
                if similarity_score < similarity_threshold:
                    result["message"] = f"No good match found (best score: {similarity_score:.2f})"
                    results.append(result)
                    failed_imports += 1
                    continue
                
                # Get the matched asset
                asset = asset_map[matched_asset_name]
                
                # Delete existing holdings
                db.query(MutualFundHolding).filter(
                    MutualFundHolding.asset_id == asset.id
                ).delete()
                
                # Create new holdings
                created_count = 0
                for holding_data in holdings:
                    holding = MutualFundHolding(
                        asset_id=asset.id,
                        user_id=current_user.id,
                        stock_name=holding_data['name'],
                        isin=holding_data.get('isin'),
                        holding_percentage=holding_data['percentage'],
                        sector=holding_data.get('sector'),
                        industry=holding_data.get('industry'),
                        data_source='consolidated_file'
                    )
                    
                    # Calculate holding value
                    if asset.quantity and asset.current_price:
                        holding.calculate_holding_value(asset.quantity, asset.current_price)
                    
                    db.add(holding)
                    created_count += 1
                
                db.commit()
                
                result["success"] = True
                result["holdings_count"] = created_count
                result["message"] = f"Successfully imported {created_count} holdings"
                results.append(result)
                successful_imports += 1
                
                logger.info(f"Imported {created_count} holdings for {matched_asset_name}")
                
            except Exception as e:
                logger.error(f"Error importing {fund_name_from_excel}: {e}")
                result["message"] = f"Error: {str(e)}"
                results.append(result)
                failed_imports += 1
                db.rollback()
        
        return {
            "success": True,
            "message": f"Import completed: {successful_imports} successful, {failed_imports} failed",
            "file_path": file_path,
            "total_funds_in_file": len(all_funds),
            "total_funds_in_portfolio": len(equity_funds),
            "successful_imports": successful_imports,
            "failed_imports": failed_imports,
            "similarity_threshold": similarity_threshold,
            "results": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in import-from-consolidated-file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to import data from the file. Please check the format."
        )


@router.post("/upload-consolidated-file", status_code=status.HTTP_200_OK)
async def upload_consolidated_file(
    file: UploadFile = File(..., description="Consolidated Excel file with multiple tabs"),
    similarity_threshold: float = Query(default=0.6, description="Minimum similarity score for fund matching (0-1)"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Upload and process a consolidated Excel file with multiple mutual fund holdings
    
    The Excel file should have:
    - Multiple tabs (one per mutual fund)
    - Fund name in the first few rows of each tab
    - Columns for: Stock Name, ISIN, Percentage
    
    The system will:
    1. Parse all tabs in the Excel file
    2. Extract fund names and holdings from each tab
    3. Match fund names to assets in your portfolio
    4. Import holdings for matched funds
    
    Returns a summary of successful and failed imports.
    """
    try:
        from app.services.consolidated_mf_parser import ConsolidatedMFParser, match_fund_to_asset
        import os
        import tempfile
        
        # Validate file type
        if not file.filename or not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be an Excel file (.xlsx or .xls)"
            )
        
        logger.info(f"Processing uploaded file: {file.filename}")
        
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        try:
            # Parse the consolidated file
            parser = ConsolidatedMFParser(tmp_file_path)
            all_funds = parser.parse_all_funds()
            
            if not all_funds:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No funds found in the Excel file. Please check the file format."
                )
            
            logger.info(f"Parsed {len(all_funds)} funds from uploaded file")
            
            # Get all equity mutual funds for this user
            equity_funds = db.query(Asset).filter(
                Asset.user_id == current_user.id,
                Asset.asset_type == AssetType.EQUITY_MUTUAL_FUND
            ).all()
            
            if not equity_funds:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No equity mutual funds found in your portfolio"
                )
            
            # Get asset names for matching
            asset_names = [fund.name for fund in equity_funds]
            asset_map = {fund.name: fund for fund in equity_funds}
            
            results = []
            successful_imports = 0
            failed_imports = 0
            
            # Match and import each fund
            for fund_name_from_excel, holdings in all_funds.items():
                result = {
                    "fund_name_from_excel": fund_name_from_excel,
                    "matched_asset": None,
                    "similarity_score": 0.0,
                    "success": False,
                    "message": "",
                    "holdings_count": 0
                }
                
                try:
                    # Match fund name to asset
                    matched_asset_name, similarity_score = match_fund_to_asset(
                        fund_name_from_excel,
                        asset_names
                    )
                    
                    result["matched_asset"] = matched_asset_name
                    result["similarity_score"] = round(similarity_score, 2)
                    
                    if similarity_score < similarity_threshold:
                        result["message"] = (
                            f"No good match found (best score: {similarity_score:.2f}). "
                            f"To fix: In Excel, rename the sheet or update the fund name in first row to match "
                            f"your portfolio fund name: '{matched_asset_name}'"
                        )
                        results.append(result)
                        failed_imports += 1
                        continue
                    
                    # Get the matched asset
                    asset = asset_map[matched_asset_name]
                    
                    # Delete existing holdings
                    db.query(MutualFundHolding).filter(
                        MutualFundHolding.asset_id == asset.id
                    ).delete()
                    
                    # Create new holdings
                    created_count = 0
                    for holding_data in holdings:
                        holding = MutualFundHolding(
                            asset_id=asset.id,
                            user_id=current_user.id,
                            stock_name=holding_data['name'],
                            isin=holding_data.get('isin'),
                            holding_percentage=holding_data['percentage'],
                            sector=holding_data.get('sector'),
                            industry=holding_data.get('industry'),
                            data_source='uploaded_file'
                        )
                        
                        # Calculate holding value
                        if asset.quantity and asset.current_price:
                            holding.calculate_holding_value(asset.quantity, asset.current_price)
                        
                        db.add(holding)
                        created_count += 1
                    
                    db.commit()
                    
                    result["success"] = True
                    result["holdings_count"] = created_count
                    result["message"] = f"Successfully imported {created_count} holdings"
                    results.append(result)
                    successful_imports += 1
                    
                    logger.info(f"Imported {created_count} holdings for {matched_asset_name}")
                    
                except Exception as e:
                    logger.error(f"Error importing {fund_name_from_excel}: {e}")
                    result["message"] = f"Error: {str(e)}"
                    results.append(result)
                    failed_imports += 1
                    db.rollback()
            
            return {
                "success": True,
                "message": f"Import completed: {successful_imports} successful, {failed_imports} failed",
                "filename": file.filename,
                "total_funds_in_file": len(all_funds),
                "total_funds_in_portfolio": len(equity_funds),
                "successful_imports": successful_imports,
                "failed_imports": failed_imports,
                "similarity_threshold": similarity_threshold,
                "results": results
            }
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(tmp_file_path)
            except:
                pass
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in upload-consolidated-file: {str(e)}")

@router.post("/preview-consolidated-file", status_code=status.HTTP_200_OK)
async def preview_consolidated_file(
    file: UploadFile = File(..., description="Consolidated Excel file with multiple tabs"),
    similarity_threshold: float = Query(default=0.6, description="Minimum similarity score for auto-matching (0-1)"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Step 1: Preview fund mappings before importing
    
    Upload Excel file and get a preview of how funds will be matched.
    User can then confirm or modify mappings before actual import.
    
    Returns:
        - List of funds found in Excel
        - Suggested matches from user's portfolio
        - Similarity scores
        - Which funds can be auto-imported
    """
    try:
        from app.services.consolidated_mf_parser import ConsolidatedMFParser, match_fund_to_asset
        from app.schemas.mutual_fund_holding import FundMappingPreview, UploadPreviewResponse
        import os
        import tempfile
        import uuid
        
        # Validate file type
        if not file.filename or not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be an Excel file (.xlsx or .xls)"
            )
        
        logger.info(f"Previewing uploaded file: {file.filename}")
        
        # Generate temporary file ID
        temp_file_id = str(uuid.uuid4())
        
        # Save uploaded file to temporary location with unique ID
        temp_dir = tempfile.gettempdir()
        temp_file_path = os.path.join(temp_dir, f"mf_upload_{temp_file_id}{os.path.splitext(file.filename)[1]}")
        
        content = await file.read()
        with open(temp_file_path, 'wb') as f:
            f.write(content)
        
        try:
            # Parse the consolidated file
            parser = ConsolidatedMFParser(temp_file_path)
            all_funds = parser.parse_all_funds()
            
            if not all_funds:
                # Clean up temp file
                os.unlink(temp_file_path)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No funds found in the Excel file. Please check the file format."
                )
            
            logger.info(f"Parsed {len(all_funds)} funds from uploaded file")
            
            # Get all equity mutual funds for this user
            equity_funds = db.query(Asset).filter(
                Asset.user_id == current_user.id,
                Asset.asset_type == AssetType.EQUITY_MUTUAL_FUND
            ).all()
            
            if not equity_funds:
                # Clean up temp file
                os.unlink(temp_file_path)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No equity mutual funds found in your portfolio. Please add funds first."
                )
            
            # Get asset names for matching
            asset_names = [fund.name for fund in equity_funds]
            asset_map = {fund.name: fund for fund in equity_funds}
            
            mappings = []
            
            # Match each fund and create preview - find ALL matching funds
            for fund_name_from_excel, holdings in all_funds.items():
                # Find all funds that match above threshold
                matching_funds = []
                for fund in equity_funds:
                    similarity = SequenceMatcher(None, fund_name_from_excel.lower(), fund.name.lower()).ratio()
                    if similarity >= similarity_threshold:
                        matching_funds.append((fund, similarity))
                
                if matching_funds:
                    # Sort by similarity score (highest first)
                    matching_funds.sort(key=lambda x: x[1], reverse=True)
                    
                    # Create a mapping entry showing all matches
                    best_match, best_score = matching_funds[0]
                    all_matched_ids = [f.id for f, _ in matching_funds]
                    all_matched_names = ", ".join([f.name for f, _ in matching_funds])
                    
                    # Create mapping with all matched IDs
                    mapping = FundMappingPreview(
                        fund_name_from_excel=fund_name_from_excel,
                        matched_asset_id=best_match.id,  # Keep for backward compatibility
                        matched_asset_name=all_matched_names if len(matching_funds) > 1 else best_match.name,
                        similarity_score=round(best_score, 2),
                        holdings_count=len(holdings),
                        can_auto_import=True,
                        needs_confirmation=False,
                        all_matched_asset_ids=all_matched_ids,
                        match_count=len(matching_funds)
                    )
                    
                    mappings.append(mapping)
                else:
                    # No match found above threshold
                    # Try to find best match even if below threshold
                    matched_asset_name, similarity_score = match_fund_to_asset(
                        fund_name_from_excel,
                        asset_names
                    )
                    
                    matched_asset = asset_map.get(matched_asset_name) if matched_asset_name else None
                    
                    mapping = FundMappingPreview(
                        fund_name_from_excel=fund_name_from_excel,
                        matched_asset_id=matched_asset.id if matched_asset else None,
                        matched_asset_name=matched_asset_name,
                        similarity_score=round(similarity_score, 2),
                        holdings_count=len(holdings),
                        can_auto_import=False,
                        needs_confirmation=True,
                        all_matched_asset_ids=[matched_asset.id] if matched_asset else [],
                        match_count=1 if matched_asset else 0
                    )
                    
                    mappings.append(mapping)
            
            # Sort mappings: auto-importable first, then by score
            mappings.sort(key=lambda x: (not x.can_auto_import, -x.similarity_score))
            
            auto_count = sum(1 for m in mappings if m.can_auto_import)
            manual_count = sum(1 for m in mappings if m.needs_confirmation)
            
            message = (
                f"Found {len(all_funds)} funds in Excel file. "
                f"{auto_count} can be auto-imported, {manual_count} need confirmation."
            )
            
            response = UploadPreviewResponse(
                temp_file_id=temp_file_id,
                total_funds_in_file=len(all_funds),
                total_funds_in_portfolio=len(equity_funds),
                mappings=mappings,
                message=message
            )
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            # Clean up temp file on error
            try:
                os.unlink(temp_file_path)
            except:
                pass
            raise
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in preview-consolidated-file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not preview the file. Please check the format."
        )


@router.post("/confirm-consolidated-import", status_code=status.HTTP_200_OK)
async def confirm_consolidated_import(
    request: "ConfirmImportRequest",
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Step 2: Confirm and execute import with user-approved mappings
    
    After user reviews and confirms/modifies the fund mappings,
    this endpoint performs the actual import.
    
    Args:
        request: Contains temp_file_id and confirmed mappings
        
    Returns:
        Import results for each fund
    """
    try:
        from app.services.consolidated_mf_parser import ConsolidatedMFParser
        from app.schemas.mutual_fund_holding import ConfirmImportRequest
        import os
        import tempfile
        
        # Reconstruct temp file path
        temp_dir = tempfile.gettempdir()
        temp_files = [f for f in os.listdir(temp_dir) if f.startswith(f"mf_upload_{request.temp_file_id}")]
        
        if not temp_files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Upload session expired. Please upload the file again."
            )
        
        temp_file_path = os.path.join(temp_dir, temp_files[0])
        
        try:
            # Parse the file again
            parser = ConsolidatedMFParser(temp_file_path)
            all_funds = parser.parse_all_funds()
            
            # Create mapping dict from confirmed mappings (fund name -> list of asset IDs)
            confirmed_map = {
                mapping.fund_name_from_excel: mapping.asset_ids
                for mapping in request.confirmed_mappings
            }
            
            results = []
            successful_imports = 0
            failed_imports = 0
            
            # Import each confirmed fund
            for fund_name_from_excel, holdings in all_funds.items():
                # Check if user confirmed this fund
                if fund_name_from_excel not in confirmed_map:
                    result = {
                        "fund_name_from_excel": fund_name_from_excel,
                        "success": False,
                        "message": "Skipped by user",
                        "holdings_count": 0
                    }
                    results.append(result)
                    continue
                
                asset_ids = confirmed_map[fund_name_from_excel]
                
                # Import holdings for ALL matched assets
                for asset_id in asset_ids:
                    result = {
                        "fund_name_from_excel": fund_name_from_excel,
                        "asset_id": asset_id,
                        "success": False,
                        "message": "",
                        "holdings_count": 0
                    }
                    
                    try:
                        # Get the asset
                        asset = db.query(Asset).filter(
                            Asset.id == asset_id,
                            Asset.user_id == current_user.id
                        ).first()
                        
                        if not asset:
                            result["message"] = f"Asset ID {asset_id} not found or access denied"
                            results.append(result)
                            failed_imports += 1
                            continue
                        
                        result["fund_name"] = asset.name
                        
                        # Delete existing holdings for this asset
                        db.query(MutualFundHolding).filter(
                            MutualFundHolding.asset_id == asset_id
                        ).delete()
                        
                        # Create new holdings
                        created_count = 0
                        for holding_data in holdings:
                            holding = MutualFundHolding(
                                asset_id=asset_id,
                                user_id=current_user.id,
                                stock_name=holding_data['name'],
                                isin=holding_data.get('isin'),
                                holding_percentage=holding_data['percentage'],
                                sector=holding_data.get('sector'),
                                industry=holding_data.get('industry'),
                                data_source='confirmed_upload'
                            )
                            
                            # Calculate holding value
                            if asset.quantity and asset.current_price:
                                holding.calculate_holding_value(asset.quantity, asset.current_price)
                            
                            db.add(holding)
                            created_count += 1
                        
                        db.commit()
                        
                        result["success"] = True
                        result["holdings_count"] = created_count
                        result["message"] = f"Successfully imported {created_count} holdings for {asset.name}"
                        results.append(result)
                        successful_imports += 1
                        
                        logger.info(f"Imported {created_count} holdings for {asset.name}")
                        
                    except Exception as e:
                        logger.error(f"Error importing to asset {asset_id}: {e}")
                        result["message"] = f"Error: {str(e)}"
                        results.append(result)
                        failed_imports += 1
                        db.rollback()
            
            # Clean up temp file
            try:
                os.unlink(temp_file_path)
            except:
                pass
            
            return {
                "success": True,
                "message": f"Import completed: {successful_imports} successful, {failed_imports} failed",
                "successful_imports": successful_imports,
                "failed_imports": failed_imports,
                "results": results
            }
            
        finally:
            # Ensure temp file is cleaned up
            try:
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
            except:
                pass
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in confirm-consolidated-import: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Import failed. Please check the file format and try again."
        )


@router.get("/sample-csv/download")
async def download_sample_csv(
    current_user: User = Depends(get_current_active_user)
):
    """
    Download a sample CSV template for portfolio holdings
    """
    from fastapi.responses import Response
    
    csv_content = MutualFundHoldingsCSVParser.generate_sample_csv()
    
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=mutual_fund_holdings_template.csv"
        }
    )


@router.get("/{asset_id}", response_model=MutualFundWithHoldings)
async def get_mutual_fund_holdings(
    asset_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all holdings for a specific mutual fund
    """
    # Get the asset
    asset = db.query(Asset).filter(
        Asset.id == asset_id,
        Asset.user_id == current_user.id
    ).first()
    
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found"
        )
    
    # Get holdings
    holdings = MutualFundHoldingsService.get_fund_holdings(db, asset_id, current_user.id)
    
    # Get last updated time
    last_updated = None
    if holdings:
        last_updated = max(h.last_updated for h in holdings)
    
    return MutualFundWithHoldings(
        asset_id=asset.id,
        fund_name=asset.name,
        fund_symbol=asset.symbol,
        isin=asset.isin,
        units_held=asset.quantity,
        current_nav=asset.current_price,
        total_value=asset.current_value,
        holdings=[MutualFundHoldingSchema.model_validate(h) for h in holdings],
        holdings_count=len(holdings),
        last_updated=last_updated
    )


@router.get("/", response_model=List[MutualFundWithHoldings])
async def get_all_mutual_fund_holdings(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get holdings for all mutual funds owned by the user
    """
    # Get all equity mutual fund assets only
    mf_assets = db.query(Asset).filter(
        Asset.user_id == current_user.id,
        Asset.asset_type == AssetType.EQUITY_MUTUAL_FUND,
        Asset.is_active == True
    ).all()
    
    result = []
    for asset in mf_assets:
        holdings = MutualFundHoldingsService.get_fund_holdings(db, asset.id, current_user.id)
        
        last_updated = None
        if holdings:
            last_updated = max(h.last_updated for h in holdings)
        
        result.append(MutualFundWithHoldings(
            asset_id=asset.id,
            fund_name=asset.name,
            fund_symbol=asset.symbol,
            isin=asset.isin,
            units_held=asset.quantity,
            current_nav=asset.current_price,
            total_value=asset.current_value,
            holdings=[MutualFundHoldingSchema.model_validate(h) for h in holdings],
            holdings_count=len(holdings),
            last_updated=last_updated
        ))
    
    return result


@router.get("/validate-holdings")
async def validate_holdings(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Validate holdings - check for duplicates and percentage totals
    """
    # Get all equity MF assets
    mf_assets = db.query(Asset).filter(
        Asset.user_id == current_user.id,
        Asset.asset_type == AssetType.EQUITY_MUTUAL_FUND,
        Asset.is_active == True
    ).all()
    
    validation_results = []
    
    for asset in mf_assets:
        # Get all holdings for this fund
        holdings = db.query(MutualFundHolding).filter(
            MutualFundHolding.asset_id == asset.id
        ).all()
        
        # Calculate total percentage
        total_percentage = sum(h.holding_percentage for h in holdings)
        
        # Check for duplicate stocks
        stock_names = [h.stock_name for h in holdings]
        duplicates = [name for name in set(stock_names) if stock_names.count(name) > 1]
        
        validation_results.append({
            "fund_id": asset.id,
            "fund_name": asset.name,
            "total_holdings": len(holdings),
            "total_percentage": round(total_percentage, 2),
            "is_valid": total_percentage <= 100 and len(duplicates) == 0,
            "has_duplicates": len(duplicates) > 0,
            "duplicate_stocks": duplicates,
            "percentage_overflow": max(0, total_percentage - 100) if total_percentage > 100 else 0
        })
    
    return {
        "validation_results": validation_results,
        "total_funds_checked": len(mf_assets),
        "funds_with_issues": sum(1 for r in validation_results if not r["is_valid"])
    }


@router.get("/dashboard/stocks", response_model=HoldingsDashboardResponse)
async def get_holdings_dashboard(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get aggregated stock holdings dashboard combining direct stocks and MF holdings
    """
    # Get all MF holdings
    mf_holdings = db.query(MutualFundHolding).filter(
        MutualFundHolding.user_id == current_user.id
    ).all()
    
    # Get all direct stock holdings
    direct_stocks = db.query(Asset).filter(
        Asset.user_id == current_user.id,
        Asset.asset_type == AssetType.STOCK,
        Asset.is_active == True
    ).all()
    
    # Aggregate by stock (using ISIN or symbol as key)
    stock_map = {}
    
    # Process MF holdings
    for holding in mf_holdings:
        key = holding.isin if holding.isin else holding.stock_symbol or holding.stock_name
        
        if key not in stock_map:
            stock_map[key] = {
                'stock_name': holding.stock_name,
                'stock_symbol': holding.stock_symbol,
                'isin': holding.isin,
                'direct_quantity': 0.0,
                'direct_value': 0.0,
                'direct_invested': 0.0,
                'mf_quantity': 0.0,
                'mf_value': 0.0,
                'mf_holding_percentage': 0.0,
                'mf_count': 0,
                'mutual_funds': [],
                'current_price': holding.stock_current_price,
                'sector': holding.sector,
                'industry': holding.industry,
                'market_cap': holding.market_cap,
                'profit_loss': 0.0,
                'profit_loss_percentage': 0.0
            }
        
        # Get the MF asset to add fund name and recalculate holding value
        mf_asset = db.query(Asset).filter(Asset.id == holding.asset_id).first()
        if mf_asset:
            if mf_asset.name not in stock_map[key]['mutual_funds']:
                stock_map[key]['mutual_funds'].append(mf_asset.name)
                stock_map[key]['mf_count'] += 1
            
            # Recalculate holding value using current MF units and NAV
            if mf_asset.quantity and mf_asset.current_price:
                total_mf_value = mf_asset.quantity * mf_asset.current_price
                current_holding_value = total_mf_value * (holding.holding_percentage / 100)
                
                # Recalculate quantity based on current stock price
                if holding.stock_current_price and holding.stock_current_price > 0:
                    current_quantity = current_holding_value / holding.stock_current_price
                else:
                    current_quantity = holding.quantity_held
                
                stock_map[key]['mf_quantity'] += current_quantity
                stock_map[key]['mf_value'] += current_holding_value
            else:
                # Fallback to stored values if MF asset doesn't have quantity/price
                stock_map[key]['mf_quantity'] += holding.quantity_held
                stock_map[key]['mf_value'] += holding.holding_value
            
            stock_map[key]['mf_holding_percentage'] += holding.holding_percentage
    
    # Process direct stock holdings
    for stock in direct_stocks:
        key = stock.isin if stock.isin else stock.symbol or stock.name
        
        if key not in stock_map:
            stock_map[key] = {
                'stock_name': stock.name,
                'stock_symbol': stock.symbol,
                'isin': stock.isin,
                'direct_quantity': 0.0,
                'direct_value': 0.0,
                'direct_invested': 0.0,
                'mf_quantity': 0.0,
                'mf_value': 0.0,
                'mf_holding_percentage': 0.0,
                'mf_count': 0,
                'mutual_funds': [],
                'current_price': stock.current_price,
                'sector': stock.details.get('sector') if stock.details else None,
                'industry': stock.details.get('industry') if stock.details else None,
                'market_cap': stock.details.get('market_cap') if stock.details else None,
                'profit_loss': 0.0,
                'profit_loss_percentage': 0.0
            }
        
        stock_map[key]['direct_quantity'] += stock.quantity
        stock_map[key]['direct_value'] += stock.current_value
        stock_map[key]['direct_invested'] += stock.total_invested
        stock_map[key]['profit_loss'] += stock.profit_loss
        if stock.total_invested > 0:
            stock_map[key]['profit_loss_percentage'] = (
                stock_map[key]['profit_loss'] / stock_map[key]['direct_invested'] * 100
            )
    
    # Calculate totals and create response
    stocks = []
    for key, data in stock_map.items():
        # Calculate average MF holding percentage
        if data['mf_count'] > 0:
            data['mf_holding_percentage'] = data['mf_holding_percentage'] / data['mf_count']
        
        data['total_quantity'] = data['direct_quantity'] + data['mf_quantity']
        data['total_value'] = data['direct_value'] + data['mf_value']
        
        stocks.append(HoldingsDashboardStock(**data))
    
    # Sort by total value descending
    stocks.sort(key=lambda x: x.total_value, reverse=True)
    
    # Calculate summary
    summary = {
        'total_stocks': len(stocks),
        'total_direct_value': sum(s.direct_value for s in stocks),
        'total_mf_value': sum(s.mf_value for s in stocks),
        'total_value': sum(s.total_value for s in stocks),
        'stocks_with_direct_holdings': sum(1 for s in stocks if s.direct_quantity > 0),
        'stocks_with_mf_holdings': sum(1 for s in stocks if s.mf_quantity > 0),
        'stocks_with_both': sum(1 for s in stocks if s.direct_quantity > 0 and s.mf_quantity > 0)
    }
    
    return HoldingsDashboardResponse(
        stocks=stocks,
        summary=summary,
        last_updated=datetime.utcnow()
    )


@router.post("/recalculate/{asset_id}")
async def recalculate_holdings_values(
    asset_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Recalculate holding values for a mutual fund (useful after NAV or units update)
    """
    # Get the asset
    asset = db.query(Asset).filter(
        Asset.id == asset_id,
        Asset.user_id == current_user.id
    ).first()
    
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found"
        )
    
    # Recalculate
    updated_count = MutualFundHoldingsService.recalculate_holding_values(db, asset)
    
    return {
        "success": True,
        "message": f"Recalculated {updated_count} holdings",
        "updated_count": updated_count
    }


# Made with Bob