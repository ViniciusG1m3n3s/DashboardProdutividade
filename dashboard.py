import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime
from diario import diario  # Importa o diário de bordo

# Função para carregar os dados do Excel do usuário logado
def load_data(usuario):
    excel_file = f'dados_acumulados_{usuario}.xlsx'  # Nome do arquivo específico do usuário
    if os.path.exists(excel_file):
        df_total = pd.read_excel(excel_file, engine='openpyxl')
    else:
        df_total = pd.DataFrame(columns=['Protocolo', 'Usuário', 'Status', 'Tempo de Análise', 'Próximo'])
    return df_total

# Função para salvar os dados no Excel do usuário logado
def save_data(df, usuario):
    excel_file = f'dados_acumulados_{usuario}.xlsx'  # Nome do arquivo específico do usuário
    df['Tempo de Análise'] = df['Tempo de Análise'].astype(str)
    with pd.ExcelWriter(excel_file, engine='openpyxl', mode='w') as writer:
        df.to_excel(writer, index=False)

# Função para garantir que a coluna 'Tempo de Análise' esteja no formato timedelta temporariamente para cálculos
def convert_to_timedelta_for_calculations(df):
    df['Tempo de Análise'] = pd.to_timedelta(df['Tempo de Análise'], errors='coerce')
    return df

# Função para formatar o timedelta em minutos e segundos
def format_timedelta(td):
    if pd.isnull(td):
        return "0 min"
    total_seconds = int(td.total_seconds())
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes} min {seconds} sec"

# Função para garantir que a coluna 'Próximo' esteja no formato de datetime
def convert_to_datetime_for_calculations(df):
    df['Próximo'] = pd.to_datetime(df['Próximo'], format='%d/%m/%Y %H:%M:%S', errors='coerce')
    return df

# Função para obter pontos de atenção
def get_points_of_attention(df):
    pontos_de_atencao = df[df['Tempo de Análise'] > pd.Timedelta(minutes=2)].copy()
    pontos_de_atencao['Protocolo'] = pontos_de_atencao['Protocolo'].astype(str).str.replace(',', '', regex=False)
    return pontos_de_atencao

