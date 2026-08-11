# Ponto Funcionario

Aplicacao local para controle de ponto, banco de horas e relatorios mensais.

## Programa desktop

- Para instalar em outro computador, envie `Instalador.Ponto.Funcionarios.exe`.
- A instalacao cria o atalho `Ponto Funcionarios` na Area de Trabalho.
- O atalho abre `PontoFuncionarios.exe` direto, sem janela de CMD.
- O instalador fecha o programa, faz backup do banco, limpa arquivos antigos e preserva os dados.
- Versao atual: `26.08.17`.
- Ela usa o banco local `data/ponto_funcionarios.db`.
- Tambem pode usar banco da empresa em PostgreSQL pelo menu `AUXILIARES > Parametros`.
- Ao abrir, o sistema entra no menu principal com os botoes de funcionario, entrada/saida, consulta, importar ponto e sair.
- A interface principal organiza as ações por Lançamentos, Relatórios e Sistema.
- O menu principal tambem tem o botao `Banco de Horas`, com resumo mensal no modelo da planilha de 2026.
- O Banco de Horas tambem gera PDF anual pronto para impressao.
- A tela de ponto tem impressao em massa: PDF unico com todos os funcionarios, um por pagina, mais PDF do Banco de Horas.
- A tela de edicao de ponto separa Dia, Ocorrencias do dia, Horarios/batidas e Totais calculados para facilitar ajustes manuais.
- A area de Ocorrencias tem botoes rapidos para Dia normal, Marcar falta e Marcar feriado.
- O menu principal mostra claramente se o sistema esta no banco local ou no banco da empresa PostgreSQL.
- A tela `Pendencias do ponto` lista faltas, batidas sem par, debitos altos, creditos altos e observacoes do mes.
- A tela `Conferencia diaria` mostra todos os funcionarios por data, separando OK, presentes, faltantes e problemas.
- O cadastro de funcionarios agora separa dados cadastrais, horarios de calculo e resumo de ponto em abas.
- A importacao do relogio mostra uma janela com dias atualizados, codigos nao encontrados e avisos da leitura.
- A tela `Fechamento mensal` permite travar ou reabrir um mes ja conferido.
- O sistema registra historico basico de importacoes, inclusoes, alteracoes, exclusoes e fechamento de mes.
- O botao `Importar Ponto` abre o TXT exportado pelo relogio e grava as batidas no banco local.
- O botao `Conferencia Individual` mostra os totais do funcionario no mes e gera PDF no formato espelho de ponto para impressao.
- A tela principal replica o fluxo do sistema antigo: menus, consulta/edicao de ponto, inclusao manual, gravar, incluir, cancelar, excluir e sair.
- O menu `AUXILIARES > Buscar Atualizacoes` consulta o manifesto publicado no GitHub.
- O arquivo principal do programa desktop e `desktop_app.py`; o arquivo empacotado para uso e `PontoFuncionarios.exe`.

## Modulos

- Painel: resumo de dias, horas trabalhadas, horas previstas e saldo.
- Importacao: leitura do TXT exportado pelo relogio.
- Funcionarios: cadastro local com ID do relogio, departamento, jornadas e tolerancia.
- Banco de horas: apuracao diaria editavel.
- Relatorios: conferencia individual padronizada, com espelho mensal em PDF pronto para impressao.
- Banco da empresa: opcao PostgreSQL central para mais de um computador editar os mesmos dados.

## Salvamento

- Os dados ficam salvos no computador de cada usuario, no banco SQLite local.
- A pasta padrao da instalacao e `%LOCALAPPDATA%\PontoFuncionarios`.
- O banco local fica em `%LOCALAPPDATA%\PontoFuncionarios\data\ponto_funcionarios.db`.
- Ao reinstalar, o instalador atualiza os arquivos do programa e preserva o banco existente.
- Para levar dados para outro computador, copie o arquivo do banco somente se quiser compartilhar os funcionarios e pontos daquele computador.

## Banco da empresa PostgreSQL

- Instale PostgreSQL no computador principal da empresa.
- Crie o banco `ponto_funcionarios` e o usuario `ponto_app`.
- No computador principal, rode como administrador:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup_postgres_empresa.ps1 -AppPassword "SENHA_DO_APP"
```

- No app, abra `AUXILIARES > Parametros`, selecione `Banco da empresa PostgreSQL`, informe IP/nome do PC, porta `5432`, banco `ponto_funcionarios`, usuario `ponto_app` e senha.
- Use `Testar conexao`, depois `Migrar SQLite atual` para levar os dados locais para o PostgreSQL.
- No computador do Victor, instale o app e configure apenas os mesmos dados de conexao.
- Para backup diario:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\criar_tarefa_backup_postgres.ps1 -Password "SENHA_DO_APP"
```

## Banco SQLite local

- Banco criado em `data/ponto_funcionarios.db`.
- O importador fica em `scripts/import_legacy_db.py`.
- O backup antigo mais recente pode ser importado com:

```powershell
python scripts\import_legacy_db.py --sql "C:\SistemaDescomplicado\Copia\202656localhostponto_biometrico.sql" --db "data\ponto_funcionarios.db"
```

- As tabelas `legacy_*` preservam os dados antigos brutos.
- As tabelas `employees` e `time_entries` deixam os dados prontos para o novo sistema.

## Pontos antigos no app

- Arquivo pronto para restaurar no app: `data/dados_antigos_app.json`.
- Arquivo com dados atuais importados em 06/08/2026: `data/dados_atuais_app.json`.
- No site, clique em `Restaurar` e selecione esse arquivo.
- Ele carrega os funcionarios antigos e as batidas do sistema antigo.
- O arquivo foi gerado com:

```powershell
python scripts\export_sqlite_to_app_state.py --db "data\ponto_funcionarios.db" --out "data\dados_antigos_app.json"
```

## Importacao aceita

- TXT com colunas `ID`, `Nome`, `Depart.`, `Tempo`.
- Layout W20 com `EnNo` e `DateTime`.
- O ID do arquivo e comparado com o `clock_id` do funcionario no banco.
- Ao importar novamente o mesmo funcionario/dia, o sistema atualiza o registro existente em vez de duplicar.

## Banco de horas

- As batidas sao agrupadas por funcionario e data.
- O calculo soma pares: primeira com segunda, terceira com quarta.
- O saldo e `trabalhado - previsto`.
- A tolerancia zera pequenas diferencas dentro do limite configurado.
- Dias incompletos ou com quantidade impar de batidas recebem alerta.
