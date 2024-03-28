import streamlit as st
import pandas as pd
import sqlite3
import datetime
import re
from git import Repo

# Set page title and icon
st.set_page_config(
    page_title="J&T Fleet Management",
    layout='wide',
    page_icon='logo.png'
)
database_file_path = 'fleet_management.db'
conn = sqlite3.connect(database_file_path)
cursor = conn.cursor()

repository_path = '.'
commit_message = 'Update data via Streamlit'


# Function to commit and push changes to the GitHub repository
def commit_and_push_changes(repo, file_path, commit_msg):
    # Set user identity for this repository
    repo.git.config("user.email", "abdelrahman-labs")
    repo.git.config("user.name", "abdelrahman-labs")

    repo.git.add(file_path)
    repo.git.commit(m=commit_msg)

    # Replace the following line with your HTTPS URL and branch name
    repo.git.push('https://abdelrahman-labs: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@github.com/abdelrahman-labs/Fleet-Management.git', 'main')


# Connect to the Git repository
repo = Repo(repository_path)


def transform_and_rearrange(text):
    ARABIC_TO_ENGLISH_DICT = {
        'ا': 'A', 'أ': 'A', 'آ': 'A', 'ب': 'B', 'ت': 'T', 'ث': 'TH', 'ج': 'G',
        'ح': 'H', 'خ': 'KH', 'د': 'D', 'ذ': 'TH', 'ر': 'R',
        'ز': 'Z', 'س': 'S', 'ش': 'SH', 'ص': 'C', 'ض': 'D',
        'ط': 'T', 'ظ': 'TH', 'ع': 'E', 'غ': 'GH', 'ف': 'F',
        'ق': 'Q', 'ك': 'K', 'ل': 'L', 'م': 'M', 'ن': 'N',
        'ه': 'H', 'ة': 'H', 'و': 'W', 'ي': 'Y', 'ى': 'Y',
        'ؤ': 'W', 'إ': 'A', 'ئ': 'Y',

        '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
        '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9'
    }

    translated_text = ''

    for char in str(text):
        if char.isalpha() and char in ARABIC_TO_ENGLISH_DICT:
            translated_text += ARABIC_TO_ENGLISH_DICT[char]
        elif char != ' ':
            translated_text += char

    letters = re.findall('[A-Za-z]+', translated_text)
    numbers = re.findall('\d+', translated_text)

    rearranged_text = ''.join(letters) + ''.join(numbers)

    return rearranged_text.upper()


def required_columns(table_name):
    cursor.execute(f"PRAGMA table_info({table_name});")
    table_columns = [column[1] for column in cursor.fetchall()]
    return table_columns


# Define a function for inserting data
def insert_data(data_option):
    if data_option == "License Renewal":
        show_license_form()
    elif data_option == "Ownerships":
        show_ownerships_form()
    elif data_option == "Vehicle Allocation":
        show_allocation_form()
    elif data_option == "Maintenance":
        show_maintenance_form()
    elif data_option == "Fueling":
        show_fuel_form()
    elif data_option == "Add a New Vehicle":
        show_new_vehicle_form()
    elif data_option == "Governmental Traffic Penalties":
        show_traffic_pen_form()


def display_required_columns_as_help_button(table_name):
    required_columns_list = required_columns(table_name)
    required_columns_str = ', '.join(required_columns_list)

    if st.button("ℹ️ Help", key=f"help_{table_name}"):
        st.info(f"Required Columns for '{table_name}': {required_columns_str}")


