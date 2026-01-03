import os
import io
import csv
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Customer Analytics Dashboard", layout="wide")
st.title("Customer Analytics Dashboard")

@st.cache_data(show_spinner=False)
def read_wrapped_csv(csv_path: str) -> pd.DataFrame:
    rows = []
    with open(csv_path, "r", encoding="utf-8", errors="replace", newline="") as f:
        outer_reader = csv.reader(f)
        for outer_row in outer_reader:
            if not outer_row:
                continue

            big = outer_row[0]

            # Parse lagi isi string-nya sebagai CSV beneran
            inner = next(csv.reader(io.StringIO(big)))
            rows.append(inner)

    if not rows:
        raise ValueError("File CSV kosong.")

    header = [h.strip() for h in rows[0]]
    data = rows[1:]

    df = pd.DataFrame(data, columns=header)
    df.columns = [c.strip() for c in df.columns]
    return df

@st.cache_data(show_spinner=False)
def load_data(csv_path: str) -> pd.DataFrame:
    if not os.path.exists(csv_path):
        raise FileNotFoundError(
            f"File '{csv_path}' tidak ditemukan. Pastikan customers.csv satu folder dengan streamlit_app.py"
        )

    # Coba baca normal dulu
    try:
        df_try = pd.read_csv(csv_path)
        df_try.columns = [c.strip() for c in df_try.columns]

        # Kalau cuma 1 kolom, berarti file kamu tipe “CSV dibungkus”
        if df_try.shape[1] == 1:
            df = read_wrapped_csv(csv_path)
        else:
            df = df_try
    except Exception:
        df = read_wrapped_csv(csv_path)

    # Normalisasi nama kolom (anti beda-beda penulisan)
    df.columns = [c.strip().replace("\ufeff", "") for c in df.columns]

    rename_map = {}
    lower_map = {c.lower(): c for c in df.columns}

    def rename_if_exists(wanted: str):
        key = wanted.lower()
        if key in lower_map and wanted not in df.columns:
            rename_map[lower_map[key]] = wanted

    rename_if_exists("Department")
    rename_if_exists("Gender")
    rename_if_exists("Age")
    rename_if_exists("AnnualSalary")

    if rename_map:
        df = df.rename(columns=rename_map)

    required_cols = ["Department", "Gender", "Age", "AnnualSalary"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(
            "Kolom wajib tidak ada di customers.csv: "
            + ", ".join(missing)
            + ". Ini biasanya karena header CSV tidak kebaca benar."
        )

    # Bersihin value
    df["Department"] = df["Department"].astype(str).str.strip()
    df["Gender"] = df["Gender"].astype(str).str.strip()

    df["Age"] = pd.to_numeric(df["Age"], errors="coerce")
    df["AnnualSalary"] = pd.to_numeric(df["AnnualSalary"], errors="coerce")

    df = df.dropna(subset=["Department", "Gender", "Age", "AnnualSalary"]).copy()
    df = df[(df["Age"] >= 0) & (df["AnnualSalary"] >= 0)].copy()

    return df

try:
    df = load_data("customers.csv")
except Exception as e:
    st.error(str(e))
    st.stop()

st.sidebar.header("Filter Data")

dept_options = sorted(df["Department"].dropna().unique().tolist())
gender_options = sorted(df["Gender"].dropna().unique().tolist())

departments = st.sidebar.multiselect(
    "Pilih Departments",
    options=dept_options,
    default=dept_options
)

genders = st.sidebar.multiselect(
    "Pilih Gender",
    options=gender_options,
    default=gender_options
)

st.sidebar.header("Filter Rentang Umur")
min_usia = int(df["Age"].min())
max_usia = int(df["Age"].max())

usia_range = st.sidebar.slider(
    "Usia",
    min_value=min_usia,
    max_value=max_usia,
    value=(min_usia, max_usia)
)

df_filtered = df[
    (df["Department"].isin(departments)) &
    (df["Gender"].isin(genders)) &
    (df["Age"].between(usia_range[0], usia_range[1]))
].copy()

st.subheader("Data Tabel")
st.dataframe(df_filtered, use_container_width=True)

st.subheader("Visualisasi Statistik")

if df_filtered.empty:
    st.warning("Data kosong. Ubah filter supaya ada data yang tampil.")
    st.stop()

col1, col2 = st.columns(2)

with col1:
    st.subheader("Distribusi Gender")
    pie_gender = px.pie(df_filtered, names="Gender")
    st.plotly_chart(pie_gender, use_container_width=True)

with col2:
    st.subheader("Gaji Rata-rata per Department")
    salary_dept = (
        df_filtered
        .groupby("Department", as_index=False)["AnnualSalary"]
        .mean()
        .sort_values("AnnualSalary", ascending=False)
    )
    bar_salary = px.bar(
        salary_dept,
        x="Department",
        y="AnnualSalary",
        color="Department"
    )
    st.plotly_chart(bar_salary, use_container_width=True)

st.subheader("Rata-rata Gaji Berdasarkan Usia")
salary_age = (
    df_filtered
    .groupby("Age", as_index=False)["AnnualSalary"]
    .mean()
    .sort_values("Age")
)

line_age = px.line(
    salary_age,
    x="Age",
    y="AnnualSalary",
    markers=True
)
st.plotly_chart(line_age, use_container_width=True)

st.subheader("Tambahkan Chart Lainnya Versi Anda Sendiri!")
st.write("Kamu bisa tambah chart lain dari kolom lain, misalnya Ethnicity, BusinessUnit, Country, City.")
