import os
from typing import List, Dict

import streamlit as st
from openai import OpenAI


# ----------------------------- Configuration ----------------------------- #

APP_TITLE = "Python Tutor Chatbot"
DEFAULT_MODEL = "gpt-4"  # Allowed: "gpt-4" or "gpt-3.5-turbo"
ALLOWED_MODELS = ["gpt-4", "gpt-3.5-turbo"]
DEFAULT_TEMPERATURE = 0.3


# ----------------------------- Utilities ----------------------------- #

def get_openai_client() -> OpenAI:
    # OpenAI SDK reads API key from environment variable: OPENAI_API_KEY
    return OpenAI()


def build_system_prompt(level: str, focus: str, style: str, socratic: bool) -> str:
    tone = "Socratic and probing while supportive" if socratic else "clear and direct with gentle guidance"
    return (
        f"You are a patient, expert Python tutor.\n"
        f"- Teaching level: {level}\n"
        f"- Focus area: {focus}\n"
        f"- Teaching style: {style}\n"
        f"- Tone: {tone}\n\n"
        f"Goals:\n"
        f"1) Explain concepts step-by-step using simple language.\n"
        f"2) Provide concise code examples using modern Python 3.12 when helpful.\n"
        f"3) Encourage good practices (readability, PEP 8, clear naming, basic testing).\n"
        f"4) Offer small exercises. Before revealing solutions, invite the learner to try first.\n"
        f"5) When asked to review code, explain what it does, identify issues, and suggest improvements.\n"
        f"6) Prefer standard library unless user requests external packages.\n\n"
        f"Formatting:\n"
        f"- Keep responses concise. Use bullet points and short code blocks where useful.\n"
        f"- Provide example outputs when helpful.\n"
        f"- Ask one clarifying or reflective question when appropriate to check understanding."
    )


def init_session_state():
    if "messages" not in st.session_state:
        st.session_state.messages: List[Dict[str, str]] = []
    if "model" not in st.session_state:
        st.session_state.model = DEFAULT_MODEL
    if "temperature" not in st.session_state:
        st.session_state.temperature = DEFAULT_TEMPERATURE
    if "level" not in st.session_state:
        st.session_state.level = "Beginner"
    if "focus" not in st.session_state:
        st.session_state.focus = "Fundamentals"
    if "style" not in st.session_state:
        st.session_state.style = "Explain, then example, then short exercise"
    if "socratic" not in st.session_state:
        st.session_state.socratic = True
    if "system_prompt_cache" not in st.session_state:
        st.session_state.system_prompt_cache = ""


def update_settings(model: str, temperature: float, level: str, focus: str, style: str, socratic: bool):
    changed = False
    if model != st.session_state.model:
        st.session_state.model = model
        changed = True
    if abs(temperature - st.session_state.temperature) > 1e-9:
        st.session_state.temperature = temperature
        changed = True
    if level != st.session_state.level:
        st.session_state.level = level
        changed = True
    if focus != st.session_state.focus:
        st.session_state.focus = focus
        changed = True
    if style != st.session_state.style:
        st.session_state.style = style
        changed = True
    if socratic != st.session_state.socratic:
        st.session_state.socratic = socratic
        changed = True
    return changed


def clear_chat():
    st.session_state.messages = []


def ensure_system_prompt() -> str:
    prompt = build_system_prompt(
        level=st.session_state.level,
        focus=st.session_state.focus,
        style=st.session_state.style,
        socratic=st.session_state.socratic,
    )
    st.session_state.system_prompt_cache = prompt
    return prompt


def generate_assistant_reply(client: OpenAI, model: str, system_prompt: str, chat_history: List[Dict[str, str]], temperature: float) -> str:
    # Compose messages: system prompt + history
    messages = [{"role": "system", "content": system_prompt}] + chat_history
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
    )
    return response.choices[0].message.content


