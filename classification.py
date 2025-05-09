import os

from datasets import Dataset
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib  # for saving and loading naive bayes model for mail classification

class Classifier(object):
    """
       Classifies student mail into one of several predefined categories using different methods.

       Attributes:
           res_bayes (int): Result of classification using Naive Bayes.
           res_distilbert (int): Result of classification using DistilBERT.
           res_manual (int): Result of manual classification.
           comparison_compatibility (bool): True if DistilBERT and Naive Bayes agree.
           nb_model(obj): Object that represents naive bayes model
       """
    def __init__(self):
        self.res_bayes = None
        self.res_distilbert = None
        self.res_manual = None
        self.comparison_compatibility = True
        self.nb_model = None

    def classify_bayes(self, msg):
        """
           Classifies the message using Naive Bayes and writes classification result into the file with mail

           :param msg: Plain text message body to classify.
           :type msg: str
           :return: None
        """
        training_data_file = "text_classification_training_data.json" # path to a file with training data for mail classification
        # loading json file with training data and conversion it to Dataset type( defined in HuggingFace)
        mail_dataset = Dataset.from_json(training_data_file)
        # division into test and training set
        x_train, x_test, y_train, y_test = train_test_split(
            mail_dataset["text"], mail_dataset["label"], test_size=0.2, random_state=42
        )
        # path to naive bayes classificator
        model_path = "naive_bayes_model.pkl"
        # loading model if exists else training it
        if os.path.exists(model_path):
            print("Loading saved model...")
            self.model = joblib.load(model_path)
        else:
            print("Training new model...")
            # Pipeline: TF-IDF → Naive Bayes
            self.model = Pipeline([
                ('tfidf', TfidfVectorizer()),
                ('nb', MultinomialNB())
            ])
            self.model.fit(x_train, y_train)
            # save trained model
            joblib.dump(self.model, model_path)

        # evaluation on test set
        y_pred = self.model.predict(x_test)
        labels = [ "student_id_extension","grade_change", "office_hours", "scholarship"]
        print(classification_report(y_test, y_pred, target_names=labels))


        # getting mails to classify from files
        folder_path = "EmailsToRespond"
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                mail_text_file = os.path.join(root, file)
                if file == "plain_text.txt":
                    with open(mail_text_file, "r") as mail:
                        content = mail.read()
                        predicted_label = self.model.predict([content])
                        # creating file with the result of classification
                        classification_res_file = os.path.join(root, "classification_result.txt")
                        with open(classification_res_file, 'w') as c:
                            c.write(str(predicted_label[0]))
                dirs.clear()

