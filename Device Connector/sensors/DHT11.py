from ..modules.data_processor import *
import matplotlib.pyplot as plt


class DHT11:

    def __init__(self, path):
        self.path = path
        self.df = self.read_data()

    def import_data(self):
        data = pd.read_csv(self.path)
        return data

    def read_data(self):
        data = self.import_data()
        dataframe = dht11_sensor(data)
        return dataframe

    def plot_dataframe(self):
        plt.figure(figsize=(10, 6))
        plt.plot(self.df.index, self.df['humidity'], color='blue', linestyle='-', label='Humidity')
        plt.plot(self.df.index, self.df['temperature'], color='red', linestyle='-', label='Temperature')
        plt.title('Humidity and temperature trends')
        plt.xlabel('Date')
        plt.ylabel('Value')
        plt.xticks(rotation=45)
        plt.grid(True)
        plt.legend()
        plt.tight_layout()
        plt.show()

    def change_granularity(self, hours):
        df = correct_non_numeric_values(self.df)
        self.df = resample_dataframe(df, hours)


if __name__ == '__main__':
    path = '../data/dataset/GreenhouseClimate.csv'
    sensor = DHT11(path)
    sensor.change_granularity(1)
    sensor.plot_dataframe()
    print(sensor.df)
