from ryanair import Ryanair
from datetime import *
import os, sys, pandas as pd, smtplib, ssl, numpy as np, math

try:
    origem     = sys.argv[1].upper()
    passengers = sys.argv[2]
except:
    print("\nINFORME origem do vôo e quantidade de passageiros\n")
    print("\npython travelcheap.py porto 2\n")
    exit(0)

email = os.environ.get('travelcheap_email')
password = os.environ.get('travelcheap_password')

if email is None or password is None:
    print("\nINFORME o email e senha, utiliznado as variaveis de ambiente, travelcheap_email e travelcheap_password.\n")
    exit(1)

cidades = {"PORTO" : "OPO", "LISBOA" : "LIS"}

ryanair = Ryanair("EUR")

arrive = pd.date_range(start=datetime(2023,1,1), end=datetime(2023,1,1) + pd.offsets.Day(60), freq="W-THU")
back   = pd.date_range(start=arrive[0], end=arrive[0] + pd.offsets.Day(60), freq="W-SUN")

flights = pd.DataFrame()

for index in range(len(arrive)):
    go        = pd.DataFrame(ryanair.get_flights(cidades[f'{origem}'], arrive[index].date(), (arrive[index] + timedelta(days=1)).date()))
    if len(go.index) > 0:
        cheap_go  = go[go['price'] < 30].copy()
        destinations = list(cheap_go['destination'])
        for destination in destinations:
            returns = pd.DataFrame(ryanair.get_flights(destination, back[index].date(), (back[index] + timedelta(days=1)).date()))
            if len(returns.index) > 0:
                cheap_returns = returns[(returns['price'] < 30)].copy()
                if len(cheap_returns.index) > 0:
                    cheap_returns.columns = [column + "_return" for column in cheap_returns.columns]
                    full_trip = cheap_go.merge(cheap_returns, left_on=['origin', 'destination'], right_on=['destination_return', 'origin_return'], how="left")
                    flights = pd.concat([flights, full_trip[full_trip['destination_return'].notnull()]])

flights = flights[[column for column in flights.columns if column not in ['origin', 'origin_return', 'destination', 'destination_return', 'originFull_return', 'destinationFull_return']]]

flights['preco'] = (int(passengers) * (flights['price'] + flights['price_return'])).round(2)

flights = flights[flights['preco'] <= 80].copy()

flights = flights.rename(columns={"originFull": "origem", "destinationFull": "destino", "departureTime": "ida", "departureTime_return": "volta"})

flights['num_dias']     = (flights['volta'] - flights['ida']) / np.timedelta64(1, 'D')
flights['num_dias']     = flights['num_dias'].apply(lambda row: int(math.ceil(row)))
flights['ida']          = flights['ida'].apply(lambda row: row.strftime("%d/%m/%Y %H:%M:%S"))
flights['volta']        = flights['volta'].apply(lambda row: row.strftime("%d/%m/%Y %H:%M:%S"))
flights['origem']       = flights['origem'].apply(lambda row: row.upper())
flights['destino']      = flights['destino'].apply(lambda row: row.upper())
flights['pais_destino'] = flights['destino'].apply(lambda row: row.split(",")[1].strip(" ").upper())

flights = flights[['ida', 'origem', 'volta', 'destino', 'preco', 'pais_destino', 'num_dias']].copy()

flights.sort_values(by=['preco'], inplace=True)

subject   = f"TRAVELCHEAP ALERTA [{str(datetime.now().date().strftime('%d/%m/%Y'))}]"
sender    = email
receivers = [email]

email_flights = []
delimiter     = "\n"

countries    = list(flights['pais_destino'].unique())

for country in countries:
    tmp_flights = flights[flights['pais_destino'] == country]
    email_flights.append(f"*********************************** {country} *****************************************")
    email_flights.append("\n")
    for index, row in tmp_flights.iterrows():
        email_flights.append(f"IDA ----------- {row['ida']}")
        email_flights.append(f"VOLTA ------ {row['volta']}, ({row['num_dias']} dias)")
        email_flights.append(f"DESTINO -- {row['destino']}")
        email_flights.append(f"PRECO ----- {row['preco']}")
        email_flights.append(f"\n")

final_flights = delimiter.join(email_flights)

for receiver in receivers:
    message  = f"""Subject: {subject}

Fala {receiver.split("@")[0]}, 

Vamo viajar barato?
    
Seguem as 9vidades quentissimas saindo de {origem}!

{final_flights}

Corre! https://www.ryanair.com/
    """

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context()) as server:
        server.login(email, password)
        server.sendmail(sender, receiver, message)