"""制造业 AI 数字员工的 Streamlit 网页版：给老板演示查数、算达成率、自动改状态。"""

import sys  # 用来把当前文件夹加入 Python 搜索路径，保证能导入旁边的 digital_worker.py
from pathlib import Path  # 用来定位本文件所在目录

import pandas as pd  # 用来给表格做一点颜色高亮，让“预警”一眼能看出来
import streamlit as st  # 用来做网页：标题、输入框、按钮、表格、提示条

CURRENT_DIR = Path(__file__).resolve().parent  # 拿到 app_worker.py 所在文件夹
if str(CURRENT_DIR) not in sys.path:  # 如果这个文件夹还不在搜索路径里
    sys.path.insert(0, str(CURRENT_DIR))  # 加进去，后面才能 from digital_worker import ...

from digital_worker import (  # 直接复用原来终端脚本里的能力，不要把 pandas 工具再抄一遍
    CSV_PATH,  # 工单 CSV 的真实路径，网页读的就是这份文件
    calc_efficiency,  # 计算某条线达成率的 pandas 工具
    get_data,  # 读取某条线工单数据的 pandas 工具
    load_work_data,  # 读 CSV 成表格，执行完任务后刷新左侧数据用
    run_agent,  # 已经绑定了三个工具的 DeepSeek Agent，模型自己决定调用顺序
    update_status,  # 修改某条线状态并写回 CSV 的 pandas 工具
)


_ = (get_data, calc_efficiency, update_status)  # 明确复用这三个工具，避免有人误以为网页版另写了一套


DEFAULT_INSTRUCTION = (  # 老板一打开页面就能看到的演示指令，点按钮就能跑
    "帮我查一下A生产线的数据，计算一下达成率，如果低于80%就自动把状态改成预警，并给我一段改进意见"
)


def describe_tool_step(tool_name: str, args: dict) -> str:
    """把模型调用的工具名，翻译成老板能看懂的中文思考过程。"""
    line_name = args.get("line_name", "")  # 模型这次针对哪条生产线
    if tool_name == "get_data":  # 第一个工具：读工单
        return f"正在读取数据...（生产线：{line_name}）"  # 对应演示要求里的“正在读取数据...”
    if tool_name == "calc_efficiency":  # 第二个工具：算达成率
        return f"正在计算达成率...（生产线：{line_name}）"  # 对应“正在计算达成率...”
    if tool_name == "update_status":  # 第三个工具：改状态
        new_status = str(args.get("new_status", ""))  # 模型准备改成什么状态
        if "预警" in new_status:  # 演示场景：低于 80% 才改成预警
            return "达成率低于80%，执行修改操作..."  # 对应“达成率低于80%，执行修改操作...”
        return f"正在把生产线 {line_name} 的状态改为“{new_status}”..."  # 其他状态也给一句人话
    return f"正在调用工具：{tool_name}..."  # 万一以后加了新工具，也不至于没字显示


def highlight_status(row: pd.Series) -> list[str]:
    """给“预警”行涂浅红，给“停线”行涂浅灰，方便老板扫一眼看出异常。"""
    status = str(row.get("状态", ""))  # 取出这一行的状态文字
    if status == "预警":  # 预警是这次演示的重点
        return ["background-color: #ffe4e6; color: #9f1239;"] * len(row)  # 整行浅红
    if status == "停线":  # 停线也很严重，单独标出来
        return ["background-color: #f3f4f6; color: #374151;"] * len(row)  # 整行浅灰
    if status == "完成":  # 完成用淡绿，表示这张工单已经达标
        return ["background-color: #dcfce7; color: #166534;"] * len(row)  # 整行淡绿
    return [""] * len(row)  # 正常状态不染色


def inject_page_style() -> None:
    """加一点点页面样式，让演示看起来像决策看板，而不是默认白页。"""
    st.markdown(  # 用 Markdown 塞一段 CSS，只改观感，不改业务
        """
        <style>
        .stApp {background: linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%);}
        .hero-card {
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 16px;
            padding: 18px 22px;
            margin-bottom: 12px;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
        }
        </style>
        """,
        unsafe_allow_html=True,  # Streamlit 默认会拦住 HTML，这里只用来美化页面
    )


st.set_page_config(  # 网页标签和布局先设好，老板打开就是宽屏看板
    page_title="制造业 AI 数字员工",  # 浏览器标签上的名字
    page_icon="🏭",  # 标签小图标
    layout="wide",  # 宽屏，左边表格右边建议才摆得下
)
inject_page_style()  # 套上浅色看板背景

st.title("🏭 制造业 AI 数字员工")  # 首页标题，按演示要求原样显示
st.caption("决策辅助系统 · 查工单、算达成率、低产自动预警，并把改进意见直接交给管理层。")  # 副标题，一句话讲清价值

if "last_answer" not in st.session_state:  # 第一次打开页面时，还没有 AI 回复
    st.session_state.last_answer = ""  # 先放空字符串，避免后面取不到
