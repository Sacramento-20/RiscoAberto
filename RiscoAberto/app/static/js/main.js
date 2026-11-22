// ==========================================
// 1. INICIALIZAÇÃO DO MAPA
// ==========================================

const map = L.map("map").setView(
    [-19.9167, -43.9345],
    12
);

L.tileLayer(
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap contributors"
    }
).addTo(map);

// ==========================================
// CAMADAS GEOGRÁFICAS
// ==========================================

// Camada dos bairros selecionados
map.createPane("bairrosPane");
map.getPane("bairrosPane").style.zIndex = 420;

// Camada das áreas de inundação
map.createPane("inundacaoPane");

// ==========================================
// CAMADA DE TODOS OS BAIRROS
// ==========================================

const camadaTodosBairros = L.geoJSON(null, {

    pane: "bairrosPane",

    style: function() {
        return {
            fillColor: "#2b8cbe",
            color: "#045a8d",
            weight: 1,
            opacity: 1,
            fillOpacity: 0.15
        };
    },

    onEachFeature: function(feature, layer) {

        layer.bindTooltip(
            feature.properties.ROTULO_CONTROLADO || feature.properties.NOME || "Bairro"
        );

        layer.on("click", function() {
            selecionarBairro(feature);
        });

    }

});

// Camada independente para destacar o bairro ou conjunto de bairros pesquisados
const camadaSelecionada = L.geoJSON(null, {

    pane: "bairrosPane",

    style: function() {
        return {
            fillColor: "#2b8cbe",
            color: "#045a8d",
            weight: 2.5,
            opacity: 1,
            fillOpacity: 0.45
        };
    },

    onEachFeature: function(feature, layer) {
        layer.bindTooltip(
            feature.properties.ROTULO_CONTROLADO || feature.properties.NOME || "Bairro"
        );

        layer.on("click", function() {
            selecionarBairro(feature);
        });
    }

});


map.getPane("inundacaoPane").style.zIndex = 450;

// Grupo das áreas de inundação
const camadaInundacao = L.geoJSON(null, {

    pane: "inundacaoPane",

    style: function(feature) {
        return {
            fillColor: "#dc2626",
            color: "#991b1b",
            weight: 1.5,
            opacity: 1,
            fillOpacity: 0.45
        };
    },

    onEachFeature: function(feature, layer) {

        const props = feature.properties;

        // Cria popup sem interpretar os dados como HTML
        const popup = document.createElement("div");

        const titulo = document.createElement("strong");
        titulo.textContent = "Área de risco de inundação";

        const identificador = document.createElement("p");
        identificador.textContent =
            `ID da área: ${props.ID_ARG ?? "-"}`;

        const risco = document.createElement("p");
        risco.textContent =
            `Classificação: ${props.RISCO_GEOLOGICO ?? "-"}`;

        const fid = document.createElement("p");
        fid.textContent = `FID: ${props.FID ?? "-"}`;

        popup.append(titulo, identificador, risco, fid);

        layer.bindPopup(popup);

        layer.bindTooltip(
            props.RISCO_GEOLOGICO || "Risco de inundação"
        );

        // Destaque ao passar o mouse
        layer.on("mouseover", function() {
            layer.setStyle({
                fillColor: "#991b1b",
                color: "#7f1d1d",
                weight: 2.5,
                fillOpacity: 0.65
            });
        });

        layer.on("mouseout", function() {
            camadaInundacao.resetStyle(layer);
        });

    }

});

let bairros = [];
let bairroSelecionado = null;
let indiceAtivo = -1;
let requisicaoBairroId = 0;
let ultimosResultados = [];

// ==========================================
// CAMADAS DE SOLUÇÕES BASEADAS NA NATUREZA (SBN)
// ==========================================

map.createPane("sbnPane");
map.getPane("sbnPane").style.zIndex = 440;

