#!/usr/bin/env python3
"""
Test script for Mistral AI API
This script tests your Mistral AI API key and allows you to ask questions to the model.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Try to import mistral client
try:
    from mistralai.client import Mistral
except ImportError:
    print("ERROR: mistral-ai package not installed.")
    print("Install it with: pip install mistralai")
    sys.exit(1)


def test_mistral_api():
    """Test Mistral AI API with your key"""
    
    # Get API key from environment
    api_key = os.getenv("MISTRAL_API_KEY")
    
    if not api_key:
        print("❌ ERROR: MISTRAL_API_KEY not found in environment variables")
        print("Please set it in your .env file: MISTRAL_API_KEY=your_key_here")
        sys.exit(1)
    
    print("✓ API key found")
    
    # Initialize Mistral client
    try:
        client = Mistral(api_key=api_key)
        print("✓ Mistral client initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize Mistral client: {e}")
        sys.exit(1)
    
    # Available models to choose from
    available_models = [
        "mistral-large-latest",      # Most capable
        "mistral-medium-latest",     # Good balance
        "mistral-small-latest",      # Fast and efficient
    ]
    
    print("\nAvailable Mistral models:")
    for i, model in enumerate(available_models, 1):
        print(f"  {i}. {model}")
    
    # Let user choose model
    while True:
        try:
            choice = input(f"\nSelect a model (1-{len(available_models)}) [default: 2]: ").strip()
            if not choice:
                choice = "2"
            model_choice = int(choice) - 1
            if 0 <= model_choice < len(available_models):
                selected_model = available_models[model_choice]
                break
            else:
                print(f"Please enter a number between 1 and {len(available_models)}")
        except ValueError:
            print("Please enter a valid number")
    
    print(f"\n✓ Using model: {selected_model}\n")
    
    # Test with a simple message first
    print("Testing with a simple message...")
    try:
        response = client.chat.complete(
            model=selected_model,
            messages=[
                {"role": "user", "content": "Say 'Hello from Mistral AI' if you can hear me."}
            ]
        )
        print(f"✓ API test successful!")
        print(f"Response: {response.choices[0].message.content}\n")
    except Exception as e:
        print(f"❌ API test failed: {e}")
        sys.exit(1)
    
    # Interactive chat loop
    print("=" * 60)
    print("You can now ask questions to the Mistral AI model")
    print("Type 'exit' or 'quit' to exit")
    print("=" * 60 + "\n")
    
    messages = []  # Maintain conversation history
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ["exit", "quit"]:
                print("\nGoodbye!")
                break
            
            # Add user message to history
            messages.append({"role": "user", "content": user_input})
            
            # Get response from Mistral
            try:
                response = client.chat.complete(
                    model=selected_model,
                    messages=messages
                )
                
                assistant_message = response.choices[0].message.content
                
                # Add assistant response to history
                messages.append({"role": "assistant", "content": assistant_message})
                
                print(f"Assistant: {assistant_message}\n")
                
            except Exception as e:
                print(f"Error getting response: {e}\n")
                # Remove the failed user message from history
                messages.pop()
        
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}\n")


if __name__ == "__main__":
    test_mistral_api()
