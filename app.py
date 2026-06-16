# -*- coding: utf-8 -*-
"""
学生成绩管理系统 - 基于 Streamlit + MySQL
功能：用户登录、学生管理、课程管理、成绩录入、成绩查询、成绩统计
"""

import streamlit as st
import pymysql
import pandas as pd
import hashlib
from typing import Optional, List, Tuple
from datetime import date

# ==================== 数据库连接配置 ====================

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '123456',
    'database': 'score',
    'charset': 'utf8mb4'
}


def get_connection():
    """获取数据库连接"""
    return pymysql.connect(**DB_CONFIG)


def execute_query(sql: str, params: Optional[tuple] = None) -> List[Tuple]:
    """执行查询SQL，返回结果列表"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()
    finally:
        conn.close()


def execute_update(sql: str, params: Optional[tuple] = None) -> int:
    """执行增删改SQL，自动commit，返回影响行数"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            affected = cursor.execute(sql, params)
            conn.commit()
            return affected
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


# ==================== 数据库初始化 ====================

def init_database():
    """初始化数据库和数据表"""
    conn = pymysql.connect(
        host=DB_CONFIG['host'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password'],
        charset=DB_CONFIG['charset']
    )
    try:
        with conn.cursor() as cursor:
            # 创建数据库
            cursor.execute(
                "CREATE DATABASE IF NOT EXISTS score DEFAULT CHARACTER SET utf8mb4"
            )
            cursor.execute("USE score")

            # 创建学生表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS student (
                    studentno CHAR(11) NOT NULL COMMENT '学号',
                    sname CHAR(8) NOT NULL COMMENT '姓名',
                    sex ENUM('男', '女') DEFAULT '男' COMMENT '性别',
                    birthdate DATE NOT NULL COMMENT '出生日期',
                    entrance INT(3) COMMENT '入学成绩',
                    phone VARCHAR(12) NOT NULL COMMENT '电话',
                    QQ VARCHAR(18) NOT NULL COMMENT 'QQ号',
                    PRIMARY KEY (studentno)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学生表'
            """)

            # 创建课程表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS course (
                    courseno CHAR(6) NOT NULL COMMENT '课程号',
                    cname VARCHAR(20) NOT NULL COMMENT '课程名',
                    type CHAR(4) NOT NULL COMMENT '课程类型',
                    credit INT(1) NOT NULL COMMENT '学分',
                    PRIMARY KEY (courseno)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='课程表'
            """)

            # 创建成绩表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS score (
                    studentno CHAR(11) NOT NULL COMMENT '学号',
                    courseno CHAR(6) NOT NULL COMMENT '课程号',
                    daily FLOAT(3,1) DEFAULT 0.0 COMMENT '平时成绩',
                    final FLOAT(3,1) DEFAULT 0.0 COMMENT '期末成绩',
                    PRIMARY KEY (studentno, courseno),
                    FOREIGN KEY (studentno) REFERENCES student(studentno)
                        ON DELETE CASCADE ON UPDATE CASCADE,
                    FOREIGN KEY (courseno) REFERENCES course(courseno)
                        ON DELETE CASCADE ON UPDATE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='成绩表'
            """)

            # 创建用户表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    username VARCHAR(20) NOT NULL COMMENT '用户名',
                    password VARCHAR(32) NOT NULL COMMENT '密码',
                    role ENUM('admin', 'teacher', 'student') DEFAULT 'student' COMMENT '角色',
                    PRIMARY KEY (username)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表'
            """)

            # 插入默认管理员账号（密码：admin123）
            cursor.execute("""
                INSERT IGNORE INTO users (username, password, role)
                VALUES ('admin', %s, 'admin')
            """, (hashlib.md5('admin123'.encode()).hexdigest(),))
            conn.commit()
    finally:
        conn.close()


def md5_hash(text: str) -> str:
    """对文本进行MD5加密"""
    return hashlib.md5(text.encode()).hexdigest()


# ==================== 用户登录 ====================

