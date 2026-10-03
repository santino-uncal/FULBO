/* La página de la liga argentina (liga.html). Los datos de cada torneo viven en data/ligas/argentina/<torneo>.js
   (window.LIGA[torneo]) y los arma tools/actualizar_liga.py. La tabla de posiciones no viene en los datos: se
   calcula acá con los resultados de cada partido (así, al bajar los partidos nuevos, la tabla queda al día).
   Dirección: liga.html?torneo=2026-clausura&vista=fechas&fecha=5 (sin torneo, el último). */
(function () {
  const PARAMS = new URLSearchParams(location.search);
  const INDICE = window.LIGA_INDICE || [];
  const CLAVE = INDICE.some(t => t.clave === PARAMS.get("torneo")) ? PARAMS.get("torneo") : INDICE.at(-1)?.clave;
  const VISTAS = [["tabla", "Tabla"], ["fechas", "Fechas"], ["playoffs", "Playoffs"], ["anual", "Tabla anual"],
    ["promedios", "Promedios"], ["goleadores", "Goleadores"]];
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
    Object.entries(T.zonas).forEach(([z, ids]) => ids.forEach(id => { zonaDe[id] = z; }));

    document.title = `${T.nombre} — Liga Profesional Argentina`;
    document.getElementById("titulo-torneo").textContent = T.nombre;
    const [dia, hora] = T.actualizado.split(" ");
    document.getElementById("actualizado").textContent = `Actualizado el ${fechaLarga(dia)} a las ${hora} · se actualiza todos los días`;

    // ---- Tabla de posiciones de cada zona (los partidos interzonales cuentan para la zona de cada club) ----
    function tabla(ids) {
      const t = Object.fromEntries(ids.map(id => [id, { id, pj: 0, g: 0, e: 0, p: 0, gf: 0, gc: 0, ultimos: [] }]));
      todos.filter(jugado).sort((a, b) => (a.fecha || "").localeCompare(b.fecha || "")).forEach(p => {
        [[p.local, p.gl, p.gv], [p.visitante, p.gv, p.gl]].forEach(([id, a, b]) => {
          const f = t[id];
          if (!f) return;
          f.pj++; f.gf += a; f.gc += b;
          const r = a > b ? "V" : a < b ? "D" : "E";
          f[{ V: "g", E: "e", D: "p" }[r]]++;
          f.ultimos.push({ r, texto: `Fecha ${p.n}: ${club(p.local).nombre} ${p.gl}–${p.gv} ${club(p.visitante).nombre}` });
        });
      });
      return Object.values(t).map(f => ({ ...f, pts: f.g * 3 + f.e, dif: f.gf - f.gc }))
        .sort((a, b) => b.pts - a.pts || b.dif - a.dif || b.gf - a.gf || club(a.id).nombre.localeCompare(club(b.id).nombre));
    }
    function tablaHTML(z) {
      const filas = tabla(T.zonas[z]);
      const cuerpo = filas.map((f, i) => {
        const dif = f.dif > 0 ? `+${f.dif}` : f.dif;
        const ultimos = f.ultimos.slice(-5).reverse().map(u => `<span class="res res-${u.r}" title="${esc(u.texto)}"
          aria-label="${{ V: "Victoria", E: "Empate", D: "Derrota" }[u.r]}">${{ V: "✓", E: "–", D: "✕" }[u.r]}</span>`).join("");
        return `<tr><td class="pos ${i < T.pasan ? "pasa" : ""}">${i + 1}</td><td class="eq">${nombreClub(f.id)}</td>
          <td class="pts">${f.pts}</td><td>${f.pj}</td><td class="gol">${f.gf}:${f.gc}</td>
          <td class="dif">${dif}</td><td class="opc">${f.g}</td><td class="opc">${f.e}</td><td class="opc">${f.p}</td>
          <td class="ultimas" title="El más reciente a la izquierda">${ultimos}</td></tr>`;
      }).join("");
      return `<div class="grupo"><h4>Zona ${esc(z)}</h4><table>
        <thead><tr><th>#</th><th class="eq">Equipo</th><th>Pts</th><th>J</th><th class="gol">Gol</th><th>+/-</th>
          <th class="opc">G</th><th class="opc">E</th><th class="opc">P</th><th class="ultimas">Últimas</th></tr></thead>
        <tbody>${cuerpo}</tbody></table></div>`;
    }
    const vistaTabla = () => `<div class="grupos">${Object.keys(T.zonas).map(tablaHTML).join("")}</div>
      <p class="leyenda"><span><i class="pasa"></i>Clasifican a los octavos de final (los ${T.pasan} primeros de cada zona)</span></p>
      <p class="vacio">Orden: puntos, diferencia de gol y goles a favor. Los partidos contra la otra zona (interzonales) suman en la zona de cada club.</p>`;

    // ---- Tabla anual: lo jugado antes en el año (T.anual: el Apertura, [pts, pj, g, e, p, gf, gc]) más este torneo ----
    const ids = Object.values(T.zonas).flat();
    function tablaAnual() {
      const ahora = Object.fromEntries(Object.values(T.zonas).flatMap(tabla).map(f => [f.id, f]));
      return ids.map(id => {
        const [pts, pj, g, e, p, gf, gc] = (T.anual || {})[id] || [0, 0, 0, 0, 0, 0, 0];
        const f = ahora[id];
        return { id, pts: pts + f.pts, pj: pj + f.pj, g: g + f.g, e: e + f.e, p: p + f.p, gf: gf + f.gf, gc: gc + f.gc };
      }).map(f => ({ ...f, dif: f.gf - f.gc }))
        .sort((a, b) => b.pts - a.pts || b.dif - a.dif || b.gf - a.gf || club(a.id).nombre.localeCompare(club(b.id).nombre));
    }
    // ---- Promedios: puntos dividido partidos de las temporadas anteriores (T.promedios: {año: {club: [pts, pj]}})
    // más la del año (la tabla anual). Los recién ascendidos dividen solo por los partidos que jugaron en Primera ----
    const aniosProm = Object.keys(T.promedios || {}).sort();
    function promedios() {
      const anual = Object.fromEntries(tablaAnual().map(f => [f.id, f]));
      return ids.map(id => {
        const temporadas = [...aniosProm.map(a => T.promedios[a][id] || null), [anual[id].pts, anual[id].pj]];
        const pts = temporadas.reduce((n, t) => n + (t ? t[0] : 0), 0);
        const pj = temporadas.reduce((n, t) => n + (t ? t[1] : 0), 0);
        return { id, temporadas, pts, pj, prom: pj ? pts / pj : 0 };
      }).sort((a, b) => b.prom - a.prom || club(a.id).nombre.localeCompare(club(b.id).nombre));
    }
    // Descienden el último de la tabla anual y el peor promedio; si es el mismo club, el anteúltimo de la tabla anual
    function descensos() {
      if (!T.descensos) return { anual: null, prom: null };
      const anual = tablaAnual(), prom = promedios().at(-1).id;
      return { prom, anual: anual.at(-1).id === prom ? anual.at(-2).id : anual.at(-1).id };
    }
    const enJuego = () => T.fechas.some(f => f.partidos.some(p => !jugado(p) && !p.estado));
    const avisoDescenso = () => `<p class="leyenda"><span><i class="desciende"></i>${enJuego() ? "Descendería si el año terminara hoy" : "Desciende"}
      (uno por la tabla anual y otro por los promedios)</span></p>`;
    function vistaAnual() {
      const d = descensos();
      const cuerpo = tablaAnual().map((f, i) => {
        const dif = f.dif > 0 ? `+${f.dif}` : f.dif;
        return `<tr><td class="pos ${f.id === d.anual ? "desciende" : ""}">${i + 1}</td><td class="eq">${nombreClub(f.id)}</td>
          <td class="pts">${f.pts}</td><td>${f.pj}</td><td class="gol">${f.gf}:${f.gc}</td><td class="dif">${dif}</td>
          <td class="opc">${f.g}</td><td class="opc">${f.e}</td><td class="opc">${f.p}</td></tr>`;
      }).join("");
      return `<p class="vacio">Suma la fase de zonas del Torneo Apertura y del Torneo Clausura ${T.anio} (los playoffs no cuentan).</p>
        <div class="grupo tabla-larga"><table><thead><tr><th>#</th><th class="eq">Equipo</th><th>Pts</th><th>J</th><th class="gol">Gol</th><th>+/-</th>
          <th class="opc">G</th><th class="opc">E</th><th class="opc">P</th></tr></thead><tbody>${cuerpo}</tbody></table></div>
        ${T.descensos ? avisoDescenso() : ""}`;
    }
    function vistaPromedios() {
      const d = descensos();
      const temporada = t => t ? t[0] : "–";
      const cuerpo = promedios().map((f, i) => `<tr><td class="pos ${f.id === d.prom ? "desciende" : ""}">${i + 1}</td>
        <td class="eq">${nombreClub(f.id)}</td>${f.temporadas.map(t => `<td class="opc" title="${t ? `${t[1]} partidos` : "No jugó en Primera"}">${temporada(t)}</td>`).join("")}
        <td>${f.pts}</td><td>${f.pj}</td><td class="pts">${f.prom.toFixed(3).replace(".", ",")}</td></tr>`).join("");
      return `<p class="vacio">Los puntos de las temporadas ${[...aniosProm, T.anio].join(", ")} divididos por los partidos jugados
        (la de ${T.anio} es la tabla anual). Los que subieron hace poco dividen solo por los partidos que jugaron en Primera.</p>
        <div class="grupo tabla-larga"><table><thead><tr><th>#</th><th class="eq">Equipo</th>${[...aniosProm, T.anio].map(a => `<th class="opc">${a}</th>`).join("")}
          <th>Pts</th><th>J</th><th>Prom.</th></tr></thead><tbody>${cuerpo}</tbody></table></div>
        ${T.descensos ? avisoDescenso() : ""}`;
    }

    // ---- Un partido ----
    // conDia: poner el día en cada partido (en las fechas no hace falta: van agrupados por día)
    function partidoHTML(p, conDia = true) {
      const res = jugado(p) ? `${p.gl} – ${p.gv}` : p.estado ? esc(p.estado) : p.hora ? `${p.hora} h` : "vs";
      const interzonal = zonaDe[p.local] && zonaDe[p.visitante] && zonaDe[p.local] !== zonaDe[p.visitante];
      const meta = [conDia && (p.fecha ? fechaLarga(p.fecha) : "Día a confirmar"), jugado(p) && p.hora && `${p.hora} h`, p.estadio, p.arbitro && `Árbitro: ${p.arbitro}`,
        p.publico && `${p.publico.toLocaleString("es-AR")} espectadores`].filter(Boolean).map(esc).join(" · ");
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
    const fechaActual = () => (T.fechas.find(f => f.partidos.some(p => !jugado(p) && !p.estado)) || T.fechas.at(-1)).numero;
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
        `<h4 class="fecha-grupo">${d ? fechaLarga(d).replace(/^./, c => c.toUpperCase()) : "Día y hora a confirmar"}</h4>${ps.map(p => partidoHTML(p, false)).join("")}`).join("");
      return `<div class="orden-partidos elegir-fecha">Fecha: ${botones}</div>
        <div class="titulo-fecha">
          <button class="flecha-anio" type="button" data-fecha="${f.numero - 1}" ${f.numero > 1 ? "" : "disabled"} aria-label="Fecha anterior">◀</button>
          <h3>Fecha ${f.numero} <small>${rango} · ${jugados === f.partidos.length ? "terminada" : `${jugados} de ${f.partidos.length} partidos jugados`}</small></h3>
          <button class="flecha-anio" type="button" data-fecha="${f.numero + 1}" ${f.numero < T.fechas.length ? "" : "disabled"} aria-label="Fecha siguiente">▶</button>
        </div>${cuerpo}`;
    }

    // ---- Playoffs: si todavía no empezaron, cómo serían los cruces si la fase regular terminara hoy ----
    function vistaPlayoffs() {
      if (T.playoffs.length) return T.playoffs.map(r => `<h3>${esc(r.nombre)}</h3>${r.partidos.map(p => partidoHTML(p)).join("")}`).join("");
      const [za, zb] = Object.keys(T.zonas);
      const a = tabla(T.zonas[za]), b = tabla(T.zonas[zb]);
      const cruces = [];
      // 1º de una zona contra el 8º de la otra, 2º contra 7º, 3º contra 6º y 4º contra 5º
      for (let i = 0; i < T.pasan / 2; i++) cruces.push([a[i], b[T.pasan - 1 - i], za, zb, i], [b[i], a[T.pasan - 1 - i], zb, za, i]);
      const fila = ([x, y, zx, zy, i]) => `<li class="cruce"><span class="local">${esc(club(x.id).nombre)}${escudo(x.id)} <small>${i + 1}º ${zx}</small></span>
        <span class="resultado">vs</span><span><small>${T.pasan - i}º ${zy}</small> ${nombreClub(y.id)}</span></li>`;
      return `<p class="nota-edicion">Los playoffs empiezan cuando termine la fase regular (fecha ${T.fechas.length}). Son a un solo partido,
        en la cancha del mejor ubicado: octavos, cuartos, semifinales y final. <strong>Si la fase regular terminara hoy</strong>, los octavos serían:</p>
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
      return filas.length ? `<div class="grupo goleadores"><table><thead><tr><th>#</th><th class="eq">Jugador</th><th class="eq">Club</th><th>Goles</th>
        <th class="opc" title="De penal">Pen.</th></tr></thead><tbody>${cuerpo}</tbody></table></div>` : `<p class="vacio">Todavía no hay goles.</p>`;
    }

    // ---- Pestañas ----
    let vista = VISTAS.some(([v]) => v === PARAMS.get("vista")) ? PARAMS.get("vista") : "tabla";
    function dibujar(guardar) {
      if (guardar) {
        const q = new URLSearchParams({ torneo: CLAVE });
        if (vista !== "tabla") q.set("vista", vista);
        if (vista === "fechas") q.set("fecha", fechaVista);
        history.pushState({ vista, fechaVista }, "", `?${q}`);
      }
      const html = { tabla: vistaTabla, fechas: vistaFechas, playoffs: vistaPlayoffs, anual: vistaAnual, promedios: vistaPromedios,
        goleadores: vistaGoleadores }[vista]();
      ligaEl.innerHTML = `<div class="pestanas" role="tablist">${VISTAS.filter(([v]) => (v !== "promedios" || T.promedios) && (v !== "anual" || T.anual)).map(([v, n]) =>
        `<button class="pestana" type="button" role="tab" data-vista="${v}" aria-selected="${v === vista}">${n}</button>`).join("")}</div>${html}`;
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
      vista = q.get("vista") || "tabla";
      fechaVista = +q.get("fecha") || fechaActual();
      dibujar();
    });
    dibujar();
  }
})();