function criarCamadaSbn(corPreenchimento, corBorda) {
    return L.geoJSON(null, {
        pane: "sbnPane",
        style: function() {
            return {
                fillColor: corPreenchimento,
                color: corBorda,
                weight: 1.2,
                opacity: 0.9,
                fillOpacity: 0.45
            };
        },
        onEachFeature: function(feature, layer) {
            const props = feature.properties;
            const popup = document.createElement("div");

            const titulo = document.createElement("strong");
            titulo.textContent = `Área Prioritária SBN — ${props.TIPO_RISCO ?? "-"}`;

            const crit = document.createElement("p");
            crit.textContent = `Criticidade: ${props.NIVEL_CRITICIDADE ?? "-"} (Índice SBN: ${props.INDICE_PRIORIDADE_SBN ?? "-"})`;

            const exp = document.createElement("p");
            exp.textContent = `Exposição: ${props.INDICE_EXPOSICAO ?? "-"} | Vulnerabilidade: ${props.INDICE_VULNERABILIDADE ?? "-"}`;

            const idEl = document.createElement("p");
            idEl.textContent = `ID Microárea (2022): ${props.ID_SBN ?? "-"}`;

            popup.append(titulo, crit, exp, idEl);
            layer.bindPopup(popup);
            layer.bindTooltip(`${props.TIPO_RISCO}: ${props.NIVEL_CRITICIDADE} (${props.INDICE_PRIORIDADE_SBN})`);
        }
    });
}

const camadaSbnAlagamento = criarCamadaSbn("#2563eb", "#1d4ed8");
const camadaSbnDeslizamento = criarCamadaSbn("#d97706", "#b45309");
const camadaSbnOndasCalor = criarCamadaSbn("#ea580c", "#c2410c");

const sbnCarregadas = new Set();

function carregarCamadaSbnSobDemanda(tipo, camada) {
    if (sbnCarregadas.has(tipo)) {
        return;
    }
    sbnCarregadas.add(tipo);
    fetch(`/api/areas-sbn/${tipo}/geojson`)
        .then(r => {
            if (!r.ok) throw new Error(`Erro ao carregar SBN ${tipo}`);
            return r.json();
        })
        .then(data => {
            camada.addData(data);
        })
        .catch(err => {
            sbnCarregadas.delete(tipo);
            console.error(err);
        });
}

// ==========================================
// CONTROLE DE CAMADAS
// ==========================================

const controleCamadas = L.control.layers(
    null,
    {
        "Todos os contornos dos bairros": camadaTodosBairros,
        "Áreas de risco de inundação (Defesa Civil)": camadaInundacao,
        "SBN — Áreas prioritárias Alagamento": camadaSbnAlagamento,
        "SBN — Áreas prioritárias Deslizamento": camadaSbnDeslizamento,
        "SBN — Áreas prioritárias Ondas de Calor": camadaSbnOndasCalor
    },
    {
        position: "topright",
        collapsed: false
    }
).addTo(map);

map.on("overlayadd", function(event) {
    if (event.layer === camadaSbnAlagamento) {
        carregarCamadaSbnSobDemanda("alagamento", camadaSbnAlagamento);
    } else if (event.layer === camadaSbnDeslizamento) {
        carregarCamadaSbnSobDemanda("deslizamento", camadaSbnDeslizamento);
    } else if (event.layer === camadaSbnOndasCalor) {
        carregarCamadaSbnSobDemanda("ondas_calor", camadaSbnOndasCalor);
    }
});

// ==========================================
// GERENCIAMENTO DOS CONTORNOS DOS BAIRROS
// ==========================================

// Verifica se a camada geral está ativada
function bairrosVisiveis() {

    return map.hasLayer(camadaTodosBairros);

}


// Quando o usuário ativa a camada geral
map.on("overlayadd", function(event) {

    if (event.layer !== camadaTodosBairros) {
        return;
    }

    camadaTodosBairros.clearLayers();

    if (bairroSelecionado) {

        // Se existe bairro selecionado,
        // mostra somente ele na camada geral
        camadaTodosBairros.addData(bairroSelecionado);

        // Remove o destaque independente
        map.removeLayer(camadaSelecionada);

    } else {

        // Sem pesquisa: mostra todos os bairros
        camadaTodosBairros.addData({
            type: "FeatureCollection",
            features: bairros
        });

    }

});


