"""
Test script to verify OpenAI API key is working
"""
import os
import sys
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_openai_key():
    """Test if OpenAI API key is valid and working"""
    
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if not openai_key:
        print("❌ ERROR: OPENAI_API_KEY not found in .env file")
        print("\nPlease add your OpenAI API key to backend/.env:")
        print("OPENAI_API_KEY=sk-your-key-here")
        return False
    
    print(f"✓ Found OpenAI API key: {openai_key[:20]}...")
    print("\nTesting API connection...")
    
    try:
        import httpx
        
        headers = {
            "Authorization": f"Bearer {openai_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {
                    "role": "user",
                    "content": "Say 'Hello, PortAct!' if you can read this."
                }
            ],
            "max_tokens": 20
        }
        
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                message = data["choices"][0]["message"]["content"]
                print(f"\n✅ SUCCESS! OpenAI API is working!")
                print(f"Response: {message}")
                print(f"\nUsage:")
                print(f"  - Prompt tokens: {data['usage']['prompt_tokens']}")
                print(f"  - Completion tokens: {data['usage']['completion_tokens']}")
                print(f"  - Total tokens: {data['usage']['total_tokens']}")
                return True
            
            elif response.status_code == 401:
                print("\n❌ ERROR: Invalid API key")
                print("Your API key is not valid or has expired.")
                print("\nTo fix:")
                print("1. Go to https://platform.openai.com/api-keys")
                print("2. Create a new API key")
                print("3. Update backend/.env with the new key")
                return False
            
            elif response.status_code == 429:
                print("\n⚠️  WARNING: Rate limit exceeded")
                print("You've hit the API rate limit.")
                print("\nThis could mean:")
                print("- You've used up your free credits")
                print("- Too many requests in a short time")
                print("\nCheck your usage at: https://platform.openai.com/usage")
                return False
            
            elif response.status_code == 403:
                print("\n❌ ERROR: Access forbidden")
                print("Your API key doesn't have permission to access this endpoint.")
                return False
            
            else:
                print(f"\n❌ ERROR: API returned status code {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
    except ImportError:
        print("\n❌ ERROR: httpx library not installed")
        print("Run: pip install httpx")
        return False
    
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        return False


async def test_news_service():
    """Test the AI news service with a sample asset"""
    print("\n" + "="*60)
    print("Testing AI News Service")
    print("="*60)
    
    try:
        from app.services.ai_news_service import AINewsService
        from app.models.asset import Asset, AssetType
        
        # Create a test asset
        test_asset = Asset(
            id=1,
            user_id=1,
            asset_type=AssetType.STOCK,
            name="Infosys Limited",
            symbol="INFY",
            current_price=1500.0,
            quantity=10
        )
        
        print(f"\nTesting with asset: {test_asset.name} ({test_asset.symbol})")
        print("Fetching news from AI...")
        
        service = AINewsService()
        
        # Build prompt
        prompt = service._build_news_prompt(test_asset)
        print(f"\nPrompt length: {len(prompt)} characters")
        
        # Query AI
        if service.ai_provider == "openai" and service.openai_api_key:
            response = await service._query_openai(prompt)
        elif service.ai_provider == "grok" and service.grok_api_key:
            response = await service._query_grok(prompt)
        else:
            print("❌ No AI provider configured")
            return False
        
        if response:
            print("\n✅ AI Response received!")
            print(f"\nResponse preview (first 500 chars):")
            print("-" * 60)
            print(response[:500])
            print("-" * 60)
            
            # Try to parse
            news_data = service._parse_ai_response(response, test_asset)
            if news_data:
                print("\n✅ Successfully parsed AI response!")
                print(f"\nParsed data:")
                print(f"  - Has significant news: {news_data.get('has_significant_news')}")
                if news_data.get('has_significant_news'):
                    print(f"  - Title: {news_data.get('title')}")
                    print(f"  - Severity: {news_data.get('severity')}")
                    print(f"  - Category: {news_data.get('category')}")
            else:
                print("\n⚠️  No significant news found (this is normal)")
            
            return True
        else:
            print("\n❌ Failed to get AI response")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR in news service test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test function"""
    print("="*60)
    print("OpenAI API Key Verification Test")
    print("="*60)
    
    # Test 1: Basic API key validation
    key_valid = await test_openai_key()
    
    if not key_valid:
        print("\n" + "="*60)
        print("RESULT: API key test FAILED")
        print("="*60)
        sys.exit(1)
    
    # Test 2: News service integration
    service_valid = await test_news_service()
    
    print("\n" + "="*60)
    if key_valid and service_valid:
        print("RESULT: All tests PASSED ✅")
        print("\nYour OpenAI API key is working correctly!")
        print("You can now use the AI News & Alerts feature.")
    else:
        print("RESULT: Some tests FAILED ❌")
        print("\nPlease check the errors above and fix them.")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())

# Made with Bob
