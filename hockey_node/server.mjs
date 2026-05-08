import express from "express";
import * as db from "./db.mjs";

const app = express();

db.connect();

app.use(express.static("."));
app.use(express.urlencoded({ extended: false }));

app.get("/", (req, res) => res.sendFile("landing.html", { root: "." }));

// ── Player season stats ───────────────────────────────────────────────────────
app.get("/api/players", (req, res) => {
  const name      = `%${req.query.name || ""}%`;
  const situation = req.query.situation || "all";
  const season    = req.query.season ? parseInt(req.query.season) : null;

  const params = [name, situation];
  const seasonClause = season ? "AND g.season_year = ?" : "";
  if (season) params.push(season);

  const sql = `
    SELECT
      p.player_id,
      p.player_name,
      p.position,
      p.shoots,
      p.birth_date,
      p.nationality,
      p.current_team,
      COALESCE(t.team_name, p.current_team) AS team_name,
      g.season_year,
      COUNT(DISTINCT pgs.game_id)        AS gp,
      SUM(pgs.goals)                     AS goals,
      SUM(pgs.primary_assists)           AS a1,
      SUM(pgs.secondary_assists)         AS a2,
      SUM(pgs.points)                    AS points,
      ROUND(SUM(pgs.x_goals), 2)         AS x_goals,
      ROUND(AVG(pgs.game_score), 3)      AS game_score,
      SUM(pgs.high_danger_goals)         AS hd_goals,
      ROUND(SUM(pgs.icetime) / 60.0, 1) AS toi_min,
      SUM(pgs.shots_on_goal)             AS shots,
      SUM(pgs.hits)                      AS hits,
      SUM(pgs.takeaways)                 AS takeaways,
      SUM(pgs.giveaways)                 AS giveaways
    FROM player_game_stats pgs
    JOIN player p ON pgs.player_id = p.player_id
    JOIN game   g ON pgs.game_id   = g.game_id
    LEFT JOIN team t ON p.current_team = t.team_code
    WHERE p.player_name LIKE ?
      AND pgs.situation = ?
      ${seasonClause}
    GROUP BY p.player_id, p.player_name, p.position, p.shoots, p.birth_date,
             p.nationality, p.current_team, t.team_name, g.season_year
    ORDER BY g.season_year DESC, points DESC
  `;

  db.query(sql, params, (results) => res.json(results));
});

// ── Player game-by-game stats ─────────────────────────────────────────────────
app.get("/api/player-games", (req, res) => {
  const playerId  = parseInt(req.query.player_id);
  const situation = req.query.situation || "all";
  const season    = req.query.season ? parseInt(req.query.season) : null;
  if (!playerId) return res.json([]);

  const params = [playerId, situation];
  const seasonClause = season ? "AND g.season_year = ?" : "";
  if (season) params.push(season);

  const sql = `
    SELECT
      g.game_id,
      g.date,
      g.season_year,
      g.home_team,
      g.away_team,
      COALESCE(ht.team_name, g.home_team) AS home_team_name,
      COALESCE(at.team_name, g.away_team) AS away_team_name,
      g.home_score,
      g.away_score,
      pgs.goals,
      pgs.primary_assists           AS a1,
      pgs.secondary_assists         AS a2,
      pgs.points,
      ROUND(pgs.x_goals, 2)         AS x_goals,
      pgs.game_score,
      pgs.high_danger_goals         AS hd_goals,
      ROUND(pgs.icetime / 60.0, 1)  AS toi_min,
      pgs.shots_on_goal             AS shots,
      pgs.hits,
      pgs.takeaways,
      pgs.giveaways
    FROM player_game_stats pgs
    JOIN game g ON pgs.game_id = g.game_id
    LEFT JOIN team ht ON g.home_team = ht.team_code
    LEFT JOIN team at ON g.away_team = at.team_code
    WHERE pgs.player_id = ?
      AND pgs.situation = ?
      ${seasonClause}
    ORDER BY g.date DESC
  `;

  db.query(sql, params, (results) => res.json(results));
});

// ── Team season stats ─────────────────────────────────────────────────────────
app.get("/api/teams", (req, res) => {
  const team   = req.query.team   || null;
  const season = req.query.season ? parseInt(req.query.season) : null;
  if (!team) return res.json([]);

  const clauses = ["situation = 'all'", "team = ?"];
  const params  = [team];
  if (season) { clauses.push("season = ?"); params.push(season); }
  const where = "WHERE " + clauses.join(" AND ");

  // Pull directly from the pre-aggregated import table — one row per team per season
  const sql = `
    SELECT
      team                                   AS team_code,
      CAST(season AS UNSIGNED)               AS season_year,
      CAST(games_played AS UNSIGNED)         AS gp,
      CAST(goalsFor AS UNSIGNED)             AS gf,
      CAST(goalsAgainst AS UNSIGNED)         AS ga,
      CAST(shotsOnGoalFor AS UNSIGNED)       AS sog_for,
      CAST(shotsOnGoalAgainst AS UNSIGNED)   AS sog_against,
      ROUND(CAST(xGoalsFor AS DECIMAL(10,2)), 2)     AS xgf,
      ROUND(CAST(xGoalsAgainst AS DECIMAL(10,2)), 2) AS xga,
      CAST(hitsFor AS UNSIGNED)              AS hits_for,
      CAST(takeawaysFor AS UNSIGNED)         AS takeaways,
      CAST(giveawaysFor AS UNSIGNED)         AS giveaways
    FROM import_seasons_all_teams
    ${where}
    ORDER BY CAST(season AS UNSIGNED) DESC
  `;

  db.query(sql, params, (results) => {
    // wins/losses not in seasons_all_teams — derive from game log separately
    // Just return what we have; frontend will display it
    res.json(results);
  });
});