// Quando o usuário desativa a camada geral
map.on("overlayremove", function(event) {

    if (event.layer !== camadaTodosBairros) {
        return;
    }

    // Se existe um bairro selecionado,
    // mantém seu contorno visível
    if (bairroSelecionado) {

        camadaSelecionada.clearLayers();

        camadaSelecionada.addData(bairroSelecionado);

        camadaSelecionada.addTo(map);

    }

});

// ==========================================
// CARREGAR ÁREAS DE INUNDAÇÃO
// ==========================================

fetch("/api/areas-inundacao/geojson")

    .then(response => {

        if (!response.ok) {
            throw new Error(
                "Erro ao carregar áreas de inundação."
            );
        }

        return response.json();

    })

    .then(data => {

        // Adiciona os polígonos ao grupo.
        // Não adiciona o grupo diretamente ao mapa.
        camadaInundacao.addData(data);

        console.log(
            "Áreas de inundação carregadas:",
            data.features.length
        );

    })

    .catch(error => {

        console.error(error);

    });

// ==========================================
// 2. ELEMENTOS DA PESQUISA
// ==========================================

const searchInput = document.getElementById("search-bairro");
const suggestions = document.getElementById("suggestions");
const clearButton = document.getElementById("clear-search");
const searchIcon = document.querySelector(".search-icon");


// ==========================================
// 3. NORMALIZAÇÃO DO TEXTO
// ==========================================

// Ignora acentos e diferenças entre maiúsculas
// e minúsculas na pesquisa.

function normalizarTexto(texto) {

    return String(texto || "")
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .toLowerCase()
        .trim();

}


// ==========================================
// 4. ESTILOS DOS POLÍGONOS
// ==========================================

function estiloBairro() {

    return {
        fillColor: "#2b8cbe",
        color: "#045a8d",
        weight: 2,
        opacity: 1,
        fillOpacity: 0.4
    };

}


// ==========================================
// 5. PAINEL DE INFORMAÇÕES
// ==========================================

function mostrarInformacoes(feature) {

    const props = feature.properties;

    function formatar(valor) {

        if (valor === null || valor === undefined || valor === "") {
            return "-";
        }

        const numero = Number(valor);

        return Number.isFinite(numero)
            ? numero.toLocaleString("pt-BR", {
                maximumFractionDigits: 3
            })
            : valor;

    }

    document.getElementById("bairro-nome").textContent =
        props.ROTULO_CONTROLADO || props.NOME || "Bairro";

    document.getElementById("bairro-descricao").textContent =
        `Unidade Territorial (${props.TIPO || "Bairro"}) · Manchas de Inundação: ${props.AREAS_INUNDACAO ?? 0}`;

    document.getElementById("bairro-area").textContent =
        formatar(props.AREA_KM2);

    document.getElementById("bairro-perimetro").textContent =
        formatar(props.PERIMETR_M);

}


async function consultarBairroBackend(feature) {

    const nomeBairro = feature.properties.NOME;
    const idBairro = feature.properties._id;

    const mensagemElemento = document.getElementById(
        "bairro-backend-mensagem"
    );

    // Identificador desta requisição
    const requisicaoAtual = ++requisicaoBairroId;

    mensagemElemento.textContent = "Cruzando dados geoespaciais no servidor...";

    try {

        const response = await fetch("/api/bairros/selecionado", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                nome_bairro: nomeBairro,
                id_bairro: idBairro
            })

        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.mensagem || "Erro ao consultar o bairro."
            );
        }

        // Ignora respostas de seleções anteriores
        if (requisicaoAtual !== requisicaoBairroId) {
            return;
        }

        mensagemElemento.textContent = data.mensagem;

        console.log("Resposta do backend:", data);

    } catch (error) {

        // Não permite que erros de requisições antigas
        // alterem a interface atual
        if (requisicaoAtual !== requisicaoBairroId) {
            return;
        }

        console.error("Erro na consulta do bairro:", error);

        mensagemElemento.textContent =
            "Não foi possível consultar as informações do bairro.";

    }

}


