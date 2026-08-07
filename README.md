# Ponto Funcionario

Aplicacao local para controle de ponto, banco de horas e relatorios mensais.

## Programa desktop

- Abra `Abrir_Ponto_Desktop.bat` para usar a versao de Windows.
- O atalho da Area de Trabalho usa `Abrir_Ponto_Desktop.vbs` para abrir sem janela de CMD.
- Versao atual: `26.8`.
- Ela usa o banco local `data/ponto_funcionarios.db`.
- A tela principal replica o fluxo do sistema antigo: menus, consulta/edicao de ponto, inclusao manual, gravar, incluir, cancelar, excluir e sair.
- O arquivo principal do programa desktop e `desktop_app.py`.

## Modulos

- Painel: resumo de dias, horas trabalhadas, horas previstas e saldo.
- Importacao: leitura do TXT exportado pelo relogio.
- Funcionarios: cadastro local com ID do relogio, departamento, jornadas e tolerancia.
- Banco de horas: apuracao diaria editavel.
- Relatorios: resumo mensal por funcionario com impressao.

## Salvamento

- Os dados ficam salvos no navegador de cada computador.
- O sistema salva importacao, funcionarios, jornadas, filtros e ajustes manuais.
- Use `Backup` para baixar um JSON.
- Use `Restaurar` para levar os dados para outro computador.
- Use `Limpar` para apagar os dados salvos naquele computador.

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

## Banco de horas

- As batidas sao agrupadas por funcionario e data.
- O calculo soma pares: primeira com segunda, terceira com quarta.
- O saldo e `trabalhado - previsto`.
- A tolerancia zera pequenas diferencas dentro do limite configurado.
- Dias incompletos ou com quantidade impar de batidas recebem alerta.