# Função principal da dashboard
def dashboard():
    st.title("Dashboard de Produtividade")
    
    # Carregar dados acumulados do arquivo Excel do usuário logado
    usuario_logado = st.session_state.usuario_logado  # Obtém o usuário logado
    df_total = load_data(usuario_logado)  # Carrega dados específicos do usuário

    st.sidebar.image("https://finchsolucoes.com.br/img/eb28739f-bef7-4366-9a17-6d629cf5e0d9.png", width=100)
    st.sidebar.text('')

    # Sidebar para navegação
    st.sidebar.header("Navegação")
    opcao_selecionada = st.sidebar.selectbox("Escolha uma visão", ["Visão Geral", "Métricas Individuais", "Diário de Bordo"])

    # Upload de planilha na sidebar
    uploaded_file = st.sidebar.file_uploader("Carregar nova planilha", type=["xlsx"])

    if uploaded_file is not None:
        df_new = pd.read_excel(uploaded_file)
        df_total = pd.concat([df_total, df_new], ignore_index=True)
        save_data(df_total, usuario_logado)  # Atualiza a planilha específica do usuário
        st.sidebar.success(f'Arquivo "{uploaded_file.name}" carregado e processado com sucesso!')

    # Converte para timedelta e datetime apenas para operações temporárias
    df_total = convert_to_timedelta_for_calculations(df_total)
    df_total = convert_to_datetime_for_calculations(df_total)

    custom_colors = ['#ff571c', '#7f2b0e', '#4c1908']

    # Função para calcular TMO por dia
    def calcular_tmo_por_dia(df):
        df['Dia'] = df['Próximo'].dt.date
        df_finalizados = df[df['Status'] == 'FINALIZADO'].copy()
        df_tmo = df_finalizados.groupby('Dia').agg(
            Tempo_Total=('Tempo de Análise', 'sum'),
            Total_Protocolos=('Tempo de Análise', 'count')
        ).reset_index()
        df_tmo['TMO'] = (df_tmo['Tempo_Total'] / pd.Timedelta(minutes=1)) / df_tmo['Total_Protocolos']
        return df_tmo[['Dia', 'TMO']]

    # Verifica qual opção foi escolhida no dropdown
    if opcao_selecionada == "Visão Geral":
        st.header("Visão Geral")

        # Adiciona filtros de datas 
        min_date = df_total['Próximo'].min().date() if not df_total.empty else datetime.today().date()
        max_date = df_total['Próximo'].max().date() if not df_total.empty else datetime.today().date()

        col1, col2 = st.columns(2)
        with col1:
            data_inicial = st.date_input("Data Inicial", min_date)
        with col2:
            data_final = st.date_input("Data Final", max_date)

        if data_inicial > data_final:
            st.sidebar.error("A data inicial não pode ser posterior à data final!")

        df_total = df_total[(df_total['Próximo'].dt.date >= data_inicial) & (df_total['Próximo'].dt.date <= data_final)]

        total_finalizados = len(df_total[df_total['Status'] == 'FINALIZADO'])
        total_reclass = len(df_total[df_total['Status'] == 'RECLASSIFICADO'])
        total_andamento = len(df_total[df_total['Status'] == 'ANDAMENTO_PRE'])
        tempo_medio = df_total[df_total['Status'] == 'FINALIZADO']['Tempo de Análise'].mean()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total de Cadastros", total_finalizados)
        col2.metric("Reclassificações", total_reclass)
        col3.metric("Andamentos", total_andamento)
        col4.metric("Tempo Médio por Cadastro", format_timedelta(tempo_medio))

        # Gráfico de pizza para o status
        st.subheader("Distribuição de Status")
        fig_status = px.pie(
            names=['Finalizado', 'Reclassificado', 'Andamento'],
            values=[total_finalizados, total_reclass, total_andamento],
            title='Distribuição de Status',
            color_discrete_sequence=custom_colors
        )
        st.plotly_chart(fig_status)

        # Gráfico de TMO por dia
        st.subheader("Tempo Médio de Operação (TMO) por Dia")
        df_tmo = calcular_tmo_por_dia(df_total)
        fig_tmo = px.bar(
            df_tmo,
            x='Dia',
            y='TMO',
            title='TMO por Dia (em minutos)',
            labels={'TMO': 'TMO (min)', 'Dia': 'Data'},
            color_discrete_sequence=custom_colors
        )
        st.plotly_chart(fig_tmo)

        # Gráfico de ranking dinâmico
        st.subheader("Ranking Dinâmico")
        df_ranking = df_total.groupby('Usuário').agg(
            Andamento=('Status', lambda x: x[x == 'ANDAMENTO_PRE'].count()),
            Finalizado=('Status', lambda x: x[x == 'FINALIZADO'].count()),
            Reclassificado=('Status', lambda x: x[x == 'RECLASSIFICADO'].count())
        ).reset_index()
        df_ranking['Total'] = df_ranking['Andamento'] + df_ranking['Finalizado'] + df_ranking['Reclassificado']
        df_ranking = df_ranking.sort_values(by='Total', ascending=False).reset_index(drop=True)
        df_ranking.index += 1
        df_ranking.index.name = 'Rank'
        df_ranking = df_ranking.rename(columns={'Usuário': 'Usuário', 'Andamento': 'Andamento', 'Finalizado': 'Finalizado', 'Reclassificado': 'Reclassificado'})
        st.dataframe(df_ranking.style.format({'Andamento': '{:.0f}', 'Finalizado': '{:.0f}', 'Reclassificado': '{:.0f}'}), width=1000)

    elif opcao_selecionada == "Diário de Bordo":
        diario()

    elif opcao_selecionada == "Métricas Individuais":
        st.header("Análise por Analista")
        # Adiciona filtros de datas 
        st.subheader("Filtro por Data")
        min_date = df_total['Próximo'].min().date() if not df_total.empty else datetime.today().date()
        max_date = df_total['Próximo'].max().date() if not df_total.empty else datetime.today().date()

        col1, col2 = st.columns(2)
        with col1:
            data_inicial = st.date_input("Data Inicial", min_date)
        with col2:
            data_final = st.date_input("Data Final", max_date)

        if data_inicial > data_final:
            st.error("A data inicial não pode ser posterior à data final!")

        df_total = df_total[(df_total['Próximo'].dt.date >= data_inicial) & (df_total['Próximo'].dt.date <= data_final)]
        analista_selecionado = st.selectbox('Selecione o analista', df_total['Usuário'].unique())
        df_analista = df_total[df_total['Usuário'] == analista_selecionado].copy()

        total_finalizados_analista = len(df_analista[df_analista['Status'] == 'FINALIZADO'])
        total_reclass_analista = len(df_analista[df_analista['Status'] == 'RECLASSIFICADO'])
        total_andamento_analista = len(df_analista[df_analista['Status'] == 'ANDAMENTO_PRE'])
        tempo_medio_analista = df_analista[df_analista['Status'] == 'FINALIZADO']['Tempo de Análise'].mean()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total de Cadastros", total_finalizados_analista)
        col2.metric("Reclassificações", total_reclass_analista)
        col3.metric("Andamentos", total_andamento_analista)
        col4.metric("Tempo Médio por Cadastro", format_timedelta(tempo_medio_analista))

        st.subheader(f"Carteiras Cadastradas por {analista_selecionado}")
        carteiras_analista = pd.DataFrame(df_analista['Carteira'].dropna().unique(), columns=['Carteiras'])
        st.write(carteiras_analista.to_html(index=False, justify='left', border=0), unsafe_allow_html=True)
        st.markdown("<style>table {width: 100%;}</style>", unsafe_allow_html=True)

        # Gráfico de pizza para o status do analista selecionado
        st.subheader(f"Distribuição de Status de {analista_selecionado}")
        fig_status_analista = px.pie(
            names=['Finalizado', 'Reclassificado', 'Andamento'],
            values=[total_finalizados_analista, total_reclass_analista, total_andamento_analista],
            title=f'Distribuição de Status - {analista_selecionado}',
            color_discrete_sequence=custom_colors
        )
        st.plotly_chart(fig_status_analista)

        # TMO por dia do analista
        st.subheader(f"Tempo Médio de Operacional (TMO) por Dia - {analista_selecionado}")
        df_tmo_analista = calcular_tmo_por_dia(df_analista)
        fig_tmo_analista = px.bar(
            df_tmo_analista,
            x='Dia',
            y='TMO',
            title=f'TMO por Dia de {analista_selecionado} (em minutos)',
            hover_name='Dia',
            hover_data=['TMO'],
            color_discrete_sequence=custom_colors
        )
        st.plotly_chart(fig_tmo_analista)

        # Tabela de pontos de atenção
        st.subheader("Pontos de Atenção")
        pontos_de_atencao_analista = get_points_of_attention(df_analista)
        if not pontos_de_atencao_analista.empty:
            st.write(pontos_de_atencao_analista[['Protocolo', 'Tempo de Análise', 'Próximo']].assign(
                **{'Tempo de Análise': pontos_de_atencao_analista['Tempo de Análise'].apply(format_timedelta)}
            ).to_html(index=False, justify='left'), unsafe_allow_html=True)
        else:
            st.write("Nenhum ponto de atenção identificado para este analista.")

    # Botão para salvar a planilha atualizada
    if st.sidebar.button("Salvar Dados"):
        save_data(df_total, usuario_logado)  # Salva dados específicos do usuário
        st.sidebar.success("Dados salvos com sucesso!")

# Para que a função dashboard seja chamada no arquivo principal
if __name__ == "__main__":
    dashboard()
