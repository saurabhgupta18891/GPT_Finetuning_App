from flask import Flask, request, jsonify
import pymongo
import boto3
import os
import json
from datetime import datetime

# Registering an App
app = Flask(__name__)

@app.route("/", methods = ["POST"])
def onboard_user():
    try:
        username = request.args.get("username")
        model_name = request.args.get("model_name")
        mongo_db_collection_name = f"{username}_{model_name}_Retraining_Data_To_Be_Used"

        mdb_client = pymongo.MongoClient(os.getenv("DB_HOST"))
        db = mdb_client["modeltrainmdb"]
        collection = db[mongo_db_collection_name]

        json_data = list(collection.find({}, {"_id" : 0}))

        if len(json_data) >= 1:
            json_data = json.dumps(json_data)
            s3_client = boto3.client(service_name = "s3", use_ssl = True,
                                        aws_access_key_id = os.getenv("aws_access_key_id"),
                                                aws_secret_access_key = os.getenv("aws_secret_access_key"))
            
            s3_client.put_object(Body = json_data, Bucket = "chatinputdata", Key = f"{username}/{model_name}/{datetime.now()}.json")
        else:
            raise ValueError(f"No Data exist for the user '{username}' & their model '{model_name}'")
           
        return jsonify("Data Uploaded Successfully")
    
    except Exception as e:
        print(str(e))
        return (str(e))
        
    
if __name__ == '__main__':
    app.run(host = "0.0.0.0", debug=True)