if "last_steps" not in st.session_state:  # 思考过程同样先初始化
    st.session_state.last_steps = []  # 用列表记下每一步，刷新页面也不会丢

st.markdown('<div class="hero-card">', unsafe_allow_html=True)  # 指令区外面包一层卡片
instruction = st.text_area(  # 业务指令输入框：默认填好演示原话，老板也能改
    "业务指令",  # 输入框上方的小标题
    value=DEFAULT_INSTRUCTION,  # 默认就是要求里的那句 A 线任务
    height=100,  # 指令比较长，用多行输入框更适合演示
)
run_clicked = st.button("执行任务", type="primary")  # 点了才调用大模型，避免一打字就反复请求
st.markdown("</div>", unsafe_allow_html=True)  # 卡片结束

if run_clicked:  # 只有按下“执行任务”，才开始跑 Agent
    try:  # 核心逻辑全部包起来，出错就在网页上红字提示，不要把页面打崩
        if not instruction.strip():  # 指令被清空时不要白白调接口
            raise ValueError("请先填写业务指令，再点击执行任务。")  # 给一个好懂的中文原因

        with st.status("AI正在思考并调用工具...", expanded=True) as status_box:  # 转圈 + 展示思考过程
            collected_steps = []  # 把每一步中文说明存下来，任务结束后还能再看

            def on_step(tool_name: str, args: dict, result: str) -> None:  # Agent 每调一次工具就进这里
                message = describe_tool_step(tool_name, args)  # 把工具名翻成老板能看懂的话
                collected_steps.append(message)  # 记进列表
                st.write(message)  # 立刻显示在状态框里，例如“正在读取数据...”
                preview = str(result).replace("\n", " | ")  # 工具原始返回太长，压成一行预览
                st.caption(preview[:180] + ("..." if len(preview) > 180 else ""))  # 让人看到确实读到了数

            answer = run_agent(instruction.strip(), on_step=on_step)  # 复用原脚本：DeepSeek 自己决定三个工具的顺序
            status_box.update(label="任务已完成", state="complete")  # 把转圈改成完成勾

        st.session_state.last_answer = answer  # 把最终改进意见存进会话，方便左右分栏展示
        st.session_state.last_steps = collected_steps  # 思考过程也存一份
    except Exception as exc:  # Key 没了、网络断了、CSV 坏了，都会走到这里
        st.error(f"出错了：{exc}")  # 用红色提示，页面继续能用
        st.stop()  # 这次执行失败，就不要再往下画可能过期的结果

left_col, right_col = st.columns([1.25, 1], gap="large")  # 左边看数据，右边看 AI 建议

with left_col:  # 左侧：给老板看真实 CSV，证明状态真的改了
    st.subheader("工单实时数据")  # 小标题
    st.caption(f"数据来源：{CSV_PATH.name}（修改会立刻写回这份文件）")  # 强调不是假数据，是本地表
    try:  # 读表单独包一层，避免 CSV 损坏时连右侧建议都出不来
        work_df = load_work_data()  # 再次读取，拿到 Agent 改状态之后的最新数据
        warning_count = int((work_df["状态"].astype(str) == "预警").sum())  # 统计当前有多少条预警
        metric_a, metric_b, metric_c = st.columns(3)  # 三个数字卡片，演示时很有画面
        metric_a.metric("工单总数", len(work_df))  # 一共多少张工单
        metric_b.metric("预警条数", warning_count)  # 预警有没有增加，老板最关心这个
        metric_c.metric("生产线", work_df["生产线"].nunique())  # 现在覆盖几条线
        st.dataframe(  # 按要求用表格展示修改后的 work_data.csv
            work_df.style.apply(highlight_status, axis=1),  # 预警行标红，完成行标绿
            use_container_width=True,  # 表格拉满左栏宽度
            hide_index=True,  # 隐藏 pandas 行号，看起来更像业务表
            height=520,  # 固定高度，49 条数据可以滚动看
        )
    except Exception as exc:  # 读表失败也用红字，不要崩溃
        st.error(f"读取工单表失败：{exc}")  # 告诉老板/演示的人文件出了什么问题

with right_col:  # 右侧：展示大模型给出的专业改进意见
    st.subheader("AI 改进意见")  # 小标题
    if st.session_state.last_steps:  # 如果刚才跑过任务，把思考过程再列一遍
        with st.expander("查看 AI 思考过程", expanded=False):  # 默认收起，避免挡住建议正文
            for index, step in enumerate(st.session_state.last_steps, start=1):  # 按调用顺序展示
                st.write(f"{index}. {step}")  # 例如 1. 正在读取数据...
    if st.session_state.last_answer:  # 有最终回复才用绿色成功框展示
        st.success(st.session_state.last_answer)  # 按要求用 st.success 展示改进意见
    else:  # 还没点执行时，右侧给一句引导
        st.info("点击左侧的“执行任务”后，这里会显示数字员工给出的改进意见。")  # 空状态提示
