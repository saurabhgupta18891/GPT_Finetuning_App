from flask import Flask, request
import psycopg2
import os

# Registering an App
app = Flask(__name__)

@app.route("/", methods = ["POST"])
def onboard_user():
    try:
        username = request.args.get("username")
        model_name = request.args.get("model_name")
        openai_model_name = request.args.get("openai_model_name")
        connection = psycopg2.connect(database = os.getenv("DB_NAME"), user = os.getenv("USERNAME"),
                                   password = os.getenv("PASSWORD"),
                              host = os.getenv("HOST"), port = os.getenv("PORT"))
    
        cursor = connection.cursor()
        cursor.execute("insert into openai_model_name (username, model_name, openai_model_name) values ('{}', '{}', '{}');".format(username, model_name, openai_model_name))
        return "OpenAI Model Name Added Successfully"
    
    except Exception as e:
        print(str(e))
        return (str(e))
    finally:
        connection.commit()
        cursor.close()
        connection.close()
        
    
    

if __name__ == '__main__':
    app.run(host = "0.0.0.0", debug=True)
