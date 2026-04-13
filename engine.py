import os
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# CHANGE THIS to a valid model: gpt-4o, gpt-4-turbo, or gpt-3.5-turbo
OPENAI_MODEL = "gpt-5.4-nano" 

class ResumeOptimizer:
    def __init__(self):
        self._openai_client = None

    @property
    def openai_client(self):
        if self._openai_client is None:
            # It's better to get the API key here to ensure it's loaded
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in environment variables")
            
            self._openai_client = OpenAI(
                api_key=api_key,
                timeout=60.0,
            )
        return self._openai_client

    def optimize_resume(self, emp_json, jd_json, provider="openai"):
        # The system prompt ensures the LLM behaves as a JSON generator
        system_prompt = (
            "You are an expert Technical Resume Writer. Your goal is to optimize a candidate's "
            "resume JSON to match a specific Job Description (JD). \n\n"
            "RULES:\n"
            "1. Maintain the EXACT same JSON structure and keys as the input.\n"
            "2. Do NOT change 'personal_info', 'education', or 'certifications'.\n"
            "3. Rewrite the 'summary' to align with the JD's core requirements.\n"
            "4. Tailor the 'workdescription' in 'experience' and 'description' in 'projects' "
            "by emphasizing skills mentioned in the JD.\n"
            "5. Update the 'skills' list to prioritize the most relevant skills for this JD.\n"
            "6. Keep the facts honest; do not invent experience the candidate doesn't have.\n"
            "7. Return ONLY the valid JSON object. No markdown, no conversational text."
        )

        user_prompt = (
            f"CANDIDATE RESUME JSON:\n{json.dumps(emp_json, indent=2)}\n\n"
            f"JOB DESCRIPTION JSON:\n{json.dumps(jd_json, indent=2)}\n\n"
            "Please return the updated RESUME JSON."
        )

        try:
            if provider.lower() == "openai":
                print(f"📡 Using OpenAI (Model: {OPENAI_MODEL})...")
                
                chat_completion = self.openai_client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    model=OPENAI_MODEL,
                    response_format={"type": "json_object"}, # Forces JSON output
                    temperature=0.3,
                )
                
                # Extract content and parse from JSON string to Python Dict
                content = chat_completion.choices[0].message.content
                return json.loads(content)

            else:
                print(f"❌ Unsupported provider: {provider}.")
                return None

        except Exception as e:
            print(f"❌ Error during LLM processing: {e}")
            return None


# --- Test Section ---
# if __name__ == "__main__":
#     # Mock data for testing (since I don't have your schema.py)
#     from schema import empjson , JD_FORMAT 
#     mock_emp_json = empjson

#     mock_jd_json = JD_FORMAT

#     print("🚀 Initializing ResumeOptimizer Test...")
#     optimizer = ResumeOptimizer()


#     # 2. Test Actual Optimization Logic
#     print("\n--- Testing Resume Optimization ---")
#     optimized_result = optimizer.optimize_resume(mock_emp_json, mock_jd_json)

#     if optimized_result:
#         print("\n✅ Optimization Successful!")
#         print(json.dumps(optimized_result, indent=2))
#     else:
#         print("\n❌ Optimization Failed.")
