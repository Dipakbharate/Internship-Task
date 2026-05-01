import streamlit as st
import pandas as pd
import numpy as np
import google.generativeai as genai
from dotenv import load_dotenv
import os
import io
import re

# LOAD ENV
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

model = genai.GenerativeModel("gemini-2.5-flash-lite")


# PAGE CONFIG
st.set_page_config(page_title="ExcelMind AI", layout="wide")

st.title("📊 ExcelMind AI — Chat with Your Customer Data")
st.write("Upload any Excel or CSV file and ask questions in plain English.")


# HELPERS

ALLOWED_PATTERN = r'^(len\(.*|df(\.|\[).*)$'

def safe_eval(code, df_context):
    code = code.strip()
    if not re.match(ALLOWED_PATTERN, code):
        raise ValueError(f"AI generated unsafe or unrecognized code: {code}")
    
    # Evaluate without sandbox restrictions to allow standard functions like len()
    return eval(code, {"df": df_context, "pd": pd, "np": np})

def show_result(result):
    if isinstance(result, pd.DataFrame):
        st.dataframe(result, use_container_width=True)
    elif isinstance(result, pd.Series):
        st.dataframe(result.reset_index(), use_container_width=True)
    else:
        st.metric(label="Result", value=result)


def download_excel(result):
    """Show Excel download button only for non-empty DataFrames."""
    if isinstance(result, pd.DataFrame) and not result.empty:
        buffer = io.BytesIO()
        result.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)
        st.download_button(
            label="⬇️ Download Results as Excel",
            data=buffer,
            file_name="results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )


@st.cache_data(show_spinner=False)
def summarize_answer(query, result, file_hash):
    if isinstance(result, (pd.DataFrame, pd.Series)):
        total_records = len(result)
        data_context = (
            f"Total Records: {total_records}\n"
            f"Data Preview (showing first 3 rows only):\n{result.head(3).to_string()}"
        )
        count_instruction = (
            f"2. CRITICAL: The exact total number of matching records is {total_records}. "
            f"You MUST use this exact number. Do NOT count the rows in the Data Preview."
        )
    else:
        data_context = f"Result:\n{str(result)}"
        count_instruction = "2. Summarize the result clearly."

    prompt = f"""
You are a Senior Business Data Analyst.

User Question:
{query}

Data Context:
{data_context}

STRICT RULES:
1. Provide a clear, smart, professional summary of the results based on the query.
{count_instruction}
3. If there are more than 3 records, YOU ARE STRICTLY FORBIDDEN from listing individual names,
   contact numbers, or specific rows. You MUST ONLY state the total count.
4. Keep the total response concise (max 2 sentences total).
5. Do not guess or make up data.
"""

    response = model.generate_content(prompt)
    return response.text


@st.cache_data(show_spinner=False)
def ask_model_for_query(query, columns, sample_rows, unique_vals, file_hash):
    prompt = f"""
You are an expert pandas analyst.

DataFrame name is df.

Available Columns:
{columns}

Sample Data (first 5 rows):
{sample_rows}

Unique Values for Categorical Columns:
{unique_vals}

Known Definitions (apply only if columns exist):
- high-intent customers = Last Call Status == "Connected" AND Budget (INR) > 8000000
- hot leads = Last Call Status == "Connected"
- premium customers = Budget (INR) > 12000000
- City Context: If a user asks for data in a broad city (e.g., "Pune", "Mumbai") but that city name does not exist in the Location/City column, DO NOT filter by it. Assume the entire dataset already belongs to that city and only contains its granular neighborhoods.

Task:
Convert the user's natural language question into ONE of the following:

A) A single-line executable pandas expression using df
OR
B) A clarification request if the query is ambiguous or uses undefined terms

STRICT RULES:
1. Return ONLY one-line pandas code if the answer can be derived from available columns.
2. If the term is undefined, vague, or not in columns, return:
   CLARIFY: <your clarifying question>
3. Use df only. No variables. No print(). No markdown. No explanation.
4. Never invent column names. Never guess business meanings.
5. Always use actual column names from the Available Columns list above.

Examples:

User: List 2BHK customers in Pune
Output:
df[df["Property Type"]=="2BHK"]

User: How many customers have budget above 90 lakhs?
Output:
len(df[df["Budget (INR)"] > 9000000])

User: What is the average budget?
Output:
df["Budget (INR)"].mean()

User: Average budget by location
Output:
df.groupby("Location")["Budget (INR)"].mean()

User: Show risky customers
Output:
CLARIFY: "risky customers" is not defined. Should I use low budget, switched off calls, or delayed possession?

User Question:
{query}
"""

    response = model.generate_content(prompt)
    output = response.text.strip()

    # Strip markdown fences if model accidentally adds them
    if output.startswith("```python"):
        output = output[9:]
    if output.startswith("```"):
        output = output[3:]
    if output.endswith("```"):
        output = output[:-3]

    return output.strip()


def get_unique_vals(df, max_unique=15):
    """Extract unique values for categorical columns to help the model."""
    result = {}
    for col in df.columns:
        if df[col].dtype == object or str(df[col].dtype) == "string":
            uniques = df[col].dropna().unique().tolist()
            if len(uniques) <= max_unique:
                result[col] = uniques
    return result



# SESSION STATE INIT

def init_session():
    defaults = {
        "current_query": None,
        "clarification_needed": False,
        "clarification_msg": "",
        "execute_query": False,
        "result_output": None,
        "summary_text": None,
        "eval_error": None,
        "is_empty": False,
        "query_history": [],
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


init_session()

# FILE UPLOAD


uploaded_file = st.file_uploader(
    "📁 Upload Excel or CSV File",
    type=["xlsx", "csv"]
)

if uploaded_file:
    file_hash = f"{uploaded_file.name}_{uploaded_file.size}"

    try:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        st.success(f"✅ File uploaded successfully — {len(df)} rows, {len(df.columns)} columns")

        with st.expander("📋 Dataset Preview", expanded=True):
            st.dataframe(df.head(), use_container_width=True)

        # Auto stats dashboard
        with st.expander("📊 Quick Data Summary", expanded=False):
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Records", len(df))
            col2.metric("Total Columns", len(df.columns))
            numeric_cols = df.select_dtypes(include="number").columns.tolist()
            if numeric_cols:
                col3.metric(
                    f"Avg {numeric_cols[0]}",
                    f"{df[numeric_cols[0]].mean():,.0f}"
                )
            st.dataframe(df.describe(include="all").T, use_container_width=True)

    except Exception as e:
        st.error(f"❌ Error reading file: {e}")
        st.stop()


    # QUERY INPUT

    st.markdown("---")
    query = st.text_input(
        "💬 Ask a Question About Your Data",
        placeholder="Example: List customers looking for 2BHK with budget above 80 lakhs"
    )

    if st.button("🔍 Get Answer", use_container_width=True) and query:
        st.session_state.current_query = query
        st.session_state.clarification_needed = False
        st.session_state.execute_query = True
        st.session_state.result_output = None
        st.session_state.summary_text = None
        st.session_state.eval_error = None
        st.session_state.is_empty = False


    # CLARIFICATION FLOW

    if st.session_state.clarification_needed:
        st.subheader("❓ Need Clarification")
        st.warning(st.session_state.clarification_msg)
        clarification_answer = st.text_input("Your Answer:", key="clarification_input")
        if st.button("Submit Answer") and clarification_answer:
            st.session_state.current_query = (
                f"{st.session_state.current_query} (Context: {clarification_answer})"
            )
            st.session_state.clarification_needed = False
            st.session_state.execute_query = True
            st.rerun()

    # QUERY EXECUTION

    if st.session_state.execute_query:
        st.session_state.execute_query = False

        with st.spinner("🤖 Analyzing your question..."):
            columns = tuple(df.columns)
            sample_rows = df.head(5).to_string()
            unique_vals = get_unique_vals(df)

            output = ask_model_for_query(
                query=st.session_state.current_query,
                columns=columns,
                sample_rows=sample_rows,
                unique_vals=str(unique_vals),
                file_hash=file_hash
            )

            if output.upper().startswith("CLARIFY:"):
                st.session_state.clarification_needed = True
                st.session_state.clarification_msg = output.replace("CLARIFY:", "").strip()
                st.rerun()
            else:
                st.session_state.result_output = output
                try:
                    # Execute safely
                    result = safe_eval(output, df)
                    if isinstance(result, pd.DataFrame) and result.empty:
                        st.session_state.is_empty = True
                        st.session_state.summary_text = None
                    else:
                        st.session_state.is_empty = False
                        st.session_state.summary_text = summarize_answer(
                            st.session_state.current_query, result, file_hash
                        )
                    st.session_state.eval_error = None

                    # Save to history
                    st.session_state.query_history.append({
                        "query": st.session_state.current_query,
                        "pandas_code": output,
                        "summary": st.session_state.summary_text or "No records found."
                    })

                except Exception as e:
                    st.session_state.eval_error = str(e)

                st.rerun()

    # DISPLAY RESULTS

    if st.session_state.result_output and not st.session_state.clarification_needed:
        output = st.session_state.result_output

        st.subheader("🧾 Generated  Query")
        st.code(output, language="python")

        if st.session_state.eval_error:
            st.error(f"❌ Execution Error: {st.session_state.eval_error}")
        else:
            try:
                result = safe_eval(output, df)

                st.subheader("📌 Result")

                if st.session_state.is_empty:
                    st.warning("⚠️ No records found matching your query. Try rephrasing or broadening your criteria.")
                else:
                    show_result(result)
                    download_excel(result)

                    if st.session_state.summary_text:
                        st.subheader("🧠 AI Summary")
                        st.info(st.session_state.summary_text)

            except Exception as e:
                st.error(f"❌ Execution Error: {e}")


# FOOTER

st.markdown("---")
st.caption("Built with using Streamlit+ Pandas + Gemini API - By Dipak")
