#from airflow.operators.bash_operator import BashOperator
from datetime import datetime
from airflow.models import DAG
from airflow.operators.bash import BashOperator
# from airflow.operators.python import PythonOperator
# import pytz  

# tz = 'America/Sao_Paulo'

# Defina a DAG
#dag = DAG(
#    'exec-web-scraping',
#    default_args={
#        'owner': 'thiago',
#        'start_date': datetime(2023, 9, 4, tzinfo=pytz.timezone(tz)),  # Adicione tzinfo aqui
#        'retries': 1,
#    },
#    schedule_interval='*/5 * * * *',  # Expressão cron para cada 5 minutos
#    end_date=datetime(2030, 12, 31, tzinfo=pytz.timezone(tz)),  # Defina uma data de término futura
#)

with DAG (
    dag_id='exec-web-scraping',
    schedule_interval='*/5 * * * *',
    start_date=datetime(year=2023, month=9, day=7),
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