# Importação dos Módulos Necessários - *** pip install minio ***
# Linha 6: O módulo os é usado para interagir com o sistema operacional
# Linha 7: O módulo minio é usado para interagir com um servidor MinIO
# Linha 8: O módulo S3Error é uma exceção específica do MinIO para exibição de forma semelhante ao Amazon S3
import os
from minio import Minio
from minio.error import S3Error

# Definição de variáveis. 
# Linha 14: DOWNLOADS recebe o caminho do diretório de downloads
# Linha 15: BRONZE_LAYER recebe uma string que representa uma camada ("layer") no servidor MinIO.
DOWNLOADS = '/home/thiago/Downloads/'
BRONZE_LAYER = 'bronze'

# Aqui, uma instância do cliente Minio é criada. 
# Linha 23: O cliente é configurado para se conectar a um servidor MinIO local usando as credenciais fornecidas
# Linhas 24 e 25: A chave de acesso = usuário e chave secreta = Senha 
# Linha 26: Sem usar conexão segura (HTTPS).
minioclient = Minio('localhost:9000',
    access_key='minioadmin',
    secret_key='minioadmin',
    secure=False)

# Linha 27: Uma lista é gerada com os arquivos do diretório de downloads que possuem a extensão ".crdownload" 
# Linhas 28 e 29: Em seguida, estes são renomeados removendo a extensão ".crdownload"  
# Linha 30: Para cada arquivo, um novo nome é gerado e a função os.rename é usada para remover essa extensão
files_to_rename = [arquivo for arquivo in os.listdir(DOWNLOADS) if arquivo.endswith(".crdownload")]
for file_name in files_to_rename:
        new_name = file_name.replace(".crdownload", "")
        os.rename(os.path.join(DOWNLOADS, file_name), os.path.join(DOWNLOADS, new_name))

# Linha 35: Uma lista é gerada com os arquivos do diretório de downloads que possuem a extensão ".gpx" 
# Linhas 36 à 39: Para cada arquivo encontrado, verifica-se se é um arquivo válido (não um diretório)
# Linhas 41 à 44: usa-se o cliente Minio para enviar o arquivo para o bucket especificado (BRONZE_LAYER), e após o envio bem-sucedido, o arquivo é excluído da pasta de downloads. 
# Linhas 45 e 46: Se ocorrer um erro durante o envio, uma mensagem de erro é exibida.
files_to_move = [files for files in os.listdir(DOWNLOADS) if files.endswith(".gpx")]
for name_file in files_to_move:
    local_path = os.path.join(DOWNLOADS, name_file)    
    if os.path.isfile(local_path):
        try:
            minioclient.fput_object(BRONZE_LAYER, name_file, local_path)
            print(f"Arquivo {name_file} enviado com sucesso para o bucket.")
            os.remove(local_path)
        except S3Error as e:
            print(f"Erro ao enviar o arquivo: {name_file} -> Erro: {e}")