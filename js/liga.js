/* La página de la liga argentina (liga.html). Los datos de cada torneo viven en data/ligas/argentina/<torneo>.js
   (window.LIGA[torneo]) y los arma tools/actualizar_liga.py. La tabla de posiciones no viene en los datos: se
   calcula acá con los resultados de cada partido (así, al bajar los partidos nuevos, la tabla queda al día).
   Dirección: liga.html?torneo=2026-clausura&vista=fechas&fecha=5 (sin torneo, el último). */
(function () {
  const PARAMS = new URLSearchParams(location.search);
  const INDICE = window.LIGA_INDICE || [];
  // El año de cada torneo sale de su clave ("2025-apertura"). Con ?anio=2025 se abre el último torneo de ese año
  // (el que cierra el año: tiene la tabla anual); sin nada, el último cargado
  const anioDe = t => t.clave.slice(0, 4);
  const delAnio = INDICE.filter(t => anioDe(t) === PARAMS.get("anio"));
  const CLAVE = INDICE.some(t => t.clave === PARAMS.get("torneo")) ? PARAMS.get("torneo")
    : delAnio.length ? delAnio.at(-1).clave : INDICE.at(-1)?.clave;
  const RONDA = { 8: "los octavos de final", 4: "los cuartos de final", 2: "las semifinales" };
  const VISTAS = [["tabla", "Tabla"], ["fechas", "Fechas"], ["playoffs", "Playoffs"], ["anual", "Tabla anual"],
    ["promedios", "Promedios"], ["goleadores", "Goleadores"], ["asistidores", "Asistidores"]];
  const ligaEl = document.getElementById("liga");
  const esc = t => String(t ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const DIAS = ["domingo", "lunes", "martes", "miércoles", "jueves", "viernes", "sábado"];
  const MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];
  const fechaLarga = f => { const d = new Date(f + "T12:00"); return `${DIAS[d.getDay()]} ${d.getDate()} de ${MESES[d.getMonth()]}`; };
  const fechaCorta = f => { const [, m, d] = f.split("-"); return `${+d}/${+m}`; };

  if (!CLAVE) { ligaEl.innerHTML = `<p class="vacio">No se encontraron los datos de la liga.</p>`; return; }
  const s = document.createElement("script");
  s.src = `data/ligas/argentina/${CLAVE}.js`;
  s.onload = () => iniciar(window.LIGA[CLAVE]);
  s.onerror = () => { ligaEl.innerHTML = `<p class="vacio">No se pudo cargar el torneo.</p>`; };
  document.body.appendChild(s);

  function iniciar(T) {
    const club = id => T.clubes[id] || { nombre: id };
    const escudo = id => club(id).escudo ? `<img class="escudo" src="${club(id).escudo}" alt="" loading="lazy" onerror="this.remove()">` : "";
    const nombreClub = id => `${escudo(id)}${esc(club(id).nombre)}`;
    const jugado = p => p.gl != null;
    const todos = T.fechas.flatMap(f => f.partidos.map(p => ({ ...p, n: f.numero })));
    const zonaDe = {};
    // Los títulos de liga de este torneo, con el número de cada uno para su club (data/ligas/argentina/titulos.js): los
    // de antes de 1990 más los de los torneos cargados hasta este. Y cuántos seguidos lleva el club (River en el
    // Apertura 1997: 3, un tricampeonato), contando todos los títulos en orden
    const TIT = window.LIGA_TITULOS || {};
    const TITULOS = (() => {
      const cuenta = { ...TIT.antes };
      // (seguidos_antes: cuántos títulos seguidos llevaba ese club: River, campeón del Metropolitano y del Nacional 1979)
      let anterior = TIT.ultimo_antes, seguidos = TIT.seguidos_antes || 1;
      for (const t of INDICE) {
        const deEste = (TIT.torneos?.[t.clave] || []).map(e => {
          const [club, texto] = Array.isArray(e) ? e : [e, null];
          cuenta[club] = (cuenta[club] || 0) + 1;
          seguidos = club === anterior ? seguidos + 1 : 1;
          anterior = club;
          return { club, texto, n: cuenta[club], seguidos };
        });
        if (t.clave === CLAVE) return deEste;
      }
      return [];
    })();
    const RACHA = { 2: "bicampeonato", 3: "tricampeonato", 4: "tetracampeonato", 5: "pentacampeonato" };
    const numeroTitulo = x => ` <small class="veces-campeon">· título de liga n.º ${x.n}${x.seguidos > 1
      ? ` · <strong class="racha" title="${x.seguidos} títulos de liga seguidos">${RACHA[x.seguidos] || `${x.seguidos} títulos seguidos`}</strong>` : ""}</small>`;
    Object.entries(T.zonas).forEach(([z, ids]) => ids.forEach(id => { zonaDe[id] = z; }));
    // {fecha: {club: zona}} en los torneos por etapas (dos etapas pueden ir en las mismas fechas: la Copa Maradona)
    const zonaEtapa = {};
    (T.etapas || []).forEach(et => et.fechas.forEach(n => {
      Object.entries(et.zonas).forEach(([z, ids]) => ids.forEach(id => { (zonaEtapa[n] ||= {})[id] = z; }));
    }));

    document.title = `${T.nombre} — Liga Profesional Argentina`;
    document.getElementById("titulo-torneo").textContent = T.nombre;
    // Los torneos cargados, para pasar de uno a otro (el que se está viendo, resaltado)
    // Primero los años y, abajo, los torneos del año que se está viendo (sin el año en el nombre: "Apertura", "Clausura")
    const anio = CLAVE.slice(0, 4);
    const anios = [...new Set(INDICE.map(anioDe))];
    // Como en la Libertadores: ◀ 📅 año ▾ ▶ (año anterior / siguiente) y el panel para escribir el año, con los años
    // agrupados por década
    const i = anios.indexOf(anio);
    const decadas = [...new Set(anios.map(a => a.slice(0, 3)))];
    const nombreDecada = d => d === "199" ? "Años 90" : `Años ${d}0`;
    document.getElementById("torneos").innerHTML =
      `<div class="grupo-anios">
        <button class="flecha-anio" type="button" data-ir-anio="${anios[i - 1] || ""}" ${i > 0 ? "" : "disabled"}
          aria-label="Año anterior" title="Año anterior">◀</button>
        <button class="boton-anios" id="boton-anios" type="button" aria-expanded="false" aria-controls="panel-anios">📅 ${anio} ▾</button>
        <button class="flecha-anio" type="button" data-ir-anio="${anios[i + 1] || ""}" ${i < anios.length - 1 ? "" : "disabled"}
          aria-label="Año siguiente" title="Año siguiente">▶</button>
      </div>
      <div class="panel-anios" id="panel-anios" hidden>
        <div class="fila-buscar-anio">
          <input id="buscar-anio" type="search" inputmode="numeric" maxlength="4" placeholder="Escribí un año (ej.: 1998)"
            autocomplete="off" aria-label="Buscar año">
        </div>
        <nav class="ediciones" id="ediciones" aria-label="Años">${decadas.map(d => `<div class="nombre-copa"><h3>${nombreDecada(d)}</h3>
          <div class="anios">${anios.filter(a => a.startsWith(d)).map(a => `<a href="?anio=${a}" data-anio="${a}"${a === anio
            ? ` aria-current="page"` : ""} title="${esc(INDICE.filter(t => anioDe(t) === a).map(t => t.nombre).join(" · "))}">${a}</a>`).join("")}</div></div>`).join("")}</nav>
        <p class="vacio" id="anio-vacio" hidden>No hay ningún torneo cargado de ese año.</p>
      </div>
      <div class="torneos-del-anio">${INDICE.filter(t => anioDe(t) === anio).map(t => `<a href="?torneo=${t.clave}"${t.clave === CLAVE
        ? ` aria-current="page"` : ""}>${esc(t.nombre.replace(/^Torneo /, "").replace(/ \d{4}$/, ""))}</a>`).join("")}</div>`;
    // Panel de años: se abre con el botón 📅; escribiendo se filtran los años y con Enter se abre el elegido
    const botonAniosEl = document.getElementById("boton-anios");
    const panelAniosEl = document.getElementById("panel-anios");
    const buscarAnioEl = document.getElementById("buscar-anio");
    const listaAniosEl = document.getElementById("ediciones");
    const irAlAnio = a => { location.href = `?anio=${a}`; };
    function filtrarAnios() {
      const q = buscarAnioEl.value.replace(/\D/g, "");
      const visibles = [...listaAniosEl.querySelectorAll("a[data-anio]")].filter(a => !(a.hidden = !a.dataset.anio.startsWith(q)));
      listaAniosEl.querySelectorAll(".nombre-copa").forEach(g => { g.hidden = !g.querySelector("a[data-anio]:not([hidden])"); });
      document.getElementById("anio-vacio").hidden = visibles.length > 0;
      return visibles;
    }
    function abrirAnios() {
      panelAniosEl.hidden = false;
      botonAniosEl.setAttribute("aria-expanded", "true");
      buscarAnioEl.focus();
    }
    function cerrarAnios() {
      if (panelAniosEl.hidden) return;
      panelAniosEl.hidden = true;
      botonAniosEl.setAttribute("aria-expanded", "false");
      buscarAnioEl.value = "";
      filtrarAnios();
    }
    botonAniosEl.addEventListener("click", () => (panelAniosEl.hidden ? abrirAnios() : cerrarAnios()));
    document.querySelectorAll("[data-ir-anio]").forEach(b => b.addEventListener("click", () => irAlAnio(b.dataset.irAnio)));
    buscarAnioEl.addEventListener("input", filtrarAnios);
    buscarAnioEl.addEventListener("keydown", e => {
      if (e.key === "Escape") { cerrarAnios(); botonAniosEl.focus(); return; }
      if (e.key !== "Enter") return;
      const visibles = filtrarAnios();
      const elegido = visibles.find(a => a.dataset.anio === buscarAnioEl.value.trim()) || (visibles.length === 1 ? visibles[0] : null);
      if (elegido) irAlAnio(elegido.dataset.anio);
    });
    // Tocar afuera del panel lo cierra
    document.addEventListener("click", e => { if (!e.target.closest("#panel-anios, #boton-anios")) cerrarAnios(); });
    // El campeón: el ganador de la final (en los 90 minutos, en el alargue o por penales)
    const final = T.playoffs.find(r => r.nombre === "Final")?.partidos[0];
    const todoJugado = T.fechas.every(f => f.partidos.every(p => p.gl != null || p.estado));
    // un triangular final entre los empatados arriba (T.triangular: el Apertura 2008): el primero de esos tres partidos
    const tri = T.triangular ? T.playoffs[0]?.partidos || [] : null;
    const clubesTri = tri && [...new Set(tri.flatMap(p => [p.local, p.visitante]))];
    // (una final a ida y vuelta: el que ganó la serie, con el global y el gol de visitante; el Nacional 1977)
    const serieFinal = T.ida_y_vuelta && T.playoffs.find(r => r.nombre === "Final")?.partidos.length === 2
      ? series(T.playoffs.find(r => r.nombre === "Final").partidos)[0] : null;
    const campeon = serieFinal ? serieFinal.gana || null
      : final && final.gl != null ? (final.gl > final.gv || final.gl === final.gv && final.pen_l > final.pen_v ? final.local : final.visitante)
      // (T.campeon_etapa: el primero de la tabla de esa etapa, el Torneo Campeonato del Metropolitano 1976; antes que el
      // triangular, que en el Nacional 1974 fue el Reducido por la Libertadores)
      : T.campeon_etapa ? (todoJugado ? (et => tabla(Object.values(et.zonas).flat(),
          todos.filter(p => et.fechas.includes(p.n) && Object.values(et.zonas).some(ids => ids.includes(p.local))))[0].id)(
          T.etapas.find(et => et.nombre === T.campeon_etapa)) : null)
      : tri && tri.length && tri.every(jugado) ? tabla(clubesTri, tri)[0].id
      : T.campeon_tabla && todoJugado ? tabla(Object.values(T.zonas).flat())[0].id : null;
    const [dia, hora] = T.actualizado.split(" ");
    document.getElementById("actualizado").textContent = campeon ? "Torneo terminado"
      : `Actualizado el ${fechaLarga(dia)} a las ${hora} · se actualiza todos los días`;
    if (campeon) {
      const c = document.getElementById("campeon-torneo");
      c.hidden = false;
      const propio = TITULOS.find(x => !x.texto && x.club === campeon);
      const nota = TIT.notas?.[CLAVE];
      c.innerHTML = `🏆 Campeón: ${nombreClub(campeon)}${propio ? numeroTitulo(propio) : nota ? ` <small class="veces-campeon">(${esc(nota)})</small>` : ""}`
        // otro título que se definió en este torneo (la final de 1990-91, la Superfinal 2012-13)
        + TITULOS.filter(x => x.texto).map(x => `<br>🏆 ${esc(x.texto)}: ${nombreClub(x.club)}${numeroTitulo(x)}`).join("");
    }


    // ---- Tabla de posiciones de cada zona (los partidos interzonales cuentan para la zona de cada club) ----
    // partidos: los que cuentan (en los torneos por etapas, los de esa etapa)
    // (descontar: restar T.descuentos; en los torneos por etapas, en la primera, como a Banfield en el Nacional 1975)
    function tabla(ids, partidos = todos, descontar = partidos === todos) {
      const t = Object.fromEntries(ids.map(id => [id, { id, pj: 0, g: 0, e: 0, p: 0, pg: 0, gf: 0, gc: 0, ultimos: [] }]));
      partidos.filter(jugado).sort((a, b) => (a.fecha || "").localeCompare(b.fecha || "")).forEach(p => {
        // (p.para_local: un partido que la AFA les dio perdido a los dos, como Almagro-Boca 2005: al local, otro resultado)
        // (p.para_visitante, y un tercer valor: el resultado que cuenta, como San Lorenzo-Huracán 1997, perdido 0-0 por los dos)
        [[p.local, ...(p.para_local || [p.gl, p.gv])], [p.visitante, ...(p.para_visitante || [p.gv, p.gl])]].forEach(([id, a, b, cuenta]) => {
          const f = t[id];
          if (!f) return;
          f.pj++; f.gf += a; f.gc += b;
          const r = cuenta || (a > b ? "V" : a < b ? "D" : "E");
          f[{ V: "g", E: "e", D: "p" }[r]]++;
          // (T.punto_penales: el Campeonato 1988-89, con penales después de cada empate y un punto más para el ganador)
          const pen = T.punto_penales && r === "E" && p.pen_l != null && !p.para_local;
          if (pen && (id === p.local ? p.pen_l > p.pen_v : p.pen_v > p.pen_l)) f.pg++;
          f.ultimos.push({ r, texto: `${p.n != null ? `Fecha ${p.n}: ` : ""}${club(p.local).nombre} ${p.gl}–${p.gv} ${club(p.visitante).nombre}${pen ? ` (penales ${p.pen_l}–${p.pen_v})` : ""}` });
        });
      });
      // (T.descuentos: puntos que se le restaron a un club en este torneo, como a Los Andes en el Clausura 2001)
      const menos = id => descontar ? (T.descuentos || {})[id] || 0 : 0;
      // (T.puntos_victoria: 2, como hasta el Clausura 1995; después, 3)
      // (en los torneos por etapas, un desempate entre dos empatados en puntos de la misma zona, como Vélez-Argentinos en
      // el Metropolitano 1979, pone primero al que lo ganó)
      const d = T.etapas && T.desempate, gana = d && d.gl != null && (d.gl > d.gv || d.gl === d.gv && d.pen_l > d.pen_v ? d.local : d.visitante);
      const porDesempate = (a, b) => gana && [d.local, d.visitante].includes(a.id) && [d.local, d.visitante].includes(b.id) ? (a.id === gana ? -1 : 1) : 0;
      return Object.values(t).map(f => ({ ...f, pts: f.g * (T.puntos_victoria || 3) + f.e + f.pg - menos(f.id), dif: f.gf - f.gc }))
        .sort((a, b) => b.pts - a.pts || porDesempate(a, b) || b.dif - a.dif || b.gf - a.gf || club(a.id).nombre.localeCompare(club(b.id).nombre));
    }
    // (bajan: los últimos que descienden, marcados; el Torneo por el descenso del Metropolitano 1979)
    // (conCampeon: marcar al campeón; no en el Reducido por la Libertadores del Nacional 1974)
    function tablaHTML(z, zonas = T.zonas, pasan = T.pasan, partidos = todos, bajan = 0, descontar = partidos === todos, conCampeon = true) {
      const filas = tabla(zonas[z], partidos, descontar);
      const cuerpo = filas.map((f, i) => {
        const dif = f.dif > 0 ? `+${f.dif}` : f.dif;
        const ultimos = f.ultimos.slice(-5).reverse().map(u => `<span class="res res-${u.r}" title="${esc(u.texto)}"
          aria-label="${{ V: "Victoria", E: "Empate", D: "Derrota" }[u.r]}">${{ V: "✓", E: "–", D: "✕" }[u.r]}</span>`).join("");
        return `<tr><td class="pos ${i < pasan ? "pasa" : i >= filas.length - bajan ? "desciende" : conCampeon && f.id === campeon ? "campeon" : ""}">${i + 1}</td><td class="eq">${nombreClub(f.id)}</td>
          <td class="pts">${f.pts}</td><td>${f.pj}</td><td class="gol">${f.gf}:${f.gc}</td>
          <td class="dif">${dif}</td><td class="opc">${f.g}</td><td class="opc">${f.e}</td><td class="opc">${f.p}</td>${T.punto_penales ? `<td class="opc">${f.pg}</td>` : ""}
          <td class="ultimas" title="El más reciente a la izquierda">${ultimos}</td></tr>`;
      }).join("");
      // (una zona con nombre largo va tal cual: "Posiciones", la del Torneo por el descenso de 1979)
      return `<div class="grupo"><h4>${z ? (z.length > 1 ? esc(z) : `Zona ${esc(z)}`) : "Tabla de posiciones"}</h4><table>
        <thead><tr><th>#</th><th class="eq">Equipo</th><th>Pts</th><th>J</th><th class="gol">Gol</th><th>+/-</th>
          <th class="opc">G</th><th class="opc">E</th><th class="opc">P</th>${T.punto_penales ? `<th class="opc" title="Empates ganados por penales (cada uno, un punto más)">Pen.</th>` : ""}<th class="ultimas">Últimas</th></tr></thead>
        <tbody>${cuerpo}</tbody></table></div>`;
    }
    // Torneos por etapas (la Copa Maradona 2020, el Nacional 1983): las zonas de cada etapa, con los partidos de sus
    // fechas (los interzonales suman en la zona de cada club; et.texto_pasan: la leyenda propia de la etapa)
    const vistaEtapas = () => `${T.nota ? `<p class="nota-edicion">${esc(T.nota)}</p>` : ""}` + T.etapas.map((et, n) => {
      const partidos = todos.filter(p => et.fechas.includes(p.n) && Object.values(et.zonas).some(ids => ids.includes(p.local)));
      const siguiente = n === 0 ? "la Fase Campeón" : "la final";
      // (T.descensos "etapa": bajan los últimos de la última etapa, el Torneo por el descenso del Metropolitano 1979)
      const bajan = T.descensos === "etapa" && n === T.etapas.length - 1 ? T.descienden || 1 : 0;
      // (el desempate entre dos de la misma zona de esta etapa, abajo de sus tablas)
      const des = T.desempate && Object.values(et.zonas).some(ids => ids.includes(T.desempate.local) && ids.includes(T.desempate.visitante));
      return `<h3>${esc(et.nombre)} <small class="vacio">(fechas ${et.fechas[0]} a ${et.fechas.at(-1)})</small></h3>
        <div class="grupos">${Object.keys(et.zonas).map(z => tablaHTML(z, et.zonas, et.pasan, partidos, bajan, n === 0)).join("")}</div>
        <p class="leyenda"><span><i class="${et.nombre === T.campeon_etapa ? "campeon" : "pasa"}"></i>${et.texto_pasan ? esc(et.texto_pasan)
          : `${et.pasan > 1 ? `Los ${et.pasan} primeros de cada zona pasan` : "El primero de cada zona pasa"}
          a ${/Complementación/.test(et.nombre) ? "la final de la Complementación" : siguiente}`}</span>${bajan
          ? `<span><i class="desciende"></i>Desciende${bajan > 1 ? `n (los ${{ 2: "dos", 3: "tres" }[bajan] || bajan} últimos)` : " (el último)"}</span>` : ""}</p>
        ${n === 0 && T.descuentos_texto ? `<p class="nota-edicion">${esc(T.descuentos_texto)}</p>` : ""}
        ${des ? `<h3>Desempate</h3><p class="vacio">${esc(T.desempate_texto || "")}</p>${partidoHTML(T.desempate)}` : ""}`;
    }).join("") + (T.sin_descensos ? `<p class="nota-edicion">${esc(T.sin_descensos)}</p>` : "");
    const vistaTabla = () => T.etapas ? vistaEtapas() : `<div class="grupos">${Object.keys(T.zonas).map(z => tablaHTML(z)).join("")}</div>
      <p class="leyenda">${T.texto_pasan ? `<span><i class="pasa"></i>${esc(T.texto_pasan)}</span>` : T.pasan ? `<span><i class="pasa"></i>Clasifican a ${RONDA[T.pasan] || "los playoffs"} (los ${T.pasan} primeros de cada zona)</span>` : ""}
        ${T.campeon_tabla ? `<span><i class="campeon"></i>Campeón: el primero de la tabla (no hay playoffs)</span>` : ""}</p>
      ${T.descuentos_texto ? `<p class="nota-edicion">${esc(T.descuentos_texto)}</p>` : ""}
      <p class="vacio">${T.puntos_victoria ? `Cada partido ganado valía ${T.puntos_victoria} puntos (los 3 puntos empezaron en el Torneo Apertura 1995). ` : ""}${T.punto_penales ? "Cada partido ganado valía 3 puntos y el empate 1; después de cada empate había penales, y el que los ganaba sumaba 1 punto más (Pen.: los empates ganados por penales). " : ""}Orden: puntos, diferencia de gol y goles a favor.${Object.keys(T.zonas).length > 1
        ? " Los partidos contra la otra zona (interzonales) suman en la zona de cada club." : ""}</p>`;

    // ---- Tabla anual: lo jugado antes en el año (T.anual: el Apertura, [pts, pj, g, e, p, gf, gc]) más este torneo ----
    const ids = Object.values(T.zonas).flat();
    // con el mismo puntaje, un partido desempate entre los dos (T.desempate) pone primero al que lo ganó
    const porDesempate = (a, b) => {
      const d = T.desempate, g = d && ganador(d), par = d ? [d.local, d.visitante] : [];
      if (!g || !par.includes(a.id) || !par.includes(b.id)) return 0;
      return a.id === g ? -1 : 1;
    };
    function tablaAnual() {
      const ahora = Object.fromEntries(Object.values(T.zonas).flatMap(z => tabla(z)).map(f => [f.id, f]));
      return ids.map(id => {
        const [pts, pj, g, e, p, gf, gc] = (T.anual || {})[id] || [0, 0, 0, 0, 0, 0, 0];
        const f = ahora[id];
        return { id, pts: pts + f.pts, pj: pj + f.pj, g: g + f.g, e: e + f.e, p: p + f.p, gf: gf + f.gf, gc: gc + f.gc };
      }).map(f => ({ ...f, dif: f.gf - f.gc }))
        .sort((a, b) => b.pts - a.pts || porDesempate(a, b) || b.dif - a.dif || b.gf - a.gf || club(a.id).nombre.localeCompare(club(b.id).nombre));
    }
    // ---- Promedios: puntos dividido partidos de las temporadas anteriores (T.promedios: {año: {club: [pts, pj]}})
    // más la del año (la tabla anual). Los recién ascendidos dividen solo por los partidos que jugaron en Primera ----
    const aniosProm = Object.keys(T.promedios || {}).sort();
    function promedios() {
      const anual = Object.fromEntries(tablaAnual().map(f => [f.id, f]));
      return ids.map(id => {
        // (T.promedios_victoria: 2, como hasta 1996-97, cuando los promedios contaban 2 puntos por partido ganado)
        // (sin el punto de los penales de 1988-89, y con los puntos descontados en el torneo)
        const pts = T.promedios_victoria ? T.promedios_victoria * anual[id].g + anual[id].e - ((T.descuentos || {})[id] || 0) : anual[id].pts;
        // (T.promedios_por_temporada: hasta 1985-86, los puntos de cada temporada divididos por las temporadas jugadas)
        const temporadas = [...aniosProm.map(a => T.promedios[a][id] || null), [pts, T.promedios_por_temporada ? 1 : anual[id].pj]];
        const total = temporadas.reduce((n, t) => n + (t ? t[0] : 0), 0);
        const pj = temporadas.reduce((n, t) => n + (t ? t[1] : 0), 0);
        return { id, temporadas, pts: total, pj, prom: pj ? total / pj : 0 };
      }).sort((a, b) => b.prom - a.prom || club(a.id).nombre.localeCompare(club(b.id).nombre));
    }
    // Descienden el último de la tabla anual y el peor promedio; si es el mismo club, el anteúltimo de la tabla anual
    // (todos: los que bajan; porProm: los que bajan por los promedios)
    function descensos(aunqueAnulados) {
      if (!T.descensos && !(aunqueAnulados && T.descensos_anulados)) return { anual: null, prom: null, todos: [], porProm: [] };
      // 2022: bajaban los dos últimos de los promedios (no había descenso por tabla anual); 2018-19, los cuatro últimos
      if (T.descensos === "promedios") {
        const n = T.descienden || 2, ids = promedios().map(f => f.id);
        // empate en el lugar del descenso definido en un partido (2014: Colón-Rafaela; 2011: Huracán-Gimnasia, por la
        // Promoción): el que ganó queda arriba del que perdió
        const des = T.desempate, gana = des && ganador(des), pierde = gana && (gana === des.local ? des.visitante : des.local);
        if (gana && ids.indexOf(gana) > ids.indexOf(pierde)) [ids[ids.indexOf(gana)], ids[ids.indexOf(pierde)]] = [pierde, gana];
        const porProm = ids.slice(-n);
        // 2011 y 2012: los dos de arriba de los que bajaban jugaban la Promoción contra equipos de la B Nacional (T.promocion)
        const promo = T.promocion ? ids.slice(-(n + T.promocion), -n) : [];
        return { porProm, todos: porProm, anual: null, promo };
      }
      // hasta 1982: bajaban los últimos de la tabla, sin promedios (un empate en ese lugar, ya resuelto en la tabla por
      // el desempate)
      if (T.descensos === "tabla") {
        const ids = tablaAnual().map(f => f.id).slice(-(T.descienden || 2));
        return { anual: null, prom: null, todos: ids, porProm: [] };
      }
      // 1979: bajaban los últimos de la última etapa (el Torneo por el descenso)
      if (T.descensos === "etapa") {
        const et = T.etapas.at(-1), ids = Object.values(et.zonas).flat();
        const partidos = todos.filter(p => et.fechas.includes(p.n) && ids.includes(p.local));
        return { anual: null, prom: null, todos: tabla(ids, partidos).map(f => f.id).slice(-(T.descienden || 1)), porProm: [] };
      }
      const anual = tablaAnual(), prom = promedios().at(-1).id;
      let porAnual = anual.at(-1).id === prom ? anual.at(-2).id : anual.at(-1).id;
      // empate en puntos por ese lugar: lo definió un partido desempate (2023: Gimnasia-Colón), baja el que perdió
      const des = T.desempate;
      if (des && des.gl != null && [des.local, des.visitante].includes(porAnual))
        porAnual = ganador(des) === des.local ? des.visitante : des.local;
      return { prom, anual: porAnual, todos: [porAnual, prom], porProm: [prom] };
    }
    const enJuego = () => T.fechas.some(f => f.partidos.some(p => !jugado(p) && !p.estado));
    const avisoDescenso = () => T.descensos_anulados ? (() => {
      const d = descensos(true);
      return `<p class="nota-edicion">${esc(T.descensos_anulados)} Con el reglamento, hubiesen descendido ${esc(club(d.anual).nombre)}
        (tabla anual) y ${esc(club(d.prom).nombre)} (promedios).</p>`;
    })() : `<p class="leyenda"><span><i class="desciende"></i>${enJuego() ? "Descendería si el año terminara hoy" : "Desciende"}
      (${T.descensos === "tabla" ? (T.descienden === 1 ? "el último de la tabla" : `los ${{ 2: "dos", 3: "tres" }[T.descienden || 2]} últimos de la tabla`) : T.descensos === "promedios" ? (T.descienden === 1 ? "el último de los promedios" : `los ${{ 2: "dos", 3: "tres", 4: "cuatro" }[T.descienden || 2]} últimos de los promedios`) : "uno por la tabla anual y otro por los promedios"})</span>${T.promocion
      ? `<span><i class="promocion"></i>${esc(T.texto_promocion || "Promoción contra un equipo de la B Nacional")} (ver la pestaña ${esc(T.nombre_playoffs || "Playoffs")})</span>` : ""}</p>`;
    // ---- Cupos para las copas del año que viene (T.cupos): a la Libertadores, los campeones del año y los mejores de
    // la tabla anual hasta completar los lugares; a la Sudamericana, los siguientes. Un campeón que ya entra por la
    // tabla libera su lugar para el siguiente, y los que descienden no juegan copas. Los títulos que todavía no se
    // definieron se guardan (su campeón puede ser cualquiera) ----
    function cupos() {
      const c = T.cupos;
      if (!c) return null;
      // cupos fijos (2015: el reparto no seguía la regla), tal cual: [{titulo, club}]
      if (c.fijos) return { ...c, listas: { libertadores: c.libertadores || [], sudamericana: c.sudamericana || [] },
        libertadores: new Set((c.libertadores || []).map(x => x.club)), sudamericana: new Set((c.sudamericana || []).map(x => x.club)) };
      const d = descensos();
      // los campeones "extra" (la Sudamericana) van a la Libertadores por la Conmebol: no ocupan un lugar de la liga
      const deLaLiga = c.campeones.filter(x => !x.extra);
      const campeones = [...new Set(deLaLiga.map(x => x.club).filter(Boolean))];
      const extras = c.campeones.filter(x => x.extra && x.club).map(x => x.club);
      const pendientes = deLaLiga.filter(x => !x.club).length;
      const resto = tablaAnual().map(f => f.id).filter(id => !campeones.includes(id) && !extras.includes(id) && !d.todos.includes(id));
      const porTabla = c.libertadores - campeones.length - pendientes;
      const libertadores = new Set([...campeones, ...extras, ...resto.slice(0, porTabla)]);
      // lugares de la Sudamericana ganados por un torneo (2021: el subcampeón de la Copa Diego Maradona), si no van ya
      // a la Libertadores: le restan lugares a la tabla
      const sudTitulos = (c.sudamericana_titulos || []).map(x => x.club).filter(id => id && !libertadores.has(id));
      const restoSud = resto.slice(porTabla).filter(id => !sudTitulos.includes(id));
      return { ...c, pendientes, porTabla, libertadores,
        sudamericana: new Set([...sudTitulos, ...restoSud.slice(0, c.sudamericana - sudTitulos.length)]) };
    }
    function cuposHTML(cu) {
      if (cu.fijos) return `<div class="cupos">${[["libertadores", "Copa Libertadores"], ["sudamericana", cu.nombre_sudamericana || "Copa Sudamericana"]].filter(([k]) => cu.listas[k].length).map(([k, n]) =>
        `<h4>${n} ${cu["anio_" + k] || cu.anio}</h4><ul class="cupos-campeones">${cu.listas[k].map(x =>
          `<li><span class="cupo-titulo">${esc(x.titulo)}</span>${nombreClub(x.club)}</li>`).join("")}</ul>`).join("")}${cu.nota
          ? `<p class="vacio">${esc(cu.nota)}</p>` : ""}</div>`;
      const titulo = x => `<li><span class="cupo-titulo">${esc(x.titulo)}</span>${x.club ? nombreClub(x.club) : `<span class="vacio">a definir</span>`}${x.extra
        ? ` <span class="vacio">(lugar aparte, no es de la liga)</span>` : ""}</li>`;
      return `<div class="cupos"><h4>Copa Libertadores ${cu.anio}</h4>
        <ul class="cupos-campeones">${cu.campeones.map(titulo).join("")}
          <li><span class="cupo-titulo">${T.anual ? "Tabla anual" : "Tabla"}</span><span>los ${cu.porTabla} mejores que no sean campeones</span></li></ul>
        <h4>Copa Sudamericana ${cu.anio}</h4>${(cu.sudamericana_titulos || []).length
          ? `<ul class="cupos-campeones">${cu.sudamericana_titulos.map(titulo).join("")}</ul>` : ""}
        <p>${(cu.sudamericana_titulos || []).length ? "Y los" : "Los"} ${cu.sudamericana.size - (cu.sudamericana_titulos || []).filter(x => x.club).length} siguientes de la tabla${T.anual ? " anual" : ""}.</p>
        <p class="vacio">Si un campeón ya entra por la tabla${T.anual ? " anual" : ""} (o gana dos títulos), su lugar pasa al siguiente de la tabla.
          Los que descienden no juegan copas.</p>${cu.nota ? `<p class="vacio">${esc(cu.nota)}</p>` : ""}</div>`;
    }
    function vistaAnual() {
      const d = descensos();
      const cu = cupos();
      const anual = tablaAnual();
      // el título del primero de la tabla anual (2025: "Campeón de Liga", lo dio la AFA), cuando terminó el año
      const tituloAnual = T.titulo_anual && !enJuego() ? T.titulo_anual : null;
      const campeonDe = id => (T.cupos?.campeones || []).filter(x => x.club === id && !/^Subcampeón/.test(x.titulo)).map(x => `Campeón de la ${x.titulo}`)
        .concat(tituloAnual && id === anual[0].id ? [tituloAnual] : []);
      const cuerpo = anual.map((f, i) => {
        const dif = f.dif > 0 ? `+${f.dif}` : f.dif;
        const marca = d.todos.includes(f.id) ? "desciende" : d.promo?.includes(f.id) ? "promocion" : cu?.libertadores.has(f.id) ? "libertadores"
          : cu?.sudamericana.has(f.id) ? "sudamericana" : "";
        const titulos = campeonDe(f.id).map(x => ` <span class="campeon-de" title="${esc(x.replace("de la Torneo", "del Torneo"))}">🏆</span>`).join("");
        return `<tr><td class="pos ${marca}">${i + 1}</td><td class="eq">${nombreClub(f.id)}${titulos}</td>
          <td class="pts">${f.pts}</td><td>${f.pj}</td><td class="gol">${f.gf}:${f.gc}</td><td class="dif">${dif}</td>
          <td class="opc">${f.g}</td><td class="opc">${f.e}</td><td class="opc">${f.p}</td></tr>`;
      }).join("");
      const hoy = enJuego() ? " si el año terminara hoy" : "";
      return `<p class="vacio">${esc(T.anual_texto || `Suma la fase de zonas del Torneo Apertura y del Torneo Clausura ${T.anio}.`)}${T.anual ? " Los playoffs no cuentan." : ""}</p>
        ${tituloAnual ? `<p class="campeon-torneo">🏆 ${esc(tituloAnual)}: ${nombreClub(anual[0].id)}${(x => x ? numeroTitulo(x) : "")(TITULOS.find(x => x.texto && x.club === anual[0].id))}
          <small class="vacio">(título que la AFA le dio al primero de la tabla anual)</small></p>` : ""}
        ${cu ? cuposHTML(cu) : ""}
        <div class="grupo tabla-larga"><table><thead><tr><th>#</th><th class="eq">Equipo</th><th>Pts</th><th>J</th><th class="gol">Gol</th><th>+/-</th>
          <th class="opc">G</th><th class="opc">E</th><th class="opc">P</th></tr></thead><tbody>${cuerpo}</tbody></table></div>
        ${cu ? `<p class="leyenda">${cu.libertadores.size ? `<span><i class="libertadores"></i>Copa Libertadores ${cu.anio}${hoy}</span>` : ""}
          ${cu.sudamericana.size ? `<span><i class="sudamericana"></i>${esc(cu.nombre_sudamericana || "Copa Sudamericana")} ${cu.anio_sudamericana || cu.anio}${hoy}</span>` : ""}<span>🏆 Campeón del año</span></p>` : ""}
        ${T.descensos || T.descensos_anulados ? avisoDescenso() : ""}
        ${T.sin_descensos ? `<p class="nota-edicion">${esc(T.sin_descensos)}</p>` : ""}
        ${T.desempate ? `<h3>Desempate${T.desempate_texto ? "" : " por el descenso"}</h3><p class="vacio">${T.desempate_texto ? esc(T.desempate_texto)
          : `${esc(club(T.desempate.local).nombre)} y ${esc(club(T.desempate.visitante).nombre)} terminaron empatados en puntos en la tabla anual,
          en el lugar del descenso: lo definieron en un partido, en cancha neutral. Bajó el que perdió.`}</p>${partidoHTML(T.desempate)}` : ""}`;
    }
    function vistaPromedios() {
      const d = descensos();
      const temporada = t => t ? t[0] : "–";
      const cuerpo = promedios().map((f, i) => `<tr><td class="pos ${d.porProm.includes(f.id) ? "desciende" : d.promo?.includes(f.id) ? "promocion" : ""}">${i + 1}</td>
        <td class="eq">${nombreClub(f.id)}</td>${f.temporadas.map(t => `<td class="opc" title="${t ? (T.promedios_por_temporada ? "Puntos de la temporada" : `${t[1]} partidos`) : "No jugó en Primera"}">${temporada(t)}</td>`).join("")}
        <td>${f.pts}</td><td>${f.pj}</td><td class="pts">${T.promedios_por_temporada ? f.prom.toFixed(2).replace(".", ",")
          : (Math.floor(f.prom * 1000 + 1e-9) / 1000).toFixed(3).replace(".", ",")}</td></tr>`).join("");
      const actual = T.temporada || T.anio;
      return `<p class="vacio">Los puntos de las temporadas ${[...aniosProm, actual].join(", ")} divididos por ${T.promedios_por_temporada
        ? "la cantidad de temporadas que cada club jugó en Primera (no por los partidos: las temporadas no tuvieron todas los mismos partidos)" : "los partidos jugados"}
        (la de ${actual} es ${T.temporada ? "este torneo" : "la tabla anual"}).${T.promedios_victoria
        ? ` Para los promedios, cada partido ganado valía ${T.promedios_victoria} puntos (en los torneos ya valía 3).` : ""}${T.promedios_por_temporada
        ? " Los que subieron hace poco dividen solo por las temporadas que jugaron en Primera."
        : " Los que subieron hace poco dividen solo por los partidos que jugaron en Primera. El promedio va con tres decimales, sin redondear (como lo publica la AFA)."}</p>
        <div class="grupo tabla-larga"><table><thead><tr><th>#</th><th class="eq">Equipo</th>${[...aniosProm, actual].map(a => `<th class="opc">${a}</th>`).join("")}
          <th>Pts</th><th>${T.promedios_por_temporada ? `<span title="Temporadas">Temp.</span>` : "J"}</th><th>Prom.</th></tr></thead><tbody>${cuerpo}</tbody></table></div>
        ${T.descensos || T.descensos_anulados ? avisoDescenso() : ""}
        ${T.sin_descensos && !T.anual && !T.cupos ? `<p class="nota-edicion">${esc(T.sin_descensos)}</p>` : ""}`;
    }

    // ---- Un partido ----
    // conDia: poner el día en cada partido (en las fechas no hace falta: van agrupados por día)
    function partidoHTML(p, conDia = true) {
      const res = jugado(p) ? `${p.gl} – ${p.gv}` : p.estado ? esc(p.estado) : p.hora ? `${p.hora} h` : "vs";
      // (en los torneos por etapas, las zonas de la etapa de esa fecha)
      const zd = T.etapas ? zonaEtapa[p.n] || {} : zonaDe;
      const interzonal = p.n != null && zd[p.local] && zd[p.visitante] && zd[p.local] !== zd[p.visitante];
      const meta = [conDia && (p.fecha ? fechaLarga(p.fecha) : "Día a confirmar"), jugado(p) && p.hora && `${p.hora} h`, p.estadio, p.arbitro && `Árbitro: ${p.arbitro}`,
        p.publico && `${p.publico.toLocaleString("es-AR")} espectadores`, p.alargue && "Con alargue", p.nota].filter(Boolean).map(esc).join(" · ");
      const gol = g => {
        const min = g.min != null ? `${g.min}${g.extra ? "+" + g.extra : ""}' ` : "";
        const texto = `${min}${esc(g.jugador || "?")}${g.tipo === "pen" ? " (penal)" : g.tipo === "ec" ? " (en contra)" : ""}`;
        const asis = g.asistencia ? `<small class="gol-asist">asist. ${esc(g.asistencia)}</small>` : "";
        return `<li>${g.equipo === "visitante" ? `⚽ ${texto}` : `${texto} ⚽`}${asis}</li>`;
      };
      const goles = (p.goles || []).length ? `<div class="goles-partido">${["local", "visitante"].map(l =>
        `<ul class="goles${l === "local" ? " goles-local" : ""}">${p.goles.filter(g => g.equipo === l).map(gol).join("")}</ul>`).join("")}</div>` : "";
      const pen = p.pen_l != null ? `<div class="partido-meta penales">Penales: ${p.pen_l} – ${p.pen_v}</div>` : "";
      return `<article class="partido${jugado(p) ? "" : " sin-jugar"}">
        <div class="partido-meta">${meta}${interzonal ? ` · <span class="etiqueta">Interzonal</span>` : ""}</div>
        <div class="marcador"><span class="local">${esc(club(p.local).nombre)}${escudo(p.local)}</span>
          <span class="resultado">${res}</span><span>${nombreClub(p.visitante)}</span></div>
        ${goles}${pen}</article>`;
    }

    // ---- Fechas: una a la vez, con flechas. Arranca en la que se está jugando (la primera con partidos sin jugar) ----
    const fechaActual = () => (T.fechas.find(f => f.partidos.some(p => !jugado(p) && !p.estado)) || T.fechas.at(-1))?.numero;
    let fechaVista = +PARAMS.get("fecha") || fechaActual();
    function vistaFechas() {
      const f = T.fechas.find(x => x.numero === fechaVista) || T.fechas[0];
      const dias = [...new Set(f.partidos.map(p => p.fecha).filter(Boolean))].sort();
      const rango = dias.length ? (dias.length > 1 ? `del ${fechaCorta(dias[0])} al ${fechaCorta(dias.at(-1))}` : `el ${fechaCorta(dias[0])}`) : "días a confirmar";
      const jugados = f.partidos.filter(jugado).length;
      const botones = T.fechas.map(x => `<button class="orden" type="button" data-fecha="${x.numero}" aria-pressed="${x.numero === f.numero}"
        title="Fecha ${x.numero}">${x.numero}</button>`).join("");
      // los partidos, separados por día (los postergados que se jugaron más tarde quedan en su fecha, con su día)
      const porDia = {};
      [...f.partidos].sort((a, b) => (a.fecha || "9").localeCompare(b.fecha || "9") || (a.hora || "").localeCompare(b.hora || ""))
        .forEach(p => (porDia[p.fecha || ""] ||= []).push(p));
      const cuerpo = Object.entries(porDia).map(([d, ps]) =>
        `<h4 class="fecha-grupo">${d ? fechaLarga(d).replace(/^./, c => c.toUpperCase()) : "Día y hora a confirmar"}</h4>${ps.map(p => partidoHTML({ ...p, n: f.numero }, false)).join("")}`).join("");
      return `<div class="orden-partidos elegir-fecha">Fecha: ${botones}</div>
        <div class="titulo-fecha">
          <button class="flecha-anio" type="button" data-fecha="${f.numero - 1}" ${f.numero > 1 ? "" : "disabled"} aria-label="Fecha anterior">◀</button>
          <h3>Fecha ${f.numero}${T.etapas ? ` · ${esc(T.etapas.filter(et => et.fechas.includes(f.numero)).map(et => et.nombre).join(" y "))}` : ""} <small>${rango} · ${jugados === f.partidos.length ? "terminada" : `${jugados} de ${f.partidos.length} partidos jugados`}</small></h3>
          <button class="flecha-anio" type="button" data-fecha="${f.numero + 1}" ${f.numero < T.fechas.length ? "" : "disabled"} aria-label="Fecha siguiente">▶</button>
        </div>${cuerpo}`;
    }

    // ---- Cuadro de los playoffs (todos a un partido). Se arma desde la última ronda que tiene partidos hacia atrás:
    // arriba de cada partido, el de la ronda anterior de su primer equipo, y abajo el del segundo. Las rondas que
    // todavía no se jugaron quedan con casillas vacías ("a definir") ----
    const ganador = p => p.gana !== undefined ? p.gana : p.gl == null ? null : p.gl > p.gv || p.gl === p.gv && p.pen_l > p.pen_v ? p.local
      : p.gl < p.gv || p.pen_v > p.pen_l ? p.visitante : null;
    function cuadroHTML() {
      // Un cuadro armado a mano (T.cuadro: la Copa Maradona 2020), en partes ("bloques"), cada una con sus columnas
      // de rondas. El campeón, marcado en la parte de la final
      if (T.cuadro) {
        // (cada columna, con los cruces de sus rondas: las series de ida y vuelta, juntas)
        const cruces = n => series(T.playoffs.find(r => r.nombre === n)?.partidos || []);
        return T.cuadro.bloques.map(([titulo, columnas]) => {
          const final = columnas.flat().includes("Final");
          return `<h4 class="bloque-cuadro">${esc(titulo)}${final && campeon ? ` <span class="campeon-bloque">🏆 Campeón: ${nombreClub(campeon)}</span>` : ""}</h4>
            ${dibujarCuadro(columnas.map(rondas => { const ps = rondas.flatMap(cruces); return ps.length ? ps : [null]; }),
              columnas.map(rondas => rondas.join(" / ")))}`;
        }).join("");
      }
      // (desde la ronda en que el cuadro es parejo: en la Copa de la Superliga 2019, octavos; la primera ronda no,
      // porque 6 entraron directo en octavos)
      const desde = T.playoffs.findIndex(r => r.nombre === T.cuadro_desde);
      const rondas = T.playoffs.slice(Math.max(0, desde)).map(r => ({ ...r, partidos: series(r.partidos) }));
      const ultima = rondas.at(-1);
      const niveles = [[...ultima.partidos].sort((a, b) => (a.fecha || "").localeCompare(b.fecha || ""))];
      for (let r = rondas.length - 2; r >= 0; r--) {
        const antes = rondas[r].partidos, usados = new Set();
        const nivel = niveles[0].flatMap(p => (p ? [p.local, p.visitante] : [null, null]).map(id => {
          const q = id && antes.find(q => !usados.has(q) && (q.local === id || q.visitante === id));
          if (q) usados.add(q);
          return q || null;
        }));
        // (los que no se pudieron ubicar, en los huecos)
        const sueltos = antes.filter(q => !usados.has(q));
        niveles.unshift(nivel.map(q => q || sueltos.shift() || null));
      }
      const NOMBRES = { 8: "Octavos de final", 4: "Cuartos de final", 2: "Semifinales", 1: "Final" };
      const nombres = rondas.map(r => r.nombre);
      while (niveles.at(-1).length > 1) {   // las rondas que faltan
        niveles.push(Array(niveles.at(-1).length / 2).fill(null));
        nombres.push(NOMBRES[niveles.at(-1).length] || "");
      }
      return dibujarCuadro(niveles, nombres);
    }
    // Series de ida y vuelta (T.ida_y_vuelta): los dos partidos de cada cruce, juntos, con el global. Si queda igual,
    // pasa el que hizo más goles de visitante (T.gol_visitante) y, si no, el que ganó los penales de la vuelta (o el de
    // la ventaja deportiva)
    function series(partidos) {
      if (!T.ida_y_vuelta) return partidos;
      const grupos = {};
      [...partidos].sort((a, b) => (a.fecha || "").localeCompare(b.fecha || ""))
        .forEach(p => (grupos[[p.local, p.visitante].sort().join("|")] ||= []).push(p));
      return Object.values(grupos).map(ps => {
        if (ps.length < 2) return ps[0];
        const [ida, vuelta] = ps;
        const s = { local: ida.local, visitante: ida.visitante, fecha: vuelta.fecha, serie: [ida, vuelta] };
        if (!jugado(ida) || !jugado(vuelta)) return { ...s, gana: null };
        s.gl = ida.gl + vuelta.gv; s.gv = ida.gv + vuelta.gl;
        if (vuelta.pen_l != null) { s.pen_l = vuelta.pen_v; s.pen_v = vuelta.pen_l; }
        // goles de visitante: el local de la ida los hizo en la vuelta, y al revés
        const fuera = T.gol_visitante ? vuelta.gv - ida.gv : 0;
        s.gana = s.gl !== s.gv ? (s.gl > s.gv ? s.local : s.visitante) : fuera ? (fuera > 0 ? s.local : s.visitante)
          : s.pen_l != null ? (s.pen_l > s.pen_v ? s.local : s.visitante)
          // (vuelta.pasa: el que pasó con el global igualado, por haber terminado mejor; la Liguilla 1988-89)
          : vuelta.pasa ? vuelta.pasa
          // (la Promoción 2012: con el global igualado se quedaba el de Primera, T.ventaja)
          : (T.ventaja || []).find(id => id === s.local || id === s.visitante) || null;
        return s;
      });
    }
    // niveles: los partidos de cada columna; nombres: el título de cada columna; titulos: el de cada partido (opcional)
    function dibujarCuadro(niveles, nombres, titulos = []) {
      const llave = p => {
        if (!p) return `<div class="llave llave-vacia"><div class="ll-eq"><span class="ll-nombre vacio">A definir</span></div>
          <div class="ll-eq"><span class="ll-nombre vacio">A definir</span></div></div>`;
        const gana = ganador(p);
        const fila = (id, g, pen) => `<div class="ll-eq${id === gana ? " gana" : ""}" title="${esc(club(id).nombre)}">
          <span class="ll-nombre">${nombreClub(id)}</span><span class="ll-total">${g ?? "–"}${pen != null ? ` <small>(${pen})</small>` : ""}</span></div>`;
        const detalle = p.serie ? p.serie.map((q, i) => `${i ? "Vuelta" : "Ida"}: ${club(q.local).nombre} ${q.gl ?? ""}–${q.gv ?? ""} ${club(q.visitante).nombre}`).join(" · ")
          : [p.fecha && fechaLarga(p.fecha), p.estadio, p.alargue && "con alargue"].filter(Boolean).join(" · ");
        return `<div class="llave" title="${esc(detalle)}">${fila(p.local, p.gl, p.pen_l)}${fila(p.visitante, p.gv, p.pen_v)}</div>`;
      };
      const columnas = niveles.map((nivel, n) => {
        const casillas = nivel.map((p, i) => `<div class="casilla">${titulos[n]?.[i]
          ? `<div class="llave-con-titulo"><div class="llave-titulo">${esc(titulos[n][i])}</div>${llave(p)}</div>` : llave(p)}</div>`);
        // (de a pares, con el corchete hacia la ronda siguiente; uno solo va derecho, con una línea)
        const cuerpo = n === niveles.length - 1 ? casillas.join("")
          : nivel.length === 1 ? `<div class="par vacio">${casillas[0]}</div>`
          : casillas.reduce((h, c, i) => i % 2 ? h + c + "</div>" : h + `<div class="par">` + c, "");
        return `<div class="ronda"><div class="ronda-titulo">${esc(nombres[n])}</div><div class="ronda-cuerpo">${cuerpo}</div></div>`;
      });
      return `<div class="cuadro-scroll"><div class="cuadro">${columnas.join("")}</div></div>`;
    }

    // ---- Playoffs: el cuadro y los partidos; si todavía no empezaron, cómo serían los cruces si la fase regular
    // terminara hoy ----
    function vistaPlayoffs() {
      // (T.pasan_triangular: los que pasaban, como los dos que fueron a la Libertadores en el Nacional 1974)
      if (tri) return `${tablaHTML("", { "": clubesTri }, T.pasan_triangular || 0, tri, 0, false, !T.campeon_etapa)}<p class="vacio">${esc(T.texto_triangular || "")}</p>` +
        T.playoffs.map(r => `<h3>Partidos</h3>${r.partidos.map(p => partidoHTML(p)).join("")}`).join("");
      if (T.playoffs.length) return (!T.fechas.length && T.nota ? `<p class="nota-edicion">${esc(T.nota)}</p>` : "") +
        `${cuadroHTML()}<p class="vacio">${T.ida_y_vuelta
          ? "El que pasó cada serie, resaltado, con el global de los dos partidos (pasando el mouse, la ida y la vuelta)"
          : "El ganador de cada partido, resaltado"};
        entre paréntesis, los penales.${T.cuadro?.nota ? " " + esc(T.cuadro.nota) : ""}</p>` +
        T.playoffs.map(r => `<h3>${esc(r.nombre)}</h3>${r.partidos.map(p => partidoHTML(p)).join("")}`).join("");
      const [za, zb] = Object.keys(T.zonas);
      const a = tabla(T.zonas[za]), b = tabla(T.zonas[zb]);
      const cruces = [];
      // 1º de una zona contra el último que pasa de la otra (con 8: 1º-8º, 2º-7º, 3º-6º y 4º-5º)
      for (let i = 0; i < T.pasan / 2; i++) cruces.push([a[i], b[T.pasan - 1 - i], za, zb, i], [b[i], a[T.pasan - 1 - i], zb, za, i]);
      const fila = ([x, y, zx, zy, i]) => `<li class="cruce"><span class="local">${esc(club(x.id).nombre)}${escudo(x.id)} <small>${i + 1}º ${zx}</small></span>
        <span class="resultado">vs</span><span><small>${T.pasan - i}º ${zy}</small> ${nombreClub(y.id)}</span></li>`;
      return `<p class="nota-edicion">Los playoffs empiezan cuando termine la fase regular (fecha ${T.fechas.length}). Son a un solo partido,
        en la cancha del mejor ubicado. <strong>Si la fase regular terminara hoy</strong>, ${RONDA[T.pasan] || "los cruces"} serían:</p>
        <ul class="cruces">${cruces.filter((_, k) => k % 2 === 0).concat(cruces.filter((_, k) => k % 2 === 1)).map(fila).join("")}</ul>`;
    }

    // ---- Goleadores (se cuentan con los goles de cada partido; los goles en contra no suman) ----
    function vistaGoleadores() {
      const g = {};
      todos.concat(T.playoffs.flatMap(r => r.partidos)).forEach(p => (p.goles || []).forEach(x => {
        if (x.tipo === "ec" || !x.jugador) return;
        const id = x.jid || x.jugador;
        const eq = x.equipo === "visitante" ? p.visitante : p.local;
        const f = g[id] ||= { nombre: x.jugador, eq, goles: 0, pen: 0 };
        f.goles++; if (x.tipo === "pen") f.pen++;
      }));
      const filas = Object.values(g).sort((a, b) => b.goles - a.goles || a.pen - b.pen || a.nombre.localeCompare(b.nombre));
      let pos = 0;
      const cuerpo = filas.slice(0, 40).map((f, i) => {
        if (!i || f.goles !== filas[i - 1].goles) pos = i + 1;
        return `<tr><td class="pos">${pos}</td><td class="eq">${esc(f.nombre)}</td><td class="eq club-goleador">${nombreClub(f.eq)}</td>
          <td class="pts">${f.goles}</td><td class="opc">${f.pen || ""}</td></tr>`;
      }).join("");
      // partidos jugados de los que ESPN no tiene todos los goles (el Clausura 2003): la lista queda incompleta
      // (p.sin_goles: un partido dado por ganado en el escritorio, sin goles de verdad)
      const faltan = todos.concat(T.playoffs.flatMap(r => r.partidos)).filter(p => jugado(p) && !p.estado && !p.sin_goles
        && (p.goles || []).length < p.gl + p.gv).length;
      const aviso = faltan ? `<p class="nota-edicion">Faltan los goles de ${faltan} partido${faltan > 1 ? "s" : ""}: la lista está
        incompleta.${T.goleadores_nota ? " " + esc(T.goleadores_nota) : ""}</p>`
        : T.goleadores_nota ? `<p class="vacio">${esc(T.goleadores_nota)}</p>` : "";
      return aviso + (filas.length ? `<div class="grupo goleadores"><table><thead><tr><th>#</th><th class="eq">Jugador</th><th class="eq">Club</th><th>Goles</th>
        <th class="opc" title="De penal">Pen.</th></tr></thead><tbody>${cuerpo}</tbody></table></div>` : faltan ? "" : `<p class="vacio">Todavía no hay goles.</p>`);
    }

    // ---- Asistidores: el que dio el pase de cada gol (ESPN lo tiene desde el Inicial 2013; viene solo el nombre, y el
    // club es el del que hizo el gol) ----
    const conAsistencia = todos.concat(T.playoffs.flatMap(r => r.partidos)).flatMap(p => (p.goles || [])
      .filter(x => x.asistencia && x.tipo !== "ec").map(x => ({ nombre: x.asistencia, eq: x.equipo === "visitante" ? p.visitante : p.local })));
    function vistaAsistidores() {
      const a = {};
      conAsistencia.forEach(x => { (a[`${x.eq}|${x.nombre}`] ||= { ...x, asist: 0 }).asist++; });
      const filas = Object.values(a).sort((x, y) => y.asist - x.asist || x.nombre.localeCompare(y.nombre));
      let pos = 0;
      const cuerpo = filas.slice(0, 40).map((f, i) => {
        if (!i || f.asist !== filas[i - 1].asist) pos = i + 1;
        return `<tr><td class="pos">${pos}</td><td class="eq">${esc(f.nombre)}</td><td class="eq club-goleador">${nombreClub(f.eq)}</td>
          <td class="pts">${f.asist}</td></tr>`;
      }).join("");
      return `<div class="grupo goleadores"><table><thead><tr><th>#</th><th class="eq">Jugador</th><th class="eq">Club</th>
        <th title="Asistencias">Asist.</th></tr></thead><tbody>${cuerpo}</tbody></table></div>`;
    }

    // ---- Pestañas ----
    // las pestañas que tiene este torneo (sin fase regular, la Copa de la Superliga 2019: el cuadro y los goleadores;
    // con cupos pero sin tabla anual, las Superligas: la de la tabla anual es la de las copas y el descenso)
    const hay = v => (v !== "tabla" && v !== "fechas" || T.fechas.length) && (v !== "promedios" || T.promedios)
      && (v !== "anual" || T.anual || T.cupos) && (v !== "playoffs" || T.pasan || T.playoffs.length)
      && (v !== "asistidores" || conAsistencia.length);   // las asistencias, solo desde el Inicial 2013
    const nombreVista = (v, n) => v === "anual" && T.nombre_anual ? T.nombre_anual : v === "anual" && !T.anual ? "Copas y descenso" : v === "playoffs" && !T.fechas.length ? "Cuadro y partidos"
      : v === "playoffs" && T.nombre_playoffs ? T.nombre_playoffs : n;
    const inicial = T.fechas.length ? "tabla" : "playoffs";
    let vista = VISTAS.some(([v]) => v === PARAMS.get("vista") && hay(v)) ? PARAMS.get("vista") : inicial;
    function dibujar(guardar) {
      if (guardar) {
        const q = new URLSearchParams({ torneo: CLAVE });
        if (vista !== inicial) q.set("vista", vista);
        if (vista === "fechas") q.set("fecha", fechaVista);
        history.pushState({ vista, fechaVista }, "", `?${q}`);
      }
      const html = { tabla: vistaTabla, fechas: vistaFechas, playoffs: vistaPlayoffs, anual: vistaAnual, promedios: vistaPromedios,
        goleadores: vistaGoleadores, asistidores: vistaAsistidores }[vista]();
      ligaEl.innerHTML = `<div class="pestanas" role="tablist">${VISTAS.filter(([v]) => hay(v)).map(([v, n]) =>
        `<button class="pestana" type="button" role="tab" data-vista="${v}" aria-selected="${v === vista}">${nombreVista(v, n)}</button>`).join("")}</div>${html}`;
    }
    ligaEl.addEventListener("click", e => {
      const b = e.target.closest("button");
      if (!b || b.disabled) return;
      if (b.dataset.vista) vista = b.dataset.vista;
      else if (b.dataset.fecha) fechaVista = +b.dataset.fecha;
      else return;
      dibujar(true);
    });
    window.addEventListener("popstate", e => {
      const q = new URLSearchParams(location.search);
      vista = q.get("vista") || inicial;
      fechaVista = +q.get("fecha") || fechaActual();
      dibujar();
    });
    dibujar();
  }
})();
