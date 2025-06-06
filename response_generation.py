import requests
import os
from sympy import false
from database_manager import  DeansOfficeHours, ScholarshipValue
import json

API_KEY = "ePpQoHNpsWS4ge3gDX2HL3V0O87tgeTx"
API_URL = "https://api.mistral.ai/v1/chat/completions"

class GptManager(object):
    """
      Manager class for generating responses to student emails using the Mistral AI API.

      Attributes
      ----------
      database : Session
          Database session used to query additional information such as office hours or scholarship details.
      headers : dict
          HTTP headers including authorization and content-type for API requests.
      """
    def __init__(self, data_session):
        """
        Initializes the GptManager instance.

        Parameters
        ----------
        data_session : Session
            Database session for executing queries.
        """
        self.database = data_session
        self.headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }

    def generate_one_response(self, mail_category,mail_content, dir_to_write):
        """
        Generates a response based on the email category and content, then writes it to a file.
        Sends a POST request to the Mistral AI API with a prompt tailored to the email category.
        If the request fails, it falls back to a simple response generator from MailSender.

        Parameters
        ----------
        mail_category : str
            Category of the email (e.g. 'student_id_extension', 'grade_change_from_other_university', 'office_hours', 'scholarship').
        mail_content : str
            Content of the student's email used as input for response generation.
        dir_to_write : str
            Directory path where the generated response file will be saved.
        """
        from mailbox_manager import MailSender

        if mail_category == 'student_id_extension':
            data = {
                "model": "mistral-medium",
                "messages": [
                    {"role": "system",
                     "content": """You are a system to respond student mails to dean's office. " +
                                            "Mail should be formal and content every elements that mail has."
                                            "Write ONLY mail, without any other text e.x without text such as \"This is mail:\" 
                                            and don't write subcject of the mail in the response"""},
                    {"role": "user",
                     "content": f"""Classify a student's mail in which the student asks about how to extend student id validity.
                                 This is students mail: {mail_content}
                                 """}
                ],
                "temperature": 0.7  # model creativity index
            }

            response = requests.post(API_URL, headers=self.headers, json=data)

            if response.status_code == 200:
                result = response.json()
                generated_email = result["choices"][0]["message"]["content"]
                with open(os.path.join(dir_to_write, "response.txt"), 'w+') as r:
                    r.write(str(generated_email))
            else:
                MailSender.generate_simple_response('student_id_extension', dir_to_write, os.path.join(dir_to_write, "response.txt"))

        elif mail_category == 'grade_change_from_other_university':
            data = {
                "model": "mistral-medium",
                "messages": [
                    {"role": "system",
                     "content": """You are a system to respond student mails to dean's office. " +
                                            "Mail should be formal and content every elements that mail has."
                                            "Write ONLY mail, without any other text e.x without text such as \"This is mail:\" 
                                            and don't write subcject of the mail in the response"""},
                    {"role": "user",
                     "content": f"""Classify a student's mail in which the student asks about transfering a grade from the other univeristy.
                                 This is students mail: {mail_content}"""}
                ],
                "temperature": 0.7  # model creativity index
            }

            response = requests.post(API_URL, headers=self.headers, json=data)

            if response.status_code == 200:
                result = response.json()
                generated_email = result["choices"][0]["message"]["content"]
                with open(os.path.join(dir_to_write, "response.txt"), 'w+') as r:
                    r.write(str(generated_email))
            else:
                MailSender.generate_simple_response('grade_change_from_other_university', dir_to_write, os.path.join(dir_to_write, "response.txt"))

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
                with open(os.path.join(dir_to_write, "response.txt"), 'w+') as r:
                    r.write(str(generated_email))
            else:
                MailSender.generate_simple_response('office_hours', dir_to_write,
                                                    os.path.join(dir_to_write, "response.txt"))

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
                with open(os.path.join(dir_to_write, "response.txt"), 'w+') as r:
                    r.write(str(generated_email))
            else:
                MailSender.generate_simple_response('scholarship', dir_to_write, os.path.join(dir_to_write, "response.txt"))
        else:
            pass


    def generate_responses(self, dir_name):
        """
        Processes all emails in the 'EmailsToRespond' folder by reading classification results
        and plain text content, then generates and writes responses for each email.

        Behavior
        --------
        Walks through the 'EmailsToRespond' directory recursively.
        For each email folder containing both 'classification_result.txt' and 'plain_text.txt',
        reads their content, calls generate_one_response to create a response,
        and clears mail_topic and mail_content to process the next email.
        """
        folder_path = rf"EmailsToRespond\{dir_name}"
        mail_topic = None
        mail_content = None
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file =="classification_result.txt":
                    mail_cls_file = os.path.join(root, file)
                    with open(mail_cls_file, "r") as c_res:
                        mail_topic = c_res.read()
                if file == "plain_text.txt":
                    mail_pl_file = os.path.join(root, "plain_text.txt")
                    with open(mail_pl_file, "r") as pl:
                        mail_content = pl.read()
                if mail_topic and mail_content:
                    self.generate_one_response(str(mail_topic), str(mail_content), folder_path)
                    mail_topic = None
                    mail_content = None
                dirs.clear()



