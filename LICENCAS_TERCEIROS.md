# Licenças de terceiros

O sistema não usa nenhuma imagem ou foto de banco de imagens. Os recursos visuais de terceiros são os
ícones, as fontes e o sistema de design abaixo, todos com licença livre que permite uso comercial.

| Componente | Onde | Licença |
|---|---|---|
| Ícones **Lucide** (desenhos SVG) | `icones.py` | ISC (texto completo abaixo) |
| Fonte **Inter** (usada onde a fonte da Apple não existe) | `static/fonts/` | SIL Open Font License 1.1 (`static/fonts/OFL.txt`) |
| Fonte **Kaushan Script** (só os contornos das letras, convertidos em desenho na escrita da logo) | `static/logo-horizontal.svg`, `static/favicon.svg`, `static/*.png`, `docs/assets/banner.svg` | SIL Open Font License 1.1, que permite usar a fonte em logos e imagens |
| Sistema de design **shadcn/ui** (tokens de cor, raios e receitas dos componentes, adaptados para CSS puro) | `static/style.css`, `static/interface.js` | MIT (texto completo abaixo) |
| **Flask**, **Jinja2**, **MarkupSafe**, **Werkzeug** | dependências Python | BSD-3-Clause |
| **requests** | dependência Python | Apache 2.0 |

A logo é uma **recriação em vetor da logo da Corpu's Academia**, enviada pelo dono do projeto
(fundo vinho listrado, nome em letra cursiva vermelha com contorno dourado). Para usar o arquivo original,
substitua `static/logo.svg` (quadrada), `static/logo-horizontal.svg` (cabeçalho) e `static/logo-email.png` (e-mails).

## shadcn/ui

```
MIT License

Copyright (c) 2023 shadcn

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Lucide

```
ISC License

Copyright (c) for portions of Lucide are held by Cole Bemis 2013-2022 as part of Feather (MIT). All other copyright (c) for Lucide are held by Lucide Contributors 2022.

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
```
