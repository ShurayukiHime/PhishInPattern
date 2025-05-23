#!/usr/bin/python
# coding=utf8

import sys
import sklearn


from textblob import Word
from textblob.classifiers import NaiveBayesClassifier
from textblob import TextBlob
import difflib
import json
import nltk
nltk.download('averaged_perceptron_tagger')
nltk.download('punkt')
import collections
from nltk.classify.scikitlearn import SklearnClassifier
from sklearn.linear_model import SGDClassifier
from sklearn.naive_bayes import MultinomialNB
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from faker import Faker
import pickle
from database import phish_db_layer
from database import phish_db_schema
import os
import pandas as pd
from nltk import everygrams
import enchant
from sklearn import metrics
import random
from sklearn.naive_bayes import GaussianNB
dir_path = os.path.abspath(os.path.dirname(__file__))

samples=None



def token_cleaning(sentence):
    res_sentences=[]
    sentence = sentence.lower()
    s=sentence   
    max=0
    # print ('sent : ',sentence)
    d = enchant.request_pwl_dict(dir_path+"/mywords.txt")
    # for ng in everygrams(sentence):
    #     print(ng)
    #     print(d.check(''.join(ng)))
    words = [''.join(_ngram) for _ngram in everygrams(sentence) if d.check(''.join(_ngram)) ]
    sentence = ' '.join(words)
    # print(sentence)
    input_sent=TextBlob(sentence)
    sent=''
    # print (input_sent.tags)
    for w,pos in input_sent.tags:
        if  (pos=="NN" or pos =="JJ") :
            sent= sent +" " + w
    
    # print ('final sent: ' +sentence + ' '+sent)
    res_sentences.append(((sentence + ' '+sent).lower()+' ')*5)
    return res_sentences


def fetch_field_training_set():

    training_set = []
    with open('./database/TrainingSet.json','r') as f:
        
        train =json.load(f)
        for obj in train:            
            for text in obj['texts']:
                data={}
                data['category'] = obj['category']
                data['text'] = text
                training_set.append(data)

    return training_set 

def pickle_data(test = False):
    from sklearn.model_selection import GridSearchCV
    global samples
   

    t_set = phish_db_layer.fetch_field_training_set() #fetch_field_training_set()
    random.shuffle(t_set)
    samples = phish_db_layer.get_categories()
    samples.sort()

    t_set = pd.DataFrame([{'cat_num': samples.index(e['category']) , 'text': token_cleaning(e['text'])[0] }for (e) in t_set])
    # t_set = pd.concat([t_set,t_set, t_set])
    X, Y = t_set['text'], t_set['cat_num']
    
    x_train, x_test, y_train, y_test = train_test_split(X,Y, test_size=0.05, random_state=123, stratify = Y )
    # print(y_test.unique())
    

    
    parameters = {
        'vect__ngram_range': [(1, 1), (1, 2),(1,3), (1,4)],
        'tfidf__use_idf': (True, False),
        'clf__alpha': (1e-2, 1e-3),
    }

    nb = Pipeline([     
    ('vect', CountVectorizer()),
     ('tfidf', TfidfTransformer()),
     ('clf', SGDClassifier(loss='log', penalty='l2',alpha=1e-3, random_state=42, max_iter=10, tol=None)),
    ])
    nb.fit(X,Y)

    if test:
        nb.fit(x_train, y_train) 
        # gs_clf = GridSearchCV(nb, parameters, cv=5, n_jobs=-1)

        # gs_clf.fit(x_train, y_train)    
        # print(gs_clf.best_score_)

        # for param_name in sorted(parameters.keys()):
        #     print("%s: %r" % (param_name, gs_clf.best_params_[param_name]))

        y_pred = nb.predict(x_test)
        
        print(metrics.classification_report(y_test, y_pred, target_names=samples))
        acc_score = metrics.accuracy_score(y_test,y_pred)
        # print('Accuracy Score :: ', acc_score)
        cm = metrics.confusion_matrix([samples[x] for x in y_test], [samples[x] for x in y_pred], labels = samples)
        plot_confusion_matrix(cm, samples, 'c.png')
    cl_pickle = open(os.path.join(dir_path,"category.pickle"),"wb")
    pickle.dump(nb,cl_pickle)
    cl_pickle.close()
    
    