def import_data(table_name):
    cursor.execute(f"PRAGMA table_info({table_name});")
    table_columns = [column[1] for column in cursor.fetchall()]
    uploaded_file = st.file_uploader("Choose Data File (Excel or CSV)")
    display_required_columns_as_help_button(table_name)

    if uploaded_file:
        # Check if the file ends with ".csv" and read accordingly
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        common_columns = list(set(df.columns) & set(table_columns))
        filtered_df = df[common_columns]

        uploaded_count = 0
        failed_count = 0

        data_confirmation_expander = st.expander("Data to be Updated")
        with data_confirmation_expander:
            st.dataframe(filtered_df)

        if st.button("Confirm Update"):
            error_messages = []
            bad_entries = []

            for index, row in filtered_df.iterrows():
                try:
                    if 'VehicleID' in row:
                        row['VehicleID'] = transform_and_rearrange(row['VehicleID'])

                    if table_name in ('VehiclesLicenses', 'Ownership'):
                        row['Date' if table_name == 'VehiclesLicenses' else 'UploadDate'] = datetime.datetime.now()

                    if table_name != 'VehicleBasics':
                        vehicle_id = row['VehicleID']
                        cursor.execute(f"SELECT COUNT(*) FROM VehicleBasics WHERE VehicleID = ?", (vehicle_id,))
                        if cursor.fetchone()[0] == 0:
                            raise Exception(f"Vehicle with ID {vehicle_id} does not exist in VehicleBasics")

                    row_data = pd.DataFrame([row], columns=filtered_df.columns)
                    row_data.to_sql(table_name, conn, if_exists='append', index=False)
                    uploaded_count += 1

                except Exception as e:
                    error_message = str(e)
                    error_messages.append(error_message)
                    bad_entries.append(row)
                    failed_count += 1

            conn.commit()
            conn.close()

            st.info(f"Uploaded: {uploaded_count} entries\nFailed: {failed_count} entries")

            if error_messages:
                bad_entries_df = pd.DataFrame(bad_entries)
                bad_entries_df['Error'] = error_messages
                st.dataframe(bad_entries_df)


# Data Insert section
def data_insert():
    st.title("Data Insert")
    colll1, nocol = st.columns([1, 3])
    options = ["License Renewal", "Ownerships", "Vehicle Allocation", "Maintenance", "Fueling", "Add a New Vehicle", "Governmental Traffic Penalties"]
    options.sort()
    data_option = colll1.selectbox("Select Data to Insert", options)

    data_table_mapping = {
        "License Renewal": "VehiclesLicenses",
        "Ownerships": "Ownership",
        "Vehicle Allocation": "VehicleAllocation",
        "Maintenance": "Maintenance",
        "Fueling": "Fuel",
        "Add a New Vehicle": "VehicleBasics",
        "Governmental Traffic Penalties": "TrafficPen"
    }

    if data_option:
        table_name = data_table_mapping[data_option]

        col1, col2 = st.columns(2)

        with col1:
            st.subheader(f"Select the {data_option} Data:")
            insert_data(data_option)

        # Right column for data entry and display
        with col2:
            st.subheader("Or, Import an Excel Sheet Directly to the database")
            import_data(table_name)


def show_license_form():
    st.write("Inserting data into the VehiclesLicenses table.")
    vehicle_ids = [row[0] for row in cursor.execute("SELECT VehicleID FROM VehicleBasics").fetchall()]
    vehicle_id = st.selectbox("Vehicle ID", vehicle_ids)
    km = st.number_input("Kilometer")
    startdate = st.date_input("License Renewal Date")
    enddate = st.date_input("License Expiration Date")

    if st.button("Insert Data"):
        cursor.execute('''INSERT INTO VehiclesLicenses (Date, VehicleID, StartDate, EndDate, CurrentMileage)
                           VALUES (?, ?, ?, ?, ?)''',
                       (str(datetime.datetime.now()), vehicle_id, startdate, enddate, km))
        conn.commit()
        st.success("Data inserted successfully!")

        inserted_data = pd.read_sql_query(f"SELECT * FROM VehiclesLicenses WHERE VehicleID = '{vehicle_id}' AND StartDate = '{startdate}' AND EndDate = '{enddate}' AND CurrentMileage = {km}", con=conn)
        st.write("Inserted Data:")
        st.dataframe(inserted_data)


