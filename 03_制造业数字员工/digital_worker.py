"""制造业 AI 数字员工：用 LangChain 把 pandas 工单工具交给 DeepSeek，由模型自己决定调用顺序。"""

from pathlib import Path  # 用来定位脚本、CSV 和 API Key 的路径

import pandas as pd  # 用来读写本地工单表 work_data.csv
from langchain.tools import tool  # 把普通 Python 函数包装成大模型可以调用的工具
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage  # 对话消息类型
from langchain_openai import ChatOpenAI  # DeepSeek 接口兼容 OpenAI，所以用这个类来调用


CSV_PATH = Path(__file__).resolve().parent / "work_data.csv"  # 工单数据文件就放在本脚本同目录
KEY_CANDIDATES = [  # 按常见位置依次找 DeepSeek Key，避免换目录后找不到
    Path(__file__).resolve().parent / "key.txt",  # 先看本文件夹
    Path(__file__).resolve().parent.parent / "key.txt",  # 再看项目根目录（你现在的 key.txt 在这里）
]


def load_api_key() -> str:
    """从 key.txt 读取 DeepSeek API Key，并去掉首尾空白。"""
    for key_path in KEY_CANDIDATES:  # 一个一个位置去试
        if key_path.exists():  # 文件确实存在才读取
            return key_path.read_text(encoding="utf-8").strip()  # 读出内容并去掉换行空格
    raise FileNotFoundError("没有找到 key.txt，请把它放在项目根目录或本脚本同目录。")  # 找不到就明确报错


def load_work_data() -> pd.DataFrame:
    """读取本地工单表，保证列名和数据类型符合后续计算。"""
    if not CSV_PATH.exists():  # 如果 CSV 丢了
        raise FileNotFoundError(f"找不到工单文件：{CSV_PATH}")  # 告诉用户具体路径
    df = pd.read_csv(CSV_PATH, encoding="utf-8")  # 按 UTF-8 读入表格
    required_cols = ["工单号", "生产线", "计划产量", "实际产量", "状态"]  # 题目要求的五列
    missing = [col for col in required_cols if col not in df.columns]  # 检查缺了哪些列
    if missing:  # 只要缺列就不能继续
        raise ValueError(f"work_data.csv 缺少列：{missing}")  # 把缺的列名报出来
    df["计划产量"] = pd.to_numeric(df["计划产量"], errors="coerce")  # 产量必须是数字，才能算达成率
    df["实际产量"] = pd.to_numeric(df["实际产量"], errors="coerce")  # 实际产量同样转成数字
    return df  # 把整理好的表交回去


def match_line(df: pd.DataFrame, line_name: str) -> pd.DataFrame:
    """按生产线名称筛选行，兼容用户说“A”或“A生产线”。"""
    name = str(line_name).strip()  # 先去掉用户输入两边空格
    exact = df[df["生产线"].astype(str).str.strip() == name]  # 先按完整名称精确匹配
    if not exact.empty:  # 精确匹配到了就直接用
        return exact  # 返回这一条（或几条）工单
    fuzzy = df[df["生产线"].astype(str).str.contains(name, na=False)]  # 再尝试模糊包含，例如只写“A”
    return fuzzy  # 可能匹配到多行，也可能为空，交给调用方处理


def save_work_data(df: pd.DataFrame) -> None:
    """把修改后的工单表写回 CSV，状态更新才会真正落盘。"""
    df.to_csv(CSV_PATH, index=False, encoding="utf-8")  # 不写行号，避免下次读取多出一列


@tool
def get_data(line_name: str) -> str:
    """读取某条生产线的当前工单数据，包括工单号、计划产量、实际产量和状态。"""
    df = load_work_data()  # 每次调用都重新读文件，保证拿到最新状态
    rows = match_line(df, line_name)  # 找出这条线对应的工单
    if rows.empty:  # 表里没有这条线
        return f"未找到生产线：{line_name}。当前可选：{', '.join(df['生产线'].astype(str).tolist())}"  # 把可选线名告诉模型
    return rows.to_csv(index=False)  # 用 CSV 文本返回，方便模型阅读结构化数据


@tool
def calc_efficiency(line_name: str) -> str:
    """计算某条生产线的达成率，公式为 实际产量 / 计划产量，结果用百分比表示。"""
    df = load_work_data()  # 
    rows = match_line(df, line_name)  
    if rows.empty:  
        return f"未找到生产线：{line_name}，无法计算达成率。"  
    planned = float(rows["计划产量"].sum()) 
    actual = float(rows["实际产量"].sum())  
    if planned <= 0:  
        return f"{line_name} 的计划产量为 {planned}，无法计算达成率。"  
    rate = actual / planned  
    percent = round(rate * 100, 2)  
    below_80 = percent < 80  
    return (
        f"生产线：{line_name}\n"
        f"计划产量：{planned}\n"
        f"实际产量：{actual}\n"
        f"达成率：{percent}%\n"
        f"是否低于80%：{'是' if below_80 else '否'}"
    )  # 把数字和判断一起返回，模型就能决定下一步要不要改状态



@tool
def update_status(line_name: str, new_status: str) -> str:
    """修改某条生产线的状态，例如改成“预警”，并保存回 work_data.csv。"""
    df = load_work_data()  
    mask = df["生产线"].astype(str).str.strip() == str(line_name).strip()  
    if not mask.any():  # 精确没中，就再按包含匹配
        mask = df["生产线"].astype(str).str.contains(str(line_name).strip(), na=False)  # 兼容只传“A”
    if not mask.any():  # 仍然找不到
        return f"未找到生产线：{line_name}，状态未修改。"  
    old_status = df.loc[mask, "状态"].astype(str).tolist()  # 记下改之前的状态，方便回显
    df.loc[mask, "状态"] = new_status  # 把匹配到的行状态改成新值
    save_work_data(df)  # 立刻写回 CSV
    return (
        f"已将生产线 {line_name} 的状态从 {old_status} 修改为“{new_status}”，并已保存到 work_data.csv。"
    )  # 告诉模型改成功了


