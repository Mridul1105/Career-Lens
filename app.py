import os
import google.generativeai as genai
from flask import Flask, request, jsonify
from flask_cors import CORS

# ===============================
# CONFIG
# ===============================

MODEL_NAME = "models/gemini-2.5-flash"
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# ===============================
# GEMINI HELPER
# ===============================

def safe_gemini_call(prompt):
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"AI_ERROR: {str(e)}"

# ===============================
# AGENTS
# ===============================

def classify_user(age):
    if age <= 15:
        return "School Student (≤10th)"
    elif 16 <= age <= 18:
        return "Senior School (11th–12th)"
    return "College Student"

def analyze_personality(answers):
    return safe_gemini_call(
        f"Analyze personality traits from this text:\n{answers}"
    )

def recommend_career(traits, answers):
    return safe_gemini_call(
        f"""
        Based on traits:
        {traits}
        and interests:
        {answers}

        Suggest ONE best-fit career in JSON.
        """
    )

def analyze_skill_gap_dynamic(career_json, user_skills):
    skills_text = safe_gemini_call(
        f"List skills required for this career:\n{career_json}"
    )
    required = [s.strip().title() for s in skills_text.split(",") if s.strip()]
    user = [s.strip().title() for s in user_skills]
    missing = [s for s in required if s not in user]
    return {"required_skills": required, "missing_skills": missing}

def suggest_courses_dynamic(missing):
    if not missing:
        return "No skill gap detected."
    return safe_gemini_call(
        f"Suggest beginner-friendly courses for: {', '.join(missing)}"
    )

# ===============================
# FLASK APP
# ===============================

app = Flask(__name__)
CORS(app)

@app.route("/")
def home():
    return "CareerLens AI Backend is running!"

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.json
        age = data["age"]
        messages = data["messages"]

        category = classify_user(age)
        convo_text = "\n".join(
            [f"{m['role']}: {m['content']}" for m in messages]
        )

        if category.startswith("School"):
            prompt = f"""
            You are a career counsellor for SCHOOL students.
            Conversation so far:
            {convo_text}
            Ask ONE interest-based question.
            """
        elif category.startswith("Senior"):
            prompt = f"""
            You are a career counsellor for 11th–12th students.
            Conversation so far:
            {convo_text}
            Ask ONE subject/stream preference question.
            """
        else:
            prompt = f"""
            You are a career counsellor for COLLEGE students.
            Conversation so far:
            {convo_text}
            If skills are not mentioned, ask about skills.
            Otherwise ask about career goals.
            """

        reply = safe_gemini_call(prompt)

        return jsonify({
            "category": category,
            "reply": reply
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        data = request.json
        age = data["age"]
        answers = data["answers"]
        skills = data.get("skills", [])

        category = classify_user(age)
        traits = analyze_personality(answers)
        career = recommend_career(traits, answers)

        if category != "College Student":
            return jsonify({
                "category": category,
                "traits": traits,
                "career_recommendation": career,
                "note": "Skill gap analysis not required."
            })

        gap = analyze_skill_gap_dynamic(career, skills)
        courses = suggest_courses_dynamic(gap["missing_skills"])

        return jsonify({
            "category": category,
            "traits": traits,
            "career_recommendation": career,
            "required_skills": gap["required_skills"],
            "missing_skills": gap["missing_skills"],
            "courses": courses
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route("/debug")
def debug():
    return "DEBUG OK - Chatbot version running"

# ===============================
# RUN
# ===============================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

