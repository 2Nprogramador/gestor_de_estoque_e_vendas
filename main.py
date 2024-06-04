import streamlit as st
import pandas as pd
from datetime import datetime

# Carregar dados de saída de vendas dos arquivos CSV ou criar um DataFrame vazio
vendas_df = pd.read_csv("vendas.csv") if st.file_uploader("Upload das vendas", type="csv") else pd.DataFrame(
columns=["Código da Venda", "Produto", "Lote", "Quantidade", "Método de Pagamento", "Data da Venda", "Valor Unitário (R$)", "Valor Total (R$)"])


# Carregar dados de entrada de estoque dos arquivos CSV ou criar um DataFrame vazio
registro_estoque_df = pd.read_csv("registro_estoque.csv") if st.file_uploader("Upload do registro de estoque", type="csv") else pd.DataFrame(
    columns=["Produto", "Lote", "Quantidade", "Data de Entrada", "Data de Validade", "Custo (R$)", "Valor de Venda (R$)"])

# DataFrame temporário para armazenar as vendas antes de salvar no DataFrame principal
vendas_temp_df = pd.DataFrame()

# Função para calcular o estoque atualizado
def calcular_estoque_atualizado():
    # Agrupa o registro de estoque pelo nome do produto e soma a quantidade
    estoque_entrada = registro_estoque_df.groupby(["Produto", "Lote"], as_index=False)["Quantidade"].sum()

    # Agrupa as vendas pelo nome do produto e soma a quantidade, com sinal negativo
    vendas = vendas_df.groupby(["Produto", "Lote"], as_index=False)["Quantidade"].sum()
    vendas["Quantidade"] *= -1  # Sinal negativo para subtrair a quantidade vendida

    # Merge dos dados de entrada e vendas
    estoque_atualizado_df = pd.merge(estoque_entrada, vendas, on=["Produto", "Lote"], how="outer", suffixes=("_entrada", "_venda"))

    # Preenche os valores nulos com 0
    estoque_atualizado_df.fillna(0, inplace=True)

    # Calcula o saldo (quantidade de entrada - quantidade de venda)
    estoque_atualizado_df["Saldo"] = estoque_atualizado_df["Quantidade_entrada"] + estoque_atualizado_df["Quantidade_venda"]

    # Adiciona as colunas de data de entrada, data de validade e custo (R$)
    estoque_atualizado_df = pd.merge(estoque_atualizado_df, registro_estoque_df[["Produto", "Lote", "Data de Entrada", "Data de Validade", "Custo (R$)"]],
                                     on=["Produto", "Lote"], how="left")

    # Calcula os custos totais (quantidade * custo)
    estoque_atualizado_df["Custos Totais"] = estoque_atualizado_df["Saldo"] * estoque_atualizado_df["Custo (R$)"]

    # Remove as datas de validade quando o saldo for igual a 0
    estoque_atualizado_df.loc[estoque_atualizado_df["Saldo"] == 0, "Data de Validade"] = ""

    return estoque_atualizado_df

# Função para salvar dados em arquivo CSV
def salvar_dados():
    global vendas_df, registro_estoque_df

    # Atualiza o DataFrame de vendas com os dados temporários
    vendas_df = pd.concat([vendas_df, vendas_temp_df], ignore_index=True)

    # Chama a função para calcular o estoque atualizado
    estoque_atualizado_df = calcular_estoque_atualizado()

    # Salva os DataFrames em arquivos CSV
    registro_estoque_df.to_csv("registro_estoque.csv", index=False)
    vendas_df.to_csv("vendas.csv", index=False)
    estoque_atualizado_df.to_csv("estoque_atualizado.csv", index=False)

# Página de Entrada de Estoque (com aprimoramento)
def entrada_estoque():
    global registro_estoque_df

    st.header("Entrada de Estoque")
    produto = st.text_input("Nome do Produto").upper()  # Converter para letras maiúsculas
    quantidade = st.number_input("Quantidade", min_value=0, step=1)
    data_entrada = datetime.today().date()  # Definindo a data de entrada como a data atual
    data_validade = st.date_input("Data de Validade")
    custo = st.number_input("Custo do Produto (R$)")
    valor_venda = st.number_input("Valor de Venda (R$)")

    # Determinar o próximo número de lote
    if produto in registro_estoque_df["Produto"].values:
        ultimo_lote = registro_estoque_df.loc[registro_estoque_df["Produto"] == produto, "Lote"].str.extract(r'(\d+)').astype(int).max().values[0]
        lote = f"LOTE {ultimo_lote + 1}"
    else:
        lote = "LOTE 1"

    if st.button("Adicionar ao Estoque"):
        novo_produto = pd.DataFrame(
            {"Produto": [produto], "Lote": [lote], "Quantidade": [quantidade], "Data de Entrada": [data_entrada],
             "Data de Validade": [data_validade], "Custo (R$)": [custo], "Valor de Venda (R$)": [valor_venda]})
        registro_estoque_df = pd.concat([registro_estoque_df, novo_produto], ignore_index=True)
        st.success(f"{quantidade} unidades de '{produto}' (Lote: {lote}) adicionadas ao estoque.")
        salvar_dados()

