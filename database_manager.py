from abc import ABC, abstractmethod, ABCMeta
from sqlalchemy import (
    create_engine, Column, Integer, String, Time, ForeignKey, LargeBinary, text, Float
)
from sqlalchemy.ext.declarative import declarative_base, DeclarativeMeta
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
import datetime
import json

class CombinedMetaClass(ABCMeta, DeclarativeMeta):
    pass

Base = declarative_base(metaclass=CombinedMetaClass)

class DeansOfficeTableInterface(metaclass = ABCMeta):
    @abstractmethod
    def table_to_dict(self):
        pass


class DeansOfficeHours(Base, DeansOfficeTableInterface):
    __tablename__ = 'hours'

    id = Column(Integer, primary_key=True, autoincrement=True)
    weekday = Column(String, primary_key = False)
    opening = Column(Time, nullable=False)
    closing = Column(Time, nullable=False)

    @classmethod
    def fill(cls, current_session):
        weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        for day in weekdays:
            current_session.add(DeansOfficeHours(
                weekday=day,
                opening=datetime.time(8, 0),
                closing=datetime.time(15, 0)
            ))

    @classmethod
    def get_by_id(cls, session, record_id):
        return session.query(cls).get(record_id)

    def table_to_dict(self):
        return {
            "day": self.weekday,
            "open_time": self.opening.strftime("%H:%M") if self.opening else None,
            "close_time": self.closing.strftime("%H:%M") if self.closing else None
        }

class ScholarshipValue(Base,  DeansOfficeTableInterface):
    __tablename__ = 'scholarship'

    id = Column(Integer, primary_key = True, autoincrement=True)
    kind = Column(String, nullable = False)
    money = Column(Float, nullable = False)
    grade_level = Column(Float, nullable = True)

    def table_to_dict(self):
        return {
            "id": self.id,
            "kind": self.kind,
            "money": self.money,
            "grade_level": self.grade_level
        }

class StudentList(Base,  DeansOfficeTableInterface):
    __tablename__ = 'students'

    student_id = Column(String, primary_key=True)
    name = Column(String, nullable = False)
    surname = Column(String, nullable = False)

    def table_to_dict(self):
        return {
            "student_id": self.student_id,
            "name": self.name,
            "surname": self.surname
        }


class Database(object):
    @classmethod
    def make_db(cls, db_init_file):
        # Tworzenie silnika bazy danych SQLite
        engine = create_engine('sqlite:///deans_office.db')

        # Tworzenie wszystkich tabel
        Base.metadata.create_all(engine)

        # Tworzenie sesji
        session1 = sessionmaker(bind=engine)
        session = session1()

        DeansOfficeHours.fill(session)
        sql_text = ("""INSERT INTO scholarship(kind, money, grade_level)
                VALUES
                ('rectors scholarschip', 1000.00, 4.5),
                ('social scholarship', 1500.99, NULL);
                """)
        session.execute(text(sql_text))
        sql_text = ("""INSERT INTO students(student_id, name, surname)
                       VALUES
                       (100001, 'James', 'Smith'),
                       (100002, 'Emily', 'Johnson'),
                       (100003, 'Michael', 'Williams'),
                       (100004, 'Olivia', 'Brown'),
                       (100005, 'William', 'Jones'),
                       (100006, 'Sophia', 'Garcia'),
                       (100007, 'Benjamin', 'Miller'),
                       (100008, 'Isabella', 'Davis'),
                       (100009, 'Ethan', 'Wilson'),
                       (100010, 'Charlotte', 'Anderson');
                    """)
        session.execute(text(sql_text))
        return session


