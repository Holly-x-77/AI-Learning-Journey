from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.document_loaders import PyPDFLoader
with open("key.txt","r",encoding="utf-8") as f:
    txt = f.read().strip()
llm = ChatOpenAI(model = "deepseek-chat",api_key = txt,base_url="https://api.deepseek.com")
loader = PyPDFLoader("test.pdf")
docs = loader.load()
knowledge = "\n\n".join(doc.page_content for doc in docs)
prompt = ChatPromptTemplate.from_template("""基于以下信息回答问题：{context}问题{question}""")
chain = prompt | llm | StrOutputParser()
response = chain.invoke({"context":knowledge,"question":"监理的工作是什么？"})
print(response)