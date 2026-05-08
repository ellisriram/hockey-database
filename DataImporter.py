import csv
import mysql.connector

DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = "2943"
DB_NAME = "hockey_schema"
DATA_DIR = "data/2026"
DEFAULT_DIVISION = "Unknown"
DEFAULT_CONFERENCE = "Unknown"

# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

def none_if_blank(val):
    val = str(val).strip()
    return val if val not in ("", "nan", "None") else None

def first_non_blank(row, keys):
    for key in keys:
        val = none_if_blank(row.get(key))
        if val is not None:
            return val
    return None

def to_int(val):
    val = none_if_blank(val)
    if val is None:
        return None
    try:
        return int(float(val))
    except ValueError:
        return None

def to_float(val):
    val = none_if_blank(val)
    if val is None:
        return None
    try:
        return float(val)
    except ValueError:
        return None

def to_bool(val):
    val = none_if_blank(val)
    if val is None:
        return None
    lowered = str(val).strip().lower()
    if lowered in ("true", "t", "yes", "y"):
        return True
    if lowered in ("false", "f", "no", "n"):
        return False
    return int(float(val)) == 1

def to_date(val):
    val = none_if_blank(val)
    if val is None:
        return None
    try:
        if len(val) == 8:
            return f"{val[:4]}-{val[4:6]}-{val[6:]}"
        return val
    except Exception:
        return None

def clean_situation(val):
    val = none_if_blank(val)
    return val if val in ('all', '5on5', '5on4', '4on5', 'other') else 'other'

def clean_position(val):
    val = none_if_blank(val)
    return val if val in ('C', 'L', 'R', 'D', 'G') else None

def clean_shoots(val):
    val = none_if_blank(val)
    return val if val in ('L', 'R') else None

# ------------------------------------------------------------------ #
# Insert functions
# ------------------------------------------------------------------ #

def insert_division(cursor, division_name, conference):
    cursor.execute("""
        INSERT IGNORE INTO division (division_name, conference)
        VALUES (%s, %s)
    """, (division_name, conference))

def insert_team(cursor, team_code, team_name=None, division_name=DEFAULT_DIVISION):
    cursor.execute("""
        INSERT INTO team (team_code, team_name, division)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE
            team_name = COALESCE(team_name, VALUES(team_name)),
            division = VALUES(division)
    """, (team_code, team_name, division_name))

def insert_season(cursor, season_year):
    label = f"{season_year}-{str(season_year + 1)[-2:]}"
    cursor.execute("""
        INSERT IGNORE INTO season (season_year, season_label)
        VALUES (%s, %s)
    """, (season_year, label))

def insert_player_full(cursor, row):
    cursor.execute("""
        INSERT IGNORE INTO player
            (player_id, player_name, position, shoots, birth_date, weight, height, nationality, jersey_number, current_team)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        to_int(row.get('playerId')),
        none_if_blank(row.get('name')),
        clean_position(row.get('primaryPosition')),
        clean_shoots(row.get('shootsCatches')),
        to_date(row.get('birthDate')),
        to_int(row.get('weight')),
        none_if_blank(row.get('height')),
        none_if_blank(row.get('nationality')),
        to_int(row.get('primaryNumber')),
        none_if_blank(row.get('team'))
    ))

def insert_player_stub(cursor, player_id, name, position, team_code):
    cursor.execute("""
        INSERT IGNORE INTO player (player_id, player_name, position, current_team)
        VALUES (%s, %s, %s, %s)
    """, (player_id, name, clean_position(position), team_code))

def insert_player_min(cursor, player_id):
    cursor.execute("""
        INSERT IGNORE INTO player (player_id)
        VALUES (%s)
    """, (player_id,))

def insert_game(cursor, game_id, season_year, game_date, home_team, away_team, home_score, away_score, is_playoffs):
    cursor.execute("""
        INSERT IGNORE INTO game
            (game_id, season_year, date, home_team, away_team, home_score, away_score, is_playoffs)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (game_id, season_year, game_date, home_team, away_team, home_score, away_score, is_playoffs))

