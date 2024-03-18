import pandas as pd
import warnings
warnings.filterwarnings("ignore")


def correct_non_numeric_values(df):
    mask = df.apply(lambda s: pd.to_numeric(s, errors='coerce').notnull().all())
    if not mask.any():
        # Convert column values to numbers
        for column in df.columns:
            if df[column].dtype == 'object':
                df[column] = pd.to_numeric(df[column], errors='coerce')  # errors='coerce' will convert non-numeric values to NaN
    if check_NaN_values(df):
        # replace NaN with values taken from interpolation
        df = fill_dataset(df)
    return df


def check_NaN_values(df):
    nan_count = df.isnull().sum().sum()  # Number of NaN values for each column
    nans = nan_count > 0  # Returns True if there are any NaN values, False otherwise
    return nans


def fill_dataset(df):
    df = df.interpolate(method='linear')
    return df


def resample_dataframe(df, minutes):
    df = df.resample(f"{minutes}min").mean().interpolate(method='cubic')
    return df


def dht11_sensor(df):
    start_date = pd.Timestamp.now().replace(year=2023, month=2, day=1, hour=0, minute=00, second=0, microsecond=0)
    num_rows = len(df)
    index = pd.date_range(start=start_date, periods=num_rows, freq='5T')
    df.index = index
    df.rename(columns={'Rhair': 'humidity', 'Tair': 'temperature'}, inplace=True)
    df = df[['humidity', 'temperature']]
    return df


if __name__ == '__main__':

    path = '../data/dataset/GreenhouseClimate.csv'
    data = pd.read_csv(path)
    df = dht11_sensor(data)
    df = correct_non_numeric_values(df)
    df = resample_dataframe(df, 6)
    print(df.head())

