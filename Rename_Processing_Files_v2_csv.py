##############################################
### IMPORTAÇÃO DAS BIBLIOTECAS NECESSÁRIAS ###
##############################################
# pip install minio 
# pip install gpxpy
# pip install pandas 

import gpxpy #--> Importação dos módulos relacionados a trabalhar com arquivos GPX
import gpxpy.gpx 
import pandas as pd #--> Importação da biblioteca pandas para análise e manipulação de dados
import os #--> # Importação do módulo os para interagir com o sistema operacional
from minio import Minio #--> O módulo minio é usado para interagir com um servidor MinIO
from minio.error import S3Error #--> O módulo S3Error é uma exceção específica do MinIO para exibição de forma semelhante ao Amazon S3

##############################
### DEFINIÇÃO DE VARIÁVEIS ### 
##############################
PRE_PROCESSING = '/home/thiago/tcc_ufrj/PRE_PROCESSING' #--> PRE_PROCESSING recebe o caminho do diretório com os arquivos pré processados
BRONZE_LAYER = 'bronze' #--> BRONZE_LAYER recebe uma string que representa uma camada ("layer") no servidor MinIO.

##############################################
### CRIANDO UMA INSTÂNCIA DO CLIENTE MINIO ###
##############################################
minioclient = Minio('localhost:9000', #--> O cliente é configurado para se conectar a um servidor MinIO local usando as credenciais fornecidas
    access_key='minioadmin', #--> A chave de acesso = usuário
    secret_key='minioadmin', #--> A chave secreta = Senha 
    secure=False) #--> Sem usar conexão segura (HTTPS).

###########################################################
### CONVERTENDO OS ARQUIVOS COM A EXTENSÃO .GPX EM .CSV ###
###########################################################
files_to_pre_processing = [arquivo for arquivo in os.listdir(PRE_PROCESSING) if arquivo.endswith(".gpx")] #--> Listando todos os arquivos da pasta pré-processamento com extensão .gpx
for file_to_pre_processing in files_to_pre_processing: #--> Iterando sobre a lista encontrada
    file_path = os.path.join(PRE_PROCESSING, file_to_pre_processing) #--> Criando o caminho completo para o arquivo .gpx
    try:
        with open(file_path, 'r', encoding='utf-8') as gpx_file: #--> Abrindo o arquivo .gpx
            gpx = gpxpy.parse(gpx_file)

        info_rota = [] #--> Lista que servirá de apoio para converter o arquivo .gpx em uma lista
        for track in gpx.tracks: #--> Sequência com aninhamentos de for para acessar as camadas internas do arquivos tais como do arquivo .gpx tais como: [tracks] [segments] e [points] e assim conseguir converter em uma lista.
            for segment in track.segments:
                for point in segment.points:
                    info_rota.append({
                        'latitude': point.latitude, #--> Obtendo a latitude e atribuindo como item [value] da [Key] latitude da lista [info_rota]
                        'longitude': point.longitude, #--> Obtendo a longitude e atribuindo como item [value] da [Key] longitude da lista [info_rota]
                        'elevacao' : point.elevation, #--> Obtendo a elevação e atribuindo como item [value] da [Key] elevação da lista [info_rota]
                        'time_point' : point.time #--> Obtendo a hora do ponto de latitude - longitude e elevação e atribuindo como item [value] da [Key] time_point da lista [info_rota]
                    })
        file_to_pre_processing_csv = file_to_pre_processing.replace('.gpx','.csv') #--> Ajustando o nome do arquivo para ficar com a extensão .csv ao inves de .gpx
        info_rota_df = pd.DataFrame(info_rota) #--> Criando um dataframe a partir da lista 
        info_rota_df.to_csv(f'{PRE_PROCESSING}/{file_to_pre_processing_csv}', index=False) #--> Criando um .csv a partir do DF criado acima e com o nome definido na variável anterior
        os.remove(file_path) #--> Excluindo o arquivo .gpx da pasta PRE_PROCESSING
    except Exception as e: #--> Capturando qualquer erro que porventura ocorra
        print(f"Erro ao converter o '{file_to_pre_processing}': {e}.") #--> Exibindo o erro
        os.remove(file_path)
        print(f"Excluindo o arquivo defeituoso: {file_to_pre_processing}")
        

################################################################################################################
### MOVENDO OS ARQUIVOS COM A EXTENSÃO .CSV DA PASTA PRE_PROCESSING PARA A PRIMEIRA CAMADA (BRONZE) NO MINIO ###
################################################################################################################
files_to_datalake = [files for files in os.listdir(PRE_PROCESSING) if files.endswith(".csv")] #--> Listando todos os arquivos da pasta pré-processamento com extensão .csv
for name_file in files_to_datalake: #--> Iterando sobre cada item da lista
    local_path = os.path.join(PRE_PROCESSING, name_file) #--> Criando o caminho completo para o arquivo .csv
    if os.path.isfile(local_path): #--> Verificando se o caminho especificado está apontando para um arquivo válido no sistema de arquivos.
        try:
            minioclient.fput_object(BRONZE_LAYER, name_file, local_path) #--> Usando o cliente Minio para enviar o arquivo para o bucket especificado (BRONZE_LAYER)
            print(f"Arquivo {name_file} enviado com sucesso para o bucket.") #--> Exibindo a mensagem de sucesso após o upload dos arquivos para o bucket.
            os.remove(local_path) # --> Após o envio bem sucedido para o bucket o arquivo é excluído da pasta PRE_PROCESSING
        except S3Error as e: #--> Capturando qualquer erro que porventura ocorra
            print(f"Erro ao enviar o arquivo: {name_file} -> Erro: {e}") #--> Exibindo o erro