def show_ownerships_form():
    st.write("Insert data into the Ownership table.")
    vehicle_ids = [row[0] for row in cursor.execute("SELECT VehicleID FROM VehicleBasics").fetchall()]
    vehicle_id = st.selectbox("Vehicle ID", vehicle_ids)
    ownership = st.selectbox("Ownership", ["J&T Express", "Lightning", "Running Rabbit"])
    certificate = st.selectbox("Data Certificate", ["Yes", "No", "Not Needed"])
    contract = st.selectbox("Contract", ["Yes", "No", "Not Needed"])

    if st.button("Insert Data"):
        cursor.execute('''INSERT INTO Ownership (VehicleID, Ownership, DataCertificate, Contract, UploadDate)
                              VALUES (?, ?, ?, ?, ?)''',
                       (vehicle_id, ownership, certificate, contract, str(datetime.datetime.now())))
        conn.commit()
        st.success("Data inserted successfully!")

        inserted_data = pd.read_sql_query(f"SELECT * FROM Ownership WHERE VehicleID = '{vehicle_id}' AND Ownership = '{ownership}' AND DataCertificate = '{certificate}' AND Contract = '{contract}'", con=conn)
        st.write("Inserted Data:")
        st.dataframe(inserted_data)


def show_allocation_form():
    st.write("Inserting data into the VehicleAllocation table.")
    date = st.date_input("Date")
    vehicle_ids = [row[0] for row in cursor.execute("SELECT VehicleID FROM VehicleBasics").fetchall()]
    vehicle_id = st.selectbox("Vehicle ID", vehicle_ids)
    agencies = [row[0] for row in cursor.execute("SELECT DISTINCT Agency FROM branches").fetchall()]
    agency = st.selectbox("Agency Name", agencies)
    branches = [row[0] for row in cursor.execute(f"SELECT Branch FROM branches WHERE Agency = '{agency}'").fetchall()]
    branch = st.selectbox("Branch Name", branches)
    condition = st.selectbox("Condition", ["Active", "Inactive", "Under Maintenance"])

    if st.button("Insert Data"):
        cursor.execute('''INSERT INTO VehicleAllocation (Date, VehicleID, Branch, Agency, Condition)
                          VALUES (?, ?, ?, ?, ?)''',
                       (date, vehicle_id, branch, agency, condition))
        conn.commit()
        st.success("Data inserted successfully!")

        inserted_data = pd.read_sql_query(f"SELECT * FROM VehicleAllocation WHERE VehicleID = '{vehicle_id}' AND Date = '{date}' AND Branch = '{branch}' AND Agency = '{agency}' AND Condition = '{condition}'", con=conn)
        st.write("Inserted Data:")
        st.dataframe(inserted_data)


def show_maintenance_form():
    st.write("Insert data into the Maintenance table.")
    date = st.date_input("Date")
    vehicle_ids = [row[0] for row in cursor.execute("SELECT VehicleID FROM VehicleBasics").fetchall()]
    vehicle_id = st.selectbox("Vehicle ID", vehicle_ids)
    km = st.number_input("Kilometer")
    maintenance_type = st.selectbox("Maintenance Type", ["Mechanical", "Electrical", "Tires", "Brakes", "Body Repair", "Accident", "Greasing", "Washing", "PM 10", "PM 20", "PM 30", "PM 40"])
    spare_part = st.text_input("Changed Spare Part (If any)")
    cost = st.number_input("Cost")
    service_provider = st.text_input("Service Provider")

    if st.button("Insert Data"):
        cursor.execute('''INSERT INTO Maintenance (Date, VehicleID, MaintenanceType, SparePartName, Mileage, Cost, ServiceProviderOrGarage)
                          VALUES (?, ?, ?, ?, ?, ?, ?)''',
                       (date, vehicle_id, maintenance_type, spare_part, km, cost, service_provider))
        conn.commit()
        st.success("Data inserted successfully!")

        inserted_data = pd.read_sql_query(
            f"SELECT * FROM Maintenance WHERE VehicleID = '{vehicle_id}' AND Date = '{date}' AND Mileage = {km} AND MaintenanceType = '{maintenance_type}' AND SparePartName = '{spare_part}' AND Cost = {cost} AND ServiceProviderOrGarage = '{service_provider}'",
            con=conn)
        st.write("Inserted Data:")
        st.dataframe(inserted_data)


