from flask import Flask, request, jsonify
from flask_pymongo import PyMongo
import pandas as pd
import json
from datetime import datetime
import os
import time
import openai
import requests
import glob


app = Flask(__name__)
app.config['MONGO_URI'] = "mongodb+srv://gptmodelmdbuser:bKJeEwjnzjMHFJ4G@dev-coredb.3stdb.mongodb.net/gptmodelmdb?retryWrites=true&w=majority"
mongo = PyMongo(app)
openai.api_key = os.environ.get('OPENAI_API_KEY', None)

def call_openai_model_api(endpoint):
    try:
        # Make the API request
        response = requests.post(endpoint)
        print(endpoint)
        print(response)

        # Check the response status code
        if response.status_code == 200:
            # API call successful
            print(f"API request successful with status code {response.status_code}")
        else:
            # API call unsuccessful
            print(f"API request failed with status code {response.status_code}")

    except Exception as e:
        print("An error occurred during the API request: " + str(e))


@app.route('/train', methods=['GET','POST'])
def train_model():
    print(request.files)
    print(request.files["filename"])
    if 'filename' in request.files:
        # CSV file upload case
        file = request.files['filename']
        print(file.filename)

        filename = file.filename
        file_ext = os.path.splitext(filename)[1]

        user_name = request.form.get('username')
        model_name = request.form.get('model_name')

        # Check if the file extension is allowed
        if file_ext.lower() == ".csv":
            df = pd.read_csv(file)
            user_collection = f'{user_name}_{model_name}_Training_Data'

            # Check if the collection already exists
            collection_exists = user_collection in mongo.db.list_collection_names()

            # Convert DataFrame to JSON format
            json_data = df.to_json(orient = 'records')
            # print(json_data)

            # Store the JSON data in the corresponding collection
            collection = mongo.db[user_collection]
            collection.insert_many(json.loads(json_data))

            if collection_exists:
                print(f"{len(df)} documents added to existing collection.")
            else:
                print(f"{len(df)} documents added to new collection.")

            # print(jsonl_data)
            json_data = df.to_json(orient = 'records', lines = True)
            jsonl_data = json_data.replace("Question", "prompt").replace("Answer", "completion")

            file_uploaded_to_openai = openai.File.create(
                file = jsonl_data,
                purpose='fine-tune'
            )
            training_file_id = file_uploaded_to_openai["id"]
            
            model_name = f"{user_name}_{model_name}"
            fine_tune_job = openai.FineTune.create(training_file = training_file_id,
                                                   model = "ada", suffix = model_name,
                                                   n_epochs = 5)
            fine_tune_id = fine_tune_job["id"]
            print(fine_tune_id)

            start_time = datetime.now()  # Start tracking the time

            # Retrieve the status of the fine-tune job
            status = openai.FineTune.retrieve(id = fine_tune_id)["status"]

            # Check the status of the fine-tune job
            while status in ["pending", "running"]:
                if status == "failed":
                    print("The fine-tune job failed.")
                    break
                else:
                    if status == "pending":
                        current_time = datetime.now()
                        elapsed_time = (current_time - start_time).total_seconds()
                        if elapsed_time > 600:  # If pending for more than 2 minutes, cancel the job
                            openai.FineTune.cancel(id = fine_tune_id)
                            print("The fine-tune job has been canceled as it was pending for more than 10 minutes.")
                            break
                        else:
                            print("The fine-tune job is pending. Waiting...")
                    elif status == "running":
                        print("The fine-tune job is running. Waiting...")
                    time.sleep(30)  # Wait for 30 seconds before checking the status again
                    status = openai.FineTune.retrieve(id = fine_tune_id)["status"]
                    print(status)

            end_time = datetime.now()  # Stop tracking the time
            total_time_seconds = (end_time - start_time).total_seconds()
            total_time_minutes = total_time_seconds / 60
            print("Total time taken for fine-tuning: {:.2f} seconds ({:.2f} minutes)".format(total_time_seconds, total_time_minutes))

            if status == "succeeded":
                fine_tuned_model_id = openai.FineTune.retrieve(id=fine_tune_id)["fine_tuned_model"]
                print(fine_tuned_model_id)

                endpoint = f'https://openaiapi-dev.sach.org.in/?username={user_name}&model_name={model_name}&openai_model_name={fine_tuned_model_id}'  # Replace with the actual API endpoint

                call_openai_model_api(endpoint)
                return jsonify('Data stored in respective collection and Model trained successfully')
            # return jsonify({"status": status})
        # return jsonify("Data stored in respective collection")
    
        elif file_ext.lower() == ".xlsx":
            df = pd.read_excel(file)
            user_collection = f'{user_name}_{model_name}_Training_Data'

            # Check if the collection already exists
            collection_exists = user_collection in mongo.db.list_collection_names()

            # Convert DataFrame to JSON format
            json_data = df.to_json(orient = 'records')
            # print(json_data)

            # Store the JSON data in the corresponding collection
            collection = mongo.db[user_collection]
            collection.insert_many(json.loads(json_data))

            if collection_exists:
                print(f"{len(df)} documents added to existing collection.")
            else:
                print(f"{len(df)} documents added to new collection.")

            json_data = df.to_json(orient = 'records', lines = True)
            jsonl_data = json_data.replace("Question", "prompt").replace("Answer", "completion")

            file_uploaded_to_openai = openai.File.create(
                file = jsonl_data,
                purpose='fine-tune'
            )
            training_file_id = file_uploaded_to_openai["id"]
            
            model_name = f"{user_name}_{model_name}"
            fine_tune_job = openai.FineTune.create(training_file = training_file_id,
                                                   model = "ada", suffix = model_name,
                                                   n_epochs = 5)
            fine_tune_id = fine_tune_job["id"]
            print(fine_tune_id)

            start_time = datetime.now()  # Start tracking the time

            # Retrieve the status of the fine-tune job
            status = openai.FineTune.retrieve(id = fine_tune_id)["status"]

            # Check the status of the fine-tune job
            while status in ["pending", "running"]:
                if status == "failed":
                    print("The fine-tune job failed.")
                    break
                else:
                    if status == "pending":
                        current_time = datetime.now()
                        elapsed_time = (current_time - start_time).total_seconds()
                        if elapsed_time > 600:  # If pending for more than 2 minutes, cancel the job
                            openai.FineTune.cancel(id = fine_tune_id)
                            print("The fine-tune job has been canceled as it was pending for more than 10 minutes.")
                            break
                        else:
                            print("The fine-tune job is pending. Waiting...")
                    elif status == "running":
                        print("The fine-tune job is running. Waiting...")
                    time.sleep(30)  # Wait for 30 seconds before checking the status again
                    status = openai.FineTune.retrieve(id = fine_tune_id)["status"]
                    print(status)

            end_time = datetime.now()  # Stop tracking the time
            total_time_seconds = (end_time - start_time).total_seconds()
            total_time_minutes = total_time_seconds / 60
            print("Total time taken for fine-tuning: {:.2f} seconds ({:.2f} minutes)".format(total_time_seconds, total_time_minutes))

            if status == "succeeded":
                fine_tuned_model_id = openai.FineTune.retrieve(id=fine_tune_id)["fine_tuned_model"]
                print(fine_tuned_model_id)

                endpoint = f'https://openaiapi-dev.sach.org.in/?username={user_name}&model_name={model_name}&openai_model_name={fine_tuned_model_id}'  # Replace with the actual API endpoint

                call_openai_model_api(endpoint)
                return jsonify('Data stored in respective collection and Model trained successfully')
            return jsonify({"status": status})


        def get_latest_model_name_rasa():
            models_dir = r"C:\Users\Saurabh.Gupta\PycharmProjects\Rasa_P2E1\models"  # Replace this with the actual path to your Rasa project's models directory
            model_dirs = glob.glob(os.path.join(models_dir, "*"))
            latest_model_dir = max(model_dirs, key=os.path.getctime)
            model_name = os.path.basename(latest_model_dir)
            return model_name

        # Example usage:
        latest_model_name_rasa = get_latest_model_name_rasa()
        #print("Latest model name:", latest_model_name)

        endpoint = f'https://openaiapi-dev.sach.org.in/?username={user_name}&model_name={model_name}&openai_model_name={latest_model_name_rasa}'

        call_openai_model_api(endpoint)


        return jsonify("Data stored in respective collection")

    else:
        # Single question-answer pair case
        user_name = request.args.get('username')
        model_name = request.args.get('model_name')
        question = request.args.get('question')
        answer = request.args.get('answer')

        # Create collection name using user_id and model_name
        user_collection = f'{user_name}_{model_name}_Training_Data'

        # Check if the collection already exists
        collection_exists = user_collection in mongo.db.list_collection_names()

        # Store the question and answer in the corresponding collection
        collection = mongo.db[user_collection]
        collection.insert_one({'Question': question, 'Answer': answer})

        if collection_exists:
            print("Question and answer pair added to existing collection.")
        else:
            print("Question and answer pair added to new collection.")

    # Fetch the collection names
    collection_names = mongo.db.list_collection_names()

    # Print the collection names
    # for collection_name in collection_names:
    #     print(collection_name)

    # # Fetch data from a collection
    # collection = mongo.db[user_collection]
    # for document in collection.find():
    #     print(document)

    return jsonify("data stored in form of question_answer pair")


if __name__ == '__main__':
    app.run(host = "0.0.0.0", debug=True)
