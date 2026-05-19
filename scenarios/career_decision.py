"""Career decision scenario — v4.15 MVP scenario #1.

Defines the form-field schema + scenario metadata. The actual
compilation happens in compiler.py via the Claude API; this module
only describes what the UI should collect.
"""

from __future__ import annotations

from dataclasses import dataclass


SCENARIO_NAME = "career_decision"
DESCRIPTION = (
    "Probabilistic decision support for career-related decisions: "
    "evaluating job offers, considering role transitions, weighing "
    "stay-vs-leave at current position. Produces 3-5 future scenarios "
    "with calibrated probabilities + key uncertainty drivers + "
    "recommended evidence to collect."
)


@dataclass(frozen=True, slots=True)
class InputField:
    """Description of one form field shown in the Streamlit UI.

    `placeholder` shows greyed-out example text inside an empty input.
    `example_value` is the realistic prefill the "Try with example
    data" button writes — lets a brand-new visitor see the prediction
    flow in one click with zero typing.
    """

    key: str
    label: str
    field_type: str  # "text" | "textarea" | "select" | "number"
    hint: str = ""
    required: bool = True
    options: tuple[str, ...] = ()  # for "select"
    placeholder: str = ""
    example_value: str = ""


INPUT_FIELDS: list[InputField] = [
    InputField(
        key="current_role",
        label="你现在在做什么? / What are you doing right now?",
        field_type="textarea",
        hint=(
            "工作 / 学习 / 自由职业 / 转型中——什么都可以。一两句话就够。"
            " | Job, study, freelance, in-transition. One or two sentences."
        ),
        placeholder=(
            "例如：清华本科应届 CS 方向找工作中 / "
            "e.g., final-year CS undergrad at Tsinghua, job-hunting"
        ),
        example_value=(
            "美国硕士毕业班学生，CS / ML 方向；之前在国内一家 AI 创业公司"
            "做过 2 年算法工程师；正在找全职岗位 + 同时在做自己的开源副业项目。"
        ),
    ),
    InputField(
        key="decision_options",
        label="你在纠结的选项 (一行一个) / Options you're choosing between (one per line)",
        field_type="textarea",
        hint=(
            "3-5 个具体选择——offer 比较、留不留、回不回国、要不要 PhD 等等。"
            " | 3-5 concrete options."
        ),
        placeholder=(
            "例如:\n"
            "- 接受 Anthropic 在湾区的 ML 工程师 offer\n"
            "- 回国加入北京一家清华系创业公司\n"
            "- 自己做开源项目，先 6 个月观察"
        ),
        example_value=(
            "- 接受 Anthropic 在湾区的 ML 工程师 offer\n"
            "- 回国加入北京一家清华系初创公司做技术负责人\n"
            "- 自己做 Omytea 这个开源项目，先 6 个月观察"
        ),
    ),
    InputField(
        key="why_considering_change",
        label="为什么纠结? (越诚实越准) / What's actually driving you? (the more honest, the more accurate)",
        field_type="textarea",
        hint=(
            "收入 / 成长 / 团队氛围 / 个人生活 / 创造欲 / 想念家人 / 签证——"
            "什么真原因都可以。 | Pay / growth / team / life / family / visa / ambition."
        ),
        placeholder=(
            "例如：北美生活成本高 + 想念家人；但担心国内 996 文化和职业天花板"
        ),
        example_value=(
            "北美生活成本太高，且想念家人；但担心国内 996 文化 + 职业"
            "天花板。自己做开源项目的话现金流压力大，又怕错过 AI 时间窗口。"
        ),
    ),
    InputField(
        key="time_horizon",
        label="多久之后回来检验? / When will you come back to score this?",
        field_type="select",
        options=("3 months", "6 months", "12 months", "24 months"),
        hint=(
            "到时候你回来这个网站点 Measurement update tab，告诉系统每个选项"
            "实际发生了多少。系统用这个真实数据给你的预测做 calibration 评分。"
            " | Come back at the Measurement update tab and score each branch by how much it actually happened."
        ),
    ),
    InputField(
        key="constraints",
        label="什么限制是绕不开的? (可选) / Hard constraints? (optional)",
        field_type="textarea",
        required=False,
        hint=(
            "财务底线 / 家人 / 签证 / 健康 / 法律——任何会硬性框住选择的东西。"
            " | Hard limits — money, family, visa, health, legal."
        ),
        placeholder=(
            "例如：F-1 签证只剩 6 个月；房租 + 学贷月支出 4500 美元；"
            "家人希望我 1 年内回国"
        ),
        example_value=(
            "F-1 签证 OPT 还有 24 个月；房租 + 学贷月支出约 ¥30k；"
            "家人希望两年内回国但不强求。"
        ),
    ),
    InputField(
        key="key_unknowns",
        label="知道自己不知道、但很影响结果的事? (可选) / Big unknowns you can name? (optional)",
        field_type="textarea",
        required=False,
        hint=(
            "比如某公司的团队氛围、国内政策走向、AI 行业窗口期——这些会变成"
            "系统给你的「值得去收集证据」清单。 | These become the system's "
            "'evidence worth collecting' list."
        ),
        placeholder=(
            "例如：Anthropic ML 组真实加班节奏；清华系 startup 12 个月生存概率；"
            "自己副业能不能 12 个月达到 $3k/月"
        ),
        example_value=(
            "Anthropic ML 组真实加班节奏；清华系初创公司 12 个月生存概率；"
            "自己副业能否在 12 个月达到 $3k/月可持续现金流。"
        ),
    ),
    InputField(
        key="user_id",
        label="给自己起个昵称 / Pick a handle",
        field_type="text",
        hint=(
            "任何字符串都行，用来 6 周后回来找到这条预测。不需要注册，不收集"
            "任何 PII。 | Any string. Used to look up this prediction later. No "
            "registration, no PII collected."
        ),
        placeholder="例如：tester-xiaoming / e.g., tester-xiaoming",
        example_value="demo-tester",
    ),
]


def validate_input(form_data: dict) -> tuple[bool, str]:
    """Check that all required fields are filled.

    Returns (is_valid, error_message). Empty error_message when valid.
    """
    for field in INPUT_FIELDS:
        if field.required:
            v = form_data.get(field.key, "").strip()
            if not v:
                return False, f"Missing required field: {field.label}"
    return True, ""
