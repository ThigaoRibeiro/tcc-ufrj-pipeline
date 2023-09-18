##############################################
### IMPORTAÇÃO DAS BIBLIOTECAS NECESSÁRIAS ###
##############################################
# pip install minio
# pip install psycopg2

import psycopg2
from minio import Minio
import io
from io import StringIO, BytesIO
import pandas as pd

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
'database': 'gold-saint',
'user': 'postgres',
'password': 'postgres',
}

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