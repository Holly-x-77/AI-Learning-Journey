from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
with open("key.txt","r",encoding="utf-8") as f:
    txt = f.read().strip()
llm = ChatOpenAI(model = "deepseek-chat",api_key = txt,base_url="https://api.deepseek.com")
knowledge = """工程合同管理主要研究工程合同的订立、履行、变更和索赔。
其中，工程索赔是指在工程承包合同履行中，当事人一方因对方不履行或未能正确履行合同所规定的义务而受到损失，向对方提出赔偿请求。"""
prompt = ChatPromptTemplate.from_template("""基于以下信息回答问题：{context}问题{question}""")
chain = prompt | llm |StrOutputParser()
response = chain.invoke({"context":knowledge,"question":"工程索赔是什么?"})
print(response)