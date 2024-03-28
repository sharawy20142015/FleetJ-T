import sqlite3
import streamlit as st
import pandas as pd
from git import Repo
st.set_page_config(
    page_title="J&T Fleet Management",
    layout='wide',
    page_icon='logo.png'
)

repository_path = '.'
commit_message = 'Update SQLite database via Streamlit'

conn = sqlite3.connect('fleet_management.db')
cursor = conn.cursor()


def commit_and_push_changes(repo, file_path, commit_msg):
    # Set user identity for this repository
    repo.git.config("user.email", "abdelrahman-labs")
    repo.git.config("user.name", "abdelrahman-labs")

    repo.git.add(file_path)
    repo.git.commit(m=commit_msg)

    # Replace the following line with your HTTPS URL and branch name
    repo.git.push('https://abdelrahman-labs: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@github.com/abdelrahman-labs/Fleet-Management.git', 'main')


def sql_query():
    st.title("SQL Query and Data Export")
    st.write("Write and execute SQL queries on the database and export the results.")
    sql_query_input = st.text_area("Enter your SQL query here:")

    if st.button("Run Query"):
        try:
            cursor.execute(sql_query_input)

            query_lower = sql_query_input.lower()
            if any(keyword in query_lower for keyword in ['insert', 'update', 'delete', 'create']):
                conn.commit()
                st.success("Database changes committed.")
                repo = Repo(repository_path)
                commit_and_push_changes(repo, 'fleet_management.db', commit_message)
            else:
                results = cursor.fetchall()
                column_names = [description[0] for description in cursor.description]
                result_df = pd.DataFrame(results, columns=column_names)

                st.subheader("Query Result:")
                st.write("Rows Affected:", len(result_df))
                st.dataframe(result_df)

        except sqlite3.Error as e:
            st.error(f"An error occurred: {e}")


# Main content
def main():
    st.header("Welcome to J&T Fleet Management System")
    sql_query()


if __name__ == '__main__':
    main()
