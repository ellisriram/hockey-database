import csv
import glob
import datetime
import mysql.connector

DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = "YOUR PASSWORD HERE" #make sure to change this to your MySQL password
DB_NAME = "Tennis_Schema"

CSV_PATTERN = "atp_matches_*.csv"

# Checks to see if a value is blank, returning None if so
def none_if_blank(blank_check):
    blank_check = str(blank_check).strip()
    if blank_check != "":
        return blank_check 
    else:
        return None

# Converts date from YYYYMMDD to YYYY-MM-DD, or returns None if blank
def to_date(date):
    date = none_if_blank(date)
    if date is None:
        return None
    return datetime.datetime.strptime(date, "%Y%m%d").strftime("%Y-%m-%d")

# Converts a value to an integer, or returns None if blank or not a valid integer
def to_int(int_check):
    int_check = none_if_blank(int_check)
    if int_check is None or int_check == "None":
        return None
    try:
        return int(int_check)
    except ValueError:
        return None

# Cleans the hand value, only allowing 'L' or 'R', anything else becomes None
def clean_hand(hand):
    # Only store 'L' or 'R', anything else becomes NULL
    hand = none_if_blank(hand)
    if hand in ('L', 'R'):
        return hand
    return None

# Estimates birthdate as January 1st of the year calculated from match date minus age, or returns None if age or match date is blank
def estimate_birthdate(age, match_current_date):
    # estimate birth year as match_year - age, and return YYYY-01-01
    if age is None or match_current_date is None:
        return None
    match_date = datetime.datetime.strptime(match_current_date, "%Y-%m-%d")
    birth_year = match_date.year - int(float(age))
    return str(birth_year) + "-01-01"

# Insert function for tournament
def insert_tournament(cursor, tournament_id, name, surface, draw_size, tourney_level, date):
    cursor.execute("""
        INSERT IGNORE INTO tournament (tournament_id, name, surface, draw_size, tourney_level, `date`)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (tournament_id, name, surface, draw_size, tourney_level, date))

# Insert function for player
def insert_player(cursor, player_name, hand, height, ioc, date_of_birth):
    cursor.execute("""
        INSERT INTO player (player_name, hand, height, ioc, date_of_birth)
        VALUES (%s, %s, %s, %s, %s)
    """, (player_name, hand, height, ioc, date_of_birth))
    return cursor.lastrowid

# Insert function for match
def insert_match(cursor, tournament_id, match_number, minutes_played, score, best_of, round_name):
    cursor.execute("""
        INSERT IGNORE INTO matches (tournament_id, match_number, minutes_played, score, best_of, `round`)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (tournament_id, match_number, minutes_played, score, best_of, round_name))