def suggested_prompts(level: str) -> List[str]:
    base = [
        "Explain list comprehensions with two small examples.",
        "Give me a short exercise on for-loops and range().",
        "What are common pitfalls with mutable default arguments?",
        "Show how to read and write a text file safely.",
        "Explain try/except/else/finally with a minimal example.",
        "How do I use virtual environments and why do they matter?",
    ]
    if level == "Beginner":
        base.extend([
            "What is the difference between a list and a tuple?",
            "Explain variables and types with simple examples.",
        ])
    elif level == "Intermediate":
        base.extend([
            "Demonstrate list vs dict iteration patterns and when to use each.",
            "Show how to write a small unit test using unittest.",
        ])
    else:
        base.extend([
            "Explain decorators with a practical example.",
            "Show how to use type hints and mypy to improve code quality.",
        ])
    return base[:6]


# ----------------------------- Streamlit App ----------------------------- #

def main():
    st.set_page_config(page_title=APP_TITLE, page_icon="🐍", layout="wide")
    init_session_state()

    st.title(APP_TITLE)
    st.caption("An interactive tutor to learn Python step-by-step.")

    # Sidebar - Settings
    with st.sidebar:
        st.header("Settings")
        model = st.selectbox("Model", ALLOWED_MODELS, index=ALLOWED_MODELS.index(st.session_state.model))
        temperature = st.slider("Creativity (temperature)", 0.0, 1.0, float(st.session_state.temperature), 0.05)
        level = st.selectbox("Level", ["Beginner", "Intermediate", "Advanced"], index=["Beginner", "Intermediate", "Advanced"].index(st.session_state.level))
        focus = st.selectbox(
            "Focus",
            ["Fundamentals", "Data Structures", "Functions", "OOP", "File I/O", "Error Handling", "Testing", "Typing", "Performance"],
            index=0 if st.session_state.focus not in ["Fundamentals", "Data Structures", "Functions", "OOP", "File I/O", "Error Handling", "Testing", "Typing", "Performance"] else
                  ["Fundamentals", "Data Structures", "Functions", "OOP", "File I/O", "Error Handling", "Testing", "Typing", "Performance"].index(st.session_state.focus)
        )
        style = st.selectbox(
            "Teaching style",
            ["Explain, then example, then short exercise", "Example-first", "Exercise-first", "Debugging-focused"],
            index=0 if st.session_state.style not in ["Explain, then example, then short exercise", "Example-first", "Exercise-first", "Debugging-focused"] else
                  ["Explain, then example, then short exercise", "Example-first", "Exercise-first", "Debugging-focused"].index(st.session_state.style)
        )
        socratic = st.checkbox("Socratic mode (ask guiding questions)", value=st.session_state.socratic)
        changed = update_settings(model, temperature, level, focus, style, socratic)

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Clear chat"):
                clear_chat()
        with col_b:
            st.write("")  # spacing

        st.divider()
        if not os.getenv("OPENAI_API_KEY"):
            st.warning("Set the OPENAI_API_KEY environment variable to use the tutor.")

        st.caption("Tip: Adjust level, focus, and style to tailor the session.")

    # Suggestion chips
    st.subheader("Try a prompt")
    cols = st.columns(3)
    prompts = suggested_prompts(st.session_state.level)
    for i, p in enumerate(prompts):
        if cols[i % 3].button(p, key=f"suggest_{i}"):
            st.session_state.messages.append({"role": "user", "content": p})

    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    user_input = st.chat_input("Ask about Python, request an explanation, or propose a coding exercise...")
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    client = get_openai_client()
                    system_prompt = ensure_system_prompt()
                    reply = generate_assistant_reply(
                        client=client,
                        model=st.session_state.model,
                        system_prompt=system_prompt,
                        chat_history=st.session_state.messages,
                        temperature=st.session_state.temperature,
                    )
                except Exception as e:
                    st.error(f"API error: {e}")
                    reply = "I'm having trouble reaching the language model API. Please check your API key and try again."

                st.markdown(reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})

    # Footer / helper text
    st.write("")
    st.caption("Note: This tutor provides guidance and examples. Always test code in your environment.")


if __name__ == "__main__":
    main()