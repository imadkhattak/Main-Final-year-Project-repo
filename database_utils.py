import mysql.connector
from config import DB_CONFIG



def get_database_schema():
    """Retrieves all tables and their respective columns from the database."""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()

        # Fetch all tables
        cursor.execute("SHOW TABLES")
        tables = [table[0] for table in cursor.fetchall()]

        schema = {}

        # Fetch column names for each table
        for table in tables:
            cursor.execute(f"DESCRIBE {table}")
            columns = [column[0] for column in cursor.fetchall()]
            schema[table] = columns  # Store columns under respective table

        cursor.close()
        connection.close()

        return schema

    except mysql.connector.Error as e:
        print(f"Database Schema Retrieval Error: {e}")
        return {}
    


# 🛠 **Fix: Add execute_sql_query() function**
def execute_sql_query(query):
    """Executes a given SQL query and returns the results."""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        cursor.execute(query)
        result = cursor.fetchall()  # Fetch all results

        cursor.close()
        connection.close()

        return result

    except mysql.connector.Error as e:
        print(f"SQL Execution Error: {e}")
        return f"Error: {e}"