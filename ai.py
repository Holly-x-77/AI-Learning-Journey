from typing import List, Dict
import openai

# 配置你的API Key
openai.api_key = "YOUR_API_KEY"

class AIAgent:
    def __init__(self, system_prompt: str):
        self.system_prompt = system_prompt
        self.memory: List[Dict[str, str]] = []  # 对话记忆

    def add_memory(self, role: str, content: str):
        self.memory.append({"role": role, "content": content})

    def tool_search(self, query: str) -> str:
        """模拟工具：搜索函数，真实场景替换为搜索引擎/数据库"""
        return f"【搜索结果】关于 {query} 的信息：xxxx"

    def tool_calc(self, expression: str) -> str:
        """模拟工具：计算器"""
        try:
            res = eval(expression)
            return f"【计算结果】{expression} = {res}"
        except:
            return "【计算失败】表达式错误"

    def call_tool(self, tool_name: str, arg: str) -> str:
        if tool_name == "search":
            return self.tool_search(arg)
        elif tool_name == "calc":
            return self.tool_calc(arg)
        else:
            return f"工具 {tool_name} 不存在"

    def step(self, user_input: str) -> str:
        # 1. 用户输入存入记忆
        self.add_memory("user", user_input)

        messages = [{"role": "system", "content": self.system_prompt}] + self.memory
        # 2. Agent思考：是否调用工具
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.2
        )
        agent_reply = resp.choices[0].message.content
        self.add_memory("assistant", agent_reply)

        # 简单解析工具调用标记
        if "[TOOL]" in agent_reply:
            # 解析：[TOOL]search|今天天气
            parts = agent_reply.split("[TOOL]")[-1].strip()
            tool_name, arg = parts.split("|")
            tool_result = self.call_tool(tool_name, arg)
            self.add_memory("tool", tool_result)
            # 拿到工具结果，再次让大模型生成最终回答
            final_resp = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role":"system","content":self.system_prompt}] + self.memory,
                temperature=0.2
            )
            final_ans = final_resp.choices[0].message.content
            self.add_memory("assistant", final_ans)
            return final_ans
        return agent_reply


# Agent系统提示词：定义Agent行为（相当于Agent的训练目标）
agent_sys_prompt = """
你是一个AI Agent，拥有思考能力和工具调用能力。
规则：
1. 先思考问题，如果需要搜索信息，输出：[TOOL]search|查询词
2. 如果需要数学计算，输出：[TOOL]calc|数学表达式
3. 不需要工具就直接回答用户问题。
不要多余解释，严格遵守格式。
"""

if __name__ == "__main__":
    agent = AIAgent(system_prompt=agent_sys_prompt)
    print("AI Agent 已启动，输入exit退出")
    while True:
        user_msg = input("> ")
        if user_msg == "exit":
            break
        ans = agent.step(user_msg)
        print(f"Agent: {ans}")
