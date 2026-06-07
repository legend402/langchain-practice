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

def _ensure_indexes(client: MilvusClient, col_name: str) -> None:
  """确保 collection 上存在必要的索引，若缺失则创建。"""
  index_names = client.list_indexes(collection_name=col_name)
  existing = {client.describe_index(col_name, name).get("field_name", "") for name in index_names}
  need_create = False
  index_params = client.prepare_index_params()

  if "dense_vector" not in existing:
    index_params.add_index(
      field_name="dense_vector",
      index_type="AUTOINDEX",
      metric_type="IP",
    )
    need_create = True

  if "sparse_vector" not in existing:
    index_params.add_index(
      field_name="sparse_vector",
      index_type="SPARSE_INVERTED_INDEX",
      metric_type="BM25",
      params={"inverted_index_algo": "DAAT_MAXSCORE"},
    )
    need_create = True

  if need_create:
    client.create_index(collection_name=col_name, index_params=index_params)

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
    _ensure_indexes(client, col_name)
    client.load_collection(col_name)
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
  _ensure_indexes(client, col_name)
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

def _v2_collection_name(user_id: str) -> str:
    """v2 collection 名称，带 _v2 后缀。"""
    return f"knowledge_v2_{user_id.replace('-', '_')}"

def get_or_create_v2_collection(user_id: str) -> str:
    """
    获取或创建 v2 知识库 collection，包含扩展元数据字段。
    新增字段：page_start, page_end, heading_path, content_type, table_id。
    参数:
        user_id: 用户 ID 字符串
    返回:
        collection 名称
    """
    client = get_milvus_client()
    col_name = _v2_collection_name(user_id)

    if client.has_collection(col_name):
        _ensure_indexes(client, col_name)
        client.load_collection(col_name)
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
            dtype=DataType.INT32,
        ),
        FieldSchema(
            name="text",
            dtype=DataType.VARCHAR,
            max_length=65535,
            enable_analyzer=True,
        ),
        FieldSchema(
            name="page_start",
            dtype=DataType.INT64,
        ),
        FieldSchema(
            name="page_end",
            dtype=DataType.INT64,
        ),
        FieldSchema(
            name="heading_path",
            dtype=DataType.VARCHAR,
            max_length=512,
        ),
        FieldSchema(
            name="content_type",
            dtype=DataType.VARCHAR,
            max_length=32,
        ),
        FieldSchema(
            name="table_id",
            dtype=DataType.VARCHAR,
            max_length=64,
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
        function_type=FunctionType.BM25,
    )
    schema.add_function(bm25_function)

    client.create_collection(collection_name=col_name, schema=schema)
    _ensure_indexes(client, col_name)
    client.load_collection(col_name)

    return col_name

def delete_v2_entry_chunks(user_id: str, entry_id: str) -> None:
    """
    从 v2 collection 中删除指定 entry 的所有 chunks。
    参数:
        user_id: 用户 ID
        entry_id: 知识条目 ID
    """
    client = get_milvus_client()
    col_name = _v2_collection_name(user_id)

    if not client.has_collection(col_name):
        return
    client.delete(
        collection_name=col_name,
        filter=f"entry_id == '{entry_id}'",
    )