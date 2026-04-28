from langchain.tools import tool
import os

@tool
def read_file(file_path):
  """
    读取一个文件的内容
    :param file_path: 文件路径
  """
  try:
      with open(file_path, 'r', encoding='utf-8') as file:
          return file.read()
  except FileNotFoundError:
      return "File not found"
  except Exception as e:
      return f"Error: {e}"

@tool
def write_file(file_path, content):
  """
    写入内容到文件。
    :param file_path: 文件路径
    :param content: 要写入文件的内容
  """
  try:
      with open(file_path, 'w', encoding='utf-8') as file:
          file.write(content)
  except Exception as e:
      return f"Error: {e}"

@tool
def create_file(file_path, content):
  """
    创建一个新文件并写入内容。
    :param file_path: 文件路径
    :param content: 要写入文件的内容
  """
  with open(file_path, 'w', encoding='utf-8') as file:
      file.write(content)
      file.close()


@tool
def read_dir(dir_path):
  """
    读取一个目录的内容。
    :param dir_path: 目录路径
  """
  try:
      return os.listdir(dir_path)
  except FileNotFoundError:
      return "Directory not found"
  except Exception as e:
      return f"Error: {e}"

def is_path_exists(path):
  """
    检查文件或目录是否存在。
    :param path: 要检查的路径。
  """
  return os.path.exists(path)

def create_dir(dir_path):
  """
    创建一个新目录。
    :param dir_path: 目录路径
  """
  os.makedirs(dir_path, exist_ok=True)
