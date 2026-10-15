# Paint Pro — edição clássica

Editor desktop de desenho em Python, CustomTkinter e Pillow. A interface segue a organização do editor clássico observado: Arquivo, Início, Exibir, faixa de ferramentas, paleta com duas cores, canvas no canto superior esquerdo e barra de zoom.

Implementação independente com código e ícones próprios. Não é um produto da Microsoft. A referência foi inspecionada pela árvore de acessibilidade; a captura da janela falhou no ambiente de desenvolvimento. Esta versão aproxima a organização e as ferramentas, mas **não é uma reprodução visual ou funcional idêntica**.

## Instalar e abrir

Use Python 3.10 ou mais recente, com Tk disponível.

```powershell
git clone https://github.com/theuszim77-ai/paint-pro.git
cd paint-pro
python -m venv .venv
# Windows: não é necessário ativar o ambiente
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe app.py
```

No macOS ou Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py
```

No Linux, instale o pacote Tk da sua distribuição caso ele não acompanhe o Python.

Para atualizar uma cópia clonada, feche o editor e execute `git pull` antes de abri-lo novamente.

## Ferramentas disponíveis

- **Arquivo:** novo, abrir, salvar e salvar como PNG, JPEG ou BMP. Pergunta antes de descartar alterações não salvas.
- **Desenho:** lápis, pincel redondo, caligrafia, marcador, borracha, balde com preenchimento contíguo, conta-gotas, texto e lupa.
- **Formas:** linha, curva quadrática, elipse, retângulo, retângulo arredondado, polígono, triângulos, losango, pentágono, hexágono, quatro setas, estrelas, balões, coração e raio.
- **Estilos:** contorno e preenchimento sólidos opcionais; espessuras de 1, 3, 5 e 8 pixels.
- **Cores:** Cor 1 e Cor 2, paleta, troca de cores e seletor personalizado. Clique com o botão direito desenha com Cor 2. A borracha usa Cor 2.
- **Seleção retangular:** arrastar para selecionar; arrastar dentro da seleção para movê-la; copiar, recortar, colar, apagar e cortar a imagem.
- **Imagem:** redimensionamento em pixels, giro de 90°/180° e inversão horizontal/vertical.
- **Exibir:** zoom de 10% a 800%, ajuste à janela, régua em pixels, grade a partir de 400%, barra de status e tela inteira.
- **Histórico:** desfazer/refazer com até 30 estados, limitado também por um orçamento de memória.

Para desenhar uma curva, arraste a linha inicial, solte e faça um segundo arrasto para definir a curvatura. Para polígonos, clique nos vértices e pressione Enter para fechar. Escape cancela uma operação em andamento e sai da tela inteira.

Escolha a ferramenta antes de desenhar. Passe o mouse sobre os ícones para ver seus nomes. Para usar preenchimento em formas, selecione “Cor sólida” em Preenchimento; o interior usa Cor 2 e o contorno usa a cor do botão de desenho.

## Atalhos

| Atalho | Ação |
|---|---|
| Ctrl+N / Ctrl+O | Novo / abrir |
| Ctrl+S / Ctrl+Shift+S | Salvar / salvar como |
| Ctrl+Z / Ctrl+Y | Desfazer / refazer |
| Ctrl+A | Selecionar tudo |
| Ctrl+C / Ctrl+X / Ctrl+V | Copiar / recortar / colar |
| Delete | Apagar seleção |
| Ctrl++ / Ctrl+- | Zoom |
| Ctrl+roda do mouse | Zoom |
| Roda do mouse | Rolar verticalmente |
| F11 / Escape | Tela inteira / sair e cancelar |
| Enter | Fechar polígono |

## Limitações conhecidas

- Copiar e colar usam uma área de transferência interna ao Paint Pro; não integram imagens de outros aplicativos.
- Texto é inserido em um diálogo e rasterizado; não possui edição posterior como objeto.
- Seleção é retangular, sem seleção livre ou transparência. Transformações atuam na imagem inteira.
- A curva usa um único ponto de controle. Não há todas as texturas de pincel, opções de impressão, inclinação ou integração Paint 3D do aplicativo de referência.
- PNGs transparentes são abertos sobre branco. O documento é RGB, sem camadas.
- Imagens são limitadas a 16 milhões de pixels. O zoom renderiza apenas a região visível.
- Testado no Windows com Python 3.14. Outros sistemas precisam de validação visual.

## Testes

Os testes de interface precisam de uma sessão gráfica ativa:

```powershell
python -m unittest -v
```

Cobrem geometria, histórico, seleção e movimento, recorte, giro, redimensionamento, balde, texto, zoom, salvamento, abertura e transparência.

## Arquivos

`app.py` inicia a aplicação; `classic.py` contém a interface e os gestos; `document.py` contém geometria, documento e histórico; `test_editor.py` contém os testes funcionais.

Licença MIT, conforme [LICENSE](LICENSE).