TOOLS = [get_data, calc_efficiency, update_status]  # 三个 pandas 工具组成工具箱
TOOLS_BY_NAME = {t.name: t for t in TOOLS}  # 用工具名快速找到对应函数，执行模型点名的调用


SYSTEM_PROMPT = """你是制造业车间的 AI 数字员工。
你必须通过工具完成查数、算达成率、改状态，不要凭空编造工单数字。
可用工具：
1. get_data(line_name)：查看某条生产线当前数据
2. calc_efficiency(line_name)：计算达成率（实际产量/计划产量）
3. update_status(line_name, new_status)：修改该生产线状态

处理规则：
- 用户提到 A 线、A生产线时，line_name 使用“A生产线”
- 先查数据，再算达成率
- 只有达成率低于 80% 时，才调用 update_status 把状态改成“预警”
- 达成率不低于 80% 时，不要改状态
- 全部工具调用结束后，用中文给出：当前数据、达成率、是否已改状态、以及一段可执行的改进意见
"""  # 系统提示只规定原则，具体调用顺序仍由模型根据用户问题自己决定


def run_agent(user_input: str, on_step=None) -> str:
    """把工具绑定给 DeepSeek，并循环执行模型自己选择的工具调用。

    on_step 是可选回调。网页版会用它把“正在读取数据...”这类过程显示出来。
    """
    api_key = load_api_key()  # 先拿到 Key
    llm = ChatOpenAI(  # 初始化 DeepSeek 对话模型
        model="deepseek-chat",  # 使用 DeepSeek 的对话模型
        api_key=api_key,  # 认证用的 Key
        base_url="https://api.deepseek.com",  # DeepSeek 官方兼容 OpenAI 的地址
        temperature=0,  # 温度调低，工具参数更稳定
    )
    llm_with_tools = llm.bind_tools(TOOLS)  # 关键一步：把三个 pandas 工具绑定给大模型

    messages = [  # 组装对话上下文
        SystemMessage(content=SYSTEM_PROMPT),  # 先告诉模型它是数字员工、有哪些工具
        HumanMessage(content=user_input),  # 再放入用户在终端里输入的任务
    ]

    max_rounds = 8  # 防止工具循环失控，一般 3 次调用足够完成本题
    for round_index in range(1, max_rounds + 1):  # 每一轮：模型思考 -> 可能调工具 -> 把结果还回去
        ai_message = llm_with_tools.invoke(messages)  # 让已绑定工具的模型决定：回答还是调用函数
        messages.append(ai_message)  # 把模型这一步的决定记进上下文

        if not ai_message.tool_calls:  # 没有工具调用，说明模型认为可以给最终答复了
            return ai_message.content  # 把最终中文回复交给终端打印

        print(f"\n第 {round_index} 轮，模型决定调用 {len(ai_message.tool_calls)} 个工具：")  # 让你在终端看到调用顺序
        for tool_call in ai_message.tool_calls:  # 本轮可能一次调用多个工具
            name = tool_call["name"]  # 模型选中的工具名
            args = tool_call["args"]  # 模型填好的参数，例如 line_name="A生产线"
            print(f"  -> {name}({args})")  # 打印真实调用，方便核对顺序
            selected_tool = TOOLS_BY_NAME[name]  # 从工具箱里取出对应 pandas 函数
            result = selected_tool.invoke(args)  # 真正执行：读 CSV / 算达成率 / 改状态
            print(f"     返回：{result}")  # 把工具原始结果也打出来，便于调试
            if on_step is not None:  # 网页版把这一步思考过程同步到界面
                on_step(name, args, result)  # 例如显示“正在计算达成率...”
            messages.append(  # 把工具结果以 ToolMessage 形式还给模型
                ToolMessage(
                    content=str(result),  # 工具返回的文本
                    tool_call_id=tool_call["id"],  # 必须带上这次调用的 id，模型才能对上号
                )
            )

    return "工具调用次数过多，已停止。请缩小任务范围后再试。"  # 超过轮次时的兜底提示


if __name__ == "__main__":  # 只有直接运行本文件时才进入终端对话
    print("制造业 AI 数字员工已启动。输入“退出”结束。")  # 启动提示
    print("示例：帮我查一下A生产线的数据，计算一下达成率，如果低于80%就自动把状态改成“预警”，并给我一段改进意见")  # 给出题目里的原话
    while True:  # 持续接收终端输入
        user_input = input("\n你问：").strip()  # 读取用户这一句任务
        if user_input in {"退出", "quit", "exit"}:  # 几种常见结束方式
            print("再见！")  # 礼貌结束
            break  # 跳出循环
        if not user_input:  # 空回车就跳过
            continue  # 重新等待输入
        try:  # 网络或数据出错时不要把整个程序打崩
            answer = run_agent(user_input)  # 交给绑定了工具的大模型去排调用顺序
            print(f"\nAI数字员工：\n{answer}")  # 打印最终改进意见和执行结果
        except Exception as exc:  # 捕获 Key、网络、CSV 等问题
            print(f"出错了，原因是：{exc}")  # 用中文把原因说清楚
