# pip install minio
# pip install pandas
# pip install numpy

from minio import Minio
from minio.error import S3Error
from io import StringIO, BytesIO
import pandas as pd
from geopy.geocoders import Nominatim

CAMADA_SILVER = 'silver'
CAMADA_GOLD = 'gold'

minioclient = Minio('localhost:9000',
    access_key='minioadmin',
    secret_key='minioadmin',
    secure=False)

def are_locations_equal(location1, location2):
    return location1 == location2


arquivos_rotas_gpx_csv = [arquivo_gpx for arquivo_gpx in minioclient.list_objects(CAMADA_SILVER) if arquivo_gpx.object_name.endswith(".csv")]
for arquivo_rotas_gpx_csv in arquivos_rotas_gpx_csv:    
    obj_rota_csv = minioclient.get_object(CAMADA_SILVER, arquivo_rotas_gpx_csv.object_name)        
    csv_decod = obj_rota_csv.data.decode('utf-8')  # Convertendo bytes para string    
    arquivo_csv = StringIO(csv_decod)
    df = pd.read_csv(arquivo_csv,sep=';')

    batch_size = 1000
    batch_list = [df[i:i+batch_size].copy() for i in range(0, len(df), batch_size)]
    geolocator = Nominatim(user_agent="geoapiExercises", timeout=10)
    processed_batches = []  # Inicialize a lista de lotes processados
    last_locations = {}

    for batch_df in batch_list:
        # Obtenha a primeira e a última linha do lote
        first_row = batch_df.iloc[0]
        last_row = batch_df.iloc[-1]

        first_location_str = f"{first_row['latitude']},{first_row['longitude']}"
        last_location_str = f"{last_row['latitude']},{last_row['longitude']}"

        # Verifique se a primeira e a última localização são iguais à última localização verificada
        if are_locations_equal(first_location_str, last_location_str) and are_locations_equal(first_location_str, last_location):
            # Se forem iguais, não é necessário consultar o serviço novamente
            location = last_location
        else:
            # Se forem diferentes, consulte o serviço de geocodificação para a última localização
            location = geolocator.reverse(last_location_str)
            last_location = location

        address = location.raw['address']
        cidade = address.get('county') or address.get('city') or address.get('suburb')
        estado = address.get('ISO3166-2-lvl4')#.split('-')[1]
        pais = address.get('country_code')
        pais = pais.upper()
        
        df.loc[:, 'cidade'] = cidade
        df.loc[:, 'estado'] = estado
        df.loc[:, 'pais'] = pais

    # Converta o DataFrame enriquecido de volta para CSV
    enriched_csv = df.to_csv(index=False, sep=';')
    enriched_csv_bytes = enriched_csv.encode('utf-8')

    # Crie um buffer de bytes
    enriched_csv_buffer = BytesIO(enriched_csv_bytes)

    minioclient.put_object(
        CAMADA_GOLD,
        arquivo_rotas_gpx_csv.object_name,  # Use o mesmo nome de arquivo
        data=enriched_csv_buffer,
        length=len(enriched_csv_bytes),
        content_type='application/csv')
