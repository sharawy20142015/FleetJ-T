import sqlite3
import datetime
import streamlit as st
import pandas as pd
import plotly.express as px
import base64
import plotly.graph_objects as go

# Set page title and icon
st.set_page_config(
    page_title="J&T Fleet Management",
    layout='wide',
    page_icon='logo.png'
)

with open('banner33.png', 'rb') as f:
    image_data = f.read()
    image_base64 = base64.b64encode(image_data).decode()

# Add the background image using custom CSS
st.markdown(
    f"""
    <style>
        .stApp {{
            background-image: url('data:image/png;base64,{image_base64}');
            background-position: top;
            background-repeat: no-repeat;
            background-size: 2500px; 
            background-color: white
        }}  
    </style>
    """,
    unsafe_allow_html=True
)

# Connect to the SQLite database
conn = sqlite3.connect('fleet_management.db')
cursor = conn.cursor()


def create_download_button(df, filename):
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}.csv" style="color: #ffffff; text-decoration: none; padding: 10px; background-color: #E62129; border-radius: 5px; margin-top: 10px; transition: background-color 0.3s;">Download ' \
           f'Data</a>'
    return href


@st.cache_data(ttl=60 * 15)
def efficiency():
    query = '''
    WITH RankedAllocations AS (
        SELECT
            VA.VehicleID,
            VA.Agency,
            ROW_NUMBER() OVER (PARTITION BY VA.VehicleID ORDER BY VA.AllocationID DESC) AS RowNum
        FROM VehicleAllocation VA
    )
    
    SELECT
        F.Date,
        F.VehicleID,
        F.Mileage,
        F.Type,
        F.Amount,
        F.Cost,
        V.VehicleType,
        VA.Agency
    FROM Fuel F
    LEFT JOIN VehicleBasics V ON F.VehicleID = V.VehicleID
    LEFT JOIN RankedAllocations VA ON F.VehicleID = VA.VehicleID AND VA.RowNum = 1;

    '''

    df = pd.read_sql_query(query, conn).drop_duplicates()
    try:
        df['Date'] = pd.to_datetime(df['Date'], format='mixed')
    except ValueError:
        df['Date'] = pd.to_datetime(df['Date'])
    grouped = df.groupby('VehicleID')

    vehicle_efficiency_data = []

    for vehicle_id, group in grouped:
        group = group.sort_values(by='Date', ascending=False)

        most_recent_date = group['Date'].iloc[0]

        last_7_days = most_recent_date - datetime.timedelta(days=7)

        group = group[group['Date'] >= last_7_days]

        total_distance = group['Mileage'].max() - group['Mileage'].min()

        total_fuel = group['Amount'].sum() - group['Amount'].iloc[0]  # Subtract the last fuel amount

        if total_fuel > 0:  # Check if there was any fuel consumption in the last 7 days
            fuel_efficiency = total_distance / total_fuel
        else:
            fuel_efficiency = 0  # Set efficiency to 0 if no fuel was consumed

        vehicle_type = group['VehicleType'].values[0]
        vehicle_area = group['Agency'].values[0]
        total_cost = group['Cost'].values[0]

        vehicle_efficiency_data.append({
            'VehicleID': vehicle_id,
            'VehicleType': vehicle_type,
            'Agency': vehicle_area,
            'FuelEfficiency': fuel_efficiency,
            'Cost': total_cost
        })

    # Create a DataFrame from the results
    fuel_efficiency_df = pd.DataFrame(vehicle_efficiency_data)
    fuel_efficiency_df = fuel_efficiency_df.loc[
        (fuel_efficiency_df['FuelEfficiency'] > 0) &
        (fuel_efficiency_df['FuelEfficiency'] < 40)
        ]

    return fuel_efficiency_df


def fuelcost():
    # Get the most recent date from the database
    most_recent_date_str = cursor.execute("SELECT MAX(Date) FROM Fuel").fetchone()[0]

    # Convert the most recent date string to a datetime object
    most_recent_date = datetime.datetime.strptime(most_recent_date_str, '%Y-%m-%d %H:%M:%S')

    # Calculate the date range
    end_date = most_recent_date
    start_date = end_date - datetime.timedelta(days=7)  # Last week
    week_before_start_date = start_date - datetime.timedelta(days=7)  # The week before

    # Use the date range in your query
    query = """
    SELECT
        ? AS MostRecentDate,
        SUM(CASE WHEN Date >= ? AND Date < ? THEN Cost ELSE 0 END) AS LastWeekCost,
        SUM(CASE WHEN Date >= ? AND Date < ? THEN Cost ELSE 0 END) AS WeekBeforeCost
    FROM Fuel
    WHERE Date >= ? AND Date < ?
    """

    cursor.execute(query, (most_recent_date_str, start_date, end_date, week_before_start_date, start_date, week_before_start_date, end_date))
    result = cursor.fetchone()
    return result


