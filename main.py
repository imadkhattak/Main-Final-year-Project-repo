import asyncio
from text_to_speech import text_to_speech_and_play
from llama_api import query_llama_api
from transcription_utils import transcribe_audio_to_text
from audio_utils import record_audio
from langchain_community.utilities import SQLDatabase
from database_utils import execute_sql_query, get_database_schema
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain.memory import ConversationBufferMemory
from langchain_core.output_parsers import StrOutputParser
import re

db_uri = "mysql+mysqlconnector://root:imad123@localhost:3306/shopping_mall"
db = SQLDatabase.from_uri(db_uri)

# Conversation Memory for Context
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

# Fetch database schema dynamically
db_schema = get_database_schema()

# Convert schema to a readable format
schema_text = "\n".join([f"{table}: {', '.join(columns)}" for table, columns in db_schema.items()])

def extract_sql_from_response(response_text):
    """Extract SQL query from LLM response, removing markdown formatting"""
    # Remove markdown code blocks
    cleaned = re.sub(r"```sql|```", "", response_text).strip()
    
    # Extract the first valid SQL statement
    lines = cleaned.split('\n')
    for line in lines:
        line = line.strip()
        if line.lower().startswith(('select', 'insert', 'update', 'delete')):
            return line
    
    return cleaned

def format_query_results(query_result, query):
    """Format database query results into readable text"""
    if not query_result or not isinstance(query_result, list):
        return "No data found."
    
    try:
        # Extract table name from query
        query_lower = query.lower()
        if 'from' in query_lower:
            table_part = query_lower.split('from')[1].strip()
            table_name = table_part.split()[0].strip()
            
            # Get column information
            desc_result = execute_sql_query(f"DESCRIBE {table_name}")
            if desc_result and isinstance(desc_result, list):
                column_names = [desc[0] for desc in desc_result]
            else:
                # Fallback: use generic column names
                column_names = [f"col_{i}" for i in range(len(query_result[0]))]
            
            # Format results
            formatted_results = []
            for row in query_result:
                if len(row) == len(column_names):
                    row_data = ", ".join(f"{col}: {val}" for col, val in zip(column_names, row))
                    formatted_results.append(row_data)
                else:
                    # Fallback formatting
                    formatted_results.append(", ".join(str(val) for val in row))
            
            return " | ".join(formatted_results)
    except Exception as e:
        print(f"Error formatting results: {e}")
        # Fallback: simple formatting
        return " | ".join([", ".join(str(val) for val in row) for row in query_result])

