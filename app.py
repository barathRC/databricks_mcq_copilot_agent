# app.py
import json
import random
import time
from pathlib import Path
from typing import Dict, Any, List

import streamlit as st

from state_utils import get_session, save_session

QUESTION_BANK_FILE = Path("question_bank.json")

EXAM_OPTIONS = {
    "Databricks Certified Data Engineer Associate": "associate",
    "Databricks Certified Data Engineer Professional": "professional"
}


# ------------- Question Bank Loader -----------------

@st.cache_data
def load_questions() -> Dict[str, Dict[str, Any]]:
    data = json.loads(QUESTION_BANK_FILE.read_text())
    return {q["question_id"]: q for q in data}


# ------------- Session State Initialization ----------

def init_app():
    if "initialized" not in st.session_state:
        st.session_state.initialized = True
        st.session_state.username = ""
        st.session_state.questions = load_questions()
        st.session_state.session = None
        st.session_state.current_index = 0
        st.session_state.last_tick = time.time()
        st.session_state.show_summary = False

        st.session_state.exam_label = list(EXAM_OPTIONS.keys())[0]
        st.session_state.exam_code = EXAM_OPTIONS[st.session_state.exam_label]


# ------------- New Test Session ----------------------

def create_new_session(username: str, exam_label: str, exam_code: str, shuffle: bool = True) -> Dict[str, Any]:
    questions = st.session_state.questions

    # Filter questions belonging to this exam by difficulty
    qids = [qid for qid, q in questions.items() if q.get("difficulty") == exam_code]

    if not qids:
        raise ValueError(f"No questions found for exam type: {exam_label} (difficulty={exam_code})")

    if shuffle:
        random.shuffle(qids)
    else:
        qids.sort()

    session = {
        "username": username,
        "exam_code": exam_code,
        "exam_label": exam_label,
        "question_order": qids,
        "responses": {
            qid: {"choice": None, "correct": None, "review": False}
            for qid in qids
        },
        "elapsed_seconds": 0,
        "completed": False,
        "started_at": time.time()
    }
    return session


# ------------- Timer & Summary -----------------------

def update_timer():
    session = st.session_state.session
    if not session:
        return

    now = time.time()
    delta = now - st.session_state.last_tick
    if delta > 0:
        session["elapsed_seconds"] += int(delta)
        st.session_state.last_tick = now
        save_session(session["username"], session["exam_code"], session)


def compute_summary(session: Dict[str, Any]) -> Dict[str, Any]:
    responses = session["responses"]
    attempted = 0
    correct = 0
    for r in responses.values():
        if r["choice"]:
            attempted += 1
            if r["correct"]:
                correct += 1
    incorrect = attempted - correct
    percent = (correct / attempted * 100.0) if attempted > 0 else 0.0
    return {
        "attempted": attempted,
        "correct": correct,
        "incorrect": incorrect,
        "percent": percent
    }


def format_time(seconds: int) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


# ------------- Main App ------------------------------

