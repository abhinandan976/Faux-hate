# Faux-Hate 🚫💬

**Faux-Hate** is an NLP-based project focused on detecting **fake** and **hate** content in social media posts. This system leverages advanced language modeling techniques and efficient fine-tuning strategies to combat misinformation and online toxicity.

---

## 🧠 Project Overview

The project uses tweets written in **Hinglish** (Hindi language using the English script), which are translated to English using the **IndicTrans2** tool. Two BERT models are fine-tuned with **Low-Rank Adaptation (LoRA)** to efficiently classify each tweet as:
- **Fake or Not Fake**
- **Hateful or Not Hateful**

LoRA enhances the model’s adaptability while reducing computational costs, making it ideal for real-world, low-resource applications.

---

## 🗃️ Dataset

- **Source**: Scraped tweets from public social media platforms.
- **Language**: Hinglish (Hindi in English script).
- **Preprocessing**:  
  - Translated Hinglish to English using [IndicTrans2](https://huggingface.co/ai4bharat/indictrans2-en).
  - Cleaned, tokenized, and labeled data for fake and hate content classification.

---

## 🧪 Model Architecture

- **Base Model**: BERT (`bert-base-uncased`)
- **Adaptation Method**: [LoRA (Low-Rank Adaptation)](https://arxiv.org/abs/2106.09685)
- **Task**: Binary classification for both fake and hate detection.
- **Libraries**:
  - Hugging Face Transformers
  - PEFT (Parameter-Efficient Fine-Tuning)
  - PyTorch / Transformers Trainer

---

## 🛠️ Technologies Used

- Python
- NLTK
- NLP (Natural Language Processing)
- BERT (Bidirectional Encoder Representations from Transformers)
- LoRA Adapters (Efficient fine-tuning)
- IndicTrans2 (Hinglish to English translation)
- Hugging Face Transformers and Datasets



## 🚀 How to Run

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/faux-hate.git
cd faux-hate
