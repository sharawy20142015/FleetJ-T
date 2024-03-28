import streamlit as st
import pandas as pd
import datetime
import sqlite3
import plotly.express as px
import numpy as np

# Set page title and icon
st.set_page_config(
    page_title="J&T Fleet Management",
    layout='wide',
    page_icon='logo.png'
)
conn = sqlite3.connect('fleet_management.db')
cursor = conn.cursor()

translations = {
    "انتهاء رخصة التسيير": "Expiry of the driving license.",
    "تجاوز السرعة المقررة": "Exceeding the specified speed limit.",
    "قيادة السيارة بدون حزام امان": "Driving without wearing a seatbelt.",
    "إضافة ملصقات مخالفة على جسم المركبة": "Placing stickers to the vehicle's body.",
    "تسبب دون مقتضى فى تعطيل حركة المرور أو تعويقها": "Causing the obstruction of traffic.",
    "عدم اتباع إشارات المرور": "Failure to obey traffic signals.",
    "استخدام التليفون يدويا أثناء القيادة": "Using the phone manually while driving.",
    "تعمد تعطيل حركة المرور": "Intentionally obstructing traffic.",
    "وضع كتابة مخالفة على جسم المركبة": "Placing a text on the vehicle's body.",
    "عدم اتباع تعليمات رجل المرور": "Failure to follow traffic officer instructions.",
    "وضع رسم مخالف على جسم المركبة": "Placing a drawing on the vehicle's body.",
    "الانتظار فى الممنوع": "Waiting in a prohibited area.",
    "قيادة مركبة بدون رخصة تسيير": "Driving a vehicle without a driving license.",
    "عدم اتباع علامات المرور": "Disregarding traffic signs."
}


@st.cache_data(ttl=60 * 15)
def basic_data_fun(where_clause_str):
    basic_data = pd.read_sql_query(f'''
    WITH VehicleAllocationCTE AS (
      SELECT
        VA1.VehicleID,
        VA1.Agency,
        VA1.Branch,
        VA1.Condition,
        ROW_NUMBER() OVER (PARTITION BY VA1.VehicleID ORDER BY VA1.AllocationID DESC) AS row_num
      FROM VehicleAllocation VA1
    ),
    FuelCTE AS (
      SELECT
        F1.VehicleID,
        F1.Amount,
        F1.Date,
        ROW_NUMBER() OVER (PARTITION BY F1.VehicleID ORDER BY F1.Date DESC) AS row_num
      FROM Fuel F1
    ),
    VehiclesLicensesCTE AS (
      SELECT
        VL1.VehicleID,
        VL1.EndDate,
        ROW_NUMBER() OVER (PARTITION BY VL1.VehicleID ORDER BY VL1.LicenseID DESC) AS row_num
      FROM VehiclesLicenses VL1
    ),
    OwnershipCTE AS (
      SELECT
        O1.VehicleID,
        O1.Ownership,
        ROW_NUMBER() OVER (PARTITION BY O1.VehicleID ORDER BY O1.OwnershipID DESC) AS row_num
      FROM Ownership O1
    )
    SELECT
      DISTINCT VB.VehicleID AS "Vehicle ID",
      VB.ChassisNo AS "Chassis No.",
      VB.VehicleType AS "Vehicle Type",
      VA.Agency AS "Agency",
      VA.Branch AS "Branch",
      F.Amount AS "Last Fuel Amount",
      F.Date AS "Last Fuel Date",
      VL.EndDate AS "Licence End Date",
      O.Ownership AS "Ownership",
      VA.Condition AS "Condition"
    FROM VehicleBasics VB
    LEFT JOIN VehicleAllocationCTE VA ON VB.VehicleID = VA.VehicleID AND VA.row_num = 1
    LEFT JOIN FuelCTE F ON VB.VehicleID = F.VehicleID AND F.row_num = 1
    LEFT JOIN VehiclesLicensesCTE VL ON VB.VehicleID = VL.VehicleID AND VL.row_num = 1
    LEFT JOIN OwnershipCTE O ON VB.VehicleID = O.VehicleID AND O.row_num = 1
    WHERE {where_clause_str};
    ''', con=conn)
    return basic_data


