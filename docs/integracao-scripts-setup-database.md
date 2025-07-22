# Integração dos Scripts de Setup com Inicialização do Banco

## Resumo das Mudanças

O script `setup_complete_database.py` foi **completamente reescrito** para implementar uma **verificação granular** do banco de dados que analisa cada tabela individualmente e executa apenas os scripts necessários para popular as tabelas vazias.

### Scripts Integrados

1. **`create_tables.py`** - Cria todas as tabelas via SQLAlchemy (inclui SAPLocation e PMM_2)
2. **`populate_database.py`** - Popula dados básicos (equipamentos, manutenções, falhas)
3. **`import_localidades_sap.py`** - Importa localidades SAP do arquivo CSV
4. **`correlate_equipment_locations.py`** - Correlaciona equipamentos com localidades
5. **`populate_pmm_2.py`** - Popula dados PMM_2 (Plano de Manutenção Maestro)
6. **`check_database.py`** - Verifica se o banco foi populado com sucesso

### Ordem de Execução

A inicialização segue esta sequência:

1. **Verificação inicial** - Checa se o banco precisa ser configurado
2. **Criação de tabelas** - Cria todas as tabelas necessárias
3. **População básica** - Popula equipamentos, manutenções e falhas
4. **Importação de localidades** - Importa dados do CSV de localidades SAP
5. **Correlação** - Correlaciona equipamentos existentes com localidades
6. **População PMM_2** - Popula dados do Plano de Manutenção Maestro
7. **Verificação final** - Confirma que tudo foi populado corretamente

### Tratamento de Erros

- **Críticos**: Falhas na criação de tabelas ou população básica abortam o processo
- **Não-críticos**: Falhas na importação de localidades ou correlação não abortam o processo, apenas geram avisos

### Configuração do Docker

O script é executado automaticamente pelo `entrypoint.sh` do Docker:

```bash
# Executa configuração completa do banco
python3 scripts/setup/setup_complete_database.py
```

### Arquivos Modificados

- `scripts/setup/setup_complete_database.py` - Adicionada execução dos novos scripts
- `tarefas/tarefas-integracao-localidades-sap.md` - Atualizada para marcar integração como concluída

### Benefícios

1. **Automação completa** - Inicialização sem intervenção manual
2. **Verificação granular** - Analisa cada tabela individualmente
3. **Eficiência máxima** - Executa apenas os scripts necessários
4. **Recuperação inteligente** - Não refaz o que já está completo
5. **Ordem garantida** - Scripts executados na sequência correta
6. **Robustez** - Tratamento adequado de erros críticos e não-críticos
7. **Visibilidade** - Logs detalhados de cada etapa com status por tabela
8. **Flexibilidade** - Pula etapas desnecessárias automaticamente

### Como Usar

Para inicializar o banco completo:

```bash
# Via Docker
docker-compose up

# Ou manualmente
python scripts/setup/setup_complete_database.py
```

O script detecta automaticamente se o banco precisa ser configurado e executa apenas as etapas necessárias. 