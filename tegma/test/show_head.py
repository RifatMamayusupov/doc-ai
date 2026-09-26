import pandas as pd

file_path = 'complex_structure_test.xlsx'

try:
    # Load the first sheet
    df = pd.read_excel(file_path, sheet_name='корабог', header=None)
    
    # Get first 20 rows
    first_20 = df.head(20)
    
    # Print in a readable format
    # Using fillna('') to make it cleaner
    print(first_20.fillna('').to_markdown(index=True))

except Exception as e:
    print(f"Error: {e}")
