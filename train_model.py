import pandas as pd
import joblib
import os
from sklearn.ensemble import RandomForestClassifier

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "student_performance.csv")

df = pd.read_csv(DATA_PATH)

X = df[
    ["attendance_percentage",
     "internal_marks",
     "external_marks",
     "quiz_average",
     "study_hours_per_day",
     "sleep_hours"]
]

y = df["risk_level"]

model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X, y)

joblib.dump(model, os.path.join(os.path.dirname(__file__), "risk_model.pkl"))
print("✅ Model trained successfully")
