from flask import Flask, request, jsonify
import openai
import re
import boto3
import os
import datetime
import time
import json
import psycopg2
import requests
import pandas as pd


app = Flask(__name__)

openai.api_key = os.getenv('OPENAI_API_KEY', None)


@app.route('/', methods=['POST'])
def re_train():
    user_name = request.args.get('username')
    model_name = request.args.get('model_name')

    # Establishing a connection to the database
    conn = psycopg2.connect(
        host = os.getenv("DB_HOST"),
        database = os.getenv("DB_NAME"),
        user = os.getenv("DB_USER"),
        password = os.getenv("DB_PASSWORD")
    )
    # Creating a cursor to interact with the database
    cursor = conn.cursor()
    # Query to fetch modelname_timestamp based on a condition on another column
    query = f"SELECT openai_model_name FROM openai_model_name WHERE model_name = %s"
    pre_trained_model_id = None
    try:
        # Executing the query
        cursor.execute(query, (f"{user_name}_{model_name}",))
        # Fetching the results
        results = cursor.fetchall()
        print(results)
        # Printing the fetched data
        pre_trained_model_id = results[-1][0]
        print(pre_trained_model_id)

    except psycopg2.Error as e:
        print("Error executing query:", e)
    finally:
        # Closing the cursor and connection
        cursor.close()
        conn.close()

    def call_mongodb_to_s3_api(user_name, model_name):
        # Make API call with user name and model name as parameters
        end_point = "https://mongos3api-dev.sach.org.in/"
        api_url = f'{end_point}?user_name={user_name}&model_name={model_name}'
        #payload = {'user_name': user_name, 'model_name': model_name}

        try:
            response = requests.post(api_url)

            if response.status_code == 200:
                # API call successful
                print(f"API request successful with status code {response.status_code}")
            else:
                # API call unsuccessful
                print(f"API request failed with status code {response.status_code}")

        except Exception as e:
                print("An error occurred during the API request: " + str(e))

    call_mongodb_to_s3_api(user_name, model_name)

    def download_data_from_s3(bucket_name, prefix, user_name, model_name, destination_directory):
        s3 = boto3.client('s3', use_ssl = True,
                                        aws_access_key_id = os.getenv("aws_access_key_id"),
                                                aws_secret_access_key = os.getenv("aws_secret_access_key"))
        downloaded_files = []

        try:
            response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
            if 'Contents' in response:
                for obj in response['Contents']:
                    file_name = obj['Key']
                    print("file = ", file_name)
                    print()
                    destination_file_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', os.path.basename(file_name))
                    destination_path = os.path.join(destination_directory, destination_file_name)
                    s3.download_file(bucket_name, file_name, destination_path)
                    print(
                        f"Data downloaded from S3 bucket: s3://{bucket_name}/{user_name}/{model_name}/ to {destination_path}")
                    downloaded_files.append(destination_path)

                combined_data = []
                for file_path in downloaded_files:
                    print(file_path)
                    with open(file_path, 'r') as file:
                        file_data = json.load(file)
                        combined_data.extend(file_data)

                combined_file_path = os.path.join(destination_directory, f'combined_data_{user_name}_{model_name}.json')
                with open(combined_file_path, 'w') as combined_file:
                    json.dump(combined_data, combined_file)

                print(f"Combined data saved to: {combined_file_path}")
            else:
                print(f"No objects found in S3 bucket with prefix: {prefix}")

        except Exception as e:
            print(f"Error occurred while downloading data from S3 bucket: {e}")

    # Usage example
    bucket_name = 'chatinputdata'
    # user_name = 'IBM'
    # model_name = 'GPT'
    # file_name = None
    prefix = f'{user_name}/{model_name}/'
    destination_directory = f'retraining_files/{user_name}/{model_name}/'
    print(destination_directory)

    if not os.path.exists(destination_directory):
        os.makedirs(destination_directory)

    download_data_from_s3(bucket_name, prefix, user_name, model_name, destination_directory)
    #file_path=f"/path/to/save/downloaded/files/{file_name}"
    file_path=f'retraining_files/{user_name}/{model_name}/combined_data_{user_name}_{model_name}.json'

    with open(file_path, 'r') as file:
        json_data = json.load(file)

    df = pd.DataFrame(json_data)

    jsonl_data = df.to_json(orient='records', lines=True)

    jsonl_data = jsonl_data.replace("Question", "prompt").replace("Answer", "completion")

    file_uploaded_to_openai = openai.File.create(
        file=jsonl_data,
        purpose='fine-tune'
    )
    training_file_id = file_uploaded_to_openai["id"]

    #model_name = f"{user_name}_{model_name}"
    fine_tune_job = openai.FineTune.create(training_file=training_file_id,
                                           model=pre_trained_model_id,
                                           n_epochs=5)
    fine_tune_id = fine_tune_job["id"]
    print(fine_tune_id)

    start_time = datetime.datetime.now()  # Start tracking the time

    # Retrieve the status of the fine-tune job
    status = openai.FineTune.retrieve(id=fine_tune_id)["status"]

    # Check the status of the fine-tune job
    while status in ["pending", "running"]:
        if status == "failed":
            print("The fine-tune job failed.")
            break
        else:
            if status == "pending":
                current_time = datetime.datetime.now()
                elapsed_time = (current_time - start_time).total_seconds()
                if elapsed_time > 600:  # If pending for more than 2 minutes, cancel the job
                    openai.FineTune.cancel(id=fine_tune_id)
                    print("The fine-tune job has been canceled as it was pending for more than 10 minutes.")
                    break
                else:
                    print("The fine-tune job is pending. Waiting...")
            elif status == "running":
                print("The fine-tune job is running. Waiting...")
            time.sleep(30)  # Wait for 30 seconds before checking the status again
            status = openai.FineTune.retrieve(id=fine_tune_id)["status"]
            print(status)

    end_time = datetime.datetime.now()  # Stop tracking the time
    total_time_seconds = (end_time - start_time).total_seconds()
    total_time_minutes = total_time_seconds / 60
    print("Total time taken for fine-tuning: {:.2f} seconds ({:.2f} minutes)".format(total_time_seconds,
                                                                                     total_time_minutes))

    if status == "succeeded":
        fine_tuned_model_id = openai.FineTune.retrieve(id=fine_tune_id)["fine_tuned_model"]
        print(fine_tuned_model_id)

        # endpoint = f'https://openaiapi-dev.sach.org.in/?username={user_name}&model_name={model_name}&openai_model_name={fine_tuned_model_id}'  # Replace with the actual API endpoint
        #
        # call_openai_model_api(endpoint)
        return jsonify('Model trained successfully')
    return jsonify({"status": status})


if __name__ == '__main__':
    app.run(host = "0.0.0.0", debug = True)