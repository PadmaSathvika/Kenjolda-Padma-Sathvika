import os
import sys
from dotenv import load_dotenv

# 1. Setup Environment and Pathing
load_dotenv()
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'modules')))

# Import the "Arms" (Tools) and the "Brain" (LLM)
from modules.tool_agent import decide_tools, generate_plan, synthesize_answer
from openai import OpenAI

class Sem8Agent:
    def __init__(self):
        # Using OpenAI client with Gemini API
        api_key = os.environ.get("GEMINI_API_KEY")
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        ) if api_key else None
        
        self.system_prompt = """
        You are a Senior Bioinformatics AI Agent specialized in 2023-2026 Drug Discovery research.
        Your goal is to provide deep scientific insights and 3D visualizations.
        
        AVAILABLE TOOLS:
        - search_papers: Searches PubMed for 2023 literature.
        - get_chemical_info: Gets SMILES and molecular weight from PubChem.
        - visualize_docking: Launches UCSF Chimera for 3D docking.
        
        PROCESS:
        1. THOUGHT: What do I need to do?
        2. ACTION: Which tool should I call?
        3. OBSERVATION: What did the tool return?
        4. FINAL ANSWER: Summarize findings for the user.
        """

    def run(self, user_query):
        print(f"\n🚀 [MAIN AGENT] Starting Task: {user_query}")
        
        if not self.client:
            return "❌ GEMINI_API_KEY not found in .env file!"
        
        # Step 1: Initial Thought & Strategy
        print("🧠 [THOUGHT] Analyzing question and selecting tools...")
        selected_tools = decide_tools(user_query)
        
        plan = generate_plan(user_query, selected_tools, self.client)
        print(f"📋 [PLAN]\n{plan}")

        # Step 2: Synthesis Phase
        collected_data = {
            "pubmed_abstracts": [],
            "compound_data": None,
            "docking_results": []
        }
        
        final_answer = synthesize_answer(user_query, collected_data, self.client)
        return final_answer


# --- Main Execution Block ---
if __name__ == "__main__":
    agent = Sem8Agent()
    
    print("--- Welcome to the Agentic Drug Discovery Platform (2026) ---")
    query = input("Ask a drug discovery question (e.g., 'Research Ibuprofen and show docking'): ")
    
    if query:
        response = agent.run(query)
        print("\n" + "="*50)
        print("FINAL AGENT RESPONSE:")
        print(response)
        print("="*50)
    else:
        print("No query provided. Exiting.")