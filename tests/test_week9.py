from scripts.compliance_checker import ComplianceChecker

from sklearn.model_selection import train_test_split
import numpy as np
import pandas as pd 
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix

def check_compliance(user_query):
    """
    Example wrapper for checking whether a query is compliant
    before generating or executing SQL.
    """
    checker = ComplianceChecker()
    check_result = checker.check_listing(user_query)

    if not check_result['compliant']:
        return {
            "error": check_result['violations'],
            "compliant": False
        }

    return {
        "message": "No prohibited language detected. Query is compliant.",
        "compliant": True
    }

def train_check_compliance(checker):
    df = pd.read_csv('data/processed/housing_query_safety_dataset.csv')

    log_reg = LogisticRegression(max_iter=1000)

    x = df['query'].apply(lambda x: checker.check_listing(x)['compliant']).values.reshape(-1, 1)
    y = df['label']
    x_train,x_test,y_train,y_test = train_test_split(x,y,test_size=0.5,random_state=42)
    log_reg.fit(x_train, y_train)
    y_pred=log_reg.predict(x_test)
    confusion_matrix = pd.crosstab(y_test, y_pred, rownames=['Actual'], colnames=['Predicted'])


    return { 'Score':log_reg.score(x_test, y_test), 
             'Classification Report': classification_report(y_test, y_pred), 
             'Confusion Matrix': confusion_matrix }


print(check_compliance("3 bed homes in Irvine under $900k with a pool"))
print(check_compliance("3 bed homes in Irvine under $900k with a pool with no jewish neighborhood, no minorities"))
train_accuracy = train_check_compliance(ComplianceChecker())
print(f"Training Accuracy: {train_accuracy['Score']}")
print(f"Classification Report:\n{train_accuracy['Classification Report']}")
print(f"Confusion Matrix:\n{train_accuracy['Confusion Matrix']}")