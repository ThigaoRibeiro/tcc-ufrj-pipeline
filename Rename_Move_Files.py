# Linha 3: Importa o módulo 'os', que fornece funções para interagir com o sistema operacional.
# Linha 4: Importa o módulo 'shutil', que fornece funções para operações de cópia/movimentação de arquivos e diretórios.
import os
#import shutil


# Linha 9: Definir a constante 'DATALAKE_STAGE' como o caminho do diretório de destino no datalake.
# Linha 10: Definir a constante 'DOWNLOADS' como o caminho para o diretório de downloads.
DATALAKE_STAGE = 'DATALAKE_STAGE'
DOWNLOADS = '/home/thiago/Downloads/'


# Linha 19: Cria uma lista de nomes de arquivos para renomear. Isso é feito percorrendo os arquivos no diretório de downloads
#           e selecionando apenas aqueles que terminam com a extensão ".crdownload".
# Linha 20-22: Um loop 'for' é usado para iterar sobre cada nome de arquivo a ser renomeado.
# Linha 21: Cria um novo nome de arquivo removendo a extensão ".crdownload" do nome original.
# Linha 22: Usar a função 'os.rename' para renomear o arquivo. Isso é feito combinando o caminho completo do arquivo original
#           com o novo nome. O arquivo é renomeado no mesmo diretório.
files_to_rename = [arquivo for arquivo in os.listdir(DOWNLOADS) if arquivo.endswith(".crdownload")]
for file_name in files_to_rename:
        new_name = file_name.replace(".crdownload", "")
        os.rename(os.path.join(DOWNLOADS, file_name), os.path.join(DOWNLOADS, new_name))


# Linha 31: Cria uma lista de nomes de arquivos a serem movidos para o datalake. Isso é feito percorrendo os arquivos no diretório
#           de downloads e selecionando apenas aqueles que terminam com a extensão ".gpx".
# Linha 32-35: Um loop 'for' é usado para iterar sobre cada nome de arquivo a ser movido.
# Linha 33-34: Constrói os caminhos de origem e destino dos arquivos usando o diretório de downloads e o diretório do datalake.
# Linha 35: Usa a função 'os.rename' para mover o arquivo. O arquivo é movido da origem para o destino especificado.
#           Isso também efetivamente renomeia o arquivo, uma vez que o diretório de destino é diferente do diretório de downloads.
files_to_move = [files for files in os.listdir(DOWNLOADS) if files.endswith(".gpx")]
for name_files in files_to_move:
    origin_path = os.path.join(DOWNLOADS, name_files)
    destiny_path = os.path.join(DATALAKE_STAGE, name_files)
    os.rename(origin_path, destiny_path)