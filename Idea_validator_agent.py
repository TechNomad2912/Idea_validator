import inspect
if not hasattr(inspect, 'getargspec'):
    inspect.getargspec = inspect.getfullargspec

from flask import Flask, request, jsonify
from flask_cors import CORS
from phi.agent import Agent
from phi.model.google import Gemini
from dotenv import load_dotenv
import os
load_dotenv()

app = Flask(__name__)
CORS(app)
validation_agent = Agent(
    name="Idea Validator",
    model=Gemini(id="gemini-1.5-flash"),
    instructions=[
        "You are an AI startup validation assistant specialized in both onboarding and idea expansion. Your tasks:",
        "Step 1: User Onboarding & Industry Detection: Given a user input prompt, identify the industry, target market, and business category. Determine potential business models for a startup in the detected industry. Generate a personalized onboarding response for a business in that sector and suggest startup funding options specific to the detected industry.",
        "Step 2: Idea Submission & Expansion: Based on the user's answers to the following key questions, generate a detailed analysis of the startup idea:",
        "⿡ What specific problem does your business aim to solve? (Describe the challenge your target audience faces.)",
        "⿢ Who are your target customers, and what makes them the right audience for your solution? (Describe your ideal users, their demographics, and pain points.)",
        "⿣ How does your solution work, and what makes it unique from existing alternatives? (Explain your approach, unique value proposition, or key differentiators.)",
        "⿤ What key resources or technologies power your business idea? (Mention any AI models, frameworks, or strategies involved.)",
        "⿥ What are your main revenue streams or business model assumptions? (Describe how you plan to monetize or sustain your business.)",
        "Using these responses, extract the core problem, solution, and target audience; provide a one-paragraph market opportunity analysis; rewrite the business idea in a structured, investor-friendly format; and expand it into a detailed business concept with key features and differentiators.",
        "Additionally, if present in the initial user input, extract and clearly indicate the following details: industry, target market cap, expected revenue.",
        "Format your response using bullet points and conclude with: 'Is this understanding correct? (Yes/No)'"
    ]
)

@app.route("/validate", methods=["POST"])
def validate_idea():
    try:
        data = request.json
        # Basic input that may include industry, market cap, and expected revenue
        user_input = data.get("user_input", "")
        
        # Fetch answers to the five questions from the frontend
        problem = data.get("problem", "")
        target_customers = data.get("target_customers", "")
        solution = data.get("solution", "")
        key_resources = data.get("key_resources", "")
        revenue_streams = data.get("revenue_streams", "")
        
        # Build a comprehensive prompt combining onboarding info and detailed idea answers
        analysis_prompt = f"""Analyze the following startup input.

Step 1: User Onboarding & Industry Detection:
User Input: {user_input}
- Identify the industry, target market, and business category.
- Determine potential business models for a startup in the detected industry.
- Generate a personalized onboarding response for a business in that sector.
- Suggest startup funding options specific to the detected industry.

Step 2: Idea Submission & Expansion:
User Responses:
⿡ Problem: {problem}
⿢ Target Customers: {target_customers}
⿣ Solution: {solution}
⿤ Key Resources: {key_resources}
⿥ Revenue Streams: {revenue_streams}

Based on the above responses:
- Extract the problem, solution, and target audience.
- Provide a one-paragraph market opportunity analysis.
- Rewrite the business idea in a structured, investor-friendly format.
- Expand the business idea into a detailed business concept with key features and differentiators.

Additionally, if present in the user input, extract and indicate:
- Industry
- Target Market Cap
- Expected Revenue

Format your response with bullet points and conclude with: 'Is this understanding correct? (Yes/No)'
"""
        agent_response = validation_agent.run(analysis_prompt)
        
        return jsonify({
            "response": agent_response.content,
            "status": "needs_confirmation",
            "original_data": {
                "user_input": user_input,
                "problem": problem,
                "target_customers": target_customers,
                "solution": solution,
                "key_resources": key_resources,
                "revenue_streams": revenue_streams
            }
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/confirm", methods=["POST"])
def handle_confirmation():
    data = request.json
    confirmation = data.get("confirmation", "").lower()
    original_data = data.get("original_data", {})

    if confirmation == "yes":
        return jsonify({
            "response": "Great! Proceeding to next steps...",
            "status": "confirmed"
        })
    
    elif confirmation == "no":
        clarification_prompt = f"""User rejected the analysis of their startup idea.
Ask 2-3 specific clarification questions focusing on:
- Market size assumptions
- Technical implementation unclear points
- Revenue model uncertainties
"""
        clarification_response = validation_agent.run(clarification_prompt)
        return jsonify({
            "response": clarification_response.content,
            "status": "needs_clarification"
        })
    
    return jsonify({"error": "Invalid confirmation"}), 400

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5004))
    app.run(debug=True, host="0.0.0.0", port=port)
