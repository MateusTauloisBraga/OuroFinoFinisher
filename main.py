import streamlit as st
import gpxpy
import numpy as np
import plotly.graph_objs as go
import pandas as pd
import requests
import tempfile



st.set_page_config(
    page_title="Verificador Finisher Ouro Fino",  # Nome exibido na aba do navegador
    page_icon="logo.jpg",  # Caminho para o ícone da aba (pode ser uma URL ou um arquivo local)
    layout="wide"
)



def download_gpx_from_strava(link):
    """Baixa um arquivo GPX do Strava, dado o link da atividade."""
    try:
        export_link = f"{link}/export_gpx"
        response = requests.get(export_link)
        response.raise_for_status()  # Verifica se houve erro na requisição
        
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".gpx")
        with open(temp_file.name, "wb") as f:
            f.write(response.content)
        
        return temp_file.name
    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao baixar o arquivo GPX: {e}")
        return None

def compare_sequential_gpx(gpx1_file, gpx2_file, max_distance=2):
    """
    Compara arquivos GPX sequencialmente, verificando cada ponto do arquivo oficial
    """
    # Ler arquivos GPX
    gpx1 = gpxpy.parse(gpx1_file)
    gpx2 = gpxpy.parse(gpx2_file)
    
    # Extrair coordenadas sequenciais
    points1 = np.array([
        [p.latitude, p.longitude] 
        for track in gpx1.tracks 
        for segment in track.segments 
        for p in segment.points
    ])
    
    points2 = np.array([
        [p.latitude, p.longitude] 
        for track in gpx2.tracks 
        for segment in track.segments 
        for p in segment.points
    ])
    
    # Flag para marcar pontos verificados
    verified_points = np.zeros(len(points1), dtype=bool)
    
    # Verificar cada ponto do arquivo oficial
    for i, point1 in enumerate(points1):
        # Calcular distâncias para todos os pontos do segundo arquivo
        distances = np.sqrt(np.sum((points2 - point1)**2, axis=1)) * 11100  # conversão para metros
        
        # Verificar se há algum ponto próximo
        if np.min(distances) <= max_distance:
            verified_points[i] = True
        # else: print(np.min(distances))
    
    # Calcular porcentagem de pontos verificados
    verified_percentage = (np.sum(verified_points) / len(points1)) * 100
    
    return verified_percentage, points1, points2, verified_points

def main():

    st.sidebar.image("logo.jpg", width=200)

    st.title('Verificador de Finisher Ouro Fino')
    
    # Carregar arquivo oficial (OuroFino.gpx)
    try:
        with open("OuroFino.gpx", "r") as gpx_file:
            gpx1_file = gpx_file.read()
    except FileNotFoundError:
        st.error("O arquivo 'OuroFino.gpx' não foi encontrado no diretório.")
        return
    
    # Escolha entre upload ou link do Strava
    input_method = st.sidebar.selectbox(
        "Como deseja fornecer o arquivo GPX a comparar?",
        options=["Upload de Arquivo", "Link do Strava"]
    )
    
    if input_method == "Upload de Arquivo":
        gpx2_file = st.sidebar.file_uploader("Arquivo GPX a Comparar", type=['gpx'])
    else:
        strava_link = st.sidebar.text_input("Insira o link da atividade no Strava")
        gpx2_file = None
        if strava_link:
            gpx2_path = download_gpx_from_strava(strava_link)
            if gpx2_path:
                gpx2_file = open(gpx2_path, "r")
    
    # Parâmetro de distância
    max_distance = st.sidebar.slider(
        'Distância máxima para considerar ponto verificado (metros)', 
        min_value=1, max_value=10, value=2
    )
    
    # Botão de comparação
    if st.sidebar.button('Comparar Arquivos'):
        if gpx2_file:
            try:
                # Resetar ponteiro do arquivo
                gpx2_file.seek(0)
                
                # Comparar arquivos
                verified_percentage, points1, points2, verified_points = compare_sequential_gpx(
                    gpx1_file, gpx2_file, max_distance
                )
                
                # Criar DataFrames para visualização
                df1 = pd.DataFrame(points1, columns=['Latitude', 'Longitude'])
                df1['Verificado'] = verified_points
                df1['Arquivo'] = 'GPX Oficial'
                
                df2 = pd.DataFrame(points2, columns=['Latitude', 'Longitude'])
                df2['Verificado'] = False
                df2['Arquivo'] = 'GPX Comparado'
                
                # Visualização com Plotly Graph Objects para mais controle
                fig = go.Figure()

                # Configurar mapa base
                fig.update_layout(
                    mapbox_style="open-street-map",
                    mapbox=dict(
                        center=dict(
                            lat=np.mean(points1[:, 0]),
                            lon=np.mean(points1[:, 1])
                        ),
                        zoom=12
                    )
                )

                # Pontos verificados em verde
                fig.add_trace(go.Scattermapbox(
                    mode="markers",
                    lon=df1[df1['Verificado']]['Longitude'],
                    lat=df1[df1['Verificado']]['Latitude'],
                    marker=dict(size=8, color='green'),
                    name='Pontos Verificados'
                ))

                # Pontos não verificados em vermelho
                fig.add_trace(go.Scattermapbox(
                    mode="markers",
                    lon=df1[~df1['Verificado']]['Longitude'],
                    lat=df1[~df1['Verificado']]['Latitude'],
                    marker=dict(size=8, color='red'),
                    name='Pontos Não Verificados'
                ))

                # Pontos do arquivo comparado em azul
                fig.add_trace(go.Scattermapbox(
                    mode="markers",
                    lon=df2['Longitude'],
                    lat=df2['Latitude'],
                    marker=dict(size=8, color='blue'),
                    name='GPX Comparado'
                ))

                # Configurações finais do layout
                fig.update_layout(
                    title='Dispersão de Pontos dos Arquivos GPX',
                    height=600,
                    margin={"r":0,"t":30,"l":0,"b":0}
                )

                # Mostrar resultados
                st.metric('Pontos Verificados', f'{verified_percentage:.2f}%')
                # st.write(f'Total de pontos no arquivo oficial: {len(points1)}')
                # st.write(f'Total de pontos no arquivo comparado: {len(points2)}')
                
                # Renderizar figura
                st.plotly_chart(fig, use_container_width=True)
                
            except Exception as e:
                st.error(f'Erro: {str(e)}')
        else:
            st.warning('Forneça o arquivo GPX ou link do Strava para comparação.')

if __name__ == '__main__':
    main()
