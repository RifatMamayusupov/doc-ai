import pandas as pd
import matplotlib.pyplot as plt

file_path = 'cleaned_data.xlsx'

try:
    # Read the cleaned data
    df = pd.read_excel(file_path)
    
    # The column for units is 'ЕД.ИЗМ' (column index 3)
    # Let's count the occurrences of each unit
    unit_counts = df['ЕД.ИЗМ'].value_counts()
    
    # Filter out small values to make the chart readable
    # Keep top 6, group others as 'Other'
    top_units = unit_counts.head(6)
    if len(unit_counts) > 6:
        others_count = unit_counts.iloc[6:].sum()
        top_units['Other'] = others_count
    
    # Create Pie Chart
    plt.figure(figsize=(10, 8))
    plt.pie(top_units, labels=top_units.index, autopct='%1.1f%%', startangle=140, colors=plt.cm.Paired.colors)
    plt.title('Distribution of Measurement Units (ЕД.ИЗМ)')
    plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    
    # Save the chart
    output_file = 'pie_chart.png'
    plt.savefig(output_file)
    print(f"Pie chart saved to {output_file}")
    
    # Print the data used for the chart
    print("\nData used for Pie Chart:")
    print(top_units.to_string())

except Exception as e:
    print(f"Error: {e}")
