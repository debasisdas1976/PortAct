"""
Tradebook parser for Zerodha and Groww equity/mutual fund tradebooks.
Supports both CSV and Excel (xlsx) formats.
"""
import pandas as pd
import logging
from typing import List, Dict, Any, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# Zerodha tradebook CSV columns
TRADEBOOK_COLUMNS = {
    'symbol', 'isin', 'trade_date', 'exchange', 'segment',
    'series', 'trade_type', 'auction', 'quantity', 'price',
    'trade_id', 'order_id', 'order_execution_time',
}


def is_zerodha_tradebook_csv(df: pd.DataFrame) -> bool:
    """Check if a DataFrame looks like a Zerodha tradebook CSV."""
    try:
        cols = {c.strip().lower() for c in df.columns}
        required = {'symbol', 'trade_date', 'trade_type', 'quantity', 'price'}
        return required.issubset(cols)
    except Exception:
        return False


def is_zerodha_tradebook_excel(file_path: str) -> bool:
    """Check if an Excel file is a Zerodha tradebook by inspecting the header row."""
    try:
        df_raw = pd.read_excel(file_path, header=None, nrows=20, engine='openpyxl')
        for i in range(min(20, len(df_raw))):
            row_values = [str(v).strip().lower().replace(' ', '_') for v in df_raw.iloc[i].values if pd.notna(v)]
            if 'symbol' in row_values and 'trade_date' in row_values and 'trade_type' in row_values:
                return True
        return False
    except Exception:
        return False


def _read_tradebook_excel(file_path: str) -> pd.DataFrame:
    """Read a Zerodha tradebook Excel file, auto-detecting the header row."""
    df_raw = pd.read_excel(file_path, header=None, engine='openpyxl')

    header_row = None
    for i in range(min(30, len(df_raw))):
        row_values = [str(v).strip().lower().replace(' ', '_') for v in df_raw.iloc[i].values if pd.notna(v)]
        if 'symbol' in row_values and 'trade_date' in row_values:
            header_row = i
            break

    if header_row is None:
        raise ValueError("Could not find tradebook header row in Excel file")

    # Build proper headers, skipping leading None columns
    headers = []
    for val in df_raw.iloc[header_row].values:
        if pd.notna(val):
            headers.append(str(val).strip().lower().replace(' ', '_'))
        else:
            headers.append(f'_skip_{len(headers)}')

    df = df_raw.iloc[header_row + 1:].copy()
    df.columns = headers
    # Drop placeholder columns
    df = df[[c for c in df.columns if not c.startswith('_skip_')]]
    df = df.dropna(subset=['symbol'])
    df = df.reset_index(drop=True)
    return df


def _read_tradebook_excel_all_sheets(file_path: str) -> pd.DataFrame:
    """Read all sheets from a Zerodha tradebook Excel file and concatenate."""
    xl = pd.ExcelFile(file_path, engine='openpyxl')
    frames = []
    for sheet_name in xl.sheet_names:
        df_raw = pd.read_excel(file_path, sheet_name=sheet_name, header=None, engine='openpyxl')

        header_row = None
        for i in range(min(30, len(df_raw))):
            row_values = [str(v).strip().lower().replace(' ', '_') for v in df_raw.iloc[i].values if pd.notna(v)]
            if 'symbol' in row_values and 'trade_date' in row_values:
                header_row = i
                break

        if header_row is None:
            continue

        headers = []
        for val in df_raw.iloc[header_row].values:
            if pd.notna(val):
                headers.append(str(val).strip().lower().replace(' ', '_'))
            else:
                headers.append(f'_skip_{len(headers)}')

        df = df_raw.iloc[header_row + 1:].copy()
        df.columns = headers
        df = df[[c for c in df.columns if not c.startswith('_skip_')]]
        df = df.dropna(subset=['symbol'])

        # Add segment info from sheet name if not in columns
        sheet_lower = sheet_name.strip().lower()
        if 'segment' not in df.columns:
            if 'mutual' in sheet_lower or 'mf' in sheet_lower:
                df['segment'] = 'MF'
            else:
                df['segment'] = 'EQ'

        frames.append(df)

    if not frames:
        raise ValueError("No tradebook data found in any sheet")

    combined = pd.concat(frames, ignore_index=True)
    return combined


