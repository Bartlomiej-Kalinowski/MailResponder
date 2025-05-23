from mailbox_manager import *
from classification import *
import re
import os

def main():
    deans_office_mailbox = ClientMailbox() # represents mailbox
    service = deans_office_mailbox.authorize("credentials.json") # Gmail API manager
    main_path = "EmailsToRespond"
    if not os.path.exists(main_path):
        os.mkdir(main_path)
    deans_office_mailbox.clean_dir_with_mails()
    deans_office_mailbox.read_unread(service) # read unread mails from students, yet only mails with plain text, no attachements
    mail_classifier = Classifier()
    mail_classifier.classify_bayes("abcd")
    # deans_office_mailbox.generate_simple_response()
    deans_office_mailbox.generate_ai_response()
    pattern = re.compile(r'^Mail\d+$')  # to find dirs like Mail1, Mail2 that represents mails in project dirs structure
    for item in os.listdir(main_path):
        item_path = os.path.join(main_path, item)
        if os.path.isdir(item_path) and pattern.match(item):
            deans_office_mailbox.send_message(service,item_path)

main()

