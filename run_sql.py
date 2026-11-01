import os
import sqlite3
import sys

import pandas as pd

folder = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(folder, "data_clean", "upi_monthly_clean.csv")

con = sqlite3.connect(os.path.join(folder, "upi.db"))
pd.read_csv(csv_path).to_sql("upi_monthly", con, if_exists="replace", index=False)

sql_file = sys.argv[1]
with open(os.path.join(folder, sql_file), encoding="utf-8") as f:
    result = pd.read_sql_query(f.read(), con)

os.makedirs(os.path.join(folder, "outputs"), exist_ok=True)
name = os.path.splitext(os.path.basename(sql_file))[0]
result.to_csv(os.path.join(folder, "outputs", name + ".csv"), index=False)

pd.set_option("display.width", 200)
print(result.tail(14).to_string(index=False))
print("Rows:", len(result))
con.close()