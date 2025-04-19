import os
from base64 import urlsafe_b64decode, urlsafe_b64encode
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials # for authorization to Gmail
from google_auth_oauthlib.flow import InstalledAppFlow # for OAuth2 authorization
from googleapiclient.discovery import build
from email.mime.multipart import MIMEMultipart # for structure of the message
import shutil

# path to credentials.json file (Google API Console)
CLIENT_SECRETS_FILE = "credentials.json"

# privileges to gmail tools( to read and send emails)
PRIVILEGES = ['https://www.googleapis.com/auth/gmail.modify']


# class manage access to mailbox
# enables authorization process using OAuth2 auth. method
# enables to interact with Gmail API
class ClientMailbox(object):
    def __init__(self):
        self.__message = MIMEMultipart() # creating an object that represents an email with MIME interface
        self.__credentials = None  # authorization data to gmail account
        self.__sender = self.recipient = self.subject = self.body = None # single mail data
        self.__gmail_api_manager = None # enables to interact with Gmail API

    def authorize(self):
        if os.path.exists('token.json'):  # does token.json file(with authorization data) exists
            self.__credentials = Credentials.from_authorized_user_file('token.json', PRIVILEGES)
        # if authorization data arent available user have to log in
        else: # json file does not exist
            if self.__credentials and self.__credentials.expired and self.__credentials.refresh_token: # token is invalid
                self.__credentials.refresh(Request())
            else: # authorization for the first time
                flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE,PRIVILEGES)  # getting authorization data
                self.__credentials = flow.run_local_server(port=0) # open the inetrnet site to authorize manually for the first time
            # save authorization data
            with open('token.json', 'w') as token:
                token.write(self.__credentials.to_json())
        self.__gmail_api_manager = build('gmail', 'v1', credentials=self.__credentials)  # creating GMAILS API manager
        return self.__gmail_api_manager


# get content of unread students mails from deans office mailbox
class EmailReader(object):
    def __init__(self):
       self.path_to_dir = "EmailsToRespond"


    def clean_dir_with_mails(self):
        for element in os.listdir(self.path_to_dir):
            full_path = os.path.join(self.path_to_dir, element)
            try:
                if os.path.isfile(full_path) or os.path.islink(full_path):
                    os.unlink(full_path)  # usuwa plik lub dowiązanie
                elif os.path.isdir(full_path):
                    shutil.rmtree(full_path)  # usuwa cały podfolder
            except Exception as e:
                print(f'Bład przy usuwaniu {full_path}: {e}')


    def read_message(self, service, message, which_mail):
        os.mkdir(f"EmailsToRespond\\Mail{which_mail}")
        email = service.users().messages().get(userId='me', id=message['id'], format='full').execute() # full info about mail
        # parts can be the message body, or attachments
        payload = email['payload'] # main info about  email
        headers = payload.get("headers") # header of an email
        parts = payload.get("parts") # parts of an email: attachments, text, images etc.
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
                        text = urlsafe_b64decode(data).decode() # changing format to print top the console
                        with open(f"EmailsToRespond\\Mail{which_mail}\\plain_text.txt", "w+") as pl:
                            pl.write(text)
        else:
            # Jeśli parts jest puste, pobierz treść z payload.body.data
            body = payload.get("body", {}).get("data")
            if body:
                text = urlsafe_b64decode(body).decode() # changing format to print top the console
                with open(f"EmailsToRespond\\Mail{which_mail}\\plain_text.txt", "w+") as pl:
                    pl.write(text)


    def read_unread(self, service):
        # Pobierz listę nieprzeczytanych wiadomości
        result = service.users().messages().list(userId='me', q="is:unread from:@student.uksw.edu.pl").execute()
        messages = result.get("messages", []) # messages is a list of dictonaries, these dictionaries represents mails
        i = 0
        for msg in messages:# for each mail
            i += 1
            self.read_message(service, msg, i)
        return False


def main():

    deans_office_mailbox = ClientMailbox() # represents mailbox
    service = deans_office_mailbox.authorize() # Gmail API manager
    mail_reader = EmailReader() # represents part of a program that reads emails from a mailbox
    if not os.path.exists("EmailsToRespond"):
        os.mkdir(f"EmailsToRespond")
    mail_reader.clean_dir_with_mails()
    mail_reader.read_unread(service) # read unread mails from students, yet only mails with plain tetx, no attachements


main()