def show_fuel_form():
    st.write("Inserting data into the Fuel table.")
    date = st.date_input("Date")
    vehicle_ids = [row[0] for row in cursor.execute("SELECT VehicleID FROM VehicleBasics").fetchall()]
    vehicle_id = st.selectbox("Vehicle ID", vehicle_ids)
    km = st.number_input("Kilometer")
    fuel_type = st.selectbox("Fuel Type", ["Gasoline", "Diesel"])
    amount = st.number_input("Amount (Liters)")
    cost = st.number_input("Cost (EGP)")

    if st.button("Insert Data"):
        cursor.execute('''INSERT INTO Fuel (Date, VehicleID, Mileage, Type, Amount, Cost)
                          VALUES (?, ?, ?, ?, ?, ?)''',
                       (date, vehicle_id, km, fuel_type, amount, cost))
        conn.commit()
        st.success("Data inserted successfully!")

        inserted_data = pd.read_sql_query(f"SELECT * FROM Fuel WHERE VehicleID = '{vehicle_id}' AND Date = '{date}' AND Mileage = {km} AND Type = '{fuel_type}' AND Amount = {amount} AND Cost = {cost}", con=conn)
        st.write("Inserted Data:")
        st.dataframe(inserted_data)


def show_new_vehicle_form():
    st.write("Insert data into the VehicleBasics table.")
    vehicle_id = st.text_input("Vehicle ID")
    chassis = st.text_input("Chassis No.")
    engine = st.text_input("Engine No")
    vehicle_types = [row[0] for row in cursor.execute("SELECT DISTINCT VehicleType FROM VehicleBasics").fetchall()]
    vehicle_type = st.selectbox("Vehicle Type", vehicle_types)

    if st.button("Insert Data"):
        cursor.execute('''INSERT INTO VehicleBasics (VehicleID, ChassisNo, EngineNo, VehicleType)
                          VALUES (?, ?, ?, ?)''',
                       (vehicle_id, chassis, engine, vehicle_type))
        conn.commit()
        st.success("Data inserted successfully!")

        inserted_data = pd.read_sql_query(f"SELECT * FROM VehicleBasics WHERE VehicleID = '{vehicle_id}' AND ChassisNo = '{chassis}' AND EngineNo = '{engine}' AND VehicleType = '{vehicle_type}'", con=conn)
        st.write("Inserted Data:")
        st.dataframe(inserted_data)


def show_traffic_pen_form():
    st.write("Insert data into the TrafficPen table.")
    date = st.date_input("Date")
    vehicle_ids = [row[0] for row in cursor.execute("SELECT VehicleID FROM VehicleBasics").fetchall()]
    vehicle_id = st.selectbox("Vehicle ID", vehicle_ids)
    location = st.text_input("Location")
    desc = st.text_input("Description")
    cost = st.number_input("Cost")

    if st.button("Insert Data"):
        cursor.execute('''INSERT INTO TrafficPen (VehicleID, Date, Location, Desc, Cost)
                          VALUES (?, ?, ?, ?)''',
                       (vehicle_id, date, location, desc, cost))
        conn.commit()
        st.success("Data inserted successfully!")

        inserted_data = pd.read_sql_query(f"SELECT * FROM TrafficPen WHERE VehicleID = '{vehicle_id}' AND Date = '{date}' AND Location = '{location}' AND Description = '{desc}' AND Cost = '{cost}'", con=conn)
        st.write("Inserted Data:")
        st.dataframe(inserted_data)


# Main content
def main():
    st.header("Welcome to J&T Fleet Management System")
    data_insert()
    if st.button("Commit and Push Changes"):
        commit_and_push_changes(repo, database_file_path, commit_message)
        st.success("Changes committed and pushed to GitHub!")


if __name__ == '__main__':
    main()
