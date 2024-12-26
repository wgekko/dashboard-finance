import streamlit as st
import pandas as pd
from datetime import timedelta, datetime
import plotly.express as px
import warnings
warnings.simplefilter("ignore", category=FutureWarning)


st.set_page_config(page_title="Dashboard", page_icon="images/logo1.png", layout="wide")

#--------------- funciones de desarrollo de la appp
#@st.cache_data
def load_data():
    data = pd.read_excel("datos/datos.xlsx")
    data.columns = data.columns.astype(str)
    data['FECHA'] = pd.to_datetime(data['FECHA'])    
    return data

# --------------  funcion para determinar los trimestres --------------------------
def custom_quarter(date):
    month = date.month
    year = date.year
    if month in [2, 3, 4]:
        return pd.Period(year=year, quarter=1, freq='Q')
    elif month in [5, 6, 7]:
        return pd.Period(year=year, quarter=2, freq='Q')
    elif month in [8, 9, 10]:
        return pd.Period(year=year, quarter=3, freq='Q')
    else:  # month in [11, 12, 1]
        return pd.Period(year=year if month != 1 else year-1, quarter=4, freq='Q')

# -----------------  funcion para asignar los datos de periodos de tiempo a los datos----
def aggregate_data(df, freq):
    if freq == 'Q':
        df = df.copy()
        df['CUSTOM_Q'] = df['FECHA'].apply(custom_quarter)
        df_agg = df.groupby('CUSTOM_Q').agg({
            'BITCOIN': 'mean',
            'BLUE': 'mean',
            'MERV': 'mean',
            'AL30D': 'mean',
            'R-BIT': 'mean',
            'R-BLUE': 'mean',
            'R-MERV': 'mean',
            'R-AL30D': 'mean'    
        })
        return df_agg
    else:
        return df.resample(freq, on='FECHA').agg({
            'BITCOIN': 'mean',
            'BLUE': 'mean',
            'MERV': 'mean',
            'AL30D': 'mean', 
            'R-BIT': 'mean',
            'R-BLUE': 'mean',
            'R-MERV': 'mean',
            'R-AL30D': 'mean'
        })


#----------------  diseñar el formato de saluda de los datos a mostrar ------------------------

def get_weekly_data(df):
    return aggregate_data(df, 'W-MON')

def get_monthly_data(df):
    return aggregate_data(df, 'ME')

def get_quarterly_data(df):
    return aggregate_data(df, 'Q')

def format_with_commas(number):
    return f"{number:,.2f}"

# ----------------creando los graficos que exponen las metricas ---------------------------------
def create_metric_chart(df, column, color, chart_type,  height=250, time_frame='Diario'):  
   
    chart_data = df[[column]].copy() 
    if time_frame == 'Trimestral':
        chart_data.index = chart_data.index.strftime('%Y Q%q ')
    if chart_type == 'Barras':  
        fig = px.bar(chart_data, y=column, x=chart_data.index)
        fig.update_traces(marker_color=color)  # Asignar color fijo a las barras
        fig.update_layout(height=height)
        st.plotly_chart(fig)
        
    if chart_type == 'Area':  
        fig1 = px.area(chart_data, y=column, x=chart_data.index)
        fig1.update_traces(fillcolor=color)  # Asignar color fijo al área
        fig1.update_layout(height=height)
        st.plotly_chart(fig1)        

# ----------------creando los graficos que exponen las metricas ---------------------------------
def create_metric_chart_hist(df, column, color, chart_type,  height=250, time_frame='Diario'):  
    # Seleccionar las columnas correctas
    df1 = df[['R-BIT', 'R-BLUE', 'R-MERV', 'R-AL30D']]    
    # Asegurarse de que la columna exista en el DataFrame
    if column not in df1.columns:
        st.error(f"La columna '{column}' no está presente en el DataFrame.")
        return
    n_bins = 25
    chart_data_hist = df1[[column]].copy()
    # Crear un key único para el gráfico
    unique_key = f"{chart_type}_{column}_{color}"
    # Crear gráfico de barras
    if chart_type == 'Barras':  
        fig2 = px.histogram(chart_data_hist, x=column, nbins=n_bins)
        fig2.update_traces(marker_color=color)  # Asignar color fijo a las barras
        fig2.update_layout(height=height)
        st.plotly_chart(fig2, key=unique_key)
        
    # Crear gráfico de área
    if chart_type == 'Area':  
        fig3 = px.histogram(chart_data_hist, x=column, nbins=n_bins)
        fig3.update_traces(marker_color=color)  # Asignar color fijo a las barras
        fig3.update_layout(height=height)
        st.plotly_chart(fig3, key=unique_key)
        