// ==========================================
// 5b. CLIMA DO BAIRRO
// ==========================================

let requisicaoClimaId = 0;

function formatarNumero(valor, unidade, casas = 1) {

    const numero = Number(valor);

    if (valor === null || valor === undefined || !Number.isFinite(numero)) {
        return "-";
    }

    return `${numero.toLocaleString("pt-BR", {
        maximumFractionDigits: casas
    })} ${unidade}`;

}

function limparClima(mensagem) {

    document.getElementById("clima-resumo").textContent = mensagem;
    document.getElementById("clima-detalhes").hidden = true;
    document.getElementById("clima-fonte").textContent = "";

}

async function consultarClima(feature) {

    const props = feature.properties;
    const requisicaoAtual = ++requisicaoClimaId;

    // O _id é único; o nome pode se repetir entre bairro e vila
    const consulta = (props._id !== undefined && props._id !== null)
        ? "id=" + encodeURIComponent(props._id)
        : "bairro=" + encodeURIComponent(props.NOME);

    limparClima("Consultando o clima...");

    try {

        const response = await fetch("/api/clima?" + consulta);

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.mensagem || "Erro ao consultar o clima."
            );
        }

        // Ignora respostas de seleções anteriores
        if (requisicaoAtual !== requisicaoClimaId) {
            return;
        }

        const clima = data.clima;
        const u = clima.unidades || {};

        document.getElementById("clima-resumo").textContent =
            clima.descricao;

        document.getElementById("clima-temperatura").textContent =
            formatarNumero(clima.temperatura_c, u.temperatura || "°C");

        document.getElementById("clima-sensacao").textContent =
            formatarNumero(clima.sensacao_termica_c, u.temperatura || "°C");

        document.getElementById("clima-umidade").textContent =
            formatarNumero(clima.umidade_relativa_pct, "%", 0);

        document.getElementById("clima-vento").textContent =
            formatarNumero(clima.vento_kmh, u.vento || "km/h");

        document.getElementById("clima-chuva-agora").textContent =
            formatarNumero(clima.precipitacao_mm, u.precipitacao || "mm");

        document.getElementById("clima-chuva-24h").textContent =
            formatarNumero(clima.chuva_ultimas_24h_mm, u.precipitacao || "mm");

        const hora = new Date(clima.atualizado_em)
            .toLocaleTimeString("pt-BR", {
                hour: "2-digit",
                minute: "2-digit"
            });

        document.getElementById("clima-fonte").textContent =
            `Atualizado às ${hora} · ${clima.fonte}`;

        document.getElementById("clima-detalhes").hidden = false;

    } catch (error) {

        if (requisicaoAtual !== requisicaoClimaId) {
            return;
        }

        console.error("Erro na consulta do clima:", error);

        limparClima("Não foi possível obter o clima agora.");

    }

}


// ==========================================
// 6. SELECIONAR UM OU MÚLTIPLOS BAIRROS
// ==========================================

function selecionarBairro(feature) {

    // Guarda o bairro selecionado
    bairroSelecionado = feature;

    // Limpa o destaque anterior
    camadaSelecionada.clearLayers();

    // Limpa a camada geral
    camadaTodosBairros.clearLayers();

    if (bairrosVisiveis()) {

        // Se a camada geral estiver ativada,
        // mostra somente o bairro pesquisado
        camadaTodosBairros.addData(feature);

        map.removeLayer(camadaSelecionada);

    } else {

        // Se estiver desativada,
        // mostra somente o bairro selecionado
        camadaSelecionada.addData(feature);

        camadaSelecionada.addTo(map);

    }

    // Calcula os limites geográficos do bairro
    const limites = L.geoJSON(feature).getBounds();

    // Aproxima o mapa
    map.fitBounds(limites, {
        padding: [40, 40],
        maxZoom: 16
    });

    // Atualiza informações
    mostrarInformacoes(feature);

    // Consulta informações adicionais no backend
    consultarBairroBackend(feature);

    // Consulta o clima atual no bairro
    consultarClima(feature);

    // Atualiza pesquisa
    searchInput.value = feature.properties.ROTULO_CONTROLADO || feature.properties.NOME;

    // Fecha sugestões
    suggestions.style.display = "none";

    clearButton.style.display = "block";

}

