import pandas as pd

def determine_status(row, tolerance=0.01):
    """Determine the match status of a single invoice row."""
    if row['amount_inv'] == 0:
        return 'Missing in Invoices'
    if row['amount_brk'] == 0:
        return 'Missing in Breakdowns'
    if row['abs_diff'] <= tolerance:
        return 'Matched'
    return 'Mismatch'

def determine_cause(row):
    """Heuristic analysis to guess the root cause of a mismatch."""
    if row['status'] == 'Matched':
        return 'None'
    if row['status'].startswith('Missing'):
        return 'Missing Document'
    
    # Check for systematic errors (multiples of 5.00)
    # Using round() to handle floating point noise
    if row['abs_diff'] < 100 and (round(row['abs_diff'], 2) % 5 == 0):
        return 'Systematic Error (Multiple of 5)'
    
    if row['abs_diff'] > 100:
        return 'Major Discrepancy'
    
    return 'Minor Discrepancy'

def reconcile_invoices(invoices_df, breakdowns_df):
    """
    Level 1: Invoice-Level Reconciliation
    Aggregates data by invoice_id and compares totals.
    """
    # Group by ID
    inv_grouped = invoices_df.groupby('invoice_id')['amount'].sum().reset_index()
    brk_grouped = breakdowns_df.groupby('invoice_id')['amount'].sum().reset_index()
    
    # Merge
    merged = pd.merge(inv_grouped, brk_grouped, on='invoice_id', how='outer', suffixes=('_inv', '_brk'))
    merged.fillna(0, inplace=True)
    
    # Calculate Differences
    merged['difference'] = merged['amount_inv'] - merged['amount_brk']
    merged['abs_diff'] = merged['difference'].abs()
    
    # Apply Logic
    merged['status'] = merged.apply(determine_status, axis=1)
    merged['potential_cause'] = merged.apply(determine_cause, axis=1)
    
    return merged

def reconcile_line_items(invoices_df, breakdowns_df, invoice_id):
    """
    Level 2: Line-Item Reconciliation for a specific Invoice
    Aggregates by Description to find specific missing items.
    """
    # Filter for the specific invoice
    inv_subset = invoices_df[invoices_df['invoice_id'] == invoice_id].copy()
    brk_subset = breakdowns_df[breakdowns_df['invoice_id'] == invoice_id].copy()
    
    # Normalize descriptions (strip whitespace)
    inv_subset['description'] = inv_subset['description'].str.strip()
    brk_subset['description'] = brk_subset['description'].str.strip()
    
    # Group by Description
    inv_grouped = inv_subset.groupby('description')['amount'].sum().reset_index()
    brk_grouped = brk_subset.groupby('description')['amount'].sum().reset_index()
    
    # Merge on Description
    merged = pd.merge(inv_grouped, brk_grouped, on='description', how='outer', suffixes=('_extracted', '_source'))
    merged.fillna(0, inplace=True)
    
    # Calculate Variance
    merged['variance'] = merged['amount_extracted'] - merged['amount_source']
    
    # Determine Status
    merged['status'] = merged['variance'].apply(lambda x: '✅ Match' if abs(x) < 0.01 else '❌ Mismatch')
    
    # Return sorted (mismatches at the top)
    return merged.sort_values(by='status', ascending=False)