def trafficcost():
    # Get the most recent date from the database
    most_recent_date_str = cursor.execute("SELECT MAX(Date) FROM TrafficPen").fetchone()[0]

    # Convert the most recent date string to a datetime object
    most_recent_date = datetime.datetime.strptime(most_recent_date_str, '%Y-%m-%d %H:%M:%S')

    # Calculate the date range
    end_date = most_recent_date
    start_date = end_date - datetime.timedelta(days=7)  # Last week
    week_before_start_date = start_date - datetime.timedelta(days=7)  # The week before

    # Use the date range in your query
    query = """
    SELECT
        ? AS MostRecentDate,
        SUM(CASE WHEN Date >= ? AND Date < ? THEN Cost ELSE 0 END) AS LastWeekCost,
        SUM(CASE WHEN Date >= ? AND Date < ? THEN Cost ELSE 0 END) AS WeekBeforeCost
    FROM TrafficPen
    WHERE Date >= ? AND Date < ?
    """

    cursor.execute(query, (most_recent_date_str, start_date, end_date, week_before_start_date, start_date, week_before_start_date, end_date))
    result = cursor.fetchone()
    return result


@st.cache_data(ttl=60 * 15)
def efficiency_old():
    query = '''
    WITH RankedAllocations AS (
        SELECT
            VA.VehicleID,
            VA.Agency,
            ROW_NUMBER() OVER (PARTITION BY VA.VehicleID ORDER BY VA.AllocationID DESC) AS RowNum
        FROM VehicleAllocation VA
    )
    
    SELECT
        F.Date,
        F.VehicleID,
        F.Mileage,
        F.Type,
        F.Amount,
        F.Cost,
        V.VehicleType,
        VA.Agency
    FROM Fuel F
    LEFT JOIN VehicleBasics V ON F.VehicleID = V.VehicleID
    LEFT JOIN RankedAllocations VA ON F.VehicleID = VA.VehicleID AND VA.RowNum = 1;

    '''

    df = pd.read_sql_query(query, conn)
    try:
        df['Date'] = pd.to_datetime(df['Date'], format='mixed')
    except ValueError:
        df['Date'] = pd.to_datetime(df['Date'])
    grouped = df.groupby('VehicleID')

    vehicle_efficiency_data = []
    for vehicle_id, group in grouped:
        group = group.sort_values(by='Date', ascending=False)

        most_recent_date = group['Date'].iloc[0]

        last_7_days = most_recent_date - datetime.timedelta(days=7)

        last_14_days = last_7_days - datetime.timedelta(days=7)

        group_last_7_to_14_days = group[(group['Date'] >= last_14_days) & (group['Date'] < last_7_days)]
        if group_last_7_to_14_days.shape[0] > 0:

            total_distance_last_7_to_14_days = group_last_7_to_14_days['Mileage'].max() - group_last_7_to_14_days['Mileage'].min()

            total_fuel_last_7_to_14_days = group_last_7_to_14_days['Amount'].sum() - group_last_7_to_14_days['Amount'].iloc[-1]

            if total_fuel_last_7_to_14_days > 0:  # Check if there was any fuel consumption in the 7 days before the last 7 days
                fuel_efficiency_last_7_to_14_days = total_distance_last_7_to_14_days / total_fuel_last_7_to_14_days
            else:
                fuel_efficiency_last_7_to_14_days = 0  # Set efficiency to 0 if no fuel was consumed during that period

            vehicle_type = group['VehicleType'].values[0]
            total_cost = group['Cost'].values[0]

            vehicle_efficiency_data.append({
                'VehicleID': vehicle_id,
                'VehicleType': vehicle_type,
                'FuelEfficiencyLast7Days': fuel_efficiency_last_7_to_14_days,
                'Cost': total_cost
            })

        # Create a DataFrame from the results
        fuel_efficiency_df = pd.DataFrame(vehicle_efficiency_data)
        fuel_efficiency_df = fuel_efficiency_df.loc[
            (fuel_efficiency_df['FuelEfficiencyLast7Days'] > 0) &
            (fuel_efficiency_df['FuelEfficiencyLast7Days'] < 40)
            ]

    return fuel_efficiency_df


