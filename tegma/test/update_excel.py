import pandas as pd

file_path = 'test_data.xlsx'

try:
    # Read the Excel file
    df = pd.read_excel(file_path)
    
    # Update Vali's age
    # loc finds rows where the condition is true and selects the 'Age' column
    df.loc[df['Name'] == 'Vali', 'Age'] = 50
    
    # Save back to Excel
    df.to_excel(file_path, index=False)
    
    print("Successfully updated Vali's age to 50.")
    print("\nUpdated Data:")
    print(df.to_string(index=False))
    
except Exception as e:
    print(f"Error: {e}")