def main():
    st.set_page_config(
        page_title="Databricks Data Engineer – MCQ Assessment Agent",
        layout="wide"
    )

    init_app()
    questions = st.session_state.questions

    st.title("🧠 Databricks Data Engineer – Intelligent MCQ Assessment Agent")

    # -------- Sidebar: User / Session Controls --------
    with st.sidebar:
        st.header("User / Exam Selection")

        st.session_state.username = st.text_input(
            "Enter your name or ID",
            value=st.session_state.username,
            placeholder="e.g., barath.r"
        )

        # Exam selector
        st.session_state.exam_label = st.selectbox(
            "Select Exam",
            options=list(EXAM_OPTIONS.keys())
        )
        st.session_state.exam_code = EXAM_OPTIONS[st.session_state.exam_label]

        shuffle_opt = st.checkbox("Shuffle questions", value=True)

        col1, col2 = st.columns(2)
        if st.session_state.username.strip():
            if col1.button("Start New Test", use_container_width=True):
                try:
                    session = create_new_session(
                        st.session_state.username,
                        st.session_state.exam_label,
                        st.session_state.exam_code,
                        shuffle=shuffle_opt
                    )
                except ValueError as e:
                    st.error(str(e))
                else:
                    st.session_state.session = session
                    st.session_state.current_index = 0
                    st.session_state.last_tick = time.time()
                    st.session_state.show_summary = False
                    save_session(session["username"], session["exam_code"], session)
                    st.success(f"New test started for: {session['exam_label']}")

            if col2.button("Resume Last Test", use_container_width=True):
                saved = get_session(st.session_state.username, st.session_state.exam_code)
                if saved:
                    st.session_state.session = saved
                    st.session_state.current_index = 0
                    st.session_state.last_tick = time.time()
                    st.session_state.show_summary = saved.get("completed", False)
                    st.success(f"Session restored for: {saved.get('exam_label')}")
                else:
                    st.warning("No saved session found for this user in this exam.")

        if st.session_state.session:
            st.markdown("---")
            s = st.session_state.session
            st.caption(f"Exam: {s.get('exam_label', 'Unknown')}")
            st.caption(f"Questions: {len(s['question_order'])}")
            st.caption(f"Elapsed: {format_time(s['elapsed_seconds'])}")

    # -------- Guard: Require user & session --------

    if not st.session_state.username.strip():
        st.info("Enter your name/ID in the sidebar to begin.")
        return

    session = st.session_state.session
    if not session:
        st.info("Select exam, then start or resume a test.")
        return

    # Update timer
    update_timer()

    # If completed, show final summary
    if session.get("completed", False) or st.session_state.show_summary:
        show_final_summary(session, questions)
        return

    # -------- Layout: Navigator + Question Panel ------
    nav_col, main_col = st.columns([1.4, 2.6])

    with nav_col:
        show_navigator(session, questions)

    with main_col:
        show_question_panel(session, questions)


# ------------- Navigator (Left Column) ----------------

def show_navigator(session: Dict[str, Any], questions: Dict[str, Dict[str, Any]]):
    st.subheader("Question Navigator")

    qids = session["question_order"]
    total = len(qids)

    # Jump to question by number
    goto_num = st.number_input(
        "Jump to question #",
        min_value=1,
        max_value=total,
        value=st.session_state.current_index + 1,
        step=1
    )
    if st.button("Go"):
        st.session_state.current_index = int(goto_num) - 1

    st.markdown("**Legend:** ✅ answered • 🔁 review • ⬜ not answered")

    # Question buttons
    for idx, qid in enumerate(qids, start=1):
        resp = session["responses"][qid]
        icon = "⬜"
        if resp["choice"]:
            icon = "✅"
        if resp["review"]:
            icon = "🔁"
        if st.button(f"Q{idx} {icon}", key=f"nav_{idx}", use_container_width=True):
            st.session_state.current_index = idx - 1

    st.markdown("---")
    st.subheader("Progress")

    summary = compute_summary(session)
    st.metric("Exam", session.get("exam_label"))
    st.metric("Elapsed Time", format_time(session["elapsed_seconds"]))
    st.metric("Attempted", f"{summary['attempted']} / {total}")
    st.metric("Correct", summary["correct"])
    st.metric("Incorrect", summary["incorrect"])
    st.metric("Score (%)", f"{summary['percent']:.1f}")

    if st.button("Finish Test & View Summary", type="primary"):
        session["completed"] = True
        save_session(session["username"], session["exam_code"], session)
        st.session_state.show_summary = True
        st.experimental_rerun()


# ------------- Question Panel ------------------------

