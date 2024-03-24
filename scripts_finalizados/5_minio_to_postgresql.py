##############################################
### IMPORTAÇÃO DAS BIBLIOTECAS NECESSÁRIAS ###
##############################################
# pip install minio
# pip install psycopg2-binary
# pip install scipy
##############################################
import psycopg2
from minio import Minio
import io
from io import StringIO, BytesIO
import pandas as pd
import requests
from scipy.spatial.distance import euclidean, cityblock, minkowski
from datetime import datetime

from dotenv import dotenv_values
config = dotenv_values(".env")
# import time
# start_time = time.time()


# #############################
# ### VARIÁVEIS DE AMBIENTE ###
# #############################
# HOST_MINIO = config.get("HOST_MINIO")
# ACCESS_KEY = config.get("ACCESS_KEY")
# SECRET_KEY = config.get("SECRET_KEY")
# HOST_POSTGRES = config.get("HOST_POSTGRES")
# DATABASE = config.get("DATABASE")
# USER = config.get("USER")
# PASSWORD =  config.get("PASSWORD")
# CREDENTIAL = config.get("TOKEN_API")


####################################
### DEFINIÇÃO DA CAMADA NO MINIO ###
####################################
CAMADA_GOLD = 'gold'
CAMADA_FILES_IN_TABLE = 'files-in-table'
DISTANCIAS = 'distancias'


##############################################
### CRIANDO UMA INSTÂNCIA DO CLIENTE MINIO ###
##############################################
minioclient = Minio('localhost:9000',
    access_key='minioadmin',
    secret_key='minioadmin',
    secure=False)


#############################################
### ACESSANDO O BANCO DE DADOS POSTGRESQL ###
#############################################
db_config = {
'host': 'localhost',
'database': 'postgres',
'user': 'postgres',
'password': 'postgres',
}


#############################################################################
### CRIAÇÃO DAS FUNÇÕES DE DISTANCIAS: EUCLIDIANA - MANHATTAN E MINKOWSKI ###
#############################################################################
def calc_dist_euclidiana(row):
    coord1 = (float(row['lon1']), float(row['lat1']))
    coord2 = (float(row['lon2']), float(row['lat2']))
    return euclidean(coord1, coord2) * 1000

def calc_dist_manhattan(row):
    coord1 = (float(row['lon1']), float(row['lat1']))
    coord2 = (float(row['lon2']), float(row['lat2']))
    return cityblock(coord1, coord2)*1000

def calc_dist_minkowski(row, p=3):
    coord1 = (float(row['lon1']), float(row['lat1']))
    coord2 = (float(row['lon2']), float(row['lat2']))
    return minkowski(coord1, coord2, p)*1000


##########################################################
### TOKEN DA API PARA CALCULO DE DESEMPENHO ENERGÉTICO ###
##########################################################
token_api = '5b3ce3597851110001cf624838eb860780704eca99c41867a83c9f6b'


