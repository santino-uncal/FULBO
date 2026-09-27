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
  // Bandera del país de cada equipo (assets/banderas/ARG.png, BRA.png…)
  const PAISES = { ARG: "Argentina", BOL: "Bolivia", BRA: "Brasil", CHI: "Chile", COL: "Colombia", ECU: "Ecuador",
    MEX: "México", PAR: "Paraguay", PER: "Perú", URU: "Uruguay", VEN: "Venezuela" };
  function bandera(id) {
    const p = equipo(id).pais;
    if (!PAISES[p]) return "";
    return `<img class="bandera" src="assets/banderas/${p}.png" alt="${PAISES[p]}" title="${PAISES[p]}" onerror="this.remove()">`;
  }
  const club = id =>`${escudo(id)}${esc(equipo(id).nombre)}`;

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
      cuenta[clave] = cuenta[clave] || { nombre, equipo: eq, n: 0, detalle: [] };
      cuenta[clave].n++;
      cuenta[clave].detalle.push({ g, p, fase: f.nombre });   // para el botón "Ver"
    })));
    return Object.values(cuenta).sort((a, b) => b.n - a.n || a.nombre.localeCompare(b.nombre));
  }

  // Un renglón por gol o asistencia: minuto, partido con resultado, fase y fecha
  function detalleRanking({ g, p, fase }, tipo) {
    const min = g.min != null ? `${g.min}${g.extra ? "+" + g.extra : ""}'` : "";
    const res = p.gl == null ? "vs" : `${p.gl}–${p.gv}`;
    const extra = tipo === "goles"
      ? [g.tipo === "pen" && "de penal", g.asistencia && `asist. ${esc(g.asistencia)}`]
      : [g.jugador && `gol de ${esc(g.jugador)}`];
    return `<li><span class="det-min">${min}</span>
      <span>${esc(equipo(p.local).nombre)} ${res} ${esc(equipo(p.visitante).nombre)}</span>
      <span class="det-meta">${[esc(fase), esc(p.fecha || ""), ...extra].filter(Boolean).join(" · ")}</span></li>`;
  }

  function tablaRanking(titulo, filas, tipo) {
    if (!filas.length) return "";
    const que = tipo === "goles" ? "goles" : "asistencias";
    const renglones = lista => lista.map(r => `<tr><td>${esc(r.nombre)}</td><td>${club(r.equipo)}</td><td class="num">${r.n}</td>
        <td class="num"><button class="ver" type="button" aria-expanded="false" title="Ver sus ${que}">Ver</button></td></tr>
        <tr class="detalle" hidden><td colspan="4"><ul>${r.detalle.map(d => detalleRanking(d, tipo)).join("")}</ul></td></tr>`).join("");
    // Se muestran los 15 primeros; el resto queda plegado debajo del botón "Ver todos"
    const resto = filas.slice(15);
    // Botón al lado del título para mostrar u ocultar toda la tabla (arranca cerrada)
    return `<h3 class="titulo-ranking">${titulo}<button class="mostrar-tabla" type="button" aria-expanded="false">Mostrar</button></h3>
      <div class="tabla-ranking" hidden><table class="ranking"><thead><tr><th>Jugador</th><th>Equipo</th><th class="num">Cant.</th><th></th></tr></thead>
      <tbody>${renglones(filas.slice(0, 15))}</tbody>
      ${resto.length ? `<tbody class="resto" hidden>${renglones(resto)}</tbody>` : ""}</table>` +
      (resto.length ? `<button class="ver-todos" type="button" data-total="${filas.length}">Ver todos (${filas.length})</button>` : "") +
      `</div>`;
  }

  // Cada gol va del lado del equipo que lo festeja (en los goles en contra, el rival del que lo hizo)
  function textoGol(g) {
    const min = g.min != null ? `${g.min}${g.extra ? "+" + g.extra : ""}' ` : "";
    const tipo = g.tipo === "pen" ? " (penal)" : g.tipo === "ec" ? " (en contra)" : "";
    const asis = g.asistencia ? `<small class="gol-asist">asist. ${esc(g.asistencia)}</small>` : "";
    const texto = `${min}${esc(g.jugador || "?")}${tipo}`;
    return `<li>${g.equipo === "visitante" ? `⚽ ${texto}` : `${texto} ⚽`}${asis}</li>`;
  }
  function golesPartido(p) {
    const goles = p.goles || [];
    if (!goles.length) return "";
    const lado = l => `<ul class="goles${l === "local" ? " goles-local" : ""}">${goles.filter(g => (g.equipo === "visitante" ? "visitante" : "local") === l).map(textoGol).join("")}</ul>`;
    return `<div class="goles-partido">${lado("local")}${lado("visitante")}</div>`;
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
      ${golesPartido(p)}
    </article>`;
  }

  function planteles(ed) {
    const ids = Object.keys(ed.planteles || {}).sort((a, b) => equipo(a).nombre.localeCompare(equipo(b).nombre));
    if (!ids.length) return "";
    // Estadio de cada equipo: donde más veces jugó de local en esta edición (los clubes cambian de cancha con los años).
    // Si esta edición no trae estadios, el de la primera edición posterior que sí los tiene (equipos.js)
    const canchas = {};
    ed.fases.forEach(f => f.partidos.forEach(p => {
      if (!p.estadio || f.nombre.startsWith("Final")) return;   // las finales pueden ser en cancha neutral
      const c = canchas[p.local] ??= {};
      const k = p.estadio + (p.ciudad ? `, ${p.ciudad}` : "");
      c[k] = (c[k] || 0) + 1;
    }));
    const estadio = id => {
      const c = Object.entries(canchas[id] || {}).sort((a, b) => b[1] - a[1])[0]?.[0] || equipo(id).estadio;
      return c ? ` <span class="plantel-estadio">🏟️ ${esc(c)}</span>` : "";
    };
    const modo = ordenPlantelElegido();
    const botones = ["posicion", "nombre"].map(m => `<button class="orden orden-plantel" type="button" data-orden-plantel="${m}"
      aria-pressed="${modo === m}">${m === "nombre" ? "Por nombre" : "Por posición"}</button>`).join("");
    return `<h3>Planteles</h3><p class="vacio">Jugadores que aparecen en formaciones o goles de esta edición.</p>
      <div class="orden-partidos">Ordenar: ${botones}</div>` +
      ids.map(id => `<details class="plantel"><summary>${club(id)} (${ed.planteles[id].length})${estadio(id)}</summary>
        <table><thead><tr><th>#</th><th>Jugador</th><th>Posición</th><th class="num">PJ</th><th class="num">Goles</th><th class="num">Asist.</th></tr></thead><tbody>
        ${ordenarPlantel(ed.planteles[id], modo).map(j => `<tr data-nombre="${esc(j.nombre)}" data-linea="${lineaDe(j.pos)}">
          <td>${esc(j.num || "")}</td><td>${esc(j.nombre)}</td><td>${esc(nombrePos(j.pos))}</td>
          <td class="num">${j.pj || 0}</td><td class="num">${j.goles || 0}</td><td class="num">${j.asist || 0}</td></tr>`).join("")}
        </tbody></table></details>`).join("");
  }
  // Las fuentes traen las posiciones en siglas en inglés (G, CD-L, AM…): se muestran en castellano
  const POSICIONES = {
    G: "Arquero", D: "Defensor", SW: "Líbero",
    CD: "Defensor central", "CD-L": "Defensor central izq.", "CD-R": "Defensor central der.",
    LB: "Lateral izquierdo", RB: "Lateral derecho",
    DM: "Volante central (5)", M: "Mediocampista", CM: "Mediocampista central",
    "CM-L": "Mediocampista central izq.", "CM-R": "Mediocampista central der.", RCM: "Mediocampista central der.",
    LM: "Volante izquierdo", RM: "Volante derecho",
    AM: "Enganche (10)", "AM-L": "Mediapunta izquierdo", "AM-R": "Mediapunta derecho",
    F: "Delantero", "CF-L": "Delantero centro izq.", "CF-R": "Delantero centro der.", RCF: "Delantero centro der.",
    LF: "Extremo izquierdo", RF: "Extremo derecho",
  };
  const nombrePos = pos => !pos || pos === "-" ? "" : POSICIONES[pos] || pos;
  // Línea de la cancha según la posición: arquero, defensores, volantes, delanteros; sin posición al final
  function lineaDe(pos) {
    if (!pos || pos === "-") return 9;
    if (pos === "G") return 0;
    if (/^DM/.test(pos)) return 2;
    if (/^(D|CD|LB|RB|SW|LWB|RWB)/.test(pos)) return 1;
    if (/^(M|CM|LM|RM|RCM|LCM)/.test(pos)) return 3;
    if (/^AM/.test(pos)) return 4;
    if (/^(F|CF|LF|RF|RCF|LCF|ST|W)/.test(pos)) return 5;
    return 8;
  }
  const porNombre = (a, b) => a.nombre.localeCompare(b.nombre, "es");
  function ordenarPlantel(jugadores, modo) {
    return [...jugadores].map(j => ({ nombre: j.nombre, linea: lineaDe(j.pos), j }))
      .sort((a, b) => (modo === "posicion" ? a.linea - b.linea : 0) || porNombre(a, b)).map(x => x.j);
  }
  function ordenPlantelElegido() {
    try { return localStorage.getItem("ordenPlantel") === "nombre" ? "nombre" : "posicion"; } catch { return "posicion"; }
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
      const ultimos = f.ultimos.slice(-5).reverse().map(u => `<span class="res res-${u.r}" title="${esc(u.texto)}" aria-label="${{ V: "Victoria", E: "Empate", D: "Derrota" }[u.r]}">${{ V: "✓", E: "–", D: "✕" }[u.r]}</span>`).join("");
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

  // El cuadro de la última etapa de grupos va en una pestaña al lado, "Fase eliminatoria"
  function gruposHTML(ed, cuadro, previa) {
    const conGrupos = etapasDeGrupos(ed);
    const etapas = conGrupos.length ? conGrupos : etapasDeLlaves(ed);
    return etapas.map((etapa, i) => {
      const leyenda = [
        etapa.siguiente && `<span><i class="pasa"></i>Clasificación a ${esc(etapa.siguiente)}</span>`,
        etapa.campeon && `<span><i class="campeon"></i>Campeón</span>`,
        ed.anio >= 2017 && etapa.nombre === "Fase de grupos" && `<span><i class="sudamericana"></i>Pasa a la Copa Sudamericana</span>`
      ].filter(Boolean).join("");
      const grupos = `<div class="grupos">${etapa.grupos.map(g => grupoHTML(g, etapa, ed.anio)).join("")}</div>
        <p class="leyenda">${leyenda}</p>`;
      // En la última etapa de grupos van las pestañas: fase previa, grupos y fase eliminatoria
      const pestanas = i !== etapas.length - 1 ? [] :
        [previa && ["Fase previa", previa], [etapa.nombre, grupos, true], cuadro && ["Fase eliminatoria", cuadro]].filter(Boolean);
      if (pestanas.length < 2) return `<h3>${esc(etapa.nombre)}</h3>${grupos}`;
      return `<div class="pestanas" role="tablist">${pestanas.map(([nombre, , activa]) =>
          `<button class="pestana" type="button" role="tab" aria-selected="${!!activa}">${esc(nombre)}</button>`).join("")}</div>` +
        pestanas.map(([, html, activa]) => `<div class="panel"${activa ? "" : " hidden"}>${html}</div>`).join("");
    }).join("");
  }

  // ---- Cuadro de la fase eliminatoria (desde la última etapa de grupos hasta la final) ----

  // Junta los partidos de las fases [desde, hasta) en llaves: mismo par de equipos dentro de la misma fase (con su desempate).
  // Con "soloPar" junta el mismo par aunque esté en otra fase (datos con la vuelta cargada en la fase siguiente)
  function juntarLlaves(ed, desde, hasta, soloPar) {
    const llaves = [];
    ed.fases.forEach((f, i) => {
      if (i < desde || i >= hasta) return;
      const fase = f.nombre.replace(/ — Desempate$/, "");
      f.partidos.forEach(p => {
        const par = [p.local, p.visitante].sort().join("|");
        // Orden de las llaves: fase, número de llave (algunas fechas están mal cargadas) y fecha
        const orden = `${String(i).padStart(3, "0")}|${String(p.llave ?? 999).padStart(3, "0")}|${p.fecha || ""}`;
        let ll = llaves.find(l => (soloPar || l.fase === fase) && l.par === par);
        if (!ll) llaves.push(ll = { fase, par, partidos: [], orden });
        ll.partidos.push(p);
        if (orden < ll.orden) ll.orden = orden;
      });
    });
    llaves.forEach(ll => {
      ll.partidos.sort((a, b) => (a.fecha || "").localeCompare(b.fecha || ""));
      ll.equipos = [ll.partidos[0].local, ll.partidos[0].visitante];
    });
    return llaves;
  }

  function cuadroHTML(ed) {
    const esGrupo = f => / — Grupo /.test(f.nombre);
    const ultimoGrupo = ed.fases.reduce((u, f, i) => esGrupo(f) ? i : u, -1);
    const llaves = juntarLlaves(ed, ultimoGrupo + 1, ed.fases.length);
    const final = llaves.find(l => l.fase.startsWith("Final"));
    if (!final) return "";
    return dibujarCuadro(llaves, [{ ll: final, gana: ed.campeon }], 2);
  }

  // ---- Cuadro de la fase previa (todas las fases antes de la fase de grupos) ----
  // No es un cuadro "puro": en cada ronda entran equipos nuevos, así que esas casillas quedan vacías
  function cuadroPreviaHTML(ed) {
    const primerGrupo = ed.fases.findIndex(f => / — Grupo /.test(f.nombre));
    if (primerGrupo <= 0) return "";
    const llaves = juntarLlaves(ed, 0, primerGrupo, true);
    // Si un equipo juega más de una llave en la misma fase no es eliminación directa (p. ej. la previa 1998-2003)
    const vistos = new Set();
    for (const ll of llaves) for (const id of ll.equipos) {
      if (vistos.has(ll.fase + id)) return "";
      vistos.add(ll.fase + id);
    }
    // Ganador de cada llave de la última ronda: el que sigue jugando después (en la fase de grupos)
    const siguen = new Set(ed.fases.slice(primerGrupo).flatMap(f => f.partidos.flatMap(p => [p.local, p.visitante])));
    const ultima = llaves[llaves.length - 1].fase;
    const raices = llaves.filter(l => l.fase === ultima).sort((a, b) => a.orden.localeCompare(b.orden))
      .map(ll => ({ ll, gana: ll.equipos.find(id => siguen.has(id)) }));
    return dibujarCuadro(llaves, raices, 1);
  }

  // Dibuja el árbol hacia atrás desde las llaves de la última ronda (raíces)
  function dibujarCuadro(llaves, raices, minRondas) {
    // La llave anterior de un equipo: la última que jugó antes de esta
    // Si el equipo todavía no se conoce ("a definir"), la primera llave libre de la ronda anterior
    const usadas = new Set(raices.map(r => r.ll));
    const anterior = (id, ll) => {
      if (id === "a-definir") {
        const antes = llaves.filter(l => l.orden < ll.orden && l.fase !== ll.fase);
        const fase = antes.length && antes[antes.length - 1].fase;
        return antes.find(l => l.fase === fase && !usadas.has(l));
      }
      return llaves.filter(l => l !== ll && l.orden < ll.orden && l.equipos.includes(id))
        .sort((a, b) => b.orden.localeCompare(a.orden))[0];
    };
    // Arma el árbol hacia atrás: cada llave tiene arriba la de su primer equipo y abajo la del segundo
    const niveles = [raices];
    while (niveles.length < 7) {
      const previo = niveles[niveles.length - 1].flatMap(x => x
        ? x.ll.equipos.map(id => {
          const ll = anterior(id, x.ll);
          if (!ll) return null;
          usadas.add(ll);
          return { ll, gana: id };
        })
        : [null, null]);
      if (!previo.some(Boolean)) break;
      niveles.push(previo);
    }
    if (niveles.length < minRondas) return "";   // sin eliminación directa antes de la final (p. ej. semifinales por grupos)
    niveles.reverse();
    // Título de cada ronda: el nombre de su fase, o uno genérico si varias rondas comparten fase (2002)
    const nombres = niveles.map(nivel => nivel.find(Boolean).ll.fase);
    const generico = { 16: "Dieciseisavos de final", 8: "Octavos de final", 4: "Cuartos de final", 2: "Semifinales", 1: "Final" };
    const columnas = niveles.map((nivel, n) => {
      const repetido = nombres.filter(x => x === nombres[n]).length > 1;
      const nombre = repetido ? generico[nivel.length] || nombres[n] : nombres[n];
      // Sin llave antes (equipos que entran directo en esta ronda): sin línea hacia atrás
      const antes = niveles[n - 1];
      const casillas = nivel.map((x, i) => {
        const sola = !antes || antes[2 * i] || antes[2 * i + 1] ? "" : " sola";
        return `<div class="casilla${sola}">${x ? llaveHTML(x.ll, x.gana) : ""}</div>`;
      });
      // Corchete hacia la ronda siguiente: completo, sólo la mitad que tiene llave, o ninguno
      const par = i => nivel[i] && nivel[i + 1] ? "par" : nivel[i] ? "par solo-arriba" : nivel[i + 1] ? "par solo-abajo" : "par vacio";
      const cuerpo = n === niveles.length - 1 ? casillas.join("")
        : casillas.reduce((h, c, i) => i % 2 ? h + c + "</div>" : h + `<div class="${par(i)}">` + c, "");
      return `<div class="ronda"><div class="ronda-titulo">${esc(nombre)}</div><div class="ronda-cuerpo">${cuerpo}</div></div>`;
    });
    return `<div class="cuadro-scroll"><div class="cuadro">${columnas.join("")}</div></div>`;
  }

  // Una llave: cada equipo con sus goles en cada partido, el total y los penales
  function llaveHTML(ll, gana) {
    const goles = (p, id) => p.local === id ? p.gl : p.gv;
    const conPen = [...ll.partidos].reverse().find(p => p.pen_l != null);
    const unSolo = ll.partidos.length === 1;
    const fila = id => {
      const parciales = ll.partidos.map(p => goles(p, id));
      const total = parciales.some(g => g == null) ? "–" : parciales.reduce((a, b) => a + b, 0);
      const pen = conPen ? ` <small>(${conPen.local === id ? conPen.pen_l : conPen.pen_v})</small>` : "";
      const celdas = unSolo ? "" : parciales.map(g => `<span class="ll-g">${g ?? "–"}</span>`).join("");
      return `<div class="ll-eq${id === gana ? " gana" : ""}" title="${esc(equipo(id).nombre)}">
        ${bandera(id)}<span class="ll-nombre">${club(id)}</span>${celdas}<span class="ll-total">${total}${pen}</span></div>`;
    };
    const detalle = ll.partidos.map(p => `${equipo(p.local).nombre} ${p.gl ?? ""}–${p.gv ?? ""} ${equipo(p.visitante).nombre}${p.fecha ? " (" + p.fecha + ")" : ""}`).join("\n");
    return `<div class="llave" title="${esc(detalle)}">${ll.equipos.map(fila).join("")}</div>`;
  }

  // Reparte los partidos de un grupo en fechas (los datos no traen el número de fecha).
  // Cada fecha junta partidos sin equipos repetidos (en un grupo de 4: A-B con C-D), tomando siempre
  // el más temprano que falte; así un partido postergado igual queda en su fecha.
  function porFechas(partidos) {
    const pendientes = [...partidos].sort((a, b) => (a.fecha || "").localeCompare(b.fecha || ""));
    const cantEquipos = new Set(partidos.flatMap(p => [p.local, p.visitante])).size;
    const porFecha = Math.max(1, Math.floor(cantEquipos / 2));
    const fechas = [];
    while (pendientes.length) {
      const fecha = [pendientes.shift()];
      const usados = new Set([fecha[0].local, fecha[0].visitante]);
      for (let i = 0; i < pendientes.length && fecha.length < porFecha; i++) {
        const p = pendientes[i];
        if (usados.has(p.local) || usados.has(p.visitante)) continue;
        fecha.push(p); usados.add(p.local).add(p.visitante);
        pendientes.splice(i--, 1);
      }
      fechas.push(fecha);
    }
    return fechas;
  }

  // Partidos de una fase eliminatoria, con dos órdenes a elegir: por fecha (como vienen)
  // o por llave (ida y vuelta juntas). La elección se recuerda para todas las fases.
  function eliminatoriaHTML(partidos) {
    const porFecha = partidos.map(partido).join("");
    const llaves = [];
    [...partidos].sort((a, b) => (a.fecha || "").localeCompare(b.fecha || "")).forEach(p => {
      const par = [p.local, p.visitante].sort().join("|");
      let ll = llaves.find(l => l.par === par);
      if (!ll) llaves.push(ll = { par, llave: p.llave ?? 999, primera: p.fecha || "", partidos: [] });
      ll.partidos.push(p);
    });
    if (llaves.length === partidos.length) return porFecha;   // todo a partido único: no hay nada que juntar
    llaves.sort((a, b) => a.llave - b.llave || a.primera.localeCompare(b.primera));
    const porLlave = llaves.map((ll, n) => {
      const [p] = ll.partidos;
      return `<h4 class="fecha-grupo">Llave ${n + 1} · ${esc(equipo(p.local).nombre)} – ${esc(equipo(p.visitante).nombre)}</h4>` +
        ll.partidos.map(partido).join("");
    }).join("");
    const modo = ordenElegido();
    return `<div class="orden-partidos">Ordenar:
        <button class="orden" type="button" data-orden="llave" aria-pressed="${modo === "llave"}">Por llave</button>
        <button class="orden" type="button" data-orden="fecha" aria-pressed="${modo === "fecha"}">Por fecha</button>
      </div>
      <div data-vista="llave"${modo === "llave" ? "" : " hidden"}>${porLlave}</div>
      <div data-vista="fecha"${modo === "fecha" ? "" : " hidden"}>${porFecha}</div>`;
  }
  function ordenElegido() {
    try { return localStorage.getItem("ordenEliminatoria") === "llave" ? "llave" : "fecha"; } catch { return "fecha"; }
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
    html += gruposHTML(ed, cuadroHTML(ed), cuadroPreviaHTML(ed));
    // El resto de las fases, de la más importante a la primera (los grupos, de la A en adelante)
    const resto = [...ed.fases].reverse().filter(f => !esFinal(f));
    const grupoDe = f => f.nombre.match(/^(.*) — Grupo (\S+)$/);
    // Ordena los grupos de cada etapa (A, B, C…), con el desempate de un grupo justo después del grupo
    const clave = f => f.nombre.match(/^(.*) — Grupo (\S+)( — Desempate)?$/);
    new Set(resto.map(clave).filter(Boolean).map(m => m[1])).forEach(etapa => {
      const lugares = resto.map((f, i) => clave(f)?.[1] === etapa ? i : -1).filter(i => i >= 0);
      const ordenados = lugares.map(i => resto[i]).sort((a, b) =>
        clave(a)[2].localeCompare(clave(b)[2], "es", { numeric: true }) || !!clave(a)[3] - !!clave(b)[3]);
      lugares.forEach((i, n) => { resto[i] = ordenados[n]; });
    });
    resto.forEach(f => {
      const g = grupoDe(f);
      const cuerpo = g
        ? porFechas(f.partidos).map((ps, n) => `<h4 class="fecha-grupo">Grupo ${esc(g[2])} · Fecha ${n + 1}</h4>` + ps.map(partido).join("")).join("")
        : eliminatoriaHTML(f.partidos);
      html += `<details class="fase"><summary>${esc(f.nombre)} (${f.partidos.length})</summary>${cuerpo}</details>`;
    });
    html += tablaRanking("Goleadores", ranking(ed, "goles"), "goles");
    html += tablaRanking("Asistidores", ranking(ed, "asistencias"), "asistencias");
    html += planteles(ed);
    edicionEl.innerHTML = html;
  }

  // ---- Ficha de un equipo (buscador) ----

  // data/historial.js (la historia de cada club) se carga recién cuando se usa el buscador
  let historialPedido;
  function cargarHistorial() {
    if (LIB.historial) return Promise.resolve(LIB.historial);
    return historialPedido ??= new Promise((ok, error) => {
      const s = document.createElement("script");
      s.src = "data/historial.js";
      s.onload = () => ok(LIB.historial);
      s.onerror = () => { historialPedido = null; error(new Error("No se pudo cargar el historial de los equipos")); };
      document.body.appendChild(s);
    });
  }

  // "Atlético" y "atletico" cuentan igual al buscar
  const normalizar = t => String(t || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();
  const linkEdicion = anio => `<a href="?edicion=${anio}" data-anio="${anio}">${anio}</a>`;
  const linkEquipo = id => `<a class="link-equipo" href="?equipo=${esc(id)}" data-equipo="${esc(id)}">${club(id)}</a>`;
  const plural = (n, uno, varios) => `${n} ${n === 1 ? uno : varios}`;

  // Equipos cuyo nombre contiene lo buscado: primero los que empiezan así, después los de más ediciones
  function buscarEquipos(texto) {
    const q = normalizar(texto);
    if (!q) return [];
    const hist = LIB.historial || {};
    return Object.keys(hist)
      .map(id => ({ id, nombre: normalizar(equipo(id).nombre) }))
      .filter(x => x.nombre.includes(q) || x.id.includes(q.replace(/\s+/g, "-")))
      .sort((a, b) => b.nombre.startsWith(q) - a.nombre.startsWith(q) ||
        hist[b.id].ediciones.length - hist[a.id].ediciones.length || a.nombre.localeCompare(b.nombre))
      .slice(0, 12).map(x => x.id);
  }

  // Un partido destacado (mayor goleada, peor derrota): "River 9–0 Universitario · 1970, Semifinales"
  function partidoDestacado(id, r) {
    if (!r) return "—";
    const [l, v, gl, gv] = r.local ? [id, r.rival, r.gf, r.gc] : [r.rival, id, r.gc, r.gf];
    return `${esc(equipo(l).nombre)} <strong>${gl}–${gv}</strong> ${esc(equipo(v).nombre)}
      <span class="det-meta">· ${linkEdicion(r.anio)}, ${esc(r.fase)}</span>`;
  }

  // Qué tan lejos llegó en una edición (más alto = mejor). "Primera fase" era la fase de grupos de antes
  const NIVEL_FASE = { "Campeón": 10, "Subcampeón": 9, "Final": 9, "Semifinales": 8, "Cuartos de final": 7,
    "Octavos de final": 6, "Segunda fase": 5, "Fase de grupos": 4, "Primera fase": 4,
    "Tercera fase previa": 3, "Segunda fase previa": 2, "Primera fase previa": 1, "Fase previa": 1 };
  // Mejor o peor instancia a la que llegó, con todos los años en que le pasó
  function participacion(eds, cual) {
    const nivel = x => NIVEL_FASE[x.fase] ?? 0;
    // La edición en juego (sin campeón todavía) no cuenta para la peor: el equipo puede seguir avanzando
    const terminadas = eds.filter(x => LIB.indice.find(e => e.anio === x.anio)?.campeon);
    if (cual === "peor" && terminadas.length) eds = terminadas;
    const n = (cual === "mejor" ? Math.max : Math.min)(...eds.map(nivel));
    const veces = eds.filter(x => nivel(x) === n);
    // Si la instancia cambió de nombre con los años ("Primera fase" → "Fase de grupos"), el más reciente
    return { fase: veces[veces.length - 1].fase, anios: veces.map(x => x.anio) };
  }

  function mostrarEquipo(id) {
    const h = LIB.historial[id];
    const e = equipo(id);
    if (!h) { edicionEl.innerHTML = `<p class="vacio">No hay datos de ese equipo.</p>`; return; }
    const t = h.total;
    const eds = h.ediciones;
    const efectividad = t.pj ? Math.round((t.g * 3 + t.e) / (t.pj * 3) * 100) : 0;
    const dato = (valor, texto, extra = "") => `<div class="dato"><strong>${valor}</strong><span>${texto}</span>${extra}</div>`;
    const anios = lista => lista.length ? `<small>${lista.map(linkEdicion).join(" · ")}</small>` : "";
    const lugar = [PAISES[e.pais] && `${bandera(id)}${PAISES[e.pais]}`, e.ciudad && esc(e.ciudad), e.estadio && `🏟️ ${esc(e.estadio)}`]
      .filter(Boolean).join(" · ");
    const dif = t.gf - t.gc;
    const mejor = participacion(eds, "mejor"), peor = participacion(eds, "peor");

    let html = `<h2 class="titulo-equipo">${e.escudo ? `<img class="escudo-grande" src="${e.escudo}" alt="" onerror="this.remove()">` : ""}${esc(e.nombre)}</h2>
      <p class="vacio">${lugar}</p>
      <div class="datos">
        ${dato(eds.length, eds.length === 1 ? "edición jugada" : "ediciones jugadas", `<small>${eds[0].anio}${eds.length > 1 ? ` a ${eds[eds.length - 1].anio}` : ""}</small>`)}
        ${dato(h.titulos.length ? "🏆 " + h.titulos.length : 0, h.titulos.length === 1 ? "título" : "títulos", anios(h.titulos))}
        ${dato(h.finales.length, h.finales.length === 1 ? "final perdida" : "finales perdidas", anios(h.finales))}
        ${dato(t.pj, "partidos", `<small>${t.g} G · ${t.e} E · ${t.p} P</small>`)}
        ${dato(`${t.gf}:${t.gc}`, "goles a favor y en contra", `<small>diferencia ${dif > 0 ? "+" : ""}${dif}</small>`)}
        ${dato(`${efectividad}%`, "de los puntos ganados", `<small>contando 3 por victoria</small>`)}
        ${dato(`<span class="dato-texto">📈 ${esc(mejor.fase)}</span>`, "mejor participación", anios(mejor.anios))}
        ${dato(`<span class="dato-texto">📉 ${esc(peor.fase)}</span>`, "peor participación", anios(peor.anios))}
      </div>
      <p>💪 Mayor goleada: ${partidoDestacado(id, h.mayorVictoria)}</p>
      <p>😣 Peor derrota: ${partidoDestacado(id, h.peorDerrota)}</p>`;

    // Edición por edición, de la más reciente a la primera
    html += `<h3>Edición por edición</h3>
      <div class="tabla-scroll"><table class="historial"><thead><tr><th>Año</th><th>Hasta dónde llegó</th>
        <th class="num">PJ</th><th class="num">G</th><th class="num">E</th><th class="num">P</th><th class="num">Goles</th></tr></thead><tbody>
      ${[...eds].reverse().map(x => `<tr class="${x.fase === "Campeón" ? "fila-campeon" : x.fase === "Subcampeón" ? "fila-sub" : ""}">
        <td>${linkEdicion(x.anio)}</td><td>${x.fase === "Campeón" ? "🏆 " : x.fase === "Subcampeón" ? "🥈 " : ""}${esc(x.fase)}</td>
        <td class="num">${x.pj}</td><td class="num">${x.g}</td><td class="num">${x.e}</td><td class="num">${x.p}</td>
        <td class="num">${x.gf}:${x.gc}</td></tr>`).join("")}
      </tbody></table></div>`;

    if (h.rivales.length) html += `<h3>Rivales más frecuentes</h3>
      <div class="tabla-scroll"><table class="historial"><thead><tr><th>Rival</th>
        <th class="num">PJ</th><th class="num">G</th><th class="num">E</th><th class="num">P</th><th class="num">Goles</th></tr></thead><tbody>
      ${h.rivales.map(r => `<tr><td>${linkEquipo(r.id)}</td><td class="num">${r.pj}</td><td class="num">${r.g}</td>
        <td class="num">${r.e}</td><td class="num">${r.p}</td><td class="num">${r.gf}:${r.gc}</td></tr>`).join("")}
      </tbody></table></div>`;

    if (h.goleadores.length) html += `<h3>Goleadores del club en la Copa</h3>
      <p class="vacio">En ediciones viejas las fuentes a veces traen solo el apellido.</p>
      <div class="tabla-scroll"><table class="historial"><thead><tr><th>Jugador</th><th>Años</th><th class="num">Goles</th></tr></thead><tbody>
      ${h.goleadores.map(g => `<tr><td>${esc(g.nombre)}</td><td>${g.anios[0]}${g.anios[1] !== g.anios[0] ? `–${g.anios[1]}` : ""}</td>
        <td class="num">${g.n}</td></tr>`).join("")}
      </tbody></table></div>`;
    edicionEl.innerHTML = html;
  }

  function seleccionarEquipo(id, guardarEnHistorial) {
    navEl.querySelectorAll("a").forEach(a => a.removeAttribute("aria-current"));
    if (guardarEnHistorial) history.pushState(null, "", `?equipo=${encodeURIComponent(id)}`);
    const nombre = equipo(id).nombre;
    document.title = `${nombre} en la Copa Libertadores — Historial`;
    const desc = document.querySelector('meta[name="description"]');
    if (desc) desc.content = `${nombre} en la Copa Libertadores: ediciones jugadas, títulos, finales, partidos, goleadores y rivales.`;
    let canonica = document.querySelector('link[rel="canonical"]');
    if (!canonica) document.head.appendChild(canonica = Object.assign(document.createElement("link"), { rel: "canonical" }));
    canonica.href = `${URL_SITIO}?equipo=${encodeURIComponent(id)}`;
    pintarFondo(id);
    edicionEl.innerHTML = `<p class="vacio">Cargando ${esc(nombre)}…</p>`;
    cargarHistorial().then(() => mostrarEquipo(id)).catch(e => { edicionEl.innerHTML = `<p class="vacio">${esc(e.message)}</p>`; });
    window.scrollTo({ top: edicionEl.offsetTop - 16, behavior: "smooth" });
  }

  // El cuadro de búsqueda: al escribir aparece la lista de equipos que coinciden
  const buscarEl = document.getElementById("buscar-equipo");
  const sugerenciasEl = document.getElementById("sugerencias");
  let elegida = -1;   // sugerencia marcada con las flechas del teclado
  function mostrarSugerencias() {
    cargarHistorial().then(() => {
      const ids = buscarEquipos(buscarEl.value);
      elegida = -1;
      if (!buscarEl.value.trim()) { sugerenciasEl.hidden = true; return; }
      sugerenciasEl.innerHTML = ids.length ? ids.map(id => {
        const h = LIB.historial[id];
        const titulos = h.titulos.length ? ` · 🏆 ${h.titulos.length}` : "";
        return `<li role="option"><a href="?equipo=${esc(id)}" data-equipo="${esc(id)}">${bandera(id)}${club(id)}
          <span class="sug-meta">${plural(h.ediciones.length, "edición", "ediciones")}${titulos}</span></a></li>`;
      }).join("") : `<li class="sug-vacia">No hay equipos con “${esc(buscarEl.value.trim())}”</li>`;
      sugerenciasEl.hidden = false;
    }).catch(() => {});
  }
  function cerrarSugerencias() { sugerenciasEl.hidden = true; elegida = -1; }
  buscarEl.addEventListener("focus", () => { cargarHistorial().catch(() => {}); if (buscarEl.value.trim()) mostrarSugerencias(); });
  buscarEl.addEventListener("input", mostrarSugerencias);
  buscarEl.addEventListener("keydown", e => {
    const links = [...sugerenciasEl.querySelectorAll("a[data-equipo]")];
    if (e.key === "Escape") return cerrarSugerencias();
    if (!links.length || sugerenciasEl.hidden) return;
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      elegida = (elegida + (e.key === "ArrowDown" ? 1 : -1) + links.length) % links.length;
      links.forEach((a, i) => a.classList.toggle("marcada", i === elegida));
    } else if (e.key === "Enter") {
      e.preventDefault();
      elegirSugerencia(links[Math.max(elegida, 0)].dataset.equipo);
    }
  });
  function elegirSugerencia(id) {
    cerrarSugerencias();
    buscarEl.value = equipo(id).nombre;
    buscarEl.blur();
    seleccionarEquipo(id, true);
  }
  sugerenciasEl.addEventListener("click", e => {
    const a = e.target.closest("a[data-equipo]");
    if (!a || e.ctrlKey || e.metaKey || e.shiftKey) return;   // ctrl+clic: abrir en otra pestaña
    e.preventDefault();
    elegirSugerencia(a.dataset.equipo);
  });
  document.addEventListener("click", e => { if (!e.target.closest(".buscador")) cerrarSugerencias(); });

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
    pintarFondo(e.campeon);
  }

  // La página se viste con los colores del campeón de esa edición (fondo y letras)
  function pintarFondo(campeon) {
    const colores = (LIB.colores || {})[campeon];
    const estilo = document.documentElement.style;
    ["--fondo", "--texto", "--acento"].forEach(v => estilo.removeProperty(v));
    if (!colores) return;   // sin campeón: colores de siempre
    estilo.setProperty("--fondo", colores[0]);
    estilo.setProperty("--texto", colores[1]);
    estilo.setProperty("--acento", colores[1]);
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
  // ?equipo=river-plate abre la ficha del club; si no, la edición pedida (o la última)
  function abrirDesdeLaUrl() {
    const id = new URLSearchParams(location.search).get("equipo");
    if (id && LIB.equipos[id]) seleccionarEquipo(id);
    else seleccionar(anioDeLaUrl());
  }
  // Botón "Ver" de goleadores y asistidores: muestra u oculta el renglón de abajo
  edicionEl.addEventListener("click", e => {
    const link = e.target.closest("a[data-anio], a[data-equipo]");
    if (link && !e.ctrlKey && !e.metaKey && !e.shiftKey) {   // años y rivales de la ficha de un equipo
      e.preventDefault();
      if (link.dataset.equipo) seleccionarEquipo(link.dataset.equipo, true);
      else { seleccionar(link.dataset.anio, true); window.scrollTo({ top: 0, behavior: "smooth" }); }
      return;
    }
    const pestana = e.target.closest("button.pestana");
    if (pestana) {   // pestañas "Fase de grupos" / "Fase eliminatoria"
      const botones = [...pestana.parentElement.children];
      let panel = pestana.parentElement.nextElementSibling;
      botones.forEach(b => {
        b.setAttribute("aria-selected", b === pestana);
        panel.hidden = b !== pestana;
        panel = panel.nextElementSibling;
      });
      return;
    }
    const ordenPlantel = e.target.closest("button.orden-plantel");
    if (ordenPlantel) {   // "Por posición" / "Por nombre": reordena todos los planteles de la edición
      const modo = ordenPlantel.dataset.ordenPlantel;
      try { localStorage.setItem("ordenPlantel", modo); } catch {}
      edicionEl.querySelectorAll("button.orden-plantel").forEach(b => b.setAttribute("aria-pressed", b.dataset.ordenPlantel === modo));
      edicionEl.querySelectorAll("details.plantel tbody").forEach(tb => {
        const filas = [...tb.rows].map(tr => ({ nombre: tr.dataset.nombre, linea: +tr.dataset.linea, tr }));
        filas.sort((a, b) => (modo === "posicion" ? a.linea - b.linea : 0) || porNombre(a, b));
        filas.forEach(f => tb.appendChild(f.tr));
      });
      return;
    }
    const orden = e.target.closest("button.orden");
    if (orden) {   // "Por llave" / "Por fecha": cambia el orden en todas las fases eliminatorias
      const modo = orden.dataset.orden;
      try { localStorage.setItem("ordenEliminatoria", modo); } catch {}
      edicionEl.querySelectorAll("button.orden").forEach(b => b.setAttribute("aria-pressed", b.dataset.orden === modo));
      edicionEl.querySelectorAll("[data-vista]").forEach(v => { v.hidden = v.dataset.vista !== modo; });
      return;
    }
    const mostrar = e.target.closest("button.mostrar-tabla");
    if (mostrar) {   // botón del título: muestra u oculta la tabla de goleadores / asistidores
      const tabla = mostrar.closest("h3").nextElementSibling;
      tabla.hidden = !tabla.hidden;
      mostrar.setAttribute("aria-expanded", !tabla.hidden);
      mostrar.textContent = tabla.hidden ? "Mostrar" : "Ocultar";
      return;
    }
    const todos = e.target.closest("button.ver-todos");
    if (todos) {   // "Ver todos": despliega el resto de la tabla que está justo arriba
      const resto = todos.previousElementSibling.querySelector("tbody.resto");
      resto.hidden = !resto.hidden;
      todos.textContent = resto.hidden ? `Ver todos (${todos.dataset.total})` : "Ver menos";
      return;
    }
    const boton = e.target.closest("button.ver");
    if (!boton) return;
    const detalle = boton.closest("tr").nextElementSibling;
    detalle.hidden = !detalle.hidden;
    boton.setAttribute("aria-expanded", !detalle.hidden);
    boton.textContent = detalle.hidden ? "Ver" : "Ocultar";
  });
  // El título "Copa Libertadores" lleva a la edición actual (la última)
  document.querySelector("a.inicio").addEventListener("click", e => {
    if (e.ctrlKey || e.metaKey || e.shiftKey) return;
    e.preventDefault();
    buscarEl.value = "";
    cerrarSugerencias();
    // Misma dirección sin "?edicion=…" (con "./" falla al abrir index.html con doble clic)
    history.pushState(null, "", location.pathname);
    seleccionar(LIB.indice[LIB.indice.length - 1].anio);
  });
  window.addEventListener("popstate", abrirDesdeLaUrl);   // botón "atrás" del navegador
  abrirDesdeLaUrl();
})();
