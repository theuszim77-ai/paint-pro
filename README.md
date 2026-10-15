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

`app.py` inicia a aplicação; `classic.py` contém a interface e os gestos; `document.py` contém geometria, documento e histórico. `native_backend.py` liga o editor ao módulo C++ em `native/`. `scripts/` contém ferramentas JavaScript. Os arquivos `test_*.py` contêm testes funcionais.

## Python + C++ + JavaScript

O aplicativo continua sendo desktop. Python cuida da interface e dos documentos; C++17 oferece uma implementação nativa do balde de tinta; JavaScript/Node automatiza execução, testes, compilação e pacote de código-fonte. As linguagens têm funções separadas e nenhuma dependência npm é necessária.

### C++ opcional

O editor procura a biblioteca compilada em `native/bin/`. Se ela não estiver disponível ou a operação nativa falhar, usa Pillow automaticamente. A implementação nativa trabalha em uma cópia da imagem, valida dimensões e não deixa exceções atravessarem a fronteira entre C++ e Python.

Para compilar, instale CMake e um compilador C++17 (Visual Studio Build Tools no Windows, GCC/Clang no Linux ou Xcode Command Line Tools no macOS):

```bash
cmake -S native -B build/native -DCMAKE_BUILD_TYPE=Release
cmake --build build/native --config Release
python -m unittest -v
```

A biblioteca é específica do sistema e da arquitetura do Python. Compile no próprio computador. `PAINT_PRO_DISABLE_NATIVE=1` força Pillow; `PAINT_PRO_REQUIRE_NATIVE=1` faz os testes falharem se o C++ não carregar. Sem essa exigência, o teste de comparação nativa é ignorado quando a biblioteca não existe. Não é necessário compilar para abrir o aplicativo.

### Ferramentas JavaScript

Com Node.js 20 ou mais recente:

```bash
node scripts/dev.mjs doctor
node scripts/dev.mjs start
node scripts/dev.mjs test
node scripts/dev.mjs build-native
node scripts/dev.mjs package
```

`doctor` verifica as dependências e informa se o motor é C++17 ou Pillow. `test` executa os testes JavaScript e Python. `package` gera `dist/paint-pro-source.zip` contendo apenas os fontes permitidos; não inclui imagens do usuário, ambientes virtuais, credenciais ou bibliotecas compiladas. O pacote exige Python e dependências instalados para executar; não é um executável autônomo.

Os mesmos comandos estão disponíveis como `npm start`, `npm test`, `npm run doctor`, `npm run build:native` e `npm run package`, caso npm esteja instalado. A variável `PAINT_PRO_PYTHON` permite escolher o caminho do Python do ambiente virtual.

O fluxo `.github/workflows/ci.yml` verifica a versão Python/Pillow e a versão C++ no Linux, além das ferramentas JavaScript, a cada push ou pull request.

Licença MIT, conforme [LICENSE](LICENSE).
