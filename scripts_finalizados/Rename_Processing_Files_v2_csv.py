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
PRE_PROCESSAMENTO = '/home/thiago/tcc_ufrj/PRE_PROCESSAMENTO' #--> PRE_PROCESSAMENTO recebe o caminho do diretório com os arquivos pré processados
CAMADA_BRONZE = 'bronze' #--> CAMADA_BRONZE recebe uma string que representa uma camada ("layer") no servidor MinIO.

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
arquivos_pre_processamento = [arquivo for arquivo in os.listdir(PRE_PROCESSAMENTO) if arquivo.endswith(".gpx")] #--> Listando todos os arquivos da pasta pré-processamento com extensão .gpx
for arquivo_pre_processamento in arquivos_pre_processamento: #--> Iterando sobre a lista encontrada
    caminho_arquivo = os.path.join(PRE_PROCESSAMENTO, arquivo_pre_processamento) #--> Criando o caminho completo para o arquivo .gpx
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as arquivo_gpx: #--> Abrindo o arquivo .gpx
            gpx = gpxpy.parse(arquivo_gpx)

        info_rota = [] #--> Lista que servirá de apoio para converter o arquivo .gpx em uma lista
        for trilha in gpx.tracks: #--> Sequência com aninhamentos de for para acessar as camadas internas do arquivos tais como do arquivo .gpx tais como: [tracks] [segments] e [points] e assim conseguir converter em uma lista.
            for segmento in trilha.segments:
                for ponto in segmento.points:
                    info_rota.append({
                        'latitude': ponto.latitude, #--> Obtendo a latitude e atribuindo como item [value] da [Key] latitude da lista [info_rota]
                        'longitude': ponto.longitude, #--> Obtendo a longitude e atribuindo como item [value] da [Key] longitude da lista [info_rota]
                        'elevacao' : ponto.elevation, #--> Obtendo a elevação e atribuindo como item [value] da [Key] elevação da lista [info_rota]
                        'time_point' : ponto.time #--> Obtendo a hora do ponto de latitude - longitude e elevação e atribuindo como item [value] da [Key] time_point da lista [info_rota]
                    })
        arquivo_pre_processamento_csv = arquivo_pre_processamento.replace('.gpx','.csv') #--> Ajustando o nome do arquivo para ficar com a extensão .csv ao inves de .gpx
        info_rota_df = pd.DataFrame(info_rota) #--> Criando um dataframe a partir da lista 
        info_rota_df.to_csv(f'{PRE_PROCESSAMENTO}/{arquivo_pre_processamento_csv}', index=False) #--> Criando um .csv a partir do DF criado acima e com o nome definido na variável anterior
        os.remove(caminho_arquivo) #--> Excluindo o arquivo .gpx da pasta PRE_PROCESSAMENTO
    except Exception as e: #--> Capturando qualquer erro que porventura ocorra
        print(f"Erro ao converter o '{arquivo_pre_processamento}': {e}.") #--> Exibindo o erro
        os.remove(caminho_arquivo)
        print(f"Excluindo o arquivo defeituoso: {arquivo_pre_processamento}")
        

################################################################################################################
### MOVENDO OS ARQUIVOS COM A EXTENSÃO .CSV DA PASTA PRE_PROCESSAMENTO PARA A PRIMEIRA CAMADA (BRONZE) NO MINIO ###
################################################################################################################
arquivos_para_datalake = [arquivo for arquivo in os.listdir(PRE_PROCESSAMENTO) if arquivo.endswith(".csv")] #--> Listando todos os arquivos da pasta pré-processamento com extensão .csv
for nome_arquivo in arquivos_para_datalake: #--> Iterando sobre cada item da lista
    caminho_pre_proc = os.path.join(PRE_PROCESSAMENTO, nome_arquivo) #--> Criando o caminho completo para o arquivo .csv
    if os.path.isfile(caminho_pre_proc): #--> Verificando se o caminho especificado está apontando para um arquivo válido no sistema de arquivos.
        try:
            minioclient.fput_object(CAMADA_BRONZE, nome_arquivo, caminho_pre_proc) #--> Usando o cliente Minio para enviar o arquivo da pasta de pré processamento para o bucket especificado (CAMADA_BRONZE)
            print(f"Arquivo {nome_arquivo} enviado com sucesso para o bucket.") #--> Exibindo a mensagem de sucesso após o upload dos arquivos para o bucket.
            os.remove(caminho_pre_proc) # --> Após o envio bem sucedido para o bucket o arquivo é excluído da pasta PRE_PROCESSAMENTO
        except S3Error as e: #--> Capturando qualquer erro que porventura ocorra
            print(f"Erro ao enviar o arquivo: {nome_arquivo} -> Erro: {e}") #--> Exibindo o erro