from openai import OpenAI
import os

def main():
    
    # Create client using API key from environment
    client = OpenAI(api_key=os.environ.get("OPENAI_MEAL_PLANNER_API_KEY"))

    # Example request
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"},
        ],
    )

    print(response.choices[0].message.content)



if __name__ == "__main__":
    main()
