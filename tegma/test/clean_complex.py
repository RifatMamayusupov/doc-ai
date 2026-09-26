import pandas as pd

file_path = 'complex_structure_test.xlsx'

try:
    # Read the file again, but skip the first 16 rows to get to the actual data table
    # Row 13 (index 12) has headers like "№№", "ОБОСНОВАНИЕ", etc.
    # But row 15 (index 14) has column numbers 1, 2, 3...
    # Let's try to use row 13 as the header row (skiprows=13)
    
    df = pd.read_excel(file_path, sheet_name='корабог', skiprows=13)
    
    # Rename columns for clarity based on visual inspection
    # The columns seem to be:
    # 0: №№
    # 1: ОБОСНОВАНИЕ
    # 2: НАИМЕНОВАНИЕ РАБОТ И РЕСУРСОВ
    # 3: ЕД.ИЗМ
    # 4: КОЛ-ВО / НА ЕДИНИЦУ
    # 5: ПО ПРОЕКТУ (Total Quantity?)
    # ... and others
    
    # Let's clean up the dataframe
    # 1. Drop rows where 'НАИМЕНОВАНИЕ РАБОТ И РЕСУРСОВ' is NaN
    df_clean = df.dropna(subset=['НАИМЕНОВАНИЕ РАБОТ И РЕСУРСОВ'])
    
    # 2. Select only relevant columns (first 6 columns seem most important for now)
    df_clean = df_clean.iloc[:, :6]
    
    # 3. Reset index
    df_clean = df_clean.reset_index(drop=True)
    
    print("Cleaned Data (First 20 rows):")
    print(df_clean.head(20).to_markdown(index=False))
    
    # Save to a new file
    output_file = 'cleaned_data.xlsx'
    df_clean.to_excel(output_file, index=False)
    print(f"\nSaved cleaned data to {output_file}")

except Exception as e:
    print(f"Error: {e}")