#################################################################
### COMANDO PARA INSERT NA TABELA [tb_distancias_percorridas_api]
#################################################################
arquivos_rotas_gpx_csv = [arquivo_gpx for arquivo_gpx in minioclient.list_objects(CAMADA_GOLD) if arquivo_gpx.object_name.endswith(".csv")] #--> Listando todos os arquivos da camada bronze do datalake com extensão .csv
for arquivo_rotas_gpx_csv in arquivos_rotas_gpx_csv: #--> Iterando sobre a lista encontrada
    try:    
        obj_rota_csv = minioclient.get_object(CAMADA_GOLD, arquivo_rotas_gpx_csv.object_name) #--> Obtendo o nome do arquivo de dentro da camada bronze
        csv_decod = obj_rota_csv.data.decode('utf-8') #--> Decodificando o arquivo encontrado para utf-8 - Essa conversão transforma os dados obtidos do arquivo no bucket em bytes
        arquivo_csv = StringIO(csv_decod) #--> Convertendo os bytes em string
        df = pd.read_csv(arquivo_csv, sep=';') #--> Convertendo string para pandas dataframe        
        id_rota = df.loc[df.index[0], 'id_rota']
        nome_usuario = df.loc[df.index[0], 'nome_usuario']
        data_inicio_rota = df.loc[df.index[0], 'data']
        data_fim_rota = df.loc[df.index[-1], 'data']
        inicio_rota = df.loc[df.index[0], 'hora']
        fim_rota = df.loc[df.index[-1], 'hora']
        latitude_inicial = df.loc[df.index[0], 'latitude']
        longitude_inicial = df.loc[df.index[0], 'longitude']
        latitude_final = df.loc[df.index[-1], 'latitude']
        longitude_final = df.loc[df.index[-1], 'longitude']
        cidade = df.loc[df.index[0], 'cidade']
        estado = df.loc[df.index[0], 'estado']
        pais = df.loc[df.index[0], 'pais']
        id_unico = f'{id_rota}__{data_inicio_rota}__{inicio_rota}__{nome_usuario}'
        data_carga_banco = df.loc[df.index[0], 'data_carga_banco']
        longitude_inicial_float = float(longitude_inicial)
        latitude_inicial_float = float(latitude_inicial)    
        longitude_final_float = float(longitude_final)
        latitude_final_float = float(latitude_final)    
        #body = {"coordinates":[[8.681495,49.41461],[8.687872,49.420318]],"radiuses":"-1"}
        body = {"coordinates": [[longitude_inicial_float, latitude_inicial_float],[longitude_final_float, latitude_final_float]],"radiuses": "-1"}

        headers = {
            'Accept': 'application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8',
            'Authorization': token_api,
            'Content-Type': 'application/json; charset=utf-8'
        }
    
        call = requests.post('https://api.openrouteservice.org/v2/directions/driving-car', json=body, headers=headers)
        response = eval(call.text)
        duration = response['routes'][0]['summary']['duration']
        distance = response['routes'][0]['summary']['distance']
        distancia_real = distance / 1000

        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        insert = f'''
            insert into tb_distancias_percorridas_api (id_unico,nome_usuario,data_inicio_rota,data_fim_rota,inicio_rota,fim_rota,latitude_inicial,longitude_inicial,latitude_final,longitude_final,cidade,estado,pais,distancia_real_km_api,data_carga_banco)
            values (
                '{id_unico}',
                '{nome_usuario}',
                '{data_inicio_rota}',
                '{data_fim_rota}',
                '{inicio_rota}',
                '{fim_rota}',
                '{latitude_inicial}',
                '{longitude_inicial}',
                '{latitude_final}',
                '{longitude_final}',
                '{cidade}',
                '{estado}',
                '{pais}',              
                '{distancia_real}',
                '{data_carga_banco}'
                )'''
        cursor.execute(insert)
        conn.commit()
        conn.close()
    except Exception as e:        
        print(f"Erro na consulta da API: {str(e)} no id {id_unico}")
        continue


################################################################
### COMANDO SQL PARA A OPERAÇÃO COPY DA TABELA [tb_gpx_full] ###
################################################################
copy_sql = """
    COPY tb_gpx_full (id_rota, nome_usuario, latitude, longitude, elevacao, data_rota, hora_rota, cidade, estado, pais, carga_banco)
    FROM stdin WITH CSV HEADER DELIMITER as ';'
"""

# copy_sql_distancia = """
#     COPY tb_dist_euclidian_manhattan_minkowski (id_rota, nome_usuario, latitude, longitude, elevacao, data_rota, hora_rota, cidade, estado, pais, carga_banco)
#     FROM stdin WITH CSV HEADER DELIMITER as ';'
# """