// ── Team game-by-game ─────────────────────────────────────────────────────────
app.get("/api/team-games", (req, res) => {
  const team   = req.query.team;
  const season = req.query.season ? parseInt(req.query.season) : null;
  if (!team) return res.json([]);

  const params = [team, team];
  const seasonClause = season ? "AND g.season_year = ?" : "";
  if (season) params.push(season);

  // DISTINCT on game_id + date IS NOT NULL deduplicates the import
  const sql = `
    SELECT DISTINCT
      g.game_id,
      g.date,
      g.season_year,
      g.home_team,
      g.away_team,
      COALESCE(ht.team_name, g.home_team) AS home_team_name,
      COALESCE(at.team_name, g.away_team) AS away_team_name,
      g.home_score,
      g.away_score,
      g.home_win
    FROM game g
    LEFT JOIN team ht ON g.home_team = ht.team_code
    LEFT JOIN team at ON g.away_team = at.team_code
    WHERE (g.home_team = ? OR g.away_team = ?)
      AND g.is_playoffs = 0
      AND g.date IS NOT NULL
      ${seasonClause}
    ORDER BY g.date DESC
  `;

  db.query(sql, params, (games) => {
    const results = games.map(g => {
      const homeWin = Buffer.isBuffer(g.home_win) ? g.home_win[0] : Number(g.home_win);
      const isHome  = g.home_team === team;
      return {
        ...g,
        home_score: Number(g.home_score),
        away_score: Number(g.away_score),
        venue:  isHome ? "Home" : "Away",
        result: (isHome ? homeWin === 1 : homeWin === 0) ? "W" : "L",
      };
    });
    res.json(results);
  });
});

// ── Line stats ────────────────────────────────────────────────────────────────
app.get("/api/lines", (req, res) => {
  const p1        = parseInt(req.query.player1);
  const p2        = parseInt(req.query.player2);
  const p3        = req.query.player3 ? parseInt(req.query.player3) : null;
  const situation = req.query.situation || "5on5";
  const season    = req.query.season    ? parseInt(req.query.season) : null;

  if (!p1 || !p2) return res.json([]);

  const playerIds    = p3 ? [p1, p2, p3] : [p1, p2];
  const n            = playerIds.length;
  const seasonClause = season ? "AND g.season_year = ?" : "";

  const sharedGamesSql = `
    SELECT pgs.game_id
    FROM player_game_stats pgs
    JOIN game g ON pgs.game_id = g.game_id
    WHERE pgs.situation = ?
      ${seasonClause}
      AND pgs.player_id IN (${playerIds.map(() => "?").join(",")})
    GROUP BY pgs.game_id
    HAVING COUNT(DISTINCT pgs.player_id) = ?
  `;

  db.query(sharedGamesSql, [situation, ...(season ? [season] : []), ...playerIds, n], (gameRows) => {
    if (!gameRows.length) return res.json([]);

    const gameIds = gameRows.map((r) => r.game_id);

    const statsSql = `
      SELECT
        p.player_id,
        p.player_name,
        p.position,
        COALESCE(t.team_name, p.current_team) AS team_name,
        g.season_year,
        COUNT(DISTINCT pgs.game_id)        AS gp,
        SUM(pgs.goals)                     AS goals,
        SUM(pgs.primary_assists)           AS a1,
        SUM(pgs.secondary_assists)         AS a2,
        SUM(pgs.points)                    AS points,
        ROUND(SUM(pgs.x_goals), 2)         AS x_goals,
        SUM(pgs.high_danger_goals)         AS hd_goals,
        ROUND(SUM(pgs.icetime) / 60.0, 1) AS toi_min,
        ROUND(AVG(pgs.game_score), 3)      AS game_score
      FROM player_game_stats pgs
      JOIN player p ON pgs.player_id = p.player_id
      JOIN game   g ON pgs.game_id   = g.game_id
      LEFT JOIN team t ON p.current_team = t.team_code
      WHERE pgs.player_id IN (${playerIds.map(() => "?").join(",")})
        AND pgs.game_id   IN (${gameIds.map(() => "?").join(",")})
        AND pgs.situation = ?
      GROUP BY p.player_id, p.player_name, p.position, t.team_name, p.current_team, g.season_year
      ORDER BY g.season_year DESC, points DESC
    `;

    db.query(statsSql, [...playerIds, ...gameIds, situation], (results) =>
      res.json(results)
    );
  });
});

