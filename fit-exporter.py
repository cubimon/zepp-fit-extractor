import os
from fitparse import FitFile
from psycopg2 import connect
from psycopg2.extensions import cursor, connection
from psycopg2.extras import execute_values
from datetime import timezone

all_field_names = set()


def parse_fit_file(
        file_path: str,
        workout_type: str,
        workout_id: str):
    fitfile = FitFile(file_path)
    metrics = []
    for record in fitfile.get_messages('record'):
        timestamp = record.get_value('timestamp')
        distance = record.get_value('distance')
        heart_rate = record.get_value('heart_rate')
        cadence = record.get_value('cadence')
        altitude = record.get_value('altitude')
        enhanced_altitude = record.get_value('enhanced_altitude')
        speed = record.get_value('speed')
        enhanced_speed = record.get_value('enhanced_speed')
        step_length = record.get_value('step_length')
        position_lat = record.get_value('position_lat')
        position_long = record.get_value('position_long')
        field_names = [field.name for field in record.fields]
        all_field_names.update(field_names)
        if timestamp is None:
            continue
        # Ensure UTC timezone
        timestamp = timestamp.replace(tzinfo=timezone.utc)
        metrics.append((
            workout_type,
            workout_id,
            timestamp,
            distance,
            heart_rate,
            cadence,
            altitude,
            enhanced_altitude,
            speed,
            enhanced_speed,
            step_length,
            position_lat,
            position_long
        ))

    return metrics


def workout_exists(
        cur: cursor,
        workout_type: str,
        workout_id: str):
    query = """
    SELECT *
    FROM workout_metrics wm
    WHERE wm.workout_type = %s AND wm.workout_id = %s
    LIMIT 1
    """
    cur.execute(query, (workout_type, workout_id))
    result = cur.fetchone()
    return result is not None


def insert_metrics(conn: connection, cur: cursor, metrics):
    query = """
    INSERT INTO workout_metrics (
        workout_type,
        workout_id,
        timestamp,
        distance,
        heart_rate,
        cadence,
        enhanced_altitude,
        altitude,
        speed,
        enhanced_speed,
        step_length,
        position_lat,
        position_long)
    VALUES %s
    ON CONFLICT DO NOTHING
    """
    execute_values(cur, query, metrics)
    conn.commit()


if __name__ == "__main__":
    fit_folder = "./generated"
    conn = connect(
        dbname="workouts",
        user="cubimon",
        host="localhost"
    )
    cur = conn.cursor()
    for filename in os.listdir(fit_folder):
        if filename.endswith(".fit"):
            workout_type, rest = filename.split('-')
            workout_id = rest.split('.')[0]
            if workout_exists(cur, workout_type, workout_id):
                continue
            print(f"exporting {filename}")
            file_path = os.path.join(fit_folder, filename)
            metrics = parse_fit_file(file_path, workout_type, workout_id)
            insert_metrics(conn, cur, metrics)
    cur.close()
    conn.close()
    print("All FIT files processed and stored in TimescaleDB.")
    print("All found field names: " + str(all_field_names))
