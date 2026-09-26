/* Lógica de la página. Los datos viven en data/ (window.LIB). */
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

  const equipo = id => LIB.equipos[id] || { nombre: id };
  const jugador = id => (LIB.jugadores[id] || { nombre: id }).nombre;

  function escudo(id) {
    const e = equipo(id);
    if (!e.escudo) return "";
    // Si el escudo todavía no se descargó, la imagen se oculta sola
    return `<img class="escudo" src="${e.escudo}" alt="" onerror="this.remove()">`;
  }

  // Goleadores y asistidores se calculan a partir de los goles de cada partido
  function ranking(ed, campo) {
    const cuenta = {};
    ed.fases.forEach(f => f.partidos.forEach(p => (p.goles || []).forEach(g => {
      const id = g[campo];
      if (!id) return;
      cuenta[id] = cuenta[id] || { id, equipo: g.equipo, n: 0 };
      cuenta[id].n++;
    })));
    return Object.values(cuenta).sort((a, b) => b.n - a.n);
  }

  function tablaRanking(titulo, filas) {
    if (!filas.length) return "";
    return `<h3>${titulo}</h3><table><thead><tr><th>Jugador</th><th>Equipo</th><th class="num">Cant.</th></tr></thead><tbody>` +
      filas.map(r => `<tr><td>${jugador(r.id)}</td><td>${escudo(r.equipo)}${equipo(r.equipo).nombre}</td><td class="num">${r.n}</td></tr>`).join("") +
      `</tbody></table>`;
  }

  function mostrar(ed) {
    let html = `<h2>${ed.anio}</h2>
      <p>🏆 Campeón: ${escudo(ed.campeon)}<strong>${equipo(ed.campeon).nombre}</strong> · Subcampeón: ${escudo(ed.subcampeon)}${equipo(ed.subcampeon).nombre}</p>`;

    ed.fases.forEach(f => {
      html += `<h3>${f.nombre}</h3>`;
      f.partidos.forEach(p => {
        const goles = (p.goles || []).map(g => `<li>⚽ ${g.min}' ${jugador(g.jugador)} (${equipo(g.equipo).nombre})</li>`).join("");
        html += `<article class="partido">
          <div class="partido-meta">${p.fecha} · ${p.estadio || ""}</div>
          <div class="marcador">
            <span class="local">${equipo(p.local).nombre}${escudo(p.local)}</span>
            <span class="resultado">${p.goles_local} – ${p.goles_visitante}</span>
            <span>${escudo(p.visitante)}${equipo(p.visitante).nombre}</span>
          </div>
          <ul class="goles">${goles}</ul>
        </article>`;
      });
    });

    html += tablaRanking("Goleadores", ranking(ed, "jugador"));
    html += tablaRanking("Asistidores", ranking(ed, "asistencia"));
    edicionEl.innerHTML = html;
  }

  function seleccionar(anio) {
    navEl.querySelectorAll("button").forEach(b => b.setAttribute("aria-pressed", b.dataset.anio == anio));
    cargarEdicion(anio).then(mostrar).catch(e => { edicionEl.innerHTML = `<p class="vacio">${e.message}</p>`; });
  }

  navEl.innerHTML = LIB.indice.map(a => `<button data-anio="${a}" aria-pressed="false">${a}</button>`).join("");
  navEl.addEventListener("click", e => { if (e.target.dataset.anio) seleccionar(e.target.dataset.anio); });
  seleccionar(LIB.indice[LIB.indice.length - 1]);
})();
