import asyncio
import json
import logging
import re
from contextvars import ContextVar
from datetime import date, datetime, timedelta

from langchain_core.tools import tool

from app.core.embedding import embed_query
from app.db.session import AsyncSessionLocal
from app.repositories.course import CourseRepository
from app.services import study_plan as study_plan_service
from app.services.course import SEMESTER
from app.services.retrieval import hybrid_search

logger = logging.getLogger(__name__)

# 只存当前请求的用户身份，业务数据由工具自己查库
_current_user_id: ContextVar[int | None] = ContextVar("current_user_id", default=None)

_WEEKDAY_LABELS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

_WEEKDAY_MAP = {
    "周一": 1,
    "星期一": 1,
    "礼拜一": 1,
    "一": 1,
    "周二": 2,
    "星期二": 2,
    "礼拜二": 2,
    "二": 2,
    "周三": 3,
    "星期三": 3,
    "礼拜三": 3,
    "三": 3,
    "周四": 4,
    "星期四": 4,
    "礼拜四": 4,
    "四": 4,
    "周五": 5,
    "星期五": 5,
    "礼拜五": 5,
    "五": 5,
    "周六": 6,
    "星期六": 6,
    "礼拜六": 6,
    "六": 6,
    "周日": 7,
    "周天": 7,
    "星期日": 7,
    "星期天": 7,
    "日": 7,
    "天": 7,
}

# 每个时段对应的大节范围（1-2 节为第 1 大节）
_PERIOD_RANGES = {
    "上午": (1, 4),
    "下午": (5, 8),
    "晚上": (9, 10),
    "全天": (1, 10),
}


def set_current_user(user_id: int) -> None:
    _current_user_id.set(user_id)


def _require_user_id() -> int:
    user_id = _current_user_id.get()
    if user_id is None:
        raise RuntimeError("当前用户未初始化")
    return user_id


def _error(code: str, message: str) -> str:
    return json.dumps({"status": code, "message": message}, ensure_ascii=False)


def _parse_deadline(text: str) -> date | None:
    """支持 2026-11-08 / 2026/11/08 / 2026年11月8日 / 11月8日"""
    value = text.strip().replace(" ", "")

    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y年%m月%d日"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue

    match = re.fullmatch(r"(?:(\d{4})[年/-])?(\d{1,2})[月/-](\d{1,2})日?", value)
    if not match:
        return None

    year = int(match.group(1)) if match.group(1) else date.today().year
    try:
        parsed = date(year, int(match.group(2)), int(match.group(3)))
    except ValueError:
        return None

    # 没写年份且日期已经过了，按明年算
    if match.group(1) is None and parsed < date.today():
        try:
            parsed = parsed.replace(year=year + 1)
        except ValueError:
            return None

    return parsed


def _resolve_day(text: str) -> int | None:
    """把今天/明天/周四/2026-10-30 统一换算成 1-7（周一到周日）"""
    value = text.strip().replace(" ", "")
    now = datetime.now()

    if value in ("今天", "今日"):
        return now.isoweekday()
    if value in ("明天", "明日"):
        return (now + timedelta(days=1)).isoweekday()
    if value in ("昨天", "昨日"):
        return (now - timedelta(days=1)).isoweekday()
    if value in _WEEKDAY_MAP:
        return _WEEKDAY_MAP[value]

    try:
        return datetime.strptime(value, "%Y-%m-%d").isoweekday()
    except ValueError:
        return None


@tool
async def get_current_time() -> str:
    """获取当前的日期、星期和时间。

    什么时候调用：
    - 用户问“现在几点”“今天几号”“今天星期几”“现在是上午还是下午”。
    - 你在回答里需要确认“今天 / 明天 / 这周”的具体日期时。

    返回 JSON，包含 date（YYYY-MM-DD）、weekday（星期几）、time（HH:MM）、period（上午/下午/晚上/凌晨）。

    回答要求：
    - 只回答用户问到的粒度。问星期几就只说星期几，问几点就只说几点，不要顺带把年月日和秒都报出来。
    - 用口语转述，不要念字段名，也不要说“根据工具返回”。
    """
    now = datetime.now()
    hour = now.hour
    if 5 <= hour < 12:
        period = "上午"
    elif 12 <= hour < 18:
        period = "下午"
    elif 18 <= hour < 24:
        period = "晚上"
    else:
        period = "凌晨"

    return json.dumps(
        {
            "date": now.strftime("%Y-%m-%d"),
            "weekday": "星期" + "一二三四五六日"[now.weekday()],
            "time": now.strftime("%H:%M"),
            "period": period,
        },
        ensure_ascii=False,
    )