def show_question_panel(session: Dict[str, Any], questions: Dict[str, Dict[str, Any]]):
    qids = session["question_order"]
    total = len(qids)
    idx = st.session_state.current_index
    qid = qids[idx]
    q = questions[qid]
    r = session["responses"][qid]

    st.subheader(f"Question {idx + 1} of {total}")
    st.caption(
        f"Exam: {session.get('exam_label', 'N/A')} • "
        f"ID: {qid} • Domain: {q['domain']} • Difficulty: {q.get('difficulty', 'N/A')}"
    )
    st.write(q["question_text"])
    st.markdown("---")

    # Choices
    options = list(q["choices"].keys())
    labels = [f"{opt}) {q['choices'][opt]}" for opt in options]

    default_index = 0
    if r["choice"] in options:
        default_index = options.index(r["choice"])

    selected_label = st.radio(
        "Select your answer:",
        options=labels,
        index=default_index,
        key=f"radio_{qid}"
    )
    selected_choice = selected_label.split(")")[0]

    # Mark for review
    review_flag = st.checkbox(
        "Mark this question for review",
        value=bool(r["review"]),
        key=f"review_{qid}"
    )
    r["review"] = review_flag

    feedback_placeholder = st.empty()

    col_submit, col_prev, col_next = st.columns([1.5, 1, 1])

    if col_submit.button("Submit Answer", key=f"submit_{qid}"):
        r["choice"] = selected_choice
        r["correct"] = (selected_choice == q["correct_answer"])
        save_session(session["username"], session["exam_code"], session)

        if r["correct"]:
            feedback_placeholder.success("✅ Correct!")
        else:
            feedback_placeholder.error(f"❌ Incorrect. Correct answer is {q['correct_answer']}.")

        with feedback_placeholder.container():
            st.markdown("**Explanation:**")
            st.write(q["explanation"]["correct"])
            st.markdown("**Why other options are incorrect:**")
            for opt, exp in q["explanation"]["options"].items():
                st.write(f"- **{opt}**: {exp}")

    if col_prev.button("⬅ Previous", disabled=(idx == 0)):
        st.session_state.current_index = max(0, idx - 1)

    if col_next.button("Next ➡", disabled=(idx == total - 1)):
        st.session_state.current_index = min(total - 1, idx + 1)


# ------------- Summary -------------------------------

def show_final_summary(session: Dict[str, Any], questions: Dict[str, Dict[str, Any]]):
    st.header("📊 Final Summary")

    summary = compute_summary(session)

    st.write(f"**User:** {session['username']}")
    st.write(f"**Exam:** {session.get('exam_label')}")
    st.write(f"**Total Questions:** {len(session['question_order'])}")
    st.write(f"**Elapsed Time:** {format_time(session['elapsed_seconds'])}")
    st.write(
        f"**Score:** {summary['percent']:.1f}% "
        f"({summary['correct']} correct / {summary['incorrect']} incorrect / "
        f"{summary['attempted']} attempted)"
    )

    st.markdown("---")
    st.subheader("Detailed Feedback by Question")

    for idx, qid in enumerate(session["question_order"], start=1):
        q = questions[qid]
        r = session["responses"][qid]

        st.markdown(f"### Q{idx}. [{q['domain']}]")
        st.write(q["question_text"])

        for key, text in q["choices"].items():
            prefix = f"{key}) "
            if key == r["choice"]:
                prefix = f"👉 {key}) "
            st.write(f"- {prefix}{text}")

        if r["choice"]:
            if r["correct"]:
                st.success(f"Your answer: {r['choice']} ✅ Correct")
            else:
                st.error(f"Your answer: {r['choice']} ❌ Incorrect")
            st.info(f"Correct answer: {q['correct_answer']}")
        else:
            st.warning("You did not answer this question.")
            st.info(f"Correct answer: {q['correct_answer']}")

        st.markdown("**Explanation:**")
        st.write(q["explanation"]["correct"])
        st.markdown("**Option Breakdown:**")
        for opt, exp in q["explanation"]["options"].items():
            st.write(f"- **{opt}**: {exp}")

        st.markdown("---")

    st.success("You may switch exam in the sidebar and start the next test.")


if __name__ == "__main__":
    main()