def insert_player_game_stats(cursor, row, player_id, game_id):
    cursor.execute("""
        INSERT IGNORE INTO player_game_stats (
            player_id, game_id, situation,
            icetime, shifts, game_score,
            goals, primary_assists, secondary_assists,
            shots_on_goal, missed_shots, blocked_shot_attempts,
            x_goals, rebounds, rebound_goals, rebound_x_goals,
            x_goals_from_x_rebounds, x_goals_from_actual_rebounds,
            high_danger_shots, medium_danger_shots, low_danger_shots,
            high_danger_x_goals, medium_danger_x_goals, low_danger_x_goals,
            high_danger_goals, medium_danger_goals, low_danger_goals,
            flurry_adjusted_x_goals, score_venue_adjusted_x_goals,
            hits, takeaways, giveaways, d_zone_giveaways, face_offs_won,
            penalties, penalty_minutes,
            o_zone_shift_starts, d_zone_shift_starts, neutral_zone_shift_starts, fly_shift_starts,
            shots_blocked_by_player,
            on_ice_f_goals, on_ice_f_x_goals, on_ice_f_shot_attempts,
            on_ice_f_high_danger_shots, on_ice_f_high_danger_goals, on_ice_f_high_danger_x_goals,
            on_ice_a_goals, on_ice_a_x_goals, on_ice_a_shot_attempts,
            on_ice_a_high_danger_shots, on_ice_a_high_danger_goals, on_ice_a_high_danger_x_goals,
            x_goals_for_after_shifts, x_goals_against_after_shifts
        ) VALUES (
            %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s,
            %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s,
            %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s,
            %s, %s, %s, %s,
            %s,
            %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s,
            %s, %s
        )
    """, (
        player_id, game_id, clean_situation(row.get('situation')),
        to_int(row.get('icetime')), to_int(row.get('shifts')), to_float(row.get('gameScore')),
        to_int(row.get('I_F_goals')), to_int(row.get('I_F_primaryAssists')), to_int(row.get('I_F_secondaryAssists')),
        to_int(row.get('I_F_shotsOnGoal')), to_int(row.get('I_F_missedShots')), to_int(row.get('I_F_blockedShotAttempts')),
        to_float(row.get('I_F_xGoals')), to_int(row.get('I_F_rebounds')), to_int(row.get('I_F_reboundGoals')), to_float(row.get('I_F_reboundxGoals')),
        to_float(row.get('I_F_xGoalsFromxReboundsOfShots')), to_float(row.get('I_F_xGoalsFromActualReboundsOfShots')),
        to_int(row.get('I_F_highDangerShots')), to_int(row.get('I_F_mediumDangerShots')), to_int(row.get('I_F_lowDangerShots')),
        to_float(row.get('I_F_highDangerxGoals')), to_float(row.get('I_F_mediumDangerxGoals')), to_float(row.get('I_F_lowDangerxGoals')),
        to_int(row.get('I_F_highDangerGoals')), to_int(row.get('I_F_mediumDangerGoals')), to_int(row.get('I_F_lowDangerGoals')),
        to_float(row.get('I_F_flurryAdjustedxGoals')), to_float(row.get('I_F_scoreVenueAdjustedxGoals')),
        to_int(row.get('I_F_hits')), to_int(row.get('I_F_takeaways')), to_int(row.get('I_F_giveaways')), to_int(row.get('I_F_dZoneGiveaways')), to_int(row.get('I_F_faceOffsWon')),
        to_int(row.get('penalties')), to_int(row.get('I_F_penalityMinutes')),
        to_int(row.get('I_F_oZoneShiftStarts')), to_int(row.get('I_F_dZoneShiftStarts')), to_int(row.get('I_F_neutralZoneShiftStarts')), to_int(row.get('I_F_flyShiftStarts')),
        to_int(row.get('shotsBlockedByPlayer')),
        to_int(row.get('OnIce_F_goals')), to_float(row.get('OnIce_F_xGoals')), to_int(row.get('OnIce_F_shotAttempts')),
        to_int(row.get('OnIce_F_highDangerShots')), to_int(row.get('OnIce_F_highDangerGoals')), to_float(row.get('OnIce_F_highDangerxGoals')),
        to_int(row.get('OnIce_A_goals')), to_float(row.get('OnIce_A_xGoals')), to_int(row.get('OnIce_A_shotAttempts')),
        to_int(row.get('OnIce_A_highDangerShots')), to_int(row.get('OnIce_A_highDangerGoals')), to_float(row.get('OnIce_A_highDangerxGoals')),
        to_float(row.get('xGoalsForAfterShifts')), to_float(row.get('xGoalsAgainstAfterShifts'))
    ))