# ------------- determinacion de los dias para saber si faltan completar los periodos de tiempo -------

def is_period_complete(date, freq):
    today = datetime.now()
    if freq == 'D':
        return date.date() < today.date()
    elif freq == 'W':
        return date + timedelta(days=6) < today
    elif freq == 'ME':
        next_month = date.replace(day=28) + timedelta(days=4)
        return next_month.replace(day=1) <= today
    elif freq == 'Q':
        current_quarter = custom_quarter(today)
        return date < current_quarter

# ---------------- calculo de variación  de acuerdo a los periodos seleccioandos .--------------------
def calculate_delta(df, column):
    if len(df) < 2:
        return 0, 0
    current_value = df[column].iloc[-1]
    previous_value = df[column].iloc[-2]
    delta = current_value - previous_value
    delta_percent = (delta / previous_value) * 100 if previous_value != 0 else 0
    return delta, delta_percent

# -------------------- se despliegan las metricas con datos y gráficos ---------------------------
def display_metric(col, title, value, df, column, color, time_frame):
    with col:
        with st.container(border=True):
            delta, delta_percent = calculate_delta(df, column)
            delta_str = f"{delta:+,.0f} ({delta_percent:+.2f}%) - var.cotización"        
            st.metric(title, format_with_commas(value), delta=delta_str)
            create_metric_chart(df, column, color, time_frame=time_frame, chart_type=chart_selection)              
            last_period = df.index[-1]
            freq = {'Diario': 'D', 'Semanal': 'W', 'Mensual': 'ME', 'Trimestral': 'Q'}[time_frame]
            if not is_period_complete(last_period, freq):
                st.caption(f"Nota: El ultimo dato {time_frame.lower() if time_frame != 'Diario' else 'day'} está incompleto.")

# -------------------- se despliegan las metricas con datos y gráficos para rendimiento esperado  ---------------------------
def display_metric_rend(col, title, value, df, column, color, time_frame):
    with col:
        with st.container(border=True):            
            delta_str = f"diferencia (máx y min) del rend. en %"       
            st.metric(title, format_with_commas(value), delta=delta_str)
            create_metric_chart(df, column, color, time_frame=time_frame, chart_type=chart_selection)            
            last_period = df.index[-1]
            freq = {'Diario': 'D', 'Semanal': 'W', 'Mensual': 'ME', 'Trimestral': 'Q'}[time_frame]
            if not is_period_complete(last_period, freq):
                st.caption(f"Nota: El ultimo dato {time_frame.lower() if time_frame != 'Diario' else 'day'} está incompleto.")

# -------------------- se despliegan las metricas con datos y gráficos para rendimiento esperado  ---------------------------
def display_metric_hist(col, title, total_value, df, column, color, time_frame):
    with col:
        with st.container(border=True):            
            delta_str = f"desviación de la media en %"       
            st.metric(title, format_with_commas(total_value), delta=delta_str)
            create_metric_chart_hist(df, column, color, time_frame=time_frame, chart_type=chart_selection)            
            last_period = df.index[-1]
            freq = {'Diario': 'D', 'Semanal': 'W', 'Mensual': 'ME', 'Trimestral': 'Q'}[time_frame]
            if not is_period_complete(last_period, freq):
                st.caption(f"Nota: El ultimo dato {time_frame.lower() if time_frame != 'Diario' else 'day'} está incompleto.")

# Load data ------------- se cargar los datos para el calculo
df = load_data()

# Set up input widgets
st.logo(image="images/logo3.png",
      size='large')

with st.sidebar:   
    st.title("Dashboard-Financiero")
    st.title("Métricas-Activos")
    st.header("Configuración")      
    max_date = df['FECHA'].max().date()
    min_date = df['FECHA'].min().date()
    default_start_date = min_date 
    default_end_date = max_date
    start_date = st.date_input("Fecha Incio", default_start_date, min_value=df['FECHA'].min().date(), max_value=max_date)
    end_date = st.date_input("Fecha Final", default_end_date, min_value=df['FECHA'].min().date(), max_value=max_date)
    time_frame = st.selectbox("Seleccionar período de tiempo",
                              ("Diario", "Semanal", "Mensual", "Trimestral"),
    )
    chart_selection = st.selectbox("Seleccionar tipo de gráfico",
                                   ("Barras", "Area"),
    )