def login_page():
    """用户登录页面"""
    st.title("📖 学生成绩管理系统")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### 🔐 用户登录")
        with st.form("login_form"):
            username = st.text_input("用户名", placeholder="请输入用户名")
            password = st.text_input("密码", placeholder="请输入密码", type="password")
            submitted = st.form_submit_button("登录", use_container_width=True)

            if submitted:
                if not username or not password:
                    st.error("用户名和密码不能为空！")
                else:
                    # 查询用户
                    result = execute_query(
                        "SELECT password, role FROM users WHERE username=%s",
                        (username,)
                    )
                    if result:
                        stored_pwd, role = result[0]
                        if stored_pwd == md5_hash(password):
                            st.session_state['logged_in'] = True
                            st.session_state['username'] = username
                            st.session_state['role'] = role
                            st.success("登录成功！")
                            st.rerun()
                        else:
                            st.error("密码错误！")
                    else:
                        st.error("用户不存在！")

        st.divider()
        st.caption("默认管理员账号：admin / admin123")
        st.caption("可通过【用户管理】添加新用户（需管理员权限）")


# ==================== 用户管理 ====================

def page_user_manage():
    """用户管理页面（仅管理员可见）"""
    if st.session_state.get('role') != 'admin':
        st.warning("仅管理员可访问用户管理功能！")
        return

    st.subheader("👤 用户管理")

    tab1, tab2 = st.tabs(["查看用户", "添加用户"])

    # ---- 查看用户 ----
    with tab1:
        users = execute_query(
            "SELECT username, role FROM users ORDER BY username"
        )
        if users:
            df = pd.DataFrame(users, columns=["用户名", "角色"])
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.caption(f"共 {len(users)} 个用户")
        else:
            st.info("暂无用户数据。")

    # ---- 添加用户 ----
    with tab2:
        with st.form("add_user_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                new_username = st.text_input("用户名 *", placeholder="请输入用户名")
                new_password = st.text_input("密码 *", placeholder="请输入密码", type="password")
            with col2:
                new_role = st.selectbox("角色 *", ["student", "teacher", "admin"])

            submitted = st.form_submit_button("✅ 添加用户", use_container_width=True)
            if submitted:
                if not new_username or not new_password:
                    st.error("用户名和密码为必填项！")
                else:
                    try:
                        execute_update(
                            "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
                            (new_username, md5_hash(new_password), new_role)
                        )
                        st.success(f"用户 {new_username} 添加成功！")
                    except pymysql.err.IntegrityError:
                        st.error(f"用户名 {new_username} 已存在！")
                    except Exception as e:
                        st.error(f"添加失败：{e}")


# ==================== 学生管理 ====================

def page_student_manage():
    """学生管理页面"""
    st.subheader("📋 学生管理")

    tab1, tab2, tab3, tab4 = st.tabs(["查看学生", "添加学生", "修改学生", "删除学生"])

    # ---- 查看学生 ----
    with tab1:
        students = execute_query(
            "SELECT studentno, sname, sex, birthdate, entrance, phone, QQ FROM student ORDER BY studentno"
        )
        if students:
            df = pd.DataFrame(
                students,
                columns=["学号", "姓名", "性别", "出生日期", "入学成绩", "电话", "QQ"]
            )
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.caption(f"共 {len(students)} 名学生")
        else:
            st.info("暂无学生数据，请先添加学生。")

    # ---- 添加学生 ----
    with tab2:
        with st.form("add_student_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                studentno = st.text_input("学号 *", placeholder="11位字符，如：20210001001")
                sname = st.text_input("姓名 *", placeholder="请输入姓名（最多8个字符）")
                sex = st.selectbox("性别 *", ["男", "女"])
                birthdate = st.date_input(
                    "出生日期 *",
                    value=date(2000, 1, 1),
                    min_value=date(1980, 1, 1),
                    max_value=date.today(),
                    format="YYYY-MM-DD"
                )
            with col2:
                entrance = st.number_input(
                    "入学成绩", min_value=0, max_value=750, value=0, step=1,
                    help="选填，满分750"
                )
                phone = st.text_input("电话 *", placeholder="请输入电话号码")
                qq = st.text_input("QQ号 *", placeholder="请输入QQ号")

            submitted = st.form_submit_button("✅ 添加学生", use_container_width=True)
            if submitted:
                if not studentno or not sname or not phone or not qq:
                    st.error("学号、姓名、电话、QQ号为必填项！")
                elif len(studentno) > 11:
                    st.error("学号不能超过11位字符！")
                elif len(sname) > 8:
                    st.error("姓名不能超过8个字符！")
                else:
                    try:
                        entrance_val = entrance if entrance > 0 else None
                        execute_update(
                            """INSERT INTO student (studentno, sname, sex, birthdate, entrance, phone, QQ)
                               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                            (studentno, sname, sex, birthdate, entrance_val, phone, qq)
                        )
                        st.success(f"学生 {sname}({studentno}) 添加成功！")
                    except pymysql.err.IntegrityError:
                        st.error(f"学号 {studentno} 已存在，请勿重复添加！")
                    except Exception as e:
                        st.error(f"添加失败：{e}")

    # ---- 修改学生 ----
    with tab3:
        students = execute_query("SELECT studentno, sname FROM student ORDER BY studentno")
        if not students:
            st.info("暂无学生数据")
        else:
            student_dict = {f"{s[0]} - {s[1]}": s[0] for s in students}
            selected = st.selectbox(
                "选择要修改的学生", list(student_dict.keys()),
                key="edit_student_select"
            )
            sno = student_dict[selected]

            # 获取当前学生信息
            current = execute_query(
                "SELECT sname, sex, birthdate, entrance, phone, QQ FROM student WHERE studentno=%s",
                (sno,)
            )
            if current:
                cur_name, cur_sex, cur_birth, cur_entrance, cur_phone, cur_qq = current[0]

                with st.form("edit_student_form", clear_on_submit=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        new_name = st.text_input("姓名 *", value=cur_name, max_chars=8)
                        new_sex = st.selectbox(
                            "性别 *", ["男", "女"],
                            index=0 if cur_sex == "男" else 1
                        )
                        new_birth = st.date_input(
                            "出生日期 *",
                            value=cur_birth,
                            min_value=date(1980, 1, 1),
                            max_value=date.today(),
                            format="YYYY-MM-DD"
                        )
                    with col2:
                        new_entrance = st.number_input(
                            "入学成绩", min_value=0, max_value=999,
                            value=int(cur_entrance) if cur_entrance else 0, step=1
                        )
                        new_phone = st.text_input("电话 *", value=cur_phone)
                        new_qq = st.text_input("QQ号 *", value=cur_qq)

                    submitted = st.form_submit_button("✏️ 保存修改", use_container_width=True)
                    if submitted:
                        if not new_name or not new_phone or not new_qq:
                            st.error("姓名、电话、QQ号不能为空！")
                        else:
                            try:
                                entrance_val = new_entrance if new_entrance > 0 else None
                                execute_update(
                                    """UPDATE student
                                       SET sname=%s, sex=%s, birthdate=%s, entrance=%s, phone=%s, QQ=%s
                                       WHERE studentno=%s""",
                                    (new_name, new_sex, new_birth, entrance_val, new_phone, new_qq, sno)
                                )
                                st.success(f"学生 {new_name} 信息修改成功！")
                            except Exception as e:
                                st.error(f"修改失败：{e}")

    # ---- 删除学生 ----
    with tab4:
        students = execute_query("SELECT studentno, sname FROM student ORDER BY studentno")
        if not students:
            st.info("暂无学生数据")
        else:
            student_dict = {f"{s[0]} - {s[1]}": s[0] for s in students}
            selected = st.selectbox(
                "选择要删除的学生", list(student_dict.keys()),
                key="delete_student_select"
            )
            sno = student_dict[selected]

            st.warning(
                f"⚠️ 删除学生 **{selected}** 将同时删除该生的所有成绩记录，此操作不可撤销！"
            )

            if st.button("🗑️ 确认删除", key="confirm_delete_student", use_container_width=True):
                try:
                    execute_update("DELETE FROM student WHERE studentno=%s", (sno,))
                    st.success(f"学生 {selected} 已删除！")
                except Exception as e:
                    st.error(f"删除失败：{e}")


# ==================== 课程管理 ====================

def page_course_manage():
    """课程管理页面"""
    st.subheader("📚 课程管理")

    tab1, tab2, tab3, tab4 = st.tabs(["查看课程", "添加课程", "修改课程", "删除课程"])

    # ---- 查看课程 ----
    with tab1:
        courses = execute_query(
            "SELECT courseno, cname, type, credit FROM course ORDER BY courseno"
        )
        if courses:
            df = pd.DataFrame(courses, columns=["课程号", "课程名", "课程类型", "学分"])
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.caption(f"共 {len(courses)} 门课程")
        else:
            st.info("暂无课程数据，请先添加课程。")

    # ---- 添加课程 ----
    with tab2:
        with st.form("add_course_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                courseno = st.text_input("课程号 *", placeholder="6位字符，如：CS1001")
                cname = st.text_input("课程名 *", placeholder="请输入课程名称")
            with col2:
                course_type = st.selectbox(
                    "课程类型 *",
                    ["必修", "选修", "公选", "实践"],
                    help="请选择课程类型"
                )
                credit = st.number_input(
                    "学分 *", min_value=1, max_value=10, value=3, step=1
                )

            submitted = st.form_submit_button("✅ 添加课程", use_container_width=True)
            if submitted:
                if not courseno or not cname:
                    st.error("课程号和课程名为必填项！")
                elif len(courseno) > 6:
                    st.error("课程号不能超过6位字符！")
                else:
                    try:
                        execute_update(
                            "INSERT INTO course (courseno, cname, type, credit) VALUES (%s, %s, %s, %s)",
                            (courseno, cname, course_type, credit)
                        )
                        st.success(f"课程「{cname}」添加成功！")
                    except pymysql.err.IntegrityError:
                        st.error(f"课程号 {courseno} 已存在！")
                    except Exception as e:
                        st.error(f"添加失败：{e}")

    # ---- 修改课程 ----
    with tab3:
        courses = execute_query("SELECT courseno, cname FROM course ORDER BY courseno")
        if not courses:
            st.info("暂无课程数据")
        else:
            course_dict = {f"{c[0]} - {c[1]}": c[0] for c in courses}
            selected = st.selectbox(
                "选择要修改的课程", list(course_dict.keys()),
                key="edit_course_select"
            )
            cno = course_dict[selected]

            current = execute_query(
                "SELECT cname, type, credit FROM course WHERE courseno=%s", (cno,)
            )
            if current:
                cur_name, cur_type, cur_credit = current[0]
                # 课程类型在表单中的索引
                type_options = ["必修", "选修", "公选", "实践"]
                type_index = type_options.index(cur_type) if cur_type in type_options else 0

                with st.form("edit_course_form", clear_on_submit=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        new_name = st.text_input("课程名 *", value=cur_name)
                        new_type = st.selectbox(
                            "课程类型 *", type_options, index=type_index
                        )
                    with col2:
                        new_credit = st.number_input(
                            "学分 *", min_value=1, max_value=10,
                            value=int(cur_credit), step=1
                        )

                    submitted = st.form_submit_button("✏️ 保存修改", use_container_width=True)
                    if submitted:
                        if not new_name:
                            st.error("课程名不能为空！")
                        else:
                            try:
                                execute_update(
                                    """UPDATE course SET cname=%s, type=%s, credit=%s
                                       WHERE courseno=%s""",
                                    (new_name, new_type, new_credit, cno)
                                )
                                st.success(f"课程「{new_name}」信息修改成功！")
                            except Exception as e:
                                st.error(f"修改失败：{e}")

    # ---- 删除课程 ----
    with tab4:
        courses = execute_query("SELECT courseno, cname FROM course ORDER BY courseno")
        if not courses:
            st.info("暂无课程数据")
        else:
            course_dict = {f"{c[0]} - {c[1]}": c[0] for c in courses}
            selected = st.selectbox(
                "选择要删除的课程", list(course_dict.keys()),
                key="delete_course_select"
            )
            cno = course_dict[selected]

            st.warning(
                f"⚠️ 删除课程 **{selected}** 将同时删除该课程的所有成绩记录，此操作不可撤销！"
            )

            if st.button("🗑️ 确认删除", key="confirm_delete_course", use_container_width=True):
                try:
                    execute_update("DELETE FROM course WHERE courseno=%s", (cno,))
                    st.success(f"课程 {selected} 已删除！")
                except Exception as e:
                    st.error(f"删除失败：{e}")


# ==================== 成绩录入 ====================

def page_score_input():
    """成绩录入页面"""
    st.subheader("📝 成绩录入")

    # 获取学生和课程列表
    students = execute_query(
        "SELECT studentno, sname FROM student ORDER BY studentno"
    )
    courses = execute_query(
        "SELECT courseno, cname FROM course ORDER BY courseno"
    )

    if not students:
        st.warning("请先在【学生管理】中添加学生数据。")
        return
    if not courses:
        st.warning("请先在【课程管理】中添加课程数据。")
        return

    with st.form("score_input_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            student_options = {f"{s[0]} - {s[1]}": s[0] for s in students}
            selected_student = st.selectbox("选择学生 *", list(student_options.keys()))
            sno = student_options[selected_student]
        with col2:
            course_options = {f"{c[0]} - {c[1]}": c[0] for c in courses}
            selected_course = st.selectbox("选择课程 *", list(course_options.keys()))
            cno = course_options[selected_course]

        col3, col4 = st.columns(2)
        with col3:
            daily = st.number_input(
                "平时成绩", min_value=0.0, max_value=100.0, value=0.0, step=0.5,
                help="平时成绩，满分100分"
            )
        with col4:
            final = st.number_input(
                "期末成绩", min_value=0.0, max_value=100.0, value=0.0, step=0.5,
                help="期末成绩，满分100分"
            )

        # 计算总评成绩预览
        total_score = daily * 0.3 + final * 0.7
        st.info(f"📊 总评成绩预览：**{total_score:.1f}**（平时30% + 期末70%）")

        submitted = st.form_submit_button("💾 保存成绩", use_container_width=True)
        if submitted:
            try:
                execute_update(
                    """INSERT INTO score (studentno, courseno, daily, final)
                       VALUES (%s, %s, %s, %s)
                       ON DUPLICATE KEY UPDATE daily=%s, final=%s""",
                    (sno, cno, daily, final, daily, final)
                )
                st.success("成绩保存成功！")
            except pymysql.err.IntegrityError as e:
                st.error(f"数据完整性错误：{e}")
            except Exception as e:
                st.error(f"保存失败：{e}")

    # 展示已有成绩
    st.divider()
    st.caption("已有成绩记录预览（最近20条）：")
    records = execute_query("""
        SELECT s.sname AS 姓名, s.studentno AS 学号, c.cname AS 课程,
               sc.daily AS 平时成绩, sc.final AS 期末成绩,
               ROUND(sc.daily * 0.3 + sc.final * 0.7, 1) AS 总评成绩
        FROM score sc
        JOIN student s ON sc.studentno = s.studentno
        JOIN course c ON sc.courseno = c.courseno
        ORDER BY sc.studentno DESC
        LIMIT 20
    """)
    if records:
        df = pd.DataFrame(
            records,
            columns=["姓名", "学号", "课程", "平时成绩", "期末成绩", "总评成绩"]
        )
        st.dataframe(df, use_container_width=True, hide_index=True)


# ==================== 成绩查询 ====================

def page_score_query():
    """成绩查询页面"""
    st.subheader("🔍 成绩查询")

    students = execute_query(
        "SELECT studentno, sname FROM student ORDER BY studentno"
    )

    if not students:
        st.info("暂无学生数据")
        return

    student_options = {f"{s[0]} - {s[1]}": s[0] for s in students}
    selected_student = st.selectbox("选择要查询的学生", list(student_options.keys()))
    sno = student_options[selected_student]

    # 查询该生的所有成绩
    records = execute_query("""
        SELECT c.cname AS 课程名称, c.type AS 课程类型, c.credit AS 学分,
               sc.daily AS 平时成绩, sc.final AS 期末成绩,
               ROUND(sc.daily * 0.3 + sc.final * 0.7, 1) AS 总评成绩
        FROM score sc
        JOIN course c ON sc.courseno = c.courseno
        WHERE sc.studentno = %s
        ORDER BY c.courseno
    """, (sno,))

    if records:
        df = pd.DataFrame(
            records,
            columns=["课程名称", "课程类型", "学分", "平时成绩", "期末成绩", "总评成绩"]
        )

        # 计算汇总统计
        total_scores = [float(r[5]) for r in records]  # 总评成绩列
        avg_score = sum(total_scores) / len(total_scores)
        total_credits = sum(int(r[2]) for r in records)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("课程数", len(records))
        with col2:
            st.metric("平均总评", f"{avg_score:.1f}")
        with col3:
            st.metric("总学分", total_credits)
        with col4:
            st.metric("最高总评", f"{max(total_scores):.1f}")

        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("该学生暂无成绩记录。")


# ==================== 成绩统计 ====================

def page_score_statistics():
    """成绩统计页面"""
    st.subheader("📊 成绩统计")

    # 查询每门课程的统计信息（按总评成绩 = 平时*0.3 + 期末*0.7）
    stats = execute_query("""
        SELECT
            c.cname AS 课程名称,
            c.type AS 课程类型,
            COUNT(sc.studentno) AS 选课人数,
            ROUND(AVG(sc.daily * 0.3 + sc.final * 0.7), 1) AS 平均总评,
            ROUND(MAX(sc.daily * 0.3 + sc.final * 0.7), 1) AS 最高总评,
            ROUND(MIN(sc.daily * 0.3 + sc.final * 0.7), 1) AS 最低总评,
            ROUND(
                SUM(CASE WHEN (sc.daily * 0.3 + sc.final * 0.7) >= 60 THEN 1 ELSE 0 END)
                / COUNT(*) * 100, 1
            ) AS 及格率
        FROM course c
        LEFT JOIN score sc ON c.courseno = sc.courseno
        GROUP BY c.courseno, c.cname, c.type
        ORDER BY c.courseno
    """)

    if stats:
        df = pd.DataFrame(
            stats,
            columns=["课程名称", "课程类型", "选课人数", "平均总评", "最高总评", "最低总评", "及格率(%)"]
        )
        st.dataframe(df, use_container_width=True, hide_index=True)

        # 全校汇总
        st.divider()
        st.caption("全校成绩汇总：")
        total_stats = execute_query("""
            SELECT
                COUNT(DISTINCT studentno) AS 参评人数,
                ROUND(AVG(daily * 0.3 + final * 0.7), 1) AS 总平均分,
                ROUND(
                    SUM(CASE WHEN (daily * 0.3 + final * 0.7) >= 60 THEN 1 ELSE 0 END)
                    / COUNT(*) * 100, 1
                ) AS 总及格率
            FROM score
        """)
        if total_stats and total_stats[0][0]:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("参评学生数", int(total_stats[0][0]))
            with col2:
                st.metric("总平均分", f"{float(total_stats[0][1]):.1f}")
            with col3:
                st.metric("总及格率", f"{float(total_stats[0][2]):.1f}%")
    else:
        st.info("暂无成绩数据可供统计。")


# ==================== 主程序 ====================

def main():
    """主程序入口"""
    # 页面配置（必须是第一个 Streamlit 命令）
    st.set_page_config(
        page_title="学生成绩管理系统",
        page_icon="📖",
        layout="wide"
    )

    # 初始化数据库
    try:
        init_database()
    except Exception as e:
        st.error(f"数据库初始化失败，请检查 MySQL 服务是否启动：{e}")
        st.stop()

    # 检查登录状态
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if not st.session_state['logged_in']:
        login_page()
        return

    # ==================== 已登录：显示主界面 ====================

    st.title("📖 学生成绩管理系统")

    # 侧边栏
    st.sidebar.title("导航菜单")

    # 构建菜单列表（管理员额外显示用户管理）
    menu_items = ["学生管理", "课程管理", "成绩录入", "成绩查询", "成绩统计"]
    if st.session_state.get('role') == 'admin':
        menu_items.append("用户管理")

    menu = st.sidebar.radio("请选择功能模块：", menu_items, index=0)

    st.sidebar.divider()
    st.sidebar.caption(f"当前用户：{st.session_state.get('username', '')}")
    st.sidebar.caption(f"角色：{st.session_state.get('role', '')}")
    st.sidebar.caption("数据库：score@localhost")

    # 退出登录按钮
    if st.sidebar.button("🚪 退出登录", use_container_width=True):
        st.session_state['logged_in'] = False
        st.session_state['username'] = ''
        st.session_state['role'] = ''
        st.rerun()

    # 根据菜单选择渲染对应页面
    if menu == "学生管理":
        page_student_manage()
    elif menu == "课程管理":
        page_course_manage()
    elif menu == "成绩录入":
        page_score_input()
    elif menu == "成绩查询":
        page_score_query()
    elif menu == "成绩统计":
        page_score_statistics()
    elif menu == "用户管理":
        page_user_manage()


if __name__ == "__main__":
    main()