def insert_goalie_game_stats(cursor, row, player_id, game_id):
    cursor.execute("""
        INSERT IGNORE INTO goalie_game_stats (
            player_id, game_id, situation,
            icetime, x_goals, goals_against,
            unblocked_shot_attempts, x_rebounds, rebounds,
            x_freeze, freeze, x_on_goal, on_goal,
            x_play_stopped, play_stopped,
            x_play_continued_in_zone, play_continued_in_zone,
            x_play_continued_outside_zone, play_continued_outside_zone,
            flurry_adjusted_x_goals,
            low_danger_shots, medium_danger_shots, high_danger_shots,
            low_danger_x_goals, medium_danger_x_goals, high_danger_x_goals,
            low_danger_goals, medium_danger_goals, high_danger_goals,
            blocked_shot_attempts, penalty_minutes, penalties
        ) VALUES (
            %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s,
            %s, %s,
            %s, %s,
            %s,
            %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s
        )
    """, (
        player_id, game_id, clean_situation(row.get('situation')),
        to_int(row.get('icetime')), to_float(row.get('xGoals')), to_int(row.get('goals')),
        to_int(row.get('unblocked_shot_attempts')), to_float(row.get('xRebounds')), to_int(row.get('rebounds')),
        to_float(row.get('xFreeze')), to_int(row.get('freeze')), to_float(row.get('xOnGoal')), to_int(row.get('ongoal')),
        to_float(row.get('xPlayStopped')), to_int(row.get('playStopped')),
        to_float(row.get('xPlayContinuedInZone')), to_int(row.get('playContinuedInZone')),
        to_float(row.get('xPlayContinuedOutsideZone')), to_int(row.get('playContinuedOutsideZone')),
        to_float(row.get('flurryAdjustedxGoals')),
        to_int(row.get('lowDangerShots')), to_int(row.get('mediumDangerShots')), to_int(row.get('highDangerShots')),
        to_float(row.get('lowDangerxGoals')), to_float(row.get('mediumDangerxGoals')), to_float(row.get('highDangerxGoals')),
        to_int(row.get('lowDangerGoals')), to_int(row.get('mediumDangerGoals')), to_int(row.get('highDangerGoals')),
        to_int(row.get('blocked_shot_attempts')), to_int(row.get('penalityMinutes')), to_int(row.get('penalties'))
    ))

def insert_line(cursor, line_id, line_name, position, team_code):
    cursor.execute("""
        INSERT IGNORE INTO line (line_id, line_name, position, team_code)
        VALUES (%s, %s, %s, %s)
    """, (line_id, line_name, position, team_code))

