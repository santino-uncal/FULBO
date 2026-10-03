/* Los continentes de la portada (el cuadro con los mapas de Sudamérica y Europa): su confederación, sus copas internacionales y sus ligas nacionales.
   Se edita a mano.
   - copa: la clave de la copa en la página (?copa=libertadores); si no tiene, la copa todavía no está cargada ("próximamente").
   - paises: los países de cada continente con el código que usa la página (el de la FIFA), para contar los títulos
     de sus clubes en el Mundial de Clubes y la Intercontinental.
   - color: el del continente en su mapa.
   - nacionales: [país, nombre de la liga, página de la liga si ya está cargada]. */
window.CONTINENTES = {
  sudamerica: {
    nombre: "Sudamérica", confederacion: "Conmebol", color: "#2e9e57",
    internacionales: [
      { nombre: "Copa Libertadores", copa: "libertadores", desde: 1960, trofeo: "assets/img/copa-libertadores.webp" },
      { nombre: "Copa Sudamericana", copa: "sudamericana", desde: 2002, trofeo: "assets/img/copa-sudamericana.webp" },
      { nombre: "Recopa Sudamericana", copa: "recopa", desde: 1989, trofeo: "assets/img/copa-recopa.webp" },
    ],
    nacionales: [
      ["ARG", "Liga Profesional", "liga.html"], ["BRA", "Brasileirão"], ["URU", "Primera División"], ["PAR", "Primera División"],
      ["CHI", "Primera División"], ["COL", "Primera A"], ["PER", "Liga 1"], ["ECU", "LigaPro"],
      ["BOL", "División Profesional"], ["VEN", "Liga FUTVE"],
    ],
    paises: ["ARG", "BRA", "URU", "PAR", "CHI", "COL", "PER", "ECU", "BOL", "VEN"],
  },
  europa: {
    nombre: "Europa", confederacion: "UEFA", color: "#3f7fd9",
    internacionales: [
      { nombre: "Champions League", copa: "champions", desde: 1955, trofeo: "assets/img/copa-champions.webp", nota: "hasta 1992, Copa de Campeones de Europa" },
      { nombre: "Europa League", copa: "europa", desde: 1971, trofeo: "assets/img/copa-europa.webp", nota: "hasta 2009, Copa UEFA" },
      { nombre: "Conference League", copa: "conference", desde: 2021, trofeo: "assets/img/copa-conference.webp", nota: "hasta 2024, Europa Conference League" },
      { nombre: "Supercopa de Europa", copa: "supercopa", desde: 1972, trofeo: "assets/img/copa-supercopa.webp" },
    ],
    nacionales: [
      ["ENG", "Premier League"], ["ESP", "LaLiga"], ["ITA", "Serie A"], ["GER", "Bundesliga"], ["FRA", "Ligue 1"],
      ["POR", "Primeira Liga"], ["NED", "Eredivisie"], ["SCO", "Premiership"],
    ],
    paises: ["ESP", "ITA", "ENG", "SCO", "GER", "NED", "POR", "FRA", "AUT", "GRE", "ROU", "SWE", "YUG",
      "MCO", "NOR", "BEL", "CRO", "DEN", "AZE", "TUR", "KAZ", "CYP", "UKR", "CZE", "SVK", "SUI",
      "FIN", "IRL", "ISL", "LTU", "LUX", "LVA", "MLT", "NIR", "POL", "HUN", "BUL", "ALB", "SRB", "SVN", "MDA", "BLR", "ISR", "RUS", "GEO", "ARM", "BIH", "MKD", "AND", "GIB", "WAL", "EST", "KOS", "FRO", "LIE", "MNE", "SMR"],
  },
};