#########################################################################
### COMANDO PARA INSERT NA TABELA [tb_dist_euclidian_manhattan_minkowski]
#########################################################################
try:
    arquivos_rotas_gpx_csv = [arquivo_gpx for arquivo_gpx in minioclient.list_objects(CAMADA_GOLD) if arquivo_gpx.object_name.endswith(".csv")] #--> Listando todos os arquivos da camada bronze do datalake com extensão .csv
    for arquivo_rotas_gpx_csv in arquivos_rotas_gpx_csv: #--> Iterando sobre a lista encontrada
        obj_rota_csv = minioclient.get_object(CAMADA_GOLD, arquivo_rotas_gpx_csv.object_name) #--> Obtendo o nome do arquivo de dentro da camada bronze
        csv_decod = obj_rota_csv.data.decode('utf-8') #--> Decodificando o arquivo encontrado para utf-8 - Essa conversão transforma os dados obtidos do arquivo no bucket em bytes
        arquivo_csv = StringIO(csv_decod) #--> Convertendo os bytes em string
        df = pd.read_csv(arquivo_csv, sep=';') #--> Convertendo string para pandas dataframe

        #df = pd.read_csv('11190523__routes__HYUNDAI_IONIQ_5_2022.csv', sep=';')
        df['lat1'] = df['latitude'].shift() #--> Aqui eu passo a função shift na coluna latitude e já crio uma nova coluna chamada lat 1
        df['lon1'] = df['longitude'].shift() #--> Aqui eu passo a função shift na coluna longitude e já crio uma nova coluna chamada lon 1
        df = df.rename(columns={'latitude': 'lat2', 'longitude': 'lon2'})
        df = df.dropna(subset=['lat1', 'lon1'])


        df['dist_euclidiana'] = df.apply(calc_dist_euclidiana, axis=1)
        df['dist_manhattan'] = df.apply(calc_dist_manhattan, axis=1)
        df['dist_minkowski'] = df.apply(calc_dist_minkowski, axis=1)


        # Obtendo as informações isoladas
        id_rota = df['id_rota'].iloc[0]
        nome_usuario = df['nome_usuario'].iloc[0]
        data_viagem = df['data'].iloc[0]
        hora_inicio = df['hora'].iloc[0]
        hora_fim = df['hora'].iloc[-1]  # Última ocorrência de hora
        cidade = df['cidade'].iloc[0]
        pais = df['pais'].iloc[0]
        
        
        # Calcular o tempo de viagem
        primeira_hora = pd.to_datetime(hora_inicio)
        ultima_hora = pd.to_datetime(hora_fim)
        if ultima_hora > primeira_hora:
            tempo_viagem = ultima_hora - primeira_hora
        else:
            tempo_viagem = primeira_hora - ultima_hora
        
        
        # Calcular as somas das distâncias
        dist_euclidiana = df['dist_euclidiana'].sum()
        dist_manhattan = df['dist_manhattan'].sum()
        dist_minkowski = df['dist_minkowski'].sum()
    
    
        # Definir a data de carga do banco como a hora atual
        data_carga_banco = datetime.now()
        # Criando o dataframe
        # df_distancias = pd.DataFrame({
        #     'id_rota': [id_rota],
        #     'nome_usuario': [nome_usuario],
        #     'data_viagem': [data_viagem],
        #     'hora_inicio': [hora_inicio],
        #     'hora_fim': [hora_fim],
        #     'tempo_viagem': [tempo_viagem],
        #     'cidade': [cidade],
        #     'pais': [pais],
        #     'dist_euclidiana': [dist_euclidiana],
        #     'dist_manhattan': [dist_manhattan],
        #     'dist_minkowski': [dist_minkowski],
        #     'data_carga_banco': [data_carga_banco]
        # })

        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        insert_dist = f'''
            insert into tb_dist_euclidian_manhattan_minkowski (id_rota,nome_usuario,data_viagem,hora_inicio,hora_fim,tempo_viagem,cidade,pais,dist_euclidiana,dist_manhattan,dist_minkowski,data_carga_banco)
            values (
                '{id_rota}',
                '{nome_usuario}',
                '{data_viagem}',
                '{hora_inicio}',
                '{hora_fim}',
                '{tempo_viagem}',
                '{cidade}',
                '{pais}',
                '{dist_euclidiana}',
                '{dist_manhattan}',
                '{dist_minkowski}',
                '{data_carga_banco}'
                )'''
        cursor.execute(insert_dist)
        conn.commit()
        conn.close()    


    # # Converta o DataFrame enriquecido de volta para CSV
    #     distancias_csv = df_distancias.to_csv(index=False, sep=';')
    #     distancias_csv_bytes = distancias_csv.encode('utf-8')

    # # Crie um buffer de bytes
    #     distancias_csv_buffer = BytesIO(distancias_csv_bytes)

    #     minioclient.put_object(
    #         DISTANCIAS,
    #         arquivo_rotas_gpx_csv.object_name,  # Use o mesmo nome de arquivo
    #         data=distancias_csv_buffer,
    #         length=len(distancias_csv_bytes),
    #         content_type='application/csv')

