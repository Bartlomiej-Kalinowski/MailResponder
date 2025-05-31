from mailbox_manager import *
from classification import *
import re
import os
from tkinter import *
from database_manager import *

"""
Main module for managing the Dean's Office email processing system.

This script:
- Authorizes and connects to Gmail API.
- Cleans the directory used to store email data.
- Reads unread emails from the mailbox.
- Classifies emails using a Bayes classifier.
- Generates AI-based responses.
- Sends replies to the respective students.

Functions:
    main(): Orchestrates the entire email processing workflow.
"""

class Application(Frame):
    def __init__(self, master, mailbox_manager):
        self.db_session = mailbox_manager.db_session
        super(Application, self).__init__(master)
        self.grid()
        self.mailbox = mailbox_manager
        self.create_widgets(master)

    def create_widgets(self, win):
        Button(win, text="Exit", command=lambda: win.destroy()).grid(row=0, column=0, padx=5)
        i = 0
        row = 1
        for dir_name in os.listdir("EmailsToRespond"):
            dir_path = os.path.join("EmailsToRespond", dir_name)
            tmp = Application.check_mail_dirs(dir_path)
            if len(tmp) == 4:
                self.create_one_widget(win, tmp[0], tmp[1], tmp[2], tmp[3], i, dir_name, row)
                if i % 3 == 2:
                    row += 1
                i += 1


    def create_one_widget(self, root_win, src_address,  date, subject , plain_text, i, dir_name, row):
        col = i % 3  # ex. 0, 1, 0, 1, 0, 1,...
        btn = Button(root_win, text=dir_name,
                     command=lambda s=subject, f=src_address, b=plain_text, d=date:
                     self.open_mail_window( s, f, b, d, dir_name))
        btn.grid(row=row, column=col, padx=10, pady=5, sticky="ew")

    @staticmethod
    def check_mail_dirs(dir_path):
        if not os.path.isdir(dir_path):
            return 0
        # Iterate over files in each subdirectory
        for file_name in os.listdir(dir_path):
            file_path = os.path.join(dir_path, file_name)
            if os.path.isfile(file_path):
                if file_name == "src_address.txt":
                    with open(file_path, "r") as src:
                        src_address = src.read()
                if file_name == "date.txt":
                    with open(file_path, "r") as dt:
                        date = dt.read()
                if file_name == "subject.txt":
                    with open(file_path, "r") as subj:
                        subject = subj.read()
                if file_name == "plain_text.txt":
                    with open(file_path, "r") as pt:
                        plain_text = pt.read()
        return [src_address, date, subject, plain_text]

    def open_mail_window(self, subject, sender, body, date,dir_name):
        win = Toplevel()
        win.title(dir_name)
        Label(win, text=f"TITLE: {subject}", font=("Arial", 10)).grid(row=0, column=0, sticky="w", padx=10, pady=(10, 0))
        Label(win, text=f"FROM: {sender}", font=("Arial", 10)).grid(row=1, column=0, sticky="w", padx=10, pady=(10, 0))
        Label(win, text=f"DATE: {date}", font=("Arial", 10)).grid(row=2, column=0, sticky="w", padx=10, pady=(10, 0))
        Label(win, text="BODY:\n",  wraplength=380, justify='left', font=("Arial", 10)).grid(row=3, column=0, sticky="w", padx=10, pady=(10, 0))
        Label(win, text=f"{body}", wraplength=380, justify='left', font=("Arial", 10, "bold")).grid(row=4,column=0,sticky="w",padx=10,pady=(10, 0))

        # --- Kontener na info i przycisk ---
        control_frame = Frame(win)
        control_frame.grid(row=5, column=0, sticky="w", padx=10, pady=5)

        Label(control_frame, text="Do you want to generate response automatically?").grid(row=0, column=0, sticky="w")
        Button(control_frame, text="Generate response", command= lambda:self.edit_response(dir_name)).grid(row=0,column=1, padx=5)
        Button(control_frame, text="Send", command=lambda: self.send_mail("EmailsToRespond", dir_name, win)).grid(row=0,
                                                                                                           column=2,
                                                                                                           padx=5)
        Button(control_frame, text="Exit", command=lambda: win.destroy()).grid(row=0, column=3,padx=5)

    def get_edited_text(self,text_box,win, dir_name):
        content = text_box.get("1.0", "end-1c")
        win.destroy()
        path = rf"EmailsToRespond\{dir_name}\response.txt"
        with open(path, "w") as r:
            r.write(content)

    def edit_response(self, dir_name):
        # Tworzymy edytowalne pole tekstowe
        win = Toplevel()
        win.title("Edit response")
        text_box = Text(win,  height=10, width=50, wrap="word")
        text_box.grid(row=0, column=0, padx=10, pady=10)
        self.mailbox.generate_ai_response(dir_name)
        # Dodajemy przykładowy tekst
        with open(rf"EmailsToRespond\{dir_name}\response.txt", "r") as f:
            res = f.read()
        text_box.insert("1.0", res)
        # Przycisk do pobierania tekstu
        Button(win, text="Finish editing response", command=lambda: self.get_edited_text(text_box, win, dir_name)).grid(row=1
                                                                                                                 , column=0
                                                                                                                 , padx=20
                                                                                                                 , pady=20)


    def check_if_student_exists(self, id_s, name, surname):
        all_students= self.db_session.query(StudentList).all()
        students_data = [s.table_to_dict() for s in all_students]
        for student in students_data:
            if student['student_id'].lower() == id_s and student['name'].lower() == name and student['surname'].lower() == surname:
                return True
        return False

    def send_and_close(self,  win, _item_path, mail_win):
        self.mailbox.send_message(self.mailbox.service, _item_path)
        win.destroy()
        mail_win.destroy()

    def send_mail(self, main_path,  dir_name, mail_win):
        item_path = os.path.join(main_path, dir_name)
        response_file = os.path.join(item_path, "response.txt")
        if os.path.isdir(item_path) and os.path.isfile(response_file):
            with open(os.path.join(item_path, 'personal_sender_data.json'), 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    student_dict = json.loads(content)
                else:
                    student_dict = None
            if not student_dict or not self.check_if_student_exists(student_dict['student_id'], student_dict['name'],
                                                                    student_dict['surname']):
                info_window = Toplevel()
                Label(info_window, text=f"The sender ({student_dict['name']} {student_dict['surname']}) of the mail is not on the list of university students",
                      font=("Arial", 10)).grid(row=0, column=0, sticky="w", padx=10,
                                               pady=(10, 0))
                Button(info_window, text="Ok", command=lambda: info_window.destroy()).grid(
                    row=1
                    , column=1
                    , padx=20
                    , pady=20)
            sure_window = Toplevel()
            Label(sure_window, text="Are you sure to send message?",font=("Arial", 10)).grid(row=0, column=0, sticky="w", padx=10,
                                               pady=(10, 0))
            Button(sure_window, text="Yes",
                    command=lambda:self.send_and_close(sure_window, item_path, mail_win)).grid(row=1, column=2 , padx=20, pady=20)
            Button(sure_window, text="Don't send",
                   command=lambda: sure_window.destroy()).grid(row=1, column=1 , padx=20, pady=20)
        else:
            error_window = Toplevel()
            Label(error_window, text="You should generate response before sending email",
                  font=("Arial", 10)).grid(row=0, column=0, sticky="w", padx=10,
                                           pady=(10, 0))
            Button(error_window, text="Exit", command=lambda: error_window.destroy()).grid(
                row=1
                , column=1
                , padx=20
                , pady=20)



def main():
    """
    Main function to run the Dean's Office email handling process.

    Workflow:
    1. Initialize mailbox client and authorize with Gmail API.
    2. Prepare directory for storing email data.
    3. Clean previous email files from the directory.
    4. Read unread emails from the mailbox.
    5. Classify emails using Bayes classifier.
    6. Generate AI responses to emails.
    7. Iterate over stored email directories matching pattern "Mail<number>".
    8. Send the generated responses via Gmail API.

    No parameters or return values.

    Side effects:
    - Reads and writes files in the "EmailsToRespond" directory.
    - Sends emails via Gmail API.
    """
    deans_office_mailbox = ClientMailbox() # represents mailbox
    main_path = "EmailsToRespond"
    if not os.path.exists(main_path):
        os.mkdir(main_path)
    deans_office_mailbox.clean_dir_with_mails()
    deans_office_mailbox.read_unread(deans_office_mailbox.service) # read unread mails from students
    mail_classifier = Classifier()
    mail_classifier.classify_bayes("abcd")
    # graphic interface
    root_win = Tk()
    root_win.title("Mail Responder")
    root_win.geometry("600x500")
    app = Application(root_win, deans_office_mailbox)
    root_win.mainloop()
    # graphic interface - end

main()

