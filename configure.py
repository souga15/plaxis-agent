import os

def main():
    print("====================================================")
    print("        PLAXIS AI AGENT — API KEY CONFIGURATION     ")
    print("====================================================")
    
    env_path = ".env"
    
    if os.path.exists(env_path):
        print("\n[INFO] You already have a configured .env file.")
        choice = input("Do you want to overwrite your existing API keys? (y/n): ").strip().lower()
        if choice != 'y':
            print("Keeping your existing configuration. Setup complete!\n")
            return

    print("\nTo use the Plaxis AI Agent, you need an API key from Google (Gemini) or Groq.")
    print("If you don't have one, you can get a free Gemini key here: https://aistudio.google.com/\n")

    gemini_key = input("Paste your Gemini API Key (press Enter to skip): ").strip()
    groq_key = input("Paste your Groq API Key (press Enter to skip): ").strip()

    if not gemini_key and not groq_key:
        print("\n[WARNING] No API keys provided. The AI agent will not be able to process requests until a key is added.")
    
    try:
        with open(env_path, "w") as f:
            f.write(f"GEMINI_API_KEY={gemini_key}\n")
            f.write(f"GROQ_API_KEY={groq_key}\n")
        print("\n[SUCCESS] API keys saved successfully to '.env' file!")
    except Exception as e:
        print(f"\n[ERROR] Failed to save keys: {e}")
    
    print("====================================================\n")

if __name__ == "__main__":
    main()