# Reports section
def reports():
    st.title("Reports")

    col1, nocol = st.columns([1, 3])
    report_option = col1.selectbox("Select Report:", ["Basic Vehicle Data", "Action Needed", "Expenses", "Maintenance History", "Traffic Penalties","Fuel Fraud"])

    col1, col2, col3, col4 = st.columns(4)
    vehicle_ids = list(set(row[0] for row in cursor.execute("SELECT VehicleID FROM VehicleBasics").fetchall()))
    agencies = list(set(row[0] for row in cursor.execute("SELECT Agency FROM VehicleAllocation").fetchall()))
    vehicle_types = list(set(row[0] for row in cursor.execute("SELECT VehicleType FROM VehicleBasics").fetchall()))

    vehicle_ids.insert(0, "All")
    agencies.insert(0, "All")
    vehicle_types.insert(0, "All")

    search_value = col1.selectbox("Search by VehicleID", vehicle_ids)
    search_agency = col2.selectbox("Search by Agency", agencies)
    search_chassis = col3.text_input("Search by Chassis")
    search_type = col4.selectbox("Search by Type", vehicle_types)

    # Define a date range slider
    start_date, end_date = st.select_slider(
        'Select a Date Range',
        options=[datetime.date(2023, 9, 1) + datetime.timedelta(days=x) for x in range((datetime.date.today() - datetime.date(2023, 9, 1)).days + 1)], value=(datetime.date(2023, 9, 1), datetime.date.today()))

    where_clause = []
    if search_value != "All":
        where_clause.append(f'"Vehicle ID" = "{search_value}"')
    if search_agency != "All":
        where_clause.append(f'"Agency" = "{search_agency}"')
    if search_chassis:
        where_clause.append(f'"Chassis No." LIKE "%{search_chassis}%"')
    if search_type != "All":
        where_clause.append(f'"Vehicle Type" = "{search_type}"')

    # Construct the WHERE clause as a string
    where_clause_str = ' AND '.join(where_clause) if where_clause else "1=1"  # Default to 1=1 for no filtering

    if report_option == "Basic Vehicle Data":
        st.subheader("Basic Vehicle Data")
        st.write("View basic data of vehicles.")

        # Replace with code to display basic vehicle data with date filter and search options
        basic_data = basic_data_fun(where_clause_str)
        datacol, chartcol = st.columns([2, 1])
        datacol.dataframe(basic_data, use_container_width=True, hide_index=True)

        # Display a bar chart for the total cost of traffic penalties by vehicle type
        vehicle_type_distribution = basic_data['Vehicle Type'].value_counts()
        chartcol.plotly_chart(px.bar(vehicle_type_distribution, x=vehicle_type_distribution.index, y='Vehicle Type',
                                     title='Vehicle Type Distribution', text_auto=True,
                                     labels={'Vehicle Type': 'Count'}, color_discrete_sequence=px.colors.qualitative.Set1),
                              use_container_width=True)

        ownership_types = basic_data['Ownership'].value_counts()
        chartcol.plotly_chart(px.pie(ownership_types, names=ownership_types.index, values=ownership_types.values,
                                     title='Ownership Distribution', color_discrete_sequence=px.colors.qualitative.Set2,hole=0.4),
                              use_container_width=True)

    elif report_option == "Action Needed":
        st.subheader("Action Needed")
        st.write("View actions needed for vehicles (e.g., license renewal, ownership transfer).")
        # Replace with code to display action-needed data with date filter
        action_data = pd.read_sql_query(f'''
        WITH RankedLicenses AS (
            SELECT
                VehicleID,
                LicenseID,
                EndDate,  -- Replace this with the actual column name
                ROW_NUMBER() OVER (PARTITION BY VehicleID ORDER BY LicenseID DESC) AS RowNum
            FROM VehiclesLicenses
        ),
        RankedOwnership AS (
            SELECT
                VehicleID,
                OwnershipID,
                Ownership,
                ROW_NUMBER() OVER (PARTITION BY VehicleID ORDER BY OwnershipID DESC) AS RowNum
            FROM Ownership
        ),
        RankedAllocation AS (
            SELECT
                VehicleID,
                Agency,
                Branch,
                Condition,
                ROW_NUMBER() OVER (PARTITION BY VehicleID ORDER BY AllocationID DESC) AS RowNum
            FROM VehicleAllocation
        )
        SELECT
            VB.VehicleID AS "Vehicle ID",
            VB.VehicleType AS "Vehicle Type",
            VA.Agency,
            VA.Branch,
            
            VL.EndDate AS "Licence End Date",
            O.Ownership AS "Ownership",
            CASE
                WHEN VL.EndDate < DATE('now') AND (O.Ownership = 'JT' OR O.Ownership IS NULL) THEN 'Renew License'
                WHEN VL.EndDate >= DATE('now') AND VL.EndDate <= DATE('now', '+1 month') AND (O.Ownership = 'JT' OR O.Ownership IS NULL) THEN 'Renew Soon'
                WHEN VL.EndDate < DATE('now') AND O.Ownership != 'JT' THEN 'Ownership Transfer and Renew License'
                WHEN VL.EndDate >= DATE('now') AND VL.EndDate <= DATE('now', '+1 month') AND O.Ownership != 'JT' THEN 'Ownership Transfer and Renew Soon'
                WHEN O.Ownership != 'JT' THEN 'Ownership Transfer'
                ELSE 'No Action Needed'
            END AS "Action Needed",
            CASE
                WHEN VL.EndDate < DATE('now') THEN 'High'
                WHEN VL.EndDate >= DATE('now') AND VL.EndDate <= DATE('now', '+1 month') THEN 'Medium'
                ELSE 
                    CASE
                        WHEN O.Ownership != 'JT' THEN
                            CASE
                                WHEN VL.EndDate < DATE('now') THEN 'High'
                                WHEN VL.EndDate >= DATE('now') AND VL.EndDate <= DATE('now', '+1 month') THEN 'Medium'
                                ELSE 'Low'
                            END
                        ELSE 'Low'
                    END
            END AS "Priority Type",
            VA.Condition
        FROM (
            SELECT VB.VehicleID
            FROM VehicleBasics VB
        ) AS UniqueVehicles
        LEFT JOIN RankedLicenses VL ON UniqueVehicles.VehicleID = VL.VehicleID AND VL.RowNum = 1
        LEFT JOIN RankedOwnership O ON UniqueVehicles.VehicleID = O.VehicleID AND O.RowNum = 1
        LEFT JOIN RankedAllocation VA ON UniqueVehicles.VehicleID = VA.VehicleID AND VA.RowNum = 1
        LEFT JOIN VehicleBasics VB ON UniqueVehicles.VehicleID = VB.VehicleID
        WHERE "Action Needed" <> 'No Action Needed'
        AND {where_clause_str}
        AND "Condition" <>'Inactive'
            ''', con=conn)
        datacol, chartcol = st.columns([2, 1])
        datacol.dataframe(action_data.drop_duplicates(), use_container_width=True, hide_index=True)
        action_distribution = action_data['Action Needed'].value_counts()
        chartcol.plotly_chart(px.bar(action_distribution, x=action_distribution.index, y='Action Needed',
                                     title='Action Needed Distribution', text_auto=True,
                                     labels={'Action Needed': 'Count'}, color_discrete_sequence=px.colors.qualitative.Set1),
                              use_container_width=True)

    elif report_option == "Expenses":
        st.subheader("Expenses")
        st.write("View expenses for each vehicle and area.")

        query = f'''
        WITH ExpenseData AS (
            SELECT
                M.MaintenanceID AS ID,
                M.VehicleID,
                M.Date,
                VB.VehicleType,
                VA.Agency,
                VB.ChassisNo,
                M.Cost,
                M.MaintenanceType
            FROM Maintenance M
            LEFT JOIN VehicleBasics VB ON M.VehicleID = VB.VehicleID
            LEFT JOIN (
                SELECT
                    VehicleID,
                    Agency,
                    ROW_NUMBER() OVER (PARTITION BY VehicleID ORDER BY AllocationID DESC) AS row_num
                FROM VehicleAllocation
            ) VA ON M.VehicleID = VA.VehicleID AND VA.row_num = 1
            UNION ALL
            SELECT
                F.FuelID,
                F.VehicleID,
                F.Date,
                VB.VehicleType,
                VA.Agency,
                VB.ChassisNo,
                F.Cost,
                NULL AS MaintenanceType
            FROM Fuel F
            LEFT JOIN VehicleBasics VB ON F.VehicleID = VB.VehicleID
            LEFT JOIN (
                SELECT
                    VehicleID,
                    Agency,
                    ROW_NUMBER() OVER (PARTITION BY VehicleID ORDER BY AllocationID DESC) AS row_num
                FROM VehicleAllocation
            ) VA ON F.VehicleID = VA.VehicleID AND VA.row_num = 1
        )

        SELECT
            ID,
            VehicleID AS "Vehicle ID",
            Date,
            VehicleType AS "Vehicle Type",
            Agency,
            ChassisNo AS "Chassis No.",
            CASE WHEN MaintenanceType IS NOT NULL THEN 'Maintenance' ELSE 'Fuel' END AS "Expense Type",
            Cost
        FROM ExpenseData
        WHERE Date BETWEEN ? AND ? AND {where_clause_str};
        '''

        expenses_data = pd.read_sql_query(query, con=conn, params=(start_date, end_date)).drop_duplicates()
        st.write(f"The total cost for the selected period is: {expenses_data['Cost'].sum():,.0f} EGP")
        datacol, chartcol = st.columns([2, 1])
        datacol.dataframe(expenses_data, use_container_width=True, hide_index=True)
        # Display a pie chart for the distribution of expense types
        expense_distribution = expenses_data.groupby('Expense Type')['Cost'].sum()
        chartcol.plotly_chart(px.pie(expense_distribution, names=expense_distribution.index, values=expense_distribution.values,
                                     title='Expense Type Distribution', color_discrete_sequence=px.colors.qualitative.Set2, hole=0.4),
                              use_container_width=True)
        total_cost_by_agency = expenses_data.groupby(['Agency', 'Expense Type'])['Cost'].sum().sort_values(ascending=False).reset_index()
        chartcol.plotly_chart(px.bar(total_cost_by_agency, x='Agency', y='Cost', color='Expense Type',
                                     title='Total Cost by Agency', labels={'Cost': 'Total Cost (EGP)'},
                                     color_discrete_sequence=px.colors.qualitative.Set2),
                              use_container_width=True)
        cost_by_vehicle_type = expenses_data.groupby(['Vehicle Type', 'Expense Type'])['Cost'].sum().sort_values(ascending=False).reset_index()
        chartcol.plotly_chart(px.bar(cost_by_vehicle_type, x='Vehicle Type', y='Cost', color='Expense Type',
                                     title='Total Cost by Vehicle Type', labels={'Cost': 'Total Cost (EGP)'},
                                     color_discrete_sequence=px.colors.qualitative.Set2),
                              use_container_width=True)

    elif report_option == "Maintenance History":
        st.subheader("Maintenance History")
        st.write("View maintenance history, focusing on repeated maintenance within a short period.")
        # Replace with code to display maintenance history data with date filter
        maintenance_history_data = pd.read_sql_query(f'''SELECT
        M.MaintenanceID,
        M.Date AS MaintenanceDate,
        M.VehicleID,
        M.MaintenanceType,
        M.Mileage,
        M.Cost,
        CASE
            WHEN EXISTS (
                SELECT 1
                FROM Maintenance AS PrevM
                WHERE PrevM.VehicleID = M.VehicleID
                AND PrevM.Date < M.Date
            ) THEN 'Yes'
            ELSE 'No'
        END AS PreviousMaintenance,
        CASE
            WHEN EXISTS (
                SELECT 1
                FROM Maintenance AS PrevM
                WHERE PrevM.VehicleID = M.VehicleID
                AND PrevM.Date < M.Date
            ) AND M.Mileage - LAG(M.Mileage) OVER (PARTITION BY M.VehicleID ORDER BY M.Date) < 5000 THEN 'Normal'
            WHEN EXISTS (
                SELECT 1
                FROM Maintenance AS PrevM
                WHERE PrevM.VehicleID = M.VehicleID
                AND PrevM.Date < M.Date
            ) AND M.Mileage - LAG(M.Mileage) OVER (PARTITION BY M.VehicleID ORDER BY M.Date) >= 5000 THEN 'Abnormal'
            ELSE 'No Previous Maintenance'
        END AS MaintenanceStatus,
        COUNT(*) OVER (PARTITION BY M.VehicleID, M.MaintenanceType) AS "Maintenance Count"
    FROM Maintenance AS M
    WHERE M.Date BETWEEN '{start_date}' AND '{end_date}' AND {where_clause_str};

        ''', con=conn)
        datacol, chartcol = st.columns([2, 1])
        datacol.dataframe(maintenance_history_data.drop_duplicates(), use_container_width=True, hide_index=True)
        # Maintenance status distribution pie chart
        maintenance_status_distribution = maintenance_history_data['MaintenanceStatus'].value_counts()

        chartcol.plotly_chart(px.pie(maintenance_status_distribution,
                                     names=maintenance_status_distribution.index,
                                     values=maintenance_status_distribution.values,
                                     title='Maintenance Status Distribution',
                                     color_discrete_sequence=px.colors.qualitative.Set2,
                                     labels={'MaintenanceStatus': 'Count'},
                                     hole=0.4),
                              use_container_width=True)
        abnormal_maintenance_costs = maintenance_history_data[maintenance_history_data['MaintenanceStatus'] == 'Abnormal']
        chartcol.plotly_chart(px.bar(abnormal_maintenance_costs,
                                     x='VehicleID',
                                     y='Cost',
                                     title='Abnormal Maintenance Costs by Vehicle',
                                     color='MaintenanceType',
                                     labels={'Cost': 'Total Cost (EGP)', 'VehicleID': 'Vehicle ID', 'MaintenanceType': 'Maintenance Type'},
                                     color_discrete_sequence=px.colors.qualitative.Set2), text_auto=True,
                              use_container_width=True)

    elif report_option == "Traffic Penalties":
        st.subheader("Traffic Penalties")
        st.write("Explore traffic penalties recorded for each vehicle.")

        # Query traffic penalties data
        traffic_penalties_data = pd.read_sql_query(f'''
                SELECT
                    TP.PenaltyID AS "Penalty ID",
                    TP.Date,
                    TP.VehicleID AS "Vehicle ID",
                    VB.VehicleType AS "Vehicle Type",
                    VA.Agency,
                    VA.Condition,  -- Assuming there is a "Condition" column in the VehicleAllocation table
                    TP.Location,
                    TP.Desc AS "Description",
                    TP.Cost,
                    TP.CompanyCode AS "Company Code"
                FROM TrafficPen TP
                LEFT JOIN (
                    SELECT
                        VA1.VehicleID,
                        VA1.Agency,
                        VA1.Condition,
                        ROW_NUMBER() OVER (PARTITION BY VA1.VehicleID ORDER BY VA1.AllocationID DESC) AS row_num
                    FROM VehicleAllocation VA1
                ) VA ON TP.VehicleID = VA.VehicleID AND VA.row_num = 1
                LEFT JOIN VehicleBasics VB ON TP.VehicleID = VB.VehicleID
                WHERE TP.Date BETWEEN ? AND ? AND {where_clause_str};
            ''', con=conn, params=(start_date, end_date))

        # Remove duplications
        traffic_penalties_data = traffic_penalties_data.drop_duplicates()

        # Translate the "Desc" column
        traffic_penalties_data["Description"] = traffic_penalties_data["Description"].map(translations)

        # Display the total cost
        st.write(f"The total cost for the selected period is: {traffic_penalties_data['Cost'].sum():,.0f} EGP")

        # Display the traffic penalties data in a table
        datacol, chartcol = st.columns([2, 1])
        datacol.dataframe(traffic_penalties_data, use_container_width=True, hide_index=True)
        # Display a horizontal bar chart for the total cost of traffic penalties by violation type
        penalty_cost_distribution = traffic_penalties_data.groupby('Description')['Cost'].sum().reset_index().sort_values(by='Cost', ascending=True)

        fig = px.bar(penalty_cost_distribution, y='Description', x='Cost', orientation='h',
                     title='Total Penalty Cost by Violation Type',
                     labels={'Cost': 'Total Cost (EGP)', 'Description': 'Violation Type'},
                     text='Cost', height=700, width=800,
                     color_discrete_sequence=px.colors.qualitative.Set1)

        # Improve text formatting on bars
        fig.update_traces(texttemplate='%{text:.2s}', textposition='auto')
        fig.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')

        # Display the chart
        chartcol.plotly_chart(fig, use_container_width=True, )

        # Display a bar chart for the total cost of traffic penalties by vehicle and agency
        penalty_cost_distribution = traffic_penalties_data.groupby(['Agency', 'Vehicle ID'])['Cost'].sum().reset_index()
        chartcol.plotly_chart(px.bar(penalty_cost_distribution, x='Vehicle ID', y='Cost', color='Agency',
                                     title='Total Penalty Cost by Vehicle and Agency',
                                     labels={'Cost': 'Total Cost (EGP)', 'Vehicle ID': 'Vehicle ID'},
                                     text='Cost', height=500, width=900,
                                     color_discrete_sequence=px.colors.qualitative.Set2),
                              use_container_width=True)

        # Display a pie chart for the distribution of total penalty cost by agency
        penalty_cost_distribution = traffic_penalties_data.groupby(['Agency'])['Cost'].sum().reset_index().sort_values(by='Cost', ascending=False)
        chartcol.plotly_chart(px.pie(penalty_cost_distribution, names='Agency', values='Cost',
                                     title='Total Penalty Cost Distribution by Agency',
                                     labels={'Cost': 'Total Cost (EGP)', 'Agency': 'Agency'},
                                     height=500,
                                     color_discrete_sequence=px.colors.qualitative.Set3,
                                     hole=0.4),
                              use_container_width=True)
    elif report_option == "Fuel Fraud":
        st.subheader("Fuel Fraud Report")
        st.write(
            "This report detects potential fuel fraud based on the last 4 fuelings for each vehicle. "
            "It identifies vehicles that have exceeded 400 km per day in the last 4 fuelings."
        )

        # Query fuel data
        fuel_data = fetch_fuel_data(conn, start_date, end_date, where_clause_str)

        # Convert the "Date" column to datetime
        fuel_data["Date"] = pd.to_datetime(fuel_data["Date"])

        # Remove duplications
        fuel_data = fuel_data.drop_duplicates()

        # Display the fuel data in a table
        st.subheader("Fuel Data Overview")
        st.dataframe(fuel_data, use_container_width=True, hide_index=True)

        # Detect potential fuel fraud
        fraud_data = fuel_data.groupby("Vehicle ID").apply(lambda group: detect_fuel_fraud(group)).reset_index(drop=True)

        # Display potential fuel fraud data
        st.subheader("Potential Fuel Fraud")
        st.write(
            "The following table shows vehicles with potential fuel fraud (exceeded 400 km per day in the last 4 fuelings):"
        )

        # Enhance the display of the fraud_data table
        st.dataframe(fraud_data.sort_values(by="Expected Kilometers",ascending=False), use_container_width=True, hide_index=True)

