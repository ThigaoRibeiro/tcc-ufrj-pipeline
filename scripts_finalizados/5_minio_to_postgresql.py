##############################################
### IMPORTAÇÃO DAS BIBLIOTECAS NECESSÁRIAS ###
##############################################
# pip install minio
# pip install psycopg2-binary

import psycopg2
from minio import Minio
import io
from io import StringIO, BytesIO
import pandas as pd
import requests
# import time
# start_time = time.time()


####################################
### DEFINIÇÃO DA CAMADA NO MINIO ###
####################################
CAMADA_GOLD = 'gold'
CAMADA_FILES_IN_TABLE = 'files-in-table'

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

token_api = '5b3ce3597851110001cf624838eb860780704eca99c41867a83c9f6b'

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
            insert into tb_distancias_percorridas_api (id_unico,nome_usuario,data_inicio_rota,data_fim_rota,hora_inicio_rota,hora_fim_rota,latitude_inicial,longitude_inicial,latitude_final,longitude_final,cidade,estado,pais,distancia_real_km_api,data_carga_banco)
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
        print(f"Erro: {str(e)} no id {id_unico}")
        continue

########################################
### COMANDO SQL PARA A OPERAÇÃO COPY ###
########################################
copy_sql = """
    COPY tb_gpx_full (id_rota, nome_usuario, latitude, longitude, elevacao, data_rota, hora_rota, cidade, estado, pais, carga_banco)
    FROM stdin WITH CSV HEADER DELIMITER as ';'
"""

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
    print(f"Erro: {str(e)}")


# end_time = time.time()
# execution_time = end_time - start_time
# 
# hours, remainder = divmod(execution_time, 3600)
# minutes, remainder = divmod(remainder, 60)
# seconds, milliseconds = divmod(remainder, 1)
# 
# print(f"Tempo de execução: {int(hours)} horas, {int(minutes)} minutos, {int(seconds)} segundos e {int(milliseconds * 1000)} milissegundos")