# Process User Query
async def process_query(transcribed_text):
    print("User Query:", transcribed_text)

    # Retrieve past conversation history
    chat_history = memory.load_memory_variables({})["chat_history"]
    
    # Format chat history for the prompt
    chat_history_text = ""
    if chat_history:
        for msg in chat_history[-4:]:  # Last 4 messages for context
            if hasattr(msg, 'content'):
                chat_history_text += f"{msg.content}\n"

    # Generate SQL Query using the corrected function call
    sql_response = query_llama_api(transcribed_text, schema_text, mode="sql")
    print(f"Generated SQL Response: {sql_response}")

    refined_response = "I'm not sure how to answer that. Could you rephrase your question?"

    if isinstance(sql_response, str) and not sql_response.startswith("Error"):
        # Split multiple SQL queries by semicolon and newline
        sql_queries = []
        for q in sql_response.replace('\n', ';').split(';'):
            q = q.strip()
            if q and q.lower().startswith(('select', 'insert', 'update', 'delete')):
                sql_queries.append(q)
        
        print(f"Extracted SQL Queries: {sql_queries}")
        
        # If no valid queries found but response contains "products", fix the table name
        if not sql_queries and "products" in sql_response.lower():
            fixed_query = sql_response.replace("products", "product").strip()
            sql_queries = [fixed_query]
            print(f"Fixed table name. New query: {sql_queries}")
        
        all_results = []
        query_types = []
        
        for sql_query in sql_queries:
            query_result = execute_sql_query(sql_query)
            print(f"Query: {sql_query}")
            print(f"Result: {query_result}")

            if isinstance(query_result, str) and "Error" in query_result:
                all_results.append("Error retrieving data")
                query_types.append("error")
            elif query_result and isinstance(query_result, list) and len(query_result) > 0:
                # Determine query type and format accordingly
                if "price" in sql_query.lower():
                    price_value = str(query_result[0][0]) if query_result[0] else "Not available"
                    all_results.append(price_value)
                    query_types.append("price")
                elif "contact" in sql_query.lower() or "phone" in sql_query.lower():
                    contact_value = str(query_result[0][0]) if query_result[0] else "Not available"
                    all_results.append(contact_value)
                    query_types.append("contact")
                elif "address" in sql_query.lower():
                    address_value = str(query_result[0][0]) if query_result[0] else "Not available"
                    all_results.append(address_value)
                    query_types.append("address")
                else:
                    formatted_data = format_query_results(query_result, sql_query)
                    all_results.append(formatted_data)
                    query_types.append("other")
            else:
                all_results.append("Not available")
                query_types.append("not_found")

        # Generate conversational response based on what was asked
        if all_results:
            response_parts = []
            
            # Check what was asked in the original question
            question_lower = transcribed_text.lower()
            
            for i, (result, q_type) in enumerate(zip(all_results, query_types)):
                if q_type == "price" and "price" in question_lower:
                    if "washing machine" in question_lower:
                        response_parts.append(f"The washing machine costs Rs. {result}")
                    elif "refrigerator" in question_lower:
                        response_parts.append(f"The refrigerator costs Rs. {result}")
                    else:
                        response_parts.append(f"The price is Rs. {result}")
                elif q_type == "contact" and ("contact" in question_lower or "phone" in question_lower):
                    response_parts.append(f"You can contact us at {result}")
                elif q_type == "address" and "address" in question_lower:
                    response_parts.append(f"Our address is {result}")
                elif q_type != "error":
                    response_parts.append(str(result))
            
            # If we didn't generate enough responses, check if queries were missed
            if "contact" in question_lower and not any("contact" in qt for qt in query_types):
                # Generate missing contact query
                contact_query = "SELECT contact_number FROM mall_information LIMIT 1"
                contact_result = execute_sql_query(contact_query)
                if contact_result and len(contact_result) > 0:
                    response_parts.append(f"You can contact us at {contact_result[0][0]}")
            
            if "address" in question_lower and not any("address" in qt for qt in query_types):
                # Generate missing address query
                address_query = "SELECT address FROM mall_information LIMIT 1"
                address_result = execute_sql_query(address_query)
                if address_result and len(address_result) > 0:
                    response_parts.append(f"Our address is {address_result[0][0]}")
            
            refined_response = ". ".join(response_parts) + "." if response_parts else "I couldn't find the information you requested."
        else:
            refined_response = "I couldn't find the information you requested."
    else:
        # Handle non-SQL queries or errors
        chat_context = f"""
        User question: {transcribed_text}
        
        STRICT INSTRUCTIONS:
        - If this is a greeting, respond with only: "Hello! How can I help you?"
        - If asking for help, respond with only: "I can help with store locations, product prices, and mall information."
        - Do NOT add extra conversational text
        - Be direct and brief
        """
        
        refined_response = query_llama_api(chat_context, "", mode="chat")
        
        if not refined_response or "Error" in refined_response:
            refined_response = "I can help with store locations, product prices, and mall information."

    # Save conversation to memory
    memory.save_context({"input": transcribed_text}, {"output": refined_response})

    print("Final Response:", refined_response)
    
    # Handle TTS with error handling
    try:
        await text_to_speech_and_play(refined_response)
    except KeyboardInterrupt:
        print("\nAudio playback interrupted by user.")
    except Exception as e:
        print(f"Error during text-to-speech: {e}")

# Main function
async def main():
    greeting_message = (
        "Hello! Welcome to Peshawar Mall. I'm your AI assistant. How can I assist you today?"
    )

    print(greeting_message)
    
    try:
        await text_to_speech_and_play(greeting_message)
    except Exception as e:
        print(f"Error playing greeting: {e}")

    # Ensure TTS playback is complete before recording
    await asyncio.sleep(1)

    while True:
        try:
            # Record audio only after TTS is done
            audio_file_path = record_audio()
            if not audio_file_path:
                print("Failed to record audio.")
                continue

            transcribed_text = transcribe_audio_to_text(audio_file_path)
            
            if not transcribed_text or transcribed_text.strip() == "":
                print("No speech detected. Please try again.")
                continue

            if any(word in transcribed_text.lower() for word in ["exit", "quit", "bye", "goodbye"]):
                goodbye_message = "Thank you for visiting Peshawar Mall! Have a great day!"
                print(goodbye_message)
                try:
                    await text_to_speech_and_play(goodbye_message)
                except Exception as e:
                    print(f"Error playing goodbye message: {e}")
                break

            await process_query(transcribed_text)
            
        except KeyboardInterrupt:
            print("\nShutting down assistant...")
            break
        except Exception as e:
            print(f"An error occurred: {e}")
            continue

if __name__ == "__main__":
    asyncio.run(main())