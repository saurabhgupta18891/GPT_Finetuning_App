from flask import Flask, request
import pymongo
import os

# Registering an App
app = Flask(__name__)

@app.route("/", methods = ["POST"])
def onboard_user():
    try:
        json_data = request.get_json()
        if json_data:
            print(json_data)
            username = json_data["username"]
            model_name = json_data["model_name"]
            mdb_client = pymongo.MongoClient(os.getenv("DB_HOST"))
            db = mdb_client["modeltrainmdb"]
            collection = db[f"{username}_{model_name}_Retraining_Data_To_Be_Used"]
            
            # print(len(json_data["Question"]))
            if isinstance(json_data["Question"], list):
                for key, value in zip(json_data["Question"], json_data["Answer"]):
                    collection.insert_one({"Question" : key, "Answer" : value})
            elif isinstance(json_data["Question"], str):
                collection.insert_one({"Question" : json_data["Question"], "Answer" : json_data["Answer"]})
            else:
                raise ValueError("Data Type not supported!")
        # if len(json_data) > 1:
        #     collection.insert_many(jsonify(json_data))
        # elif len(json_data) == 1:
        #     collection.insert_one(json_data)
        else:
            raise "No Data Provided"
        
        
        return "Data Added Successfully"
    
    except Exception as e:
        print(str(e))
        return (str(e))
        
    
    

if __name__ == '__main__':
    app.run(host = "0.0.0.0", debug=True)