function destacarMultiplosBairros(lista, termoBusca) {

    if (!lista || lista.length === 0) {
        return;
    }

    if (lista.length === 1) {
        selecionarBairro(lista[0]);
        return;
    }

    bairroSelecionado = null;
    camadaSelecionada.clearLayers();
    camadaTodosBairros.clearLayers();

    // Adiciona todos os bairros correspondentes na camada destacada
    camadaSelecionada.addData({
        type: "FeatureCollection",
        features: lista
    });

    camadaSelecionada.addTo(map);

    try {
        const limites = camadaSelecionada.getBounds();
        if (limites && limites.isValid()) {
            map.fitBounds(limites, {
                padding: [40, 40],
                maxZoom: 15
            });
        }
    } catch (e) {
        console.warn("Erro ao ajustar limites do mapa:", e);
    }

    // Atualiza o painel com o resumo da busca
    document.getElementById("bairro-nome").textContent =
        `Busca: ${lista.length} unidades encontradas`;

    const nomesFormatados = lista.slice(0, 6)
        .map(f => f.properties.ROTULO_CONTROLADO || f.properties.NOME)
        .join(", ");
    const sufixoMais = lista.length > 6 ? ` e mais ${lista.length - 6}...` : "";

    document.getElementById("bairro-descricao").textContent =
        `Resultados da busca para "${termoBusca}". Mostrando todos os contornos correspondentes destacados no mapa. Clique em um bairro no mapa para ver o diagnóstico individual.`;

    document.getElementById("bairro-backend-mensagem").textContent =
        `Unidades territoriais localizadas: ${nomesFormatados}${sufixoMais}. Clique sobre qualquer um dos polígonos no mapa para gerar o boletim detalhado de riscos e clima.`;

    limparClima(`Exibindo ${lista.length} bairros no mapa. Clique em um bairro específico para ver os dados climáticos.`);

    [
        "bairro-area",
        "bairro-perimetro"
    ].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = "-";
    });

    suggestions.style.display = "none";
    clearButton.style.display = "block";

}


// ==========================================
// 7. CRIAR LISTA DE SUGESTÕES (CONTROLE DE VOCABULÁRIO)
// ==========================================

function mostrarSugestoes(lista) {

    suggestions.innerHTML = "";
    indiceAtivo = -1;

    if (lista.length === 0) {

        const mensagem = document.createElement("div");

        mensagem.className = "no-results";
        mensagem.textContent = "Nenhum bairro encontrado para os critérios e filtros informados.";

        suggestions.appendChild(mensagem);

        suggestions.style.display = "block";

        return;
    }

    // Cabeçalho informativo com contagem e dica de navegação
    const cabecalho = document.createElement("div");
    cabecalho.className = "suggestions-header";
    cabecalho.innerHTML = `
        <span><strong>${lista.length}</strong> encontrado(s)</span>
        <span style="font-size:11px; color:#64748b; font-weight:normal;">Pressione [Enter] para ver todos no mapa</span>
    `;
    suggestions.appendChild(cabecalho);

    // Limita a quantidade de sugestões visíveis na lista suspensa
    lista.slice(0, 15).forEach((feature) => {

        const props = feature.properties;
        const botao = document.createElement("button");

        botao.type = "button";
        botao.className = "suggestion-item";

        const nomeSpan = document.createElement("strong");
        nomeSpan.textContent = props.ROTULO_CONTROLADO || props.NOME;
        botao.appendChild(nomeSpan);

        const badgeTipo = document.createElement("span");
        badgeTipo.className = "badge-tipo";
        badgeTipo.textContent = `${props.TIPO || "Bairro"} · ID ${props._id}`;
        botao.appendChild(badgeTipo);

        if (props.AREAS_INUNDACAO > 0) {
            const badgeRisco = document.createElement("span");
            badgeRisco.className = "badge-tipo badge-risco";
            badgeRisco.textContent = `${props.AREAS_INUNDACAO} área(s) inundação`;
            botao.appendChild(badgeRisco);
        }

        botao.addEventListener("click", () => {
            selecionarBairro(feature);
        });

        suggestions.appendChild(botao);

    });

    suggestions.style.display = "block";

}


