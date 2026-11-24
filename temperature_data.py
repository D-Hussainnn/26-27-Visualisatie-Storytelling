"""Download and prepare the NASA and KNMI temperature datasets.

Run this file from the folder containing the notebook:
    python temperature_data.py
The generated CSV files are saved in the same folder.
"""
from io import StringIO
from pathlib import Path
import pandas as pd
import requests

FOLDER = Path(__file__).resolve().parent
NASA_URL = "https://data.giss.nasa.gov/gistemp/tabledata_v4/GLB.Ts+dSST.csv"
KNMI_URL = "https://www.daggegevens.knmi.nl/klimatologie/daggegevens"

def download_global_temperature():
    response = requests.get(NASA_URL, timeout=60)
    response.raise_for_status()

    # NASA's first line is a description; the second line contains column names.
    raw = pd.read_csv(StringIO(response.text), skiprows=1, na_values=["***"])
    year_col = "Year" if "Year" in raw.columns else raw.columns[0]
    annual_col = "J-D"
    if annual_col not in raw.columns:
        raise ValueError("De jaarlijkse kolom 'J-D' is niet gevonden in het NASA-bestand.")

    data = raw[[year_col, annual_col]].copy()
    data.columns = ["year", "temperature_anomaly_c"]
    data["year"] = pd.to_numeric(data["year"], errors="coerce")
    data["temperature_anomaly_c"] = pd.to_numeric(
        data["temperature_anomaly_c"], errors="coerce"
    )
    data = data.dropna()
    data = data[(data["year"] >= 1995) & (data["year"] <= 2019)]
    data["year"] = data["year"].astype(int)

    if data.empty:
        raise ValueError("NASA heeft geen temperatuurgegevens voor 1995–2019 teruggegeven.")

    output = FOLDER / "global_temperature_preprocessed.csv"
    data.to_csv(output, index=False)
    return data

def download_knmi_temperature():
    payload = {
        "start": "19950101",
        "end": "20191231",
        "vars": "TG",
        "stns": "260",  # KNMI station De Bilt
        "fmt": "csv",
    }
    response = requests.post(KNMI_URL, data=payload, timeout=120)
    response.raise_for_status()

    # KNMI CSV has explanatory lines beginning with '#'.
    data_lines = [
        line for line in response.text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not data_lines:
        raise ValueError("KNMI heeft geen daggegevens teruggegeven.")

    raw = pd.read_csv(
        StringIO("\n".join(data_lines)),
        header=None,
        names=["station", "date", "TG"],
        skipinitialspace=True
    )

    raw["date"] = pd.to_datetime(
        raw["date"].astype(str).str.strip(),
        format="%Y%m%d",
        errors="coerce"
    )
    raw["TG"] = pd.to_numeric(raw["TG"], errors="coerce")
    raw = raw.dropna(subset=["date", "TG"])

    # KNMI TG is given in tenths of a degree Celsius.
    raw = raw[raw["TG"] > -900].copy()
    raw["avg_temperature_c"] = raw["TG"] / 10
    raw["year"] = raw["date"].dt.year
    raw["month"] = raw["date"].dt.month

    output = raw[["date", "year", "month", "avg_temperature_c"]].copy()
    output.to_csv(FOLDER / "city_temperature_preprocessed.csv", index=False)
    return output

def prepare_temperature_data():
    global_temp = download_global_temperature()
    netherlands_temp = download_knmi_temperature()
    print("Temperatuurgegevens zijn opgeslagen als CSV-bestanden.")
    print("NASA:", len(global_temp), "jaargegevens")
    print("KNMI:", len(netherlands_temp), "daggegevens")
    return global_temp, netherlands_temp

if __name__ == "__main__":
    prepare_temperature_data()
