# pip install minio
from minio import Minio
from minio.error import S3Error
from io import StringIO
import pandas as pd

BRONZE_LAYER = 'bronze'
SILVER_LAYER = 'silver'


minioclient = Minio('localhost:9000',
    access_key='minioadmin',
    secret_key='minioadmin',
    secure=False)

info_rota_csv = []
arquivos_rotas_gpx_csv = [arquivo_gpx for arquivo_gpx in minioclient.list_objects(BRONZE_LAYER) if arquivo_gpx.object_name.endswith(".csv")]