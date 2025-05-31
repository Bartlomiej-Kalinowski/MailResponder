from transformers import pipeline
from database_manager import *
from sqlalchemy import func

class NameSearcher(object):
    """
    A class to perform Named Entity Recognition (NER) on text input and
    search for matching student names in a mail.

    Attributes:
        pipe (transformers.Pipeline): A Hugging Face transformers pipeline for token classification (NER).
        session (SQLAlchemy.Session): Database session for querying student records.
    """
    def __init__(self, db_session):
        """
       Initializes the NameSearcher with a pre-trained NER pipeline and a database session.

       :param db_session: SQLAlchemy session object connected to the student database.
        """
        self.pipe = pipeline("token-classification", model="51la5/distilbert-base-NER")
        self.session = db_session

    def text_ner_analizer(self, txt):
        """
        Analyze input text using NER to extract potential student names and surnames,
        and match them against the database records.

        The method searches for the first matching name and surname found in the text
        that exist in the database, then retrieves the corresponding student record.

        :param txt: str, input text to analyze.
        :return: dict or None, containing keys 'name', 'surname', and 'student_id' if a matching student is found; otherwise None.
        """
        ner_results =self.pipe(txt)
        name = None
        surname = None
        essential_info = None
        for word_dict in ner_results:
            name = word_dict['word'].lower()
            surname = word_dict['word'].lower()
        student = self.session.query(StudentList).filter(
            func.lower(StudentList.name) == name,
            func.lower(StudentList.surname) == surname
        ).first()
        if student:
            essential_info = {
                'name': name,
                'surname': surname,
                'student_id': student.student_id
            }
        else:
            essential_info = {
                'name': name,
                'surname': surname,
                'student_id': '000000'
            }
        return essential_info