url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR38RHrj7Ne1De_dZg7xf7T8bdD2iZt0MHcOhnbfhXbZkRaOIfsbyJEMeZ4FxKmSN-pRza9s6CcX38k/pub?gid=247980336&single=true&output=csv"

maintdf = pd.read_csv(url, skiprows=1).fillna(0)


# Dashboard section
def dashboard():
    st.title("Fleet Dashboard")

    # Display key performance indicators
    col1, col2, col3, col4, col6, col5 = st.columns(6)

    # Total Vehicles
    cursor.execute("SELECT COUNT(*) FROM VehicleBasics")
    total_vehicles = cursor.fetchone()[0]
    with col1:
        st.metric("🚚 Total Vehicles", f"{total_vehicles:,.0f}", help="Total vehicles in the fleet.")

    # Maintenance Due
    with col2:
        due_count = maintdf.iloc[10, 19]
        st.metric("🔧 Under Maintenance", f"{due_count:,.0f}", help="Vehicles currently under maintenance.")

    # Vehicles with Expired Licenses
    cursor.execute('''SELECT count(vl.VehicleID), vl.LicenseID
        FROM VehiclesLicenses vl
        WHERE vl.EndDate < DATE('now')
        AND vl.LicenseID = (
            SELECT MAX(vl_inner.LicenseID)
            FROM VehiclesLicenses vl_inner
            WHERE vl_inner.VehicleID = vl.VehicleID
        )''')
    expired_licenses = cursor.fetchone()[0]
    percentage_expired_licenses = (expired_licenses / total_vehicles) * 100
    percentage_expired_licenses_str = f"{percentage_expired_licenses:.2f}%"

    with col3:
        st.metric("📅 Expired Licenses", expired_licenses, help=f"Number of vehicles with expired licenses ({percentage_expired_licenses_str} of total vehicles).")

    # Fuel Efficiency (Average)
    fuel_eff = efficiency()
    avg_fuel_efficiency = fuel_eff.FuelEfficiency.mean()
    fuel_eff_old = efficiency_old()
    avg_fuel_efficiency_old = fuel_eff_old.FuelEfficiencyLast7Days.mean()
    with col4:
        st.metric("⛽ Fuel Efficiency (KM/L)", f"{avg_fuel_efficiency:,.1f}", help=f"Average fuel efficiency (KM/L) of the fleet. (Last updated on {fuelcost()[0]})", delta=f"{avg_fuel_efficiency - avg_fuel_efficiency_old:,.1f}")

    with col6:
        total_cost, last_update_date = fuelcost()[1], fuelcost()[0]
        total_cost_old = fuelcost()[2]
        formatted_cost = f"EGP {total_cost / 1000:.2f}K"
        help_message = f"Weekly Fuel Cost of vehicles in EGP. (Last updated on {last_update_date})"
        st.metric("⛽ Weekly Fuel Cost", formatted_cost, help=help_message, delta=f"{(total_cost - total_cost_old) / 1000:,.2f}K", delta_color='inverse')

    # Penalties
    # cursor.execute("SELECT AVG(Efficiency) FROM fuel_efficiency")
    # avg_fuel_efficiency = cursor.fetchone()[0]
    with col5:
        total_cost, last_update_date = trafficcost()[1], trafficcost()[0]
        total_cost_old = trafficcost()[2]
        formatted_penalties = f"EGP {total_cost / 1000:.2f}K"
        st.metric("🚦 Weekly Traffic Penalties", formatted_penalties, help=f"Weekly Traffic penalties of the vehicles in EGP. (Last updated on {last_update_date})", delta=f"{(total_cost - total_cost_old) / 1000:,.2f}K", delta_color='inverse')

    # Fuel Efficiency by Vehicle Type (Chart)
    st.markdown("<hr>", unsafe_allow_html=True)
    st.subheader("Fleet Analysis")
    coll1, coll2 = st.columns(2)

    with coll1.expander("**Fuel Efficiency**", expanded=True):
        average_efficiency_by_type = efficiency().groupby('VehicleType')['FuelEfficiency'].mean().reset_index()
        average_efficiency_by_type.columns = ['Vehicle Type', 'Average Fuel Efficiency (KM/L)']
        average_efficiency_by_type = average_efficiency_by_type.sort_values(by='Average Fuel Efficiency (KM/L)', ascending=False)
        fig = px.bar(average_efficiency_by_type, x="Vehicle Type", y="Average Fuel Efficiency (KM/L)", text="Average Fuel Efficiency (KM/L)",
                     labels={"Vehicle Type": "Vehicle Type", "Average Fuel Efficiency (KM/L)": "Fuel Efficiency (KM/L)"},
                     title="Average Fuel Efficiency by Vehicle Type")

        # Update the color scheme to be more reddish
        fig.update_traces(marker_color='#E62129', texttemplate='%{text:.1f}', textposition='auto')

        # Customize the layout for better visuals
        fig.update_layout(
            plot_bgcolor='rgba(0, 0, 0, 0)',
            paper_bgcolor='rgba(0, 0, 0, 0)',
            xaxis_title="Vehicle Type",
            yaxis_title="Fuel Efficiency (KM/L)",
            font=dict(family="Arial", size=12),
            title_font=dict(family="Arial", size=16),
            showlegend=False  # Remove the legend
        )

        st.plotly_chart(fig, use_container_width=True)
        fuel_efficiency_data = efficiency().groupby(['Agency', 'VehicleType'])['FuelEfficiency'].mean().reset_index()

        fig = go.Figure()

        # Create a heatmap
        heatmap = go.Heatmap(
            z=fuel_efficiency_data['FuelEfficiency'].values,
            x=fuel_efficiency_data['Agency'].values,
            y=fuel_efficiency_data['VehicleType'].values,
            colorscale='Reds',
            zmin=fuel_efficiency_data['FuelEfficiency'].min(),
            zmax=fuel_efficiency_data['FuelEfficiency'].max(),
            hoverinfo="x+y+z",  # Display x, y, and z (Fuel Efficiency) in the hover tooltip
        )

        fig.add_trace(heatmap)

        # Add text annotations for each cell
        for i in range(len(fuel_efficiency_data)):
            x = fuel_efficiency_data['Agency'].values[i]
            y = fuel_efficiency_data['VehicleType'].values[i]
            text = f"{fuel_efficiency_data['FuelEfficiency'].values[i]:.1f}"

            fig.add_annotation(
                x=x,
                y=y,
                text=text,
                showarrow=False,
                font=dict(color='black', size=12)  # Adjust text color and size
            )

        fig.update_xaxes(categoryorder='total ascending', showline=False, showgrid=False)
        fig.update_yaxes(showline=False, showgrid=False)
        fig.update_layout(
            title_text='Fuel Efficiency by Vehicle Type and Area',
            coloraxis_colorbar_title='Fuel Efficiency',
            plot_bgcolor='rgba(0, 0, 0, 0)',
            paper_bgcolor='rgba(0, 0, 0, 0)',
        )

        st.plotly_chart(fig, use_container_width=True)
        st.markdown(create_download_button(fuel_efficiency_data, "Download Data"), unsafe_allow_html=True)
    with coll2.expander("**Maintenance Status**", expanded=True):
        # Create a pie chart for Vehicle Status
        cursor.execute('''    
        WITH RankedAllocations AS (
            SELECT
                VB.VehicleID AS "Vehicle ID",
                VA.Condition,
                ROW_NUMBER() OVER (PARTITION BY VB.VehicleID ORDER BY VA.AllocationID DESC) AS RowNum
            FROM
                VehicleBasics VB
                LEFT JOIN VehicleAllocation VA ON VB.VehicleID = VA.VehicleID
            WHERE
                VA.Condition = "Inactive"
        )
        SELECT
            "Vehicle ID",
            Condition
        FROM
            RankedAllocations
        WHERE
            RowNum = 1;
        ''')
        stolen = cursor.fetchall()
        stolen_df = pd.DataFrame(stolen)
        stolen_count = len(stolen_df)

        due_count = maintdf.iloc[10, 19]
        cursor.execute("SELECT COUNT(*) FROM VehicleBasics")
        total_vehicles = cursor.fetchone()[0]

        # Create a DataFrame with all vehicle statuses
        maintenance_data = pd.DataFrame({
            "Status": ["Normally Working", "Under Maintenance", "Lost"],
            "Count": [total_vehicles - due_count - stolen_count, due_count, stolen_count]
        })

        colors = ['#E62129', '#FFAB33', '#000000']

        maintenance_fig = px.pie(
            maintenance_data,
            values="Count",
            names="Status",
            title="Vehicle Status",
            color_discrete_sequence=colors,
        )

        # Further customizations
        maintenance_fig.update_traces(
            textinfo='percent+label',
            pull=[0, 0.1, 0.1],
            marker=dict(line=dict(color='#FFFFFF', width=2)
                        )
        )

        # Customize the layout for better visuals
        maintenance_fig.update_layout(
            plot_bgcolor='rgba(0, 0, 0, 0)',
            paper_bgcolor='rgba(0, 0, 0, 0)',
            title_font=dict(family="Arial", size=16),
            showlegend=False
        )

        st.plotly_chart(maintenance_fig, use_container_width=True)
        st.markdown(create_download_button(maintdf, "maintenance_data"), unsafe_allow_html=True)

    with coll2.expander("**Total Vehicles by Location and Type**", expanded=True):
        # Create a bar chart for Total Vehicles
        cursor.execute("""
        SELECT A.Agency, COUNT(DISTINCT B.VehicleID) AS TotalVehicles, B.VehicleType
        FROM VehicleAllocation A
        LEFT JOIN VehicleBasics B ON A.VehicleID = B.VehicleID
        WHERE A.AllocationID IN (
            SELECT MAX(AllocationID)
            FROM VehicleAllocation
            GROUP BY VehicleID
        )
        GROUP BY A.Agency, B.VehicleType
        """)
        total_vehicles_data = pd.DataFrame(cursor.fetchall(), columns=["Location", 'Total Vehicles', "VehicleType"])
        fig = px.sunburst(total_vehicles_data, path=['Location', 'VehicleType'], values='Total Vehicles', color='Location', color_discrete_sequence=px.colors.qualitative.Set3,
                          maxdepth=2,
                          hover_data={
                              'Total Vehicles': ':,.0f',
                          },
                          custom_data=['Location', 'VehicleType', 'Total Vehicles']
                          )

        # Update the layout of the chart

        fig.update_layout(
            plot_bgcolor='rgba(0, 0, 0, 0)',
            paper_bgcolor='rgba(0, 0, 0, 0)',
            font=dict(family="Arial", size=12),
            title='Total Vehicles by Location and Type',
            title_font=dict(family="Arial", size=16),
        )

        # Update the hovertemplate of the chart to show the custom data
        fig.update_traces(
            hovertemplate='<br>'.join([
                'Location: %{customdata[0]}',
                'VehicleType: %{customdata[1]}',
                'Total Vehicles: %{customdata[2]:,.0f}',
            ])
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown(create_download_button(total_vehicles_data, "total_vehicles_types"), unsafe_allow_html=True)

    with coll1.expander("**Total Vehicles by Location**", expanded=True):
        # Create a bar chart for Total Vehicles
        cursor.execute("""
        SELECT A.Agency, COUNT(DISTINCT B.VehicleID) AS TotalVehicles
        FROM VehicleAllocation A
        LEFT JOIN VehicleBasics B ON A.VehicleID = B.VehicleID
        WHERE A.AllocationID IN (
            SELECT MAX(AllocationID)
            FROM VehicleAllocation
            GROUP BY VehicleID
        )
        GROUP BY A.Agency
        """)
        total_vehicles_data = pd.DataFrame(cursor.fetchall(), columns=["Location", "Total Vehicles"]).sort_values(by='Total Vehicles', ascending=False)
        fig = px.bar(total_vehicles_data, x="Location", y="Total Vehicles", text="Total Vehicles",
                     title="Total Vehicles by Location")

        # Update the color scheme to be more reddish
        fig.update_traces(marker_color='#E62129', textposition='auto')

        # Customize the layout for better visuals
        fig.update_layout(
            plot_bgcolor='rgba(0, 0, 0, 0)',
            paper_bgcolor='rgba(0, 0, 0, 0)',
            xaxis_title="Location",
            yaxis_title="Total Vehicles",
            font=dict(family="Arial", size=12),
            title_font=dict(family="Arial", size=16),
            showlegend=False  # Remove the legend
        )

        st.plotly_chart(fig, use_container_width=True)
        st.markdown(create_download_button(total_vehicles_data, "total_vehicles"), unsafe_allow_html=True)


# Reports section
def add_logo():
    # Read the local image file
    with open('Daco_5026733.png', 'rb') as f:
        local_image_data = f.read()
        local_image_base64 = base64.b64encode(local_image_data).decode('utf-8')

    # Create the CSS style with the local image as the background
    css = f"""
    <style>
        [data-testid="stSidebarNav"] {{
            background-image: url(data:image/jpeg;base64,{local_image_base64});
            background-repeat: no-repeat;
            padding-top: 40px;
            background-position: 20px 20px;
            background-size: 80%; /* Match the sidebar width */
        }}
        [data-testid="stSidebarNav"]::before {{
            content: "Navigation";
            margin-left: 20px;
            margin-top: 20px;
            font-size: 30px;
            position: relative;
            top: 90px;
        }}
    </style>
    """

    st.markdown(css, unsafe_allow_html=True)


# Main content
def main():
    add_logo()
    st.header("Welcome to J&T Fleet Management System")
    efficiency()
    dashboard()


if __name__ == '__main__':
    main()
