import streamlit as st
from google import genai
from google.genai import errors
from PyPDF2 import PdfReader
from gtts import gTTS
import base64
import os

# --- 1. CONFIGURATION & IDENTITY ---
# Project Metadata for Tech Fest
AUTHOR = "Pratyasha Bharti"
DEPT = "Civil Engineering"
SEM = "5th Sem"
PRIMARY_MODEL = "gemini-2.5-flash-lite"
BACKUP_MODEL = "gemini-1.5-flash"

# Replace with your actual Gemini API Key
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY_HERE"
client = genai.Client(api_key=GEMINI_API_KEY)

st.set_page_config(page_title="AI Study Buddy", layout="wide")

# --- 2. CUSTOM CSS & STYLING ---
st.markdown(f"""
    <style>
    .main {{ background-color: #0f1116; color: #ffffff; }}
    .stTabs [data-baseweb="tab-list"] {{ gap: 24px; }}
    .stTabs [data-baseweb="tab"] {{ height: 50px; white-space: pre-wrap; background-color: #1e2129; border-radius: 5px; color: white; }}
    .quiz-card {{ background-color: #262730; padding: 20px; border-radius: 10px; border-left: 5px solid #4CAF50; margin-bottom: 10px; }}
    </style>
    """, unsafe_allow_html=True)

# --- 3. CORE LOGIC FUNCTIONS ---
def generate_response(prompt):
    try:
        response = client.models.generate_content(model=PRIMARY_MODEL, contents=prompt)
        return response.text
    except errors.ServerError:
        # Failover to 1.5 Flash if 2.5 is at high demand
        response = client.models.generate_content(model=BACKUP_MODEL, contents=prompt)
        return response.text

def play_audio(text):
    try:
        # Filter out markdown/special chars for cleaner audio
        clean_text = text.replace("*", "").replace("#", "")[:250]
        tts = gTTS(text=clean_text, lang='en')
        tts.save("response.mp3")
        with open("response.mp3", "rb") as f:
            data = f.read()
            b64 = base64.b64encode(data).decode()
            md = f'<audio src="data:audio/mp3;base64,{b64}" controls autoplay="true" style="display:none;"></audio>'
            st.markdown(md, unsafe_allow_html=True)
    except Exception: pass

# --- 4. SESSION STATE INITIALIZATION ---
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "pdf_text" not in st.session_state: st.session_state.pdf_text = ""
if "quiz_data" not in st.session_state: st.session_state.quiz_data = []
if "quiz_answers" not in st.session_state: st.session_state.quiz_answers = []
if "score" not in st.session_state: st.session_state.score = 0

# --- 5. SIDEBAR: PROGRESS & UPLOAD ---
with st.sidebar:
    st.title("🛡️ Student Hub")
    st.write(f"**User:** {AUTHOR}")
    st.write(f"**Dept:** {DEPT} ({SEM})")
    
    st.divider()
    
    uploaded_file = st.file_uploader("Upload Lesson (PDF)", type="pdf")
    if st.button("Initialize Material"):
        if uploaded_file:
            reader = PdfReader(uploaded_file)
            st.session_state.pdf_text = "".join([p.extract_text() for p in reader.pages])
            st.success("Lesson Loaded Successfully!")
        else: st.error("Upload a file first.")

# --- 6. MAIN APP INTERFACE ---
st.title("🎓 AI Study Buddy")
tab_chat, tab_sum, tab_quiz, tab_tips = st.tabs(["💬 Chatbot", "📖 Deep Summary", "📝 Exam Mode", "💡 Study Tips"])

# TAB 1: CONVERSATIONAL CHATBOT
with tab_chat:
    st.subheader("Interactive Learning Assistant")
    chat_box = st.container(height=350)
    
    with chat_box:
        for role, text in st.session_state.chat_history:
            with st.chat_message(role): st.write(text)

    if query := st.chat_input("Ask a doubt from the lesson..."):
        st.session_state.chat_history.append(("user", query))
        with chat_box: st.chat_message("user").write(query)
        
        with chat_box:
            with st.chat_message("assistant"):
                context = f"Context: {st.session_state.pdf_text[:4000]}\n\nUser Question: {query}"
                ans = generate_response(context)
                st.write(ans)
                st.session_state.chat_history.append(("assistant", ans))
                play_audio(ans)

# TAB 2: DEEP SUMMARY
with tab_sum:
    st.subheader("Technical Summarization Engine")
    if st.button("Generate Extended Summary"):
        if st.session_state.pdf_text:
            prompt = f"Provide a long technical summary including key formulas and concepts for: {st.session_state.pdf_text[:8000]}"
            summary = generate_response(prompt)
            st.markdown(summary)
            play_audio("Detailed summary ready.")
        else: st.warning("Please upload a PDF.")

# TAB 3: 10-QUESTION QUIZ (HIDDEN ANSWERS)
with tab_quiz:
    st.subheader("10-Question Mock Exam")
    if st.button("Generate Exam Paper"):
        if st.session_state.pdf_text:
            prompt = f"Create 10 MCQs from the text. Format: Q: [Question] | A) [Opt] B) [Opt] C) [Opt] D) [Opt] | CORRECT: [Letter]. Split with '###'. Context: {st.session_state.pdf_text[:5000]}"
            raw = generate_response(prompt)
            items = raw.split("###")
            st.session_state.quiz_data = [i.split("CORRECT:")[0].strip() for i in items if "CORRECT:" in i]
            st.session_state.quiz_answers = [i.split("CORRECT:")[1].strip()[0] for i in items if "CORRECT:" in i]
            play_audio("Exam generated. Good luck.")

    if st.session_state.quiz_data:
        user_choices = []
        for i, q in enumerate(st.session_state.quiz_data[:10]):
            st.markdown(f"<div class='quiz-card'>{q}</div>", unsafe_allow_html=True)
            user_choices.append(st.radio(f"Select Answer Q{i+1}:", ["A", "B", "C", "D"], key=f"ans_{i}", index=None))
        
        if st.button("Submit & Grade"):
            score = sum(1 for i in range(len(st.session_state.quiz_answers)) if user_choices[i] == st.session_state.quiz_answers[i])
            st.success(f"Exam Complete! Final Score: {score}/10")
            st.progress(score / 10)
            if score >= 8: st.balloons()

# TAB 4: STUDY TIPS
with tab_tips:
    st.subheader("BTech Success Tips")
    if st.button("Get Productivity Hacks"):
        tips = generate_response("Give 5 high-yield study tips for engineering students.")
        st.info(tips)