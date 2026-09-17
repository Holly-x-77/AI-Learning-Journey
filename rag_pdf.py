from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

# 读取 API Key，用于调用 DeepSeek 对话模型
with open("key.txt", "r", encoding="utf-8") as f:
    txt = f.read().strip()

# 初始化大模型：DeepSeek 负责根据检索到的资料回答问题
llm = ChatOpenAI(model="deepseek-chat", api_key=txt, base_url="https://api.deepseek.com")

# 1. 加载 PDF：每一页会变成一个 Document 对象
loader = PyPDFLoader("test.pdf")
docs = loader.load()

# 2. 文本切分：把整份 PDF 拆成约 1000 字的小块，相邻块重叠 200 字，避免关键句子被切断
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
chunks = text_splitter.split_documents(docs)

# 3. 嵌入模型：把文字块转成向量。DeepSeek 主要用于对话，这里用本地 HuggingFace 模型做向量化
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

# 4. 写入 Chroma 向量数据库：持久化到本地 chroma_db 目录，方便下次直接检索
vectorstore = Chroma.from_documents(
    documents=chunks,
    embedding=embeddings,
    persist_directory="./chroma_db",
)

# 5. 用户提问：先在向量库里找出语义最相近的 3 个文本块，再作为 context 交给大模型
question = "监理的工作是什么？"
retrieved_docs = vectorstore.similarity_search(question, k=3)
knowledge = "\n\n".join(doc.page_content for doc in retrieved_docs)

# 提示词：要求模型只基于检索到的资料作答
prompt = ChatPromptTemplate.from_template("""基于以下信息回答问题：{context}问题{question}""")

# 保留原有链式调用：提示词 -> 大模型 -> 解析成字符串
chain = prompt | llm | StrOutputParser()
response = chain.invoke({"context": knowledge, "question": question})
print(response)
