from datetime import datetime, timedelta
from airflow.models import DAG
from airflow.operators.bash import BashOperator

default_args={
     'owner': 'thiago',     
     'retries': 5,
     'retry_delay': timedelta(minutes=5)
}


with DAG (
    dag_id='load_minio_to_postgres',
    default_args= default_args,
    description='DAG Responsável por verificar a existencia de arquivos na camada Silver. Caso existam arquivos, estes serOpenStreetMap, pré processamento e carga no bucket.',
    start_date=datetime(2023,9,8),    
    schedule_interval='0 */2 * * *',  # Executa a cada 2 horas
    catchup=False
) as dag:
      

# Tarefa para executar o script WebScraping_OpenStreetMap_v2.py
    minio_to_postgres_sync = BashOperator(
        task_id='load_minio_to_bucket',
        bash_command='/home/thiago/tcc_ufrj/scripts_finalizados/Minio_to_Postgresql.py',
        dag=dag,
    )

# Defina a ordem das tarefas
minio_to_postgres_sync