def fetch_fuel_data(conn, start_date, end_date, where_clause_str):
    query = f'''
        SELECT
            F.FuelID AS "Fuel ID",
            F.Date as "Date",
            F.VehicleID AS "Vehicle ID",
            VB.VehicleType AS "Vehicle Type",
            VA.Agency,
            F.Amount AS "Fuel Amount (Liters)",
            F.Cost AS "Fuel Cost (EGP)"
        FROM Fuel F
        LEFT JOIN VehicleBasics VB ON F.VehicleID = VB.VehicleID
        LEFT JOIN (
            SELECT
                VA1.VehicleID,
                VA1.Agency,
                ROW_NUMBER() OVER (PARTITION BY VA1.VehicleID ORDER BY VA1.AllocationID DESC) AS row_num
            FROM VehicleAllocation VA1
        ) VA ON F.VehicleID = VA.VehicleID AND VA.row_num = 1
        WHERE F.Date BETWEEN ? AND ? AND {where_clause_str}
    '''
    return pd.read_sql_query(query, con=conn, params=(start_date, end_date))

def detect_fuel_fraud(group):
    group = group.sort_values(by="Date", ascending=False).head(4)
    group["Days"] = (group["Date"].max() - group["Date"]).dt.days
    grouppp = group.groupby(['Vehicle ID', 'Vehicle Type', 'Agency']).agg({'Days': 'max', 'Fuel Amount (Liters)': 'sum'}).reset_index()
    grouppp['Fuel Amount (Liters)'] -= group['Fuel Amount (Liters)'].iloc[0]
    group = grouppp
    group["Fuel Efficiency (km/l)"] = 8
    group["Expected Kilometers"] = ((group["Fuel Efficiency (km/l)"] * group["Fuel Amount (Liters)"]) / group["Days"])
    group.replace([np.inf, -np.inf], np.nan, inplace=True)
    group["Exceeded 400 km per Day"] = group["Expected Kilometers"] > 400
    group = group.loc[group['Exceeded 400 km per Day']]
    return group[["Vehicle ID", "Vehicle Type", "Agency", "Days", "Fuel Amount (Liters)", "Fuel Efficiency (km/l)", "Expected Kilometers", "Exceeded 400 km per Day"]].sort_values(by="Expected Kilometers")

# Main content
def main():
    st.header("Welcome to J&T Fleet Management System")
    reports()


if __name__ == '__main__':
    main()