// ==========================================
// 8. RECUPERAÇÃO DA INFORMAÇÃO (OPERADORES BOOLEANOS + FILTROS)
// ==========================================

const filterTipo = document.getElementById("filter-tipo");
const filterRiscoInundacao = document.getElementById("filter-risco-inundacao");

/**
 * Parser de consultas booleanas que suporta:
 *   - OR / OU: união de blocos de busca
 *   - AND / E: interseção de termos dentro do bloco
 *   - NOT / NAO / -termo: exclusão de termos indesejados
 *   - Aspas: ex. "Santa Efigenia" para correspondência de expressão
 *   - Parênteses: ignorados de forma graciosa sem quebrar a busca
 *   - Tolerância a operadores pendentes enquanto o usuário digita
 */
function parseConsultaBooleana(consultaBruta) {
    if (!consultaBruta || typeof consultaBruta !== "string") {
        return null;
    }

    let texto = normalizarTexto(consultaBruta);
    if (!texto) {
        return null;
    }

    // Higieniza parênteses
    texto = texto.replace(/[()]/g, " ");

    // Divide a consulta pelos operadores de união OR / OU (com limites de palavra)
    const blocosOrRaw = texto.split(/\b(?:or|ou)\b/i);
    const blocosValidos = [];

    for (let blocoRaw of blocosOrRaw) {
        blocoRaw = blocoRaw.trim();
        if (!blocoRaw) {
            continue;
        }

        // Tokeniza respeitando aspas para expressões compostas
        const tokens = [];
        const regexTokens = /"([^"]+)"|(\S+)/g;
        let match;
        while ((match = regexTokens.exec(blocoRaw)) !== null) {
            const token = (match[1] || match[2]).trim();
            if (token) {
                tokens.push(token);
            }
        }

        const obrigatorios = [];
        const excluidos = [];

        for (let i = 0; i < tokens.length; i++) {
            const t = tokens[i];

            // Ignora conectivos de conjunção soltos
            if (t === "and" || t === "e") {
                continue;
            }

            // Operadores de negação
            if (t === "not" || t === "nao") {
                if (i + 1 < tokens.length) {
                    const prox = tokens[++i];
                    if (
                        prox &&
                        prox !== "and" &&
                        prox !== "e" &&
                        prox !== "not" &&
                        prox !== "nao"
                    ) {
                        excluidos.push(prox);
                    }
                }
                // Se não há próximo termo (usuário ainda digitando), apenas ignora
                continue;
            }

            // Prefixo de exclusão '-' (ex.: -vila, -inundacao)
            if (t.startsWith("-") && t.length > 1) {
                excluidos.push(t.slice(1));
                continue;
            }

            obrigatorios.push(t);
        }

        // Considera o bloco válido se tiver ao menos uma restrição
        if (obrigatorios.length > 0 || excluidos.length > 0) {
            blocosValidos.push({ obrigatorios, excluidos });
        }
    }

    return blocosValidos.length > 0 ? blocosValidos : null;
}

/**
 * Avalia se o documento indexado do bairro satisfaz os blocos da consulta booleana.
 */
function avaliarDocumento(documentoNorm, blocos) {
    if (!blocos || blocos.length === 0) {
        return true;
    }

    // Regra do OR: se atender a qualquer bloco, retorna true
    return blocos.some(bloco => {
        const atendeObrigatorios = bloco.obrigatorios.every(termo =>
            documentoNorm.includes(termo)
        );
        const atendeExcluidos = bloco.excluidos.every(termo =>
            !documentoNorm.includes(termo)
        );

        return atendeObrigatorios && atendeExcluidos;
    });
}