def insert_line_game_stats(cursor, row, line_id, game_id):
    cursor.execute("""
        INSERT IGNORE INTO line_game_stats (
            line_id, game_id, situation, icetime,
            goals_for, x_goals_for, x_on_goal_for,
            shots_on_goal_for, missed_shots_for, blocked_shot_attempts_for, shot_attempts_for,
            rebounds_for, rebound_goals_for, rebound_x_goals_for,
            x_goals_from_x_rebounds_for, x_goals_from_actual_rebounds_for,
            high_danger_shots_for, medium_danger_shots_for, low_danger_shots_for,
            high_danger_x_goals_for, medium_danger_x_goals_for, low_danger_x_goals_for,
            high_danger_goals_for, medium_danger_goals_for, low_danger_goals_for,
            flurry_adjusted_x_goals_for, score_venue_adjusted_x_goals_for, total_shot_credit_for,
            hits_for, takeaways_for, giveaways_for, d_zone_giveaways_for,
            face_offs_won_for, penalties_for, penalty_minutes_for,
            goals_against, x_goals_against, x_on_goal_against,
            shots_on_goal_against, missed_shots_against, blocked_shot_attempts_against, shot_attempts_against,
            rebounds_against, rebound_goals_against, rebound_x_goals_against,
            x_goals_from_x_rebounds_against, x_goals_from_actual_rebounds_against,
            high_danger_shots_against, medium_danger_shots_against, low_danger_shots_against,
            high_danger_x_goals_against, medium_danger_x_goals_against, low_danger_x_goals_against,
            high_danger_goals_against, medium_danger_goals_against, low_danger_goals_against,
            flurry_adjusted_x_goals_against, score_venue_adjusted_x_goals_against, total_shot_credit_against,
            hits_against, takeaways_against, giveaways_against, d_zone_giveaways_against,
            face_offs_won_against, penalties_against, penalty_minutes_against
        ) VALUES (
            %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s
        )
    """, (
        line_id, game_id, clean_situation(row.get('situation')), to_int(row.get('icetime')),
        to_int(row.get('goalsFor')), to_float(row.get('xGoalsFor')), to_float(row.get('xOnGoalFor')),
        to_int(row.get('shotsOnGoalFor')), to_int(row.get('missedShotsFor')), to_int(row.get('blockedShotAttemptsFor')), to_int(row.get('shotAttemptsFor')),
        to_int(row.get('reboundsFor')), to_int(row.get('reboundGoalsFor')), to_float(row.get('reboundxGoalsFor')),
        to_float(row.get('xGoalsFromxReboundsOfShotsFor')), to_float(row.get('xGoalsFromActualReboundsOfShotsFor')),
        to_int(row.get('highDangerShotsFor')), to_int(row.get('mediumDangerShotsFor')), to_int(row.get('lowDangerShotsFor')),
        to_float(row.get('highDangerxGoalsFor')), to_float(row.get('mediumDangerxGoalsFor')), to_float(row.get('lowDangerxGoalsFor')),
        to_int(row.get('highDangerGoalsFor')), to_int(row.get('mediumDangerGoalsFor')), to_int(row.get('lowDangerGoalsFor')),
        to_float(row.get('flurryAdjustedxGoalsFor')), to_float(row.get('scoreVenueAdjustedxGoalsFor')), to_float(row.get('totalShotCreditFor')),
        to_int(row.get('hitsFor')), to_int(row.get('takeawaysFor')), to_int(row.get('giveawaysFor')), to_int(row.get('dZoneGiveawaysFor')),
        to_int(row.get('faceOffsWonFor')), to_int(row.get('penaltiesFor')), to_int(row.get('penalityMinutesFor')),
        to_int(row.get('goalsAgainst')), to_float(row.get('xGoalsAgainst')), to_float(row.get('xOnGoalAgainst')),
        to_int(row.get('shotsOnGoalAgainst')), to_int(row.get('missedShotsAgainst')), to_int(row.get('blockedShotAttemptsAgainst')), to_int(row.get('shotAttemptsAgainst')),
        to_int(row.get('reboundsAgainst')), to_int(row.get('reboundGoalsAgainst')), to_float(row.get('reboundxGoalsAgainst')),
        to_float(row.get('xGoalsFromxReboundsOfShotsAgainst')), to_float(row.get('xGoalsFromActualReboundsOfShotsAgainst')),
        to_int(row.get('highDangerShotsAgainst')), to_int(row.get('mediumDangerShotsAgainst')), to_int(row.get('lowDangerShotsAgainst')),
        to_float(row.get('highDangerxGoalsAgainst')), to_float(row.get('mediumDangerxGoalsAgainst')), to_float(row.get('lowDangerxGoalsAgainst')),
        to_int(row.get('highDangerGoalsAgainst')), to_int(row.get('mediumDangerGoalsAgainst')), to_int(row.get('lowDangerGoalsAgainst')),
        to_float(row.get('flurryAdjustedxGoalsAgainst')), to_float(row.get('scoreVenueAdjustedxGoalsAgainst')), to_float(row.get('totalShotCreditAgainst')),
        to_int(row.get('hitsAgainst')), to_int(row.get('takeawaysAgainst')), to_int(row.get('giveawaysAgainst')), to_int(row.get('dZoneGiveawaysAgainst')),
        to_int(row.get('faceOffsWonAgainst')), to_int(row.get('penaltiesAgainst')), to_int(row.get('penalityMinutesAgainst'))
    ))

