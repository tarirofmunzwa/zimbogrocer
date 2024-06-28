import google.generativeai as genai
from flask import Flask,request,jsonify,render_template
import requests
import os
import fitz
from mimetypes import guess_type
import psycopg2
from datetime import datetime,timedelta
from pathlib import Path
from urlextract import URLExtract
from  PIL import Image
from io import BytesIO
from training import instructions
import sched
import time


db=False
wa_token=os.environ.get("WA_TOKEN") # Whatsapp API Key
gen_api=os.environ.get("GEN_API") # Gemini API Key
owner_phone=os.environ.get("OWNER_PHONE") # Owner's phone number with countrycod
model_name="gemini-1.5-flash-latest"

folder=Path("product_images")
product_images=[file.stem for file in folder.iterdir() if file.is_file()]
product_images=list(map(lambda i:i.replace(" ","_"),product_images))

app=Flask(__name__)
genai.configure(api_key=gen_api)

extractor=URLExtract(limit=1)

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

convo.send_message(instructions.instructions)

with open("products.txt","r") as f:
    products=f.read()
    convo.send_message(f"Here are the links for products images:\n\n{products}")


def send(answer,sender,phone_id):
    url = f"https://graph.facebook.com/v19.0/{phone_id}/messages"
    headers = {
        'Authorization': f'Bearer {wa_token}',
        'Content-Type': 'application/json'
    }
    type="text"
    body="body"
    content=answer
    urls=extractor.find_urls(answer)
    if len(urls)>0:
        mime_type,_=guess_type(urls[0].split("/")[-1])
        type=mime_type.split("/")[0]
        body="link"
        content=urls[0]
        answer=answer.replace(urls[0],"\n")
    data = {
        "messaging_product": "whatsapp",
        "to": sender,
        "type": type,
        type: {
            body:content,
            **({"caption":answer} if type!="text" else {})
        },
    }
    response = requests.post(url, headers=headers, json=data)
    if db:
        insert_chat("Bot",answer)
    return response

def remove(*file_paths):
    for file in file_paths:
        if os.path.exists(file):
            os.remove(file)
        else:pass

if db:
    db_url=os.environ.get("POSTGRES_URL") # Database URL
    connect=psycopg2.connect(db_url)
    cursor=connect.cursor()
    scheduler = sched.scheduler(time.time, time.sleep)
    report_time = datetime.now().replace(hour=22, minute=00, second=0, microsecond=0)

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
    
    def create_report(phone_id):
        today=datetime.today().strftime('%d-%m-%Y')
        query = f"SELECT chat_content FROM chats WHERE date_trunc('day', chat_timestamp) = %s"
        cursor.execute(query, (today,))
        chats = cursor.fetchall()
        if chats !="":
            chats=today+"\n\n"+chats
            send(chats,owner_phone,phone_id)
        cursor.close()
        connect.close()

else:pass

notification=lambda message,phone_id:send(message,owner_phone,phone_id)

def message_handler(data,phone_id):
    sender=data["from"]
    if data["type"] == "text":
        prompt = data["text"]["body"]
        insert_chat(sender,prompt)
        convo.send_message(prompt)
    else:
        media_url_endpoint = f'https://graph.facebook.com/v19.0/{data[data["type"]]["id"]}/'
        headers = {'Authorization': f'Bearer {wa_token}'}
        media_response = requests.get(media_url_endpoint, headers=headers)
        media_url = media_response.json()["url"]
        media_download_response = requests.get(media_url, headers=headers)
        if data["type"] == "audio":
            filename = "/tmp/temp_audio.mp3"
        elif data["type"] == "image":
            filename = "/tmp/temp_image.jpg"
        elif data["type"] == "document":
            doc=fitz.open(stream=media_download_response.content,filetype="pdf")
            for _,page in enumerate(doc):
                destination="/tmp/temp_image.jpg"
                pix = page.get_pixmap()
                pix.save(destination)
                file = genai.upload_file(path=destination,display_name="tempfile")
                response = model.generate_content(["Read this document carefully and explain it in detail",file])
                answer=response._result.candidates[0].content.parts[0].text
                convo.send_message(f'''Direct image input has limitations,
                                    so this message is created by an llm model based on the document send by the user, 
                                    reply to the customer assuming you saw that document.
                                    (Warn the customer and stop the chat if it is not related to the business): {answer}''')
                remove(destination)
        else:send("This format is not Supported by the bot ☹",sender,phone_id)
        if data["type"] == "image" or data["type"] == "audio":
            with open(filename, "wb") as temp_media:
                temp_media.write(media_download_response.content)
            file = genai.upload_file(path=filename,display_name="tempfile")
            if data["type"] == "image":
                response = model.generate_content(["What is in this image?",file])
                answer=response.text
                convo.send_message(f'''Customer has sent an image,
                                    So here is the llm's reply based on the image sent by the customer:{answer}\n\n''')
                urls=extractor.find_urls(convo.last.text)
                if len(urls)>0:
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
                    response=requests.get(urls[0],headers=headers)
                    img=Image.open(BytesIO(response.content))
                    response=model.generate_content(["Is the things in both the images are exactly same? Explain in detail",img,file])
                    answer=response.text
                    convo.send_message(f'''This is the message from AI after comparing the two images: {answer}''')
            else:
                response = model.generate_content(["What is the content of this audio file?",file])
                answer=response.text
                convo.send_message(f'''Direct media input has limitations,
                                            so this message is created by an llm model based on the audio send by the user, 
                                            reply to the customer assuming you heard that audio.
                                            (Warn the customer and stop the chat if it is not related to the business): {answer}''')
            remove("/tmp/temp_image.jpg","/tmp/temp_audio.mp3")
        files=genai.list_files()
        for file in files:
            file.delete()
    reply=convo.last.text
    if "unable_to_solve_query" in reply:
        send(f"customer {sender} is not satisfied", owner_phone, phone_id)
        reply=reply.replace("unable_to_solve_query",'\n')
        send(reply, sender, phone_id)
    else:send(reply,sender,phone_id)
    if db:
        scheduler.enterabs(report_time.timestamp(), 1, create_report, (phone_id,))
        scheduler.run()
        delete_old_chats()

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

if __name__ == "__main__":app.run(debug=True, port=8000)
