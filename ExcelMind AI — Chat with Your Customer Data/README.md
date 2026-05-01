# ExcelMind AI — Chat with Your Customer Data
 
A Streamlit application that lets you query any customer Excel or CSV file using plain English. 
 
---
 
## Project Overview
 
ExcelMind AI uses a two-step approach to answer questions accurately:
 
1. **Query Generation** — Google Gemini translates your natural language question into a pandas expression
2. **Local Execution** — The pandas expression runs directly on your data (no AI guessing)
3. **AI Summary** — Gemini generates a concise, professional summary of the result
This means answers are always grounded in real data — not AI hallucinations.
 
### Key Features
 
- **Natural Language Querying** — Ask questions in plain English
- **Works on Any Excel/CSV** — Upload any customer dataset.
- **Smart Clarification** — If your question is ambiguous, the app asks for clarification instead of guessing
- **Empty Result Handling** — Shows a clear warning instead of returning misleading output
- **Download Results** — Export filtered results directly as an Excel file
- **Data Summary Dashboard** — Auto-generated stats when you upload a file
- **Pre-configured Business Logic**:
  - *High-intent customers*: Connected calls + Budget > ₹80 Lakhs
  - *Hot leads*: Customers with connected calls
  - *Premium customers*: Budget > ₹1.2 Crores

 
---
 
## Setup Instructions
 
### 1. **Clone the repository and navigate to the project folder:**
 
```bash
cd "Internship-Task\ExcelMind AI — Chat with Your Customer Data"
```
 
### 2. Install Dependencies
 
 
```bash
pip install -r requirements.txt
```
 
### 3. Set Up Environment Variables
 
Create a `.env` file in the root directory:
 
```env
GEMINI_API_KEY=your_gemini_api_key_here
```
 
 
### 4. Run the App
 
```bash
streamlit run app.py
```
 
 
## Example Queries
 
Here are 5 example queries you can try, along with their expected outputs based on the sample dataset:

1. **Query**: `List 2BHK customers in Pune`
   - **Expected Output**: Displays a DataFrame showing all customers looking for a 2BHK property. (it correctly searches across all granular neighborhoods instead of incorrectly filtering for the exact string "Pune").

2. **Query**: `Show customers with budget above 1.5 crore`
   - **Expected Output**: If no customers match this exact criteria, it gracefully shows a warning: `⚠️ No records found matching your query.`

3. **Query**: `How many customers have a budget above 90 lakhs?`
   - **Expected Output**: A single number representing the count of customers whose budget exceeds ₹9,000,000, along with a concise, professional AI summary stating the total count.

4. **Query**: `Show risky customers`
   - **Expected Output**: The system pauses and asks for clarification: `❓ Need Clarification: "risky customers" is not defined. Should I use low budget, switched off calls, or delayed possession?`

5. **Query**: `Average budget by location`
   - **Expected Output**: Displays a DataFrame (Series) with each granular location (e.g., Baner, Kharadi, Hinjewadi) and the corresponding average budget.



 
---
 
## Project Structure
 
```
excelmind-ai/
├── app.py                  # Main Streamlit application
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
├── sample_data.xlsx        #sample dataset given by the company
└── README.md               # This file
```
 
---
 
## Requirements
 
See `requirements.txt` for full list. Core dependencies:
 
- `streamlit` — UI framework
- `pandas` — Data processing
- `google-generativeai` — Gemini API
- `openpyxl` — Excel file handling
- `python-dotenv` — Environment variable management
---
 
## Important Notes
 
- **Data Privacy**: Your data is processed locally using pandas. The Gemini API only receives column names, 5 sample rows, and the generated query string — never your full dataset.
- **API Quota**: The app uses `gemini-2.5-flash-lite` if you face any quota related problem  then use another model like gemini-2.5-flash,gemini-3.1-flash-lite-preview.

 