# Insert function for match outcome
def insert_match_outcome(cursor, tournament_id, match_number, player_id, result,
                       rank, rank_points, aces, double_faults, serve_points,
                       first_in, first_won, second_won, serve_games, bp_saved, bp_faced):
    cursor.execute("""
        INSERT IGNORE INTO match_outcome (tournament_id, match_number, player_id, result,
            `rank`, rank_points, aces, double_faults, serve_points,
            first_in, first_won, second_won, serve_games, bp_saved, bp_faced)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (tournament_id, match_number, player_id, result,
          rank, rank_points, aces, double_faults, serve_points,
          first_in, first_won, second_won, serve_games, bp_saved, bp_faced))

# Establishes database connection
connection = mysql.connector.connect(
    host=DB_HOST,
    user=DB_USER,
    password=DB_PASSWORD,
    database=DB_NAME
)
cursor = connection.cursor()

# Dictionaries to remember players we have already inserted
seen_players = {}
seen_tournaments = {}

# Counters for testing/checking at the end
player_count = 0
tournament_count = 0
match_count = 0
matchstat_count = 0
file_count = 0

# Processes each CSV data file, inserting tournaments, players, matches, and match outcomes while keeping track of what has already been inserted to avoid duplicates.
for filename in sorted(glob.glob(CSV_PATTERN)):
    file_count += 1

    with open(filename, "r") as f:
        reader = csv.DictReader(f)
        first_row = next(reader, None)
        if first_row is None or 'winner_name' not in first_row:
            continue
        for row in reader:
            tournament_id = none_if_blank(row["tourney_id"])
            name = none_if_blank(row["tourney_name"])
            surface = none_if_blank(row["surface"])
            draw_size = to_int(row["draw_size"])
            tourney_level = none_if_blank(row["tourney_level"])
            date = to_date(row["tourney_date"])

            if tournament_id not in seen_tournaments:
                insert_tournament(cursor, tournament_id, name, surface, draw_size, tourney_level, date)
                seen_tournaments[tournament_id] = True
                tournament_count += 1

            winner_name = none_if_blank(row["winner_name"])
            winner_hand = clean_hand(row["winner_hand"])
            winner_height = to_int(row["winner_ht"])
            winner_ioc = none_if_blank(row["winner_ioc"])
            winner_age = none_if_blank(row["winner_age"])
            winner_key = (winner_name, winner_ioc, winner_hand, winner_height)

            if winner_key not in seen_players:
                winner_dob = estimate_birthdate(winner_age, date)
                winner_id  = insert_player(cursor, winner_name, winner_hand, winner_height, winner_ioc, winner_dob)
                seen_players[winner_key] = winner_id
                player_count += 1
            else:
                winner_id = seen_players[winner_key]

            loser_name = none_if_blank(row["loser_name"])
            loser_hand = clean_hand(row["loser_hand"])
            loser_height = to_int(row["loser_ht"])
            loser_ioc = none_if_blank(row["loser_ioc"])
            loser_age = none_if_blank(row["loser_age"])
            loser_key = (loser_name, loser_ioc, loser_hand, loser_height)

            if loser_key not in seen_players:
                loser_dob = estimate_birthdate(loser_age, date)
                loser_id  = insert_player(cursor, loser_name, loser_hand, loser_height, loser_ioc, loser_dob)
                seen_players[loser_key] = loser_id
                player_count += 1
            else:
                loser_id = seen_players[loser_key]

            match_number = to_int(row["match_num"])
            minutes_played = to_int(row["minutes"])
            score = none_if_blank(row["score"])
            best_of = to_int(row["best_of"])
            round_name = none_if_blank(row["round"])
            insert_match(cursor, tournament_id, match_number, minutes_played, score, best_of, round_name)
            match_count += 1

            insert_match_outcome(cursor,tournament_id,match_number,winner_id,'W',to_int(row["winner_rank"]),to_int(row["winner_rank_points"]),
                to_int(row["w_ace"]),to_int(row["w_df"]),to_int(row["w_svpt"]),to_int(row["w_1stIn"]),to_int(row["w_1stWon"]),
                to_int(row["w_2ndWon"]),to_int(row["w_SvGms"]),to_int(row["w_bpSaved"]),to_int(row["w_bpFaced"])
            )
            matchstat_count += 1

            insert_match_outcome(cursor,tournament_id,match_number,loser_id,'L',to_int(row["loser_rank"]),to_int(row["loser_rank_points"]),
                to_int(row["l_ace"]),to_int(row["l_df"]),to_int(row["l_svpt"]),to_int(row["l_1stIn"]),to_int(row["l_1stWon"]),
                to_int(row["l_2ndWon"]),to_int(row["l_SvGms"]),to_int(row["l_bpSaved"]),to_int(row["l_bpFaced"])
            )
            matchstat_count += 1

# Commits to database and closes connection
connection.commit()
cursor.close()
connection.close()

# Prints out counts of files processed, players inserted, tournaments inserted, matches inserted, and match stats inserted for verification.
print("Files processed:", file_count)
print("Players inserted:", player_count)
print("Tournaments inserted:", tournament_count)
print("Matches inserted:", match_count)
print("Match stats inserted:", matchstat_count)