/* Lógica de la página. Los datos viven en data/ (window.LIB). Versión funcional provisoria: el diseño se define después. */
(function () {
  const LIB = window.LIB;
  const URL_SITIO = "https://santino-uncal.github.io/FULBO/";   // dirección publicada en GitHub Pages
  const navEl = document.getElementById("ediciones");
  const edicionEl = document.getElementById("edicion");

  // Carga data/ediciones/<año>.js una sola vez (funciona también abriendo index.html con doble clic)
  function cargarEdicion(anio) {
    if (LIB.ediciones && LIB.ediciones[anio]) return Promise.resolve(LIB.ediciones[anio]);
    return new Promise((ok, error) => {
      const s = document.createElement("script");
      s.src = `data/ediciones/${anio}.js`;
      s.onload = () => ok(LIB.ediciones[anio]);
      s.onerror = () => error(new Error(`No se encontró la edición ${anio}`));
      document.body.appendChild(s);
    });
  }

  const esc = t => String(t ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const equipo = id => LIB.equipos[id] || { nombre: id || "?" };

  function escudo(id) {
    const e = equipo(id);
    if (!e.escudo) return "";
    // Si el escudo todavía no se descargó, la imagen se oculta sola
    return `<img class="escudo" src="${e.escudo}" alt="" loading="lazy" onerror="this.remove()">`;
  }
  const club = id => `${escudo(id)}${esc(equipo(id).nombre)}`;

  // Goleadores y asistidores se calculan a partir de los goles de cada partido
  function ranking(ed, tipo) {
    const cuenta = {};
    ed.fases.forEach(f => f.partidos.forEach(p => (p.goles || []).forEach(g => {
      if (tipo === "goles" && g.tipo === "ec") return;          // los goles en contra no suman al goleador
      const nombre = tipo === "goles" ? g.jugador : g.asistencia;
      if (!nombre) return;
      const id = tipo === "goles" ? g.jid : g.aid;
      const eq = p[g.equipo];
      const clave = id || `${nombre}|${eq}`;
      cuenta[clave] = cuenta[clave] || { nombre, equipo: eq, n: 0 };
      cuenta[clave].n++;
    })));
    return Object.values(cuenta).sort((a, b) => b.n - a.n || a.nombre.localeCompare(b.nombre)).slice(0, 15);
  }

  function tablaRanking(titulo, filas) {
    if (!filas.length) return "";
    return `<h3>${titulo}</h3><table><thead><tr><th>Jugador</th><th>Equipo</th><th class="num">Cant.</th></tr></thead><tbody>` +
      filas.map(r => `<tr><td>${esc(r.nombre)}</td><td>${club(r.equipo)}</td><td class="num">${r.n}</td></tr>`).join("") +
      `</tbody></table>`;
  }

  function textoGol(g, p) {
    const min = g.min != null ? `${g.min}${g.extra ? "+" + g.extra : ""}' ` : "";
    const tipo = g.tipo === "pen" ? " (penal)" : g.tipo === "ec" ? " (en contra)" : "";
    const asis = g.asistencia ? ` — asist. ${esc(g.asistencia)}` : "";
    return `<li>⚽ ${min}${esc(g.jugador || "?")}${tipo} <span class="gol-eq">(${esc(equipo(p[g.equipo]).nombre)})</span>${asis}</li>`;
  }

  function partido(p) {
    const res = p.gl == null ? "vs" : `${p.gl} – ${p.gv}`;
    const pen = p.pen_l != null ? `<div class="partido-meta">Penales: ${p.pen_l} – ${p.pen_v}</div>` : "";
    const meta = [p.fecha, p.estadio, p.arbitro && `Árbitro: ${p.arbitro}`, p.publico && `${p.publico.toLocaleString("es-AR")} espectadores`]
      .filter(Boolean).map(esc).join(" · ");
    const nota = p.notas ? `<div class="partido-meta">Nota: ${esc(p.notas)}</div>` : "";
    return `<article class="partido">
      <div class="partido-meta">${meta}</div>
      <div class="marcador">
        <span class="local">${esc(equipo(p.local).nombre)}${escudo(p.local)}</span>
        <span class="resultado">${res}</span>
        <span>${club(p.visitante)}</span>
      </div>${pen}${nota}
      <ul class="goles">${(p.goles || []).map(g => textoGol(g, p)).join("")}</ul>
    </article>`;
  }

  function planteles(ed) {
    const ids = Object.keys(ed.planteles || {}).sort((a, b) => equipo(a).nombre.localeCompare(equipo(b).nombre));
    if (!ids.length) return "";
    return `<h3>Planteles</h3><p class="vacio">Jugadores que aparecen en formaciones o goles de esta edición.</p>` +
      ids.map(id => `<details class="plantel"><summary>${club(id)} (${ed.planteles[id].length})</summary>
        <table><thead><tr><th>#</th><th>Jugador</th><th>Pos.</th><th class="num">PJ</th><th class="num">Goles</th><th class="num">Asist.</th></tr></thead><tbody>
        ${ed.planteles[id].map(j => `<tr><td>${esc(j.num || "")}</td><td>${esc(j.nombre)}</td><td>${esc(j.pos || "")}</td>
          <td class="num">${j.pj || 0}</td><td class="num">${j.goles || 0}</td><td class="num">${j.asist || 0}</td></tr>`).join("")}
        </tbody></table></details>`).join("");
  }

  // ---- Tablas de grupos (se calculan a partir de los partidos) ----

  // Agrupa las fases tipo "Fase de grupos — Grupo A" por etapa ("Fase de grupos") y averigua a qué fase se pasa
  function etapasDeGrupos(ed) {
    const etapas = [];
    ed.fases.forEach((f, i) => {
      const m = f.nombre.match(/^(.*) — Grupo (\S+)$/);   // los "— Desempate" quedan afuera
      if (!m) return;
      let etapa = etapas.find(e => e.nombre === m[1]);
      if (!etapa) etapas.push(etapa = { nombre: m[1], grupos: [], ultima: i });
      etapa.grupos.push({ letra: m[2], partidos: f.partidos });
      etapa.ultima = i;
    });
    etapas.forEach(e => {
      // La fase siguiente es la primera que viene después y no es de esta misma etapa
      const sig = ed.fases.slice(e.ultima + 1).find(f => !f.nombre.startsWith(e.nombre));
      e.siguiente = sig ? sig.nombre.replace(/ — .*$/, "") : null;
      // Pasan los que juegan la etapa siguiente (puede ser, a su vez, varios grupos)
      const siguientes = sig ? ed.fases.filter(f => f.nombre.replace(/ — .*$/, "") === e.siguiente) : [];
      e.pasan = new Set(siguientes.flatMap(f => f.partidos.flatMap(p => [p.local, p.visitante])));
      e.grupos.sort((a, b) => a.letra.localeCompare(b.letra, "es", { numeric: true }));
    });
    return etapas;
  }

  // Ediciones sin grupos (1960, 1961): cada llave de ida y vuelta se definía por puntos, como un grupo de 2
  function etapasDeLlaves(ed) {
    return ed.fases.map((f, i) => {
      const llaves = {};
      f.partidos.forEach(p => (llaves[p.llave ?? `${p.local}|${p.visitante}`] ||= []).push(p));
      const sig = ed.fases[i + 1];
      const pasan = sig ? sig.partidos.flatMap(p => [p.local, p.visitante]) : [ed.campeon];
      return {
        nombre: f.nombre, siguiente: sig ? sig.nombre : null, campeon: !sig, pasan: new Set(pasan),
        grupos: Object.values(llaves).map(ps => ({
          titulo: `${equipo(ps[0].local).nombre} – ${equipo(ps[0].visitante).nombre}`, partidos: ps
        }))
      };
    });
  }

  function tablaDeGrupo(partidos, anio) {
    const ptsVictoria = anio >= 1995 ? 3 : 2;   // hasta 1994 la victoria valía 2 puntos
    const t = {};
    const fila = id => t[id] = t[id] || { id, pj: 0, g: 0, e: 0, p: 0, gf: 0, gc: 0, ultimos: [] };
    [...partidos].sort((a, b) => (a.fecha || "").localeCompare(b.fecha || "")).forEach(p => {
      const l = fila(p.local), v = fila(p.visitante);
      if (p.gl == null || p.gv == null) return;   // partido sin jugar
      [[l, p.gl, p.gv, p.visitante], [v, p.gv, p.gl, p.local]].forEach(([f, a, b, rival]) => {
        f.pj++; f.gf += a; f.gc += b;
        const r = a > b ? "V" : a < b ? "D" : "E";
        f[{ V: "g", E: "e", D: "p" }[r]]++;
        f.ultimos.push({ r, texto: `${equipo(p.local).nombre} ${p.gl}–${p.gv} ${equipo(p.visitante).nombre}${p.fecha ? " (" + p.fecha + ")" : ""}` });
      });
    });
    return Object.values(t).map(f => ({ ...f, pts: f.g * ptsVictoria + f.e, dif: f.gf - f.gc }));
  }

  function grupoHTML(grupo, etapa, anio) {
    const filas = tablaDeGrupo(grupo.partidos, anio).sort((a, b) =>
      b.pts - a.pts || b.dif - a.dif || b.gf - a.gf ||
      etapa.pasan.has(b.id) - etapa.pasan.has(a.id) ||          // desempates que no se ven en la tabla
      equipo(a.id).nombre.localeCompare(equipo(b.id).nombre));
    const hayResultados = filas.some(f => f.pj);
    const cuerpo = filas.map((f, i) => {
      let marca = "";
      if (hayResultados && etapa.pasan.has(f.id)) marca = etapa.campeon ? "campeon" : "pasa";
      else if (hayResultados && anio >= 2017 && etapa.nombre === "Fase de grupos" && i === 2) marca = "sudamericana";
      const dif = f.dif > 0 ? `+${f.dif}` : f.dif;
      const ultimos = f.ultimos.slice(-5).reverse().map(u => `<span class="res res-${u.r}" title="${esc(u.texto)}">${u.r}</span>`).join("");
      return `<tr>
        <td class="pos ${marca}">${i + 1}</td>
        <td class="eq">${club(f.id)}</td>
        <td class="pts">${f.pts}</td><td>${f.pj}</td><td>${f.gf}:${f.gc}</td>
        <td class="dif ${f.dif > 0 ? "pos-dif" : f.dif < 0 ? "neg-dif" : ""}">${dif}</td>
        <td class="opc">${f.g}</td><td class="opc">${f.e}</td><td class="opc">${f.p}</td>
        <td class="ultimas" title="El más reciente a la izquierda">${ultimos}</td>
      </tr>`;
    }).join("");
    return `<div class="grupo">
      <h4>${esc(grupo.titulo || `Grupo ${grupo.letra}`)}</h4>
      <table>
        <thead><tr><th>#</th><th class="eq">Equipo</th><th>Pts</th><th>J</th><th>Gol</th><th>+/-</th>
          <th class="opc">G</th><th class="opc">E</th><th class="opc">P</th><th class="ultimas">Últimas</th></tr></thead>
        <tbody>${cuerpo}</tbody>
      </table>
    </div>`;
  }

  function gruposHTML(ed) {
    const conGrupos = etapasDeGrupos(ed);
    const etapas = conGrupos.length ? conGrupos : etapasDeLlaves(ed);
    return etapas.map(etapa => {
      const leyenda = [
        etapa.siguiente && `<span><i class="pasa"></i>Clasificación a ${esc(etapa.siguiente)}</span>`,
        etapa.campeon && `<span><i class="campeon"></i>Campeón</span>`,
        ed.anio >= 2017 && etapa.nombre === "Fase de grupos" && `<span><i class="sudamericana"></i>Pasa a la Copa Sudamericana</span>`
      ].filter(Boolean).join("");
      return `<h3>${esc(etapa.nombre)}</h3>
        <div class="grupos">${etapa.grupos.map(g => grupoHTML(g, etapa, ed.anio)).join("")}</div>
        <p class="leyenda">${leyenda}</p>`;
    }).join("");
  }

  function mostrar(ed) {
    let html = `<h2>${ed.anio}</h2>
      <p>🏆 Campeón: <strong>${ed.campeon ? club(ed.campeon) : "—"}</strong> · Subcampeón: ${ed.subcampeon ? club(ed.subcampeon) : "—"}</p>
      <p class="vacio">Fuentes: ${ed.fuentes.join(" + ")}</p>`;
    // La final (y su desempate, si hubo) va arriba de todo
    const esFinal = f => f.nombre.startsWith("Final");
    ed.fases.filter(esFinal).forEach(f => {
      html += `<h3>${esc(f.nombre)}</h3>` + f.partidos.map(partido).join("");
    });
    html += gruposHTML(ed);
    html += tablaRanking("Goleadores", ranking(ed, "goles"));
    html += tablaRanking("Asistidores", ranking(ed, "asistencias"));
    // El resto de las fases, de la más importante a la primera
    [...ed.fases].reverse().filter(f => !esFinal(f)).forEach(f => {
      html += `<details class="fase"><summary>${esc(f.nombre)} (${f.partidos.length})</summary>` +
        f.partidos.map(partido).join("") + `</details>`;
    });
    html += planteles(ed);
    edicionEl.innerHTML = html;
  }

  // Título y descripción de cada edición (lo que muestra Google en el resultado de búsqueda)
  function actualizarTitulo(anio) {
    const e = LIB.indice.find(x => x.anio == anio) || {};
    const campeon = e.campeon ? equipo(e.campeon).nombre : null;
    document.title = `Copa Libertadores ${anio}${campeon ? " — Campeón " + campeon : ""}`;
    const desc = document.querySelector('meta[name="description"]');
    if (desc) desc.content = `Copa Libertadores ${anio}: ${campeon ? `campeón ${campeon}, subcampeón ${equipo(e.subcampeon).nombre}. ` : ""}` +
      "Final, tablas de grupos, todos los partidos, goleadores, asistidores y planteles.";
    // Dirección "oficial" de esta edición, para que Google no la tome como copia de otra
    let canonica = document.querySelector('link[rel="canonical"]');
    if (!canonica) document.head.appendChild(canonica = Object.assign(document.createElement("link"), { rel: "canonical" }));
    canonica.href = `${URL_SITIO}?edicion=${anio}`;
  }

  function seleccionar(anio, guardarEnHistorial) {
    navEl.querySelectorAll("a").forEach(a => a.toggleAttribute("aria-current", a.dataset.anio == anio));
    if (guardarEnHistorial) history.pushState(null, "", `?edicion=${anio}`);
    actualizarTitulo(anio);
    edicionEl.innerHTML = `<p class="vacio">Cargando ${anio}…</p>`;
    cargarEdicion(anio).then(mostrar).catch(e => { edicionEl.innerHTML = `<p class="vacio">${esc(e.message)}</p>`; });
  }

  // Cada edición es un link real (?edicion=1960) para que Google pueda encontrarlas todas
  navEl.innerHTML = LIB.indice.map(e => `<a href="?edicion=${e.anio}" data-anio="${e.anio}" title="${esc(equipo(e.campeon).nombre)}">${e.anio}</a>`).join("");
  navEl.addEventListener("click", e => {
    const a = e.target.closest("a[data-anio]");
    if (!a || e.ctrlKey || e.metaKey || e.shiftKey) return;   // ctrl+clic: abrir en otra pestaña
    e.preventDefault();
    seleccionar(a.dataset.anio, true);
  });
  const anioDeLaUrl = () => {
    const pedido = new URLSearchParams(location.search).get("edicion");
    return LIB.indice.some(e => e.anio == pedido) ? pedido : LIB.indice[LIB.indice.length - 1].anio;
  };
  window.addEventListener("popstate", () => seleccionar(anioDeLaUrl()));   // botón "atrás" del navegador
  seleccionar(anioDeLaUrl());
})();
