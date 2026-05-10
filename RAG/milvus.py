from pymilvus import DataType, MilvusClient
from RAG import get_chunks, init_embedding_model
from utils import read_pdf

class MilvusProcessor:
  def __init__(self, database: str):
    self.client = MilvusClient(
      uri="http://localhost:19530",
      token="root:Milvus"
    )
    self.embedding = init_embedding_model()
    self.init_databases(database=database)

  def init_databases(self, database: list[str] | str):
      if not self.check_database_exist(database):
        self.client.create_database(db_name=database)
  
  def check_database_exist(self, database: str):
    current_databases = self.client.list_databases()
    return database in current_databases

  def create_collection(self, collection_name):
    if self.client.has_collection(collection_name):
      self.client.drop_collection(collection_name)

    dim = self.embedding.dimensions
    schemas = self.client.create_schema()

    schemas.add_field(
      field_name="id", datatype=DataType.INT64, is_primary=True, auto_id=True
    )

    schemas.add_field(
      field_name="text", datatype=DataType.VARCHAR, max_length=3000, enable_analyzer=True
    )

    schemas.add_field(
      field_name="embedding", datatype=DataType.FLOAT_VECTOR, dim=dim
    )

    self.client.create_collection(
      collection_name=collection_name,
      metric_type="COSINE",
      auto_id=True,
      schema=schemas,
    )
  
  def insert_text(self, collection_name: str, text: str):
    chunks = get_chunks(text)
    embedding_result = []
    for chunk in [chunks[i:i+64] for i in range(0, len(chunks), 64)]:
      result = self.embedding.embed_documents(chunk)
      embedding_result.extend([{ "embedding": vector, "text": chunk[i] } for i, vector in enumerate(result)])
    self.client.insert(collection_name=collection_name, data=embedding_result)

    index_params = self.client.prepare_index_params()
    index_params.add_index(
      field_name="embedding", index_type="IVF_FLAT", metric_type="COSINE", params={"nlist": 128}
    )
    self.client.create_index(
      collection_name=collection_name,
      index_params=index_params
    )

  def query_search(self, collection_name: str, text: str):
    """
      根据查询内容从向量数据库检索相关数据
      :param collection_name: 检索数据集名称
      :param str: 查询内容
    """
    query_vec = self.embedding.embed_documents([text])
    self.client.load_collection(collection_name=collection_name)
    result = self.client.search(
      collection_name=collection_name,
      data=query_vec,
      limit=5,
      output_fields=["text"]
    )
    return result

  def query_search_tool(self, collection_name: str):
    def inner_tool(text: str):
      """
        根据查询内容从向量数据库检索相关数据
        :param str: 查询内容
      """
      return self.query_search(collection_name=collection_name, text=text)
    return inner_tool
