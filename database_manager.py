import os
from sqlalchemy import (
    create_engine, Column, Integer, String, Time, ForeignKey, LargeBinary
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
import datetime
Base = declarative_base()

class DeansOfficeHours(Base):
    __tablename__ = 'hours'

    id = Column(Integer, primary_key=True)
    weekday = Column(String, primary_key = False)
    opening = Column(Time, nullable=False)
    closing = Column(Time, nullable=False)

    @classmethod
    def get_by_id(cls, session, record_id):
        return session.query(cls).get(record_id)

class StudentMailsCategories(Base):
    __tablename__ = 'categories'

    id = Column(Integer, primary_key = True)
    name = Column(String, nullable = False)

    files_to_attach = relationship('Attachements', back_populates='category')

class Attachements(Base):
    __tablename__ = 'attachements'

    id = Column(Integer, primary_key = True)
    category_id = Column(Integer, ForeignKey('categories.id'))
    file_name = Column(String, nullable=False)
    attachement = Column(LargeBinary, nullable=False)

    category = relationship('StudentMailsCategories', back_populates='files_to_attach')

    @classmethod
    def save_pdf(cls, session, file_path):
        with open(file_path, 'rb') as f:
            file_data = f.read()
        attachment = Attachements(
            file_name=os.path.basename(file_path),
            attachement=file_data
        )

        session.add(attachment)
        session.commit()

        print(f"Zapisano plik: {file_path}")

    @classmethod
    def get_pdf(cls, session, file_id, output_path):
        attachment_file = session.query(Attachements).filter_by(id=file_id).first()
        if attachment_file:
            with open(output_path, 'wb') as f:
                f.write(attachment_file.attachement)
            print(f"Obraz zapisany do: {output_path}")
        else:
            print("Nie znaleziono obrazu o podanym ID.")


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

        # Dodanie dni tygodnia (pon-pt) z godzinami 8:00–15:00
        weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        for day in weekdays:
            session.add(DeansOfficeHours(
                weekday=day,
                opening=datetime.time(8, 0),
                closing=datetime.time(15, 0)
            ))
        Attachements.save_pdf(session, db_init_file)
        print("Baza danych i dane(tabela, zdjecie) zostały utworzone.")

        return session  # zwraca sesję do dalszego użytku