@tool
async def query_schedule(day: str = "今天", period: str = "全天", course_name: str | None = None) -> str:
    """查询当前登录用户数据库里的课表。

    什么时候调用：
    - 用户问“今天 / 明天 / 周四 / 某天有什么课”“下午有没有课”“下节课在哪上”“某门课在哪间教室”。

    参数：
    - day：要查哪一天，支持“今天”“明天”“周四”“星期四”或“2026-10-30”。
    - period：要查哪个时段，取值“上午 / 下午 / 晚上 / 全天”，默认全天。
    - course_name：只查某门课时填写课程名，查整天的课留空。

    数据来源：
    - 直接查数据库 courses 表里当前用户的课程，不要自己编造。

    输出要求：
    - 返回 JSON，courses 是课程数组；数组为空说明这个时段没有课。
    - 回答时按开始时间排序，说明第几节、课程名、教室、老师。
    """
    user_id = _require_user_id()

    target_day = _resolve_day(day)
    if target_day is None:
        return json.dumps(
            {"status": "invalid_day", "message": f"没看懂要查哪一天：{day}"},
            ensure_ascii=False,
        )

    start_section, end_section = _PERIOD_RANGES.get(period, (1, 10))

    async with AsyncSessionLocal() as session:
        courses = await CourseRepository.list_by_user(session, user_id, SEMESTER)

    result: list[dict] = []
    for course in courses:
        if course.day_of_week != target_day:
            continue
        if not (start_section <= course.start_section <= end_section):
            continue
        if course_name and course_name not in course.course_name:
            continue

        result.append(
            {
                "name": course.course_name,
                "teacher": course.teacher,
                "room": course.classroom,
                "section": (course.start_section + 1) // 2,
                "start_section": course.start_section,
                "end_section": course.end_section,
            }
        )

    weekday = _WEEKDAY_LABELS[target_day - 1] if 1 <= target_day <= 7 else "未知"
    return json.dumps(
        {
            "status": "ok",
            "day": day,
            "weekday": weekday,
            "period": period,
            "courses": result,
        },
        ensure_ascii=False,
    )


@tool
async def query_study_plan(status: str = "全部", course_name: str | None = None) -> str:
    """查询当前用户的学习计划。

    什么时候调用：
    - 用户问“我的学习计划是什么”“这周要复习什么”“某门课的计划到哪一步了”“还有哪些任务没完成”。

    参数：
    - status：筛选用，取值“全部 / 未完成 / 已完成”，默认全部。
    - course_name：只查某门课的计划时填写课程名，查全部留空。

    数据来源：
    - 直接查数据库 study_plans / study_plan_tasks 表里当前用户的数据。

    输出要求：
    - 按截止日期排序，说明计划标题、关联课程、截止日期、未完成任务。
    - 数据为空时直接说没有计划，不要编造计划或截止日期。
    """
    user_id = _require_user_id()

    async with AsyncSessionLocal() as session:
        plans = await study_plan_service.list_plans(session, user_id)

    result: list[dict] = []
    for plan in plans:
        if course_name and course_name not in (plan.course or ""):
            continue

        all_tasks = plan.tasks
        if status == "未完成":
            tasks = [task for task in all_tasks if not task.done]
        elif status == "已完成":
            tasks = [task for task in all_tasks if task.done]
        else:
            tasks = all_tasks

        if not tasks:
            continue

        result.append(
            {
                "title": plan.title,
                "course": plan.course,
                "deadline": plan.deadline.isoformat() if plan.deadline else None,
                "progress": f"{sum(1 for task in all_tasks if task.done)}/{len(all_tasks)}",
                "tasks": [{"name": task.name, "done": task.done} for task in tasks],
            }
        )

    return json.dumps({"status": "ok", "plans": result}, ensure_ascii=False)