def parse_zerodha_tradebook(file_path: str, file_type: str) -> Tuple[List[Dict[str, Any]], int]:
    """
    Parse a Zerodha tradebook file (CSV or Excel).

    Returns:
        Tuple of (list of trade dicts, total_count)
        Each trade dict has: symbol, isin, trade_date, exchange, segment,
        trade_type, quantity, price, total_amount, trade_id, order_id
    """
    # Read data
    if 'csv' in file_type.lower() or file_path.endswith('.csv'):
        df = pd.read_csv(file_path)
        df.columns = [c.strip().lower() for c in df.columns]
    else:
        df = _read_tradebook_excel_all_sheets(file_path)

    trades: List[Dict[str, Any]] = []

    for _, row in df.iterrows():
        try:
            symbol = str(row.get('symbol', '')).strip()
            if not symbol:
                continue

            isin = str(row.get('isin', '')).strip() if pd.notna(row.get('isin')) else None
            trade_date_raw = row.get('trade_date', '')
            quantity = float(row.get('quantity', 0))
            price = float(row.get('price', 0))
            trade_type = str(row.get('trade_type', '')).strip().lower()
            segment = str(row.get('segment', 'EQ')).strip().upper() if pd.notna(row.get('segment')) else 'EQ'
            exchange = str(row.get('exchange', '')).strip() if pd.notna(row.get('exchange')) else ''
            trade_id = str(row.get('trade_id', '')).strip() if pd.notna(row.get('trade_id')) else None
            order_id = str(row.get('order_id', '')).strip() if pd.notna(row.get('order_id')) else None

            # Parse trade date
            if isinstance(trade_date_raw, datetime):
                trade_date = trade_date_raw
            elif isinstance(trade_date_raw, str):
                trade_date_raw = trade_date_raw.strip()
                for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%d/%m/%y', '%Y-%m-%dT%H:%M:%S'):
                    try:
                        trade_date = datetime.strptime(trade_date_raw, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    logger.warning(f"Could not parse trade date: {trade_date_raw}")
                    continue
            else:
                continue

            total_amount = round(quantity * price, 2)

            trades.append({
                'symbol': symbol,
                'isin': isin,
                'trade_date': trade_date,
                'exchange': exchange,
                'segment': segment,
                'trade_type': trade_type,  # 'buy' or 'sell'
                'quantity': quantity,
                'price': price,
                'total_amount': total_amount,
                'trade_id': trade_id,
                'order_id': order_id,
            })
        except Exception as e:
            logger.warning(f"Skipping tradebook row: {e}")
            continue

    logger.info(f"Parsed {len(trades)} trades from tradebook")

    # Consolidate trades: combine same symbol + same date + same trade_type
    trades = consolidate_trades(trades)
    logger.info(f"After consolidation: {len(trades)} trades")

    return trades, len(trades)


def _parse_groww_amount(val) -> float:
    """Parse a Groww amount value which may be a comma-separated string like '9,999' or '9,99,950'."""
    if pd.isna(val):
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    return float(str(val).replace(',', '').strip())


def is_groww_stock_tradebook(file_path: str) -> bool:
    """Check if an Excel file is a Groww stock order history."""
    try:
        df_raw = pd.read_excel(file_path, header=None, nrows=10, engine='openpyxl')
        for i in range(min(10, len(df_raw))):
            row_values = [str(v).strip().lower() for v in df_raw.iloc[i].values if pd.notna(v)]
            if 'stock name' in row_values and 'symbol' in row_values and 'order status' in row_values:
                return True
        return False
    except Exception:
        return False


def is_groww_mf_tradebook(file_path: str) -> bool:
    """Check if an Excel file is a Groww mutual fund order history."""
    try:
        xl = pd.ExcelFile(file_path, engine='openpyxl')
        for sheet_name in xl.sheet_names:
            df_raw = pd.read_excel(file_path, sheet_name=sheet_name, header=None, nrows=15, engine='openpyxl')
            for i in range(min(15, len(df_raw))):
                row_values = [str(v).strip().lower() for v in df_raw.iloc[i].values if pd.notna(v)]
                if 'scheme name' in row_values and 'transaction type' in row_values and 'nav' in row_values:
                    return True
        return False
    except Exception:
        return False


def is_groww_tradebook(file_path: str) -> bool:
    """Check if an Excel file is any type of Groww tradebook (stock or MF)."""
    return is_groww_stock_tradebook(file_path) or is_groww_mf_tradebook(file_path)


def _read_groww_stock_tradebook(file_path: str) -> pd.DataFrame:
    """Read a Groww stock order history Excel file, auto-detecting the header row."""
    df_raw = pd.read_excel(file_path, header=None, engine='openpyxl')

    header_row = None
    for i in range(min(20, len(df_raw))):
        row_values = [str(v).strip().lower() for v in df_raw.iloc[i].values if pd.notna(v)]
        if 'stock name' in row_values and 'symbol' in row_values:
            header_row = i
            break

    if header_row is None:
        raise ValueError("Could not find Groww stock tradebook header row")

    headers = []
    for val in df_raw.iloc[header_row].values:
        if pd.notna(val):
            headers.append(str(val).strip().lower())
        else:
            headers.append(f'_skip_{len(headers)}')

    df = df_raw.iloc[header_row + 1:].copy()
    df.columns = headers
    df = df[[c for c in df.columns if not c.startswith('_skip_')]]
    df = df.dropna(subset=['symbol'])
    df = df.reset_index(drop=True)
    return df


def _read_groww_mf_tradebook(file_path: str) -> pd.DataFrame:
    """Read a Groww MF order history Excel file, auto-detecting the header row."""
    xl = pd.ExcelFile(file_path, engine='openpyxl')
    frames = []

    for sheet_name in xl.sheet_names:
        df_raw = pd.read_excel(file_path, sheet_name=sheet_name, header=None, engine='openpyxl')

        header_row = None
        for i in range(min(20, len(df_raw))):
            row_values = [str(v).strip().lower() for v in df_raw.iloc[i].values if pd.notna(v)]
            if 'scheme name' in row_values and 'transaction type' in row_values:
                header_row = i
                break

        if header_row is None:
            continue

        headers = []
        for val in df_raw.iloc[header_row].values:
            if pd.notna(val):
                headers.append(str(val).strip().lower())
            else:
                headers.append(f'_skip_{len(headers)}')

        df = df_raw.iloc[header_row + 1:].copy()
        df.columns = headers
        df = df[[c for c in df.columns if not c.startswith('_skip_')]]
        df = df.dropna(subset=['scheme name'])
        df = df.reset_index(drop=True)
        frames.append(df)

    if not frames:
        raise ValueError("No MF tradebook data found in any sheet")

    return pd.concat(frames, ignore_index=True)


def parse_groww_tradebook(file_path: str, file_type: str) -> Tuple[List[Dict[str, Any]], int]:
    """
    Parse a Groww tradebook file (stock or mutual fund order history).

    Returns:
        Tuple of (list of trade dicts, total_count)
        Each trade dict has the same shape as Zerodha trades: symbol, isin, trade_date,
        exchange, segment, trade_type, quantity, price, total_amount, trade_id, order_id
    """
    is_stock = is_groww_stock_tradebook(file_path)
    is_mf = is_groww_mf_tradebook(file_path)

    trades: List[Dict[str, Any]] = []

    if is_stock:
        df = _read_groww_stock_tradebook(file_path)
        for _, row in df.iterrows():
            try:
                symbol = str(row.get('symbol', '')).strip()
                if not symbol:
                    continue

                order_status = str(row.get('order status', '')).strip().lower()
                if order_status != 'executed':
                    continue

                stock_name = str(row.get('stock name', '')).strip()
                isin = str(row.get('isin', '')).strip() if pd.notna(row.get('isin')) else None
                trade_type = str(row.get('type', '')).strip().lower()
                quantity = float(row.get('quantity', 0))
                # Groww 'value' = total trade value (quantity * price)
                total_value = _parse_groww_amount(row.get('value', 0))
                price = round(total_value / quantity, 4) if quantity else 0
                exchange = str(row.get('exchange', '')).strip() if pd.notna(row.get('exchange')) else ''
                order_id = str(row.get('exchange order id', '')).strip() if pd.notna(row.get('exchange order id')) else None

                # Parse execution date: "28-04-2025 09:15 AM"
                exec_date_raw = row.get('execution date and time', '')
                if isinstance(exec_date_raw, datetime):
                    trade_date = exec_date_raw
                elif isinstance(exec_date_raw, str):
                    exec_date_raw = exec_date_raw.strip()
                    for fmt in ('%d-%m-%Y %I:%M %p', '%d-%m-%Y %H:%M', '%d-%m-%Y', '%Y-%m-%d'):
                        try:
                            trade_date = datetime.strptime(exec_date_raw, fmt)
                            break
                        except ValueError:
                            continue
                    else:
                        logger.warning(f"Could not parse Groww execution date: {exec_date_raw}")
                        continue
                else:
                    continue

                trades.append({
                    'symbol': symbol,
                    'isin': isin,
                    'trade_date': trade_date,
                    'exchange': exchange,
                    'segment': 'EQ',
                    'trade_type': trade_type,
                    'quantity': quantity,
                    'price': price,
                    'total_amount': round(total_value, 2),
                    'trade_id': None,
                    'order_id': order_id,
                })
            except Exception as e:
                logger.warning(f"Skipping Groww stock tradebook row: {e}")
                continue

    if is_mf:
        df = _read_groww_mf_tradebook(file_path)
        for _, row in df.iterrows():
            try:
                scheme_name = str(row.get('scheme name', '')).strip()
                if not scheme_name:
                    continue

                txn_type_raw = str(row.get('transaction type', '')).strip().lower()
                if txn_type_raw in ('purchase', 'buy'):
                    trade_type = 'buy'
                elif txn_type_raw in ('redeem', 'redemption', 'sell'):
                    trade_type = 'sell'
                else:
                    trade_type = txn_type_raw

                units = _parse_groww_amount(row.get('units', 0))
                nav = _parse_groww_amount(row.get('nav', 0))
                amount = _parse_groww_amount(row.get('amount', 0))

                # Parse date: "05 Feb 2026"
                date_raw = row.get('date', '')
                if isinstance(date_raw, datetime):
                    trade_date = date_raw
                elif isinstance(date_raw, str):
                    date_raw = date_raw.strip()
                    for fmt in ('%d %b %Y', '%d-%m-%Y', '%Y-%m-%d', '%d/%m/%Y'):
                        try:
                            trade_date = datetime.strptime(date_raw, fmt)
                            break
                        except ValueError:
                            continue
                    else:
                        logger.warning(f"Could not parse Groww MF date: {date_raw}")
                        continue
                else:
                    continue

                trades.append({
                    'symbol': scheme_name,
                    'isin': None,
                    'trade_date': trade_date,
                    'exchange': '',
                    'segment': 'MF',
                    'trade_type': trade_type,
                    'quantity': units,
                    'price': nav,
                    'total_amount': round(amount, 2),
                    'trade_id': None,
                    'order_id': None,
                })
            except Exception as e:
                logger.warning(f"Skipping Groww MF tradebook row: {e}")
                continue

    logger.info(f"Parsed {len(trades)} trades from Groww tradebook")

    trades = consolidate_trades(trades)
    logger.info(f"After consolidation: {len(trades)} Groww trades")

    return trades, len(trades)


def consolidate_trades(trades: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Consolidate trades that share the same symbol, trade date, and trade type
    into a single trade with summed quantity and weighted average price.
    """
    from collections import defaultdict

    groups: Dict[tuple, List[Dict[str, Any]]] = defaultdict(list)
    for trade in trades:
        trade_date = trade['trade_date']
        date_key = trade_date.date() if isinstance(trade_date, datetime) else trade_date
        key = (trade['symbol'].upper(), date_key, trade['trade_type'])
        groups[key].append(trade)

    consolidated: List[Dict[str, Any]] = []
    for key, group in groups.items():
        if len(group) == 1:
            consolidated.append(group[0])
            continue

        total_qty = sum(t['quantity'] for t in group)
        total_amount = sum(t['total_amount'] for t in group)
        avg_price = round(total_amount / total_qty, 2) if total_qty else 0

        # Collect all trade_ids and order_ids
        trade_ids = [t['trade_id'] for t in group if t.get('trade_id')]
        order_ids = [t['order_id'] for t in group if t.get('order_id')]

        # Use the first trade as the base, update with consolidated values
        merged = dict(group[0])
        merged['quantity'] = total_qty
        merged['price'] = avg_price
        merged['total_amount'] = round(total_amount, 2)
        merged['trade_id'] = ','.join(trade_ids) if trade_ids else None
        merged['order_id'] = ','.join(order_ids) if order_ids else None

        consolidated.append(merged)

    # Sort by trade_date descending for consistent ordering
    consolidated.sort(key=lambda t: t['trade_date'], reverse=True)
    return consolidated