def insert_shot(cursor, row, game_id):
    cursor.execute("""
        INSERT IGNORE INTO shot (
            game_id, team_code, shooter_player_id, goalie_id,
            event, shot_type, shot_on_empty_net, shot_rebound, shot_rush,
            shot_generated_rebound, shot_goalie_froze, shot_play_stopped,
            shot_play_continued_in_zone, shot_play_continued_outside_zone,
            x_cord_adjusted, y_cord_adjusted, arena_adjusted_x_cord, arena_adjusted_y_cord,
            shot_angle_adjusted, arena_adjusted_shot_distance,
            x_goal, x_rebound, x_freeze,
            shot_angle_plus_rebound, shot_angle_rebound_royal_road,
            period, time,
            home_team_goals, away_team_goals, home_empty_net, away_empty_net,
            home_skaters_on_ice, away_skaters_on_ice,
            last_event_category, last_event_team,
            last_event_x_cord_adjusted, last_event_y_cord_adjusted,
            distance_from_last_event, speed_from_last_event,
            time_since_last_event, time_since_faceoff,
            player_position_that_did_event,
            shooter_time_on_ice, shooter_time_on_ice_since_faceoff,
            time_difference_since_change, average_rest_difference
        ) VALUES (
            %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s,
            %s, %s, %s, %s,
            %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s, %s
        )
    """, (
        game_id,
        none_if_blank(row.get('teamCode')) or none_if_blank(row.get('team')),
        to_int(row.get('shooterPlayerId')),
        to_int(row.get('goalieIdForShot')),
        none_if_blank(row.get('event')),
        none_if_blank(row.get('shotType')),
        to_bool(row.get('shotOnEmptyNet')),
        to_bool(row.get('shotRebound')),
        to_bool(row.get('shotRush')),
        to_bool(row.get('shotGeneratedRebound')),
        to_bool(row.get('shotGoalieFroze')),
        to_bool(row.get('shotPlayStopped')),
        to_bool(row.get('shotPlayContinuedInZone')),
        to_bool(row.get('shotPlayContinuedOutsideZone')),
        to_float(row.get('xCordAdjusted')),
        to_float(row.get('yCordAdjusted')),
        to_float(row.get('arenaAdjustedXCord')),
        to_float(row.get('arenaAdjustedYCord')),
        to_float(row.get('shotAngleAdjusted')),
        to_float(row.get('arenaAdjustedShotDistance')),
        to_float(row.get('xGoal')),
        to_float(row.get('xRebound')),
        to_float(row.get('xFreeze')),
        to_float(row.get('shotAnglePlusRebound')),
        to_bool(row.get('shotAngleReboundRoyalRoad')),
        to_int(row.get('period')),
        to_int(row.get('time')),
        to_int(row.get('homeTeamGoals')),
        to_int(row.get('awayTeamGoals')),
        to_bool(row.get('homeEmptyNet')),
        to_bool(row.get('awayEmptyNet')),
        to_int(row.get('homeSkatersOnIce')),
        to_int(row.get('awaySkatersOnIce')),
        none_if_blank(row.get('lastEventCategory')),
        none_if_blank(row.get('lastEventTeam')),
        to_float(first_non_blank(row, ['lastEventxCord_adjusted', 'lastEventxCordAdjusted', 'lastEventxCord'])),
        to_float(first_non_blank(row, ['lastEventyCord_adjusted', 'lastEventyCordAdjusted', 'lastEventyCord'])),
        to_float(row.get('distanceFromLastEvent')),
        to_float(row.get('speedFromLastEvent')),
        to_float(row.get('timeSinceLastEvent')),
        to_float(row.get('timeSinceFaceoff')),
        none_if_blank(row.get('playerPositionThatDidEvent')),
        to_float(row.get('shooterTimeOnIce')),
        to_float(row.get('shooterTimeOnIceSinceFaceoff')),
        to_float(row.get('timeDifferenceSinceChange')),
        to_float(row.get('averageRestDifference'))
    ))

