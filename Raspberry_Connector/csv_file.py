from raspberry_connector import RaspberryConnector
import pandas as pd

# Inizializza il RaspberryConnector per accedere ai sensori
rc = RaspberryConnector(conf_path="conf.json", devices_path="devices.json")

# Recupera i dati dai sensori (grodan, PAR_meter, pH_meter, temp_sens, air_hum_sens)
series_index = rc.pH_meter.value.index  # Usa l'indice del pH_meter come riferimento temporale

# Recupera i dati dalle serie temporali dei sensori
series_ph = rc.pH_meter.value  # Valori del pH_meter
series_temp = rc.temp_sens.value  # Valori del sensore di temperatura
series_grodan = rc.grodan.value  # Valori del grodan
series_par = rc.PAR_meter.value  # Valori del PAR meter
series_air_hum = rc.air_hum_sens.value  # Valori del sensore di umidità dell'aria

# Crea un DataFrame con i valori raccolti, utilizzando l'indice temporale del pH_meter
df = pd.DataFrame({
    "pH_meter": series_ph,
    "temp_sens": series_temp,
    "grodan": series_grodan,
    "PAR_meter": series_par,
    "air_hum_sens": series_air_hum
}, index=series_index)

# Aggiungi una colonna chiamata 'measurement' con un valore costante (ad esempio, 'sensor_data')
df.insert(0, 'measurement', 'sensor_data')

# Riempimento dei campi mancanti
# Utilizza l'interpolazione lineare per i sensori con dati continui
df['temp_sens'].interpolate(method='linear', inplace=True)
df['grodan'].interpolate(method='linear', inplace=True)
df['air_hum_sens'].interpolate(method='linear', inplace=True)

# Riempie i valori mancanti con "forward fill" per garantire la continuità dei dati non lineari
df.fillna(method='ffill', inplace=True)

# Salva il DataFrame come file CSV
df.to_csv("sensor_data.csv", index=False)

print("File CSV creato: sensor_data.csv")
