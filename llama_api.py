import requests
from config import RAPIDAPI_KEY, RAPIDAPI_HOST
import re

def query_llama_api(prompt, schema_text="", mode="chat"):
    """
    Query the Llama API for SQL generation or chat responses
    
    Args:
        prompt (str): The user's question or prompt
        schema_text (str): Database schema information (for SQL mode)
        mode (str): "sql" for SQL generation, "chat" for conversational responses
    """
    url = "https://meta-llama-3-1-405b.p.rapidapi.com/"

    if mode == "sql":
        system_message = f"""
You are a SQL query generator for Peshawar Mall's database. 

EXACT Database Schema:
{schema_text}

CRITICAL RULES:
1. Use ONLY the table names shown in the schema above

MULTIPLE QUESTIONS HANDLING:
- If user asks multiple questions, generate multiple SQL queries
- Separate each query with a semicolon and newline
- Example for "price of TV and contact number":
  SELECT price FROM product WHERE product_name = 'TV';
  SELECT contact_number FROM mall_information;

USER QUESTION: {prompt}

Generate SQL queries (use exact table names from schema):
"""
    else:
        system_message = f"""
You are a friendly, conversational AI assistant working at **Peshawar Mall**. Your job is to help customers by answering their queries about the mall using the information provided from the database.

INSTRUCTIONS:
- You are helpful, conversational, and polite — like a human customer service assistant.
- You must answer ONLY using the result provided from the database.
- DO NOT make up information. If the data is missing, say: “Sorry, I couldn’t find that information.”
- Be concise and avoid lengthy or unrelated replies.
- You must sound polite and helpful, but never add unrelated small talk or personal opinions.
- Avoid robotic, one-line answers. Instead, use natural language like: "Sure! The price of the item is..." or "Yes, you'll find that store on the first floor."
- Do NOT invent data that isn’t explicitly in the results.
- If the result is empty or missing, politely say: “Sorry, I couldn’t find that information in our system.”
- If a customer asks something not related to the database, gently inform them that you can only help with mall-related information.

You are powered by real-time data queries from the mall's database, so always trust the provided result when answering.

Begin the conversation only after the customer speaks.

Customer: {prompt}
Mall Assistant:
"""
    payload = {
        "model": "llama-3.1-405b",
        "max_tokens": 300,
        "temperature": 0.1,  # Lower temperature for more consistent responses
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": str(prompt)},
        ],
    }

    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST,
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        response_data = response.json()

        if "choices" in response_data and response_data["choices"]:
            response_text = response_data["choices"][0]["message"]["content"]

            # Clean up the respons
            if mode == "sql":
                # Remove markdown formatting from SQL queries
                cleaned_query = re.sub(r"```sql|```|```", "", response_text).strip()
                
                # Extract the SQL query (remove explanatory text)
                lines = cleaned_query.split('\n')
                sql_lines = []
                for line in lines:
                    line = line.strip()
                    if line.lower().startswith(('select', 'insert', 'update', 'delete')):
                        sql_lines.append(line)

                if sql_lines:
                    return "\n".join(sql_lines)
                # If no valid SQL found, return the cleaned text
                return cleaned_query
            else:
                # For chat mode, return the response as-is (cleaned)
                return response_text.strip()
        else:
            return "Error: No valid response generated."

    except requests.exceptions.RequestException as e:
        print(f"Error calling Llama API: {e}")
        return f"Error: API request failed - {str(e)}"
    except KeyError as e:
        print(f"Error parsing API response: {e}")
        return "Error: Invalid API response format."
    except Exception as e:
        print(f"Unexpected error: {e}")
        return f"Error: {str(e)}"