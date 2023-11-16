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


minioclient = Minio('localhost:9000',
    access_key='minioadmin',
    secret_key='minioadmin',
    secure=False)

db_config = {
'host': 'localhost',
'database': 'gold-saint',
'user': 'postgres',
'password': 'postgres',
}


sql_query = """
select	
	nome_usuario,
	case when tipo_combustivel = 'gas' then 1 end as tipo_combustivel, 	
	dist_km,
	media_consumo_km_l, 
	case when custo_trajeto = null then avg(custo_trajeto) else custo_trajeto end as custo_trajeto  	
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
df_resultado = df_agrup_veiculos[['nome_usuario', 'dist_km', 'media_consumo_km_l', 'cluster_consumo']].copy()
df_resultado



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