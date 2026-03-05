import os
import json
from fitparse import FitFile
from psycopg2 import connect
from psycopg2.extensions import cursor, connection
from psycopg2.extras import execute_values
from datetime import timezone, datetime

all_field_names = set()
summaries = None

with open('download/summaries.json') as f:
    summaries = json.load(f)


def find_summary(workout_id):
    for summary in summaries:
        if summary['trackid'] == workout_id:
            return summary


def parse_fit_file(
        file_path: str,
        workout_type: str,
        workout_id: str):
    fitfile = FitFile(file_path)
    workout_metrics = []
    summary = find_summary(workout_id)
    workout = (
        workout_type,
        workout_id,
        datetime.fromtimestamp(int(summary['end_time'])),
        summary['dis'],
        summary['calorie'],
        summary['run_time'],
        summary['total_step'],
        summary['avg_stride_length'],
        summary['avg_pace'],
        summary['min_pace'],
        summary['max_pace'],
        summary['avg_frequency'],
        summary['avg_heart_rate'],
        summary['min_heart_rate'],
        summary['max_heart_rate'],
        summary['min_altitude'],
        summary['max_altitude'],
        summary['altitude_ascend'],
        summary['altitude_descend'],
        summary['avg_altitude'],
        summary['distance_ascend'],
        summary['climb_dis_descend'],
        summary['climb_dis_ascend_time'],
        summary['climb_dis_descend_time'],
        summary['te'],
        summary['anaerobic_te'])
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
        workout_metrics.append((
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

    return workout_metrics, workout


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


def insert_workout_metrics(conn: connection, cur: cursor, metrics):
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


def insert_workout(conn: connection, cur: cursor, workout):
    query = """
    INSERT INTO workouts (
        workout_type,
        workout_id,
        end_time,
        dis,
        calorie,
        run_time,
        total_step,
        avg_stride_length,
        avg_pace,
        min_pace,
        max_pace,
        avg_frequency,
        avg_heart_rate,
        min_heart_rate,
        max_heart_rate,
        min_altitude,
        max_altitude,
        altitude_ascend,
        altitude_descend,
        avg_altitude,
        distance_ascend,
        climb_dis_descend,
        climb_dis_ascend_time,
        climb_dis_descend_time,
        te,
        anaerobic_te)
    VALUES %s
    ON CONFLICT DO NOTHING
    """
    execute_values(cur, query, [workout])
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
            workout_metrics, workout = parse_fit_file(
                file_path, workout_type, workout_id)
            insert_workout_metrics(conn, cur, workout_metrics)
            insert_workout(conn, cur, workout)
    cur.close()
    conn.close()
    print("All FIT files processed and stored in TimescaleDB.")
    print("All found field names: " + str(all_field_names))