# ------------------------------------------------------------------ #
# Connection
# ------------------------------------------------------------------ #

connection = mysql.connector.connect(
    host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME
)
cursor = connection.cursor()

seen_seasons = {}
seen_teams = {}
seen_players = {}
seen_games = {}
seen_lines = {}

season_count = team_count = player_count = game_count = 0
skater_stat_count = goalie_stat_count = line_count = line_stat_count = shot_count = 0

# ------------------------------------------------------------------ #
# 0. Default division for teams without metadata
# ------------------------------------------------------------------ #
insert_division(cursor, DEFAULT_DIVISION, DEFAULT_CONFERENCE)

# ------------------------------------------------------------------ #
# 1. Players — data/2026/all_players.csv
# ------------------------------------------------------------------ #
print("Loading all_players.csv...")
with open(f"{DATA_DIR}/all_players.csv", "r") as f:
    reader = csv.DictReader(f)
    for row in reader:
        team_code = none_if_blank(row.get('team'))
        if team_code and team_code not in seen_teams:
            insert_team(cursor, team_code)
            seen_teams[team_code] = True
            team_count += 1

        player_id = to_int(row.get('playerId'))
        if player_id and player_id not in seen_players:
            insert_player_full(cursor, row)
            seen_players[player_id] = True
            player_count += 1

connection.commit()
print(f"  Players: {player_count}, Teams: {team_count}")

# ------------------------------------------------------------------ #
# 2. Games — data/2026/2026_games_teams.csv
# One row per team per game; only insert the game once using HOME row
# ------------------------------------------------------------------ #
print("Loading 2026_games_teams.csv...")
with open(f"{DATA_DIR}/2026_games_teams.csv", "r") as f:
    reader = csv.DictReader(f)
    for row in reader:
        if none_if_blank(row.get('home_or_away')) != 'HOME':
            continue

        season_year = to_int(row.get('season'))
        if season_year and season_year not in seen_seasons:
            insert_season(cursor, season_year)
            seen_seasons[season_year] = True
            season_count += 1

        home_team = none_if_blank(row.get('playerTeam'))
        away_team = none_if_blank(row.get('opposingTeam'))
        home_team_name = none_if_blank(row.get('name'))
        for tc in [home_team, away_team]:
            if tc and tc not in seen_teams:
                insert_team(cursor, tc, home_team_name if tc == home_team else None)
                seen_teams[tc] = True
                team_count += 1

        game_id = to_int(row.get('gameId'))
        if game_id and game_id not in seen_games:
            insert_game(
                cursor, game_id, season_year,
                to_date(str(row.get('gameDate'))),
                home_team, away_team,
                to_int(row.get('goalsFor')), to_int(row.get('goalsAgainst')),
                to_bool(row.get('playoffGame'))
            )
            seen_games[game_id] = True
            game_count += 1

