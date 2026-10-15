# Paint Pro

Um editor de desenho desktop leve e original, inspirado na simplicidade dos aplicativos clássicos de pintura. Desenvolvido em Python com CustomTkinter e Pillow.

> Este é um projeto independente. Não contém código, recursos visuais ou marcas proprietárias de outros editores.

## Recursos do MVP

- canvas para desenho livre;
- pincel e borracha com espessura ajustável;
- linha, retângulo e elipse com pré-visualização;
- paleta rápida e seletor de cores;
- abertura de PNG, JPG e JPEG;
- exportação para PNG e JPEG;
- desfazer e refazer (até 30 estados);
- zoom de 20% a 300%;
- atalhos de teclado.

## Requisitos

- Python 3.10 ou mais recente
- Windows, macOS ou Linux com suporte a Tk

## Instalação

```bash
git clone https://github.com/theuszim77-ai/paint-pro.git
cd paint-pro
python -m venv .venv
```

Ative o ambiente virtual:

```powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

```bash
# macOS/Linux
source .venv/bin/activate
```

Instale as dependências e execute:

```bash
python -m pip install -r requirements.txt
python app.py
```

## Atalhos

| Atalho | Ação |
|---|---|
| `Ctrl+N` | Novo desenho |
| `Ctrl+O` | Abrir imagem |
| `Ctrl+S` | Salvar imagem |
| `Ctrl+Z` | Desfazer |
| `Ctrl+Y` | Refazer |
| `Ctrl++` / `Ctrl+-` | Zoom |

## Estrutura

```text
paint-pro/
├── app.py
├── requirements.txt
├── README.md
└── .gitignore
```

## Licença

Distribuído sob a licença MIT. Consulte `LICENSE`.
