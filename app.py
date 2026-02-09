import streamlit as st
from google import genai
from google.genai import errors
from PyPDF2 import PdfReader
from gtts import gTTS
import base64
import re

# --- CONFIGURATION ---
GEMINI_API_KEY = "AIzaSyBWebsYEGZ7z2gsmHeijHOnM-ZlXdWBiCE"
client = genai.Client(api_key=GEMINI_API_KEY)
PRIMARY_MODEL = "gemini-2.5-flash-lite"
BACKUP_MODEL = "gemini-1.5-flash"

st.set_page_config(page_title="Pro Study AI", layout="wide", initial_sidebar_state="expanded")

# --- UI STYLING ---
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #E0E0E0; }
    .stButton>button { background: linear-gradient(45deg, #4CAF50, #2E7D32); color: white; border: none; font-weight: bold; }
    .quiz-card { background-color: #1E1E1E; padding: 20px; border-radius: 15px; border-left: 5px solid #4CAF50; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- HELPER FUNCTIONS ---
def generate_response(prompt):
    try:
        response = client.models.generate_content(model=PRIMARY_MODEL, contents=prompt)
        return response.text
    except errors.ServerError:
        response = client.models.generate_content(model=BACKUP_MODEL, contents=prompt)
        return response.text

def play_audio(text):
    try:
        tts = gTTS(text=text[:150], lang='en')
        tts.save("voice.mp3")
        with open("voice.mp3", "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
            st.markdown(f'<audio src="data:audio/mp3;base64,{b64}" controls autoplay style="display:none;"></audio>', unsafe_allow_html=True)
    except: pass

# --- INITIALIZE SESSION STATE ---
if "quiz_data" not in st.session_state: st.session_state.quiz_data = None
if "pdf_text" not in st.session_state: st.session_state.pdf_text = ""
if "score" not in st.session_state: st.session_state.score = 0

# --- SIDEBAR ---
with st.sidebar:
    st.title("🛡️ Pro Study Control")
    files = st.file_uploader("Upload Engineering Notes (PDF)", type="pdf")
    if st.button("🚀 Process Material"):
        if files:
            reader = PdfReader(files)
            st.session_state.pdf_text = "".join([p.extract_text() for p in reader.pages])
            st.success("Analysis Complete!")
    
    st.divider()
    st.write(f"### Current Score: {st.session_state.score}/10")
    st.progress(st.session_state.score * 10)

# --- MAIN UI ---
tab1, tab2, tab3 = st.tabs(["📖 Smart Summary", "✍️ 10-Question Quiz", "💡 Study Tips"])

# TAB 1: EXTENDED SUMMARY
with tab1:
    st.header("Deep Learning Summary")
    if st.button("Generate Detailed Technical Summary"):
        if st.session_state.pdf_text:
            with st.spinner("Analyzing deep structures..."):
                prompt = f"""Provide a comprehensive, long-form technical summary of the following text. 
                Include: 1. Core Architecture/Concepts 2. Key Mathematical or Logical formulas 3. Practical Applications.
                Text: {st.session_state.pdf_text[:8000]}"""
                summary = generate_response(prompt)
                st.markdown(summary)
                play_audio("Summary generated. Review the key technical points below.")
        else: st.warning("Please upload a PDF first.")

import streamlit as st
import re

# --- TAB 2: EXAM MODE (HIDDEN ANSWERS) ---
with tab2:
    st.header("📝 Engineering Mock Exam")
    st.write("Test your knowledge without seeing the answers upfront.")

    if st.button("Generate 10 Hidden MCQs"):
        if st.session_state.pdf_text:
            with st.spinner("Preparing Exam Paper..."):
                # We tell the AI to use a very specific delimiter (###)
                prompt = f"""Generate 10 MCQs from this text. 
                Format each question EXACTLY like this:
                Q: [Question]
                A) [Opt] B) [Opt] C) [Opt] D) [Opt]
                CORRECT: [Letter]
                ###
                Text: {st.session_state.pdf_text[:5000]}"""
                
                raw_response = generate_response(prompt)
                
                # Logic to split by our delimiter ###
                raw_questions = raw_response.split("###")
                processed_questions = []
                correct_answers = []

                for q in raw_questions:
                    if "CORRECT:" in q:
                        # Extract the correct letter and remove it from the display text
                        parts = q.split("CORRECT:")
                        display_text = parts[0].strip()
                        answer_letter = parts[1].strip()[0] # Takes just 'A', 'B', etc.
                        processed_questions.append(display_text)
                        correct_answers.append(answer_letter)
                
                st.session_state.quiz_list = processed_questions
                st.session_state.ans_list = correct_answers
                st.session_state.user_choices = [None] * 10
                play_audio("Exam is ready. No cheating!")
        else:
            st.warning("Upload a PDF first!")

    # DISPLAY THE QUIZ
    if "quiz_list" in st.session_state:
        user_input_answers = []
        for i, q_text in enumerate(st.session_state.quiz_list[:10]):
            st.markdown(f"<div class='quiz-card'>{q_text}</div>", unsafe_allow_html=True)
            choice = st.radio(f"Select for Q{i+1}:", ["A", "B", "C", "D"], key=f"q{i}", index=None)
            user_input_answers.append(choice)

        if st.button("Submit & Grade Exam"):
            score = 0
            results = []
            for i in range(len(st.session_state.ans_list)):
                if user_input_answers[i] == st.session_state.ans_list[i]:
                    score += 1
                    results.append(f"Q{i+1}: ✅ Correct")
                else:
                    results.append(f"Q{i+1}: ❌ Wrong (Correct: {st.session_state.ans_list[i]})")
            
            st.session_state.score = score
            st.divider()
            st.subheader(f"Your Final Grade: {score}/10")
            
            # Show progress bar based on performance
            st.progress(score / 10)
            
            for r in results:
                st.write(r)
            
            if score >= 8:
                st.balloons()
                st.success("Exemplary Performance!")
            elif score >= 5:
                st.info("Good effort, keep reviewing.")
            else:
                st.error("Needs Improvement. Try re-reading the summary.")
# TAB 3: STUDY TIPS
with tab3:
    st.header("BTech Success Hacks")
    tips_prompt = "Give 5 high-yield study tips specifically for engineering students dealing with heavy technical subjects."
    if st.button("Get New Tips"):
        tips = generate_response(tips_prompt)
        st.info(tips)