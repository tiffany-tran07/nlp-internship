import pandas as pd
import numpy as np

test_df = pd.read_csv('data/processed/extracted_test_suite.csv')
amenity_df = pd.read_csv('data/processed/suite_amenities.csv')


def to_set(val):
        return set(val)
def row_metrics(extracted, actual):
    tp = len(extracted & actual)
    fp = len(extracted - actual)
    fn = len(actual - extracted)
    return pd.Series({'tp': tp, 'fp': fp, 'fn': fn})
   
extracted_sets = test_df['found_amen'].apply(to_set)
actual_sets = amenity_df['amenities'].apply(to_set)

metrics = pd.DataFrame([row_metrics(e, a) for e, a in zip(extracted_sets, actual_sets)])

test_df['amen_tp'] = metrics['tp']
test_df['amen_fp'] = metrics['fp']
test_df['amen_fn'] = metrics['fn']

# per-row precision/recall (guard divide-by-zero)
test_df['amen_precision'] = test_df['amen_tp'] / (test_df['amen_tp'] + test_df['amen_fp']).replace(0, np.nan)
test_df['amen_recall'] = test_df['amen_tp'] / (test_df['amen_tp'] + test_df['amen_fn']).replace(0, np.nan)
# overall (micro-averaged) totals
total_tp = test_df['amen_tp'].sum()
total_fp = test_df['amen_fp'].sum()
total_fn = test_df['amen_fn'].sum()

overall_precision = total_tp / (total_tp + total_fp)
overall_recall = total_tp / (total_tp + total_fn)
overall_f1 = 2 * overall_precision * overall_recall / (overall_precision + overall_recall)

print(f"Overall precision: {overall_precision:.3f}")
print(f"Overall recall: {overall_recall:.3f}")
print(f"Overall F1: {overall_f1:.3f}")

test_df['actual_beds'] = amenity_df['beds']
test_df['actual_baths'] = amenity_df['baths']
test_df['actual_sqft'] = amenity_df['sqft']

beds_null = test_df['extracted_bedrooms'].isna() & amenity_df['beds'].isna()
beds_equal = test_df['extracted_bedrooms'] == amenity_df['beds']

test_df['corr_beds'] = np.where(beds_null | beds_equal, True, False)

baths_null = test_df['extracted_bathrooms'].isna() & amenity_df['baths'].isna()
baths_equal = test_df['extracted_bathrooms'] == amenity_df['baths']

test_df['corr_baths'] = np.where(baths_null | baths_equal, True, False)

sqft_null = test_df['extracted_sqft'].isna() & amenity_df['sqft'].isna()
sqft_equal = test_df['extracted_sqft'] == amenity_df['sqft']

test_df['corr_sqft'] = np.where(sqft_null | sqft_equal, True, False)

# test_df['corr_baths'] = np.where(test_df['extracted_bathrooms'] == amenity_df['baths'], True, False)
# test_df['corr_sqft'] = np.where(test_df['extracted_sqft'] == amenity_df['sqft'], True, False)

corr_beds = test_df['corr_beds'].sum()
corr_baths = test_df['corr_baths'].sum()
corr_sqft = test_df['corr_sqft'].sum()
accuracy_eval = test_df[['extracted_bedrooms', 'actual_beds', 'extracted_bathrooms','actual_baths','extracted_sqft','actual_sqft','corr_beds', 'corr_baths', 'corr_sqft', 'amen_tp', 'amen_fp','amen_fn']]
# accuracy_eval['actual_beds'] = amenity_df['beds']
accuracy_eval.to_csv('data/processed/accuracy_eval.csv')

print(f"correct beds identified: {corr_beds}\ncorrect baths identified: {corr_baths}\n correct sqft identified: {corr_sqft}\n")
