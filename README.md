# Ponto Funcionario

Aplicacao local para controle de ponto, banco de horas e relatorios mensais.

## Programa desktop

- Para instalar em outro computador, envie `Instalador.Ponto.Funcionarios.exe`.
- A instalacao cria o atalho `Ponto Funcionarios` na Area de Trabalho.
- O atalho abre `PontoFuncionarios.exe` direto, sem janela de CMD.
- Versao atual: `26.08.5`.
- Ela usa o banco local `data/ponto_funcionarios.db`.
- Ao abrir, o sistema entra no menu principal com os botoes de funcionario, entrada/saida, consulta, importar ponto e sair.
- O menu principal tambem tem o botao `Banco de Horas`, com resumo mensal no modelo da planilha de 2026.
- O botao `Importar Ponto` abre o TXT exportado pelo relogio e grava as batidas no banco local.
- O botao `Conferencia Individual` mostra os totais do funcionario no mes, seguindo a soma usada pelo sistema antigo.
- A tela principal replica o fluxo do sistema antigo: menus, consulta/edicao de ponto, inclusao manual, gravar, incluir, cancelar, excluir e sair.
- O menu `AUXILIARES > Buscar Atualizacoes` consulta o manifesto publicado no GitHub.
- O arquivo principal do programa desktop e `desktop_app.py`; o arquivo empacotado para uso e `PontoFuncionarios.exe`.

## Modulos

- Painel: resumo de dias, horas trabalhadas, horas previstas e saldo.
- Importacao: leitura do TXT exportado pelo relogio.
- Funcionarios: cadastro local com ID do relogio, departamento, jornadas e tolerancia.
- Banco de horas: apuracao diaria editavel.
- Relatorios: resumo mensal por funcionario com impressao.

## Salvamento

- Os dados ficam salvos no computador de cada usuario, no banco SQLite local.
- A pasta padrao da instalacao e `%LOCALAPPDATA%\PontoFuncionarios`.
- O banco local fica em `%LOCALAPPDATA%\PontoFuncionarios\data\ponto_funcionarios.db`.
- Ao reinstalar, o instalador atualiza os arquivos do programa e preserva o banco existente.
- Para levar dados para outro computador, copie o arquivo do banco somente se quiser compartilhar os funcionarios e pontos daquele computador.

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
