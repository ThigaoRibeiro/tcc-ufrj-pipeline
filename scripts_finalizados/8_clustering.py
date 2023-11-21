import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import numpy as np
from minio import Minio
import io
from io import StringIO, BytesIO
import psycopg2
from datetime import datetime
data_hora_atual = datetime.now()
CLUSTERING = 'clustering'
ML_RESULTS = 'resultados-ml'


minioclient = Minio('localhost:9000',
    access_key='minioadmin',
    secret_key='minioadmin',
    secure=False)

db_config = {
'host': 'localhost',
'database': 'postgres',
'user': 'postgres',
'password': 'postgres',
}


sql_query = """
select	
	nome_usuario,
	case when tipo_combustivel = 'gas' then 1 end as tipo_combustivel, 	
	dist_km,
	media_consumo_km_l, 
	case when custo_trajeto = null then avg(custo_trajeto::numeric) else custo_trajeto end as custo_trajeto  	
from vw_valores_combustivel_por_viagem
where tipo_combustivel = 'gas'
group by
	nome_usuario,
	tipo_combustivel, 	
	dist_km,
	media_consumo_km_l,
	custo_trajeto 
"""


conn = psycopg2.connect(**db_config)
cursor = conn.cursor()
cursor.execute(sql_query)
resultados_agrup_veiculos = cursor.fetchall()
conn.close()
df_agrup_veiculos = pd.DataFrame(resultados_agrup_veiculos, columns=[desc[0] for desc in cursor.description])


# Selecionando colunas relevantes
X = df_agrup_veiculos[['dist_km', 'media_consumo_km_l']]


# Normalizando os dados
scaler = StandardScaler()
X_normalized = scaler.fit_transform(X)


# Especificando o número de clusters
num_clusters = 3  # ou o número que você achar mais apropriado


# Aplicando o K-means
kmeans = KMeans(n_clusters=num_clusters, random_state=0)
df_agrup_veiculos['cluster_consumo'] = kmeans.fit_predict(X_normalized)


# Criando um novo DataFrame com os resultados do agrupamento
df_veiculos_clusterizados = df_agrup_veiculos[['nome_usuario', 'dist_km', 'media_consumo_km_l', 'cluster_consumo']].copy()


df_veiculos_clusterizados.to_csv('resultado_agrupamento.csv', index=False)

##--------------------------------------------------------------------------------------------------##
##--------------------------------------------------------------------------------------------------##
## Adicionando informações adicionais conforme necessário
#df_resultado['informacao_adicional'] = ...
## Salvando o DataFrame resultante em um arquivo CSV ou inserindo no banco de dados
#df_resultado.to_csv('resultado_agrupamento.csv', index=False)


##--------------------------------------------------------------------------------------------------##
##--------------------------------------------------------------------------------------------------##
## Calculando a média do consumo de combustível para cada cluster
#media_consumo_por_cluster = df_agrup_veiculos.groupby('cluster_consumo')['media_consumo_km_l'].mean()
## Exibindo os resultados
#for cluster, media_consumo in media_consumo_por_cluster.items():
#    print(f"\nCluster {cluster} - Média de Consumo: {media_consumo}")
#    veiculos_cluster = df_agrup_veiculos[df_agrup_veiculos['cluster_consumo'] == cluster]
#    print(veiculos_cluster[['nome_usuario', 'media_consumo_km_l']])

## Converta o DataFrame enriquecido de volta para CSV
csv_veiculos_clusterizados = df_veiculos_clusterizados.to_csv(index=False, sep=';')
csv_veiculos_clusterizados_bytes = csv_veiculos_clusterizados.encode('utf-8')

## Crie um buffer de bytes
csv_veiculos_clusterizados_buffer = BytesIO(csv_veiculos_clusterizados_bytes)
nome_arquivo = f'clustering_{data_hora_atual}.csv'

minioclient.put_object(
        CLUSTERING,
        nome_arquivo,  # Use o mesmo nome de arquivo
        data=csv_veiculos_clusterizados_buffer,
        length=len(csv_veiculos_clusterizados_bytes),
        content_type='application/csv')

## Enviando o clustering para o Banco 
conn = psycopg2.connect(**db_config)
cursor = conn.cursor()

truncate = """ truncate table veiculos_clusterizados_temp; """
cursor.execute(truncate)

copy_sql = """
    COPY veiculos_clusterizados_temp (nome_usuario, dist_km, media_consumo_km_l, cluster_consumo)
    FROM stdin WITH CSV HEADER DELIMITER as ';'"""

arquivos_clustering = [arquivo for arquivo in minioclient.list_objects(CLUSTERING) if arquivo.object_name.endswith(".csv")]
## Itera sobre cada arquivo CSV encontrado no Minio
for arquivo_clustering in arquivos_clustering:
    # Obtém o objeto do arquivo CSV do Minio  
    obj_regr = minioclient.get_object(CLUSTERING, arquivo_clustering.object_name)
    csv_decod = obj_regr.data.decode('utf-8')  # Convertendo bytes para string
    arquivo_csv = StringIO(csv_decod)
    df = pd.read_csv(arquivo_csv, sep=';')
    csv_bytes = df.to_csv(index=False,sep=';').encode('utf-8')
    csv_buffer = BytesIO(csv_bytes)
    nome_arquivo = arquivo_clustering.object_name

    with io.StringIO(csv_decod) as file:
        cursor.copy_expert(sql=copy_sql, file=file)
conn.commit()
conn.close()