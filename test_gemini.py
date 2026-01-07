"""Quick test script to verify Gemini API is working"""
import os
from dotenv import load_dotenv

load_dotenv()

def test_gemini_llm():
    """Test Gemini LLM"""
    print("Testing Gemini LLM...")
    from langchain_google_genai import ChatGoogleGenerativeAI

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=os.getenv("GOOGLE_API_KEY")
    )

    response = llm.invoke("Say 'Hello from Gemini!' in one sentence.")
    print(f"LLM Response: {response.content}")
    print("[OK] Gemini LLM working!")
    return True

def test_gemini_embeddings():
    """Test Gemini Embeddings"""
    print("\nTesting Gemini Embeddings...")
    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/text-embedding-004",
        google_api_key=os.getenv("GOOGLE_API_KEY")
    )

    result = embeddings.embed_query("This is a test")
    print(f"Embedding dimensions: {len(result)}")
    print(f"First 5 values: {result[:5]}")
    print("[OK] Gemini Embeddings working!")
    return True

if __name__ == "__main__":
    try:
        test_gemini_llm()
        test_gemini_embeddings()
        print("\n" + "="*50)
        print("All Gemini API tests passed!")
        print("="*50)
    except Exception as e:
        print(f"\nError: {e}")
        print("Please check your GOOGLE_API_KEY")
