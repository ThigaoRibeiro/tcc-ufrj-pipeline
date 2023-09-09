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
    start_date=datetime(2023,9,8),
    #schedule_interval='@daily',
    schedule_interval='*/5 * * * *',
    catchup=False
) as dag:
      

# Tarefa para executar o script WebScraping_OpenStreetMap_v2.py
    executar_web_scraping = BashOperator(
        task_id='web_scraping',
        bash_command='python3 /home/thiago/tcc_ufrj/scripts_finalizados/WebScraping_OpenStreetMap_v2.py',
        dag=dag,
    )

# Tarefa para executar o segundo script (Rename_Processing_Files_v2_csv.py)
    executar_rename_processing_files = BashOperator(
        task_id='rename_processing_files',
        bash_command='python3 /home/thiago/tcc_ufrj/scripts_finalizados/Rename_Processing_Files_v2_csv.py',
        dag=dag,
    )

# Tarefa para executar o terceiro script (Data_Preparation.py)
    executar_data_preparation = BashOperator(
        task_id='data_preparation',
        bash_command='python3 /home/thiago/tcc_ufrj/scripts_finalizados/Data_Preparation.py',
        dag=dag,
    )

# Defina a ordem das tarefas
executar_web_scraping >> executar_rename_processing_files >> executar_data_preparation