except Exception as e:
    # Em caso de erro, imprime a mensagem de erro
    print(f"Erro no insert da [tb_dist_euclidian_manhattam_minkowski]: {str(e)}")


#########################################################
### COMANDO PARA CARGA DO CSV NA TABELA [tb_gpx_full] ### 
#########################################################
try:
    # Lista todos os arquivos na camada "gold" do Minio que têm extensão .csv
    arquivos_rotas_gpx_csv = [arquivo_gpx for arquivo_gpx in minioclient.list_objects(CAMADA_GOLD) if arquivo_gpx.object_name.endswith(".csv")]
    
    # Verifica se há arquivos no bucket antes de continuar
    if not arquivos_rotas_gpx_csv:
        print("Não existem arquivos CSV no bucket. Nenhuma carga de dados será executada.")

    else:
        # Conexão com o banco de dados PostgreSQL
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()

        # Itera sobre cada arquivo CSV encontrado no Minio
        for arquivo_rotas_gpx_csv in arquivos_rotas_gpx_csv:
            # Obtém o objeto do arquivo CSV do Minio  
            obj_rota_csv = minioclient.get_object(CAMADA_GOLD, arquivo_rotas_gpx_csv.object_name)            

            # Decodifica os dados do arquivo CSV de bytes para string
            csv_decod = obj_rota_csv.data.decode('utf-8')  # Convertendo bytes para string
            arquivo_csv = StringIO(csv_decod)
            df = pd.read_csv(arquivo_csv, sep=';')
            csv_bytes = df.to_csv(index=False,sep=';').encode('utf-8')
            csv_buffer = BytesIO(csv_bytes)
            nome_arquivo = arquivo_rotas_gpx_csv.object_name


            # Usa io.StringIO para criar um objeto de arquivo legível a partir da string CSV
            with io.StringIO(csv_decod) as file:        

                # Executa o comando COPY para inserir os dados no banco de dados PostgreSQL
                cursor.copy_expert(sql=copy_sql, file=file)

            ## Commit para salvar as alterações no banco de dados    
            conn.commit()

            minioclient.put_object( #-->Usdndo o metodo do MinIO responsável por adicionar arquivos no Bucket
                    CAMADA_FILES_IN_TABLE, #--> Nome da camada de destino do arquivo transformado
                    nome_arquivo, #--> Nome do arquivo a ser adicionado na nova camada
                    data=csv_buffer, #--> Objeto csv_buffer que contém os bytes do arquivo CSV.
                    length=len(csv_bytes), #--> Especificando o comprimento dos bytes do arquivo CSV que você está enviando.
                    content_type='application/csv')        
            
            # Após a copia para o bucket de segurança os arquivos são eliminados da camada gold
            minioclient.remove_object(CAMADA_GOLD, arquivo_rotas_gpx_csv.object_name)

        # Fecha a conexão com o banco de dados PostgreSQL
        conn.close()

except Exception as e:
    # Em caso de erro, imprime a mensagem de erro
    print(f"Erro na carga da tabela [tb_gpx_full]: {str(e)}")

# end_time = time.time()
# execution_time = end_time - start_time
# 
# hours, remainder = divmod(execution_time, 3600)
# minutes, remainder = divmod(remainder, 60)
# seconds, milliseconds = divmod(remainder, 1)
# 
# print(f"Tempo de execução: {int(hours)} horas, {int(minutes)} minutos, {int(seconds)} segundos e {int(milliseconds * 1000)} milissegundos")
