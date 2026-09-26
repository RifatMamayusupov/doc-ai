import pandas as pd

file_path = 'complex_structure_test.xlsx'

try:
    # Load the Excel file
    xls = pd.ExcelFile(file_path)
    
    print(f"File: {file_path}")
    print(f"Sheets found: {xls.sheet_names}")
    print("-" * 30)
    
    for sheet_name in xls.sheet_names:
        print(f"\nAnalyzing Sheet: '{sheet_name}'")
        df = pd.read_excel(xls, sheet_name=sheet_name)
        
        print(f"Dimensions: {df.shape[0]} rows, {df.shape[1]} columns")
        print("\nColumns:")
        for col in df.columns:
            print(f" - {col} ({df[col].dtype})")
            
        print("\nFirst 5 rows:")
        print(df.head().to_string())
        
        print("\nBasic Statistics:")
        print(df.describe().to_string())
        print("-" * 30)

except Exception as e:
    print(f"Error analyzing file: {e}")
