from datetime import date

import streamlit as st

from services import equipamentos as svc_equip
from services import locais as svc_locais
from services import ocorrencias as svc_ocorr
from services import motivos_quebra as svc_motivos
from utils.auth import usuario_logado


def render():
    st.markdown('<div class="page-title">Registrar Quebra</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-subtitle">Registre uma ocorrência de quebra de equipamento</div>',
        unsafe_allow_html=True,
    )

    usuario = usuario_logado()
    eh_supervisor = usuario and usuario.get("perfil") == "Supervisor"

    equipamentos = [
        e for e in svc_equip.listar_equipamentos() if e["status"] not in svc_equip.STATUS_FORA_DE_OPERACAO
    ]
    # Supervisor só pode registrar quebra de equipamentos do local dele.
    if eh_supervisor:
        equipamentos = [e for e in equipamentos if e.get("localizacao_atual_id") == usuario.get("local_id")]

    locais_map = svc_locais.mapa_id_para_nome()
    motivos = svc_motivos.nomes_ativos()

    if not equipamentos:
        st.info("Não há equipamentos elegíveis para registro de quebra.")
        return
    if not motivos:
        st.warning("Nenhum motivo de quebra cadastrado. Peça a um administrador para cadastrar em Configurações → Cadastros.")
        return

    codigos_map = {e["codigo"]: e for e in equipamentos}

    # clear_on_submit limpa todos os campos do formulário após o envio,
    # garantindo que a tela fique pronta para um novo registro.
    with st.form("form_quebra", clear_on_submit=True):
        codigo_selecionado = st.selectbox("Equipamento", options=list(codigos_map.keys()))
        equipamento = codigos_map[codigo_selecionado]
        local_nome = locais_map.get(equipamento.get("localizacao_atual_id"), "-")
        st.text_input("Local", value=local_nome, disabled=True)

        tipo_problema = st.selectbox("Tipo de problema", motivos)
        descricao = st.text_area("Descrição", placeholder="Descreva o problema observado")
        data_ocorrencia = st.date_input("Data", value=date.today(), format="DD/MM/YYYY")

        registrar = st.form_submit_button("Registrar quebra")

        if registrar:
            try:
                svc_ocorr.registrar_quebra(
                    equipamento_id=equipamento["id"],
                    local_id=equipamento.get("localizacao_atual_id"),
                    tipo_ocorrencia=tipo_problema,
                    descricao=descricao,
                    data_ocorrencia=data_ocorrencia.isoformat(),
                    responsavel_id=usuario["id"] if usuario else None,
                )
            except Exception as exc:
                # Mensagem genérica pro usuário — nunca expor o erro técnico
                # bruto na tela (mesmo padrão de segurança do resto do
                # sistema). O detalhe real vai pro log do Streamlit Cloud.
                print(f"[quebra.py] Falha ao registrar quebra: {exc}")
                st.error(
                    "Não foi possível registrar a quebra. Tente novamente ou avise um administrador."
                )
            else:
                st.success(
                    f"Quebra registrada para {codigo_selecionado}. Status atualizado para 'Quebrada'."
                )
                st.info(
                    "O sistema verificou automaticamente o déficit da unidade. "
                    "Caso haja déficit, uma substituição pendente foi criada em 'Substituições'."
                )
                st.rerun()
