# Chicago Food Inspections dashboard

An interactive Streamlit dashboard built on the cleaned City of Chicago Food
Inspections data (311,802 inspections, January 2010 – October 2026).

## What's in it

- **Filters (sidebar):** years, facility type, risk level, inspection type, and a
  switch to include visits where no inspection took place.
- **Headline numbers:** inspections, pass rate, fail rate, average violations.
- **Tabs:** Trends · Business types · Risk levels · Map · Zip codes · Data
  (with a CSV download of the filtered records).

## Run it on your computer

1. Install Python 3.10 or newer.
2. Open a terminal in this folder and run:

   ```
   pip install -r requirements.txt
   streamlit run app.py
   ```

3. Your browser opens the dashboard at http://localhost:8501.

## Put it online (free)

1. Create a GitHub repository and upload everything in this folder,
   including `inspections.parquet` (about 4 MB) and the `.streamlit` folder.
2. Go to https://share.streamlit.io, sign in with GitHub, choose
   **Create app**, pick the repository, and set the main file to `app.py`.

## Notes on the numbers

- Pass and fail rates count only real inspections (Pass, Pass w/ Conditions, Fail)
  unless the sidebar switch is turned on.
- Average violations leave out inspections whose violation details weren't
  recorded (NOT ASSESSED / UNKNOWN).
- 2026 is a partial year, and "Other" groups 500+ small facility types.
