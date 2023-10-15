from flask import Flask, request, jsonify
import openai
import re
import os
import requests
import psycopg2
import subprocess


app = Flask(__name__)

openai.api_key = os.environ.get('OPENAI_API_KEY', None)

def predict_answer(question, model_name):
    # Establishing a connection to the database
    conn = psycopg2.connect(
        host = os.getenv("DB_HOST"),
        database = os.getenv("DB_NAME"),
        user = os.getenv("DB_USER"),
        password = os.getenv("DB_PASSWORD"),
                             port = os.getenv("PORT"))
    
    # Creating a cursor to interact with the database
    cursor = conn.cursor()
    
    # Query to fetch modelname_timestamp based on a condition on another column
    query = f"SELECT openai_model_name FROM openai_model_name WHERE model_name='{model_name}'"
    # trained_model_id = None
    try:
        # Executing the query
        cursor.execute(query)

        # Fetching the results
        results = cursor.fetchall()
        # print(results)
        trained_model_id = results[-1][0]

    except psycopg2.Error as e:
        print("Error executing query:", e)
    finally:
        # Closing the cursor and connection
        cursor.close()
        conn.close()
    # Your model prediction code here
    prom = f'Question:{question}\nAnswer:'
    print(prom, trained_model_id)
    try:
        response = openai.Completion.create(
            model = trained_model_id,  ##"davinci:ft-p2e-pro:sach-bot1-2023-05-02-09-04-23",
            prompt = prom,
            # stop = ["\n", "END"],
            temperature = 1,
            n = 2,
            best_of = 2,
            max_tokens = 200,
            presence_penalty=1,
            frequency_penalty=1
        )

        answer = response.choices[0].text.lstrip().rstrip()
        print("Answer = " + str(answer))


        # Handle the error or exception appropriately
    except openai.error.APIError as e:
        # Handle API error here, e.g. retry or log
        print(f"OpenAI API returned an API Error: {e}")
        answer = "Sorry I Don't Know the Answer"
    except openai.error.APIConnectionError as e:
        # Handle connection error here
        print(f"Failed to connect to OpenAI API: {e}")
        answer = "Sorry I Don't Know the Answer"
    except openai.error.RateLimitError as e:
        # Handle rate limit error (we recommend using exponential backoff)
        print(f"OpenAI API request exceeded rate limit: {e}")
        answer = "Sorry I Don't Know the Answer"
    except Exception as e:
        answer = "Sorry I Don't Know the Answer " + str(e)

    patterns = ['END OF QUESTION', 'QUESTION', 'Question']
    for pattern in patterns:
        match = re.search(re.escape(pattern), answer)
        if match:
            left_part = answer[:match.start()]
            answer = left_part
        else:
            answer = answer

    def run_rasa_server(trained_model_id):
        command = f"rasa run -m models/{trained_model_id} --enable-api --cors '*'"
        subprocess.run(command, shell=True)
        #command = ["rasa", "run", "-m", f"models/{trained_model_id}", "--enable-api", "--cors", "'*'"]

    if __name__ == "__main__":
        run_rasa_server(trained_model_id)

    def run_custom_action_server():
        action_command = "rasa run actions"
        subprocess.run(action_command, shell=True)

    if __name__ == "__main__":
        run_custom_action_server()

    #run_rasa_server(trained_model_id)

    ##Rasa prediction

    def send_message_to_rasa_bot(question):
        url = "http://localhost:5005/webhooks/rest/webhook"
        data = {"sender": "user", "message": question}
        response = requests.post(url, json=data)
        return response.json()

    # while True:
        #question = input("You: ")
        # if question.lower() == "stop":
        #     break

    response = send_message_to_rasa_bot(question)
    if response:
        # print(response)
        print("Bot:", response[0]['text'])

        answer=response[0]['text']


    return answer

# Endpoint for model prediction
@app.route('/', methods = ["POST"])
def predict():

    question = request.args.get("question")
    model_name = request.args.get("model_name")
    translation_required = request.args.get("translation_required")

    if translation_required.lower() == "yes" or translation_required.lower() == "y":
        source_language_code = request.args.get("source_language_code")
        endpoint = f"https://translateapi-dev.sach.org.in/?source_language={source_language_code}&target_language=en&input_text={question}"

        text_in_english =  requests.post(endpoint).text                                    
        answer = predict_answer(text_in_english, model_name)
        print(answer)
        
        endpoint_for_reverse_translation =  f"https://translateapi-dev.sach.org.in/?source_language=en&target_language={source_language_code}&input_text={answer}"
        
        reverse_answer = requests.post(endpoint_for_reverse_translation).text
        print(reverse_answer)
        return reverse_answer
    else:
        answer = predict_answer(question, model_name)
        return jsonify(answer)


if __name__ == '__main__':
    app.run(host = "0.0.0.0", debug=True)

