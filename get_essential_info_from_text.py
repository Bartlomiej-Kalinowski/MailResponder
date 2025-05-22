from transformers import pipeline
from database_manager import *
from sqlalchemy import func

class NameSearcher(object):
    def __init__(self, db_session):
        self.pipe = pipeline("token-classification", model="51la5/distilbert-base-NER")
        self.session = db_session

    def text_ner_analizer(self, txt):
        ner_results =self.pipe(txt)
        name = None
        surname = None
        essential_info = None
        for word_dict in ner_results:
            if self.session.query(StudentList).filter(func.lower(StudentList.name) == word_dict['word'].lower()).first() and not name:
                name = word_dict['word'].lower()
            if self.session.query(StudentList).filter(func.lower(StudentList.surname) == word_dict['word'].lower()).first() and not surname:
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

        print(essential_info)
        return essential_info


