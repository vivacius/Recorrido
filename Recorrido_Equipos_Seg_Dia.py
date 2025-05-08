import pandas as pd
import folium
from folium import Marker, Icon
from folium.plugins import MarkerCluster, AntPath
from streamlit_folium import st_folium
import streamlit as st
from geopy.distance import geodesic
from io import StringIO

# Cargar datos desde el archivo subido
def cargar_datos(file):
    df = pd.read_csv(file, delimiter=';')
    df['Fecha/Hora'] = pd.to_datetime(df['Fecha/Hora'], format='%d/%m/%Y %H:%M:%S')
    df = df.dropna(subset=['Latitud', 'Longitud'])
    df['Grupo Operacion'] = df['Grupo Operacion'].astype(str).str.strip().str.upper()
    return df

st.title("Visualización de Recorridos de Equipos")

# Subir archivo
archivo_subido = st.file_uploader("Sube el archivo de datos (formato .txt)", type=["txt"])

if archivo_subido is not None:
    # Cargar y procesar datos
    df = cargar_datos(archivo_subido)

    # --- TABLA RESUMEN POR GRUPO EQUIPO / FRENTE ---
    st.subheader("Resumen de Inicio de Labores por Grupo Equipo / Frente")

    # Filtrar y calcular la hora de inicio de labor para los equipos
    def obtener_hora_inicio_grupo(equipo):
        # Filtrar por equipo y velocidad mayor a 7 para calcular la hora de inicio
        datos_equipo = df[df['Equipo'] == equipo]
        datos_labor = datos_equipo[datos_equipo['Velocidad'] > 7]

        if not datos_labor.empty:
            return datos_labor['Fecha/Hora'].iloc[0]  # Hora de inicio
        else:
            return "Equipo sin inicio de labor"  # Si no hay datos de labor con velocidad > 7

    # Obtener resumen de hora de inicio por equipo y grupo
    inicio_por_equipo = []
    for grupo, equipo_data in df.groupby('Grupo Equipo/Frente'):
        for equipo in equipo_data['Equipo'].unique():
            hora_inicio = obtener_hora_inicio_grupo(equipo)
            inicio_por_equipo.append({'Grupo Equipo/Frente': grupo, 'Equipo': equipo, 'Hora Inicio': hora_inicio})

    inicio_por_equipo_df = pd.DataFrame(inicio_por_equipo)
    st.dataframe(inicio_por_equipo_df)

    # Selección del equipo
    equipos_disponibles = df['Equipo'].unique()
    equipo_seleccionado = st.selectbox("Selecciona un equipo", equipos_disponibles)

    # Filtrar y ordenar datos del equipo
    datos_equipo = df[df['Equipo'] == equipo_seleccionado].sort_values(by='Fecha/Hora')

    if not datos_equipo.empty:
        # Crear mapa centrado
        centro = [datos_equipo['Latitud'].mean(), datos_equipo['Longitud'].mean()]
        mapa = folium.Map(location=centro, zoom_start=13)

        # Línea animada con dirección (AntPath)
        puntos_linea = [[row['Latitud'], row['Longitud']] for _, row in datos_equipo.iterrows()]
        if len(puntos_linea) >= 2:
            AntPath(locations=puntos_linea, color='green', weight=4, delay=800).add_to(mapa)
        else:
            st.warning("No hay suficientes puntos para trazar la ruta.")

        # Crear un cluster para las paradas
        cluster = MarkerCluster().add_to(mapa)

        # Variables para las paradas
        paradas = []

        # Filtrar paradas (PERDIDA o MANTENIMIENTO)
        for _, row in datos_equipo.iterrows():
            estado = row['Grupo Operacion']
            if estado in ['PERDIDA', 'MANTENIMIENTO']:
                paradas.append([row['Latitud'], row['Longitud']])

        # Solo agregar un marcador para el cluster con el número de paradas
        if paradas:
            Marker(
                location=[datos_equipo['Latitud'].mean(), datos_equipo['Longitud'].mean()],
                popup=f"Total de Paradas: {len(paradas)}",
                icon=Icon(color='red', icon='cloud', prefix='fa')
            ).add_to(cluster)

        # Calcular hora de inicio y fin de labores (velocidad > 7)
        datos_labor = datos_equipo[datos_equipo['Velocidad'] > 7]
        if not datos_labor.empty:
            inicio = datos_labor['Fecha/Hora'].iloc[0]
            fin = datos_labor['Fecha/Hora'].iloc[-1]
            duracion = fin - inicio

            puntos_labor = list(zip(datos_labor['Latitud'], datos_labor['Longitud']))
            distancia = sum(geodesic(p1, p2).meters for p1, p2 in zip(puntos_labor[:-1], puntos_labor[1:]))

            # Marcadores para inicio y fin de labores
            Marker(
                location=[datos_labor['Latitud'].iloc[0], datos_labor['Longitud'].iloc[0]],
                icon=Icon(color='green', icon='play')
            ).add_to(mapa)
            Marker(
                location=[datos_labor['Latitud'].iloc[-1], datos_labor['Longitud'].iloc[-1]],
                icon=Icon(color='red', icon='stop')
            ).add_to(mapa)

            # Estadísticas
            st.subheader("Estadísticas de Labor")
            st.write(f"**Hora de inicio:** {inicio.strftime('%d/%m/%Y %H:%M:%S')}")
            st.write(f"**Hora de fin:** {fin.strftime('%d/%m/%Y %H:%M:%S')}")
            st.write(f"**Duración estimada:** {duracion}")
            st.write(f"**Distancia recorrida:** {distancia / 1000:.2f} km")
        else:
            st.warning("No se encontró velocidad > 7 km/h para este equipo.")

        # Mostrar el mapa
        st_folium(mapa, width=700, height=500)
    else:
        st.error("No hay datos para este equipo.")
else:
    st.warning("Por favor, sube el archivo para visualizar los datos.")

#python -m streamlit run c:/Users/sacor/Downloads/Recorrido_Equipos_Seg_Dia.py
