/* Lógica de la página. Los datos viven en data/ (window.LIB). Versión funcional provisoria: el diseño se define después. */
(function () {
  const LIB = window.LIB;
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

  function mostrar(ed) {
    let html = `<h2>${ed.anio}</h2>
      <p>🏆 Campeón: <strong>${ed.campeon ? club(ed.campeon) : "—"}</strong> · Subcampeón: ${ed.subcampeon ? club(ed.subcampeon) : "—"}</p>
      <p class="vacio">Fuentes: ${ed.fuentes.join(" + ")}</p>`;
    html += tablaRanking("Goleadores", ranking(ed, "goles"));
    html += tablaRanking("Asistidores", ranking(ed, "asistencias"));
    // Las fases más importantes primero (la final arriba)
    [...ed.fases].reverse().forEach(f => {
      html += `<details class="fase" ${f.nombre.startsWith("Final") ? "open" : ""}><summary>${esc(f.nombre)} (${f.partidos.length})</summary>` +
        f.partidos.map(partido).join("") + `</details>`;
    });
    html += planteles(ed);
    edicionEl.innerHTML = html;
  }

  function seleccionar(anio) {
    navEl.querySelectorAll("button").forEach(b => b.setAttribute("aria-pressed", b.dataset.anio == anio));
    edicionEl.innerHTML = `<p class="vacio">Cargando ${anio}…</p>`;
    cargarEdicion(anio).then(mostrar).catch(e => { edicionEl.innerHTML = `<p class="vacio">${esc(e.message)}</p>`; });
  }

  navEl.innerHTML = LIB.indice.map(e => `<button data-anio="${e.anio}" aria-pressed="false" title="${esc(equipo(e.campeon).nombre)}">${e.anio}</button>`).join("");
  navEl.addEventListener("click", e => { if (e.target.dataset.anio) seleccionar(e.target.dataset.anio); });
  seleccionar(LIB.indice[LIB.indice.length - 1].anio);
})();
