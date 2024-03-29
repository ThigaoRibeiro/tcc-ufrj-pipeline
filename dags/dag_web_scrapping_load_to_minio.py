#from airflow.operators.bash_operator import BashOperator
from datetime import datetime, timedelta
from airflow.models import DAG
from airflow.operators.bash import BashOperator

default_args={
     'owner': 'thiago',     
     'retries': 5,
     'retry_delay': timedelta(minutes=5)
}


with DAG (
    dag_id='exec-web-scraping',
    default_args= default_args,
    description='DAG Responsável pelo processo de raspagem dos dados do OpenStreetMap, pré processamento e carga no bucket.',
    start_date=datetime(2023,9,18),
    #schedule_interval='@daily',
    schedule_interval='*/20 * * * *',
    catchup=False
) as dag:
      

# 1ª Tarefa
    exec_web_scraping = BashOperator(
        task_id='web_scraping',
        bash_command='python3 /home/thiago/tcc_ufrj/scripts_finalizados/1_webScraping_openstreetmap.py',
        dag=dag,
    )

# 2ª Tarefa
    exec_rename_processing_files = BashOperator(
        task_id='rename_processing_files',
        bash_command='python3 /home/thiago/tcc_ufrj/scripts_finalizados/2_rename_processing_files.py',
        dag=dag,
    )

# 3ª Tarefa
    exec_data_prep_silver = BashOperator(
        task_id='data_prep_silver',
        bash_command='python3 /home/thiago/tcc_ufrj/scripts_finalizados/3_data_prep_silver.py',
        dag=dag,
    )

# 4ª Tarefa
    exec_data_prep_gold = BashOperator(
        task_id='data_prep_gold',
        bash_command='python3 /home/thiago/tcc_ufrj/scripts_finalizados/4_data_prep_gold.py',
        dag=dag,
    )


# 5ª Tarefa
    exec_minio_to_postgres_sync = BashOperator(
        task_id='load_minio_to_bucket',
        bash_command='python3 /home/thiago/tcc_ufrj/scripts_finalizados/5_minio_to_postgresql.py',
        dag=dag,
    )

# Definindo a ordem das tarefas
exec_web_scraping >> exec_rename_processing_files >> exec_data_prep_silver >> exec_data_prep_gold >> exec_minio_to_postgres_sync
#exec_web_scraping