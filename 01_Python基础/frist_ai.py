from pathlib import Path
from openai import OpenAI
current_folder = Path(__file__).parent
key_path = current_folder / "key.txt"
api_key = key_path.read_text(encoding="utf-8").strip()
client = OpenAI(api_key=api_key,base_url="https://api.deepseek.com")
print("AI助手已经启动！输入'退出'结束对话。")
while True:
    user_input = input("\n你问：")
    if user_input == "退出":
        print("再见！")
        break
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一个专业的工程管理助理"},
                {"role": "user", "content": user_input}])
        ai_reply = response.choices[0].message.content
        print(f"AI答：{ai_reply}")
        with open("text", "a", encoding="utf-8") as f:
            f.write(f"你问{user_input} ")
            f.write(f"AI回答{ai_reply}")
            f.write("-"* 30+"\n")
    except Exception as e:
        print(f"出错了，出错原因是{e}")