import requests
import os
from database_manager import *

API_KEY = "ePpQoHNpsWS4ge3gDX2HL3V0O87tgeTx"
API_URL = "https://api.mistral.ai/v1/chat/completions"

class GptManager(object):
    def __init__(self, data_session):
        self.database = data_session
        self.headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }

    def generate_one_response(self, mail_category,mail_content, file_to_write):
        if mail_category == 'student_id_extension':
            pass
        elif mail_category == 'grade_change':
            pass
        elif mail_category == 'office_hours':
            all_hours = self.database.query(DeansOfficeHours).all()
            hours_data = [h.table_to_dict() for h in all_hours]
            hours_to_prompt = json.dumps(hours_data, indent=2, ensure_ascii=False)
            data = {
                "model": "mistral-medium",
                "messages": [
                    {"role": "system",
                     "content": """You are a system to respond student mails to dean's office. " +
                                "Mail should be formal and content every elements that mail has."
                                "Write ONLY mail, without any other text e.x without text such as \"This is mail:\" 
                                and don't write subcject of the mail in the response"""},
                    {"role": "user",
                     "content": f"""Classify a student's mail in which the student ask what are the opening hours.
                     This is students mail: {mail_content}
                     Here is the json file with dean's offce opening and closing hours during the week: {hours_to_prompt}"""}
                ],
                "temperature": 0.7  # model creativity index
            }

            response = requests.post(API_URL, headers=self.headers, json=data)

            if response.status_code == 200:
                result = response.json()
                generated_email = result["choices"][0]["message"]["content"]
                print("Wiadomosc:\n",generated_email)
                folder_path = "EmailsToRespond"
                file_to_write.write(str(generated_email))
            else:
                print("Blad:", response.status_code, response.text)

        elif mail_category == 'scholarship':
            all_scholarships = self.database.query(ScholarshipValue).all()
            scholarship_data = [s.table_to_dict() for s in all_scholarships]
            scholarship_to_prompt = json.dumps(scholarship_data,indent=2,ensure_ascii=False)
            data = {
                "model": "mistral-medium",
                "messages": [
                    {"role": "system",
                     "content": """You are a system to respond student mails to dean's office. " +
                                           "Mail should be formal and content every elements that mail has."
                                           "Write ONLY mail, without any other text e.x without text such as \"This is mail:\" 
                                           and don't write subcject of the mail in the response"""},
                    {"role": "user",
                     "content": f"""Classify a student's mail in which the student asks about scholarships at the university.
                                This is students mail: {mail_content}
                                Here is the json file with dean's offce opening and closing hours during the week: {scholarship_to_prompt}"""}
                ],
                "temperature": 0.7  # model creativity index
            }

            response = requests.post(API_URL, headers=self.headers, json=data)

            if response.status_code == 200:
                result = response.json()
                generated_email = result["choices"][0]["message"]["content"]
                print("Wiadomosc:\n", generated_email)
                folder_path = "EmailsToRespond"
                file_to_write.write(str(generated_email))
            else:
                print("Blad:", response.status_code, response.text)
        else:
            pass

    def generate_responses(self):
        folder_path = "EmailsToRespond"
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                mail_text_file = os.path.join(root, file)
                if file == "classification_result.txt":
                    with open(mail_text_file, "r") as c_res:
                        mail_topic = c_res.read()
                        # creating file with the result of classification
                        generated_response = os.path.join(root, "response.txt")
                        with open(generated_response, 'w') as c:
                            plain_text_file = os.path.join(root, "plain_text.txt")
                            with open(plain_text_file, 'r') as f:
                                plain_text = f.read()
                                self.generate_one_response(str(mail_topic), str(plain_text), c)
                dirs.clear()


