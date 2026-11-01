# UPI Growth Analysis (April 2016 to September 2026)

## Business question
How fast has UPI grown in India, is growth slowing, and how has the average
transaction size changed?

## Data
- Source: NPCI, UPI Product Statistics (monthly), npci.org.in
- Coverage: April 2016 to September 2026 (126 months)
- Columns: banks live on UPI, volume (millions of transactions), value (Rs crore)
- Note from NPCI: data excludes transactions with debit and credit to the same
  account from August 2018 onward.
- Volume is zero for April to June 2016 because UPI had only just launched.

## What is in this repo
- `data_raw/` : the 11 Excel files downloaded from NPCI, one per financial year
- `data_clean/upi_monthly_clean.csv` : combined, cleaned monthly table
- `combine_upi.py` : script that combines and cleans the raw files
- Average ticket size (Rs) = value in crore x 10 / volume in million

## Status
In progress. Still to come: SQL growth analysis, seasonality, forecast,
Power BI dashboard and key findings.

## Key findings
To be added after the analysis is finished.
