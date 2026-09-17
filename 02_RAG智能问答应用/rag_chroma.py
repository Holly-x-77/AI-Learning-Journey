import os
from pathlib import Path

# 1. 强制走国内 HuggingFace 镜像，防止下载卡死
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

# 2. 读取 API Key
current_folder = Path(__file__).parent
api_key = (current_folder / "key.txt").read_text(encoding="utf-8").strip()

# 3. 初始化大模型（用 DeepSeek 进行最终的问答）
llm = ChatOpenAI(model="deepseek-chat", api_key=api_key, base_url="https://api.deepseek.com")

# 4. 初始化本地向量化模型（极小，下载极快，无需 API 接口）
embeddings = HuggingFaceEmbeddings(
    model_name="BAAI/bge-small-zh-v1.5",
    model_kwargs={'device': 'cpu'},
    encode_kwargs={'normalize_embeddings': True}
)

# 5. 加载 PDF 并切分
loader = PyPDFLoader("test.pdf") # 确保你的PDF文件叫这个名字
docs = loader.load()
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
chunks = text_splitter.split_documents(docs)

# 6. 存入 Chroma 向量数据库
vectorstore = Chroma.from_documents(
    documents=chunks,
    embedding=embeddings,
    persist_directory="./chroma_db"
)

# 7. 检索并生成回答
question = "监理的工作是什么？"
retrieved_docs = vectorstore.similarity_search(question, k=3)   
knowledge = "\n\n".join(doc.page_content for doc in retrieved_docs)

prompt = ChatPromptTemplate.from_template("""
基于以下信息回答问题：
{context}
问题：{question}
""")

chain = prompt | llm | StrOutputParser()
response = chain.invoke({"context": knowledge, "question": question})
print(response)