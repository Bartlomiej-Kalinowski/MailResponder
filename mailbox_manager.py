import abc
import base64
import os
from base64 import urlsafe_b64decode, urlsafe_b64encode
from email.message import EmailMessage
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials # for authorization to Gmail
from google_auth_oauthlib.flow import InstalledAppFlow # for OAuth2 authorization
from googleapiclient.discovery import build
from email.mime.multipart import MIMEMultipart # for structure of the message
import shutil
from abc import ABC, abstractmethod
from googleapiclient.errors import HttpError
from get_essential_info_from_text import *
from response_generation import *


# get content of unread students mails from deans office mailbox
class EmailReader(ABC):
    @abc.abstractmethod
    def read_message(self, service, message, which_mail):
        pass

    @abc.abstractmethod
    def read_unread(self, service):
        pass


class MailSender(ABC):
    @abstractmethod
    def generate_simple_response(self):
        pass

    def send_message(self,service,  path_to_mail):
        pass


# class manage access to mailbox
# enables authorization process using OAuth2 auth. method
# enables to interact with Gmail API
class ClientMailbox(EmailReader, MailSender):
    """
        Dean's office mailbox manager.
        Enables authorization and uses the Gmail API.

        Attributes:
            sender (str): The dean's office mailbox address.
            recipient(str): Student's mailbox address
            message(MIMEMultipart):  object that represents an email
            credentials (str): authorization data to gmail account
            subject(str): subject of an email
            body(str): main content of the email
            gmail_api_manager (object): A Resource object for interacting with the Gmail API service.
            path_to_dir(str): path to a directory to save emails read from the mailbox
            response(dict): dict of emails responses related to classification result
    """
    def __init__(self):
        self.message = MIMEMultipart() # creating an object that represents an email with MIME interface
        self.credentials = None  # authorization data to gmail account
        self.sender = None
        self.recipient = None
        self.subject = None
        self.body = None # single mail data
        self.gmail_api_manager = None # enables to interact with Gmail API
        self.path_to_dir = "EmailsToRespond"
        self.response = {"student_id_extension": "Response id", "grade_change": "response_grade",
                         "office_hours": "response_hours",
                         "scholarship": "res_scholarship"}
        self.db_session = Database.make_db(r'DB_init\application.pdf')
        self.response_generator = GptManager(self.db_session)
        self.name_searcher = NameSearcher(self.db_session)

    def authorize(self, client_secrets_file):
        """
            Authorizes access to Gmail using the OAuth2 method and sets the gmail_api_manager value.

            :param client_secrets_file:file with credentials to Gmail API

            :return: A Resource object for interacting with the Gmail API.
        """
        if os.path.exists('token.json'):  # does token.json file(with authorization data) exists
            self.credentials = Credentials.from_authorized_user_file('token.json', ['https://www.googleapis.com/auth/gmail.modify'])
        # if authorization data arent available user have to log in
        else: # json file does not exist
            if self.credentials and self.credentials.expired and self.credentials.refresh_token: # token is invalid
                self.credentials.refresh(Request())
            else: # authorization for the first time
                flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file,['https://www.googleapis.com/auth/gmail.modify'])  # getting authorization data
                self.credentials = flow.run_local_server(port=0) # open the inetrnet site to authorize manually for the first time
            # save authorization data
            with open('token.json', 'w') as token:
                token.write(self.credentials.to_json())
        self.gmail_api_manager = build('gmail', 'v1', credentials=self.credentials)  # creating GMAILS API manager
        return self.gmail_api_manager

    def read_message(self, service, message, which_mail):
        """
           Reads mails and saves them into the project directory

           :param service: Gmail API manager
           :param message: mail
           :param which_mail: number of read mail
           :return: None
        """
        os.mkdir(f"EmailsToRespond\\Mail{which_mail}")
        email = service.users().messages().get(userId='me', id=message['id'], format='full').execute() # full info about mail
        # parts can be the message body, or attachments
        payload = email['payload'] # main info about  email
        headers = payload.get("headers") # header of an email
        parts = payload.get("parts") # parts of an email: attachments, text, images etc.
        sender_essential_data = None
        if headers:
            # this section prints email basic info & creates a folder for the email
            for header in headers:
                name = header.get("name")
                value = header.get("value")
                if name.lower() == 'from':
                    # we print the From address
                    with open(f"EmailsToRespond\\Mail{which_mail}\\src_address.txt", "w+") as src:
                        src.write(value)
                if name.lower() == "to":
                    # we print the To address
                    with open(f"EmailsToRespond\\Mail{which_mail}\\dst_address.txt", "w+") as dest:
                        dest.write(value)
                if name.lower() == "date":
                    # we print the date when the message was sent
                    with open(f"EmailsToRespond\\Mail{which_mail}\\date.txt", "w+") as dt:
                        dt.write(value)
                if name.lower() == "subject":
                    # we print the date when the message was sent
                    with open(f"EmailsToRespond\\Mail{which_mail}\\subject.txt", "w+") as sb:
                        sb.write(value)
        if parts:
            for part in parts:
                if part.get("mimeType") == "text/plain":
                    # if the email part is text plain
                    body = part.get("body") # body of an email
                    data = body.get("data") # data email was received to the mailbox
                    if data:
                        mail_content = urlsafe_b64decode(data).decode() # changing format to print top the console
                        with open(f"EmailsToRespond\\Mail{which_mail}\\plain_text.txt", "w+") as pl:
                            pl.write(mail_content)
                        sender_essential_data = self.name_searcher.text_ner_analizer(mail_content)

        else:
            # if parts is empty get content from payload.body.data
            body = payload.get("body", {}).get("data")
            if body:
                mail_content = urlsafe_b64decode(body).decode() # changing format to print top the console
                with open(f"EmailsToRespond\\Mail{which_mail}\\plain_text.txt", "w+") as pl:
                    pl.write(mail_content)
                sender_essential_data = self.name_searcher.text_ner_analizer(mail_content)
        with open(f"EmailsToRespond\\Mail{which_mail}\\personal_sender_data.json", "w+") as pers:
            if sender_essential_data:
                json.dump(sender_essential_data, pers, ensure_ascii=False, indent=4)

    def read_unread(self, service):
        """
            Searches the mailbox and returns unread messages from students.

            :param service: Gmail API manager
            :return: False if no unread emails from students else calls read_message() method
            :rtype: boolean
        """
        # getting list of unread mails from students
        result = service.users().messages().list(userId='me', q="is:unread from:@student.uksw.edu.pl").execute()
        messages = result.get("messages", []) # messages is a list of dictonaries, these dictionaries represents mails
        i = 0
        for msg in messages:# for each mail
            i += 1
            self.read_message(service, msg, i)
        return False

    def generate_simple_response(self):
        """
            Generate response related to the result of mail classification using gpt model
            and write the response into the same directory where mail was saved

            :return: None
        """
        # generating responses and writing them to appriopriate files
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
                            c.write(str(self.response[mail_topic]))
                dirs.clear()

    def generate_ai_response(self):
        self.response_generator.generate_responses()

    def clean_dir_with_mails(self):
        """
            cleans files in directory with saved mails with mails saved in the previous application use

            :return: None
        """
        for element in os.listdir(self.path_to_dir):
            full_path = os.path.join(self.path_to_dir, element)
            try:
                if os.path.isfile(full_path) or os.path.islink(full_path):
                    os.unlink(full_path)  # usuwa plik lub dowiązanie
                elif os.path.isdir(full_path):
                    shutil.rmtree(full_path)  # usuwa cały podfolder
            except Exception as e:
                print(f'Bład przy usuwaniu {full_path}: {e}')

    def send_message(self, service, path_to_mail):
        """
            sends answer mail to a student

            :param service: Gmail API manager
            :param path_to_mail: path to directory with mail
            :return: None
        """
        try:
            message = EmailMessage()
            with open (os.path.join(path_to_mail , "response.txt"), "r") as response:
                message.set_content(response.read())


            with open (os.path.join(path_to_mail ,"src_address.txt"), "r") as to:
                message["To"] = to.read()
            with open(os.path.join(path_to_mail , "dst_address.txt"), "r") as fr:
                message["From"] = fr.read()
            with open(os.path.join(path_to_mail , "subject.txt"), "r") as subj:
                message["Subject"] = subj.read()

            # encoded message
            encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

            create_message = {"raw": encoded_message}
            send_message = (
                service.users()
                .messages()
                .send(userId="me", body=create_message)
                .execute()
            )
            print(f'Message Id: {send_message["id"]}')
        except HttpError as error:
            print(f"An error occurred: {error}")
            send_message = None