function executarPesquisa() {
    const textoBruto = searchInput.value;
    const tipoSelecionado = filterTipo.value;
    const apenasComRisco = filterRiscoInundacao.checked;

    clearButton.style.display = textoBruto ? "block" : "none";

    const consultaVazia = !textoBruto || !textoBruto.trim();
    if (consultaVazia && tipoSelecionado === "TODOS" && !apenasComRisco) {
        suggestions.style.display = "none";
        ultimosResultados = [];
        return;
    }

    const blocos = parseConsultaBooleana(textoBruto);

    ultimosResultados = bairros.filter(feature => {
        const props = feature.properties;

        // 1. Filtro Facetado por TIPO (Bairro, Vila, Conjunto)
        if (tipoSelecionado !== "TODOS" && props.TIPO !== tipoSelecionado) {
            return false;
        }

        // 2. Filtro Facetado por Risco de Inundação
        if (apenasComRisco && !(props.AREAS_INUNDACAO > 0)) {
            return false;
        }

        // 3. Documento indexado com vocabulário controlado e descritores claros
        const statusRisco = props.AREAS_INUNDACAO > 0
            ? "inundacao risco alagamento"
            : "livre seguro sem_inundacao";

        const docIndexado = normalizarTexto(
            `${props.NOME || ""} ${props.TIPO || ""} ${props.ROTULO_CONTROLADO || ""} ${statusRisco}`
        );

        return avaliarDocumento(docIndexado, blocos);
    });

    mostrarSugestoes(ultimosResultados);
}

searchInput.addEventListener("input", executarPesquisa);
filterTipo.addEventListener("change", executarPesquisa);
filterRiscoInundacao.addEventListener("change", executarPesquisa);

if (searchIcon) {
    searchIcon.setAttribute("title", "Executar busca no mapa (Enter)");
    searchIcon.addEventListener("click", () => {
        if (ultimosResultados.length === 1) {
            selecionarBairro(ultimosResultados[0]);
        } else if (ultimosResultados.length > 1) {
            destacarMultiplosBairros(ultimosResultados, searchInput.value);
        }
    });
}

// Botão de Metadados Dublin Core / ISO 19115 / e-ARQ
const btnMetadados = document.getElementById("btn-metadados");
const metadadosBox = document.getElementById("metadados-box");

btnMetadados.addEventListener("click", async function() {
    if (!metadadosBox.hidden) {
        metadadosBox.hidden = true;
        btnMetadados.textContent = "Ver Metadados (Dublin Core / ISO 19115 / e-ARQ)";
        return;
    }
    metadadosBox.hidden = false;
    btnMetadados.textContent = "Ocultar Metadados";
    if (!metadadosBox.textContent) {
        metadadosBox.textContent = "Carregando catálogo de metadados...";
        try {
            const r = await fetch("/api/metadados");
            const dados = await r.json();
            metadadosBox.textContent = JSON.stringify(dados, null, 2);
        } catch (e) {
            metadadosBox.textContent = "Erro ao carregar metadados.";
        }
    }
});


// ==========================================
// 9. NAVEGAÇÃO PELO TECLADO
// ==========================================

searchInput.addEventListener("keydown", function(event) {

    const botoes = suggestions.querySelectorAll(
        ".suggestion-item"
    );

    if (event.key === "ArrowDown" && botoes.length) {

        event.preventDefault();

        indiceAtivo = Math.min(
            indiceAtivo + 1,
            botoes.length - 1
        );

        atualizarSugestaoAtiva(botoes);

    }

    else if (event.key === "ArrowUp" && botoes.length) {

        event.preventDefault();

        indiceAtivo = Math.max(
            indiceAtivo - 1,
            0
        );

        atualizarSugestaoAtiva(botoes);

    }

    else if (event.key === "Enter") {

        event.preventDefault();

        if (indiceAtivo >= 0 && botoes[indiceAtivo]) {

            botoes[indiceAtivo].click();

        } else if (ultimosResultados.length === 1) {

            selecionarBairro(ultimosResultados[0]);

        } else if (ultimosResultados.length > 1) {

            destacarMultiplosBairros(ultimosResultados, searchInput.value);

        }

    }

    else if (event.key === "Escape") {

        limparPesquisa();

    }

});


