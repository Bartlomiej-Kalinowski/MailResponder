from abc import ABC, abstractmethod, ABCMeta
from sqlalchemy import (
    create_engine, Column, Integer, String, Time, ForeignKey, LargeBinary, text, Float
)
from sqlalchemy.ext.declarative import declarative_base, DeclarativeMeta
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
import datetime

class CombinedMetaClass(ABCMeta, DeclarativeMeta):
    """
    Metaclass combining ABCMeta and DeclarativeMeta to support both abstract base classes
    and SQLAlchemy ORM declarative base functionality.
    """
    pass

Base = declarative_base(metaclass=CombinedMetaClass)

class DeansOfficeTableInterface(metaclass = ABCMeta):
    """
    Abstract interface class for Dean's Office database tables.

    Requires implementing classes to provide a method to convert
    table instances to dictionary representation.
    """
    @abstractmethod
    def table_to_dict(self):
        pass


class DeansOfficeHours(Base, DeansOfficeTableInterface):
    """
    SQLAlchemy ORM model representing Dean's Office working hours.

    Attributes:
        id (int): Primary key, autoincremented.
        weekday (str): Name of the weekday (e.g., 'Monday').
        opening (datetime.time): Office opening time.
        closing (datetime.time): Office closing time.
    """
    __tablename__ = 'hours'

    id = Column(Integer, primary_key=True, autoincrement=True)
    weekday = Column(String, primary_key = False)
    opening = Column(Time, nullable=False)
    closing = Column(Time, nullable=False)

    @classmethod
    def fill(cls, current_session):
        """
        Populate the 'hours' table with default working hours (8:00 to 15:00)
        for weekdays Monday through Friday.

        :param current_session: SQLAlchemy session to add records to.
        :return: None
        """
        weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        for day in weekdays:
            current_session.add(DeansOfficeHours(
                weekday=day,
                opening=datetime.time(8, 0),
                closing=datetime.time(15, 0)
            ))

    def table_to_dict(self):
        """
        Convert the instance data to dictionary format.

        :return: dict with keys "day", "open_time", and "close_time"
        """
        return {
            "day": self.weekday,
            "open_time": self.opening.strftime("%H:%M") if self.opening else None,
            "close_time": self.closing.strftime("%H:%M") if self.closing else None
        }

class ScholarshipValue(Base,  DeansOfficeTableInterface):
    """
    ORM model representing scholarship types and values.

    Attributes:
        id (int): Primary key, autoincremented.
        kind (str): Type of scholarship (e.g., 'rectors scholarship').
        money (float): Amount of money awarded.
        grade_level (float): Minimum grade level required, nullable.
    """
    __tablename__ = 'scholarship'

    id = Column(Integer, primary_key = True, autoincrement=True)
    kind = Column(String, nullable = False)
    money = Column(Float, nullable = False)
    grade_level = Column(Float, nullable = True)

    def table_to_dict(self):
        """
        Convert the scholarship instance to dictionary.

        :return: dict with keys "id", "kind", "money", "grade_level"
        """
        return {
            "id": self.id,
            "kind": self.kind,
            "money": self.money,
            "grade_level": self.grade_level
        }

class StudentList(Base,  DeansOfficeTableInterface):
    """
    ORM model representing a student record.

    Attributes:
        student_id (str): Primary key student identifier.
        name (str): Student's first name.
        surname (str): Student's surname.
    """
    __tablename__ = 'students'

    student_id = Column(String, primary_key=True)
    name = Column(String, nullable = False)
    surname = Column(String, nullable = False)

    def table_to_dict(self):
        """
        Convert the student record to dictionary format.

        :return: dict with keys "student_id", "name", "surname"
        """
        return {
            "student_id": self.student_id,
            "name": self.name,
            "surname": self.surname
        }


class Database(object):
    """
    Class for initializing the SQLite database and session.
    """
    @classmethod
    def make_db(cls):
        """
        Initialize the SQLite database, create tables, and populate with
        default data including office hours, scholarships, and student records.

        :return: SQLAlchemy session instance connected to the database.
        """
        # creating SQLite engine
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


