import os
import json
import requests
import google.generativeai as genai
from flask import Flask, request, jsonify

app = Flask(__name__)

# --- CONFIGURATION ---
# Replace with your real key
os.environ["GOOGLE_API_KEY"] = "AIzaSyCDLnpcTeMm1xjJbadiluP80lyS6p3TAc4" 
MY_SECRET_API_KEY = "12345"
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

system_instruction = """
You are 'Smt. Lakshmi', a 65-year-old retired Indian teacher. 
You are confused by technology. A scammer is messaging you.
Pretend to be a victim. Keep them talking.
Your GOAL: Extract Bank Accounts, UPI IDs, Phone Numbers.
OUTPUT JSON ONLY:
{
  "reply": "your response to scammer",
  "scam_detected": true,
  "extracted_intelligence": {
     "bankAccounts": [],
     "upiIds": [],
     "phoneNumbers": []
  },
  "agentNotes": "summary"
}
"""

# Using gemini-1.5-flash as it is the most stable for JSON output
model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    generation_config={"response_mime_type": "application/json"},
    system_instruction=system_instruction
)

MAX_TURNS = 15

@app.route("/")
def health():
    return "Agentic Honeypot running"

@app.route('/scam-honeypot', methods=['POST'])
def honeypot():
    # 1. Check API Key First
    api_key = request.headers.get("x-api-key")
    if api_key != MY_SECRET_API_KEY:
        return jsonify({"status": "error", "message": "Invalid API key"}), 401

    # 2. Extract Data Safely
    try:
        data = request.get_json(force=True, silent=True) or {}
        message_obj = data.get("message", {})
        incoming_msg = message_obj.get("text", "")
        history = data.get("conversationHistory") or []
        session_id = data.get("sessionId", "unknown_session")
    except Exception as e:
        return jsonify({"status": "error", "message": "Malformed JSON input"}), 400

    # 3. Check Conversation Length
    if len(history) > MAX_TURNS:
        return jsonify({
            "status": "success",
            "reply": "Beta, I am tired now. I will talk later."
        })

    # 4. Ask the AI
    full_context = f"History: {history}\n\nNew Message from Scammer: {incoming_msg}"
    
    try:
        response = model.generate_content(full_context)
        # Ensure we handle empty or weird responses
        ai_result = json.loads(response.text)
    except Exception as e:
        print(f"Gemini error: {e}")
        ai_result = {
            "reply": "Beta, please explain slowly. I am confused.",
            "extracted_intelligence": {"bankAccounts": [], "upiIds": [], "phoneNumbers": []},
            "agentNotes": "Fallback used due to AI error"
        }

    # 5. Reporting Logic
    intelligence = ai_result.get('extracted_intelligence', {})
    # Check if intelligence values exist and have items
    found_something = False
    if isinstance(intelligence, dict):
        found_something = any(len(v) > 0 for v in intelligence.values() if isinstance(v, list))

    if found_something:
        guvi_payload = {
            "sessionId": session_id,
            "scamDetected": True,
            "totalMessagesExchanged": len(history) + 1,
            "extractedIntelligence": intelligence,
            "agentNotes": ai_result.get('agentNotes', 'No notes')
        }
        try:
            # Short timeout to prevent hanging
            requests.post("https://hackathon.guvi.in/api/updateHoneyPotFinalResult", json=guvi_payload, timeout=3)
        except Exception as e:
            print(f"Reporting failed: {e}")

    # 6. Final Reply
    return jsonify({
        "status": "success",
        "reply": ai_result.get('reply', 'Repeat beta?')
    })

if __name__ == '__main__':
    # debug=True will tell you exactly what the 500 error is in your terminal
    app.run(port=5000, debug=True)
