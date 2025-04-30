import os

from datasets import Dataset
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib  # for saving and loading naive bayes model for mail classification

class Classifier(object):
    def __init__(self):
        self.res_bayes = self.res_distilbert = res_manual = None
        self.comparison_compatibility = True
        self.model = None

    def classify_bayes(self, msg):
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

