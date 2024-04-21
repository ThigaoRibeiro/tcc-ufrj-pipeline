##############################################
### IMPORTAÇÃO DAS BIBLIOTECAS NECESSÁRIAS ###
##############################################
# pip install minio
# pip install pandas
# pip install numpy
# pip install geopy
##############################################
from minio import Minio
from minio.error import S3Error
from io import StringIO, BytesIO
import pandas as pd
from geopy.geocoders import Nominatim
from datetime import datetime
# import time
# start_time = time.time()


####################################
### DEFINIÇÃO DA CAMADA NO MINIO ###
####################################
CAMADA_SILVER = 'silver'
CAMADA_GOLD = 'gold'


##############################################
### CRIANDO UMA INSTÂNCIA DO CLIENTE MINIO ###
##############################################
minioclient = Minio('localhost:9000',
    access_key='minioadmin',
    secret_key='minioadmin',
    secure=False)


########################################################
### CRIAÇÃO DA FUNÇÃO PARA COMPARAÇÃO DE LOCALIZAÇÃO ###
########################################################
def are_locations_equal(location1, location2):
    return location1 == location2


#############################################################################
### LISTANDO ARQUIVOS DO BUCKET SILVER E OS TRANSFORMANDO EM UM DATAFRAME ###
#############################################################################
arquivos_rotas_gpx_csv = [arquivo_gpx for arquivo_gpx in minioclient.list_objects(CAMADA_SILVER) if arquivo_gpx.object_name.endswith(".csv")]
for arquivo_rotas_gpx_csv in arquivos_rotas_gpx_csv:    
    obj_rota_csv = minioclient.get_object(CAMADA_SILVER, arquivo_rotas_gpx_csv.object_name)        
    csv_decod = obj_rota_csv.data.decode('utf-8')  # Convertendo bytes para string    
    arquivo_csv = StringIO(csv_decod)
    df = pd.read_csv(arquivo_csv,sep=';')


    #######################################################################################################################################
    ### PROCESSANDO O DATAFRAME EM LOTES E CONSUMINDO DADOS DA BIBLIOTECA GEOPY PARA VERIFICAR A LOCALIDADE DE ONDE AS ROTAS OCORRERAM ###
    #######################################################################################################################################
    batch_size = 1000
    batch_list = [df[i:i+batch_size].copy() for i in range(0, len(df), batch_size)]
    geolocator = Nominatim(user_agent="thiago_tcc", timeout=10)
    processed_batches = []  # Inicialize a lista de lotes processados
    last_location = {}

    
    ################################################################################################
    ### VERIFICANDO SE A LOCALIDADE (CIDADE-ESTADO) DO INICIO DA ROTA É O MESMO DO FINAL DA ROTA ###
    ################################################################################################
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

    
        ######################################################################################################################
        ### ADICIONANDO AS INFORMAÇÕES OBTIDAS (CIDADE - ESTADO - PAÍS) COM LAT-LONG INICIAL E LAT-LONG FINAL NO DATAFRAME ###
        ######################################################################################################################
        address = location.raw['address']
        cidade = address.get('county') or address.get('city') or address.get('suburb')
        estado = address.get('ISO3166-2-lvl4')#.split('-')[1]
        pais = address.get('country_code')
        pais = pais.upper()
        
        df.loc[:, 'cidade'] = cidade
        df.loc[:, 'estado'] = estado
        df.loc[:, 'pais'] = pais

        data_carga_banco = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        df['data_carga_banco'] = data_carga_banco


    ##########################################################################
    ### CONVERTENDO O DATAFRAME EM CSV PARA POSTERIOR CARGA NO BUCKET GOLD ### 
    ##########################################################################
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
    
    minioclient.remove_object(CAMADA_SILVER, arquivo_rotas_gpx_csv.object_name) #--> Removendo o arquivo do bucket


###########################################################
### CALCULANDO O TEMPO DE EXECUÇÃO DO SCRIPT (OPCIONAL) ###
###########################################################
# end_time = time.time()
# execution_time = end_time - start_time
# 
# hours, remainder = divmod(execution_time, 3600)
# minutes, remainder = divmod(remainder, 60)
# seconds, milliseconds = divmod(remainder, 1)
# 
# print(f"Tempo de execução: {int(hours)} horas, {int(minutes)} minutos, {int(seconds)} segundos e {int(milliseconds * 1000)} milissegundos")