connection.commit()
print(f"  Seasons: {season_count}, Games: {game_count}")

# ------------------------------------------------------------------ #
# 3. Skater game stats — data/2026/2026_games_skaters.csv
# ------------------------------------------------------------------ #
print("Loading 2026_games_skaters.csv...")
with open(f"{DATA_DIR}/2026_games_skaters.csv", "r") as f:
    reader = csv.DictReader(f)
    for row in reader:
        player_id = to_int(row.get('playerId'))
        game_id = to_int(row.get('gameId'))
        season_year = to_int(row.get('season'))
        team_code = none_if_blank(row.get('playerTeam'))
        opposing_team = none_if_blank(row.get('opposingTeam'))
        home_or_away = none_if_blank(row.get('home_or_away'))

        if season_year and season_year not in seen_seasons:
            insert_season(cursor, season_year)
            seen_seasons[season_year] = True

        for tc in [team_code, opposing_team]:
            if tc and tc not in seen_teams:
                insert_team(cursor, tc)
                seen_teams[tc] = True
                team_count += 1

        if player_id and player_id not in seen_players:
            insert_player_stub(cursor, player_id, none_if_blank(row.get('name')), row.get('position'), team_code)
            seen_players[player_id] = True
            player_count += 1

        if game_id and game_id not in seen_games:
            home_team = team_code if home_or_away == 'HOME' else opposing_team
            away_team = opposing_team if home_or_away == 'HOME' else team_code
            insert_game(
                cursor, game_id, season_year,
                to_date(str(row.get('gameDate'))),
                home_team, away_team,
                None, None,
                None
            )
            seen_games[game_id] = True
            game_count += 1

        if player_id and game_id:
            insert_player_game_stats(cursor, row, player_id, game_id)
            skater_stat_count += 1

connection.commit()
print(f"  Skater stats: {skater_stat_count}")

# ------------------------------------------------------------------ #
# 4. Goalie game stats — data/2026/2026_games_goalies.csv
# ------------------------------------------------------------------ #
print("Loading 2026_games_goalies.csv...")
with open(f"{DATA_DIR}/2026_games_goalies.csv", "r") as f:
    reader = csv.DictReader(f)
    for row in reader:
        player_id = to_int(row.get('playerId'))
        game_id = to_int(row.get('gameId'))
        season_year = to_int(row.get('season'))
        team_code = none_if_blank(row.get('playerTeam'))
        opposing_team = none_if_blank(row.get('opposingTeam'))
        home_or_away = none_if_blank(row.get('home_or_away'))

        if season_year and season_year not in seen_seasons:
            insert_season(cursor, season_year)
            seen_seasons[season_year] = True

        for tc in [team_code, opposing_team]:
            if tc and tc not in seen_teams:
                insert_team(cursor, tc)
                seen_teams[tc] = True
                team_count += 1

        if player_id and player_id not in seen_players:
            insert_player_stub(cursor, player_id, none_if_blank(row.get('name')), 'G', team_code)
            seen_players[player_id] = True
            player_count += 1

        if game_id and game_id not in seen_games:
            home_team = team_code if home_or_away == 'HOME' else opposing_team
            away_team = opposing_team if home_or_away == 'HOME' else team_code
            insert_game(
                cursor, game_id, season_year,
                to_date(str(row.get('gameDate'))),
                home_team, away_team,
                None, None,
                None
            )
            seen_games[game_id] = True
            game_count += 1

        if player_id and game_id:
            insert_goalie_game_stats(cursor, row, player_id, game_id)
            goalie_stat_count += 1

connection.commit()
print(f"  Goalie stats: {goalie_stat_count}")

