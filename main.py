from mailbox_manager import *
from classification import *

def main():
    deans_office_mailbox = ClientMailbox() # represents mailbox
    service = deans_office_mailbox.authorize("credentials.json") # Gmail API manager
    if not os.path.exists("EmailsToRespond"):
        os.mkdir(f"EmailsToRespond")
    deans_office_mailbox.clean_dir_with_mails()
    deans_office_mailbox.read_unread(service) # read unread mails from students, yet only mails with plain tetx, no attachements
    mail_classifier = Classifier()
    mail_classifier.classify_bayes("abcd")
    deans_office_mailbox.generate_response()

main()

