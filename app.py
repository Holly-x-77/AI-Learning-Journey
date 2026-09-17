import os  # 用来设置环境变量，让模型下载走国内镜像
from pathlib import Path  # 用来拼出 key.txt 的路径，避免找不到文件
import tempfile  # 上传的 PDF 先存成临时文件，PyPDFLoader 才能按路径去读

os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"  # 强制走国内 HuggingFace 镜像，防止模型下载卡死

import streamlit as st  # 用来做网页：标题、上传框、输入框、按钮、显示结果
from langchain_openai import ChatOpenAI  # 用来调用 DeepSeek 大模型（接口长得像 OpenAI）
from langchain_core.prompts import ChatPromptTemplate  # 用来写提示词模板，里面可以填资料和问题
from langchain_core.output_parsers import StrOutputParser  # 把模型返回结果收成普通字符串
from langchain_community.document_loaders import PyPDFLoader  # 专门用来读取 PDF 里的文字
from langchain_text_splitters import RecursiveCharacterTextSplitter  # 把长文本切成一小块一小块
from langchain_community.vectorstores import Chroma  # 本地向量数据库，负责按意思找相关段落
from langchain_community.embeddings import HuggingFaceEmbeddings  # 本地把文字变成向量，不用再申请一套接口


st.set_page_config(page_title="PDF 智能问答", layout="centered")  # 设置浏览器标签标题，页面居中更好看
st.title("PDF 智能问答助手")  # 网页上最大的标题，让用户一眼知道这是干什么的

uploaded_file = st.file_uploader("请上传一份 PDF 文件", type=["pdf"])  # 上传组件，只允许选 PDF
question = st.text_input("请输入你的问题", placeholder="例如：监理的工作是什么？")  # 文本框，让用户打问题
submit_button = st.button("提交")  # 点这个按钮才开始跑 RAG，避免一打字就反复计算


@st.cache_resource  # 把模型和向量化工具缓存起来，避免每次点按钮都重新下载、重新加载
def load_models():  # 定义一个函数：专门负责准备 DeepSeek 和本地嵌入模型
    current_folder = Path(__file__).parent  # 拿到 app.py 所在的文件夹
    api_key = (current_folder / "key.txt").read_text(encoding="utf-8").strip()  # 读出 API Key，去掉首尾空格
    llm = ChatOpenAI(model="deepseek-chat", api_key=api_key, base_url="https://api.deepseek.com")  # 准备好用来写答案的大模型
    embeddings = HuggingFaceEmbeddings(  # 准备好把中文变成向量的本地小模型
        model_name="BAAI/bge-small-zh-v1.5",  # 选用中文检索模型，适合监理类 PDF
        model_kwargs={"device": "cpu"},  # 用 CPU 跑，没有独立显卡也能用
        encode_kwargs={"normalize_embeddings": True},  # 把向量长度拉齐，检索更稳
    )  # 嵌入模型参数到这里结束
    return llm, embeddings  # 把两个工具一起交回去，后面 RAG 会用到


if submit_button:  # 只有用户点了“提交”，才开始干活
    try:  # 先尝试正常执行；万一出错，就跳到下面的 except，网页不会直接崩溃
        if uploaded_file is None:  # 如果根本没上传 PDF
            raise ValueError("请先上传一份 PDF 文件，再点击提交。")  # 主动报一个好懂的错，后面会用红色显示
        if not question.strip():  # 如果问题是空的，或者只打了空格
            raise ValueError("请先输入问题，再点击提交。")  # 同样给出友好提示

        llm, embeddings = load_models()  # 取出缓存好的大模型和向量化模型

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:  # 建一个临时 PDF 文件，关掉后先不自动删
            tmp.write(uploaded_file.getvalue())  # 把网页上上传的内容写进这个临时文件
            tmp_path = tmp.name  # 记住临时文件的完整路径，待会儿给 PyPDFLoader 用

        with st.spinner("正在阅读 PDF 并检索相关内容，请稍候..."):  # 转圈提示，让用户知道程序在干活，不是卡住了
            loader = PyPDFLoader(tmp_path)  # 用刚才保存的临时 PDF 来创建读取器
            docs = loader.load()  # 真正把 PDF 每一页的文字读出来
            if not docs:  # 如果一页字都没读到
                raise ValueError("这份 PDF 里没有读出文字，请换一份可复制文字的 PDF 再试。")  # 扫描件图片 PDF 经常会这样

            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)  # 规定每块大约 1000 字，相邻重叠 200 字
            chunks = text_splitter.split_documents(docs)  # 按规则把整份 PDF 切成小块
            if not chunks:  # 如果切完还是空的
                raise ValueError("PDF 切分后没有得到内容，请检查文件是否正常。")  # 告诉用户文件可能有问题

            persist_dir = tempfile.mkdtemp(prefix="chroma_db_")  # 每次问答建一个临时向量库文件夹，避免不同 PDF 的内容混在一起
            vectorstore = Chroma.from_documents(  # 把小块文字变成向量，存进 Chroma
                documents=chunks,  # 原料就是刚切好的文本块
                embedding=embeddings,  # 用本地中文模型做向量化
                persist_directory=persist_dir,  # 把这次的向量库存到临时目录
            )  # 向量库创建结束

            retrieved_docs = vectorstore.similarity_search(question, k=3)  # 按意思找出和问题最像的 3 块
            knowledge = "\n\n".join(doc.page_content for doc in retrieved_docs)  # 把这 3 块正文拼成一份参考资料
            if not knowledge.strip():  # 如果检索结果空空的
                raise ValueError("没有检索到相关内容，请换个问法，或确认 PDF 里确实有相关信息。")  # 友好提示换问题或换文件

            prompt = ChatPromptTemplate.from_template(  # 写提示词：要求模型先看资料，再回答问题
                """基于以下信息回答问题：
{context}
问题：{question}
"""
            )  # 模板到这里结束，{context} 和 {question} 后面会填进去
            chain = prompt | llm | StrOutputParser()  # 保留原来的链式调用：提示词 -> 大模型 -> 变成字符串
            response = chain.invoke({"context": knowledge, "question": question})  # 把检索到的资料和用户问题一起交给模型

        st.subheader("AI 回答")  # 在网页上加一个小标题，标明下面是答案
        st.write(response)  # 把模型生成的回答显示出来

        try:  # 清理临时 PDF 失败也不要影响已经显示出来的答案
            Path(tmp_path).unlink(missing_ok=True)  # 用完就把临时 PDF 删掉，避免磁盘越积越多
        except Exception:  # 删除文件万一失败
            pass  # 静默跳过，不影响用户看答案

    except Exception as e:  # 上面任何一步报错，都会来到这里
        st.error(f"出错了：{e}")  # 用红色提示告诉用户原因，而不是让整个网页崩溃
