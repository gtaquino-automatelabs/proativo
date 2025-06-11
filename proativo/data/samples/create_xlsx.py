import openpyxl
from openpyxl import Workbook
from datetime import datetime

# Criar workbook
wb = Workbook()

# Planilha de histórico de falhas
ws = wb.active
ws.title = 'Historico_Falhas'

# Headers
headers = ['id', 'equipment_id', 'data_falha', 'tipo_falha', 'severidade', 'tempo_parada_horas', 'causa_raiz', 'acao_tomada', 'custo_reparo', 'impacto_operacional']
ws.append(headers)

# Dados
falhas = [
    ['FLH-0001', 'TR-0001', '2023-07-15', 'SOBREAQUECIMENTO', 'ALTA', 12, 'Falha no sistema de refrigeração', 'Substituição de bombas de óleo', 25000.00, 'Transferência de carga para TR-0002'],
    ['FLH-0002', 'DJ-0001', '2023-09-22', 'FALHA_MECANICA', 'MEDIA', 4, 'Desgaste de contatos', 'Substituição de contatos principais', 8500.00, 'Manobra via by-pass'],
    ['FLH-0003', 'CP-0001', '2023-11-10', 'CURTO_CIRCUITO', 'CRITICA', 8, 'Falha de isolamento interno', 'Substituição de unidades danificadas', 15000.00, 'Redução de compensação reativa'],
    ['FLH-0004', 'CH-0001', '2024-01-08', 'TRAVAMENTO', 'BAIXA', 2, 'Falta de lubrificação', 'Lubrificação e ajuste mecânico', 2500.00, 'Operação manual temporária'],
    ['FLH-0005', 'PR-0002', '2023-12-20', 'DESCARGA_PARCIAL', 'ALTA', 6, 'Degradação do elemento ativo', 'Substituição completa do para-raios', 12000.00, 'Redução de confiabilidade da proteção']
]

for falha in falhas:
    ws.append(falha)

# Adicionar segunda planilha com indicadores
ws2 = wb.create_sheet('Indicadores_Confiabilidade')
headers2 = ['equipment_id', 'mtbf_horas', 'mttr_horas', 'disponibilidade_percent', 'falhas_ultimo_ano', 'custo_manutencao_anual']
ws2.append(headers2)

indicadores = [
    ['TR-0001', 8760, 24, 99.73, 1, 45000.00],
    ['DJ-0001', 17520, 6, 99.97, 1, 12000.00],
    ['TR-0002', 26280, 20, 99.92, 0, 25000.00],
    ['CP-0001', 8760, 16, 99.82, 1, 20000.00],
    ['CH-0001', 17520, 4, 99.98, 1, 5000.00]
]

for ind in indicadores:
    ws2.append(ind)

# Salvar arquivo
wb.save('indicadores_manutencao.xlsx')
print('Arquivo XLSX criado com sucesso!')