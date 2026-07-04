from scripts.text_cleaning import TextCleaner
import pandas as pd
import os

cleaner = TextCleaner()
df = pd.read_csv('data/processed/listing_sample.csv')
print("Original remarks Length:", len(df['remarks'].dropna()))


# for remark in df['remarks'].dropna():
#     cleaned_remark = cleaner.clean_text(remark)
#     print(f"Original: {remark}\nCleaned: {cleaned_remark}\n")

os.remove('data/processed/cleaned_remarks.txt') if os.path.exists('data/processed/cleaned_remarks.txt') else None
for remark in df['remarks'].dropna():
    cleaned_remark = cleaner.clean_text(remark)
    with open('data/processed/cleaned_remarks.txt', 'a') as f:
        f.write(f"Original: {remark}\nCleaned: {cleaned_remark}\n\n")

cleaned_remarks = df['remarks'].dropna().apply(cleaner.clean_text)
df.drop(columns=['remarks'], inplace=True)
df['cleaned_remarks'] = cleaned_remarks
print("Cleaned remarks Length:", len(df['cleaned_remarks'].dropna()))

df.to_csv('data/processed/cleaned_listing_sample.csv', index=False)


