from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import mysql.connector

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        passwd="njkl;'",
        database="hockey_schema"
    )

def q(sql, params=()):
    conn = db()
    cur = conn.cursor(dictionary=True)
    cur.execute(sql, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

@app.get("/")
def root():
    return FileResponse("index.html")

@app.get("/player")
def player(name: str):
    players = q("""
        SELECT DISTINCT playerid, name, position, team, shootscatches, birthdate
        FROM import_all_players
        WHERE name LIKE %s
        LIMIT 10
    """, (f"%{name}%",))

    if not players:
        return []

    results = []
    for p in players:
        pid = p["playerid"]
        seasons = q("""
            SELECT
                season,
                COUNT(DISTINCT gameid)                          AS gp,
                SUM(CAST(i_f_goals AS DECIMAL))                AS goals,
                SUM(CAST(i_f_primaryassists AS DECIMAL))       AS a1,
                SUM(CAST(i_f_secondaryassists AS DECIMAL))     AS a2,
                SUM(CAST(i_f_points AS DECIMAL))               AS points,
                ROUND(SUM(CAST(i_f_xgoals AS DECIMAL)), 2)     AS x_goals,
                ROUND(AVG(CAST(gamescore AS DECIMAL)), 3)       AS game_score,
                SUM(CAST(i_f_highdangergoals AS DECIMAL))      AS hd_goals,
                ROUND(SUM(CAST(icetime AS DECIMAL)) / 60.0, 1) AS toi_min,
                SUM(CAST(i_f_shotsongoal AS DECIMAL))          AS shots,
                SUM(CAST(i_f_hits AS DECIMAL))                 AS hits,
                SUM(CAST(i_f_takeaways AS DECIMAL))            AS takeaways,
                SUM(CAST(i_f_giveaways AS DECIMAL))            AS giveaways
            FROM import_games_players
            WHERE playerid = %s AND situation = 'all'
            GROUP BY season
            ORDER BY season DESC
        """, (pid,))
        results.append({**p, "seasons": seasons})

    return results
