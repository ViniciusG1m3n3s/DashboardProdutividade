import streamlit as st
import os
from datetime import datetime

# Função para carregar as anotações do diário de bordo do usuário a partir de um arquivo .txt
def load_diario(usuario):
    file_path = f'diario_bordo_{usuario}.txt'
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            anotacoes = file.readlines()
    else:
        anotacoes = []
    return anotacoes

# Função para salvar uma nova anotação no arquivo .txt do usuário
def save_anotacao(usuario, anotacao):
    file_path = f'diario_bordo_{usuario}.txt'
    with open(file_path, 'a', encoding='utf-8') as file:
        file.write(f"{datetime.now().strftime('%d/%m/%Y %H:%M')} - {anotacao}\n")

# Função para exibir e adicionar anotações no diário de bordo
def diario():
    usuario_logado = st.session_state.usuario_logado  # Obtém o usuário logado

    st.header("Diário de Bordo")

    # Carregar anotações anteriores
    anotacoes = load_diario(usuario_logado)

    # Área para adicionar uma nova anotação
    st.subheader("Nova Anotação")
    nova_anotacao = st.text_area("Escreva sua anotação aqui...")

    if st.button("Salvar Anotação"):
        if nova_anotacao.strip():
            save_anotacao(usuario_logado, nova_anotacao)
            st.success("Anotação salva com sucesso!")
            st.rerun()  # Recarrega a página para exibir a nova anotação
        else:
            st.error("A anotação não pode estar vazia!")


    # Exibir anotações anteriores
    if anotacoes:
        st.subheader("Anotações anteriores")
        for anotacao in anotacoes:
            st.write(anotacao.strip())  # Exibe cada anotação
    else:
        st.info("Nenhuma anotação encontrada.")

