import abc
import base64
import mimetypes
import os
import re
from base64 import urlsafe_b64decode, urlsafe_b64encode
from email import mime
from email.message import EmailMessage
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials # for authorization to Gmail
from google_auth_oauthlib.flow import InstalledAppFlow # for OAuth2 authorization
from googleapiclient.discovery import build
from email.mime.multipart import MIMEMultipart # for structure of the message
import shutil
from abc import ABC, abstractmethod
from googleapiclient.errors import HttpError
from get_essential_info_from_text import NameSearcher
from response_generation import GptManager
from database_manager import  Database
import magic
import json

import base64

def decode_base64(data):
    """
       Decode base64 string with padding correction.

       :param data: base64 encoded string
       :return: decoded utf-8 string
    """
    missing_padding = len(data) % 4
    if missing_padding:
        data += '=' * (4 - missing_padding)
    return base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')

# get content of unread students mails from deans office mailbox
class EmailReader(ABC):
    """Abstract base class for reading emails."""
    @abc.abstractmethod
    def read_message(self, service, message, which_mail):
        pass

    @abc.abstractmethod
    def read_unread(self, service):
        pass


class MailSender(ABC):
    """Abstract base class for generating and sending emails."""
    @classmethod
    def generate_simple_response(cls, category, path, response_file):
        """
        Generate a simple canned response based on classification category and write it to file.

        :param category: classification category of the email
        :param path: directory path where response file will be saved
        :param response_file: full path to response file
        """
        # generating responses and writing them to appriopriate files
        # creating file with the result of classification
        with open("simple_responses.json", 'r', encoding='utf-8') as file:
            response_dict = json.load(file)
        with open(response_file, 'w+') as c:
            c.write(str(response_dict[category]))

    def add_attachments(self, path_to_dir_with_attachments, classification_result, msg):
        """
        Add attachments from a directory to the email message.

        :param path_to_dir_with_attachments: base directory with attachment folders
        :param classification_result: classification category (folder name)
        :param msg: EmailMessage object to add attachments to
        """
        for root, dirs, files in os.walk(path_to_dir_with_attachments):
            for file in files:
                if root ==  os.path.join(path_to_dir_with_attachments, classification_result):
                    with open(os.path.join(root, file), "rb") as att:
                        attachment_data = att.read()
                        attachment_name = os.path.basename(os.path.join(root, file))
                        msg.add_attachment(
                            attachment_data,
                            maintype="application",
                            subtype="octet-stream",
                            filename=attachment_name)

    @abstractmethod
    def generate_ai_response(self, dir_name):
        pass

    @abstractmethod
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
        self.db_session = Database.make_db()
        self.response_generator = GptManager(self.db_session)
        self.name_searcher = NameSearcher(self.db_session)
        self.service = self.authorize("credentials.json")  # Gmail API manager

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

    def save_attachment(self, data_b64, original_filename, dir_with_mails, i):
        """
        Save email attachment to local file after checking attachment extension.

        :param data_b64: base64 encoded attachment data
        :param original_filename: original filename of the attachment
        :param dir_with_mails: directory path to save attachments
        :param i: attachment index for unique naming
        """
        # decoding data
        try:
            file_data = base64.urlsafe_b64decode(data_b64.encode('utf-8'))
        except Exception as e:
            print(f"Decoding error base64: {e}")
            return

        # guess MIME type basing on binary data
        mime_type = magic.from_buffer(file_data, mime=True)
        extension = mimetypes.guess_extension(mime_type) or ''
        # save the attachement in mail directory
        path = os.path.join(dir_with_mails, f"Attachement{i}.{extension}")
        try:
            with open(path, 'wb') as f:
                f.write(file_data)
            print(f"Attachment from mail stored at\n: {path} \n(typ: {mime_type})")
            i += 1
        except Exception as e:
            print(f"Błąd zapisu pliku: {e}")

    def read_message(self, service, message, which_mail):
        """
           Reads mails and saves them into the project directory

           :param service: Gmail API manager
           :param message: mail
           :param which_mail: number of read mail
           :return: None
        """
        os.mkdir(rf"EmailsToRespond\Mail{which_mail}")
        email = service.users().messages().get(userId='me', id=message['id'], format='full').execute() # full info about mail
        # parts can be the message body, or attachments
        payload = email['payload'] # main info about  email
        with open(rf"EmailsToRespond\Mail{which_mail}\mail_id.txt", "w+") as id:
            id.write(message['id'])
        headers = payload.get("headers") # header of an email
        parts = payload.get("parts") # parts of an email: attachments, text, images etc.
        sender_essential_data = None
        if headers:
            # this section prints email basic info & creates a folder for the email
            for header in headers:
                name = header.get("name")
                value = header.get("value")
                if name.lower() == 'from':
                    with open(rf"EmailsToRespond\Mail{which_mail}\src_address.txt", "w+") as src:
                        src.write(value)
                if name.lower() == "to":
                    with open(rf"EmailsToRespond\Mail{which_mail}\dst_address.txt", "w+") as dest:
                        dest.write(value)
                if name.lower() == "date":
                    with open(rf"EmailsToRespond\Mail{which_mail}\date.txt", "w+") as dt:
                        dt.write(value)
                if name.lower() == "subject":
                    with open(rf"EmailsToRespond\Mail{which_mail}\subject.txt", "w+") as sb:
                        sb.write(value)
        if parts:
            i=0
            for part in parts:
                mime1 = part.get("mimeType", "")
                try:
                    if part.get("mimeType") == "text/plain":
                        body = part.get("body")
                        if body:  # body of an email
                            data = body.get("data")  # data email was received to the mailbox
                            if data:
                                mail_content = urlsafe_b64decode(
                                    data).decode()  # changing format to print top the console
                                with open(rf"EmailsToRespond\Mail{which_mail}\plain_text.txt", "w+") as pl:
                                    pl.write(mail_content)
                                sender_essential_data = self.name_searcher.text_ner_analizer(mail_content)
                    elif part.get("mimeType") == "multipart/alternative":
                        internal_parts = part.get("parts")
                        if internal_parts:  # body of an email
                            for internal_part in internal_parts:
                                if internal_part.get("mimeType") == "text/plain":
                                    internal_body = internal_part.get("body")
                                    if internal_body:  # body of an email
                                        internal_data = internal_body.get("data")  # data email was received to the mailbox
                                        if internal_data:
                                            mail_content = decode_base64(internal_data)  # changing format to print top the console
                                            with open(rf"EmailsToRespond\Mail{which_mail}\plain_text.txt", "w+") as pl:
                                                pl.write(mail_content)
                                            sender_essential_data = self.name_searcher.text_ner_analizer(mail_content)
                    elif re.match(r"application/\w+", mime1):
                        body = part.get("body")
                        if body:  # body of an email
                            if part.get("body").get("attachmentId"):
                                att_id = part.get("body").get("attachmentId")
                                att = service.users().messages().attachments().get(userId="me",  messageId=message['id'],                                                                                      id=att_id).execute()
                                data_b64 = att['data']
                                self.save_attachment(data_b64,part['filename'],rf"EmailsToRespond\Mail{which_mail}",i )
                    else:
                        pass
                except HttpError as error:
                    att = None

            with open(f"EmailsToRespond\\Mail{which_mail}\\personal_sender_data.json", "w+") as pers:
                if sender_essential_data:
                    json.dump(sender_essential_data, pers, ensure_ascii=False, indent=4)

    def mark_mail_as_read(self, service, path):
        with open(os.path.join(path, "mail_id.txt"), "r") as f:
            id_m = f.read()
        service.users().messages().modify(
            userId='me',
            id=id_m,
            body={'removeLabelIds': ['UNREAD']}
        ).execute()

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

    def generate_ai_response(self, dir_name):
        """Generate AI responses for saved emails using Mistral Gpt model"""
        self.response_generator.generate_responses(dir_name)

    def clean_dir_with_mails(self):
        """
        Cleans the directory containing saved emails by deleting all files and subdirectories.

        This method removes all files and symbolic links inside the directory specified by
        `self.path_to_dir`. It also recursively deletes all subdirectories within that directory.
        It is called every time the application is being used to delete old mails from the previous mailbox scan.

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
            with open(os.path.join(path_to_mail , "classification_result.txt"), "r") as res:
                category = res.read()
            self.add_attachments("attachements", category, message)

            # encoded message
            encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

            create_message = {"raw": encoded_message}
            send_message = (
                service.users()
                .messages()
                .send(userId="me", body=create_message)
                .execute()
            )
            self.mark_mail_as_read(service, path_to_mail)
        except HttpError as error:
            print(f"An error occurred: {error}")
            send_message = None


