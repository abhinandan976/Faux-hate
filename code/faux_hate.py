# -*- coding: utf-8 -*-
"""Faux-hate.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1vJVFsriS1AeTa4zsoK4TKRJwdGE_N06y
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import f1_score, classification_report
from sklearn.model_selection import train_test_split
import torch
import re
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

# Download necessary NLTK data
nltk.download('stopwords')
nltk.download('punkt')
nltk.download('punkt_tab')

# Load data
data = pd.read_csv('/kaggle/input/dataset2/translatedDataset(Task_A).csv')

# Set stop words
stop_words = set(stopwords.words('english'))

# Preprocessing function
def preprocess_tweet(tweet):
    if isinstance(tweet, str):
        tweet = tweet.lower()
        tweet = re.sub(r'http\S+|www\S+|https\S+', '', tweet, flags=re.MULTILINE)
        tweet = re.sub(r'@\w+', '', tweet)
        tweet = re.sub(r'#\w+', '', tweet)
        tweet = re.sub(r'[^\w\s]', '', tweet)
        tweet = re.sub(r'\d+', '', tweet)
        tokens = word_tokenize(tweet)
        tokens = [w for w in tokens if w not in stop_words]
        preprocessed_tweet = " ".join(tokens)
        return preprocessed_tweet
    return ""

# Apply preprocessing
data['Processed_Tweet'] = data['Tweet'].apply(preprocess_tweet)

# Drop original Tweet column and rearrange
data = data.drop('Tweet', axis=1)
cols = list(data.columns)
cols.insert(0, cols.pop(cols.index('Processed_Tweet')))
data = data.loc[:, cols]

# Display data head
print(data.head())

# Importing libraries for model development
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModel, AutoTokenizer
from peft import LoraConfig, get_peft_model

# Dataset class
class TextDataset(Dataset):
    def __init__(self, texts, hate_labels, fake_labels, tokenizer, max_length=128):
        self.texts = texts
        self.hate_labels = torch.tensor(hate_labels.values, dtype=torch.float)
        self.fake_labels = torch.tensor(fake_labels.values, dtype=torch.float)
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        text = self.texts.iloc[idx]
        hate_label = self.hate_labels[idx]
        fake_label = self.fake_labels[idx]

        inputs = self.tokenizer(
            text,
            return_tensors='pt',
            padding='max_length',
            truncation=True,
            max_length=self.max_length
        )
        input_ids = inputs['input_ids'].squeeze(0)
        attention_mask = inputs['attention_mask'].squeeze(0)

        return input_ids, attention_mask, hate_label, fake_label

# Model class
class DualBERTWithLoRA(nn.Module):
    def __init__(self, model_name='bert-base-uncased', lora_rank=8, lora_alpha=16):
        super(DualBERTWithLoRA, self).__init__()
        hate_model_name = "Hate-speech-CNERG/dehatebert-mono-english"
        fake_model_name = "bert-base-uncased"

        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.hate_model = AutoModel.from_pretrained(hate_model_name)
        self.fake_model = AutoModel.from_pretrained(fake_model_name)

        hate_lora_config = LoraConfig(
            r=lora_rank,
            lora_alpha=lora_alpha,
            target_modules=["query", "key"],
            lora_dropout=0.1
        )
        fake_lora_config = LoraConfig(
            r=lora_rank,
            lora_alpha=lora_alpha,
            target_modules=["query", "key"],
            lora_dropout=0.1
        )

        self.hate_model = get_peft_model(self.hate_model, hate_lora_config)
        self.fake_model = get_peft_model(self.fake_model, fake_lora_config)

        self.hate_classifier = nn.Sequential(
            nn.Linear(self.hate_model.config.hidden_size, 1),
            nn.Sigmoid()
        )
        self.fake_classifier = nn.Sequential(
            nn.Linear(self.fake_model.config.hidden_size, 1),
            nn.Sigmoid()
        )

    def forward(self, input_ids, attention_mask):
        hate_outputs = self.hate_model(input_ids=input_ids, attention_mask=attention_mask).last_hidden_state[:, 0, :]
        hate_score = self.hate_classifier(hate_outputs).squeeze(-1)

        fake_outputs = self.fake_model(input_ids=input_ids, attention_mask=attention_mask).last_hidden_state[:, 0, :]
        fake_score = self.fake_classifier(fake_outputs).squeeze(-1)

        return hate_score, fake_score

# Trainer class
class DualBERTTrainer:
    def __init__(self, model, learning_rate=1e-5):
        self.model = model
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=learning_rate)
        self.criterion = nn.BCELoss()

    def train_step(self, batch):
        input_ids, attention_mask, hate_labels, fake_labels = batch
        input_ids, attention_mask = input_ids.to(device), attention_mask.to(device)
        hate_labels, fake_labels = hate_labels.to(device), fake_labels.to(device)

        self.model.train()
        hate_preds, fake_preds = self.model(input_ids, attention_mask)

        hate_loss = self.criterion(hate_preds, hate_labels)
        fake_loss = self.criterion(fake_preds, fake_labels)
        loss = hate_loss + fake_loss

        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        return loss.item()

    def evaluate(self, dataloader):
        self.model.eval()
        all_hate_preds, all_fake_preds = [], []
        all_hate_labels, all_fake_labels = [], []

        with torch.no_grad():
            for batch in dataloader:
                input_ids, attention_mask, hate_labels, fake_labels = batch
                input_ids, attention_mask = input_ids.to(device), attention_mask.to(device)

                hate_preds, fake_preds = self.model(input_ids, attention_mask)

                all_hate_preds.extend(hate_preds.cpu().numpy())
                all_fake_preds.extend(fake_preds.cpu().numpy())
                all_hate_labels.extend(hate_labels.numpy())
                all_fake_labels.extend(fake_labels.numpy())

        hate_preds = [1 if pred > 0.5 else 0 for pred in all_hate_preds]
        fake_preds = [1 if pred > 0.5 else 0 for pred in all_fake_preds]

        print("Hate Speech Classification Report:")
        print(classification_report(all_hate_labels, hate_preds, target_names=["Not Hate", "Hate"]))
        print("Fake News Classification Report:")
        print(classification_report(all_fake_labels, fake_preds, target_names=["Not Fake", "Fake"]))

        hate_accuracy = accuracy_score(all_hate_labels, hate_preds)
        fake_accuracy = accuracy_score(all_fake_labels, fake_preds)
        hate_f1 = f1_score(all_hate_labels, hate_preds)
        fake_f1 = f1_score(all_fake_labels, fake_preds)

        return hate_accuracy, fake_accuracy, hate_f1, fake_f1

# Preparing Dataset
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

texts = data['Processed_Tweet']
hate_labels = data['Hate']
fake_labels = data['Fake']

train_texts, test_texts, train_hate_labels, test_hate_labels, train_fake_labels, test_fake_labels = train_test_split(
    texts, hate_labels, fake_labels, test_size=0.2, random_state=42
)

tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")

train_dataset = TextDataset(train_texts, train_hate_labels, train_fake_labels, tokenizer)
test_dataset = TextDataset(test_texts, test_hate_labels, test_fake_labels, tokenizer)

train_dataloader = DataLoader(train_dataset, batch_size=16, shuffle=True)
test_dataloader = DataLoader(test_dataset, batch_size=32)

# Training and Evaluation Loop
model = DualBERTWithLoRA().to(device)
trainer = DualBERTTrainer(model)

num_epochs = 5
for epoch in range(num_epochs):
    total_loss = 0
    for batch in train_dataloader:
        loss = trainer.train_step(batch)
        total_loss += loss

    print(f"Epoch {epoch + 1}/{num_epochs}, Loss: {total_loss / len(train_dataloader)}")
    hate_acc, fake_acc, hate_f1, fake_f1 = trainer.evaluate(test_dataloader)
    print(f"Epoch {epoch + 1} - Hate F1: {hate_f1:.4f}, Fake F1: {fake_f1:.4f}, Hate Acc: {hate_acc:.4f}, Fake Acc: {fake_acc:.4f}")