@tool
async def create_study_plan(title: str, course_name: str, deadline: str, tasks: list[str]) -> str:
    """把已经和用户确认过的学习计划写入数据库。

    什么时候调用（非常重要）：
    - 只有用户已经明确说过“哪门课”“截止日期”，并且在你问过“就这些？还要加或改吗？”之后明确确认（“就这些 / 可以 / 没问题 / 就这样”）时才调用。
    - 信息没问全，或者用户还在补充、修改时，绝对不要调用本工具，继续用对话确认。

    参数：
    - title：计划标题，例如“数据结构期末冲刺”，不超过 100 字。
    - course_name：课程名称。
    - deadline：截止日期，格式 YYYY-MM-DD；用户说的“下个月 8 号”要先换算成具体日期。
    - tasks：任务清单，每项一句话，按执行顺序排列，3-8 条为宜。

    调用成功后，用口语告诉用户计划已保存到“学习计划”页面；你没有删除计划的权限。
    """
    user_id = _require_user_id()

    parsed_deadline = _parse_deadline(deadline)
    if parsed_deadline is None:
        return _error("invalid_deadline", f"没看懂截止日期：{deadline}，请先和用户确认具体日期")
    if parsed_deadline < date.today():
        return _error("deadline_passed", "截止日期已经过去了，请先和用户确认新的日期")

    clean_tasks = [task.strip() for task in tasks if task.strip()]
    if not clean_tasks:
        return _error("missing_tasks", "任务清单是空的，先和用户确认要复习哪些内容")

    plan_title = (title.strip() or f"{course_name.strip()}学习计划")[:100]

    async with AsyncSessionLocal() as session:
        plan = await study_plan_service.create_plan(
            session,
            user_id,
            plan_title,
            course_name.strip(),
            parsed_deadline,
            clean_tasks,
        )

    return json.dumps(
        {
            "status": "ok",
            "plan_id": plan.id,
            "title": plan.title,
            "deadline": parsed_deadline.isoformat(),
            "task_count": len(clean_tasks),
        },
        ensure_ascii=False,
    )


@tool
async def search_course_material(query: str, course_name: str | None = None) -> str:
    """在用户的课程资料里检索内容（RAG）。

    什么时候调用：
    - 用户问“课件里怎么讲的”“资料里有没有提到某个知识点”“根据上传的文档回答”。
    - 用户问学籍、休学/复学、考试、处分、培养方案、校历、申请流程等学校规定，或问“手册/文件里怎么写的”。
    - 用户上传过资料，问题可能在那份资料里出现时，先检索一次，不要凭通用知识直接回答。

    参数：
    - query：检索用的关键词或问题，尽量保留用户原话里的关键概念。
    - course_name：限定某门课的资料时填写课程名，不限定留空。

    输出要求：
    - 返回命中的资料片段和来源（文件名、切片序号）。
    - 只能依据检索结果回答，并说明出处；资料里没有的内容要说没查到，不要补。
    """
    user_id = _require_user_id()

    try:
        vector = await asyncio.to_thread(embed_query, query)
    except Exception:
        logger.exception("查询向量化失败")
        return _error("unavailable", "embedding 服务暂时不可用，请稍后再试")

    try:
        hits = await asyncio.to_thread(hybrid_search, user_id, query, vector, 5, course_name)
    except Exception:
        logger.exception("课程资料检索失败")
        return _error("unavailable", "向量库检索暂时不可用，请确认 Milvus 正常运行")

    return json.dumps({"status": "ok", "chunks": hits}, ensure_ascii=False)


TOOLS = [
    get_current_time,
    query_schedule,
    query_study_plan,
    create_study_plan,
    search_course_material,
]
TOOL_MAP = {item.name: item for item in TOOLS}