# Classify some text
def classify(text):
    
    global samples
    if len(text)<2:
        return "", 0
    try:
        if samples == None:
            samples = phish_db_layer.get_categories()
            samples.sort()
            # print(samples)
        cl_pickle = open(os.path.join(dir_path,"category.pickle"),"rb")
        nb = pickle.load(cl_pickle)
        cl_pickle.close()
        
        text=  text.encode('ascii','ignore').decode() # text.decode('unicode_escape').encode('ascii','ignore')

        X_test = token_cleaning(text)

        y_pred = nb.predict(X_test)
        
        y_pred_prob = nb.predict_proba(X_test)[:,y_pred]
        # print(X_test, y_pred, nb.predict_proba(X_test))
        # print (samples)
        result = samples[y_pred[0]]

        # print(text)
        if 'captcha' in text.lower():        
            result = "Captcha"
        elif 'sms' in text.lower() or '2FA' in text or 'otp' in text.lower():
            result = 'sms'
        # if 'address' not in result.lower():
        #     print(result,';;(',y_pred_prob[0],')' , X_test[0] )

        if result.lower() in X_test[0].lower():        
            return result, y_pred_prob[0]
        elif y_pred_prob[0]*100 <20:
            # print ("low probability")
            return "", 0

        return result, y_pred_prob[0]
    except Exception as e:
        print(e)


def get_category_input_value(category):
    
    try:
        fake = Faker()
        
        choice ={'address' : fake.address(),
                'name'    : fake.name(),
                'username': fake.simple_profile(sex=None).get("username"),
                'password': fake.password(), #fake.word()+'@'+str(fake.random_number(digits=3)),
                'identification': fake.simple_profile(sex=None).get("username"),
                'email'   : fake.email(),
                'phone'   : str(fake.random_number(digits=10)),
                'month'   : fake.month(),
                'date'    : str(fake.simple_profile(sex=None).get("birthdate")),
                'year'    : fake.year(),
                'day'     : fake.day_of_month(),
                'card'    : fake.credit_card_number(card_type=None),
                'cvv'     : fake.credit_card_security_code(card_type=None),
                'expdate' : fake.credit_card_expire(),#start="now", end="+10Y", date_format="%m%y"),
                'ssn'     : fake.ssn(),
                'zip'     : fake.zipcode(),
                'sms'     : str(fake.random_number(digits=6)),
                'captcha' : fake.password(length=6, special_chars=False),
                'city'    : fake.city(),
                'state'   : fake.state(),
                'license' : fake.ssn(),
                'search'  : ''
        }    
        return choice.get(category.lower(),"default")
    except Exception as e:
        print(e)

def test_real_samples():

    
    cl_pickle = open(os.path.join(dir_path,"category.pickle"),"rb")
    nb = pickle.load(cl_pickle)
    cl_pickle.close()

    print(nb.classes_)
    
    samples = phish_db_layer.get_categories()
    samples.sort()
    samples = [s.lower() for s in samples]
    print((samples))
    # exit()

    
    
    df_test = pd.read_csv('../data/field_test_results_unknown.csv', header=0)
    
    df_test = df_test[df_test['field_category'].notna()]
    
    # df_test
    df_test['field_category'] = df_test['field_category'].apply(lambda x: x.lower())
    df_test = df_test.fillna('')
    df_category_count = df_test.groupby(['field_category']).count()
    print(df_category_count.head(20))
    pred = []
    y_test = []
    for i,row in df_test.iterrows():
        text_data = row['field_text']
        res, _ = classify(text_data)
        res = res if res!="" else 'unknown'
        # if 'username' in text_data.lower():
        #     res = 'username'
        if res!="":
            pred.append(res.lower())
            y_test.append(row['field_category'])
    # print(set(pred))
    # labels = list(set(df_test['field_category'].tolist()).union(set(pred)))
    labels = phish_db_layer.get_categories()
    labels.sort()
    labels = [s.lower() for s in labels]
    # print(pred)
    acc_score = metrics.accuracy_score(y_test,pred)
    # cm = metrics.confusion_matrix(df_test['field_category'], pred, labels = labels)
    pred_labels = list(set(pred))
    pred_labels.sort()
    print(metrics.classification_report(y_test, pred, labels = pred_labels ))

    #plot_confusion_matrix(cm, labels, 'c.png')
    
    print('Accuracy Score ::', acc_score)
    df_test['Predicted'] = pred
    df_test.to_csv('field_test_results_unknown.csv', index = False)

# classify('email')
if __name__ == '__main__':
    # pickle_data(test=False)
    test_real_samples()
    # classify('User ID')
    