# Página de Saída de Vendas (com a adição da coluna "Código da Venda")
# Página de Saída de Vendas (com a adição da coluna "Código da Venda")
def saida_vendas():
    global registro_estoque_df

    st.header("Saída de Vendas")

    # Calcula o estoque atualizado
    estoque_atualizado_df = calcular_estoque_atualizado()

    # Filtra produtos com saldo maior que zero
    produtos_disponiveis = estoque_atualizado_df[estoque_atualizado_df["Saldo"] > 0]

    # Ordena os produtos pela data de validade mais próxima
    produtos_ordenados = produtos_disponiveis.sort_values(["Produto", "Data de Validade"], ascending=[True, True])

    # Remove as duplicatas, mantendo apenas o produto com a data de validade mais próxima do vencimento
    produtos_ordenados = produtos_ordenados.drop_duplicates(subset=["Produto", "Lote"], keep="last")

    # Seleção dos produtos
    produtos_selecionados = st.multiselect("Selecione os Produtos", produtos_ordenados["Produto"] + " - " + produtos_ordenados["Lote"])
    if not produtos_selecionados:
        st.warning("Por favor, selecione ao menos um produto.")
        return

    # Inicializa o DataFrame temporário de vendas
    vendas_temp_data = []

    # Gera um código único de venda para cada DataFrame temporário
    codigo_venda_temp = datetime.now().strftime("%Y%m%d%H%M%S")  # Captura a data e hora atual

    for produto_lote in produtos_selecionados:
        produto, lote = produto_lote.split(" - ")
        st.subheader(f"Informações do Produto: {produto} (Lote: {lote})")
        quantidade_disponivel = estoque_atualizado_df.loc[(estoque_atualizado_df["Produto"] == produto) & (estoque_atualizado_df["Lote"] == lote), "Saldo"].values[0]
        quantidade = st.number_input(f"Quantidade para {produto} (Lote: {lote})", min_value=1, max_value=int(quantidade_disponivel), step=1, key=f"quantidade_{produto}_{lote}")  # Alterado para int
        metodo_pagamento = st.selectbox("Selecione o Método de Pagamento",
                                        options=["Dinheiro", "Pix", "Cartão de Crédito", "Cartão de Débito"],
                                        key=f"metodo_pagamento_{produto}_{lote}")
        valor_minimo_venda = registro_estoque_df.loc[(registro_estoque_df["Produto"] == produto) & (registro_estoque_df["Lote"] == lote), "Valor de Venda (R$)"].values[0]
        valor_unitario = st.number_input(f"Valor Unitário (R$) para {produto} (Lote: {lote})", min_value=valor_minimo_venda, help=f"Digite o valor de venda mínimo de {valor_minimo_venda} para o produto.", key=f"valor_unitario_{produto}_{lote}")  # Adicionando uma chave única
        valor_total = valor_unitario * quantidade

        # Adiciona a data e hora atual à venda
        data_hora_venda = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        vendas_temp_data.append({"Código da Venda": codigo_venda_temp, "Produto": produto, "Lote": lote, "Quantidade": quantidade, "Método de Pagamento": metodo_pagamento,  "Valor Unitário (R$)": valor_unitario, "Valor Total (R$)": valor_total, "Data da Venda": data_hora_venda})  # Adiciona a data e hora à venda

    global vendas_temp_df
    vendas_temp_df = pd.DataFrame(vendas_temp_data)

    if st.button("Registrar Venda"):
        salvar_dados()
        st.success("Venda registrada com sucesso.")

    # Exibe o DataFrame temporário de vendas
    st.subheader("Produtos Selecionados para Venda:")
    st.dataframe(vendas_temp_df)


# Página de Visualização de Estoque e Vendas (com aprimoramento)
def visualizar_dados():
    st.header("Registro de Estoque")
    st.dataframe(registro_estoque_df)

    st.header("Vendas")
    st.dataframe(vendas_df)

    st.header("Estoque Atualizado")
    estoque_atualizado_df = calcular_estoque_atualizado()
    st.dataframe(estoque_atualizado_df)

    # Calcula o lucro total
    lucro_total = vendas_df["Valor Total (R$)"].sum() - estoque_atualizado_df["Custos Totais"].sum()

    # Calcula o produto mais vendido
    produto_mais_vendido = vendas_df.groupby("Produto")["Quantidade"].sum().idxmax()

    # Calcula o custo em estoque
    custo_em_estoque = registro_estoque_df["Custo (R$)"].sum()

    mostrar_informacoes_negocio = st.sidebar.checkbox("Mostrar Informações do Negócio", value=False)

# Dentro da função visualizar_dados(), envolva as seções de exibição das informações do negócio
# com uma estrutura condicional que verifica o valor de mostrar_informacoes_negocio
    if mostrar_informacoes_negocio:
        st.header("Informações sobre o Negócio")
        st.subheader("Lucro Total")
        st.write(f"O lucro total é: R$ {lucro_total:.2f}")

        st.subheader("Produto Mais Vendido")
        st.write(f"O produto mais vendido é: {produto_mais_vendido}")

        st.subheader("Custo em Estoque")
        st.write(f"O custo em estoque é: R$ {custo_em_estoque:.2f}")

# Barra de Navegação
page = st.sidebar.radio("Selecione uma opção", options=["Entrada de Estoque", "Saída de Vendas", "Visualizar Dados"])

# Exibindo a página selecionada
if page == "Entrada de Estoque":
    entrada_estoque()
elif page == "Saída de Vendas":
    saida_vendas()
else:
    visualizar_dados()