# ------------------------------------------------------------------ #
# 5. Line game stats — data/2026/2026_games_lines.csv
# ------------------------------------------------------------------ #
print("Loading 2026_games_lines.csv...")
with open(f"{DATA_DIR}/2026_games_lines.csv", "r") as f:
    reader = csv.DictReader(f)
    for row in reader:
        team_code = none_if_blank(row.get('playerTeam'))
        opposing_team = none_if_blank(row.get('opposingTeam'))
        home_or_away = none_if_blank(row.get('home_or_away'))
        season_year = to_int(row.get('season'))
        game_id = to_int(row.get('gameId'))

        if season_year and season_year not in seen_seasons:
            insert_season(cursor, season_year)
            seen_seasons[season_year] = True

        for tc in [team_code, opposing_team]:
            if tc and tc not in seen_teams:
                insert_team(cursor, tc)
                seen_teams[tc] = True
                team_count += 1

        line_id = none_if_blank(row.get('lineId'))
        if line_id and line_id not in seen_lines:
            insert_line(cursor, line_id, none_if_blank(row.get('name')), none_if_blank(row.get('position')), team_code)
            seen_lines[line_id] = True
            line_count += 1

        if game_id and game_id not in seen_games:
            home_team = team_code if home_or_away == 'HOME' else opposing_team
            away_team = opposing_team if home_or_away == 'HOME' else team_code
            insert_game(
                cursor, game_id, season_year,
                to_date(str(row.get('gameDate'))),
                home_team, away_team,
                None, None,
                None
            )
            seen_games[game_id] = True
            game_count += 1

        if line_id and game_id:
            insert_line_game_stats(cursor, row, line_id, game_id)
            line_stat_count += 1

connection.commit()
print(f"  Lines: {line_count}, Line stats: {line_stat_count}")

# ------------------------------------------------------------------ #
# 6. Shots — data/2026/2026_shots.csv
# ------------------------------------------------------------------ #
print("Loading 2026_shots.csv...")
with open(f"{DATA_DIR}/2026_shots.csv", "r") as f:
    reader = csv.DictReader(f)
    for row in reader:
        game_id = to_int(first_non_blank(row, ['game_id', 'gameId']))
        season_year = to_int(row.get('season'))
        team_code = none_if_blank(row.get('teamCode')) or none_if_blank(row.get('team'))
        home_team = none_if_blank(row.get('homeTeamCode'))
        away_team = none_if_blank(row.get('awayTeamCode'))

        if season_year and season_year not in seen_seasons:
            insert_season(cursor, season_year)
            seen_seasons[season_year] = True

        for tc in [team_code, home_team, away_team]:
            if tc and tc not in seen_teams:
                insert_team(cursor, tc)
                seen_teams[tc] = True
                team_count += 1

        if game_id and game_id not in seen_games:
            insert_game(
                cursor, game_id, season_year,
                None,
                home_team, away_team,
                to_int(row.get('homeTeamGoals')), to_int(row.get('awayTeamGoals')),
                to_bool(row.get('isPlayoffGame'))
            )
            seen_games[game_id] = True
            game_count += 1

        shooter_id = to_int(row.get('shooterPlayerId'))
        goalie_id = to_int(row.get('goalieIdForShot'))
        if shooter_id and shooter_id not in seen_players:
            insert_player_min(cursor, shooter_id)
            seen_players[shooter_id] = True
            player_count += 1
        if goalie_id and goalie_id not in seen_players:
            insert_player_min(cursor, goalie_id)
            seen_players[goalie_id] = True
            player_count += 1

        if game_id:
            insert_shot(cursor, row, game_id)
            shot_count += 1

connection.commit()
print(f"  Shots: {shot_count}")

cursor.close()
connection.close()

print("\n=== Final counts ===")
print(f"Seasons:      {season_count}")
print(f"Teams:        {team_count}")
print(f"Players:      {player_count}")
print(f"Games:        {game_count}")
print(f"Skater stats: {skater_stat_count}")
print(f"Goalie stats: {goalie_stat_count}")
print(f"Lines:        {line_count}")
print(f"Line stats:   {line_stat_count}")
print(f"Shots:        {shot_count}")