function atualizarSugestaoAtiva(botoes) {

    botoes.forEach((botao, index) => {

        botao.classList.toggle(
            "active",
            index === indiceAtivo
        );

    });

}


// ==========================================
// 10. LIMPAR PESQUISA
// ==========================================

function limparPesquisa() {

    searchInput.value = "";

    suggestions.style.display = "none";

    clearButton.style.display = "none";

    // Remove os bairros selecionados
    map.removeLayer(camadaSelecionada);

    camadaSelecionada.clearLayers();

    bairroSelecionado = null;
    ultimosResultados = [];

    // Invalida requisições anteriores
    requisicaoBairroId++;
    requisicaoClimaId++;

    limparClima("Selecione um bairro para ver o clima.");

    // Se o toggle geral estiver ligado, restaura todos os bairros
    if (bairrosVisiveis()) {

        camadaTodosBairros.clearLayers();

        camadaTodosBairros.addData({
            type: "FeatureCollection",
            features: bairros
        });

    } else {

        // Caso contrário, mantém todos ocultos
        camadaTodosBairros.clearLayers();

    }

    // Volta para a visão geral de BH
    map.setView([-19.9167, -43.9345], 12);

    // Limpa o painel
    document.getElementById("bairro-nome").textContent =
        "Informações do bairro";

    document.getElementById("bairro-descricao").textContent =
        "Pesquise e selecione um bairro para visualizar seu contorno.";

    [
        "bairro-area",
        "bairro-perimetro"
    ].forEach(id => {

        const el = document.getElementById(id);
        if (el) el.textContent = "-";

    });

    document.getElementById("bairro-backend-mensagem").textContent =
        "Selecione um bairro para consultar o backend.";

}

clearButton.addEventListener("click", function() {

    limparPesquisa();
    searchInput.focus();

});

// Atalho global: tecla Esc limpa o bairro selecionado e volta a ver todos os bairros
document.addEventListener("keydown", function(event) {

    if (event.key === "Escape") {

        if (
            bairroSelecionado !== null ||
            searchInput.value.trim() !== "" ||
            ultimosResultados.length > 0 ||
            camadaSelecionada.getLayers().length > 0
        ) {
            limparPesquisa();
        } else if (suggestions.style.display === "block") {
            suggestions.style.display = "none";
        }

    }

});


// Fecha as sugestões ao clicar fora da pesquisa
document.addEventListener("click", function(event) {

    if (!event.target.closest(".search-container")) {

        suggestions.style.display = "none";

    }

});


// ==========================================
// 11. CARREGAR OS BAIRROS DO FLASK
// ==========================================

fetch("/api/bairros/geojson")

    .then(response => {

        if (!response.ok) {
            throw new Error("Erro ao carregar os bairros.");
        }

        return response.json();

    })

    .then(data => {

        bairros = data.features || [];

        console.log(
            "Total de bairros disponíveis:",
            bairros.length
        );

        // Se o usuário já ativou a camada geral,
        // carrega todos os bairros
        if (bairrosVisiveis() && !bairroSelecionado) {

            camadaTodosBairros.clearLayers();

            camadaTodosBairros.addData({
                type: "FeatureCollection",
                features: bairros
            });

        }

        // Se o usuário já alterou filtros ou digitou antes do carregamento terminar,
        // reexecuta a pesquisa automaticamente
        if (
            searchInput.value.trim() !== "" ||
            filterTipo.value !== "TODOS" ||
            filterRiscoInundacao.checked
        ) {
            executarPesquisa();
        }

    })

    .catch(error => {

        console.error(error);

        document.getElementById("bairro-descricao").textContent =
            "Não foi possível carregar os bairros. Tente novamente.";

    });
