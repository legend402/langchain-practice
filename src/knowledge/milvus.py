import os

from pymilvus import CollectionSchema, DataType, FieldSchema, Function, FunctionType, MilvusClient


MILVUS_URI = os.getenv("MILVUS_URI", "http://localhost:19530")
DENSE_DIM = 2048

_client: MilvusClient | None = None

def get_milvus_client() -> MilvusClient:
  global _client
  if _client is None:
    _client = MilvusClient(uri=MILVUS_URI)
  return _client

def _collection_name(user_id: str) -> str:
  return f"knowledge_{user_id.replace('-', '_')}"

def get_or_create_collection(user_id: str) -> str:
  """
    获取或创建用户的知识库 collection，返回 collection 名称。
    Schema 包含 dense_vector（embedding-3）和 sparse_vector（BM25 自动生成）。
  """
  client = get_milvus_client()
  col_name = _collection_name(user_id)

  if client.has_collection(col_name):
    return col_name
  
  schema = CollectionSchema(fields=[
    FieldSchema(
      name="pk",
      dtype=DataType.VARCHAR,
      is_primary=True,
      auto_id=True,
      max_length=100,
    ),
    FieldSchema(
      name="entry_id",
      dtype=DataType.VARCHAR,
      max_length=100,
    ),
    FieldSchema(
      name="chunk_index",
      dtype=DataType.INT32
    ),
    FieldSchema(
      name="text",
      dtype=DataType.VARCHAR,
      max_length=65535,
      enable_analyzer=True,
    ),
    FieldSchema(
      name="dense_vector",
      dtype=DataType.FLOAT_VECTOR,
      dim=DENSE_DIM,
    ),
    FieldSchema(
      name="sparse_vector",
      dtype=DataType.SPARSE_FLOAT_VECTOR,
    ),
  ])

  bm25_function = Function(
    name="text_bm25",
    input_field_names=["text"],
    output_field_names=["sparse_vector"],
    function_type=FunctionType.BM25
  )
  schema.add_function(bm25_function)

  client.create_collection(collection_name=col_name, schema=schema)

  index_params = client.prepare_index_params()
  index_params.add_index(
    field_name="dense_vector",
    index_type="AUTOINDEX",
    metric_type="IP",
  )
  index_params.add_index(
    field_name="sparse_vector",
    index_type="SPARSE_INVERTED_INDEX",
    metric_type="BM25",
    params={"inverted_index_algo": "DAAT_MAXSCORE"},
  )
  client.create_index(
    collection_name=col_name,
    index_params=index_params,
  )
  client.load_collection(col_name)

  return col_name

def delete_entry_chunks(user_id: str, entry_id: str) -> None:
  client = get_milvus_client()
  col_name = _collection_name(user_id)

  if not client.has_collection(col_name):
    return
  client.delete(
    collection_name=col_name,
    filter=f"entry_id == '{entry_id}'"
  )