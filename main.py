import google.generativeai as genai
from flask import Flask,request,jsonify,render_template
import requests
import os
import fitz
from mimetypes import guess_type
import psycopg2
from datetime import datetime,timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from pathlib import Path

db=False
send_report=False
wa_token=os.environ.get("WA_TOKEN") # Whatsapp API Key
gen_api=os.environ.get("GEN_API") # Gemini API Key
owner_phone=os.environ.get("OWNER_PHONE") # Owner's phone number with countrycode
model_name="gemini-1.5-flash-latest"

folder=Path("product_images")
product_images=[file.stem for file in folder.iterdir() if file.is_file()]
product_images=list(map(lambda i:i.replace(" ","_"),product_images))

app=Flask(__name__)
genai.configure(api_key=gen_api)
generation_config = {
  "temperature": 1,
  "top_p": 0.95,
  "top_k": 0,
  "max_output_tokens": 8192,
}

safety_settings = [
  {"category": "HARM_CATEGORY_HARASSMENT","threshold": "BLOCK_MEDIUM_AND_ABOVE"},
  {"category": "HARM_CATEGORY_HATE_SPEECH","threshold": "BLOCK_MEDIUM_AND_ABOVE"},  
  {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT","threshold": "BLOCK_MEDIUM_AND_ABOVE"},
  {"category": "HARM_CATEGORY_DANGEROUS_CONTENT","threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

model = genai.GenerativeModel(model_name=model_name,
                              generation_config=generation_config,
                              safety_settings=safety_settings)

convo = model.start_chat(history=[])

with open("instructions.txt","r") as f:
    commands=f.read()
convo.send_message(commands)


def send(answer,sender,phone_id):
    url = f"https://graph.facebook.com/v19.0/{phone_id}/messages"
    headers = {
        'Authorization': f'Bearer {wa_token}',
        'Content-Type': 'application/json'
    }
    data = {
        "messaging_product": "whatsapp",
        "to": sender,
        "type": "text",
        "text": {"body": answer},
    }
    response = requests.post(url, headers=headers, json=data)
    return response


def send_media(filename,sender,phone_id):
    file_type=guess_type(filename)[0]
    url_upload=f"https://graph.facebook.com/v20.0/{phone_id}/media"
    headers={
        'Authorization':f'Bearer {wa_token}'
    }
    files={
        'file':('file',open(filename,'rb'),file_type)
    }
    data={
        'messaging_product':'whatsapp',
        'type':file_type
    }
    response1=requests.post(url_upload,headers=headers,files=files,data=data)
    if response1.status_code==200:
        media_id=response1.json()["id"]
        url_send=f"https://graph.facebook.com/v19.0/{phone_id}/messages"
        headers2={
            'Authorization':f'Bearer {wa_token}',
            'Content-Type':'application/json'
        }
        data = {
            "messaging_product": "whatsapp",
            "to": sender,
            "type": file_type.split("/")[0],
            file_type.split("/")[0]: {
                "id": media_id,
                "caption":(filename.split("\\")[1]).split(".")[0]
            }
        }
        response2=requests.post(url_send, headers=headers2, json=data)
        if response2.status_code==200:
            url_delete=f"https://graph.facebook.com/v20.0/{media_id}"
            requests.delete(url_delete,headers=headers)

    else:print("send_media function failed to send image")

def remove(*file_paths):
    for file in file_paths:
        if os.path.exists(file):
            os.remove(file)
        else:pass

if db:
    db_url=os.environ.get("POSTGRES_URL") # Database URL
    connect=psycopg2.connect(db_url)
    cursor=connect.cursor()

    def insert_chat(sender,message):
        cursor.execute("INSERT INTO chats (sender,message) VALUES (%s,%s)",(sender,message))
        connect.commit()
        cursor.close()

    def get_chats(sender):
        cursor.execute("SELECT chat_text FROM chats WHERE sender = %s", (sender,))
        chats=cursor.fetchall()
        cursor.close()
        return chats
    
    def delete_old_chats():
        cutoff_date = datetime.now() - timedelta(days=14)
        cursor.execute("DELETE FROM chats WHERE timestamp < %s", (cutoff_date,))
        connect.commit()
        cursor.close()
    
    def create_report():
        today=datetime.today().strftime('%d-%m-%Y')
        query = f"SELECT chat_content FROM chats WHERE date_trunc('day', chat_timestamp) = %s"
        cursor.execute(query, (today,))
        chats = cursor.fetchall()
        doc = fitz.open()
        page = doc.new_page()
        text = f"Chat Report for {today}\n\n"
        for content in chats:
            text += f"{content[0]}\n\n"
        page.insert_text((100, 100), text)
        path=f"/tmp/chat_report_{today}.pdf"
        doc.save(path)
        doc.close()
        cursor.close()
        connect.close()
        return path

    def send_daily_report(phone_id):
        pdf_path = create_report()
        if pdf_path:
            send_media(pdf_path,owner_phone,phone_id)
        else:
            print("Failed to create PDF report.")
    notification=lambda message,phone_id:send(message,owner_phone,phone_id)
else:pass

def message_handler(data,phone_id):
    sender=data["from"]
    if data["type"] == "text":
        prompt = data["text"]["body"]
        convo.send_message(prompt)
    else:
        media_url_endpoint = f'https://graph.facebook.com/v19.0/{data[data["type"]]["id"]}/'
        headers = {'Authorization': f'Bearer {wa_token}'}
        media_response = requests.get(media_url_endpoint, headers=headers)
        media_url = media_response.json()["url"]
        media_download_response = requests.get(media_url, headers=headers)
        if data["type"] == "audio":filename = "/tmp/temp_audio.mp3"
        elif data["type"] == "image":filename = "/tmp/temp_image.jpg"
        elif data["type"] == "document":
            doc=fitz.open(stream=media_download_response.content,filetype="pdf")
            for _,page in enumerate(doc):
                destination="/tmp/temp_image.jpg"
                pix = page.get_pixmap()
                pix.save(destination)
                file = genai.upload_file(path=destination,display_name="tempfile")
                response = model.generate_content(["What is this",file])
                answer=response._result.candidates[0].content.parts[0].text
                convo.send_message(f'''Direct image input has limitations,
                                       so this message is created by an llm model based on the image prompt of user, 
                                       reply to the customer assuming you saw that image 
                                       (Warn the customer and stop the chat if it is not related to the business): {answer}''')
                remove(destination)
        else:send("This format is not Supported by the bot ☹",sender,phone_id)
        if data["type"] == "image" or data["type"] == "audio":
            with open(filename, "wb") as temp_media:
                temp_media.write(media_download_response.content)
            file = genai.upload_file(path=filename,display_name="tempfile")
            response = model.generate_content(["What is this",file])
            answer=response._result.candidates[0].content.parts[0].text
            remove("/tmp/temp_image.jpg","/tmp/temp_audio.mp3")
            convo.send_message(f'''Direct media input has limitations,
                               so this message is created by an llm model based on the image prompt of user, 
                               reply to the customer assuming you saw that image 
                               (Warn the customer and stop the chat if it is not related to the business): {answer}''')
        files=genai.list_files()
        for file in files:
            file.delete()
    reply=convo.last.text
    if "unable_to_solve_query" in reply:
        send(f"customer {sender} is not satisfied", owner_phone, phone_id)
        reply=reply.replace("unable_to_solve_query",'\n')
        send(reply, sender, phone_id)
            
    elif any(f'{i}_image' in reply for i in product_images):
        for i in product_images:
            if f'{i}_image' in reply:
                reply=reply.replace(f"{i}_image",'\n')
                image=i.replace("_"," ")
                try:
                    product_path = os.path.join("product_images", f"{image}.jpg")
                except:send("An error occurred while loading the image",sender,phone_id)
                if os.path.exists(product_path):send_media(product_path,sender,phone_id)
                else:send("Unable to load images",sender,phone_id)
                break
        send(reply, sender, phone_id)
        
    else:send(reply,sender,phone_id)

@app.route("/", methods=["GET", "POST"])
def index():
    return render_template("connected.html")

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        if mode == "subscribe" and token == "BOT":
            return challenge, 200
        else:
            return "Failed", 403
    elif request.method == "POST":
        try:
            data = request.get_json()["entry"][0]["changes"][0]["value"]["messages"][0]
            phone_id=request.get_json()["entry"][0]["changes"][0]["value"]["metadata"]["phone_number_id"]
            message_handler(data,phone_id)
        except :pass
        return jsonify({"status": "ok"}), 200
    else:return "WhatsApp Bot is Running"
      
if __name__ == "__main__":
    app.run(debug=True, port=8000)