# Prepare data based on selected time frame
if time_frame == 'Diario':
    df_display = df.set_index('FECHA')
elif time_frame == 'Semanal':
    df_display = get_weekly_data(df)
elif time_frame == 'Mensual':
    df_display = get_monthly_data(df)
elif time_frame == 'Trimestral':
    df_display = get_quarterly_data(df)

# Display Key Metrics --- mostrar los datos y metricas 
st.subheader("Datos Estatisticos - Media de Activos Financieros")

#----------------- configuración de metricas a desplegar ---------------------------
metrics = [
    ("Bitcoin-Media", "BITCOIN", '#29b5e8'),
    ("Blue-Media", "BLUE", '#FF9F36'),
    ("Ind.Merval-Media", "MERV", '#FF3383'),
    ("AL30D-Media", "AL30D", '#7D44CF')    
]

metrics_uno = [
    ("Rend.Esp.Bitcoin (amplitud)", "R-BIT", '#29b5e8'),
    ("Rend.Esp.Blue (amplitud)", "R-BLUE", '#FF9F36'),
    ("Red.Esp.Merval (amplitud)", "R-MERV", '#FF3383'),  
    ("Rend.Esp.AL30D (amplitud)", "R-AL30D", '#7D44CF')    
]

metrics_dos = [
    ("Bitcoin (histograma rend.)", "R-BIT", '#29b5e8'),
    ("Blue (histograma rend.)", "R-BLUE", '#FF9F36'),
    ("Merval (histograma rend.)", "R-MERV", '#FF3383'),  
    ("AL30D (histograma rend.)", "R-AL30D", '#7D44CF')    
]

#------------------------- mostrar los graficos de los analisis de metricas --------------------

cols = st.columns(4)
for col, (title, column, color) in zip(cols, metrics):
    total_value = df[column].mean()
    display_metric(col, title, total_value, df_display, column, color, time_frame)

if time_frame == 'Trimestral':
    start_quarter = custom_quarter(start_date)
    end_quarter = custom_quarter(end_date)
    mask = (df_display.index >= start_quarter) & (df_display.index <= end_quarter)
else:
    mask = (df_display.index >= pd.Timestamp(start_date)) & (df_display.index <= pd.Timestamp(end_date))
    df_filtered = df_display.loc[mask]
    

st.subheader("Metrica de rendimiento esperado")
cols = st.columns(4)
for col, (title, column, color) in zip(cols, metrics_uno):    
    total_value = (df[column].max()-df[column].min())*100
    display_metric_rend(col, title, total_value, df_display, column, color, time_frame)

if time_frame == 'Trimestral':
    start_quarter = custom_quarter(start_date)
    end_quarter = custom_quarter(end_date)
    mask = (df_display.index >= start_quarter) & (df_display.index <= end_quarter)
else:
    mask = (df_display.index >= pd.Timestamp(start_date)) & (df_display.index <= pd.Timestamp(end_date))
    df_filtered = df_display.loc[mask]

st.subheader("Histograma de Rendimiento")
cols = st.columns(4)
for col, (title, column, color) in zip(cols, metrics_dos):    
    total_value = df[column].std()*100
    display_metric_hist(col, title, total_value, df_display, column, color, time_frame)

if time_frame == 'Trimestral':
    start_quarter = custom_quarter(start_date)
    end_quarter = custom_quarter(end_date)
    mask = (df_display.index >= start_quarter) & (df_display.index <= end_quarter)
else:
    mask = (df_display.index >= pd.Timestamp(start_date)) & (df_display.index <= pd.Timestamp(end_date))
    df_filtered = df_display.loc[mask]


# DataFrame display- -mostrar los datos basicos de los  calculos
with st.expander('Ver datos (Dataframe)-descagar en formato csv'):
    #st.dataframe(df_filtered)
    st.dataframe(df)    


st.write("---")
with st.container():
  #st.write("---")
  st.write("&copy; - derechos reservados -  2024 -  Walter Gómez - FullStack Developer - Data Science - Business Intelligence")
  #st.write("##")
  left, right = st.columns(2, gap='small', vertical_alignment="bottom")
  with left:
    #st.write('##')
    st.link_button("Mi LinkedIn", "https://www.linkedin.com/in/walter-gomez-fullstack-developer-datascience-businessintelligence-finanzas-python/")
  with right: 
     #st.write('##') 
    st.link_button("Mi Porfolio", "https://walter-portfolio-animado.netlify.app/")
    