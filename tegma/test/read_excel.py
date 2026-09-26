import pandas as pd

try:
    df = pd.read_excel('test_data.xlsx')
    print(df.to_markdown(index=False))
except Exception as e:
    # Fallback if tabulate is not installed (to_markdown requires tabulate)
    print(df.to_string(index=False))