// ── Player search for autocomplete ────────────────────────────────────────────
app.get("/api/player-search", (req, res) => {
  const name = `%${req.query.name || ""}%`;
  const sql = `
    SELECT player_id, player_name, position, current_team
    FROM player
    WHERE player_name LIKE ?
    ORDER BY player_name
    LIMIT 20
  `;
  db.query(sql, [name], (results) => res.json(results));
});

// ── Shot stats ─────────────────────────────────────────────────────────────────
// All queries use player_game_stats / goalie_game_stats — never the raw shot table.
// The shot table (1GB+) causes server crashes on unfiltered scans.
app.get("/api/shots", (req, res) => {
  const type   = req.query.type   || "by-player";
  const season = req.query.season ? parseInt(req.query.season) : null;
  const team   = req.query.team   || null;
  const player = req.query.player ? `%${req.query.player}%` : null;

  // ── Top shooters by xGoals ───────────────────────────────────────────────
  if (type === "by-player") {
    const clauses = ["pgs.situation = 'all'"];
    const params  = [];
    if (season) { clauses.push("g.season_year = ?"); params.push(season); }
    if (team)   { clauses.push("p.current_team = ?"); params.push(team); }
    if (player) { clauses.push("p.player_name LIKE ?"); params.push(player); }
    const where = "WHERE " + clauses.join(" AND ");

    const sql = `
      SELECT
        p.player_name,
        p.position,
        COALESCE(t.team_name, p.current_team) AS team_name,
        g.season_year,
        SUM(pgs.shots_on_goal)   AS shots_on_goal,
        SUM(pgs.goals)           AS goals,
        ROUND(SUM(pgs.goals) * 100.0 / NULLIF(SUM(pgs.shots_on_goal), 0), 2) AS sh_pct,
        ROUND(SUM(pgs.x_goals), 2) AS total_xgoal,
        SUM(pgs.high_danger_goals)  AS hd_goals,
        SUM(pgs.high_danger_shots)  AS hd_shots
      FROM player_game_stats pgs
      JOIN player p ON pgs.player_id = p.player_id
      JOIN game   g ON pgs.game_id   = g.game_id
      LEFT JOIN team t ON p.current_team = t.team_code
      ${where}
      GROUP BY p.player_id, p.player_name, p.position, t.team_name, p.current_team, g.season_year
      HAVING shots_on_goal >= 10
      ORDER BY total_xgoal DESC
      LIMIT 50
    `;
    return db.query(sql, params, (results) => res.json(results));
  }

  // ── Goalie stats ──────────────────────────────────────────────────────────
  if (type === "by-goalie") {
    const clauses = ["ggs.situation = 'all'"];
    const params  = [];
    if (season) { clauses.push("g.season_year = ?"); params.push(season); }
    if (team)   { clauses.push("p.current_team = ?"); params.push(team); }
    const where = "WHERE " + clauses.join(" AND ");

    const sql = `
      SELECT
        p.player_name AS goalie,
        COALESCE(t.team_name, p.current_team) AS team_name,
        g.season_year,
        SUM(ggs.on_goal)                AS shots_faced,
        SUM(ggs.goals_against)          AS goals_against,
        ROUND((SUM(ggs.on_goal) - SUM(ggs.goals_against)) * 100.0
          / NULLIF(SUM(ggs.on_goal), 0), 3) AS save_pct,
        ROUND(SUM(ggs.x_goals) - SUM(ggs.goals_against), 2) AS gsax,
        SUM(ggs.high_danger_goals)      AS hd_goals_against,
        SUM(ggs.high_danger_shots)      AS hd_shots_faced,
        ROUND((SUM(ggs.high_danger_shots) - SUM(ggs.high_danger_goals)) * 100.0
          / NULLIF(SUM(ggs.high_danger_shots), 0), 2) AS hd_save_pct
      FROM goalie_game_stats ggs
      JOIN player p ON ggs.player_id = p.player_id
      JOIN game   g ON ggs.game_id   = g.game_id
      LEFT JOIN team t ON p.current_team = t.team_code
      ${where}
      GROUP BY ggs.player_id, p.player_name, t.team_name, p.current_team, g.season_year
      HAVING shots_faced >= 50
      ORDER BY gsax DESC
      LIMIT 30
    `;
    return db.query(sql, params, (results) => res.json(results));
  }

  res.json([]);
});

// ── Seasons list ──────────────────────────────────────────────────────────────
app.get("/api/seasons", (req, res) => {
  db.query("SELECT season_year, season_label FROM season ORDER BY season_year DESC", [], (r) =>
    res.json(r)
  );
});

// ── Teams list ────────────────────────────────────────────────────────────────
app.get("/api/teams-list", (req, res) => {
  db.query("SELECT team_code, COALESCE(team_name, team_code) AS team_name FROM team ORDER BY team_code", [], (r) =>
    res.json(r)
  );
});

app.listen(8080, () => console.log("Server running on http://localhost:8080"));
